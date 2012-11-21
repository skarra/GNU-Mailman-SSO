//
// Created       : Tue Nov 20 14:02:01 IST 2012
// Last Modified : Wed Nov 21 11:32:34 IST 2012
//
// Copyright (C) 2012, Sriram Karra <karra.etc@gmail.com>
// All Rights Reserved

var navElemId;

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
