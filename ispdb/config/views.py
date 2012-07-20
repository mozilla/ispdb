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
from django.forms.models import modelformset_factory
from django.contrib.auth import logout
from django.template import RequestContext
from django.utils import simplejson
from django.utils import timezone
from django.utils.functional import curry
from django.db.models import Q
from django.contrib import comments
from django.contrib.comments.views.comments import post_comment
from django.contrib.comments.models import Comment
from django.contrib.comments.views.moderation import delete as delete_comment
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from ispdb.config.models import (Config, ConfigForm, Domain, DomainForm,
    DomainRequest, BaseDomainFormSet, Issue, IssueForm, DocURL, DocURLDesc,
    BaseDocURLFormSet, DocURLForm, DocURLDescForm, BaseDocURLDescFormSet)
from ispdb.config import serializers
from ispdb.config.configChecks import do_domain_checks
from ispdb.config.configChecks import do_config_checks

@login_required
def comment_post_wrapper(request):
    if not request.method == 'POST':
        return HttpResponseRedirect('/')
    return post_comment(request)

@permission_required("comments.can_moderate")
def delete_comment(request, id):
    comment = get_object_or_404(comments.get_model(), pk=id,
        site__pk=settings.SITE_ID)
    comment.is_removed = True
    comment.save()
    redir = request.META.get('HTTP_REFERER', None) or '/'
    return HttpResponseRedirect(redir)

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
        elif field.name in ('last_update_datetime'):
            other_fields.append(data)
    # Doc URLs
    DocURLFormSet = modelformset_factory(DocURL, extra=0,
            form=DocURLForm, formset=BaseDocURLFormSet)
    docurl_formset = DocURLFormSet(queryset=config.docurl_set.all())
    return render_to_response("config/details.html", {
            'config': config,
            'incoming': incoming,
            'outgoing': outgoing,
            'other_fields': other_fields,
            'error': error,
            'issues': config.reported_issues.filter(status="open"),
            'docurls': docurl_formset},
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
    config = get_object_or_404(Config, pk=config_id)
    # Validate the user
    if not (request.user.is_superuser or (
            (config.status == 'requested' or config.status == 'suggested')
             and config.owner == request.user)):
        return HttpResponseRedirect(reverse('ispdb_login'))
    # Get initial data
    if config.domains.all():
        model = Domain
    else:
        model = DomainRequest
    DomainFormSet = modelformset_factory(model, extra=0, max_num=10,
            form=DomainForm, formset=BaseDomainFormSet)
    domain_queryset = Domain.objects.filter(config=config) or \
            DomainRequest.objects.filter(config=config)
    DocURLFormSet = modelformset_factory(DocURL, extra=0,
            form=DocURLForm, formset=BaseDocURLFormSet)
    docurl_queryset = config.docurl_set.all()

    if request.method == 'POST':
        data = request.POST
        # A form bound to the POST data
        domain_formset = DomainFormSet(request.POST, request.FILES,
                queryset=domain_queryset)
        docurl_formset = DocURLFormSet(request.POST, request.FILES,
                queryset=docurl_queryset)
        config_form = ConfigForm(request.POST,
                                 request.FILES,
                                 instance=config,
                                 domain_formset=domain_formset,
                                 docurl_formset=docurl_formset)
        if config_form.is_valid_all():
            config_form.save_all()
            if config.status == 'suggested':
                id = config.issue.all()[0].id
                return HttpResponseRedirect(reverse('ispdb_show_issue',
                                                    args=[id]))
            return HttpResponseRedirect(reverse('ispdb_details',
                                                args=[config.id]))
    else:
        docurl_formset = DocURLFormSet(queryset=docurl_queryset)
        domain_formset = DomainFormSet(queryset=domain_queryset)
        config_form = ConfigForm(instance=config,
                                 domain_formset=domain_formset,
                                 docurl_formset=docurl_formset)

    return render_to_response('config/enter_config.html', {
        'config_form': config_form,
        'action': 'edit',
        'callback': reverse('ispdb_edit', args=[config.id]),
    }, context_instance=RequestContext(request))



@login_required
def add(request, domain=None):
    DomainFormSet = modelformset_factory(DomainRequest, extra=1, max_num=10,
            form=DomainForm, formset=BaseDomainFormSet)
    DocURLFormSet = formset_factory(DocURLForm, extra=1,
            formset=BaseDocURLFormSet)
    action = 'add'
    has_errors = False

    if request.method == 'POST': # If the form has been submitted...
        data = request.POST
        docurl_formset = DocURLFormSet(request.POST, request.FILES,
                queryset=DocURL.objects.none())
        domain_formset = DomainFormSet(request.POST, request.FILES,
                queryset=DomainRequest.objects.none())
        # did the user fill in a full form, or are they just asking for some
        # domains to be registered
        if data['asking_or_adding'] == 'asking':
            config_form = ConfigForm(domain_formset=domain_formset,
                                     docurl_formset=docurl_formset)
            action = 'ask'
            if domain_formset.is_valid():
                domain_formset.save(commit=False)
                for form in domain_formset:
                    name = form.instance.name
                    exists = DomainRequest.objects.filter(name=name)
                    if exists:
                        domain = exists[0]
                        domain.votes += 1
                        domain.save()
                    else:
                        form.save()
                return HttpResponseRedirect('/') # Redirect after POST
        else:
            config = Config(owner=request.user, status='requested')
            # A form bound to the POST data
            config_form = ConfigForm(request.POST,
                                     request.FILES,
                                     instance=config,
                                     domain_formset=domain_formset,
                                     docurl_formset=docurl_formset)
            # All validation rules pass
            if config_form.is_valid_all():
                config_form.save_all()
                return HttpResponseRedirect(reverse('ispdb_details',
                                                    args=[config.id]))
            else:
                has_errors = True
    else:
        docurl_formset = DocURLFormSet(queryset=DocURL.objects.none())
        domain_formset = DomainFormSet(initial=[{'name': domain}],
                queryset=DomainRequest.objects.none())
        config_form = ConfigForm(domain_formset=domain_formset,
                                 docurl_formset=docurl_formset)

    return render_to_response('config/enter_config.html', {
        'config_form': config_form,
        'action': action,
        'callback': reverse('ispdb_add'),
        'has_errors': has_errors
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
    old_status = config.status
    message = ''
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
            # Check mandatory comment when invalidating
            if data['comment'] == 'Other - invalid':
                if not data['commenttext']:
                    error = "Enter a comment."
                    return details(request, id, error=error)
                message = data['commenttext']
            else:
                message = data['comment']
            config.status = 'invalid'
        else:
            raise ValueError, "shouldn't get here"
        config.save()
        comment = Comment(user_name='ISPDB System',
                          site_id=settings.SITE_ID)
        c = "<ul><li><b>Status</b> changed from <b><i>%s</i></b> to \
             <b><i>%s</i></b> by %s</li></ul>\n %s" % (old_status,
            config.status, request.user.email, message)
        comment.comment = c
        comment.content_type = ContentType.objects.get_for_model(Config)
        comment.object_pk = config.pk
        comment.save()

    return HttpResponseRedirect('/details/' + id) # Redirect after POST

@permission_required("config.can_approve")
def sanity(request, id):
    config = get_object_or_404(Config, pk=id)
    domains = config.domains.all() or config.domainrequests.all()
    domain_errors, domain_warnings = do_domain_checks(domains)
    config_errors, config_warnings = do_config_checks(config)
    data = simplejson.dumps({"errors" : domain_errors + config_errors,
                             "warnings" : domain_warnings + config_warnings,
                            })
    return HttpResponse(data, mimetype='application/json')

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
    has_errors = False
    # Get initial data
    if config.domains.all():
        model = Domain
    else:
        model = DomainRequest
    DomainFormSet = modelformset_factory(model, extra=0, max_num=10,
            form=DomainForm, formset=BaseDomainFormSet)
    domain_queryset = config.domains.all() or config.domainrequests.all()
    DocURLFormSet = modelformset_factory(DocURL, extra=0,
            form=DocURLForm, formset=BaseDocURLFormSet)
    docurl_queryset = config.docurl_set.all()

    if request.method == 'POST':
        data = request.POST
        domain_formset = DomainFormSet(request.POST, request.FILES,
                queryset=domain_queryset)
        docurl_formset = DocURLFormSet(request.POST, request.FILES,
                queryset=docurl_queryset)
        p_config = Config(owner=request.user, status='suggested')
        issue = Issue(config=config, owner=request.user)
        config_form = ConfigForm(request.POST,
                                 request.FILES,
                                 instance=p_config,
                                 domain_formset=domain_formset,
                                 docurl_formset=docurl_formset)
        issue_form = IssueForm(request.POST, instance=issue)
        if issue_form.is_valid():
            if issue_form.cleaned_data['show_form']:
                if config_form.is_valid_all():
                    # save forms manually because we don't want to update the
                    # original objects
                    config_form.save()
                    # Save domains
                    for form in domain_formset:
                        if not form.cleaned_data or (
                                form.cleaned_data['DELETE']):
                            continue
                        name = form.cleaned_data['name']
                        domain = DomainRequest(name=name,
                                               config=p_config)
                        domain.save()
                    # Save DocURL formset
                    docurl_formset.save(commit=False)
                    for form in docurl_formset:
                        form.instance.pk = None
                        if not form.cleaned_data or (
                                form.cleaned_data['DELETE']):
                            continue
                        form.instance.config = p_config
                        for desc_form in form.desc_formset:
                            desc_form.instance.pk = None
                            if not desc_form.cleaned_data or (
                                    desc_form.cleaned_data['DELETE']):
                                continue
                    docurl_formset.save()
                    # Save Issue
                    issue.updated_config = p_config
                    issue_form.save()
                    return HttpResponseRedirect(reverse('ispdb_show_issue',
                                                        args=[issue.id]))
                else:
                    has_errors = True
            else:
                issue_form.save()
                return HttpResponseRedirect(reverse('ispdb_show_issue',
                                                    args=[issue.id]))

    else:
        domain_formset = DomainFormSet(queryset=domain_queryset)
        docurl_formset = DocURLFormSet(queryset=docurl_queryset)
        config_form = ConfigForm(instance=config,
                                 domain_formset=domain_formset,
                                 docurl_formset=docurl_formset)
        issue = Issue(config=config)
        issue_form = IssueForm(instance=issue)
    return render_to_response('config/enter_config.html', {
        'config_form': config_form,
        'issue_form': issue_form,
        'action': 'report',
        'callback': reverse('ispdb_report', args=[id]),
        'has_errors': has_errors,
    }, context_instance=RequestContext(request))

def show_issue(request, id):
    issue = get_object_or_404(Issue, pk=id)
    incoming = []
    outgoing = []
    base = []
    non_modified_domains = set()
    removed_domains = set()
    added_domains = set()
    error = ""
    new_docurl_formset = []

    up_conf = issue.updated_config
    if up_conf:
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
        # Doc URLs
        DocURLFormSet = modelformset_factory(DocURL, extra=0,
                form=DocURLForm, formset=BaseDocURLFormSet)
        docurl_formset = DocURLFormSet(queryset=issue.config.docurl_set.all())
        new_docurl_formset = DocURLFormSet(queryset=up_conf.docurl_set.all())

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
                    # update domains
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
                    # update config fields
                    all_fields = base + incoming + outgoing
                    for field in all_fields:
                        if field.has_key('new_value'):
                            setattr(issue.config, field['name'], field['new_value'])
                    # update docurls
                    docurl_formset.delete()
                    for docurl in new_docurl_formset:
                        docurl.instance.config = issue.config
                        docurl.instance.save()
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
            'non_modified_domains': non_modified_domains,
            'removed_domains': removed_domains,
            'added_domains': added_domains,
            'new_docurl_formset': new_docurl_formset,
            'error': error,
        }, context_instance=RequestContext(request))
