/**
 * View for a topic card. Displays a TopicCardModel.
 */
;(function (define) {
    'use strict';
    define(['backbone', 'gettext', 'js/components/card/views/card', 'teams/js/views/team_count_detail'],
        function (Backbone, gettext, CardView, TeamCountDetailView) {
            var TopicCardView = CardView.extend({
                initialize: function () {
                    this.detailViews = [new TeamCountDetailView({ model: this.model })];
                    CardView.prototype.initialize.apply(this, arguments);
                },

                action: function (event) {
                    event.preventDefault();
                    console.log("Navigating to topic " + this.model.get('id'));
                },

                configuration: 'square_card',
                cardClass: 'topic-card',
                title: function () { return this.model.get('name'); },
                description: function () { return this.model.get('description'); },
                details: function () { return this.detailViews; },
                actionClass: 'action-view',
                actionContent: gettext('View') + ' <span class="icon fa-arrow-right"></span>'
            });

            return TopicCardView;
        });
}).call(this, define || RequireJS.define);
