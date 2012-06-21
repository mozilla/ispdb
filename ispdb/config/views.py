# -*- coding: utf-8 -*-

import StringIO
import lxml.etree as ET

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.forms.formsets import formset_factory
from django.forms.models import inlineformset_factory
from django.contrib.auth import logout
from django.template import RequestContext
from django.utils import simplejson
from django.utils import timezone
from django.utils.functional import curry
from django.db.models import Q

from ispdb.config.models import (Config, ConfigForm, Domain, DomainForm,
    DomainRequest, BaseDomainFormSet, Issue, IssueForm)
from ispdb.config import serializers

def login(request):
    redirect_url = '/'
    if 'next' in request.GET:
        redirect_url = request.GET['next']
    return render_to_response("config/login.html", {'redir_url': redirect_url},
                              context_instance=RequestContext(request))

def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')

def intro(request):
    domains = Domain.objects.all()
    return render_to_response("config/intro.html", {'domains': domains},
                              context_instance=RequestContext(request))

def list(request, format="html"):
    if format == "xml":
        providers = ET.Element("providers")
        configs = Config.objects.filter(status='approved')
        for config in configs:
            provider = ET.SubElement(providers, "provider")
            ET.SubElement(provider, "id").text = unicode(config.id)
            ET.SubElement(provider, "export").text = reverse("ispdb_export_xml",
                                            kwargs={"id": config.id})
            ET.SubElement(provider, "lastUpdated").text = unicode(
                config.last_update_datetime)
        xml = ET.ElementTree(providers)
        output = StringIO.StringIO("w")
        xml.write(output, encoding="UTF-8", xml_declaration=True)
        response = HttpResponse(mimetype="text/xml")
        response.write(output.getvalue())
        output.close()
        return response
    configs = Config.objects.all()
    return render_to_response("config/list.html", {'configs': configs},
                              context_instance=RequestContext(request))

def details(request, id, error=None):
    config = get_object_or_404(Config, pk=id)
    other_fields = []
    incoming = []
    outgoing = []

    for field in config._meta.fields:
        data = {'name': field.name,
                'verbose_name': field.verbose_name,
                'choices': field.choices,
                'value': getattr(config, field.name)}
        if field.name.startswith('incoming'):
            incoming.append(data)
        elif field.name.startswith('outgoing'):
            if field.name not in ('outgoing_add_this_server'
                                  'outgoing_use_global_preferred_server'):
                outgoing.append(data)
        # We want a few others:
        elif field.name in ('last_update_datetime', 'settings_page_url'):
            other_fields.append(data)
    return render_to_response("config/details.html", {
            'config': config,
            'incoming': incoming,
            'outgoing': outgoing,
            'other_fields': other_fields,
            'error': error,
            'issues': config.reported_issues.filter(status="open")},
        context_instance=RequestContext(request))

def export_xml(request, version=None, id=None, domain=None):
    config = None
    if id is not None:
        config = Config.objects.filter(id=int(id))[0]
    elif domain is not None:
        config = Domain.objects.filter(name=domain)[0].config
    serialize = serializers.get(version)
    if serialize is None:
        raise Http404
    data = serialize(config)
    return HttpResponse(data, mimetype='text/xml')

@login_required
def edit(request, config_id):
    DomainFormSet = formset_factory(DomainForm, extra=0, max_num=10,
            formset=BaseDomainFormSet)
    InlineFormSet = inlineformset_factory(Config, DomainRequest)
    config = get_object_or_404(Config, pk=config_id)
    # Validate the user
    if not (request.user.is_superuser or (
            (config.status == 'requested' or config.status == 'suggested')
             and config.owner == request.user)):
        return HttpResponseRedirect(reverse('ispdb_login'))
    # Get initial data
    initial = []
    for domain in config.domains.all() or config.domainrequests.all():
        initial.append({'name': domain.name})

    if request.method == 'POST':
        data = request.POST
        # A form bound to the POST data
        config_form = ConfigForm(request.POST,
                                 request.FILES,
                                 instance=config)
        DomainFormSet.form = staticmethod(curry(DomainForm,
                                                config_status=config.status))
        formset = DomainFormSet(request.POST, request.FILES, initial=initial)
        if config_form.is_valid() and formset.is_valid():
            config_form.save()
            for form in formset.forms:
                # if the form hasn't changed, do nothing
                if not form.has_changed():
                    continue
                # check if we need to delete the domain
                if form.cleaned_data['delete']:
                    # if domain is new and is deleted, do nothing
                    if not form in formset.initial_forms:
                        continue
                    # get initial domain name
                    index = formset.initial_forms.index(form)
                    if config.status == 'approved':
                        d = config.domains.all()[index]
                    else:
                        d = config.domainrequests.all()[index]
                    d.delete()
                    continue
                else:   # update or create new domain
                    domain = form.cleaned_data['name']
                    # Check if deleted or invalid domain exists
                    exists = Domain.objects.filter(name=domain)
                    if exists:
                        if config.status == 'approved':
                            exists[0].config = config
                            exists[0].save()
                            continue
                        else:
                            claimed = DomainRequest(name=domain,
                                                    votes=1,
                                                    config=config)
                    # Check if it is a rename
                    elif form in formset.initial_forms:
                        index = formset.initial_forms.index(form)
                        if config.status == 'approved':
                            claimed = config.domains.all()[index]
                        else:
                            claimed = config.domainrequests.all()[index]
                        claimed.name = domain
                    else:
                        if config.status == 'approved':
                            claimed = Domain(name=domain,
                                             config=config)
                        else:
                            claimed = DomainRequest(name=domain,
                                                    votes=1,
                                                    config=config)
                    claimed.save()

            if config.status == 'suggested':
                id = config.issue.all()[0].id
                return HttpResponseRedirect(reverse('ispdb_show_issue',
                                                    args=[id]))
            return HttpResponseRedirect(reverse('ispdb_details',
                                                args=[config.id]))
    else:
        config_form = ConfigForm(instance=config)
        formset = DomainFormSet(initial=initial)

    return render_to_response('config/enter_config.html', {
        'formset': formset,
        'config_form': config_form,
        'action': 'edit',
        'callback': reverse('ispdb_edit', args=[config.id]),
    }, context_instance=RequestContext(request))



@login_required
def add(request, domain=None):
    DomainFormSet = formset_factory(DomainForm, extra=0, max_num=10,
        formset=BaseDomainFormSet)
    InlineFormSet = inlineformset_factory(Config, Domain, can_delete=False)
    action = 'add'

    #from nose.tools import set_trace;set_trace()
    if request.method == 'POST': # If the form has been submitted...
        data = request.POST
        formset = DomainFormSet(request.POST,request.FILES)
        # did the user fill in a full form, or are they just asking for some
        # domains to be registered
        if data['asking_or_adding'] == 'asking':
            config_form = ConfigForm()
            action = 'ask'
            if formset.is_valid():
                domains = []
                num_domains = int(data['form-TOTAL_FORMS'])
                for i in range(num_domains):
                    domains.append(data['form-' + unicode(i) + '-name'])
                # we'll create (unclaimed) domains if they don't exist, otherwise
                # register the vote
                for domain in domains:
                    exists = Domain.objects.filter(name=domain) or \
                             DomainRequest.objects.filter(name=domain)
                    if exists:
                        d = exists[0]
                        if isinstance(d, DomainRequest):
                            d.votes += 1
                            d.save()
                    else:
                        d = DomainRequest(name=domain,
                                          votes=1)
                        d.save()
                return HttpResponseRedirect('/') # Redirect after POST
        else:
            config = Config(owner=request.user, status='requested')
            # A form bound to the POST data
            config_form = ConfigForm(request.POST,
                                     request.FILES,
                                     instance=config)
            # All validation rules pass
            if config_form.is_valid() and formset.is_valid():
                config_form.save()
                for form in formset:
                    # discard deleted forms
                    if not form.cleaned_data or form.cleaned_data['delete']:
                        continue
                    domain = form.cleaned_data['name']
                    unclaimed = DomainRequest.objects.filter(name=domain,
                                                             config=None)
                    if unclaimed:
                        claimed = unclaimed[0]
                        claimed.config = config
                    else:
                        claimed = DomainRequest(name=domain,
                                                votes=1,
                                                config=config)
                    claimed.save()
                return HttpResponseRedirect(reverse('ispdb_details',
                                                    args=[config.id]))
    else:
        config_form = ConfigForm()
        formset = DomainFormSet(initial=[{'name': domain}])

    return render_to_response('config/enter_config.html', {
        'formset': formset,
        'config_form': config_form,
        'action': action,
        'callback': reverse('ispdb_add'),
    }, context_instance=RequestContext(request))

def queue(request):
    domains = DomainRequest.objects.filter(config=None).order_by('-votes')
    pending_configs = Config.objects.filter(status='requested')
    invalid_configs = Config.objects.filter(status='invalid')

    return render_to_response('config/queue.html', {
        'domains': domains,
        'pending_configs': pending_configs,
        'invalid_configs': invalid_configs,
    }, context_instance=RequestContext(request))

def policy(request):
    return render_to_response('config/policy.html', {},
                              context_instance=RequestContext(request))

@permission_required("config.can_approve")
def approve(request, id):
    config = get_object_or_404(Config, pk=id)
    if request.method == 'POST': # If the form has been submitted...
        data = request.POST
        if data.get('approved', False):
            # check if domains and domains requests are null
            if not config.domains.all() and not config.domainrequests.all():
                error = """Can't approve this configuration. There is no
                        correlated domain."""
                return details(request, id, error=error)
            # check if domain names already exist
            for domain in config.domainrequests.all():
                if Domain.objects.filter(name=domain).exclude(
                        Q(config__status='deleted') |
                        Q(config__status='invalid')):
                    error = """Can't approve this configuration. Domain is
                            already used by another approved configuration."""
                    return details(request, id, error=error)
            config.status = 'approved'
            for domain in config.domainrequests.all():
                exists = Domain.objects.filter(name=domain)
                if exists:
                    claimed = exists[0]
                    claimed.config = config
                else:
                    claimed = Domain(name=domain.name,
                                     config=config)
                claimed.save()
                domain.delete()
        elif data.get('denied', False):
            config.status = 'invalid'
        else:
            raise ValueError, "shouldn't get here"
        # XXX do something w/ the comment text
        config.save()
    return HttpResponseRedirect('/details/' + id) # Redirect after POST

@login_required
def delete(request, id):
    config = get_object_or_404(Config, pk=id)
    if not (request.user.has_perm('config.can_approve') or (
            (config.status == 'requested' or config.last_status == 'requested')
            and config.owner == request.user)):
        return HttpResponseRedirect(reverse('ispdb_login'))
    if request.method == 'POST':
        data = request.POST
        if data.has_key('delete') and data['delete'] == "delete":
            if not config.status in ("invalid", "requested"):
                return HttpResponseRedirect(reverse('ispdb_details',args=[id]))
            config.last_status = config.status
            config.deleted_datetime = timezone.now()
            config.status = 'deleted'
            config.save()
        elif data.has_key('delete') and data['delete'] == "undo":
            if not config.status == 'deleted':
                return HttpResponseRedirect(reverse('ispdb_details',args=[id]))
            delta = timezone.now() - config.deleted_datetime
            if not delta.days > 0:
                config.status = config.last_status
                config.last_status = ''
                config.save()
    return HttpResponseRedirect(reverse('ispdb_details', args=[id]))

@login_required
def report(request, id):
    config = get_object_or_404(Config, pk=id, status='approved')
    DomainFormSet = formset_factory(DomainForm, extra=0, max_num=10,
        formset=BaseDomainFormSet)
    InlineFormSet = inlineformset_factory(Config, Domain, can_delete=False)
    initial = []
    for domain in config.domains.all() or config.domainrequests.all():
        initial.append({'name': domain.name})

    if request.method == 'POST':
        data = request.POST
        p_config = Config()
        issue = Issue(config=config)
        config_form = ConfigForm(request.POST,
                                 request.FILES,
                                 instance=p_config)
        issue_form = IssueForm(request.POST, instance=issue)
        formset = DomainFormSet(request.POST, request.FILES, initial=initial)
        if issue_form.is_valid():
            issue.owner = request.user
            if issue_form.cleaned_data['show_form']:
                if config_form.is_valid() and formset.is_valid():
                    p_config.status = 'suggested'
                    p_config.owner = request.user
                    config_form.save()
                    issue.updated_config = p_config
                    issue_form.save()
                    for form in formset.forms:
                        # check if domain is deleted
                        if not form.cleaned_data or (
                                form.cleaned_data['delete']):
                            continue
                        else:   # create domain requests
                            domain = form.cleaned_data['name']
                            claimed = DomainRequest(name=domain,
                                                    config=p_config)
                            claimed.save()
                    return HttpResponseRedirect(reverse('ispdb_show_issue',
                                                        args=[issue.id]))
            else:
                issue_form.save()
                return HttpResponseRedirect(reverse('ispdb_show_issue',
                                                    args=[issue.id]))

    else:
        formset = DomainFormSet(initial=initial)
        config_form = ConfigForm(instance=config)
        issue = Issue(config=config)
        issue_form = IssueForm(instance=issue)
    return render_to_response('config/enter_config.html', {
        'formset': formset,
        'config_form': config_form,
        'issue_form': issue_form,
        'action': 'report',
        'callback': reverse('ispdb_report', args=[id]),
    }, context_instance=RequestContext(request))

def show_issue(request, id):
    issue = get_object_or_404(Issue, pk=id)
    other_fields = []
    incoming = []
    outgoing = []
    base = []
    non_modified_domains = set()
    removed_domains = set()
    added_domains = set()
    error = ""

    up_conf = issue.updated_config
    for field in issue.config._meta.fields:
        data = {'name': field.name,
                'verbose_name': field.verbose_name,
                'choices': field.choices,
                'value': getattr(issue.config, field.name)}
        if up_conf and field in up_conf._meta.fields:
            new_value = getattr(up_conf, field.name)
            if data['value'] != new_value:
                data['new_value'] = new_value
        if field.name in ('display_name', 'display_short_name'):
            base.append(data)
        elif field.name.startswith('incoming'):
            incoming.append(data)
        elif field.name.startswith('outgoing'):
            if field.name not in ('outgoing_add_this_server'
                                  'outgoing_use_global_preferred_server'):
                outgoing.append(data)
        elif field.name in ('settings_page_url', 'settings_page_language'):
            other_fields.append(data)

    if issue.updated_config:
        # get removed/added domains
        original_domains = []
        updated_domains = []
        for domain in (issue.config.domains.all() or
                       issue.config.domainrequets.all()):
            original_domains.append(domain.name)
        for domain in issue.updated_config.domainrequests.all():
            updated_domains.append(domain.name)
        d_set = set(original_domains)
        ud_set = set(updated_domains)
        non_modified_domains = d_set.intersection(updated_domains)
        removed_domains = d_set.difference(updated_domains)
        added_domains = ud_set.difference(original_domains)

    if request.method == 'POST':
        data = request.POST
        if not request.user.is_superuser:
            return HttpResponseRedirect(reverse('ispdb_login'))
        if data['action'] == 'close':
            issue.status = 'closed'
            issue.save()
        elif data['action'] == 'merge':
            if not issue.config.status == "approved":
                error = "Can't merge into non approved configurations."
            elif issue.updated_config:
                # check if any of the added domains are already bound to some
                # approved configuration
                if added_domains:
                    for domain in added_domains:
                        if Domain.objects.filter(name=domain,
                                                 config__status="approved"):
                            error = """Can't approve this configuration.
                                    Domain %s is already used by another approved
                                    configuration.""" % (domain)
                            break;
                if not error:
                    for domain in removed_domains:
                        d = Domain.objects.filter(name=domain)[0]
                        d.delete()
                    for domain in added_domains:
                        exists = Domain.objects.filter(name=domain)
                        if exists:
                            exists[0].config = issue.config
                            exists[0].save()
                        else:
                            claimed = Domain(name=domain,
                                             config=issue.config)
                            claimed.save()
                    all_fields = base + incoming + outgoing + other_fields
                    for field in all_fields:
                        if field.has_key('new_value'):
                            setattr(issue.config, field['name'], field['new_value'])
                    issue.updated_config.status = 'deleted'
                    issue.updated_config.save()
                    issue.config.save()
                    issue.status = 'closed'
                    issue.save()
                    return HttpResponseRedirect(reverse('ispdb_details',
                        args=[issue.config.id]))

    return render_to_response("config/show_issue.html", {
            'issue': issue,
            'base': base,
            'incoming': incoming,
            'outgoing': outgoing,
            'other_fields': other_fields,
            'non_modified_domains': non_modified_domains,
            'removed_domains': removed_domains,
            'added_domains': added_domains,
            'error': error,
        }, context_instance=RequestContext(request))
