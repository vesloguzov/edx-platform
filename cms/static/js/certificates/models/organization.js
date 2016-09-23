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

        initialize: function() {
            // Set the unique id for Backbone Relational
            this.set('id', _.uniqueId('organization'));
            return this;
        },

        parse: function(response) {
            // Parse must be defined for the model, but does not need to do anything special right now
            return response
        },

        getOrganizationDetails: function(){
            return {
                // TODO: implement
                long_name: 'Test Organization',
                logo: '//test_logo'
            }
        }
    });
    return Organization;
});
