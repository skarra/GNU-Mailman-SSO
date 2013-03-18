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
import json
import os
import re
import signal
import string
import sys
import traceback

from email.Utils import parseaddr

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Message
from Mailman import Errors
from Mailman import i18n
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog
from Mailman.Utils import sha_new
from Mailman.UserDesc import UserDesc

from Mailman.tornado import template

# Set up i18n
_ = i18n._
i18n.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)

def auto_version (resource):
    """Intended to be invoked from inside tornado templates, given a resource
    names such as /static/ctl.js this will return something like
    /static/ctl.v201211010141551.css to version it. For this to work we need a
    working url rewrite rule in apache or equivalent to strip out the
    timestamp.

    It is assumed that static resources that need to be versioned are
    available at the first level inside the PREFIX Directory"""

    if mm_cfg.SSO_ENVIRONMENT == mm_cfg.SSO_DEV:
        return resource

    absname   = os.path.abspath(os.path.join(mm_cfg.VAR_PREFIX, resource[1:]))
    d         = datetime.fromtimestamp(os.path.getmtime(absname))
    timestamp = d.strftime("%Y%m%d%H%M%S")

    res = re.match('(.*\.)([a-zA-Z]*$)', resource)
    return ''.join([res.group(1), 'v', timestamp, '.', res.group(2)])


def can_create_lists (em):
    """Returns True if a user is authorized to create lists on the
    server. False if otherwise. By default this method merely checks if em is
    in the SSO_LIST_CREATE_AUTHIDS array."""

    if not mm_cfg.SSO_LIST_CREATE_AUTHIDS or em in mm_cfg.SSO_LIST_CREATE_AUTHIDS:
        return True

    return False

def get_curr_user (raw=False):
    """Extracts the Cleartrip userid from the cookie. This cookie is set by
    any authenticated Cleartrip site - and as a result the site where this
    list server will be hosted."""

    _curr_user = None
    cookie_key = mm_cfg.SSO_USER_COOKIE
    try:
        cookie = Cookie.SimpleCookie(os.environ["HTTP_COOKIE"])
        if raw:
            _curr_user = cookie[cookie_key].value
        else:
            _curr_user = mm_cfg.sso_user_cookie_hook(cookie[cookie_key].value)
    except Cookie.CookieError, e:
        _curr_user = "Cookie Error"
    except  KeyError, e:
        syslog('sso', 'Cookie key (%s) not found. Forcing signin' % cookie_key)

    return _curr_user


class Action(object):
    def __init__ (self, templ):
        self._cgidata   = cgi.FieldStorage()
        self._templ     = templ
        self._curr_user = get_curr_user()
        self._all_mls   = None
        self._templ_dir = "../templates/en"
        self.kwargs     = {'auto_version' : auto_version,
                           'curr_user'    : self.curr_user,
                           'logged_user'  : get_curr_user(raw=True),
                           'hostname'     : Utils.get_domain(),
                           }
        self.more_headers = []

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

    @property
    def all_mls (self):
        """A dictionary of listname to corresponding MailList objects. The
        lists are not locked. This is an important thing to keep in mind.

        This is potentially time consuming to create for every call. We may
        revisit this as a potential performance improvement. FIXME"""

        if self._all_mls:
            return self._all_mls

        self._all_mls = {}
        for name in Utils.list_names():
            self._all_mls[name] = MailList.MailList(name, lock=0)

        return self._all_mls

    def kwargs_add (self, key, val):
        self.kwargs.update({key : val})

    def header_add (self, header):
        self.more_headers.append(header)

    def handler (self):
        self.render()


class HTMLAction(Action):
    def __init__ (self, templ):
        Action.__init__(self, templ)

    def render (self):
        loader = template.Loader(self.templ_dir)
        if self.more_headers:
            for header in self.more_headers:
                print header
        print 'Content-Type: text/html; charset=%s\n' % 'us-ascii'
        print
        print loader.load(self.templ).generate(**self.kwargs)


class JSONAction(Action):
    def __init__ (self, templ=None):
        Action.__init__(self, templ)             # There is no template, really.
        del self.kwargs['auto_version']

    def render (self):
        if self.more_headers:
            for header in self.more_headers:
                if header != '':
                    print header
        print 'Content-Type: application/json; charset=us-ascii\n'
        print
        print json.dumps(self.kwargs)
        

class HTMLError(HTMLAction):
    def __init__ (self):
        HTMLAction.__init__(self, "ctl-error.html")
        self.header_add("Status: 500 Internal Server Error")


class JSONError(JSONAction):
    def __init__ (self):
        JSONAction.__init__(self)
        self.header_add("Status: 500 Internal Server Error")


class JSONException(Exception): pass


class Home(HTMLAction):
    def __init__ (self):
        HTMLAction.__init__(self, "ctl-base.html")


class View(HTMLAction):
    def __init__ (self):
        HTMLAction.__init__(self, "ctl-view.html")
    
    def add_req_ln_details (self, ln):
        ml = self.all_mls[ln]

        self.kwargs_add('vl_ln', ln)
        self.kwargs_add('vl_archives', '/pipermail/%s' % ln)
        self.kwargs_add('vl_bd', ml.description)
        self.kwargs_add('vl_dd', ml.info)
        self.kwargs_add('vl_roster', ml.getRegularMemberKeys())
        self.kwargs_add('vl_owners', ml.owner)
        self.kwargs_add('vl_owners_email', ml.GetOwnerEmail())

    def handler (self, parts):
        lists = []
        for name, mlist in self.all_mls.iteritems():
            members = mlist.getRegularMemberKeys()
            subscribed = True if self.curr_user in members else False

            if not mlist.advertised and not subscribed:
                continue

            lists.append({'script_url'  : mlist.GetScriptURL('listinfo'),
                          'real_name'   : mlist.real_name,
                          'description' : Utils.websafe(mlist.description),
                          'subscribed'  : subscribed,
                          'owners'      : ', '.join(mlist.owner),
                          'owner-email' : mlist.GetOwnerEmail(),
                          'advertised'  : mlist.advertised,
                          })
    
        self.kwargs_add('lists', lists)

        if len(parts) > 0:
            try:
                self.add_req_ln_details(parts[0].strip())
            except:
                self.kwargs_add('vl_ln', None)
        else:
            self.kwargs_add('vl_ln', None)

        self.render()


class Subscription(JSONAction):
    """This action will perform a subscribe or unsubscribe action and redirect
       to the view action handler"""

    def __init__ (self):
        JSONAction.__init__(self)

    def handler (self):
        listname = self.cgidata.getvalue('list')
        action   = self.cgidata.getvalue('action').lower().strip()

        syslog('sso', 'User: %s; Listname: %s; action: %s' % (self.curr_user,
                                                              listname, action))

        mlist = MailList.MailList(listname)
        userdesc = UserDesc(self.curr_user, u'', mm_cfg.SSO_STOCK_USER_PWD,
                            False)

        if action == 'join':
            try:
                text = ('Welcome to %s. Visit the List Server to ' +
                        'manage your subscriptions') % listname
                mlist.ApprovedAddMember(userdesc, True, text,
                                        whence='SSO Web Interface')
                mlist.Save()
                self.kwargs_add('notice_success', True)
                self.kwargs_add('notice_text',
                                'Successfully added to list: %s' % listname)
            except Errors.MMAlreadyAMember:
                self.kwargs_add('notice_success', False)
                self.kwargs_add('notice_text',
                                'You are already subscribed to %s' % listname)
        elif action == 'leave':
            try:
                mlist.ApprovedDeleteMember(self.curr_user)
                mlist.Save()
                self.kwargs_add('notice_success', True)
                self.kwargs_add('notice_text',
                                'Successfully removed from list: %s' % listname)
            except Errors.NotAMemberError:
                # User has already been unsubscribed
                self.kwargs_add('notice_success', False)
                self.kwargs_add('notice_text',
                                'You are not a member of %s' % listname)

        self.render()


class Create(HTMLAction):
    def __init__ (self):
        HTMLAction.__init__(self, "ctl-listadmin.html")
        self._ln = self.cgival('lc_name').lower()
        self._priv = self.cgival('lc_private') != ''
        self._safelin = Utils.websafe(self.ln)
        self._pw = mm_cfg.SSO_STOCK_ADMIN_PWD
        self._owner = self.get_owners()
        self._hn = Utils.get_domain()
        self._eh = mm_cfg.VIRTUAL_HOSTS.get(self.hn, mm_cfg.DEFAULT_EMAIL_HOST)
        self._ml = None
        self._langs = [mm_cfg.DEFAULT_SERVER_LANGUAGE]
        self._moderate = mm_cfg.DEFAULT_DEFAULT_MEMBER_MODERATION
        self._notify = 1
        self._info = self.cgival('lc_info')
        self._welcome = self.cgival('lc_welcome')
        self._desc = self.cgival('lc_desc')

    @property
    def ln (self):
        return self._ln

    @property
    def safeln (self):
        return self._safeln

    @property
    def priv (self):
        return self._priv

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
    def welcome (self):
        return self._welcome

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

    def errcheck (self, action):
        """Performs all error checks. Returns None is all's good. Otherwise
        returns a string with error message."""

        if not can_create_lists(self.curr_user):
            return 'You are not authorized to creates lists on this server'

        if len(self.owner) <= 0:
            return 'Cannot create list without a owner.'

        if self.ln == '':
            return 'You forgot to enter the list name'

        if '@' in self.ln:
            return 'List name must not include "@": %s' % self.safeln

        if action == 'create' and Utils.list_exists(self.ln):
            return 'List already exists: %s' % self.safe_ln

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

    def get_owners (self):
        ret = []
        for key in self.cgidata.keys():
            if re.match('^lc_owner', key):
                fn, em = parseaddr(self.cgival(key).lower().strip())
                ret.append(em)

        return ret

    def add_members (self, save=False):
        """Add any email addressses that are provided in the create form."""

        if self.welcome == '':
            text = ('Welcome to %s. Visit the List Server to ' +
            'manage your subscriptions') % self.ln
        else:
            text = self.welcome

        for key in self.cgidata.keys():
            if re.match('^lc_member_', key):
                fn, em = parseaddr(self.cgival(key).lower().strip())
                userdesc = UserDesc(em, fn, mm_cfg.SSO_STOCK_USER_PWD, False)
                try:
                    self.ml.ApprovedAddMember(userdesc, True, text,
                                              whence='SSO List Creation Time')
                    syslog('sso',
                           'Successfully added %s to list: %s' % (em,
                                                                  self.ln))
                except Errors.MMAlreadyAMember:
                    ## FIXME: Need to find some way of communicating this
                    ## case to the user. As thisi s a new list, this can only
                    ## happen if the same address is given by the admin... hm
                    syslog('sso',
                           '%s already a member of listL %s' % (em, self.ln))

        if save:
            self.ml.Save()


    def edit_members (self):
        oldm = self.ml.getRegularMemberKeys()
        newm = []
        for key in self.cgidata.keys():
            if re.match('^lc_member_', key):
                fn, em = parseaddr(self.cgival(key).lower())
                newm.append(em)

        remove = [x for x in oldm if not x in newm]
        insert = [x for x in newm if not x in oldm]

        syslog('sso', 'Will remove %s from list %s' % (remove, self.ln))
        syslog('sso', 'Will add %s to list %s' % (insert, self.ln))

        for em in remove:
            self.ml.ApprovedDeleteMember(em, whence='SSO Web Interface')

        for em in insert:
            userdesc = UserDesc(em, '', mm_cfg.SSO_STOCK_USER_PWD, False)
            try:
                self.ml.ApprovedAddMember(userdesc, True, self.welcome,
                                          whence='SSO List Edit')
                syslog('sso',
                       'Successfully added %s to list: %s' % (em,
                                                              self.ln))
            except Errors.MMAlreadyAMember:
                syslog('sso',
                       'request_edit: %s already a member of list %s' % (em,
                                                                         self.ln))

    def set_ml_params (self):
        """Set some mailing list values from the form fields filled out by the
        user."""

        self.ml.advertised = not self.priv
        self.ml.default_member_moderation = self.moderate
        self.ml.web_page_url = mm_cfg.DEFAULT_URL_PATTERN % self.hn
        self.ml.host_name = self.eh
        self.ml.info = self.info
        self.ml.description = self.desc
        self.ml.welcome_msg = self.welcome

    def set_ml_defaults (self):
        """Set some of the static defaults for mailing list config
        variables. This is largely intended to override any Mailman defaults
        as we see fit for SSO use case. This is meant to be invoked at list
        creation time only."""

        self.ml.send_welcome_msg = mm_cfg.SSO_DEFAULT_SEND_WELCOME_MSG
        self.ml.send_goodbye     = mm_cfg.SSO_DEFAULT_SEND_GOODBYE_MSG
        self.ml.send_reminders   = mm_cfg.SSO_DEFAULT_SEND_REMINDERS
        self.ml.generic_nonmember_action = mm_cfg.SSO_DEFAULT_GENERIC_NONMEMBER_ACTION
        self.ml.msg_footer     = mm_cfg.SSO_DEFAULT_MSG_FOOTER
        self.ml.digest_footer  = mm_cfg.SSO_DEFAULT_DIGEST_FOOTER

        ## FIXME: Should support more list configuration options supported by
        ## Mailman.


    def set_ml_owners (self, save=False):
        """The caller should call Save() after this by default, unless
        'save' is set to True."""

        self.ml.owner = []
        for owner in self.owner:
            self.ml.owner.append(owner)

        if save:
           self.ml.Save() 

    def request_create (self):
        """Creates a list (name taken from the CGI form value called lc_name).

        Returns None if the list was created successfully. Returns a string
        containing error message if list could not be created for whatever
        reason."""

        self._ml = MailList.MailList()
        err = self.errcheck(action='create')
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
                    self.ml.Create(self.ln, self.owner[0], pwhex, self.langs,
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

            self.set_ml_defaults()
            self.set_ml_params()
            self.ml.Save()

            syslog('sso', 'Successfully created list: %s' % self.ln)

            self.add_members()
            self.set_ml_owners()
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

    def request_edit (self):
        self._ml = self.all_mls[self.ln]
        err = self.errcheck(action='edit')
        if err:
            return err

        # We've got all the data we need, so go ahead and try to edit the
        # list See admin.py for why we need to set up the signal handler.

        try:
            signal.signal(signal.SIGTERM, self.sigterm_handler)

            self.ml.Lock()
            self.set_ml_params()
            self.edit_members()
            self.set_ml_owners()
            self.ml.Save()
            syslog('sso', 'Successfully modified list config: %s' % self.ln)
        finally:
            # Now be sure to unlock the list.  It's okay if we get a signal
            # here because essentially, the signal handler will do the same
            # thing.  And unlocking is unconditional, so it's not an error if
            # we unlock while we're already unlocked.
            self.ml.Unlock()

        return None

    def handler_new (self, parts, submit):
        """This method is invoked when the user tries to create a new list.

        If submit is False then we render the empty form. On submission of the
        form (after validation in javascript, we get a submit=True invocation
        of this same routine."""

        self.kwargs_add('list_to_edit', None)
        if not submit:
            self.kwargs_add('lc_empty_form', True)
            return

        self.kwargs_add('lc_empty_form', False)

        error = self.request_create()
        self.kwargs_add('action_taken', True)
        self.kwargs_add('create_ln', self.ln)
        if not error:
            self.kwargs_add('create_status', 'success')
            self.kwargs_add('create_status_msg', 'Successfully Created')
        else:
            self.kwargs_add('create_status', 'failed')
            self.kwargs_add('create_status_msg',
                            'Creation failed (%s)' % error)

    def handler_edit (self, parts):
        ## This is when a POST request is made after the user fills out
        ## the form and clicks "Create" button.
        error = self.request_edit()
        self.kwargs_add('action_taken', True)
        self.kwargs_add('create_ln', self.ln)
        if not error:
            self.kwargs_add('create_status', 'success')
            self.kwargs_add('create_status_msg', 'Successfully Edited')
        else:
            self.kwargs_add('create_status', 'failed')
            self.kwargs_add('create_status_msg',
                            'Edit failed (%s)' % error)
        self.kwargs_add('list_to_edit', None)
        self.kwargs_add('lc_empty_form', False)

    def handler (self, parts):
        owned = []
        cu = self.curr_user
        for mln, ml in self.all_mls.iteritems():
            if cu in ml.owner or cu in mm_cfg.SSO_ADMIN_AUTHIDS:
                owned.append({'real_name' : ml.real_name,
                              'description' : Utils.websafe(ml.description),
                              'advertised' : ml.advertised,
                              })
        self.kwargs_add('lists', owned)
        self.kwargs_add('can_create_lists', can_create_lists)

        if self.cgidata.has_key('lc_submit'):
            if parts[0] == 'new':
                self.handler_new(parts, submit=True)
            else:
                self.handler_edit(parts)
        else:
            ## This is the case when we are landing here through a GET
            ## request.
            self.kwargs_add('action_taken', False)

            if (len(parts) == 0 or parts[0] == ''):
                ## This is the root /create page
                self.kwargs_add('list_to_edit', None)
                self.kwargs_add('lc_empty_form', False)
            elif parts[0] == 'new':
                ## This is the root /create/new page
                self.handler_new(parts, submit=False)
            else:
                ## This is some /create/xyz type page which is for editing the
                ## configuration of list named xyz
                self.kwargs_add('list_to_edit', self.all_mls[parts[0].lower()])
                self.kwargs_add('lc_empty_form', False)

        self.render()

class Admin(HTMLAction):
    def __init__ (self):
        Action.__init__(self, "ctl-siteadmin.html")


def doit ():
    parts = Utils.GetPathPieces()
    if not parts:
        Home().handler()
        return

    action = parts[0].lower().strip()

    if action == 'view':
        View().handler(parts[1:])
    elif action == 'listadmin':
        Create().handler(parts[1:])
    elif action == 'siteadmin':
        Admin().handler()
    elif action == 'subscribe':
        try:
            Subscription().handler()
        except Exception, e:
            ## FIXME: This is not the best approach. The overall exception
            ## handling has become a mess... Hm.
            raise JSONException(str(e))
    else:
        ## FIXME: This should throw a 404.
        Home().handler()


def main ():
    try:
        doit()
    except JSONException, e:
        err = JSONError()
        err.kwargs_add('error', str(e) + '\n' + traceback.format_exc())
        err.handler()
    except:
        err = HTMLError()
        err.kwargs_add('error', traceback.format_exc())
        err.handler()        


if __name__ == "__main__":
    main()
