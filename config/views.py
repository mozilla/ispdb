from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from ispdb.config.models import Config, ConfigForm, Domain, DomainForm, UnclaimedDomain
from django.shortcuts import get_object_or_404, render_to_response
from django.forms.formsets import formset_factory
from django.forms.models import inlineformset_factory
from django.contrib.auth import logout
from django.template import RequestContext
import sys

def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')

@login_required
def admin_login(request):
    return HttpResponseRedirect('/')

def intro(request):
    domains = Domain.objects.all()
    return render_to_response("config/intro.html", {'domains': domains},
                              context_instance=RequestContext(request))

def list(request):
    configs = Config.objects.all()
    return render_to_response("config/list.html", {'configs': configs},
                              context_instance=RequestContext(request))


def details(request, id):
    config = Config.objects.filter(id=int(id))[0]
    other_fields = []
    incoming = []
    outgoing = []
    
    for field in config._meta.fields:
        data = {'name': field.name,
                'verbose_name': field.verbose_name,
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
    return render_to_response("config/details.html", {'config': config,
                                               'incoming': incoming,
                                               'outgoing': outgoing,
                                               'other_fields': other_fields},
                              context_instance=RequestContext(request))


def export_xml(request, id):
    from django.core import serializers
    config = Config.objects.filter(id=int(id))[0]
    data = config.as_xml()
    return HttpResponse(data, mimetype='text/xml')


def add(request, domain):
    DomainFormSet = formset_factory(DomainForm, extra=0, max_num=10)
    InlineFormSet = inlineformset_factory(Config, Domain, can_delete=False)

    if request.method == 'POST': # If the form has been submitted...
        # is this a domain request, or a full configuration?
        data = request.POST
        domains = []
        num_domains = int(data['form-TOTAL_FORMS'][0])
        for i in range(num_domains):
            domains.append(data['form-' + str(i) + '-name'])
        # did the user fill in a full form, or are they just asking for some
        # domains to be registered
        if data['asking_or_adding'] == 'asking':
            # we'll create (unclaimed) domains if they don't exist, otherwise
            # register the vote
            for domain in domains:
                exists = Domain.objects.filter(name=domain) or UnclaimedDomain.objects.filter(name=domain)
                if exists:
                    d = exists[0]
                    d.votes += 1
                else:
                    d = UnclaimedDomain(name=domain, status='requested', votes=1)
                d.save()
            return HttpResponseRedirect('/') # Redirect after POST
        else:
            config = Config()
            config_form = ConfigForm(request.POST, request.FILES, instance=config) # A form bound to the POST data
            if config_form.is_valid(): # All validation rules pass
                config_form.save()
                created_domains = []
                for domain in domains:
                    unclaimed = UnclaimedDomain.objects.filter(name=domain)
                    if unclaimed:
                        d = unclaimed[0]
                        claimed = Domain(name=domain, votes=d.votes, config=config)
                        d.delete()
                    else:
                        claimed = Domain(name=domain, votes=1, config=config)
                    claimed.save()
                return HttpResponseRedirect('/add/') # Redirect after POST
            initials = []
            for domain in domains:
                initials.append({'name': domain})
            formset = DomainFormSet(initial=initials)
    else:
        config_form = ConfigForm()
        formset = DomainFormSet(initial=[{'name': domain}])

    return render_to_response('config/enter_config.html', {
        'formset': formset,
        'config_form': config_form,
    }, context_instance=RequestContext(request))



def queue(request):
    domains = UnclaimedDomain.objects.filter(status='requested').order_by('-votes')
    pending_configs = Config.objects.filter(approved=False, invalid=False)
    invalid_configs = Config.objects.filter(invalid=True)

    return render_to_response('config/queue.html', {
        'domains': domains,
        'pending_configs': pending_configs,
        'invalid_configs': invalid_configs,
    }, context_instance=RequestContext(request))

def policy(request):
    return render_to_response('config/policy.html', {},
                              context_instance=RequestContext(request))

def approve(request, id):
    config = Config.objects.filter(id=id)[0]
    if request.method == 'POST': # If the form has been submitted...
        data = request.POST
        if data.get('approved', False):
            config.approved = True
        elif data.get('denied', False):
            config.invalid = True
            config.approved = False
        else:
            raise ValueError, "shouldn't get here"
        # XXX do something w/ the comment text
        config.save()
    return HttpResponseRedirect('/details/' + id) # Redirect after POST
