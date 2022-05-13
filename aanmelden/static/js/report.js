// script for report page

$(document).ready(function() {
    $("input").click(function(e) {
        let url = '/register/seen/' + $(this).attr('id') + '/' + $(this).is(":checked");
        fetch(url, { method: 'GET' })
            .catch(errorMsg => { console.log(errorMsg); });
    });
});
