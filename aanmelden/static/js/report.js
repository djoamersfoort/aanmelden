// script for report page

$(document).ready(function() {
    $(".form-check-input").click(function(e) {
        window.location.replace('/register/seen/' + $(this).attr('id') + '/' + $(this).is(":checked"));
    });
});
