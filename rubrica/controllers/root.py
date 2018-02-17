# -*- coding: utf-8 -*-
"""Main Controller"""

from tg import expose, flash, require, url, lurl
from tg import request, redirect, tmpl_context, validate
from tg.validation import Convert
from tg.i18n import ugettext as _, lazy_ugettext as l_
from tg.exceptions import HTTPFound
from tg import predicates
from rubrica import model
from rubrica.controllers.secure import SecureController
from rubrica.model import DBSession, User, Rubrica
from tgext.admin.tgadminconfig import BootstrapTGAdminConfig as TGAdminConfig
from tgext.admin.controller import AdminController
from rubrica.lib.base import BaseController
from rubrica.controllers.error import ErrorController
from formencode import validators
from tg.predicates import not_anonymous

__all__ = ['RootController']


class RootController(BaseController):
    """
    The root controller for the rubrica application.

    All the other controllers and WSGI applications should be mounted on this
    controller. For example::

        panel = ControlPanelController()
        another_app = AnotherWSGIApplication()

    Keep in mind that WSGI applications shouldn't be mounted directly: They
    must be wrapped around with :class:`tg.controllers.WSGIAppController`.

    """
    secc = SecureController()
    admin = AdminController(model, DBSession, config_type=TGAdminConfig)

    error = ErrorController()

    @expose('rubrica.templates.index')
    def index(self):
        return dict(page="index")

    @expose('rubrica.templates.home')
    @expose('json')
    @require(not_anonymous(msg='Only logged user can access thi page'))
    def home(self, *args):
        contact = DBSession.query(Rubrica).\
            filter_by(parent_id=request.identity['user'].user_id).\
            order_by(Rubrica.user_name).all()
        return dict(page='home', contact=contact)

    @expose('json')
    @require(not_anonymous(msg='Only logged user can access thi page'))
    def jp(self):
        contact = DBSession.query(Rubrica.user_name, Rubrica.user_Number).\
            filter_by(parent_id=request.identity['user'].user_id).all()  
        return dict(contact=contact)


    @expose('rubrica.templates.home')
    @require(not_anonymous(msg='Only logged user can access this page'))
    @validate(validators=dict(
        {'search': validators.String(max=80, not_empty=True),}))
    def search(self, search):
        if not search:
            redirect('/home')                               
        else:
            try:
                contact = DBSession.query(Rubrica).\
                filter(Rubrica.parent_id==request.identity['user'].user_id). \
                filter(Rubrica.user_name.like(f"%{search}%")).\
                order_by(Rubrica.user_name).all()
                return dict(page='home', contact=contact)
            except:
                redirect('/home')

    @expose('rubrica.templates.nuovo')
    @require(not_anonymous(msg='Only logged user can access thi page'))
    def new_contact(self):
        return dict(page='nuovo')

    @expose()
    def errore(self, **kwargs):
        flash('An error occurred: %s' % request.validation['errors'])

    @expose()
    @require(not_anonymous(msg='Only logged user can access thi page'))
    @validate({
        'name': validators.String(max=80, not_empty=True),
        'number': Convert(int, 'Must be a number')}, error_handler=errore)
    def add(self, name, number):
        r = model.Rubrica()
        r.user_name = name
        r.user_Number = number
        r.parent_id = request.identity['user'].user_id 
        model.DBSession.add(r)
        model.DBSession.flush()      
        redirect('/home')
  
    @expose()
    @require(not_anonymous(msg='Only logged user can access thi page'))
    def delete(self, id):
        obj = DBSession.query(Rubrica).filter_by(user_id=id).one()
        model.DBSession.delete(obj)
        model.DBSession.flush() 
        redirect('/home')


    # funzione non funzionante poichè devo trovare un modo per veficare 
    # se l'email che l'utente decide magari di cambiare
    # se esista o meno, perciò per ora la seguente pagina 
    # si limita solo a far vedere i dati dell'user 
    # e la password mostrata è quella hashata 
    @expose('rubrica.templates.settings')
    @require(not_anonymous(msg='Only logged user can access thi page'))
    def setting(self, **kw):
        try:
            user = DBSession.query(User)\
            .filter_by(user_id=request.identity['user'].user_id).one()
            return dict(page='setting', user=user)
        except:
            return dict(page='setting')


    @expose('rubrica.templates.login')
    def login(self, came_from=lurl('/home'), failure=None, login=''):
        """Start the user login."""
        if failure is not None:
            if failure == 'user-not-found':
                flash(_('User not found'), 'error')
            elif failure == 'invalid-password':
                flash(_('Invalid Password'), 'error')

        login_counter = request.environ.get('repoze.who.logins', 0)
        if failure is None and login_counter > 0:
            flash(_('Wrong credentials'), 'warning')

        return dict(page='login', login_counter=str(login_counter),
                    came_from=came_from, login=login)

    @expose()
    def post_login(self, came_from=lurl('/home')):
        """
        Redirect the user to the initially requested page on successful
        authentication or redirect her back to the login page if login failed.

        """
        if not request.identity:
            login_counter = request.environ.get('repoze.who.logins', 0) + 1
            redirect('/login',
                     params=dict(came_from=came_from, __logins=login_counter))
        userid = request.identity['repoze.who.userid']
        flash(_('Welcome back, %s!') % userid)

        # Do not use tg.redirect with tg.url as it will add the mountpoint
        # of the application twice.
        return HTTPFound(location=came_from)

    @expose()
    def post_logout(self, came_from=lurl('/h')):
        """
        Redirect the user to the initially requested page on logout and say
        goodbye as well.

        """
        flash(_('We hope to see you soon!'))
        return HTTPFound(location=came_from)