;(function (define) {
    'use strict';
    define(['backbone', 'gettext', 'js/components/card/views/card', 'teams/js/views/team_count_detail'],
        function (Backbone, gettext, CardView, TeamCountDetailView) {
            var TopicCardView = CardView.extend({
                configuration: 'square_card',

                action: function (event) {
                    event.preventDefault();
                    console.log("Navigating to topic " + this.model.get('id'));
                },

                cardClass: 'topic-card',
                title: function () { return this.model.get('name'); },
                description: function () { return this.model.get('description'); },
                details: function () {
                    return [new TeamCountDetailView({ model: this.model })]
                },
                actionClass: 'action-view',
                actionContent: gettext('View') + ' <span class="icon fa-arrow-right"></span>'
            });

            return TopicCardView;
        });
}).call(this, define || RequireJS.define);