from django.contrib import admin
from ispdb.config.models import Config, Domain, DomainRequest


class DomainInline(admin.TabularInline):
    model = Domain
    extra = 0


class DomainRequestInline(admin.TabularInline):
    model = DomainRequest
    extra = 0


class ConfigAdmin(admin.ModelAdmin):
    inlines = [
        DomainRequestInline,
    ]
    radio_fields = {"incoming_type": admin.VERTICAL}
    list_display = ['display_name', 'status', 'list_domains']
    list_filter = ['status']
    search_fields = ['display_name', 'domains__name']

    def change_view(self, request, obj_id):
        c = self.model.objects.get(pk=obj_id)
        if not c.domainrequests.all():
            self.inlines = [DomainInline, ]
        return super(ConfigAdmin, self).change_view(request, obj_id)

    def list_domains(self, obj):
        if obj.domains.all():
            return '<br/>'.join(str(c) for c in obj.domains.all())
        else:
            return '<br/>'.join(str(c) for c in obj.domainrequests.all())
    list_domains.allow_tags = True

admin.site.register(Config, ConfigAdmin)
