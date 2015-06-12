"""
Test cases for Call Stack Manager
"""
import unittest
from .models import ModelMixin, ModelNothing, ModelMixinCSM, ModelAnotherCSM, ModelWithCSM, ModelWithCSMChild
from django.test import TestCase
from testfixtures import LogCapture
from openedx.core.djangoapps.call_stack_manager import donottrack


class TestingCallStackManager(TestCase):
    """
    Tests for call_stack_manager package
    """
    def test_save(self):
        """ tests save functionality of call stack manager/ applies same for delete()
        1. classes with CallStackMixin should participate in logging.
        """
        with LogCapture() as log_capt:
            ModelMixin(id_field=1).save()
            latest_log = log_capt.records[-1].getMessage()[:log_capt.records[-1].getMessage().find(':')]
            latest_class = latest_log[latest_log.find('<'):]
            desired_class = str(ModelMixin)
            self.assertEqual(latest_class, desired_class)

    def test_withoutmixin_save(self):
        """tests save functionality of call stack manager / applies same for delete()
        1. classes without CallStackMixin should not participate in logging
        """
        with LogCapture() as log_capt:
            ModelAnotherCSM(id_field=1).save()
            self.assertEqual(len(log_capt.records), 0)

    def test_queryset(self):
        """ Tests for Overriding QuerySet API
        1. Tests if classes with CallStackManager gets logged.
        """
        with LogCapture() as log_capt:
            ModelMixinCSM(id_field=1).save()

            ModelMixinCSM.objects.all()

            latest_log = log_capt.records[-1].getMessage()[:log_capt.records[-1].getMessage().find(':')]
            latest_class = latest_log[latest_log.find('<'):]

            # desired latest class here
            desired_class = str(ModelMixinCSM)

            self.assertEqual(latest_class, desired_class)

    def test_withoutqueryset(self):
        """ Tests for Overriding QuerySet API
        1. Tests if classes without CallStackManager does not log
        """
        with LogCapture() as log_capt:
            # create and save objects of class not overriding queryset API
            ModelNothing(id_field=1).save()

            # class not using Manager, should not get logged
            ModelNothing.objects.all()

            self.assertEqual(len(log_capt.records), 0)

    def test_donottrack(self):
        """ Test for @donottrack
        1. calls in decorated function should not get tracked
        """
        with LogCapture() as log_capt:
            donottrack_func()
            self.assertEqual(len(log_capt.records), 0)

    def test_parameterized_donottrack(self):
        """ Test for parameterized @donottrack
        1. Should not log calls of classes specified in the decorator @donotrack
        """
        with LogCapture() as log_capt:
            donottrack_parent_func()

            latest_log = log_capt.records[-1].getMessage()[:log_capt.records[-1].getMessage().find(':')]
            latest_class = latest_log[latest_log.find('<'):]

            # desired latest class here
            desired_class = str(ModelMixinCSM)

            self.assertEqual(latest_class, desired_class)

    def test_nested_parameterized_donottrack(self):
        """ Tests parameterized nested @donottrack
        1. should not track call of classes specified in decorated with scope bounded to the respective class
        """
        with LogCapture() as log_capt:
            #  class with CallStackManager as Manager
            ModelAnotherCSM(id_field=1).save()

            donottrack_parent_func()

            latest_log = log_capt.records[-1].getMessage()[:log_capt.records[-1].getMessage().find(':')]
            latest_class1 = latest_log[latest_log.find('<'):]

            latest_log = log_capt.records[-2].getMessage()[:log_capt.records[-2].getMessage().find(':')]
            latest_class2 = latest_log[latest_log.find('<'):]

            actual_sequence = [latest_class2, latest_class1]
            desired_sequence = [str(ModelAnotherCSM), str(ModelMixinCSM)]
            self.assertEqual(actual_sequence, desired_sequence)

    def test_nested_parameterized_donottrack_after(self):
        """ Tests parameterized nested @donottrack
        1. should not track call of classes specified in decorated with scope bounded to the respective class
        """
        with LogCapture() as log_capt:

            donottrack_child_func()

            #  class with CallStackManager as Manager
            ModelAnotherCSM(id_field=1).save()
            ModelAnotherCSM.objects.filter(id_field=1)

            latest_log = log_capt.records[-1].getMessage()[:log_capt.records[-1].getMessage().find(':')]
            latest_class1 = latest_log[latest_log.find('<'):]

            latest_log = log_capt.records[-2].getMessage()[:log_capt.records[-2].getMessage().find(':')]
            latest_class2 = latest_log[latest_log.find('<'):]

            actual_sequence = [latest_class2, latest_class1]
            desired_sequence = [str(ModelMixinCSM), str(ModelAnotherCSM)]
            self.assertEqual(actual_sequence, desired_sequence)

    def test_donottrack_called_in_func(self):
        """ test for function which calls decorated function.
        """
        with LogCapture() as log_capt:
            ModelAnotherCSM(id_field=1).save()
            ModelMixinCSM(id_field=1).save()

            track_it()

            self.assertEqual(len(log_capt.records), 4)

    def test_donottrack_child_too(self):
        """
        1. subclass should be tracked when superclass is called in a @donottrack decorated function
        """
        with LogCapture() as log_capt:
            ModelWithCSM(id_field=1).save()
            ModelWithCSMChild(id_field=1, id1_field=1).save()

            abstract_do_not_track()

            self.assertEqual(len(log_capt.records), 0)

    def test_dotrack_parent(self):
        """
        1. subclass should be tracked when superclass is called in a @donottrack decorated function
        """
        with LogCapture() as log_capt:
            ModelWithCSM(id_field=1).save()
            ModelWithCSMChild(id_field=1, id1_field=1).save()

            abstract_do_track()

            latest_log = log_capt.records[-1].getMessage()[:log_capt.records[-1].getMessage().find(':')]
            latest_class = latest_log[latest_log.find('<'):]

            # desired latest class here
            desired_class = str(ModelWithCSM)

            self.assertEqual(latest_class, desired_class)


@donottrack(ModelWithCSMChild)
def abstract_do_track():
    """ Function for inheritence
    """
    ModelWithCSM.objects.filter(id_field=1)
    ModelWithCSMChild.objects.filter(id1_field=1)


@donottrack(ModelWithCSM)
def abstract_do_not_track():
    """ Function for inheritence
    """
    ModelWithCSM.objects.filter(id_field=1)
    ModelWithCSMChild.objects.filter(id1_field=1)


def track_it():
    """ Function for inheritence
    """
    ModelAnotherCSM.objects.filter(id_field=1)
    donottrack_child_func()
    ModelAnotherCSM.objects.filter(id_field=1)


@donottrack(ModelAnotherCSM)
def donottrack_child_func():
    """ Function for decorator @donottrack
    """
    # should not be tracked
    ModelAnotherCSM.objects.filter(id_field=1)

    # should be tracked
    ModelMixinCSM.objects.filter(id_field=1)


@donottrack(ModelMixinCSM)
def donottrack_parent_func():
    """ Function for decorator @donottrack
    """
    # should not  be tracked
    ModelMixinCSM.objects.filter(id_field=1)

    # should be tracked
    ModelAnotherCSM.objects.filter(id_field=1)

    donottrack_child_func()


@donottrack()
def donottrack_func():
    """ Function for decorator @donottrack
    """
    ModelMixin.objects.all()
    donottrack_func_child()
    ModelMixin.objects.filter(id_field=1)


@donottrack()
def donottrack_func_child():
    """ Function for decorator @donottrack
    """
    # Should not be tracked
    ModelMixin.objects.all()
