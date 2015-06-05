"""
Get call stacks of Model Class
in three cases-
1. QuerySet API
2. save()
3. delete()

classes:
CallStackManager -  stores all stacks in global dictionary and logs
CallStackMixin - used for Model save(), and delete() method

Functions:
capture_call_stack - global function used to store call stack

Decorators:
donottrack - mainly for the places where we know the calls. This decorator will let us not to track in specified cases

How to use-
1. Import following in the file where class to be tracked resides
    from openedx.core.lib.call_stack_manager import CallStackManager, CallStackMixin
2. Override objects of default manager by writing following in any model class which you want to track-
    objects = CallStackManager()
3. For tracking Save and Delete events-
    Use mixin called "CallStackMixin"
    For ex.
        class StudentModule(CallStackMixin, models.Model):

Note -
1.Format for STACK_BOOK
{
    "modelclass1":
        [[(frame 1),(frame 2)],
         [(frame 11),(frame21)]]
    "modelclass2":
        [[(frame 3),(frame 4)],
         [(frame 6),(frame 5)]]

}
where frame is a tuple of
(file path, Line Number, Context)
"""

import logging
import traceback
import re
import collections
from django.db.models import Manager

log = logging.getLogger(__name__)

# Module Level variables
# dictionary which stores call stacks.
# { "ModelClasses" : [ListOfFrames]}
# Frames - ('FilePath','LineNumber','Context')
# ex. {"<class 'courseware.models.StudentModule'>" : [[(file,line number,context),(---,---,---)],
#                                                     [(file,line number,context),(---,---,---)]]}
STACK_BOOK = collections.defaultdict(list)

# filter to trickle down call stacks
EXCLUDE = ['^.*python2.7.*$', '^.*call_stack_manager.*$', '^.*<exec_function>.*$', '^.*exec_code_object.*$']
REGULAR_EXPS = [re.compile(x) for x in EXCLUDE]

# Variable which decides whether to track calls in the function or not. Do it by default.
TRACK_FLAG = True

# List keeping track of Model classes not be tracked for special cases
# usually cases where we know that the function is calling Model classes.
HALT_TRACKING = []


def capture_call_stack(current_model):
    """ logs customised call stacks in global dictionary `STACK_BOOK`, and logs it.

    Args:
        current_model - Name of the model class
    """

    # holds temporary callstack
    # frame[0][6:-1] -> File name along with path
    # frame[1][6:] -> Line Number
    # frame[2][3:] -> Context
    temp_call_stack = [(frame[0][6:-1],
                        frame[1][6:],
                        frame[2][3:])
                       for frame in [stack.replace("\n", "").strip().split(',') for stack in traceback.format_stack()]
                       if not any(reg.match(frame[0]) for reg in REGULAR_EXPS)]

    # avoid duplication.
    if temp_call_stack not in STACK_BOOK[current_model] \
            and TRACK_FLAG and not any(current_model[current_model.rfind(".") + 1:] == cls for cls in HALT_TRACKING):
        STACK_BOOK[current_model].append(temp_call_stack)
        log.info("logging new call stack for %s:\n %s", current_model, temp_call_stack)


class CallStackMixin(object):
    """
    A mixin class for getting call stacks when Save() and Delete() methods are called
    """

    def save(self, *args, **kwargs):
        """
        Logs before save and overrides respective model API save()
        """
        capture_call_stack(str(type(self))[str(type(self)).find('\'') + 1: str(type(self)).rfind('\'')])
        return super(CallStackMixin, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Logs before delete and overrides respective model API delete()
        """
        capture_call_stack(str(type(self))[str(type(self)).find('\'') + 1: str(type(self)).rfind('\'')])
        return super(CallStackMixin, self).delete(*args, **kwargs)


class CallStackManager(Manager):
    """
    gets call stacks of model classes
    """
    def get_query_set(self):
        """
        overriding the default queryset API methods

        """
        capture_call_stack(str(self.model)[str(self.model).find('\'') + 1: str(self.model).rfind('\'')])
        return super(CallStackManager, self).get_query_set()


def donottrack(*classes_not_to_be_tracked):
    """function decorator which deals with toggling call stack
    How to use -
    1. Just Import following
        import from openedx.core.lib.call_stack_manager import donottrack
    Args:
        *classes_not_to_be_tracked: model classes where tracking is undesirable
    Returns:
        wrapped function
    """
    donottrack.depth = 0

    def real_donottrack(function):
        """takes function to be decorated and returns wrapped function

        Args:
            function - wrapped function i.e. real_donottrack
        """
        def wrapper(*args, **kwargs):
            """ wrapper function for decorated function
            Returns:
                wrapper function i.e. wrapper
            """
            if len(classes_not_to_be_tracked) == 0:
                global TRACK_FLAG  # pylint: disable=W0603
                if donottrack.depth == 0:
                    TRACK_FLAG = False
                donottrack.depth += 1
                function(*args, **kwargs)
                donottrack.depth -= 1
                if donottrack.depth == 0:
                    TRACK_FLAG = False
            else:
                global HALT_TRACKING  # pylint: disable=W0603
                if donottrack.depth == 0:
                    HALT_TRACKING = list(classes_not_to_be_tracked)
                donottrack.depth += 1
                function(*args, **kwargs)
                donottrack.depth -= 1
                if donottrack.depth == 0:
                    HALT_TRACKING[:] = []
        return wrapper
    return real_donottrack

