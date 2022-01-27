function mk_Course () {
  $("#form").append("<select id='Course' name='Course'>\
    <option disabled selected value>-- course --</option>\
    <option value='MyCourse'>C programming</option>\
    <option value='AnotherCourse'>Processing programming</option>\
    </select>");
  $("#Course").change(on_Course);
}

function on_Course () {
  $("#Course").nextAll().remove();
  jQuery.globalEval("mk_Course_" + $("#Course").val() + "();");
}

function mk_Course_MyCourse () {
  $("#form").append("<select id='MyCourse' name='MyCourse'>\
    <option disabled selected value>-- exercise --</option>\
    <option value='Test'>factorial</option>\
    </select>");
  $("#MyCourse").change(on_Course_MyCourse);
}

function on_Course_MyCourse () {
  $("#MyCourse").nextAll().remove();
  jQuery.globalEval("mk_Course_MyCourse_" + $("#MyCourse").val() + "();");
}

function mk_Course_MyCourse_Test () {
  $("#form").append("<input type='hidden' name='path' value='scripts/cprog/fact.bad'>",
    "<label for='source'>Source file(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h,.zip'>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AnotherCourse () {
  $("#form").append("<select id='AnotherCourse' name='AnotherCourse'>\
    <option disabled selected value>-- exercise --</option>\
    <option value='Test'>hello world</option>\
    </select>");
  $("#AnotherCourse").change(on_Course_AnotherCourse);
}

function on_Course_AnotherCourse () {
  $("#AnotherCourse").nextAll().remove();
  jQuery.globalEval("mk_Course_AnotherCourse_" + $("#AnotherCourse").val() + "();");
}

function mk_Course_AnotherCourse_Test () {
  $("#form").append("<input type='hidden' name='path' value='scripts/processing/hello.bad'>",
    "<label for='source'>Source file(s)</label>",
    "<input type='file' name='source' multiple='' accept='.pde'>",
    "<input type='submit' value='Submit'>");
}

$(document).ready(mk_Course);
