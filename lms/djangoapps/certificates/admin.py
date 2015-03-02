from django.contrib import admin

from certificates.models import GeneratedCertificate

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
