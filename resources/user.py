# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, abort, Blueprint, Response
from flask_cors import cross_origin
from app import app, db
from app.models import User
from datetime import datetime
import re
from app.email import send_password_reset_email, send_registration_notification


user = Blueprint('user', __name__)


@user.route('{base_path}/user/regexps'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
def get_user_regexps():
    return jsonify({
        'email_regexp': app.config['EMAIL_REGEXP'],
        'password_regexp': app.config['PASSWORD_REGEXP'],
        'allowed_lang_codes': app.config['ALLOWED_LANGS']
    }), 200


@user.route('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def create_user():
    username = request.json.get('username')
    email = request.json.get('email')
    preferred_lang = request.json.get('preferredLang') or app.config['DEFAULT_LANG']
    password = request.json.get('password')
    repeat_password = request.json.get('repeatPassword')
    last_seen = datetime.utcnow()
    registered = datetime.utcnow()
    errors = []
    if username is None:
        errors.append({'field': 'username', 'message': 'Required'})
    if password is None:
        errors.append({'field': 'password', 'message': 'Required'})
    if email is None:
        errors.append({'field': 'email', 'message': 'Required'})
    if password != repeat_password:
        errors.append({'field': 'repeatPassword', 'message': 'Password confirmation is invalid!'})
    if not re.match(app.config['USERNAME_REGEXP'], username):
        errors.append({'field': 'username', 'message': 'Bad username!'})
    if not re.match(app.config['EMAIL_REGEXP'], email):
        errors.append({'field': 'email', 'message': 'Bad email!'})
    if not re.match(app.config['PASSWORD_REGEXP'], password):
        errors.append({'field': 'password', 'message': 'Password does not satisfy security requirements!'})
    if User.query.filter_by(username=username.casefold()).count() > 0:
        errors.append(
            {'field': 'username', 'message': 'User with username {username} already exists!'.format(username=username)})
    if User.query.filter_by(email=email).first() is not None:
        errors.append({'field': 'email', 'message': 'User with email {email} already exists!'.format(email=email)})
    if preferred_lang not in app.config['ALLOWED_LANGS']:
        errors.append(
            {'field': 'preferredLang', 'message': 'Language {lang} is not supported!'.format(lang=preferred_lang)})
    if errors:
        return jsonify({
            'errors': errors
        }), 400
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
            'preferredLang': user.preferred_language,
            'registered': user.registered,
            'lastSeen': user.last_seen,
            'aboutMe': user.about_me
        }), \
        201, \
        {'Location': url_for('user.get_user', username=username, _external=True)}


@user.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
@cross_origin()
def get_user(username):
    username = username.casefold()
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404, 'User {username} not found!'.format(username=username))
    return jsonify({
        'username': user.username,
        'email': user.email,
        'preferredLang': user.preferred_language,
        'registered': user.registered,
        'lastSeen': user.last_seen,
        'aboutMe': user.about_me
    }), 200


@user.route('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def post_token():
    username = request.json.get('username').casefold()
    password = request.json.get('password')
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(str(password)):
        # abort(401, 'Invalid username or password')
        return jsonify({
            'errors': [
                {'field': 'password', 'message': 'Invalid username or password!'}
            ]
        }), 401
    else:
        token = user.generate_auth_token()
        return jsonify({
            'token': token,
            'expiresIn': app.config['TOKEN_LIFETIME']
        }), 201


@user.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['PUT'])
@cross_origin()
def edit_user(username):

    token = request.json.get('token')
    username = username.casefold()
    # print('editing user ' + str(username))
    requesting_user = User.verify_api_auth_token(token)
    if requesting_user is None:
        abort(401, 'Invalid username or authorization token!')

    modified_user = User.query.filter_by(username=username).first()
    if modified_user is None:
        abort(404, 'User {username} not found!'.format(username=username))
    if modified_user != requesting_user:
        abort(401, 'You can update only your own profile ({username})!'.format(username=str(requesting_user.username)))

    email = request.json.get('email') or modified_user.email
    about_me = request.json.get('aboutMe') or modified_user.about_me
    preferred_lang = request.json.get('preferredLang') or modified_user.preferred_language
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
        'preferredLang': modified_user.preferred_language,
        'registered': modified_user.registered,
        'lastSeen': modified_user.last_seen,
        'aboutMe': modified_user.about_me
    }), 200


@user.route('{base_path}/user/password/recover'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
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
@cross_origin()
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
@cross_origin()
def reset_password_form(token):

    user = User.verify_reset_password_token(token)
    if not user:
        return 'Token is invalid!'

    return 'Here come reset password form (under construction)!'