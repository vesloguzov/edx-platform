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


class NestedRouter(Router):
    """
    Nested router for urls like parents/<parent_id>/children/[<child_id>/]

    Gets parent_router as a first argument to __init__
    """
    # Copied from drf-nested-router, but inheritance is changed since initial version uses outdated parent
    def __init__(self, parent_router, parent_prefix, *args, **kwargs):
        self.parent_router = parent_router
        self.parent_prefix = parent_prefix
        self.nest_count = getattr(parent_router, 'nest_count', 0) + 1
        self.nest_prefix = kwargs.pop('lookup', 'nested_%i' % self.nest_count) + '_'
        super(NestedRouter, self).__init__(*args, **kwargs)

        parent_registry = [registered for registered in self.parent_router.registry if registered[0] == self.parent_prefix]
        try:
            parent_registry = parent_registry[0]
            parent_prefix, parent_viewset, parent_basename = parent_registry
        except:
            raise RuntimeError('parent registered resource not found')

        nested_routes = []
        parent_lookup_regex = parent_router.get_lookup_regex(parent_viewset, self.nest_prefix)
        self.parent_regex = '{parent_prefix}/{parent_lookup_regex}/'.format(parent_prefix=parent_prefix, parent_lookup_regex=parent_lookup_regex)
        if hasattr(parent_router, 'parent_regex'):
            self.parent_regex = parent_router.parent_regex + self.parent_regex

        for route in self.routes:
            route_contents = route._asdict()
            route_contents['url'] = route.url.replace('^', '^' + self.parent_regex)
            nested_routes.append(route.__class__(**route_contents))

        self.routes = nested_routes
