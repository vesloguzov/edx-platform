define(["backbone", "jquery", "jquery.ui", "jquery.ui.datepickerDefaults"], function(Backbone, $) {
    // course update -- biggest kludge here is the lack of a real id to map updates to originals
    var CourseUpdate = Backbone.Model.extend({
        defaults: {
            "date" : $.datepicker.formatDate($.datepicker._defaults['dateFormat'], new Date()),
            "content" : "",
            "push_notification_enabled": false,
            "push_notification_selected" : false
        }
    });
    return CourseUpdate;
}); // end define()
