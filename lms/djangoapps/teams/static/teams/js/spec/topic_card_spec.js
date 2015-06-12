(function (define) {
    'use script';

    define(['jquery',
            'underscore',
            'teams/js/views/topic_card',
            'teams/js/models/topic_card'],
        function ($, _, TopicCardView, TopicCardModel) {

            describe('topic card view', function () {
                var view;

                beforeEach(function () {
                    view = new TopicCardView({
                        model: new TopicCardModel({
                            'id': 'renewables',
                            'name': 'Renewable Energy',
                            'description': 'Explore how changes in renewable energy will affect our lives.',
                            'team_count': 34
                        }),
                    });
                });

                it('can render itself', function () {
                    expect(view.$el.find('.card-title').text()).toContain('Renewable Energy');
                    expect(view.$el.find('.card-description').text()).toContain('changes in renewable energy');
                    expect(view.$el.find('.card-meta-details').text()).toContain('34 Teams');
                    expect(view.$el.find('.action').text()).toContain('View');
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
