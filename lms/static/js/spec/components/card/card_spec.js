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
                    spyOn(CardView.prototype, "action");
                    view = new CardView({
                        configuration: 'square_card'
                    });
                });

                it('can render itself as a square card', function () {
                    expect(view.$el).toHaveClass('square-card');
                });

                it('can render itself as a list card', function () {
                    view = new CardView({ configuration: 'list_card' });
                    expect(view.$el).toHaveClass('list-card');
                });

                it('calls action when clicked', function () {
                    view.$el.find('.action').trigger('click');
                    expect(view.action).toHaveBeenCalled();
                });
            });
        });
}).call(this, define || RequireJS.define);
