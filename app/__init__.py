from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config
from flask_mail import Mail
from flask_socketio import SocketIO


app = Flask(__name__)
app.config.from_object(Config)
CORS(app,resources={r"/*":{"origins":"*"}})
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'
mail = Mail(app)
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

from app import routes, models, socket
