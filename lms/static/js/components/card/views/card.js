/**
 * A generic card view class.
 *
 * Subclasses must implement:
 * - action (function): Action to take when the action text is clicked.
 */
;(function (define) {
    'use strict';
    define(['backbone',
            'text!templates/components/card/square-card.underscore',
            'text!templates/components/card/list-card.underscore'],
        function (Backbone, squareCardTemplate, listCardTemplate) {
            var CardView = Backbone.View.extend({
                events: {
                    'click .action' : 'action'
                },

                initialize: function (options) {
                    var configuration = options.configuration || 'square_card';
                    this.template = configuration == 'square_card' ?
                        _.template(squareCardTemplate) : _.template(listCardTemplate);
                    this.render();
                },

                render: function () {
                    this.$el.html(this.template({
                        card_class: this.getCardClass(),
                        title: this.getTitle(),
                        description: this.getDescription(),
                        details: this.getDetails(),
                        action_url: this.getActionUrl(),
                        action_content: this.getActionContent()
                    }));
                    return this;
                },

                getCardClass: function () { return ''; },
                getTitle: function () { return ''; },
                getDescription: function () { return ''; },
                getDetails: function () { return []; },
                getActionUrl: function () { return ''; },
                getActionContent: function () { return ''; }
            });

            return CardView;
        });
}).call(this, define || RequireJS.define);
