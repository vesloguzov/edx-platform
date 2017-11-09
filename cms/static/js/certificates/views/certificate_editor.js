// Backbone Application View: Certificate Editor

define([
    'jquery',
    'underscore',
    'backbone',
    'gettext',
    'js/views/list_item_editor',
    'js/certificates/models/signatory',
    'js/certificates/views/signatory_editor',
    'js/certificates/views/organizations_editor',
    'text!templates/certificate-editor.underscore'
],
function($, _, Backbone, gettext,
         ListItemEditorView, SignatoryModel, SignatoryEditorView, OrganizationsEditorView, certificateEditorTemplate) {
    'use strict';

    // If signatories limit is required to specific value then we can change it.
    // However, Setting this limit to 100 that will allow PMs to add as many signatories as they want.
    var MAX_SIGNATORIES_LIMIT = 100;
    var CertificateEditorView = ListItemEditorView.extend({
        tagName: 'div',
        events: {
            'change .collection-name-input': 'setName',
            'change .certificate-description-input': 'setDescription',
            'change .certificate-course-title-input': 'setCourseTitle',
            'change .certificate-course-description-input': 'setCourseDescription',
            'change .certificate-show-grade-input': 'setShowGrade',
            'change .certificate-honor-code-disclaimer-input': 'setHonorCodeDisclaimer',
            'focus .input-text': 'onFocus',
            'blur .input-text': 'onBlur',
            'submit': 'setAndClose',
            'click .action-cancel': 'cancel',
            'click .action-add-signatory': 'addSignatory'
        },

        className: function() {
            // Determine the CSS class names for this model instance
            var index = this.model.collection.indexOf(this.model);

            return [
                'collection-edit',
                'certificates',
                'certificate-edit',
                'certificate-edit-' + index
            ].join(' ');
        },

        initialize: function(options) {
            // Set up the initial state of the attributes set for this model instance
            _.bindAll(this, 'onSignatoryRemoved', 'clearErrorMessage');
            this.max_signatories_limit = options.max_signatories_limit || MAX_SIGNATORIES_LIMIT;
            this.template = _.template(certificateEditorTemplate);
            this.eventAgg = _.extend({}, Backbone.Events);
            this.eventAgg.bind('onSignatoryRemoved', this.onSignatoryRemoved);
            this.eventAgg.bind('onSignatoryUpdated', this.clearErrorMessage);
            ListItemEditorView.prototype.initialize.call(this);
        },

        onSignatoryRemoved: function() {
            // Event handler for model deletions
            this.model.setOriginalAttributes();
            this.render();
        },

        clearErrorMessage: function() {
            // Hides away the error message displayed during field validations
            this.$('.certificate-edit-error').remove();
        },

        render: function() {
            // Assemble the editor view for this model
            ListItemEditorView.prototype.render.call(this);
            var self = this;
            // Ensure we have at least one signatory associated with the certificate.
            this.model.get('signatories').each(function(modelSignatory) {
                var signatory_view = new SignatoryEditorView({
                    model: modelSignatory,
                    isEditingAllCollections: true,
                    eventAgg: self.eventAgg
                });
                self.$('div.signatory-edit-list').append($(signatory_view.render()));
            });
            this.disableAddSignatoryButton();

            var organizations_editor = new OrganizationsEditorView({
                collection: this.model.get("organizations")
            });
            this.$('div.organizations-wrapper').append(organizations_editor.render().$el);
            return this;
        },

        addSignatory: function() {
            // Append a new signatory to the certificate model's signatories collection
            var signatory = new SignatoryModel({certificate: this.getSaveableModel()});  // eslint-disable-line max-len, no-unused-vars
            this.render();
        },

        disableAddSignatoryButton: function() {
            // Disable the 'Add Signatory' link if the constraint has been met.
            if (this.$('.signatory-edit-list > div.signatory-edit').length >= this.max_signatories_limit) {
                this.$('.action-add-signatory').addClass('disableClick');
            }
        },

        getTemplateOptions: function() {
            // Retrieves the current attributes/options for the model
            return {
                id: this.model.get('id'),
                uniqueId: _.uniqueId(),
                name: this.model.get('name'),
                description: this.model.get('description'),
                course_title: this.model.get('course_title'),
                course_description: this.model.get('course_description'),
                show_grade: this.model.get('show_grade'),
                honor_code_disclaimer: this.model.get('honor_code_disclaimer'),
                org_logo_path: this.model.get('org_logo_path'),
                is_active: this.model.get('is_active'),
                isNew: this.model.isNew()
            };
        },

        getSaveableModel: function() {
            // Returns the current model instance
            return this.model;
        },

        setName: function(event) {
            this._setTextModelField(event, 'name', '.collection-name-input');
        },

        setDescription: function(event) {
            this._setTextModelField(event, 'description', '.certificate-description-input');
        },

        setCourseTitle: function(event) {
            this._setTextModelField(event, 'course_title', '.certificate-course-title-input');
        },

        setCourseDescription: function(event) {
            this._setTextModelField(event, 'course_description', '.certificate-course-description-input');
        },

        setHonorCodeDisclaimer: function(event) {
            this._setTextModelField(event, 'honor_code_disclaimer', '.certificate-honor-code-disclaimer-input');
        },

        setShowGrade: function(event) {
            // Updates the indicated model field (still requires persistence on server)
            if (event && event.preventDefault) { event.preventDefault(); }
            this.model.set(
                'show_grade',
                this.$('.certificate-show-grade-input').is(':checked'),
                { silent: true }
            );
        },

        _setTextModelField: function(event, model_field_name, input_selector) {
            // Updates the indicated model field (still requires persistence on server)
            if (event && event.preventDefault) { event.preventDefault(); }
            this.model.set(
                model_field_name,
                this.$(input_selector).val(),
                { silent: true }
            );
        },

        setValues: function() {
            // Update the specified values in the local model instance
            this.setName();
            this.setDescription();
            this.setCourseTitle();
            this.setCourseDescription();
            this.setShowGrade();
            this.setHonorCodeDisclaimer();
            return this;
        }
    });
    return CertificateEditorView;
});
