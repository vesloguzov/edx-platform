from rest_framework import routers

class Router(routers.DefaultRouter):
    def get_lookup_regex(self, viewset, lookup_prefix=''):
        """
        Router reading custom lookup url patterns from viewsets
        """
        if getattr(viewset, 'lookup_regex', False):
            return viewset.lookup_regex
        else:
            return super(Router, self).get_lookup_regex(viewset, lookup_prefix)
