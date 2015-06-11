"""
The file defines Model classes required for testing call_stack_manager.py
"""
from django.db import models
from openedx.core.djangoapps.call_stack_manager import CallStackManager, CallStackMixin


class ModelMixinCSM(CallStackMixin, models.Model):
    """
    Test Model class which uses both CallStackManager, and CallStackMixin
    """
    # override Manager objects
    objects = CallStackManager()

    id_field = models.IntegerField()


class ModelMixin(CallStackMixin, models.Model):
    """
    Test Model that uses CallStackMixin but does not use CallStackManager
    """
    id_field = models.IntegerField()


class ModelNothing(models.Model):
    """
    Test Model class that neither uses CallStackMixin nor CallStackManager
    """
    id_field = models.IntegerField()


class ModelAnotherCSM(models.Model):
    """
    Test Model class that only uses overridden Manager CallStackManager
    """
    objects = CallStackManager()
    id_field = models.IntegerField()


class ModelWithCSM(models.Model):
    """
    Test Model Classes
    """
    objects = CallStackManager()
    id_field = models.IntegerField()


class ModelWithCSMChild(ModelWithCSM):
    """child class of ModelWithCSM

    """
    objects = CallStackManager()
    id1_field = models.IntegerField()
