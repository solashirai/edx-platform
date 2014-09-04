(function() {
    var CohortModel = Backbone.Model.extend({
        defaults: {
            name: "",
            user_count: "0"
        }
    });

    this.CohortModel = CohortModel;
}).call(this);
