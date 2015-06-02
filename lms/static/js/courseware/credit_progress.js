$(document).ready(function() {
    $('.detail-collapse').on('click', function() {
        $('.requirement-container').toggleClass('is-hidden');
        var el = $(this);
        el.find('.fa').toggleClass('fa-caret-down fa-caret-up');
        el.find('span').text(function(i, text){
          return text === gettext("More") ? gettext("Less") : gettext("More");
        });
    });

});
