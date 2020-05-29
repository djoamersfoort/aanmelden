// script for main page

$(document).ready(function() {
    $(".register").click(function(e) {

        if(!localStorage.verifiedEmailAddress) {
            $(".verify-email").modal("show");
            return false;
        }
    });

    $(".verify-btn-confirm").click(function(e) {
        localStorage.verifiedEmailAddress = true;
        $(".verify-email").modal("hide");
    });

    $(".verify-btn-deny").click(function(e) {
        $(".verify-email").modal("hide");
        $(".change-email").modal("show");
    });

    if(new Date() < new Date("2020-06-02") && !sessionStorage.hidePreAlert) {
      $(".pre-alert").show();
    }

    $(".pre-alert button").click(function() {
      sessionStorage.hidePreAlert = true;
    });
});
