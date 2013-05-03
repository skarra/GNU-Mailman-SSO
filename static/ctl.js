//
// Created       : Tue Nov 20 14:02:01 IST 2012
// Last Modified : Fri May 03 23:39:30 IST 2013
//
// Copyright (C) 2012, Sriram Karra <karra.etc@gmail.com>
// All Rights Reserved

var navElemId = null;
var view_lists_table;
var lists_admin_table;

//
// ctl-base specific handlers
//

function addHandlersBase () {
}

//
// ctl-view specific handlers
//

function subActions () {
    var aPos  = view_lists_table.fnGetPosition(this);
    var aData = view_lists_table.fnGetData(aPos[0]);
    var list   = aData[0];
    var action_res = aData[4].toLowerCase().match(/>(.*)</);
    var action = action_res[1];

    console.log('Will ' + action + ' from/to ' + list);

    $.post("/mailman/ctl/subscribe",
	   {'action' : action,
	    'list'   : list},
	   function(response) {
	       console.log('Response: ' + response);
	       var stat = response['notice_success'];
	       var news;
	       if (stat) {
		   // We could just toggle the subscribed state, but
		   // updaging contents from here is generating
		   // additional click evenst. Quite a pain. Let's
		   // just redirect for now, which will re-render the
		   // page. FIXME: for better performance

		   window.location = '/mailman/ctl/view';

		   // if (action == 'subscribe') {
		   //     news = 'Unsubscribe';
		   // } else {
		   //     news = 'Subscribe'
		   // }
		   // view_lists_table.fnUpdate(news, aPos[0], 2);
	       }
	       console.log('Text   : ' + response['notice_text']);
	   }
	  ).error(function(xhr, status, error) {
	      console.log("Status: " + status + "; Error: " + error);
	      var d = $.parseJSON(xhr.responseText);
	      console.log('parsed data: ' + d['error']);
	      $("#sub_result").html('<pre>' + d['error'] + '</pre>');
	  });
}

function viewActions () {
    var aPos  = view_lists_table.fnGetPosition(this);
    var aData = view_lists_table.fnGetData(aPos[0]);
    var list   = aData[0];

    window.location = '/mailman/ctl/view/' + list + '#vl';
}

function addHandlersView () {
    view_lists_table = $("#view_lists_table").dataTable({
	"aoColumns": [
            { "sWidth": "15%", "sClass": "left" },
            { "sWidth": "53%", "sClass": "left"},
            { "sWidth": "10%", "sClass": "left"},
            { "sWidth": "5%", "sClass": "center"},
            { "sWidth": "17%", "sClass": "center"}],

	"fnDrawCallback" : function(oSettings) {
	    $("#view_lists_table tbody td.subscribe").click(subActions);
	    $("#view_lists_table tbody td.clickable.view").click(viewActions);
	}
    });
}

//
// ctl-listadmin specific handlers
//

var member_cnt;
var owner_cnt;

function isValidEmail (em) {
    var reg = /^([A-Za-z0-9_\-\.])+\@([A-Za-z0-9_\-\.])+\.([A-Za-z]{2,4})$/;
    
    if (reg.test(em) == false) {
        return false;
    }

    return true;
}

function validateNewListDetails () {
    var msg = "";
    var lc_name = $("#lc_name").val();
    var lc_desc = $("#lc_desc").val();

    try {
	if (lc_name.trim() == "") {
	    msg += "* List name cannnot be empty\n";
	}

	if (lc_name.toLowerCase().trim() == "new") {
	    msg += "* Lists cannot be named 'new'. Please try another name\n";
	}

	if (lc_desc.trim() == "") {
	    msg += "* Brief description cannot be empty.\n";
	}

	var empty = true;
	$(".lc_members").each(function(x, domEle) {
	    if ($(domEle).val().trim() != "") {
		var em = $(domEle).val().trim();
		console.log('Processing email address: ' + em);
		if (isValidEmail(em)) {
		    empty = false;
		}
	    }
	});

	if (empty) {
	    msg += "* At least one valid email address needs to be provided.\n"
	}
    } catch (e) {
	alert(e);
	return false;
    }

    if (msg != "") {
	alert("Cannot create list due to following error(s): \n" + msg);
	return false;
    }

    return true;
}

function listsAdminActions () {
    var aPos  = lists_admin_table.fnGetPosition(this);
    var aData = lists_admin_table.fnGetData(aPos[0]);
    var list   = aData[0];

    window.location = '/mailman/ctl/listadmin/' + list + '#action';
}

function addHandlersListAdmin () {
    var t0 = '<input type="text" class="lc_members"';
    var t1;
    var t2 = ' placeholder="Enter a valid plain email address" /> <br/>';
    var d = 'lc_member_';

    console.log('Initializing handlers for the list admin template');
    member_cnt = $(".lc_members").length;

    $("#lc_member_add_new").click(function() {
	t1 = ' id="' + d + member_cnt + '" name="' + d + member_cnt + '"';
	var t = t0 + t1 + t2
	$("#lc_members").append(t);
	member_cnt += 1;
    });

    owner_cnt = $(".lc_owners").length;

    var ot0 = '<input type="text" class="lc_owners"';
    var ot1;
    var ot2 = ' placeholder="Enter a valid plain email address" /> <br/>';
    var od = 'lc_owner_';

    $("#lc_owner_add_new").click(function() {
	ot1 = ' id="' + od + owner_cnt + '" name="' + od + owner_cnt + '"';
	var ot = ot0 + ot1 + ot2
	$("#lc_owners").append(ot);
	owner_cnt += 1;
    });

    $("#lc_form").submit(validateNewListDetails);

    lists_admin_table = $("#lists_admin_table").dataTable({
 	"aoColumns": [
            { "sWidth": "30%", "sClass": "left" },
            { "sWidth": "60%", "sClass": "left"},
            { "sWidth": "10%", "sClass": "center"}
	],
 
 	"fnDrawCallback" : function(oSettings) {
 	    $("#lists_admin_table tbody td.clickable.admin").click(listsAdminActions);
 	}
    });

    $("#lc_create_action").click(function() {
	window.location = '/mailman/ctl/listadmin/new#action';
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

    var reg;
    var actions = ["Home", "View", "ListAdmin", "SiteAdmin", "Error"];
    for (var i=0; i < actions.length; i++) {
	action   = actions[i];
	action_l = action.toLowerCase();
	reg = new RegExp("\\/" + action_l);

	if (reg.test(url) == true) {
	    navElemId = "#nav" + action;
	}
    }

    if (navElemId == null) {
	console.log('NavElem: Unknown web page: ' + url);
	navElemId = "#navHome";
    }

    console.log('navElemId: ' + navElemId);

    $(navElemId).css({"background-color" : "#3c63a9"});
}

function addHandlers () {

    $("#navHome").click(function() { window.location = '/mailman/ctl/home';});
    $("#navView").click(function() { window.location = '/mailman/ctl/view';});
    $("#navListAdmin").click(function() { window.location = '/mailman/ctl/listadmin';});
    $("#navSiteAdmin").click(function() { window.location = '/mailman/ctl/siteadmin';});

    if (navElemId == "#navView") {
	addHandlersView();
    } else if (navElemId == "#navListAdmin") {
	addHandlersListAdmin();
    } else if (navElemId == "#navSiteAdmin") {
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
