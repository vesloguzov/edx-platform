""" receivers of course_published and library_updated events in order to trigger indexing task """
from datetime import datetime
from pytz import UTC

from django.dispatch import receiver, Signal

from xmodule.modulestore.django import SignalHandler
from contentstore.courseware_index import CoursewareSearchIndexer, LibrarySearchIndexer

import course_owners.models


@receiver(SignalHandler.course_published)
def listen_for_course_publish(sender, course_key, **kwargs):  # pylint: disable=unused-argument
    """
    Receives signal and kicks off celery task to update search index
    """
    # import here, because signal is registered at startup, but items in tasks are not yet able to be loaded
    from .tasks import update_search_index
    if CoursewareSearchIndexer.indexing_is_enabled():
        update_search_index.delay(unicode(course_key), datetime.now(UTC).isoformat())


@receiver(SignalHandler.library_updated)
def listen_for_library_update(sender, library_key, **kwargs):  # pylint: disable=unused-argument
    """
    Receives signal and kicks off celery task to update search index
    """
    # import here, because signal is registered at startup, but items in tasks are not yet able to be loaded
    from .tasks import update_library_index
    if LibrarySearchIndexer.indexing_is_enabled():
        update_library_index.delay(unicode(library_key), datetime.now(UTC).isoformat())


COURSE_CREATED = Signal(providing_args=['course_id', 'user'])
COURSE_RERUN_CREATED = Signal(providing_args=['src_course', 'dst_course', 'user'])

COURSE_CREATED.connect(course_owners.models.create_new_course_ownership)
COURSE_RERUN_CREATED.connect(course_owners.models.create_rerun_ownership)
