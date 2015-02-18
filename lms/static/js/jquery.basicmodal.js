/* basicModal plugin
 * @author <a href="mailto:liubov@lektorium.tv">Liubov Fomicheva</a>
 * @requires jQuery 1.6+
 *
 * Copyright 2014, Liubov Fomicheva
 *
 * Based on leanModal plugin implementation, but handles close events and
 * permits multiple invocation (not creating additional overlay elements, etc)
 *
 * Provides 3 methods:
 *     basicModal('open') - open modal;
 *     basicModal('close') - just close modal with executing only onClose handler;
 *     basicModal('userClose') - imitate user closing modal.
 *
 * Options:
 *     autoOpen - specifies wheter modal should be opened instantly (default false),
 *     top - position parameter (default 100),
 *     overlay - overlay opacity (default 0.5),
 *     mainPage - main page element,
 *     closeButton - identifier of built-in close button (default null),
 *     onOpen - handler fired after modal is opened,
 *     onClose - handler for closing by user or automatically (default null),
 *     onUserClose - handler for closing by user only, fired before onClose (default null),
 */
(function($){
var focusableElementsSelector = "a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, object, embed, *[tabindex], *[contenteditable]";
var methods = {
    init: function(item, options){
        item.data('basicmodal', {
            open: function(){
                methods.open(item, options);
            },
            close: function(){
                methods.close(item, options);
            },
            userClose: function(){
                methods.userClose(item, options);
            }
        });
        item.find(options.closeButton).add($('#basicmodal-overlay')).click(function(){
            item.basicModal('userClose');
        });

        item.css({
            'position' : 'absolute',
            'opacity' : 0,
            'z-index': parseInt($('#basicmodal-overlay').css('z-index')) + 1 || 101,
            'left' : 50 + '%',
            'margin-left' : -(item.outerWidth()/2) + "px",
            'top' : options.top + "px"
        });
        if (options.autoOpen)
            item.basicModal('open');
    },
    open: function(item, options){
        $('#basicmodal-overlay')
         .css({'display': 'block', opacity: 0})
         .fadeTo(200, options.overlay);

        item
         .css('display', 'block')
         .fadeTo(200, 1);

        if (options.onOpen)
            options.onOpen(item);

        methods.makeAccessible(item, options);
        options.mainPage.attr('aria-hidden', 'true');
        item.attr('aria-hidden', 'false');

        $('body').on('keydown', methods.closeOnEsc);
    },
    close: function(item, options){
        $('#basicmodal-overlay').fadeOut(200);
        item.css('display', 'none');
        options.mainPage.attr('aria-hidden', 'false');
        item.attr('aria-hidden', 'true');
        if (options.onClose)
            options.onClose(item);
    },
    userClose: function(item, options){
        if (options.onUserClose)
            options.onUserClose(item);
        methods.close(item, options);
    },
    closeOnEsc: function(e){
        var keyCode = e.keyCode || e.which;
        if (keyCode == 27) {
            $('.basicModal').basicModal('userClose');
            $(this).off('keydown', methods.closeOnEsc);
            return false;
        }
    },
    makeAccessible: function(item, options){
        if (item.data('basicmodal').accessible) return;

        var focusableElements = item.find(focusableElementsSelector).not(options.closeButton).filter(':visible');
        var last = (focusableElements.length) ? focusableElements.last() : options.closeButton;

        // toggle focus between last visible control and close button
        last.on('keydown', function(e){
            var keyCode = e.keyCode || e.which;
            if (!e.shiftKey && keyCode == 9){
                e.preventDefault();
                if (options.closeButton)
                    options.closeButton.focus();
                else
                    focusableElements.first().focus();
            }
        });
        var first = options.closeButton || focusableElements.first();
        first.on('keydown', function(e){
            var keyCode = e.keyCode || e.which;
            if (e.shiftKey && keyCode == 9){
                e.preventDefault();
                last.focus();
            }
        });
        // focus on first focusable element
        if (focusableElements.length)
            focusableElements.first().focus();
        else if (options.closeButton)
            options.closeButton.focus();

        item.data('basicmodal').accessible = true;
    }
};

$.fn.extend({
    basicModal: function(){
        var defaults = {
            autoOpen: false,
            top: 100,
            overlay: 0.5,
            mainPage: $('body'),
            closeButton: null,
            onOpen: null,
            onClose: null, // handler for closing by user or automatically
            onUserClose: null // handler for closing by user
        }
        var args = arguments;
        var options = $.extend(defaults, (typeof(args[0])=='object') ? args[0] : {});

        var overlay = $('#basicmodal-overlay');
        if (! overlay.length)
            overlay = $('<div id="basicmodal-overlay"></div>')
                .appendTo('body')
                .click(function(){
                $('.basicModal').basicModal('close');
            });

        return this.each(function(){
            var _this = $(this).addClass('basicModal');
            if (typeof(args[0])=='object' || ! args[0]){
                methods.init(_this, options);
                return;
            } else if (! _this.data('basicmodal')){
                throw new Error('Trying to work with basicmodal before initialization!')
            }

            switch(args[0]){
                case 'open':
                    _this.data('basicmodal').open();
                    break;
                case 'close':
                    _this.data('basicmodal').close();
                    break;
                case 'userClose':
                    _this.data('basicmodal').userClose();
                    break;
            }
        });
    }
});
})(jQuery);
