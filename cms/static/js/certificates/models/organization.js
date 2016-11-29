// Backbone.js Application Model: Certificate Organization

define([ // jshint ignore:line
    'underscore',
    'underscore.string',
    'backbone',
    'backbone-relational',
    'gettext'
],
function(_, str, Backbone, BackboneRelational, gettext) {
    'use strict';
    _.str = str;

    var Organization = Backbone.RelationalModel.extend({
        defaults: {
            short_name: ''
        },
        NOT_FOUND_MESSAGE: gettext("No organization found. Please contact your manager to add the organization to the system."),
        DUPLICATE_MESSAGE: gettext("Organization already added."),

        initialize: function() {
            // Set the unique id for Backbone Relational
            this.set('id', _.uniqueId('organization'));
            return this;
        },

        parse: function(response) {
            // Parse must be defined for the model, but does not need to do anything special right now
            return response;
        },

        getOrganizationDetails: function() {
            for (var i=0; i < window.organizationsList.length; i++) {
                var organization = window.organizationsList[i];
                if (organization.short_name === this.get('short_name')) {
                    return {
                        long_name: organization.long_name,
                        logo: organization.logo || ''
                    };
                }
            }
            throw new Error(this.NOT_FOUND_MESSAGE);
        }
    });
    return Organization;
});
