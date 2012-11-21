"""Primary web entry point for the customized intranet implementation.

This eliminates a lot of the complexity based on the assumption that access to
this site is controlled via a domain level browser authentication. No other
operation requires a password from the user. Note however that this layer
wraps around some of the password authentication requirements of mailman by
using some defaults, and relieves the user of such headaches. So this layer
does not chnage mailman behaviour in any way.
"""

# No lock needed in this script, because we don't change data.

from   datetime import datetime
import os
import re

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


def ctl_home ():
    loader = template.Loader("../templates/en")
    print 'Content-Type: text/html; charset=%s\n' % 'us-ascii'
    print
    print loader.load("ctl-base.html").generate(auto_version=auto_version)

def ctl_view ():
    loader = template.Loader("../templates/en")
    print 'Content-Type: text/html; charset=%s\n' % 'us-ascii'
    print
    print loader.load("ctl-view.html").generate(auto_version=auto_version)

def ctl_create ():
    loader = template.Loader("../templates/en")
    print 'Content-Type: text/html; charset=%s\n' % 'us-ascii'
    print
    print loader.load("ctl-create.html").generate(auto_version=auto_version)

def ctl_admin ():
    loader = template.Loader("../templates/en")
    print 'Content-Type: text/html; charset=%s\n' % 'us-ascii'
    print
    print loader.load("ctl-admin.html").generate(auto_version=auto_version)

def main ():
    parts = Utils.GetPathPieces()
    if not parts:
        ctl_home()
        return

    action = parts[0].lower()
    if action == 'view':
        ctl_view()
    elif action == 'create':
        ctl_create()
    elif action == 'admin':
        ctl_admin()
    else:
        ## FIXME: This should throw a 404.
        ctl_home()


if __name__ == "__main__":
    main()
