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
    PASSWORD_REGEXP = os.environ.get('PASSWORD_REGEXP') or "(?=.*[a-z])(?=.*[A-Z]).{6,32}$"
    PASSWORD_REQUIREMENTS = os.environ.get('PASSWORD_REQUIREMENTS') or '6 to 32 characters, uppercase and lowercase'
    EMAIL_REGEXP = os.environ.get('EMAIL_REGEXP') or "(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    ALLOWED_LANGS = os.environ.get('ALLOWED_LANGS') or ['ru', 'en']
    TOKEN_LIFETIME = os.environ.get('TOKEN_LIFETIME') or 86400  # 24 hours
    API_BASE_PATH = os.environ.get('API_BASE_PATH') or '/api/v1'
    MAX_USERS_PER_ROOM = os.environ.get('MAX_USERS_PER_ROOM') or 6
    DEFAULT_LANG = os.environ.get('DEFAULT_LANG') or 'en'
    MIN_PLAYER_TO_START = os.environ.get('MIN_PLAYER_TO_START') or 2
    MAX_PLAYER_TO_START = os.environ.get('MAX_PLAYER_TO_START') or 10
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 465)
    MAIL_USE_TLS = False # os.environ.get('MAIL_USE_TLS')
    MAIL_USE_SSL = True # os.environ.get('MAIL_USE_SSL')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'nigelsappservice@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'ftriivstiomjrjbh'
    ADMINS = ['nigelsappservice@gmail.com', 'akhmed.kadymov@gmail.com']
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/Users/akadymov/reactJS Apps/naegels-app-responsive-ui/public/img/profile-pics'
    MAX_CONTENT_SIZE = os.environ.get('MAX_CONTENT_SIZE') or 300 * 1024
    CONTENT_ALLOWED_FORMATS = os.environ.get('CONTENT_ALLOWED_FORMATS') or ['png']
    MAX_TEXT_SYMBOLS = os.environ.get('MAX_ABOUT_ME_SYMBOLS') or 500
