define(['jquery',
        'edx-ui-toolkit/js/utils/spec-helpers/ajax-helpers',
        'common/js/spec_helpers/view_helpers', 'js/index',
        'common/js/components/utils/view_utils'],
    function($, AjaxHelpers, ViewHelpers, IndexUtils, ViewUtils) {
        describe('Course listing page', function() {
            var mockIndexPageHTML = readFixtures('mock/mock-index-page.underscore');

            var fillInFields = function(org, number, run, name) {
                $('.new-course-org').val(org);
                $('.new-course-number').val(number);
                $('.new-course-run').val(run);
                $('.new-course-name').val(name);
            };

            var fillInLibraryFields = function(org, number, name) {
                $('.new-library-org').val(org).keyup();
                $('.new-library-number').val(number).keyup();
                $('.new-library-name').val(name).keyup();
            };

            beforeEach(function() {
                ViewHelpers.installMockAnalytics();
                appendSetFixtures(mockIndexPageHTML);
                IndexUtils.onReady();
            });

            afterEach(function() {
                ViewHelpers.removeMockAnalytics();
                delete window.source_course_key;
            });

            it('can dismiss notifications', function() {
                var requests = AjaxHelpers.requests(this);
                var reloadSpy = spyOn(ViewUtils, 'reload');
                $('.dismiss-button').click();
                AjaxHelpers.expectJsonRequest(requests, 'DELETE', 'dummy_dismiss_url');
                AjaxHelpers.respondWithNoContent(requests);
                expect(reloadSpy).toHaveBeenCalled();
            });

            it('saves new courses', function() {
                var requests = AjaxHelpers.requests(this);
                var redirectSpy = spyOn(ViewUtils, 'redirect');
                $('.new-course-button').click();
                AjaxHelpers.expectJsonRequest(requests, 'GET', '/organizations');
                AjaxHelpers.respondWithJson(requests, ['DemoX', 'DemoX2', 'DemoX3']);
                fillInFields('DemoX', 'DM101', '2014', 'Demo course');
                $('.new-course-save').click();
                AjaxHelpers.expectJsonRequest(requests, 'POST', '/course/', {
                    org: 'DemoX',
                    number: 'DM101',
                    run: '2014',
                    display_name: 'Demo course'
                });
                AjaxHelpers.respondWithJson(requests, {
                    url: 'dummy_test_url'
                });
                expect(redirectSpy).toHaveBeenCalledWith('dummy_test_url');
                $('.new-course-org').autocomplete('destroy');
            });

            it('set the correct direction of text in case of rtl', function() {
                $('body').addClass('rtl');
                $('.new-course-button').click();
                $('.new-course-run').val('2014_T2').trigger('input');
                expect($('.new-course-run').hasClass('placeholder-text-direction')).toBe(false);
                $('.new-course-run').val('').trigger('input');
                expect($('.new-course-run').hasClass('placeholder-text-direction')).toBe(true);
            });


            it('displays an error when saving fails', function() {
                var requests = AjaxHelpers.requests(this);
                $('.new-course-button').click();
                AjaxHelpers.expectJsonRequest(requests, 'GET', '/organizations');
                AjaxHelpers.respondWithJson(requests, ['DemoX', 'DemoX2', 'DemoX3']);
                fillInFields('DemoX', 'DM101', '2014', 'Demo course');
                $('.new-course-save').click();
                AjaxHelpers.respondWithJson(requests, {
                    ErrMsg: 'error message'
                });
                expect($('.create-course .wrap-error')).toHaveClass('is-shown');
                expect($('#course_creation_error')).toContainText('error message');
                expect($('.new-course-save')).toHaveClass('is-disabled');
                expect($('.new-course-save')).toHaveAttr('aria-disabled', 'true');
                $('.new-course-org').autocomplete('destroy');
            });

            it('saves new libraries', function() {
                var requests = AjaxHelpers.requests(this);
                var redirectSpy = spyOn(ViewUtils, 'redirect');
                $('.new-library-button').click();
                fillInLibraryFields('DemoX', 'DM101', 'Demo library');
                $('.new-library-save').click();
                AjaxHelpers.expectJsonRequest(requests, 'POST', '/library/', {
                    org: 'DemoX',
                    number: 'DM101',
                    display_name: 'Demo library'
                });
                AjaxHelpers.respondWithJson(requests, {
                    url: 'dummy_test_url'
                });
                expect(redirectSpy).toHaveBeenCalledWith('dummy_test_url');
            });

            it('displays an error when a required field is blank', function() {
                var requests = AjaxHelpers.requests(this);
                $('.new-library-button').click();
                var values = ['DemoX', 'DM101', 'Demo library'];
                // Try making each of these three values empty one at a time and ensure the form won't submit:
                for (var i = 0; i < values.length; i++) {
                    var values_with_blank = values.slice();
                    values_with_blank[i] = '';
                    fillInLibraryFields.apply(this, values_with_blank);
                    expect($('.create-library li.field.text input').parent()).toHaveClass('error');
                    expect($('.new-library-save')).toHaveClass('is-disabled');
                    expect($('.new-library-save')).toHaveAttr('aria-disabled', 'true');
                    $('.new-library-save').click();
                    AjaxHelpers.expectNoRequests(requests);
                }
            });

            it('can cancel library creation', function() {
                $('.new-library-button').click();
                fillInLibraryFields('DemoX', 'DM101', 'Demo library');
                $('.new-library-cancel').click();
                expect($('.wrapper-create-library')).not.toHaveClass('is-shown');
                $('.wrapper-create-library form input[type=text]').each(function() {
                    expect($(this)).toHaveValue('');
                });
            });

            it('displays an error when saving a library fails', function() {
                var requests = AjaxHelpers.requests(this);
                $('.new-library-button').click();
                fillInLibraryFields('DemoX', 'DM101', 'Demo library');
                $('.new-library-save').click();
                AjaxHelpers.respondWithError(requests, 400, {
                    ErrMsg: 'error message'
                });
                expect($('.create-library .wrap-error')).toHaveClass('is-shown');
                expect($('#library_creation_error')).toContainText('error message');
                expect($('.new-library-save')).toHaveClass('is-disabled');
                expect($('.new-library-save')).toHaveAttr('aria-disabled', 'true');
            });

            it('can switch tabs', function() {
                var $courses_tab = $('.courses-tab'),
                    $libraraies_tab = $('.libraries-tab');

                // precondition check - courses tab is loaded by default
                expect($courses_tab).toHaveClass('active');
                expect($libraraies_tab).not.toHaveClass('active');

                $('#course-index-tabs .libraries-tab').click();  // switching to library tab
                expect($courses_tab).not.toHaveClass('active');
                expect($libraraies_tab).toHaveClass('active');

                $('#course-index-tabs .courses-tab').click(); // switching to course tab
                expect($courses_tab).toHaveClass('active');
                expect($libraraies_tab).not.toHaveClass('active');
            });

        });
        describe("Course listing page with auto key generator", function () {
            var mockIndexPageHTML = readFixtures('mock/mock-index-page-auto-key.underscore');

            var fillInFields = function (org, number, run, name) {
                $('.new-course-org').val(org);
                $('.new-course-number').val(number);
                $('.new-course-run').val(run);
                $('.new-course-name').val(name);
            };

            var fillInLibraryFields = function(org, number, name) {
                $('.new-library-org').val(org).keyup();
                $('.new-library-number').val(number).keyup();
                $('.new-library-name').val(name).keyup();
            };

            beforeEach(function () {
                ViewHelpers.installMockAnalytics();
                appendSetFixtures(mockIndexPageHTML);
                IndexUtils.onReady();
            });

            afterEach(function () {
                ViewHelpers.removeMockAnalytics();
                delete window.source_course_key;
            });

            it("saves new courses with auto key", function () {
                var requests = AjaxHelpers.requests(this);
                var redirectSpy = spyOn(ViewUtils, 'redirect');
                $('.new-course-button').click()
                AjaxHelpers.expectJsonRequest(requests, 'GET', '/organizations');
                AjaxHelpers.respondWithJson(requests, []);
                fillInFields('', '', '', 'Demo course');
                $('.new-course-save').click();
                AjaxHelpers.expectJsonRequest(requests, 'POST', '/course/', {
                    org: '',
                    number: '',
                    run: '',
                    display_name: 'Demo course'
                });
                AjaxHelpers.respondWithJson(requests, {
                    url: 'dummy_test_url'
                });
                expect(redirectSpy).toHaveBeenCalledWith('dummy_test_url');
            });

            it("displays an error when a required field (name) is blank", function () {
                var requests = AjaxHelpers.requests(this);
                var requests_count = requests.length;
                $('.new-course-button').click();
                var values = ('DemoX', 'DM101', '2014', '');
                // Try to submit some filled fields when the name is empty and ensure the form won't submit
                for (var i=0; i<values.length;i++) {
                    var values_with_blank = values.slice();
                    values_with_blank[i] = '';
                    fillInFields.apply(this, values_with_blank);
                    expect($('.create-course li.field.text input').parent()).toHaveClass('error');
                    expect($('.new-course-save')).toHaveClass('is-disabled');
                    expect($('.new-course-save')).toHaveAttr('aria-disabled', 'true');
                    $('.new-course-save').click();
                    expect(requests.length).toEqual(requests_count); // Expect no new requests
                }
            });

            it("disables course creation button during request and restores label on error", function(){
                var requests = AjaxHelpers.requests(this);
                var initial_label = $('.new-course-save').val();
                $('.new-course-button').click();
                AjaxHelpers.expectJsonRequest(requests, 'GET', '/organizations');
                AjaxHelpers.respondWithJson(requests, []);
                fillInFields('', '', '', 'Demo course');
                $('.new-course-save').click();
                expect($('.new-course-save')).toHaveClass('is-disabled');
                expect($('.new-course-save')).toHaveAttr('aria-disabled', 'true');
                expect($('.new-course-save').val()).not.toEqual(initial_label);
                AjaxHelpers.respondWithJson(requests, {
                    ErrMsg: 'error message'
                });
                expect($('.new-course-save')).toHaveClass('is-disabled');
                expect($('.new-course-save')).toHaveAttr('aria-disabled', 'true');
                expect($('.new-course-save').val()).toEqual(initial_label);
            });

            it("saves new libraries with auto key", function () {
                var requests = AjaxHelpers.requests(this);
                var redirectSpy = spyOn(ViewUtils, 'redirect');
                $('.new-library-button').click();
                fillInLibraryFields('', '', 'Demo library');
                $('.new-library-save').click();
                AjaxHelpers.expectJsonRequest(requests, 'POST', '/library/', {
                    org: '',
                    number: '',
                    display_name: 'Demo library'
                });
                AjaxHelpers.respondWithJson(requests, {
                    url: 'dummy_test_url'
                });
                expect(redirectSpy).toHaveBeenCalledWith('dummy_test_url');
            });

            it("displays an error when a required field (name) is blank", function () {
                var requests = AjaxHelpers.requests(this);
                var requests_count = requests.length;
                $('.new-library-button').click();
                var values = ['DemoX', 'DM101', ''];
                // Try to submit some filled fields when the name is empty and ensure the form won't submit
                for (var i=0; i<values.length;i++) {
                    var values_with_blank = values.slice();
                    values_with_blank[i] = '';
                    fillInLibraryFields.apply(this, values_with_blank);
                    expect($('.create-library li.field.text input').parent()).toHaveClass('error');
                    expect($('.new-library-save')).toHaveClass('is-disabled');
                    expect($('.new-library-save')).toHaveAttr('aria-disabled', 'true');
                    $('.new-library-save').click();
                    expect(requests.length).toEqual(requests_count); // Expect no new requests
                }
            });

            it("disables library creation button during request and restores label on error", function(){
                var requests = AjaxHelpers.requests(this);
                var initial_label = $('.new-library-save').val();
                $('.new-library-button').click();
                fillInLibraryFields('', '', 'Demo library');
                $('.new-library-save').click();

                expect($('.new-library-save')).toHaveClass('is-disabled');
                expect($('.new-library-save')).toHaveAttr('aria-disabled', 'true');
                expect($('.new-library-save').val()).not.toEqual(initial_label);
                AjaxHelpers.respondWithError(requests, 400, {
                    ErrMsg: 'error message'
                });
                expect($('.new-library-save')).toHaveClass('is-disabled');
                expect($('.new-library-save')).toHaveAttr('aria-disabled', 'true');
                expect($('.new-library-save').val()).toEqual(initial_label);
            });
        });
        describe("Course listing page visibility control", function(){
            var mockVisibilityControl = readFixtures('mock/mock-course-action-visible.underscore');

            beforeEach(function () {
                appendSetFixtures(mockVisibilityControl);
                IndexUtils.onReady();
            });

            it("saves visibility:visible setting", function(){
                var requests = AjaxHelpers.requests(this);
                $('.toggle-checkbox').click()
                AjaxHelpers.expectJsonRequest(requests, 'POST', '/visibility_setting_url/', {
                    value: 'both',
                });
            });

            it("saves visibility:hidden setting", function(){
                // change checkbox state without firing "click" event
                $('.toggle-checkbox').prop('checked', false)

                var requests = AjaxHelpers.requests(this);
                $('.toggle-checkbox').click()
                AjaxHelpers.expectJsonRequest(requests, 'POST', '/visibility_setting_url/', {
                    value: 'about',
                });
            });
        });
    });
