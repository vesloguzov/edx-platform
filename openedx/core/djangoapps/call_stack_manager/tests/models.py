"""
The file defines Model classes required for testing call_stack_manager.py
"""
from django.db import models
from openedx.core.djangoapps.call_stack_manager import CallStackManager, CallStackMixin


class Rohan(CallStackMixin, models.Model):
    """
    Test Model class which uses both CallStackManager, and CallStackMixin
    """
    # override Manager objects
    objects = CallStackManager()

    id_field = models.IntegerField()
    string_field = models.TextField()


class Gondor(CallStackMixin, models.Model):
    """
    Test Model that uses CallStackMixin but does not use CallStackManager
    """
    id_field = models.IntegerField()
    text_field = models.CharField(max_length=10)
    float_field = models.FloatField()


class Mordor(models.Model):
    """
    Test Model class that neither uses CallStackMixin nor CallStackManager
    """
    id_field = models.IntegerField()
    name_field = models.CharField(max_length=20)


class Shire(models.Model):
    """
    Test Model class that only uses overridden Manager CallStackManager
    """
    objects = CallStackManager()
    id_field = models.IntegerField()
    name_field = models.CharField(max_length= 20)


