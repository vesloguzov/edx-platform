"""
django admin pages for certificates models
"""
from config_models.admin import ConfigurationModelAdmin
from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from certificates.models import (
    CertificateGenerationConfiguration,
    CertificateGenerationCourseSetting,
    CertificateHtmlViewConfiguration,
    CertificateTemplate,
    CertificateTemplateAsset,
    GeneratedCertificate
)
from util.organizations_helpers import get_organizations


class CertificateTemplateForm(forms.ModelForm):
    """
    Django admin form for CertificateTemplate model
    """
    def __init__(self, *args, **kwargs):
        super(CertificateTemplateForm, self).__init__(*args, **kwargs)
        organizations = get_organizations()
        org_choices = [(org["id"], org["name"]) for org in organizations]
        org_choices.insert(0, ('', _('None')))
        self.fields['organization_id'] = forms.TypedChoiceField(
            choices=org_choices, required=False, coerce=int, empty_value=None,
            label=CertificateTemplate._meta.get_field('organization_id').verbose_name.capitalize(),
            help_text=CertificateTemplate._meta.get_field('organization_id').help_text
        )

    class Meta(object):
        model = CertificateTemplate
        fields = '__all__'


class CertificateTemplateAdmin(admin.ModelAdmin):
    """
    Django admin customizations for CertificateTemplate model
    """
    list_display = ('name', 'description', 'organization', 'course_key', 'mode', 'is_active')
    form = CertificateTemplateForm

    def organization(self, obj):
        return self.organizations_dict.get(obj.organization_id) or obj.organization_id

    @property
    def organizations_dict(self):
        if not hasattr(self, '_organizations_dict'):
            self._organizations_dict = {org['id']: org['name'] for org in get_organizations()}
        return self._organizations_dict

    organization.short_description = _('Organization')


class CertificateTemplateAssetAdmin(admin.ModelAdmin):
    """
    Django admin customizations for CertificateTemplateAsset model
    """
    list_display = ('description', 'asset_slug',)
    prepopulated_fields = {"asset_slug": ("description",)}


class GeneratedCertificateAdmin(admin.ModelAdmin):
    """
    Django admin customizations for GeneratedCertificate model
    """
    raw_id_fields = ('user',)
    show_full_result_count = False
    search_fields = ('course_id', 'user__username', 'user__email')
    list_select_related = ('user',)
    list_display = ('id', 'username', 'email', 'course_id', 'mode', 'download_url',)

    def username(self, obj):
        return obj.user.username
    username.short_description = _('Username')

    def email(self, obj):
        return obj.user.email
    email.short_description = _('Email')

class CertificateGenerationCourseSettingAdmin(admin.ModelAdmin):
    """
    Django admin customizations for CertificateGenerationCourseSetting model
    """
    list_display = ('course_key',)
    readonly_fields = ('course_key',)
    search_fields = ('course_key',)
    show_full_result_count = False


admin.site.register(CertificateGenerationConfiguration)
admin.site.register(CertificateGenerationCourseSetting, CertificateGenerationCourseSettingAdmin)
admin.site.register(CertificateHtmlViewConfiguration, ConfigurationModelAdmin)
admin.site.register(CertificateTemplate, CertificateTemplateAdmin)
admin.site.register(CertificateTemplateAsset, CertificateTemplateAssetAdmin)
admin.site.register(GeneratedCertificate, GeneratedCertificateAdmin)
