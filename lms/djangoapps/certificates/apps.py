from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CertificatesConfig(AppConfig):
    name = 'certificates'
    verbose_name = _("Certificates")
