function mk_Course () {
  $("#form").append("<select id='Course' name='Course'>\
    <option disabled selected value>-- course --</option>\
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
    <option disabled selected value>-- groupe --</option>\
    <option value='L1_DLBI_G0'>Bio-Info / Groupe 0</option>\
    <option value='L1_DLM_G1'>Maths / Groupe 1</option>\
    <option value='L1_DLM_G2'>Maths / Groupe 2</option>\
    <option value='L1_DLM_G3'>Maths / Groupe 3</option>\
    <option value='L1_DLME'>Maths-Eco</option>\
    <option value='L1_DLSDV'>SdV</option>\
    <option value='L1_info_G1'>Info / Groupe 1</option>\
    <option value='L1_info_G2'>Info / Groupe 2</option>\
    <option value='L1_info_G3'>Info / Groupe 3</option>\
    <option value='L1_info_G4'>Info / Groupe 4</option>\
    <option value='L1_info_G5'>Info / Groupe 5</option>\
    </select>");
  $("#AlgoL1").change(on_Course_AlgoL1);
}

function on_Course_AlgoL1 () {
  $("#AlgoL1").nextAll().remove();
  jQuery.globalEval("mk_Course_AlgoL1_" + $("#AlgoL1").val() + "();");
}

function mk_Course_AlgoL1_L1_DLBI_G0 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AlgoL1_L1_DLM_G1 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AlgoL1_L1_DLM_G2 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AlgoL1_L1_DLM_G3 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AlgoL1_L1_DLME () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AlgoL1_L1_DLSDV () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AlgoL1_L1_info_G1 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AlgoL1_L1_info_G2 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AlgoL1_L1_info_G3 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AlgoL1_L1_info_G4 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_AlgoL1_L1_info_G5 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<select name='exercise'><option value='Test'>factorial</option><option value='Exo1'>Exercise 1</option><option value='Exo2'>Exercise 2</option><option value='Exo3'>Exercise 3</option><option value='Exo4'>Exercise 4</option><option value='Exo5'>Exercise 5</option><option value='Exo6'>Exercise 6</option><option value='Exo7'>Exercise 7</option><option value='Exo8'>Exercise 8</option><option value='Exo9'>Exercise 9</option><option value='Exo10'>Exercise 10</option><option value='Exo11'>Exercise 11</option><option value='Exo12'>Exercise 12</option><option value='Exo13'>Exercise 13</option></select>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_UnixL2 () {
  $("#form").append("<select id='UnixL2' name='UnixL2'>\
    <option disabled selected value>-- groupe --</option>\
    <option value='G1'>Groupe 1</option>\
    <option value='G2'>Groupe 2</option>\
    <option value='G3'>Groupe 3</option>\
    </select>");
  $("#UnixL2").change(on_Course_UnixL2);
}

function on_Course_UnixL2 () {
  $("#UnixL2").nextAll().remove();
  jQuery.globalEval("mk_Course_UnixL2_" + $("#UnixL2").val() + "();");
}

function mk_Course_UnixL2_G1 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_UnixL2_G2 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<input type='submit' value='Submit'>");
}

function mk_Course_UnixL2_G3 () {
  $("#form").append("<input type='hidden' name='path' value=''>",
    "<input type='submit' value='Submit'>");
}

$(document).ready(mk_Course);
