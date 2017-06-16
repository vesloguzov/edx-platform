"""
Url configuration for the static tempates, used only for service variant configured for marketing links.
"""

from django.conf import settings
from django.conf.urls import patterns, url

urlpatterns = patterns('',)

_use_theme_templates = (
    settings.SERVICE_VARIANT == 'lms' and settings.FEATURES.get("USE_CUSTOM_THEME", False)
    or settings.SERVICE_VARIANT == 'cms' and settings.FEATURES.get("USE_CUSTOM_STUDIO_THEME", False)
)
# Only enable URLs for those marketing links actually enabled in the
# settings. Disable URLs by marking them as None.
for key, value in settings.MKTG_URL_LINK_MAP.items():
    # Skip disabled URLs
    if value is None:
        continue

    # These urls are enabled separately
    if key == "ROOT" or key == "COURSES":
        continue

    # Make the assumptions that the templates are all in the same dir
    # and that they all match the name of the key (plus extension)
    template = "%s.html" % key.lower()

    # To allow theme templates to inherit from default templates,
    # prepend a standard prefix
    if _use_theme_templates:
        template = "theme-" + template

    # Make the assumption that the URL we want is the lowercased
    # version of the map key
    urlpatterns += (url(r'^%s$' % key.lower(),
                        'static_template_view.views.render',
                        {'template': template}, name=value),)
