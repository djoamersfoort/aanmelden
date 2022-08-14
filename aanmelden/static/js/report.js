// script for report page

$(document).ready(function() {
    let skipReload = false;

    $("input").click(function(e) {
        let url = '/register/seen/' + $(this).attr('id') + '/' + $(this).is(":checked");
        skipReload = true;
        fetch(url, { method: 'GET' })
            .catch(errorMsg => { console.log(errorMsg); });
    });

    const socket = io();
    socket.on('update_report_page', () => {
        if (!skipReload) location.reload();
        skipReload = false;
    });
});
