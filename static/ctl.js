//
// Created       : Tue Nov 20 14:02:01 IST 2012
// Last Modified : Tue Nov 27 21:09:23 IST 2012
//
// Copyright (C) 2012, Sriram Karra <karra.etc@gmail.com>
// All Rights Reserved

var navElemId;
var view_lists_table;

//
// ctl-base specific handlers
//

function addHandlersBase () {
}

//
// ctl-view specific handlers
//

function addHandlersView () {
    view_lists_table = $("#view_lists_table").dataTable({
	"aoColumns": [
            { "sWidth": "30%", "sClass": "left" },
            { "sWidth": "53%", "sClass": "left"},
            { "sWidth": "17%", "sClass": "center"}],
    });
}

//
// ctl-create specific handlers
//

var member_cnt;

function addHandlersCreate () {
    var t0 = '<br/><input type="text" ';
    var t1;
    var t2 = ' placeholder="Enter a valid email address" />';
    var d = 'lc_member_';

    member_cnt = 2;

    $("#lc_member_add_new").click(function() {
	t1 = ' id="' + d + member_cnt + '" name="' + d + member_cnt + '"';
	var t = t0 + t1 + t2
	$("#lc_members").append(t);
	member_cnt += 1;
    });
}

//
// ctl-admin specific handlers
//

function addHandlersAdmin () {
}

//
// ctl-error specific handlers
//

function addHandlersError () {
}

function highlightNavElem () {
    var url = window.location.pathname;
    var filename = url.replace(/^.*[\\\/]/, '');
    var elemId;

    console.log('highlightNavElem: filename is: ' + filename);

    if (filename == "view") {
	navElemId = "#navView";
    } else if (filename == "create") {
	navElemId = "#navCreate";
    } else if (filename == "admin") {
	navElemId = "#navAdmin";
    } else if (filename == "base") {
	navElemId = "#navHome";
    } else if (filename == "error") {
	navElemId = "#navError";
    } else {
	console.log('highlightNavElem: Unknown web page: ' + url);
	navElemId = "#navHome";
    }

    $(navElemId + " a").css({"font" : "verdana", "color" : "blue"});
}

function addHandlers () {
    if (navElemId == "#navView") {
	addHandlersView();
    } else if (navElemId == "#navCreate") {
	addHandlersCreate();
    } else if (navElemId == "#navAdmin") {
	addHandlersAdmin();
    } else if (navElemId == "#navError") {
	addHandlersError();
    } else {
	addHandlersBase();
    }
}

function onLoad () {
    console.log('jQuery.onLoad(): Howdy dowdy World!');

    //
    // Set up an error handler
    //

    window.onerror = function (em, url, ln) {
        alert(em + ", " + url + ", " + ln);
        return false;
    }

    // 
    // Highlight the nav element corresponding to the current html file
    //

    highlightNavElem();

    // 
    // Disable the div containing the home tab contents if not in home
    //

    if (navElemId != "#navHome") {
	$("#section_home").css({display : "none"});
    }

    //
    // Set up all the other handlers now
    //

    addHandlers();
}

jQuery(onLoad);
