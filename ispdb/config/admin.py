from ispdb.config.models import Config, Domain
from django.contrib import admin

class DomainInline(admin.TabularInline):
    model = Domain

class ConfigAdmin(admin.ModelAdmin):
    inlines = [
        DomainInline,
    ]
    radio_fields = {"incoming_type": admin.VERTICAL}

#admin.site.register(Config, ConfigAdmin)
