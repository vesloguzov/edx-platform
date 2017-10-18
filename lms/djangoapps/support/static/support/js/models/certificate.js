(function(define) {
    'use strict';
    define(['backbone'], function(Backbone) {
        return Backbone.Model.extend({
            defaults: {
                username: null,
                course_key: null,
                type: null,
                status: null,
                error_reason: null,
                download_url: null,
                grade: null,
                created: null,
                modified: null,
                generation_enabled: false
            }
        });
    });
}).call(this, define || RequireJS.define);
