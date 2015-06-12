"""
Test cases for Call Stack Manager
"""
from mock import patch
from .models import ModelMixin, ModelNothing, ModelMixinCSM, ModelAnotherCSM, ModelWithCSM, ModelWithCSMChild
from django.test import TestCase
from openedx.core.djangoapps.call_stack_manager import donottrack


class TestingCallStackManager(TestCase):
    """
    Tests for call_stack_manager package
    """
    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_save(self, log_capt):
        """ tests save functionality of call stack manager/ applies same for delete()
        1. classes with CallStackMixin should participate in logging.
        """
        ModelMixin(id_field=1).save()
        self.assertEqual(ModelMixin, log_capt.call_args[0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_withoutmixin_save(self, log_capt):
        """tests save functionality of call stack manager / applies same for delete()
        1. classes without CallStackMixin should not participate in logging
        """
        ModelAnotherCSM(id_field=1).save()
        self.assertEqual(len(log_capt.call_args_list), 0)

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_queryset(self, log_capt):
        """ Tests for Overriding QuerySet API
        1. Classes with CallStackManager gets logged.
        """
        ModelMixinCSM(id_field=1).save()
        ModelMixinCSM.objects.all()
        self.assertEqual(ModelMixinCSM, log_capt.call_args[0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_withoutqueryset(self, log_capt):
        """ Tests for Overriding QuerySet API
        1. Classes without CallStackManager does not log
        """
        # create and save objects of class not overriding queryset API
        ModelNothing(id_field=1).save()
        # class not using Manager, should not get logged
        ModelNothing.objects.all()
        self.assertEqual(len(log_capt.call_args_list), 0)

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_donottrack(self, log_capt):
        """ Test for @donottrack
        1. calls in decorated function should not get tracked
        """
        donottrack_func()
        self.assertEqual(len(log_capt.call_args_list), 0)

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_parameterized_donottrack(self, log_capt):
        """ Test for parameterized @donottrack
        1. Should not log calls of classes specified in the decorator @donotrack
        """
        donottrack_child_func()
        self.assertEqual(ModelMixinCSM, log_capt.call_args[0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_nested_parameterized_donottrack(self, log_capt):
        """ Tests parameterized nested @donottrack
        1. should not track call of classes specified in decorated with scope bounded to the respective class
        """
        ModelAnotherCSM(id_field=1).save()
        donottrack_parent_func()
        self.assertEqual(ModelAnotherCSM, log_capt.call_args_list[0][0][1])
        self.assertEqual(ModelMixinCSM, log_capt.call_args_list[1][0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_nested_parameterized_donottrack_after(self, log_capt):
        """ Tests parameterized nested @donottrack
        1. should not track call of classes specified in decorated with scope bounded to the respective function
        """
        donottrack_child_func()
        # class with CallStackManager as Manager
        ModelAnotherCSM(id_field=1).save()
        # test is this- that this should get called.
        ModelAnotherCSM.objects.filter(id_field=1)
        self.assertEqual(ModelMixinCSM, log_capt.call_args_list[0][0][1])
        self.assertEqual(ModelAnotherCSM, log_capt.call_args_list[1][0][1])

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_donottrack_called_in_func(self, log_capt):
        """ test for function which calls decorated function.
        """
        ModelAnotherCSM(id_field=1).save()
        ModelMixinCSM(id_field=1).save()
        track_it()
        self.assertEqual(ModelMixinCSM, log_capt.call_args_list[0][0][1])
        self.assertEqual(ModelAnotherCSM, log_capt.call_args_list[1][0][1] )
        self.assertEqual(ModelMixinCSM, log_capt.call_args_list[2][0][1])
        self.assertEqual(ModelAnotherCSM, log_capt.call_args_list[3][0][1] )


    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_donottrack_child_too(self, log_capt):
        """
        1. subclass should not be tracked when superclass is called in a @donottrack decorated function
        """
        ModelWithCSM(id_field=1).save()
        ModelWithCSMChild(id_field=1, id1_field=1).save()
        abstract_do_not_track()
        self.assertEqual(len(log_capt.call_args_list), 0)

    @patch('openedx.core.djangoapps.call_stack_manager.core.log.info')
    def test_duplication(self, log_capt):
        """ Test for duplication of call stacks
        1. no duplication of call stacks
        """
        for dummy in range(1, 5):
            ModelMixinCSM(id_field=1).save()
        self.assertEqual(len(log_capt.call_args_list), 1)


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
