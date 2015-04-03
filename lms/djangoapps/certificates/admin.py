"""
django admin pages for certificates models
"""
from django.contrib import admin

from config_models.admin import ConfigurationModelAdmin
from certificates.models import GeneratedCertificate, CertificateGenerationConfiguration, CertificateHtmlViewConfiguration


class GeneratedCertificateAdmin(admin.ModelAdmin):
    list_select_related = True
    list_display = (
        'username',
        'email',
        'course_id',
        'download_url',
    )
    search_fields = (
        'user__username',
        'user__email',
        'course_id',
    )

    def username(self, obj):
        return obj.user.username

    def email(self, obj):
        return obj.user.email

admin.site.register(GeneratedCertificate, GeneratedCertificateAdmin)
admin.site.register(CertificateGenerationConfiguration)
admin.site.register(CertificateHtmlViewConfiguration, ConfigurationModelAdmin)
