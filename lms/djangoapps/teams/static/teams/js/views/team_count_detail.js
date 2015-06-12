/**
 * View for displaying the number of teams in a topic.
 */
;(function (define) {
    'use strict';
    define(['backbone', 'text!teams/templates/team_count_detail.underscore'], function (Backbone, template) {
        var TeamCountDetailView = Backbone.View.extend({
            tagName: 'p',
            className: 'team-count',

            initialize: function () {
                this.template = _.template(template);
                this.render();
            },

            render: function () {
                this.$el.html(this.template(this.model.attributes));
                return this;
            }
        });
        return TeamCountDetailView;
    });
}).call(this, define || RequireJS.define);
