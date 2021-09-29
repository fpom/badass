$(function () {
    var userList = new List("users", {
        valueNames: ["firstname",
                     "lastname",
                     "email",
                     "group",
                     "roles",
                     "studentid",
                     "activated"]
    });
    $(".search-firstname").on("keyup", function() {
        userList.search($(this).val(), ["firstname"]);
    });
    $(".search-lastname").on("keyup", function() {
        userList.search($(this).val(), ["lastname"]);
    });
    $(".search-email").on("keyup", function() {
        userList.search($(this).val(), ["email"]);
    });
    $(".search-group").on("keyup", function() {
        userList.search($(this).val(), ["group"]);
    });
    $(".search-roles").on("keyup", function() {
        userList.search($(this).val(), ["roles"]);
    });
    $(".search-studentid").on("keyup", function() {
        userList.search($(this).val(), ["studentid"]);
    });
    $(".search-activated").on("keyup", function() {
        userList.search($(this).val(), ["activated"]);
    });
});
