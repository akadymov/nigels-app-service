# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, abort, Blueprint, Response
from app import app, db
from app.models import User
from datetime import datetime
import re


user = Blueprint('user', __name__)


@user.route('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def create_user():
    username = request.json.get('username')
    email = request.json.get('email')
    preferred_lang = request.json.get('preferred_lang') or app.config['DEFAULT_LANG']
    password = request.json.get('password')
    last_seen = datetime.utcnow()
    registered = datetime.utcnow()
    if username is None or \
            password is None or \
            email is None:
        abort(400, 'Missing mandatory arguments (username, password or email)!')
    if not re.match(app.config['USERNAME_REGEXP'], password):
        abort(400, 'Bad username!')
    if not re.match(app.config['EMAIL_REGEXP'], email):
        abort(400, 'Bad email!')
    if not re.match(app.config['PASSWORD_REGEXP'], password):
        abort(400, 'Password does not satisfy security requirements!')
    if User.query.filter_by(username=username).first() is not None:
        abort(400, 'User with username {username} already exists!'.format(username=username))
    if User.query.filter_by(email=email).first() is not None:
        abort(400, 'User with email {email} already exists!'.format(email=email))
    if preferred_lang not in ['ru', 'en']:
        abort(400, 'Language {lang} is not supported!'.format(lang=preferred_lang))
    user = User(
        username=username,
        email=email,
        preferred_language=preferred_lang,
        last_seen=last_seen,
        registered=registered
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return \
        jsonify({
            'username': user.username,
            'email': user.email,
            'preferred_lang': user.preferred_language,
            'registered': user.registered,
            'last_seen': user.last_seen,
            'about_me': user.about_me
        }), \
        201, \
        {'Location': url_for('user.get_user', username=username, _external=True)}


@user.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
def get_user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404, 'User {username} not found!'.format(username=username))
    return jsonify({
        'username': user.username,
        'email': user.email,
        'preferred_lang': user.preferred_language,
        'registered': user.registered,
        'last_seen': user.last_seen,
        'about_me': user.about_me
    }), 200


@user.route('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def post_token():
    username = request.json.get('username')
    password = request.json.get('password')
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(str(password)):
        abort(401, 'Invalid username or password')
    else:
        token = user.generate_auth_token()
        return jsonify({
            'token': token.decode('ascii'),
            'expires_in': app.config['TOKEN_LIFETIME']
        })


@user.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['PUT'])
def edit_user(username):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('user.post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('user.post_token')))

    modified_user = User.query.filter_by(username=username).first()
    if modified_user is None:
        abort(404, 'User {username} not found!'.format(username=username))
    if modified_user != requesting_user:
        abort(401, 'You can update only your own profile ({username})!'.format(username=str(requesting_user)))

    email = request.json.get('email') or modified_user.email
    about_me = request.json.get('about_me') or modified_user.about_me
    preferred_lang = request.json.get('preferred_lang') or modified_user.preferred_language
    if not re.match(app.config['EMAIL_REGEXP'], email):
        abort(400, 'Bad email!')
    conflict_user = User.query.filter_by(email=email).first()
    if conflict_user is not None and conflict_user != modified_user:
        abort(400, 'User with email {email} already exists!'.format(email=email))
    if preferred_lang not in ['ru', 'en']:
        abort(400, 'Language {lang} is not supported!'.format(lang=preferred_lang))

    modified_user.email = email
    modified_user.about_me = about_me
    modified_user.preferred_language = preferred_lang
    modified_user.last_seen = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'username': modified_user.username,
        'email': modified_user.email,
        'preferred_lang': modified_user.preferred_language,
        'registered': modified_user.registered,
        'last_seen': modified_user.last_seen,
        'about_me': modified_user.about_me
    }), 200
