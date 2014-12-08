(function($){
$.fn.extend({
/* ajaxForm plugin
 * @author <a href="mailto:liubov@lektorium.tv">Liubov Fomicheva</a>
 * @requires jQuery 1.6+
 *
 * Copyright 2014, Liubov Fomicheva
 *
 * Performs basic form handling: submitting post requests to some url and
 * handling jXHR like:
 *     {
 *          success: [true, false],
 *          errors: {
 *              ['', 'field_name']: 'error text'],
 *          }
 *      }
 *
 * JSON responses returned with status 400 are searched for 'error' object
 * field that would be displayed as 'non_field_errors' div.
 *
 * Requires form to have placeholder <div>s in places for field errors
 * with ids like "<field_id>_error" and with class 'non_field_errors' for
 * non-field errors.
 *
 * Options:
 *      action: form action for submit event,
 *      method: form method (default: 'post'),
 *      onSuccess: event handler for succeded form submission,
 *      onError: event handler for unseccessful form submission, triggered after errors are rendered,
 *      onCancel: event handler for $('.cancel') form button,
 *      errorClass: class used for error messages (default: 'error')
 */

    ajaxForm: function(opts){
        var defaults = {
            action: null,
            method: 'post',
            onSuccess: null,
            onError: null,
            onCancel: null,
            errorClass: 'error'
        }
        var options = $.extend(defaults, opts);

        return this.each(function(){
            var form = $(this);
            form.submit(function(){
                $('.' + options.errorClass).remove();

                $.ajax({
                    url: options.action || form.attr('action'),
                    type: options.method,
                    data: form.serialize()
                })
                .done(function(response){
                    if (response.success){
                        if (options.onSuccess)
                            options.onSuccess(form);
                    } else {
                        var errors = response.errors;
                        var error_fields = [];
                        $.each(errors, function(index, error){
                            var error_div = $('<div></div>')
                            .addClass(options.errorClass)
                            .text(error.errors).show();
                            if (error.field  == '')
                              form.find('.non_field_errors').html(error_div);
                            else{
                              $('#' + error.field + '_error').html(error_div);
                              error_fields.push($('#' + error.field));
                            }
                        });
                        if (error_fields.length)
                            error_fields[0].focus();
                        if (options.onError)
                            options.onError(form);
                    }
                })
                .fail(function(jXHR, textStatus, errorThrown){
                    if (jXHR.status == 400) {
                    try {
                        response = $.parseJSON(jXHR.responseText);
                        if (response.error) {
                            var error_div = $('<div></div>')
                             .addClass(options.errorClass)
                             .text(response.error).show();
                            form.find('.non_field_errors').html(error_div);
                        }
                    } catch (exception) {}
                    }
                });
            return false;
            });
            if (options.onCancel)
                form.find('.cancel').click(options.onCancel)
        });
    }
});
})(jQuery);
