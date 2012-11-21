"""Primary web entry point for the customized intranet implementation.

This eliminates a lot of the complexity based on the assumption that access to
this site is controlled via a domain level browser authentication. No other
operation requires a password from the user. Note however that this layer
wraps around some of the password authentication requirements of mailman by
using some defaults, and relieves the user of such headaches. So this layer
does not chnage mailman behaviour in any way.
"""

# No lock needed in this script, because we don't change data.

import Cookie
from   datetime import datetime
import os
import re
import string

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman import i18n
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog

from Mailman.tornado import template

# Set up i18n
_ = i18n._
i18n.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)

def auto_version (resource):
    """Intended to be invoked from inside tornado templates, given a resource
    names such as /static/ctl.js this will return something like
    /static/ctl.201211010141551..css to version it. For this to work we need a
    working url rewrite rule in apache or equivalent to strip out the
    timestamp.

    It is assumed that static resources that need to be versioned are
    available at the first level inside the PREFIX Directory"""

    absname   = os.path.abspath(os.path.join(mm_cfg.VAR_PREFIX, resource[1:]))
    d         = datetime.fromtimestamp(os.path.getmtime(absname))
    timestamp = d.strftime("%Y%m%d%H%M%S")

    res = re.match('(.*\.)([a-zA-Z]*$)', resource)
    return ''.join([res.group(1), timestamp, '.', res.group(2)])


def get_curr_user ():
    """Extracts the Cleartrip userid from the cookie. This cookie is set by
    any authenticated Cleartrip site - and as a result the site where this
    list server will be hosted."""

    _curr_user = None
    try:
        cookie = Cookie.SimpleCookie(os.environ["HTTP_COOKIE"])
        _curr_user = string.replace(cookie["userid"].value, '%40', '@')
    except Cookie.CookieError, e:
        _curr_user = "Take a hike, Mike - C"
    except  KeyError, e:
        _curr_user = "Take a hike, Mike - K"

    return _curr_user


class Action:
    def __init__ (self, templ):
        self._templ     = templ
        self._curr_user = get_curr_user()
        self._templ_dir = "../templates/en"
        self.kwargs     = {'auto_version' : auto_version,
                           'curr_user'    : self.curr_user,
                           }

    @property
    def templ_dir (self): 
        return self._templ_dir;

    @property
    def templ (self): 
        return self._templ;

    @property
    def curr_user (self):
        return self._curr_user

    def kwargs_add (self, key, val):
        self.kwargs.update({key : val})

    def render (self):
        loader = template.Loader(self.templ_dir)
        print 'Content-Type: text/html; charset=%s\n' % 'us-ascii'
        print
        print loader.load(self.templ).generate(**self.kwargs)

    def handler (self):
        """To be overridden, but we have a simple default, regardless"""
        self.render()


class Home(Action):
    def __init__ (self):
        Action.__init__(self, "ctl-base.html")


class View(Action):
    def __init__ (self):
        Action.__init__(self, "ctl-view.html")
    
    def handler (self):
        listnames = Utils.list_names()
        listnames.sort()
    
        lists = []
        for name in listnames:
            mlist   = MailList.MailList(name, lock=0)
            members = mlist.getRegularMemberKeys()
            subscribed = True if self.curr_user in members else False
    
            lists.append({'script_url'  : mlist.GetScriptURL('listinfo'),
                          'real_name'   : mlist.real_name,
                          'description' : Utils.websafe(mlist.description),
                          'subscribed'  : subscribed,
                          'owners'      : ', '.join(mlist.owner),
                          'owner-email' : mlist.GetOwnerEmail(),
                          })
    
        self.kwargs_add('lists', lists)
        self.render()


class Create(Action):
    def __init__ (self):
        Action.__init__(self, "ctl-create.html")


class Admin(Action):
    def __init__ (self):
        Action.__init__(self, "ctl-admin.html")


def main ():
    parts = Utils.GetPathPieces()
    if not parts:
        Home().handler()
        return

    action = parts[0].lower()
    if action == 'view':
        View().handler()
    elif action == 'create':
        Create().handler()
    elif action == 'admin':
        Admin().handler()
    else:
        ## FIXME: This should throw a 404.
        Home().handler()


if __name__ == "__main__":
    main()
