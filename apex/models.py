import hashlib

import bcrypt
import six
import transaction
from pyramid.threadlocal import get_current_request
from pyramid.util import DottedNameResolver
from sqlalchemy import Column, ForeignKey, Index, Table, types, Unicode
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker, synonym
from sqlalchemy.sql.expression import func
from zope.sqlalchemy import ZopeTransactionExtension

from apex.lib.db import get_or_create

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

auth_group_table = Table(
    'auth_auth_groups', Base.metadata,
    Column('auth_id', types.Integer(),
           ForeignKey('auth_id.id', onupdate='CASCADE', ondelete='CASCADE')),
    Column('group_id', types.Integer(),
           ForeignKey('auth_groups.id', onupdate='CASCADE', ondelete='CASCADE'))
)
# need to create Unique index on (auth_id,group_id)
Index('auth_group', auth_group_table.c.auth_id, auth_group_table.c.group_id)


class AuthGroup(Base):
    """ Table name: auth_groups
    
::

    id = Column(types.Integer(), primary_key=True)
    name = Column(Unicode(80), unique=True, nullable=False)
    description = Column(Unicode(255), default=u'')
    """
    __tablename__ = 'auth_groups'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(types.Integer(), primary_key=True)
    name = Column(Unicode(80), unique=True, nullable=False)
    description = Column(Unicode(255), default=u'')

    users = relationship('AuthID', secondary=auth_group_table,
                         backref='auth_groups')

    def __repr__(self):
        return u'%s' % self.name

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__()


class AuthID(Base):
    """ Table name: auth_id

::

    id = Column(types.Integer(), primary_key=True)
    display_name = Column(Unicode(80), default=u'')
    active = Column(types.Enum(u'Y',u'N',u'D', name=u'active'), default=u'Y')
    created = Column(types.DateTime(), default=func.now())

    """

    __tablename__ = 'auth_id'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(types.Integer(), primary_key=True)
    display_name = Column(Unicode(80), default=u'')
    active = Column(types.Enum(u'Y', u'N', u'D', name=u'active'), default=u'Y')
    created = Column(types.DateTime(), default=func.now())

    groups = relationship('AuthGroup', secondary=auth_group_table, backref='auth_users')

    users = relationship('AuthUser')

    """
    Fix this to use association_proxy
    groups = association_proxy('auth_group_table', 'authgroup')
    """

    last_login = relationship(
        'AuthUserLog', order_by='AuthUserLog.id.desc()', uselist=False)
    login_log = relationship('AuthUserLog', order_by='AuthUserLog.id')

    def in_group(self, group):
        """
        Returns True or False if the user is or isn't in the group.
        """
        return group in [g.name for g in self.groups]

    @classmethod
    def get_by_id(cls, id):
        """ 
        Returns AuthID object or None by id

        .. code-block:: python

           from apex.models import AuthID

           user = AuthID.get_by_id(1)
        """
        return DBSession.query(cls).filter(cls.id == id).first()

    def get_profile(self, request=None):
        """
        Returns AuthUser.profile object, creates record if it doesn't exist.

        .. code-block:: python

           from apex.models import AuthUser

           user = AuthUser.get_by_id(1)
           profile = user.get_profile(request)

        in **development.ini**

        .. code-block:: python

           apex.auth_profile = 
        """
        if not request:
            request = get_current_request()

        auth_profile = request.registry.settings.get('apex.auth_profile')
        if auth_profile:
            resolver = DottedNameResolver(auth_profile.split('.')[0])
            profile_cls = resolver.resolve(auth_profile)
            return get_or_create(DBSession, profile_cls, auth_id=self.id)

    @property
    def group_list(self):
        group_list = []
        if self.groups:
            for group in self.groups:
                group_list.append(group.name)
        return ','.join(map(str, group_list))


class AuthUser(Base):
    """ Table name: auth_users

::

    id = Column(types.Integer(), primary_key=True)
    login = Column(Unicode(80), default=u'', index=True)
    _password = Column('password', Unicode(80), default=u'')
    email = Column(Unicode(80), default=u'', index=True)
    active = Column(types.Enum(u'Y',u'N',u'D'), default=u'Y')
    """
    __tablename__ = 'auth_users'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(types.Integer(), primary_key=True)
    auth_id = Column(types.Integer, ForeignKey(AuthID.id), index=True)
    provider = Column(Unicode(80), default=u'local', index=True)
    login = Column(Unicode(80), default=u'', index=True)
    salt = Column(Unicode(40))
    _password = Column('password', Unicode(80), default=u'')
    email = Column(Unicode(80), default=u'', index=True)
    created = Column(types.DateTime(), default=func.now())
    active = Column(types.Enum(u'Y', u'N', u'D', name=u'active'), default=u'Y')

    # need unique index on auth_id, provider, login
    # create unique index ilp on auth_users (auth_id,login,provider);
    # how do we handle same auth on multiple ids?

    def _set_password(self, password, rounds=13):
        # Handle arbitrarily long passwords by pre-hashing
        self._password = bcrypt.hashpw(
            self._pre_hash_password(password),
            bcrypt.gensalt(rounds=rounds)).decode('utf-8')

    def _get_password(self):
        return self._password

    @staticmethod
    def _pre_hash_password(password):
        return hashlib.sha512(password.encode('utf-8')).digest()

    password = synonym('_password', descriptor=property(_get_password, _set_password))

    def get_salt(self, length, rounds=13):
        # salt = bcrypt.gensalt(rounds=rounds)
        # salt = salt.decode('utf-8')[:length]
        # return salt
        # Ignored - salt is generated once in _set_password and stored inside the hash.
        return ''

    @classmethod
    def get_by_id(cls, id):
        """ 
        Returns AuthUser object or None by id

        .. code-block:: python

           from apex.models import AuthID

           user = AuthID.get_by_id(1)
        """
        return DBSession.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_by_login(cls, login):
        """ 
        Returns AuthUser object or None by login

        .. code-block:: python

           from apex.models import AuthUser

           user = AuthUser.get_by_login('login')
        """
        return DBSession.query(cls).filter(cls.login == login).first()

    @classmethod
    def get_by_email(cls, email):
        """ 
        Returns AuthUser object or None by email

        .. code-block:: python

           from apex.models import AuthUser

           user = AuthUser.get_by_email('email@address.com')
        """
        return DBSession.query(cls).filter(cls.email == email).first()

    @classmethod
    def check_password(cls, **kwargs):
        user = None
        if 'id' in kwargs:
            user = cls.get_by_id(kwargs['id'])
        if 'login' in kwargs:
            user = cls.get_by_login(kwargs['login'])

        if not user:
            return False
        try:
            if bcrypt.checkpw(
                    cls._pre_hash_password(kwargs['password']),
                    user.password.encode('utf-8')):
                return True
        except TypeError:
            pass

        request = get_current_request()
        fallback_auth = request.registry.settings.get('apex.fallback_auth')
        if fallback_auth:
            resolver = DottedNameResolver(fallback_auth.split('.', 1)[0])
            fallback = resolver.resolve(fallback_auth)
            return fallback().check(
                DBSession, request, user, kwargs['password'])

        return False


class AuthUserLog(Base):
    """
    event: 
      L - Login
      R - Register
      P - Password
      F - Forgot
    """
    __tablename__ = 'auth_user_log'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(types.Integer, primary_key=True)
    auth_id = Column(types.Integer, ForeignKey(AuthID.id), index=True)
    user_id = Column(types.Integer, ForeignKey(AuthUser.id), index=True)
    time = Column(types.DateTime(), default=func.now())
    ip_addr = Column(Unicode(39), nullable=False)
    event = Column(types.Enum(u'L', u'R', u'P', u'F', name=u'event'), default=u'L')


def populate(settings):
    session = DBSession()

    default_groups = []
    if 'apex.default_groups' in settings:
        for name in settings['apex.default_groups'].split(','):
            default_groups.append((six.u(name.strip()), u''))
    else:
        default_groups = [(u'users', u'User Group'),
                          (u'admin', u'Admin Group')]
    for name, description in default_groups:
        group = AuthGroup(name=name, description=description)
        session.add(group)

    session.flush()
    transaction.commit()


def initialize_sql(engine, settings):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
    if 'apex.velruse_providers' in settings:
        pass
        # SQLBase.metadata.bind = engine
        # SQLBase.metadata.create_all(engine)
    try:
        populate(settings)
    except IntegrityError:
        transaction.abort()
