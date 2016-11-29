import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms.envs.aws')
os.environ.setdefault('SERVICE_VARIANT', 'lms')

import lms.startup
lms.startup.run()

from django.contrib.auth.models import User
from xmodule.modulestore.django import modulestore
from django.db.models.loading import get_models
get_models()
