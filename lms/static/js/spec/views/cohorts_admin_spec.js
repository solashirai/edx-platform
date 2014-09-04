describe("Cohorts Admin View", function() {
    var createMockCohorts, createCohortsView, installTemplateFixture;

    createMockCohorts = function() {
        return {
            cohorts: [{
                id: 1,
                name: 'Cat Lovers',
                user_count: 123
            },{
                id: 2,
                name: 'Dog Lovers',
                user_count: 456
            }]
        };
    };

    createCohortsView = function() {
        var cohorts, view;
        cohorts = new CohortCollection(createMockCohorts(), {parse: true});
        view = new CohortsAdminView({
            model: cohorts
        });
        view.render();
        return view;
    };

    installTemplateFixture = function(templateName, templateDirectory) {
        var templateFixture = readFixtures(templateDirectory + templateName + '.underscore');
        appendSetFixtures($('<script>', { id: templateName + '-template', type: 'text/template' })
            .text(templateFixture));
    };

    beforeEach(function() {
        setFixtures("<div></div>");
        installTemplateFixture('cohort-admin', 'templates/instructor_dashboard_2/');
        installTemplateFixture('cohorts-admin', 'templates/instructor_dashboard_2/');
    });

    describe("Cohort Selector", function() {
        it('has no initial selection', function() {
            var view = createCohortsView();
            view.render();
            expect(view.$('.cohort-select').val()).toBe('');
            expect(view.$('.cohort-management-group-header .title-value').text()).toBe('');
        });

        it('can select a cohort', function() {
            var view = createCohortsView();
            view.render();
            view.$('.cohort-select').val("1").change();
            expect(view.$('.cohort-select').val()).toBe('1');
            expect(view.$('.cohort-management-group-header .title-value').text()).toBe('Cat Lovers');
            expect(view.$('.cohort-management-group-header .group-count').text()).toBe('123');
        });

        it('can switch cohort', function() {
            var view = createCohortsView();
            view.render();
            view.$('.cohort-select').val("1").change();
            view.$('.cohort-select').val("2").change();
            expect(view.$('.cohort-select').val()).toBe('2');
            expect(view.$('.cohort-management-group-header .title-value').text()).toBe('Dog Lovers');
            expect(view.$('.cohort-management-group-header .group-count').text()).toBe('456');
        });
    });
});
