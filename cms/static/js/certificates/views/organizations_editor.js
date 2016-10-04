// Backbone Application View: Organizations List Editor

define([ // jshint ignore:line
    'jquery',
    'underscore',
    'backbone',
    'gettext',
    'js/utils/templates',
    'js/certificates/models/organization',
    'js/certificates/views/organization_details',
    'jquery.ui'
],
function ($, _, Backbone, gettext, TemplateUtils, OrganizationModel, OrganizationDetailsView) {
    'use strict';
    var OrganizationsEditorView = Backbone.View.extend({
        tagName: 'div',
        className: 'organizations-editor',
        events: {
            'change .organization-short_name-input': 'updateAddButtonState',
            'click .action-add-organization': 'onAddOrganization',
            'keyup .organization-short_name-input': 'shortNameKeyUp',
            'keypress .organization-short_name-input': 'preventFormSubmission'
        },
        initialize: function() {
            this.eventAgg = _.extend({}, Backbone.Events);
            this.eventAgg.bind("onClickDeleteOrganization", this.deleteOrganization, this);

            this.template = this.loadTemplate('organizations-editor');
            this.organization_template = this.loadTemplate('organization-details');
        },

        render: function() {
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
            this._setupAutocomplete();
            return this;
        },

        loadTemplate: function(name) {
            // Retrieve the corresponding template for this model
            return TemplateUtils.loadTemplate(name);
        },

        onAddOrganization: function(event) {
            if (event && event.preventDefault) { event.preventDefault(); }
            var short_name = this.$('.organization-short_name-input').val().trim();

            if (! this._organizationExists(short_name)) {
                this._toggleOrganizationError(OrganizationModel.prototype.NOT_FOUND_MESSAGE);
            } else if (this._organizationUsed(short_name)) {
                this._toggleOrganizationError(OrganizationModel.prototype.DUPLICATE_MESSAGE);
            } else {
                this.addOrganization();
            }
        },

        addOrganization: function() {
            // Appends organization to certificate models organizations collection
            // (still requires persistence on server)
            new OrganizationModel({
                certificate: this.collection.certificate,
                short_name: this.$('.organization-short_name-input').val().trim()
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
            this._toggleOrganizationError(false);
            if (event.which === $.ui.keyCode.ENTER) {
                this.onAddOrganization();
            }
        },

        preventFormSubmission: function(event) {
            if (event.which === $.ui.keyCode.ENTER) { event.preventDefault(); }
        },

        _setupAutocomplete: function() {
            var self = this;
            this.$('.organization-short_name-input').autocomplete({
                source: function(request, response) {
                    var matcher = new RegExp( $.ui.autocomplete.escapeRegex( request.term ), "i" );
                    response(
                        $.grep(window.organizationsList, function(item) {
                            return (
                                matcher.test(item.short_name) || matcher.test(item.long_name)
                            ) && !self._organizationUsed(item.short_name);
                        })
                    );
                },
                focus: function(event, ui) {
                    $(this).val(ui.item.short_name).change();
                    return false;
                },
                select: function(event, ui) {
                    $(this).val(ui.item.short_name).change();
                    return false;
                }
            }).data('ui-autocomplete')._renderItem = function(ul, item) {
                // show short and long organization names
                return $('<li>').append(
                    $('<a>').append(
                        $('<strong>').text(item.short_name + ': '),
                        document.createTextNode(item.long_name)
                    )
                ).appendTo(ul);

            };
        },
        _organizationExists: function(short_name) {
            return $.grep(window.organizationsList, function(item){
                return item.short_name === short_name;
            }).length > 0;
        },
        _organizationUsed: function(short_name) {
            var used = this.collection.certificate.get('organizations').map(function(organization){
                return organization.get('short_name');
            });
            return $.inArray(short_name, used) != -1;
        },

        _toggleOrganizationError: function(message) {
            this.$('.organization-add-input-wrapper').toggleClass('error', message);
            this.$('.organization-add-error').text(message);
        }
    });
    return OrganizationsEditorView;
});
