import os, cherrypy
from gettext import gettext as _
from auth import require
from plugin_mount import PagePlugin, FormPlugin
import cfg
from forms import Form
from util import *

class users(PagePlugin):
    order = 20 # order of running init in PagePlugins
    def __init__(self, *args, **kwargs):
        PagePlugin.__init__(self, *args, **kwargs)
        self.register_page("sys.users")

    @cherrypy.expose
    @require()
    def index(self):
        parts = self.forms('/sys/config')
        parts['title']=_("Manage Users and Groups")
        return self.fill_template(**parts)

class add(FormPlugin, PagePlugin):
    url = ["/sys/users"]
    order = 30

    sidebar_left = ''
    sidebar_right = _("""<h2>Add User</h2><p>Adding a user via this
        administrative interface <b>might</b> create a system user.
        For example, if you provide a user with ssh access, she will
        need a system account.  If you don't know what that means,
        don't worry about it.</p>""")

    def main(self, username='', name='', email='', message=None, *args, **kwargs):
        form = Form(title="Add User", 
                        action="/sys/users/add/index", 
                        onsubmit="return md5ify('add_user_form', 'password')", 
                        name="add_user_form",
                        message=message)
        form.text = '<script type="text/javascript" src="/static/js/md5.js"></script>\n'+form.text
        form.text_input(_("Username"), name="username", value=username)
        form.text_input(_("Full name"), name="name", value=name)
        form.text_input(_("Email"), name="email", value=email)
        form.text_input(_("Password"), name="password")
        form.text_input(name="md5_password", type="hidden")
        form.submit(label=_("Create User"), name="create")
        return form.render()

    def process_form(self, username=None, name=None, email=None, md5_password=None, **kwargs):
        msg = ''

        if not username: msg = add_message(msg, _("Must specify a username!"))
        if not md5_password: msg = add_message(msg, _("Must specify a password!"))
        
        if cfg.users.get(username):
            msg = add_message(msg, _("User already exists!"))
        else:
            try:
                cfg.users.set(User(dict={'username':username, 'name':name, 'email':email, 'password':md5_password}))
            except:
                msg = add_message(msg, _("Error storing user!"))

        if not msg:
            msg = add_message(msg, "%s saved." % username)

        main = self.make_form(username, name, email, message=msg)
        return self.fill_template(title="", main=main, sidebar_left=self.sidebar_left, sidebar_right=self.sidebar_right)

class edit(FormPlugin, PagePlugin):
    url = ["/sys/users"]
    order = 35
    
    sidebar_left = ''
    sidebar_right = _("""<h2>Edit Users</h2><p>Click on a user's name to
    go to a screen for editing that user's account.</p><h2>Delete
    Users</h2><p>Check the box next to a users' names and then click
    "Delete User" to remove users from %s and the %s
    system.</p><p>Deleting users is permanent!</p>""" % (cfg.product_name, cfg.box_name))

    def main(self, msg=''):
        users = cfg.users.get_all()
        add_form = Form(title=_("Edit or Delete User"), action="/sys/users/edit", message=msg)
        add_form.html('<span class="indent"><b>Delete</b><br /></span>')
        for uname in sorted(users.keys()):
            add_form.html('<span class="indent">&nbsp;&nbsp;%s&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;' % 
                          add_form.get_checkbox(name=uname) +
                          '<a href="/sys/users/edit?username=%s">%s (%s)</a><br /></span>' % 
                          (uname, users[uname]['name'], uname))
        add_form.submit(label=_("Delete User"), name="delete")
        return add_form.render()

    def process_form(self, **kwargs):
        if 'delete' in kwargs:
            msg = Message()
            usernames = find_keys(kwargs, 'on')
            cfg.log.info("%s asked to delete %s" % (cherrypy.session.get(cfg.session_key), usernames))
            if usernames:
                for username in usernames:
                    if cfg.users.exists(username):
                        try:
                            cfg.users.remove(username)
                            msg.add(_("Deleted user %s." % username))
                        except IOError, e:
                            if cfg.users.get('username', reload=True):
                                m = _("Error on deletion, user %s not fully deleted: %s" % (username, e))
                                cfg.log.error(m)
                                msg.add(m)
                            else:
                                m = _('Deletion failed on %s: %s' % (username, e))
                                cfg.log.error(m)
                                msg.add(m)
                    else:
                        cfg.log.warning(_("Can't delete %s.  User does not exist." % username))
                        msg.add(_("User %s does not exist." % username))
            else:
                msg.add = _("Must specify at least one valid, existing user.")
            main = self.make_form(msg=msg.text)
            return self.fill_template(title="", main=main, sidebar_left=self.sidebar_left, sidebar_right=self.sidebar_right)

        sidebar_right = ''
        u = cfg.users.get(kwargs['username'])
        if not u:
            main = _("<p>Could not find a user with username of %s!</p>" % kwargs['username'])
            return self.fill_template(template="err", title=_("Unnown User"), main=main, 
                             sidebar_left=self.sidebar_left, sidebar_right=sidebar_right)
            
        main = _("""<h2>Edit User '%s'</h2>""" % u['username'])
        sidebar_right = ''
        return self.fill_template(title="", main=main, sidebar_left=self.sidebar_left, sidebar_right=sidebar_right)
