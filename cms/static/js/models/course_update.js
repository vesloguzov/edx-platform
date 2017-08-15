define(['backbone', 'jquery', 'jquery.ui', 'jquery.ui.datepickerDefaults'], function(Backbone, $) {
    // course update -- biggest kludge here is the lack of a real id to map updates to originals
    var INTERNAL_DATE_FORMAT = 'yy-mm-dd';  // ISO-8601

    var CourseUpdate = Backbone.Model.extend({
        defaults: {
            "date" : $.datepicker.formatDate(INTERNAL_DATE_FORMAT, new Date()),
            'content': '',
            'push_notification_enabled': false,
            'push_notification_selected': false
        },
        validate: function(attrs) {
            var date_exists = (attrs.date !== null && attrs.date !== '');
            var date_is_valid_string = ($.datepicker.formatDate(INTERNAL_DATE_FORMAT, new Date(attrs.date)) === attrs.date);
            if (!(date_exists && date_is_valid_string)) {
                return {'date_required': gettext('Action required: Enter a valid date.')};
            }
        },
        getInputDate: function() {
            try {
                var date = new Date(this.get('date'));
            } catch (e) {
                var date = null;
            }
            return $.datepicker.formatDate($.datepicker._defaults['dateFormat'], date);
        },
        dateFromInputDate: function(inputDate) {
            try {
                var parsedDate = $.datepicker.parseDate($.datepicker._defaults['dateFormat'], inputDate);
            } catch (e) {
                var parsedDate = null;
            }
            return $.datepicker.formatDate(INTERNAL_DATE_FORMAT, parsedDate);
        },
        getLongDate: function() {
            // temporary solution (since edx-ui-toolkit DateUtil has broken language resolution
            return this.getInputDate();
        }
    });
    return CourseUpdate;
}); // end define()
