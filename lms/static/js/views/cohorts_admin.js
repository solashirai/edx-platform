(function() {
    var CohortsAdminView = Backbone.View.extend({
        events : {
            "change .cohort-select": "selectCohort"
        },

        initialize: function(options) {
            this.template = _.template($('#cohorts-admin-template').text());
        },

        render: function() {
            this.$el.html(this.template({
                cohorts: this.model.models
            }));
            return this;
        },

        getSelectedCohort: function() {
            var id = this.$('.cohort-select').val(),
                cohorts = this.model.models,
                i;
            for (i=0; i < cohorts.length; i++) {
                if (cohorts[i].get('id').toString() === id) {
                    return cohorts[i];
                }
            }
            return null;
        },

        selectCohort: function(event) {
            event.preventDefault();
            var selectedCohort = this.getSelectedCohort();
            this.cohortView = new CohortAdminView({
                el: this.$('.cohort-management-group'),
                model: selectedCohort
            });
            this.cohortView.render();
        }
    });

    this.CohortsAdminView = CohortsAdminView;
}).call(this);
