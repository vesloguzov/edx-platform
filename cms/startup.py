"""
Module with code executed during Studio startup
"""

from django.conf import settings

# Force settings to run so that the python path is modified
settings.INSTALLED_APPS  # pylint: disable=pointless-statement

from openedx.core.lib.django_startup import autostartup
import django
from monkey_patch import third_party_auth

import xmodule.x_module
import cms.lib.xblock.runtime

import edxmako


def run():
    """
    Executed during django startup
    """
    third_party_auth.patch()

    if settings.FEATURES.get('USE_CUSTOM_STUDIO_THEME', False):
        enable_stanford_theme_translations()

    django.setup()

    if settings.FEATURES.get('USE_CUSTOM_THEME', False):
        enable_lms_theme()

    if settings.FEATURES.get('USE_CUSTOM_STUDIO_THEME', False):
        enable_studio_theme()

    autostartup()

    add_mimetypes()

    # In order to allow descriptors to use a handler url, we need to
    # monkey-patch the x_module library.
    # TODO: Remove this code when Runtimes are no longer created by modulestores
    # https://openedx.atlassian.net/wiki/display/PLAT/Convert+from+Storage-centric+runtimes+to+Application-centric+runtimes
    xmodule.x_module.descriptor_global_handler_url = cms.lib.xblock.runtime.handler_url
    xmodule.x_module.descriptor_global_local_resource_url = cms.lib.xblock.runtime.local_resource_url


def add_mimetypes():
    """
    Add extra mimetypes. Used in xblock_resource.

    If you add a mimetype here, be sure to also add it in lms/startup.py.
    """
    import mimetypes

    mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
    mimetypes.add_type('application/x-font-opentype', '.otf')
    mimetypes.add_type('application/x-font-ttf', '.ttf')
    mimetypes.add_type('application/font-woff', '.woff')


def enable_lms_theme():
    """
    Enable the settings for a custom lms theme, whose files should be stored
    in ENV_ROOT/themes/THEME_NAME (e.g., edx_all/themes/stanford).
    This is actually just a fix for collectstatic,
    (see https://openedx.atlassian.net/browse/TNL-726)
    """
    # Workaround for setting THEME_NAME to an empty
    # string which is the default due to this ansible
    # bug: https://github.com/ansible/ansible/issues/4812
    if settings.THEME_NAME == "":
        settings.THEME_NAME = None
        return

    assert settings.FEATURES['USE_CUSTOM_THEME']
    settings.FAVICON_PATH = 'themes/{name}/images/favicon.ico'.format(
        name=settings.THEME_NAME
    )

    # Calculate the location of the theme's files
    theme_root = settings.ENV_ROOT / "themes" / settings.THEME_NAME

    # Namespace the theme's static files to 'themes/<theme_name>' to
    # avoid collisions with default edX static files
    settings.STATICFILES_DIRS.append(
        (u'themes/{}'.format(settings.THEME_NAME), theme_root / 'static')
    )


def enable_studio_theme():
    """
    Enable the settings for a custom studio theme, whose files should be stored
    in ENV_ROOT/themes/THEME_NAME (e.g., edx_all/themes/stanford).
    """
    # Workaround for setting STUDIO_THEME_NAME to an empty
    # string which is the default due to this ansible
    # bug: https://github.com/ansible/ansible/issues/4812
    if settings.STUDIO_THEME_NAME == "":
        settings.STUDIO_THEME_NAME = None
        return

    assert settings.FEATURES['USE_CUSTOM_STUDIO_THEME']
    settings.FAVICON_PATH = 'themes/{name}/images/favicon.ico'.format(
        name=settings.STUDIO_THEME_NAME
    )

    # Calculate the location of the theme's files
    theme_root = settings.ENV_ROOT / "themes" / settings.STUDIO_THEME_NAME

    # Include the theme's templates in the template search paths
    settings.DEFAULT_TEMPLATE_ENGINE['DIRS'].insert(0, theme_root / 'templates')
    edxmako.paths.add_lookup('main', theme_root / 'templates', prepend=True)

    # Namespace the theme's static files to 'themes/<theme_name>' to
    # avoid collisions with default edX static files
    settings.STATICFILES_DIRS.append(
        (u'themes/{}'.format(settings.STUDIO_THEME_NAME), theme_root / 'static')
    )
    # allow static files overrides
    settings.STATICFILES_DIRS.insert(0, theme_root / 'static-overrides')


def enable_stanford_theme_translations():
    # Calculate the location of the theme's files
    theme_root = settings.ENV_ROOT / "themes" / settings.STUDIO_THEME_NAME

    # Include theme locale path for django translations lookup
    settings.LOCALE_PATHS = (theme_root / 'conf/locale',) + settings.LOCALE_PATHS
