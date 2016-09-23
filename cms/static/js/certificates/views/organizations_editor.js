// Backbone Application View: Organizations List Editor

define([ // jshint ignore:line
    'jquery',
    'underscore',
    'backbone',
    'gettext',
    'js/utils/templates',
    'js/certificates/models/organization',
    'js/certificates/views/organization_details'
],
function ($, _, Backbone, gettext, TemplateUtils, OrganizationModel, OrganizationDetailsView) {
    'use strict';
    var OrganizationsEditorView = Backbone.View.extend({
        tagName: 'div',
        className: 'organizations-editor',
        events: {
            'change .organization-short_name-input': 'updateAddButtonState',
            'click .action-add-organization': 'addOrganization',
            'keyup .organization-short_name-input': 'shortNameKeyUp',
            'keypress .organization-short_name-input': 'preventFormSubmission'
            // TODO: sorting
        },
        initialize: function(options) {
            this.eventAgg = _.extend({}, Backbone.Events);
            this.eventAgg.bind("onClickDeleteOrganization", this.deleteOrganization, this);

            this.template = this.loadTemplate('organizations-editor');
            this.organization_template = this.loadTemplate('organization-details');
        },

        render: function(options) {
            var self = this;
            $(this.el).html(this.template());
            this.collection.each(function(modelOrganization) {
                var organization_detail_view = new OrganizationDetailsView({
                    model: modelOrganization,
                    editable: true,
                    eventAgg: self.eventAgg
                });
                self.$('div.organizations-edit-list').append($(organization_detail_view.render().$el));
            });
            return this;
        },

        loadTemplate: function(name) {
            // Retrieve the corresponding template for this model
            return TemplateUtils.loadTemplate(name);
        },

        addOrganization: function(event) {
            // Appends organization to certificate models organizations collection (still requires persistence on server)
            if (event && event.preventDefault) { event.preventDefault(); }
            var organizations = new OrganizationModel({
                certificate: this.collection.certificate,
                short_name: this.$('.organization-short_name-input').val()
            });
            this.render();
            this.$('.organization-short_name-input').focus();
        },

        deleteOrganization: function(event, model) {
            if (event && event.preventDefault) { event.preventDefault(); }
            model.collection.remove(model);
            this.render();
            this.eventAgg.trigger("onOrganizationRemoved", model);
        },

        shortNameKeyUp: function(event) {
            this.$('.organization-short_name-input').trigger('change');
            if (event.which == $.ui.keyCode.ENTER) {
                // TODO: implement search
                var organization_found = true;
                if (organization_found) {
                    this.addOrganization();
                }
            }
        },

        updateAddButtonState: function() {
            // Searches for organization in organizations list
            // and enables/disables add organizaton button
            // TODO: implement search
            var organization_found = true;
            this.$(".action-add-organization").toggleClass("disableClick", !organization_found);
        },

        preventFormSubmission: function(event) {
            if (event.which == $.ui.keyCode.ENTER) { event.preventDefault(); }
        }
    });
    return OrganizationsEditorView;
});
