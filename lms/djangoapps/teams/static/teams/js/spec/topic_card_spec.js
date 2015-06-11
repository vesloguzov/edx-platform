(function (define) {
    'use script';

    define(['jquery',
            'underscore',
            'backbone',
            'teams/js/views/topic_card'],
        function ($, _, Backbone, TopicCardView) {

            describe('topic card view', function () {
                var view;

                beforeEach(function () {
                    view = new TopicCardView({
                        model: new Backbone.Model({
                            'id': 'renewables',
                            'name': 'Renewable Energy',
                            'description': 'Explore how changes in renewable energy will affect our lives.',
                            'team_count': 34
                        }),
                        configuration: 'square_card'
                    });
                });

                it('can render itself', function () {
                    expect(view.$el.find('.card-title').text()).toContain('Renewable Energy');
                    expect(view.$el.find('.card-description').text()).toContain('changes in renewable energy');
                    expect(view.$el.find('.card-meta-details').text()).toContain('34 Teams');
                });

                it('navigates when clicked', function () {
                    spyOn(console, 'log');
                    view.$el.find('.action').trigger('click');
                    expect(console.log).toHaveBeenCalledWith('Navigating to topic renewables');
                });
            });
        }
    );
}).call(this, define || RequireJS.define);