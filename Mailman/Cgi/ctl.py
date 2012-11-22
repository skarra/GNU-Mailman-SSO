"""Primary web entry point for the customized intranet implementation.

This eliminates a lot of the complexity based on the assumption that access to
this site is controlled via a domain level browser authentication. No other
operation requires a password from the user. Note however that this layer
wraps around some of the password authentication requirements of mailman by
using some defaults, and relieves the user of such headaches. So this layer
does not chnage mailman behaviour in any way.
"""

# No lock needed in this script, because we don't change data.

import cgi
import Cookie
from   datetime import datetime
import os
import re
import signal
import string
import sys
import traceback

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Message
from Mailman import Errors
from Mailman import i18n
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog
from Mailman.Utils import sha_new

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
    cookie_key = mm_cfg.SSO_USER_COOKIE
    try:
        cookie = Cookie.SimpleCookie(os.environ["HTTP_COOKIE"])
        _curr_user = mm_cfg.sso_user_cookie_hook(cookie[cookie_key].value)
    except Cookie.CookieError, e:
        _curr_user = "Take a hike, Mike - C"
    except  KeyError, e:
        _curr_user = "Take a hike, Mike - K"

    return _curr_user


class Action:
    def __init__ (self, templ):
        self._cgidata   = cgi.FieldStorage()
        self._templ     = templ
        self._curr_user = get_curr_user()
        self._templ_dir = "../templates/en"
        self.kwargs     = {'auto_version' : auto_version,
                           'curr_user'    : self.curr_user,
                           }

    @property
    def cgidata (self): 
        return self._cgidata;

    def cgival (self, key):
        return self.cgidata.getvalue(key, '').strip()

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
        self._ln = self.cgival('lc_name')
        self._safelin = Utils.websafe(self.ln)
        self._pw = mm_cfg.SSO_STOCK_ADMIN_PWD
        self._owner = self.curr_user
        self._hn = Utils.get_domain()
        self._eh = mm_cfg.VIRTUAL_HOSTS.get(self.hn, mm_cfg.DEFAULT_EMAIL_HOST)
        self._ml = MailList.MailList()
        self._langs = [mm_cfg.DEFAULT_SERVER_LANGUAGE]
        self._moderate = mm_cfg.DEFAULT_DEFAULT_MEMBER_MODERATION
        self._notify = 1
        self._info = self.cgival('lc_info')
        self._desc = self.cgival('lc_desc')

    @property
    def ln (self):
        return self._ln

    @property
    def safeln (self):
        return self._safeln

    @property
    def pw (self):
        return self._pw

    @property
    def owner (self):
        return self._owner

    @property
    def hn (self):
        return self._hn

    @property
    def eh (self):
        return self._eh

    @property
    def ml (self):
        return self._ml

    @property
    def langs (self):
        return self._langs

    @property
    def moderate (self):
        return self._moderate

    @property
    def notify (self):
        return self._notify

    @property
    def info (self):
        return self._info

    @property
    def desc (self):
        return self._desc

    def sigterm_handler (self, signum, frame):
        # Make sure the list gets unlocked...
        self.ml.Unlock()
        # ...and ensure we exit, otherwise race conditions could cause us to
        # enter MailList.Save() while we're in the unlocked state, and that
        # could be bad!
        sys.exit(0)

    def errcheck (self):
        """Performs all error checks. Returns None is all's good. Otherwise
        returns a string with error message."""

        if not self.owner in mm_cfg.SSO_LIST_CREATE_AUTHIDS:
            return 'You are not authorized to creates lists on this server'

        if self.ln == '':
            return 'You forgot to enter the list name'

        if '@' in self.ln:
            return 'List name must not include "@": %s' % self.safeln

        if Utils.list_exists(self.ln):
            return 'List already exists: %s' % safe_ln

        if mm_cfg.VIRTUAL_HOST_OVERVIEW and \
          not mm_cfg.VIRTUAL_HOSTS.has_key(self.hn):
            safehostname = Utils.websafe(self.hn)
            return 'Unknown virtual host: %s' % safehostname

        return None

    def notify_owner (self):
        """Send an email to the owner of the list of successful creation."""

        siteowner = Utils.get_site_email(self.ml.host_name, 'owner')
        text = Utils.maketext(
            'newlist.txt',
            {'listname'    : self.ln,
             'password'    : '',
             'admin_url'   : self.ml.GetScriptURL('admin', absolute=1),
             'listinfo_url': self.ml.GetScriptURL('listinfo', absolute=1),
             'requestaddr' : self.ml.GetRequestEmail(),
             'siteowner'   : siteowner,
             }, mlist=self.ml)
        msg = Message.UserNotification(
            self.owner, siteowner, 'Your new mailing list: %s' % self.ln,
            text, self.ml.preferred_language)
        msg.send(self.ml)

    def request_create (self):
        """Creates a list (name taken from the CGI form value called lc_name).

        Returns None if the list was created successfully. Returns a string
        containing error message if list could not be created for whatever
        reason."""

        err = self.errcheck()
        if err:
            return err

        # We've got all the data we need, so go ahead and try to create the
        # list See admin.py for why we need to set up the signal handler.

        try:
            signal.signal(signal.SIGTERM, self.sigterm_handler)
            pwhex = sha_new(self.pw).hexdigest()

            # Guarantee that all newly created files have the proper permission.
            # proper group ownership should be assured by the autoconf script
            # enforcing that all directories have the group sticky bit set
            oldmask = os.umask(002)
            try:
                try:
                    self.ml.Create(self.ln, self.owner, pwhex, self.langs,
                                   self.eh, urlhost=self.hn)
                finally:
                    os.umask(oldmask)
            except Errors.EmailAddressError, e:
                if e.args:
                    s = Utils.websafe(e.args[0])
                else:
                    s = Utils.websafe(owner)

                return 'Bad owner email address: %s' % s
            except Errors.MMListAlreadyExistsError:
                return 'List already exists: %s' % self.ln
            except Errors.BadListNameError, e:
                if e.args:
                    s = Utils.websafe(e.args[0])
                else:
                    s = Utils.websafe(listname)
                return 'Illegal list name: %s' % self.ln
            except Errors.MMListError:
                return 'Some unknown error occurred while creating the list.'

            # Initialize the host_name and web_page_url attributes, based on
            # virtual hosting settings and the request environment variables.
            self.ml.default_member_moderation = self.moderate
            self.ml.web_page_url = mm_cfg.DEFAULT_URL_PATTERN % self.hn
            self.ml.host_name = self.eh
            self.ml.info = self.info
            self.ml.description = self.desc
            self.ml.Save()
        finally:
            # Now be sure to unlock the list.  It's okay if we get a signal
            # here because essentially, the signal handler will do the same
            # thing.  And unlocking is unconditional, so it's not an error if
            # we unlock while we're already unlocked.
            self.ml.Unlock()

        # Now do the MTA-specific list creation tasks
        if mm_cfg.MTA:
            modname = 'Mailman.MTA.' + mm_cfg.MTA
            __import__(modname)
            sys.modules[modname].create(self.ml, cgi=1)

        # And send the notice to the list owner.
        if self.notify:
            self.notify_owner()

        return None

    def handler (self):
        if self.cgidata.has_key('lc_submit'):
            error = self.request_create()
            self.kwargs_add('action_taken', True)
            self.kwargs_add('create_ln', self.ln)
            if not error:
                self.kwargs_add('create_status', 'Successfully Created')
            else:
                self.kwargs_add('create_status',
                                'Creation failed (%s)' % error)
        else:
            self.kwargs_add('action_taken', False)

        self.render()


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
