"""Simple utility functions that operate on course metadata.

Ths is a place to put simple functions that operate on course metadata. It
allows us to share code between the CourseDescriptor and CourseOverview
classes, which both need these type of functions.
"""

from datetime import datetime
from base64 import b32encode

from django.utils.timezone import UTC

from .fields import Date

DEFAULT_START_DATE = datetime(2030, 1, 1, tzinfo=UTC())

def clean_id(location, padding_char):
    """Returns a unique deterministic base32-encoded ID for a course.

    Args:
        location (UsageKey): The UsageKey of said course
        padding_char (str): Character used for padding at end of the encoded string.
                            The standard value for this is '='.
    """
    return "course_{}".format(
        b32encode(unicode(location.course_key)).replace('=', padding_char)
    )

def display_name_with_default(display_name, location):
    """Calculate the display name for a course.

    Default to the given display_name if it isn't None, else fall back to creating
    a name based on the URL (location.name)

    Args:
        display_name (str): Display name of said course
        location (UsageKey): Usage key of said course
    """
    return (display_name if display_name is not None else location.name.replace('_', ' ')) \
        .replace('<', '&lt;') \
        .replace('>', '&gt;')

def _add_timezone_string(date_time):
    """
    Adds 'UTC' string to the end of start/end date and time texts.
    """
    return date_time + u" UTC"

def start_date_is_still_default(start, advertised_start):
    """
    Checks if the start date set for a course is still default, i.e. .start has not been modified,
    and .advertised_start has not been set.
    """
    return advertised_start is None and start == DEFAULT_START_DATE

def start_datetime_text(start, advertised_start, format_string, ugettext, strftime):
    """
    Returns the desired text corresponding the course's start date and time in UTC.  Prefers .advertised_start,
    then falls back to .start.

    Args:
        start (datetime): the start date of a course
        advertised_start (str): the advertised start date of a course, as a string
        format_string (str): the date format type, as passed to strftime
        ugettext (str -> str): a text localization function
        strftime (datetime, str -> str): a localized string formatting function
    """
    if isinstance(advertised_start, basestring):
        try:
            date_to_display = Date().from_json(advertised_start)
        except ValueError:
            date_to_display = None
    elif not start_date_is_still_default(start, advertised_start):
        date_to_display = advertised_start or start
    else:
        # Translators: TBD stands for 'To Be Determined' and is used when a course
        # does not yet have an announced start date.
        _ = ugettext
        return _('TBD')

    if date_to_display:
        result = strftime(date_to_display, format_string)
        return _add_timezone_string(result) if format_string == "DATE_TIME" \
            else result
    else:
        return advertised_start.title()


def end_datetime_text(end, format_string, strftime_localized):
    """Returns a formatted string for a course's end date or date_time .
    If end is none, an empty string will be returned.

    Args:
        start (datetime): the start date of a course
        advertised_start (str): the advertised start date of a course, as a string
        format_string (str): the date format type, as passed to strftime
        ugettext (str -> str): a text localization function
        strftime_localized (datetime, str -> str): a localized string formatting function

    """
    if end is None:
        return ''
    else:
        formatted_date = strftime_localized(end, format_string)
        return formatted_date if format_string == "SHORT_DATE" else _add_timezone_string(formatted_date)

def may_certify(certificates_display_behavior, certificates_show_before_end, has_ended):
    """
    Returns whether it is acceptable to show the student a certificate download link for a course.
    """
    show_early = certificates_display_behavior in ('early_with_info', 'early_no_info') \
        or certificates_show_before_end
    return show_early or has_ended
