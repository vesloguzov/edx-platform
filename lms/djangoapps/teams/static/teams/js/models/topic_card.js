/**
 * Model for a topic card.
 */
(function (define) {
    'use strict';
    define(['backbone'], function (Backbone) {
        var TopicCardModel = Backbone.Model.extend({
            defaults: {
                name: '',
                description: '',
                team_count: 0,
                id: ''
            }
        });
        return TopicCardModel;
    })
}).call(this, define || RequireJS.define);
