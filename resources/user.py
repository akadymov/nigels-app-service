# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, abort, Blueprint, Response
from app import app, db
from app.models import User
from datetime import datetime
import re
from app.email import send_password_reset_email, send_registration_notification


user = Blueprint('user', __name__)


@user.route('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def create_user():
    username = request.json.get('username')
    email = request.json.get('email')
    preferred_lang = request.json.get('preferred-lang') or app.config['DEFAULT_LANG']
    password = request.json.get('password')
    repeat_password = request.json.get('repeat-password')
    last_seen = datetime.utcnow()
    registered = datetime.utcnow()
    missing_parameters = []
    if username is None:
        missing_parameters.append('username')
    if password is None:
        missing_parameters.append('password')
    if email is None:
        missing_parameters.append('email')
    if missing_parameters:
        return jsonify({
            'error': 'Missing mandatory arguments (username, password or email)!',
            'missing_fields': missing_parameters
        }), 400, {'Access-Control-Allow-Origin': 'localhost:3000', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods':'*'}
    if password != repeat_password:
        return jsonify({
            'error': 'Password confirmation is invalid!',
            'incorrect_fields': ['repeat-password']
        }), 400, {'Access-Control-Allow-Origin': 'localhost:3000', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods':'*'}
    if not re.match(app.config['USERNAME_REGEXP'], username):
        return jsonify({
            'error': 'Bad username!',
            'incorrect_fields': ['username']
        }), 400, {'Access-Control-Allow-Origin': 'localhost:3000', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods':'*'}
    if not re.match(app.config['EMAIL_REGEXP'], email):
        return jsonify({
            'error': 'Bad email!',
            'incorrect_fields': ['email']
        }), 400, {'Access-Control-Allow-Origin': 'localhost:3000'}
    if not re.match(app.config['PASSWORD_REGEXP'], password):
        return jsonify({
            'error': 'Password does not satisfy security requirements!',
            'incorrect_fields': ['password']
        }), 400, {'Access-Control-Allow-Origin': 'localhost:3000', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods':'*'}
    if User.query.filter_by(username=username.casefold()).count() > 0:
        return jsonify({
            'error': 'User with username {username} already exists!'.format(username=username),
            'incorrect_fields': ['username']
        }), 400, {'Access-Control-Allow-Origin': 'localhost:3000', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods':'*'}
    if User.query.filter_by(email=email).first() is not None:
        return jsonify({
            'error': 'User with email {email} already exists!'.format(email=email),
            'incorrect_fields': ['email']
        }), 400, {'Access-Control-Allow-Origin': 'localhost:3000', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods':'*'}
    if preferred_lang not in ['ru', 'en']:
        return jsonify({
            'error': 'Language {lang} is not supported!'.format(lang=preferred_lang),
            'incorrect_fields': ['preferred-lang']
        }), 400, {'Access-Control-Allow-Origin': 'localhost:3000', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods':'*'}
    user = User(
        username=username.casefold(),
        email=email.casefold(),
        preferred_language=preferred_lang,
        last_seen=last_seen,
        registered=registered
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    send_registration_notification(user)
    return \
        jsonify({
            'username': user.username.casefold(),
            'email': user.email,
            'preferred-lang': user.preferred_language,
            'registered': user.registered,
            'last_seen': user.last_seen,
            'about_me': user.about_me
        }), \
        201, \
        {'Location': url_for('user.get_user', username=username, _external=True),
         'Access-Control-Allow-Origin': 'localhost:3000', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods':'*'}


@user.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
def get_user(username):
    username = username.casefold()
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404, 'User {username} not found!'.format(username=username))
    return jsonify({
        'username': user.username,
        'email': user.email,
        'preferred-lang': user.preferred_language,
        'registered': user.registered,
        'last_seen': user.last_seen,
        'about_me': user.about_me
    }), 200


@user.route('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def post_token():
    username = request.json.get('username').casefold()
    password = request.json.get('password')
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(str(password)):
        abort(401, 'Invalid username or password')
    else:
        token = user.generate_auth_token()
        return jsonify({
            'token': token.decode('ascii'),
            'expires_in': app.config['TOKEN_LIFETIME']
        }), 201


@user.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['PUT'])
def edit_user(username):

    token = request.json.get('token')
    username = username.casefold()
    requesting_user = User.verify_api_auth_token(token)

    modified_user = User.query.filter_by(username=username).first()
    if modified_user is None:
        abort(404, 'User {username} not found!'.format(username=username))
    if modified_user != requesting_user:
        abort(401, 'You can update only your own profile ({username})!'.format(username=str(requesting_user.username)))

    email = request.json.get('email') or modified_user.email
    about_me = request.json.get('about_me') or modified_user.about_me
    preferred_lang = request.json.get('preferred-lang') or modified_user.preferred_language
    if not re.match(app.config['EMAIL_REGEXP'], email):
        abort(400, 'Bad email!')
    conflict_user = User.query.filter_by(email=email).first()
    if conflict_user is not None and conflict_user != modified_user:
        abort(400, 'User with email {email} already exists!'.format(email=email))
    if preferred_lang not in ['ru', 'en']:
        abort(400, 'Language {lang} is not supported!'.format(lang=preferred_lang))

    modified_user.email = email.casefold()
    modified_user.about_me = about_me
    modified_user.preferred_language = preferred_lang
    modified_user.last_seen = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'username': modified_user.username,
        'email': modified_user.email,
        'preferred-lang': modified_user.preferred_language,
        'registered': modified_user.registered,
        'last_seen': modified_user.last_seen,
        'about_me': modified_user.about_me
    }), 200


@user.route('{base_path}/user/password/recover'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def send_password_recovery():

    email = request.json.get('email')
    if not email:
        abort(400, 'Invalid email!')
    user = User.query.filter_by(email=email).first()
    if not user:
        abort(400, 'Invalid email!')
    send_password_reset_email(user)

    return jsonify('Password recovery link is sent!'), 200


@user.route('{base_path}/user/password/reset'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def reset_password():

    new_password = request.json.get('new_password')
    token = request.json.get('token')
    if not re.match(app.config['PASSWORD_REGEXP'], new_password):
        abort(400, 'Password does not satisfy security requirements!')
    user = User.verify_reset_password_token(token)
    if not user:
        abort(403, 'Invalid temporary token!')
    if not new_password:
        abort(400, 'Invalid new password!')

    user.set_password(new_password)
    db.session.commit()

    return jsonify('New password is saved!'), 200


@user.route('/user/reset_password/<token>', methods=['GET'])
def reset_password_form(token):

    user = User.verify_reset_password_token(token)
    if not user:
        return 'Token is invalid!'

    return 'Here come reset password form (under construction)!'