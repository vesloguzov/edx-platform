"""
Test cases for Call Stack Manager
"""
from .models import Gondor, Mordor, Rohan, Shire
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
        Gondor.objects.all().delete()
        Rohan.objects.all().delete()
        Mordor.objects.all().delete()
        Shire.objects.all().delete()

    def test_save(self):
        """ tests save functionality of call stack manager
        1. classes without CallStackMixin should not participate in logging.
        """
        with LogCapture() as l:
            gondor_obj1 = Gondor(id_field=1, text_field="Gondor1", float_field=12.34)
            gondor_obj1.save()

            mordor_obj1 = Mordor(id_field=1, name_field="Sauron")
            mordor_obj1.save()

            # Example - logging new call stack for openedx.core.djangoapps.call_stack_manager.tests.models.Gondor
            latest_log = l.records[-1].getMessage()[:l.records[-1].getMessage().find(':')]
            latest_class = latest_log[latest_log.rfind('.') + 1:]

            # desired latest class here
            desired_class = "Gondor"

            self.assertEqual(latest_class, desired_class, msg="Latest logged event should belong to " + desired_class)

    def test_queryset(self):
        """ Tests for Overriding QuerySet API
        1. Tests if classes with CallStackManager gets logged.
        """
        with LogCapture() as l:
            # create and save objects of class not overriding queryset API
            gondor_obj3 = Gondor(id_field=1, float_field=12.89)
            gondor_obj4 = Gondor(id_field=1, float_field=23.56)
            gondor_obj3.save()
            gondor_obj4.save()

            rohan_obj1 = Rohan(id_field=1, string_field="Thou shall not pass")
            rohan_obj2 = Rohan(id_field=1, string_field="Not all those who wonder are lost")
            rohan_obj1.save()
            rohan_obj2.save()

            Rohan.objects.all()

            # class not using Manager, should not get logged
            Gondor.objects.all()

            # Example - logging new call stack for openedx.core.djangoapps.call_stack_manager.tests.models.Gondor
            latest_log = l.records[-1].getMessage()[:l.records[-1].getMessage().find(':')]
            latest_class = latest_log[latest_log.rfind('.') + 1:]

            # desired latest class here
            desired_class = "Rohan"

            self.assertEqual(latest_class, desired_class, msg="Latest logged event should belong to " + desired_class)

    def test_donottrack(self):
        """ Test for @donottrack
        1. calls in decorated function should not get tracked
        """
        with LogCapture() as l:
            bombadil()
            self.assertEqual(len(l.records), 0, msg="Check @donottrack. should not log anything here!")

    def test_parameterized_donottrack(self):
        """ Test for parameterized @donottrack
        1. Should not log calls of classes specified in the decorator @donotrack
        """
        with LogCapture() as l:
            faramir()

            # Example - logging new call stack for openedx.core.djangoapps.call_stack_manager.tests.models.Gondor
            latest_log = l.records[-1].getMessage()[:l.records[-1].getMessage().find(':')]
            latest_class = latest_log[latest_log.rfind('.') + 1:]

            # desired latest class here
            desired_class = "Rohan"

            self.assertEqual(latest_class, desired_class,
                             msg="The latest log should be of the class" + desired_class + "not" + latest_class)

    def test_nested_parameterized_donottrack(self):
        """ Tests parameterized nested @donottrack
        1. should not track call of classes specified in decorated with scope bounded to the respective class
        """
        with LogCapture() as l:
            #  class with CallStackManager as Manager
            shire_obj = Shire(id_field=1, name_field="The Crownless again shall be king")
            shire_obj.save()

            faramir()

            # Example - logging new call stack for openedx.core.djangoapps.call_stack_manager.tests.models.Gondor
            latest_log = l.records[-1].getMessage()[:l.records[-1].getMessage().find(':')]
            latest_class1 = latest_log[latest_log.rfind('.') + 1:]

            latest_log = l.records[-2].getMessage()[:l.records[-2].getMessage().find(':')]
            latest_class2 = latest_log[latest_log.rfind('.') + 1:]

            actual_sequence = [latest_class2, latest_class1]
            desired_sequence = ["Shire", "Rohan"]
            self.assertEqual(actual_sequence, desired_sequence, msg=str(l))


@donottrack('Shire')
def denethor():
    """ Function for decorator @donottrack
    """
    # should not be tracked
    Shire.objects.filter(id_field=1)

    # should be tracked
    Rohan.objects.filter(id_field=1)


@donottrack('Rohan')
def faramir():
    """ Function for decorator @donottrack
    """
    # should not  be tracked
    Rohan.objects.filter(id_field=1)

    # should be tracked
    Shire.objects.filter(id_field=1)

    denethor()


@donottrack()
def bombadil():
    """ Function for decorator @donottrack
    """
    Gondor.objects.all()
    child_bombadil()
    Gondor.objects.filter(id_field=1)


@donottrack()
def child_bombadil():
    """ Function for decorator @donottrack
    """
    # Should not be tracked
    Gondor.objects.all()
