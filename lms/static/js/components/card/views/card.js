/**
 * A generic card view class.
 *
 * Subclasses can implement any of the following functions:
 * - action: Action to take when the action button is clicked. Defaults to a no-op.
 * - getCardClass: Returns class name for this card's DOM element.
 * - getTitle: Returns the title of the card.
 * - getDescription: Returns the description of the card.
 * - getDetails: Returns an array of detail hashes with this structure:
 *      - tag: string of the HTML tag name for this detail
 *      - detail_class: class for the detail DOM element
 *      - content: Detail content. This may include HTML.
 * - getActionUrl: Returns the URL to navigate to when the action button is clicked.
 * - getActionContent: Returns the content of the action button. This may include HTML.
 *
 * To configure the card as a square card or list card, pass "square_card" or "list_card", respectively, as
 * "configuration" in the constructor. Default is square card.
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

                switchOnConfiguration: function (configuration, square_result, list_result) {
                    return (configuration || 'square_card') == 'square_card' ? square_result : list_result;
                },

                initialize: function (options) {
                    this.template = this.switchOnConfiguration(
                        options.configuration,
                        _.template(squareCardTemplate),
                        _.template(listCardTemplate)
                    );
                    this.render();
                },

                className: function () {
                    return 'card ' +
                        this.switchOnConfiguration(this.options.configuration, 'square-card', 'list-card') +
                        ' ' + this.getCardClass();
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

                action: function () { },
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
