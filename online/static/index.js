function mk_Course () {
  $("#form").append("<select id='Course' name='Course'>\
    <option disabled selected value>-- cours --</option>\
    <option value='AlgoL1'>L1 / Algorithmique en C</option>\
    <option value='UnixL2'>L2 / Programmation Unix</option>\
    </select>");
  $("#Course").change(on_Course);
}

function on_Course () {
  $("#Course").nextAll().remove();
  jQuery.globalEval("mk_Course_" + $("#Course").val() + "();");
}

function mk_Course_AlgoL1 () {
  $("#form").append("<select id='AlgoL1' name='AlgoL1'>\
    <option disabled selected value>-- exercice --</option>\
    <option value='Exo1'>Exercice 1</option>\
    <option value='Exo2'>Exercice 2</option>\
    <option value='Exo3'>Exercice 3</option>\
    <option value='Exo4'>Exercice 4</option>\
    <option value='Exo5'>Exercice 5</option>\
    <option value='Exo6'>Exercice 6</option>\
    <option value='Exo7'>Exercice 7</option>\
    <option value='Exo8'>Exercice 8</option>\
    <option value='Exo9'>Exercice 9</option>\
    <option value='Exo10'>Exercice 10</option>\
    <option value='Exo11'>Exercice 11</option>\
    <option value='Exo12'>Exercice 12</option>\
    <option value='Exo13'>Exercice 13</option>\
    </select>");
  $("#AlgoL1").change(on_Course_AlgoL1);
}

function on_Course_AlgoL1 () {
  $("#AlgoL1").nextAll().remove();
  jQuery.globalEval("mk_Course_AlgoL1_" + $("#AlgoL1").val() + "();");
}

function mk_Course_AlgoL1_Exo1 () {
  $("#form").append("<select id='Exo1' name='Exo1'>\
    <option disabled selected value>-- question --</option>\
    <option value='Q1'>hello.c du cours</option>\
    <option value='Q2'>hello.c sans #include</option>\
    <option value='Q3'>helloname.c du cours</option>\
    <option value='Q4'>helloname.c sans free</option>\
    </select>");
  $("#Exo1").change(on_Course_AlgoL1_Exo1);
}

function on_Course_AlgoL1_Exo1 () {
  $("#Exo1").nextAll().remove();
  jQuery.globalEval("mk_Course_AlgoL1_Exo1_" + $("#Exo1").val() + "();");
}

function mk_Course_AlgoL1_Exo1_Q1 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo01-1.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo1_Q2 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo01-2.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo1_Q3 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo01-3.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo1_Q4 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo01-4.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo2 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo02.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo3 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo03.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo4 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo04.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo5 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo05.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo6 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo06.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo7 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo07.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo8 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo08.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo9 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo09.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo10 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo10.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo11 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo11.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo12 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo12.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo13 () {
  $("#form").append("<select id='Exo13' name='Exo13'>\
    <option disabled selected value>-- question --</option>\
    <option value='Q1'>Question 1</option>\
    <option value='Q2'>Question 2</option>\
    <option value='Q3'>Question 3</option>\
    <option value='Q4'>Question 4</option>\
    <option value='Q5'>Question 5</option>\
    </select>");
  $("#Exo13").change(on_Course_AlgoL1_Exo13);
}

function on_Course_AlgoL1_Exo13 () {
  $("#Exo13").nextAll().remove();
  jQuery.globalEval("mk_Course_AlgoL1_Exo13_" + $("#Exo13").val() + "();");
}

function mk_Course_AlgoL1_Exo13_Q1 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo13-1.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<label for='FUN'>Nom de la fonction</label>",
    "<input name='FUN' type='text'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo13_Q2 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo13-2.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<label for='FUN'>Nom de la fonction</label>",
    "<input name='FUN' type='text'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo13_Q3 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo13-3.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<label for='FUN'>Nom de la fonction</label>",
    "<input name='FUN' type='text'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo13_Q4 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo13-4.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<label for='FUN'>Nom de la fonction</label>",
    "<input name='FUN' type='text'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_AlgoL1_Exo13_Q5 () {
  $("#form").append("<input type='hidden' name='path' value='L1/algo/exo13-5.bad'>",
    "<label for='source'>Fichier(s) source(s)</label>",
    "<input type='file' name='source' multiple='' accept='.c,.h'>",
    "<label for='FUN'>Nom de la fonction</label>",
    "<input name='FUN' type='text'>",
    "<input type='submit' value='Envoyer'>");
}

function mk_Course_UnixL2 () {
  $("#form").append("<select id='UnixL2' name='UnixL2'>\
    <option disabled selected value>-- exercice --</option>\
    <option value='Exo1'>Exercice 1</option>\
    </select>");
  $("#UnixL2").change(on_Course_UnixL2);
}

function on_Course_UnixL2 () {
  $("#UnixL2").nextAll().remove();
  jQuery.globalEval("mk_Course_UnixL2_" + $("#UnixL2").val() + "();");
}

function mk_Course_UnixL2_Exo1 () {
  $("#form").append("<input type='hidden' name='path' value='L2/Unix/exo01.bad'>",
    "<label for='source'>Fichier(s) source</label>",
    "<input type='file' name='source' multiple=''>",
    "<input type='submit' value='Envoyer'>");
}

$(document).ready(mk_Course);
