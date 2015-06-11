(function (define) {
    'use strict';

    define(['jquery',
            'underscore',
            'js/components/card/views/card'
           ],
        function($, _, CardView) {

            describe('card component view', function () {
                var view;

                beforeEach(function () {
                    view = new (CardView.extend({
                        action: function (event) {
                            event.preventDefault();
                            view.$el.toggleClass('clicked');
                        }
                    }))({
                        configuration: 'square_card'
                    });
                });

                it('can render itself', function () {
                    expect(view.$el.find('.card')).toHaveClass('square-card');
                });

                it('changes when clicked', function () {
                    view.$el.find('.action').trigger('click');
                    expect(view.$el).toHaveClass('clicked');
                });
            });
        });
}).call(this, define || RequireJS.define);
