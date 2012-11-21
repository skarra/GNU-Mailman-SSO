//
// Created       : Tue Nov 20 14:02:01 IST 2012
// Last Modified : Wed Nov 21 16:13:47 IST 2012
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
    });
}

//
// ctl-create specific handlers
//

function addHandlersCreate () {
}

//
// ctl-admin specific handlers
//

function addHandlersAdmin () {
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
