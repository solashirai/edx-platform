(function() {
    var CohortAdminView = Backbone.View.extend({
        initialize: function(options) {
            this.template = _.template($('#cohort-admin-template').text());
        },

        render: function() {
            this.$el.html(this.template({
                cohort: this.model
            }));
            return this;
        }
    });

    this.CohortAdminView = CohortAdminView;
}).call(this);
