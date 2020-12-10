function mk_Course () {
  $("#form").append("<select id='Course' name='Course'>\
    <option disabled selected value>-- course --</option>\
    <option value='MyCourse'>C programming</option>\
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
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Submit'>");
}

$(document).ready(mk_Course);
