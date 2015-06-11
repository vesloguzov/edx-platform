;(function (define) {
    'use strict';
    define(['backbone', 'gettext', 'js/components/card/views/card'],
        function (Backbone, gettext, CardView) {
            var TopicCardView = CardView.extend({
                action: function (event) {
                    event.preventDefault();
                    console.log("Navigating to topic " + this.model.get('id'));
                },

                getCardClass: function () { return 'topic-card'; },
                getTitle: function () { return this.model.get('name'); },
                getDescription: function () { return this.model.get('description'); },
                getDetails: function () {
                    return [{
                        tag: 'p',
                        detail_class: 'team-count',
                        content: interpolate(
                            gettext('%(team_count)s Teams'),
                            { team_count: this.model.get('team_count') },
                            true
                        )
                    }]
                },
                getActionContent: function () { return gettext('View') + ' <span class="icon fa-arrow-right"></span>'; }
            });

            return TopicCardView;
        });
}).call(this, define || RequireJS.define);