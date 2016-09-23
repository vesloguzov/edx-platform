// Backbone.js Application Collection: Certificate Organizations

define([ // jshint ignore:line
    'backbone',
    'js/certificates/models/organization'
],
function(Backbone, Organization) {
    'use strict';
    var OrganizationCollection = Backbone.Collection.extend({
        model: Organization
    });
    return OrganizationCollection;
});
