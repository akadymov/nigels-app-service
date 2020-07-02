import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    ENVIRONMENT = os.environ.get('ENVIRONMENT') or 'DEV'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    # Use following pattern for mysql or postgresql: db_type://db_username:password@host:port/db_name
    # Use following pattern for sqlite: sqlite:///path/to/db/folder/test.db
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OAUTH_CREDENTIALS = {
        'facebook': {
            'id': os.environ.get('facebook_id'),
            'secret': os.environ.get('facebook_secret')
        }
    }
    USERNAME_REGEXP = os.environ.get('USERNAME_REGEXP') or "^[a-zA-Z][a-zA-Z0-9-_\.]{1,35}$"
    PASSWORD_REGEXP = os.environ.get('PASSWORD_REGEXP') or "(?=^.{8,}$)(?=.*[a-z])(?=.*[A-Z])(?!.*\s).*$"
    EMAIL_REGEXP = os.environ.get('EMAIL_REGEXP') or "(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    ALLOWED_LANGS = os.environ.get('ALLOWED_LANGS') or ['ru', 'en']
    TOKEN_LIFETIME = os.environ.get('TOKEN_LIFETIME') or 86400  # 24 hours
    API_BASE_PATH = os.environ.get('API_BASE_PATH') or '/api/v1'
    MAX_USERS_PER_ROOM = os.environ.get('MAX_USERS_PER_ROOM') or 10
    DEFAULT_LANG = os.environ.get('DEFAULT_LANG') or 'en'
    MIN_PLAYER_TO_START = os.environ.get('MIN_PLAYER_TO_START') or 2
    MAX_PLAYER_TO_START = os.environ.get('MAX_PLAYER_TO_START') or 10
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') or False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'nigelsappservice@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['nigelsappservice@gmail.com', 'a-kadymov@yandex.ru']
    CORS_HEADERS = 'Content-Type'
