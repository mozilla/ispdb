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
from django.utils.functional import curry
from django.db.models import Q

from ispdb.config.models import (Config, ConfigForm, Domain, DomainForm,
    DomainRequest, BaseDomainFormSet)
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


def details(request, id, confirm_delete=False):
    config = get_object_or_404(Config, ~Q(status='deleted'), pk=id)
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
            'confirm_delete': confirm_delete},
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
            config.status == 'requested' and config.owner == request.user)):
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
        if config.status == 'approved':
            DomainFormSet.form = staticmethod(curry(DomainForm,
                is_domainrequest=False))
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
                    if form in formset.initial_forms:
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
            if not config.domains and not config.domainrequests:
                #TODO show error message
                return HttpResponseRedirect('/')
            # we check if domain names already exist
            for domain in config.domainrequests.all():
                if Domain.objects.filter(name=domain).exclude(
                        Q(config__status='deleted') |
                        Q(config__status='invalid')):
                    #TODO show error message
                    return HttpResponseRedirect('/')
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
    if not (request.user.is_superuser or (
            config.status == 'requested' and config.owner == request.user)):
        return HttpResponseRedirect(reverse('ispdb_login'))
    if request.method == 'POST':
        data = request.POST
        if data.has_key('confirm_delete') and data['confirm_delete'] == "1":
          config.status = 'deleted'
          config.save()
          return HttpResponseRedirect(reverse('ispdb_list'))
        else:
            # The user dont have JS
            return details(request, config.id, confirm_delete=True)
    else:
        return details(request, config.id, confirm_delete=True)
