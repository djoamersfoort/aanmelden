// script for report page

$(document).ready(function() {
    $("input").click(function(e) {
        window.location.replace('/register/seen/' + $(this).attr('id') + '/' + $(this).is(":checked"));
    });
});
