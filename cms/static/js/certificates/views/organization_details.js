// Backbone Application View:  Signatory Details

define([ // jshint ignore:line
    'jquery',
    'underscore',
    'underscore.string',
    'backbone',
    'gettext',
    'js/utils/templates',
    'common/js/components/utils/view_utils',
    'js/views/baseview'
],
function ($, _, str, Backbone, gettext, TemplateUtils, ViewUtils, BaseView) {
    'use strict';
    var OrganizationDetailsView = BaseView.extend({
        tagName: 'div',
        events: {
            'click .action-delete-organization': 'triggerDeleteOrganization'
        },

        className: function () {
            // Determine the CSS class names for this model instance
            var index = this.model.collection.indexOf(this.model);
            return [
                'organization-details',
                'organization-details-view-' + index
            ].join(' ');
        },

        initialize: function(options) {
            // Set up the initial state of the attributes set for this model instance
            this.eventAgg = options.eventAgg;
            this.template = this.loadTemplate('organization-details');
            // Show/hide editing controls
            this.editable = options.editable || false;
        },

        loadTemplate: function(name) {
            // Retrieve the corresponding template for this model
            return TemplateUtils.loadTemplate(name);
        },

        render: function() {
            // Assemble the detail view for this model
            var context = this.getTemplateContext();
            $(this.el).html(this.template(context));
            return this;
        },

        getTemplateContext: function() {
            var details = this.model.getOrganizationDetails();
            return $.extend(
                {editable: this.editable},
                this.model.attributes,
                details
            );
        },
        triggerDeleteOrganization: function(event) {
            this.eventAgg.trigger("onClickDeleteOrganization", event, this.model);
        }
    });
    return OrganizationDetailsView;
});
