import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OAUTH_CREDENTIALS = {
        'facebook': {
            'id': os.environ.get('facebook_id'),
            'secret': os.environ.get('facebook_secret')
        }
    }
    USERNAME_REGEXP = os.environ.get('USERNAME_REGEXP') or "^[a-zA-Z][a-zA-Z0-9- _\.]{1,20}$"
    PASSWORD_REGEXP = os.environ.get('PASSWORD_REGEXP') or "(?=^.{8,}$)(?=.*[a-z])(?=.*[A-Z])(?!.*\s).*$"
    EMAIL_REGEXP = os.environ.get('EMAIL_REGEXP') or "(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    TOKEN_LIFETIME = os.environ.get('TOKEN_LIFETIME') or 86400  # 24 hours
    API_BASE_PATH = os.environ.get('API_BASE_PATH') or '/api/v0'
    MAX_USERS_PER_ROOM = os.environ.get('MAX_USERS_PER_ROOM') or 10
    DEFAULT_LANG = os.environ.get('DEFAULT_LANG') or 'en'
    MIN_PLAYER_TO_START = os.environ.get('MIN_PLAYER_TO_START') or 2
    MAX_PLAYER_TO_START = os.environ.get('MAX_PLAYER_TO_START') or 10
