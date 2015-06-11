"""
Test cases for Call Stack Manager
"""
from .models import ModelMixin, ModelNothing, ModelMixinCSM, ModelAnotherCSM
from django.test import TestCase
from testfixtures import LogCapture
from openedx.core.djangoapps.call_stack_manager import donottrack


class TestingCallStackManager(TestCase):
    """
    Tests for call_stack_manager package
    """
    def setUp(self):
        super(TestingCallStackManager, self).setUp()

    def tearDown(self):
        """ Deleting all databases after tests
        """
        super(TestingCallStackManager, self).setUp()
        ModelMixin.objects.all().delete()
        ModelMixinCSM.objects.all().delete()
        ModelNothing.objects.all().delete()
        ModelAnotherCSM.objects.all().delete()

    def test_save(self):
        """ tests save functionality of call stack manager
        1. classes without CallStackMixin should not participate in logging.
        """
        with LogCapture() as l:
            ModelMixin_obj1 = ModelMixin(id_field=1, text_field="ModelMixin1", float_field=12.34)
            ModelMixin_obj1.save()

            ModelNothing_obj1 = ModelNothing(id_field=1, name_field="Sauron")
            ModelNothing_obj1.save()

            # Example - logging new call stack for openedx.core.djangoapps.call_stack_manager.tests.models.ModelMixin
            latest_log = l.records[-1].getMessage()[:l.records[-1].getMessage().find(':')]
            latest_class = latest_log[latest_log.rfind('.') + 1:]

            # desired latest class here
            desired_class = "ModelMixin"

            self.assertEqual(latest_class, desired_class, msg="Latest logged event should belong to " + desired_class)

    def test_queryset(self):
        """ Tests for Overriding QuerySet API
        1. Tests if classes with CallStackManager gets logged.
        """
        with LogCapture() as l:
            # create and save objects of class not overriding queryset API
            ModelMixin_obj3 = ModelMixin(id_field=1, float_field=12.89)
            ModelMixin_obj4 = ModelMixin(id_field=1, float_field=23.56)
            ModelMixin_obj3.save()
            ModelMixin_obj4.save()

            ModelMixinCSM_obj1 = ModelMixinCSM(id_field=1, string_field="Thou shall not pass")
            ModelMixinCSM_obj2 = ModelMixinCSM(id_field=1, string_field="Not all those who wonder are lost")
            ModelMixinCSM_obj1.save()
            ModelMixinCSM_obj2.save()

            ModelMixinCSM.objects.all()

            # class not using Manager, should not get logged
            ModelMixin.objects.all()

            # Example - logging new call stack for openedx.core.djangoapps.call_stack_manager.tests.models.ModelMixin
            latest_log = l.records[-1].getMessage()[:l.records[-1].getMessage().find(':')]
            latest_class = latest_log[latest_log.rfind('.') + 1:]

            # desired latest class here
            desired_class = "ModelMixinCSM"

            self.assertEqual(latest_class, desired_class, msg="Latest logged event should belong to " + desired_class)

    def test_donottrack(self):
        """ Test for @donottrack
        1. calls in decorated function should not get tracked
        """
        with LogCapture() as l:
            donottrack_func()
            self.assertEqual(len(l.records), 0, msg="Check @donottrack. should not log anything here!")

    def test_parameterized_donottrack(self):
        """ Test for parameterized @donottrack
        1. Should not log calls of classes specified in the decorator @donotrack
        """
        with LogCapture() as l:
            donottrack_parent_func()

            # Example - logging new call stack for openedx.core.djangoapps.call_stack_manager.tests.models.ModelMixin
            latest_log = l.records[-1].getMessage()[:l.records[-1].getMessage().find(':')]
            latest_class = latest_log[latest_log.rfind('.') + 1:]

            # desired latest class here
            desired_class = "ModelMixinCSM"

            self.assertEqual(latest_class, desired_class,
                             msg="The latest log should be of the class" + desired_class + "not" + latest_class)

    def test_nested_parameterized_donottrack(self):
        """ Tests parameterized nested @donottrack
        1. should not track call of classes specified in decorated with scope bounded to the respective class
        """
        with LogCapture() as l:
            #  class with CallStackManager as Manager
            ModelAnotherCSM_obj = ModelAnotherCSM(id_field=1, name_field="The Crownless again shall be king")
            ModelAnotherCSM_obj.save()

            donottrack_parent_func()

            # Example - logging new call stack for openedx.core.djangoapps.call_stack_manager.tests.models.ModelMixin
            latest_log = l.records[-1].getMessage()[:l.records[-1].getMessage().find(':')]
            latest_class1 = latest_log[latest_log.rfind('.') + 1:]

            latest_log = l.records[-2].getMessage()[:l.records[-2].getMessage().find(':')]
            latest_class2 = latest_log[latest_log.rfind('.') + 1:]

            actual_sequence = [latest_class2, latest_class1]
            desired_sequence = ["ModelAnotherCSM", "ModelMixinCSM"]
            self.assertEqual(actual_sequence, desired_sequence, msg=str(l))


@donottrack('ModelAnotherCSM')
def donottrack_child_func():
    """ Function for decorator @donottrack
    """
    # should not be tracked
    ModelAnotherCSM.objects.filter(id_field=1)

    # should be tracked
    ModelMixinCSM.objects.filter(id_field=1)


@donottrack('ModelMixinCSM')
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
