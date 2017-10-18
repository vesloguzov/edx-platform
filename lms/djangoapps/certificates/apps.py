"""
Certificates Application Configuration

Signal handlers are connected here.
"""

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CertificatesConfig(AppConfig):
    """
    Application Configuration for Certificates.
    """
    name = u'certificates'
    verbose_name = _("Certificates")

    def ready(self):
        """
        Connect handlers to signals.
        """
        # Can't import models at module level in AppConfigs, and models get
        # included from the signal handlers
        from . import signals  # pylint: disable=unused-variable
