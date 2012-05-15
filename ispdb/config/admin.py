from ispdb.config.models import Config, Domain, UnclaimedDomain
from django.contrib import admin

class DomainInline(admin.TabularInline):
    model = Domain

class UnclaimedDomainAdmin(admin.ModelAdmin):
    model = UnclaimedDomain


class ConfigAdmin(admin.ModelAdmin):
    inlines = [
        DomainInline,
    ]
    radio_fields = {"incoming_type": admin.VERTICAL}

#admin.site.register(Config, ConfigAdmin)
#admin.site.register(UnclaimedDomain, UnclaimedDomainAdmin)

