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
    USERNAME_REGEXP = "^[a-zA-Z][a-zA-Z0-9-_\.]{1,20}$"
    PASSWORD_REGEXP = "(?=^.{8,}$)(?=.*[a-z])(?=.*[A-Z])(?!.*\s).*$"
    EMAIL_REGEXP = "(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    TOKEN_LIFETIME = 600