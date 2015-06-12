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
 * - getActionClass: Returns class name for the action DOM element.
 * - getActionUrl: Returns the URL to navigate to when the action button is clicked.
 * - getActionContent: Returns the content of the action button. This may include HTML.
 *
 * To configure the card as a square card or list card, pass "square_card" or "list_card", respectively, as
 * "configuration" in the constructor. Default is square card.
 */
;(function (define) {
    'use strict';
    define(['jquery',
            'backbone',
            'text!templates/components/card/square-card.underscore',
            'text!templates/components/card/list-card.underscore'],
        function ($, Backbone, squareCardTemplate, listCardTemplate) {
            var CardView = Backbone.View.extend({
                events: {
                    'click .action' : 'action'
                },

                switchOnConfiguration: function (square_result, list_result) {
                    return (this.callIfFunction(this.configuration) || 'square_card') === 'square_card' ?
                        square_result : list_result;
                },

                callIfFunction: function (value) {
                    if ($.isFunction(value)) {
                        return value.call(this);
                    } else {
                        return value;
                    }
                },

                initialize: function () {
                    this.template = this.switchOnConfiguration(
                        _.template(squareCardTemplate),
                        _.template(listCardTemplate)
                    );
                    this.render();
                },

                className: function () {
                    return 'card ' +
                        this.switchOnConfiguration('square-card', 'list-card') +
                        ' ' + this.callIfFunction(this.cardClass);
                },

                configuration: function () {
                    return this.options.configuration;
                },

                render: function () {
                    this.$el.html(this.template({
                        card_class: this.callIfFunction(this.cardClass),
                        title: this.callIfFunction(this.title),
                        description: this.callIfFunction(this.description),
                        action_class: this.callIfFunction(this.actionClass),
                        action_url: this.callIfFunction(this.actionUrl),
                        action_content: this.callIfFunction(this.actionContent)
                    }));
                    var detailsEl = this.$el.find('.card-meta-details');
                    _.each(this.callIfFunction(this.details), function (detail) {
                        detail.render();
                        detail.$el.addClass('meta-detail');
                        detailsEl.append(detail.el);
                    });
                    return this;
                },

                action: function () { },
                cardClass: '',
                title: '',
                description: '',
                details: function () { return []; },
                actionClass: '',
                actionUrl: '',
                actionContent: ''
            });

            return CardView;
        });
}).call(this, define || RequireJS.define);
