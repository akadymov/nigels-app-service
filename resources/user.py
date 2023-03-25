# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, Blueprint, Response
from flask_cors import cross_origin
from app import app, db
from app.models import User
from datetime import datetime
import re
import os
from werkzeug.utils import secure_filename
from app.email import send_password_reset_email, send_registration_notification


user = Blueprint('user', __name__)


@user.route('{base_path}/user/regexps'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
def get_user_regexps():
    return jsonify({
        'email_regexp': app.config['EMAIL_REGEXP'],
        'password_regexp': app.config['PASSWORD_REGEXP'],
        'password_requirements': app.config['PASSWORD_REQUIREMENTS'],
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
        errors.append({'field': 'password', 'message': app.config['PASSWORD_REQUIREMENTS']})
    if User.query.filter_by(username=username.casefold()).count() > 0:
        errors.append(
            {'field': 'username', 'message': 'Username "{username}" is unavailable!'.format(username=username)})
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
def get_user(username):
    username = username.casefold()
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({
            'errors': [
                {
                    'message': 'User {username} not found!'.format(username=username)
                }
            ]
        }), 404

    return jsonify({
        'username': user.username,
        'email': user.email,
        'preferredLang': user.preferred_language,
        'registered': user.registered,
        'lastSeen': user.last_seen,
        'aboutMe': user.about_me,
        'connectedRoomId': user.get_connected_room_id()
    }), 200


@user.route('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def post_token():
    username = request.json.get('username').casefold()
    password = request.json.get('password')
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(str(password)):
        return jsonify({
            'errors': [
                {'field': 'password', 'message': 'Invalid username or password!'},
                {'field': 'username', 'message': '   '}
            ]
        }), 401
    else:
        token = user.generate_auth_token()
        return jsonify({
            'token': token,
            'expiresIn': app.config['TOKEN_LIFETIME'],
            'connectedRoomId': user.get_connected_room_id()
        }), 201


@user.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['PUT'])
@cross_origin()
def edit_user(username):

    token = request.json.get('token')
    username = username.casefold()
    requesting_user = User.verify_api_auth_token(token)
    if requesting_user is None:
        return jsonify({
            'errors': [
                {
                    'message': 'Invalid username or authorization token!'
                }
            ]
        }), 401

    modified_user = User.query.filter_by(username=username).first()
    if modified_user is None:
        return jsonify({
            'errors': [
                {
                    'message': 'User {username} not found!'.format(username=username)
                }
            ]
        }), 404
    if modified_user != requesting_user:
        return jsonify({
            'errors': [
                {
                    'message': 'You can update only your own profile ({username})!'.format(username=str(requesting_user.username))
                }
            ]
        }), 401

    email = request.json.get('email')
    preferred_lang = request.json.get('preferredLang') or app.config['DEFAULT_LANG']
    about_me = request.json.get('aboutMe')
    errors = []
    if not re.match(app.config['EMAIL_REGEXP'], email):
        errors.append({'field': 'email', 'message': 'Bad email!'})
    email_user = User.query.filter_by(email=email).first()
    if email_user is not None and email_user != modified_user:
        errors.append({'field': 'email', 'message': 'User with email {email} already exists!'.format(email=email)})
    if preferred_lang not in app.config['ALLOWED_LANGS']:
        errors.append(
            {'field': 'preferredLang', 'message': 'Language {lang} is not supported!'.format(lang=preferred_lang)})
    if len(about_me) >= app.config['MAX_TEXT_SYMBOLS']:
        errors.append(
            {'field': 'aboutMe', 'message': 'About me section must be {max_symbols} symbols long'.format(max_symbols=app.config['MAX_TEXT_SYMBOLS'])}
        )

    if errors:
        return jsonify({
            'errors': errors
        }), 400

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
    username = request.json.get('username')
    if app.debug:
        print(email)
        print(username)
    errors = []
    err = False
    if not email:
        err = True
    if not username:
        err = True
    requesting_user = None
    if username and email:
        requesting_user = User.query.filter_by(username=username).first()
    if not requesting_user:
        err = True
    elif requesting_user.email != email:
        err = True

    if err:
        return jsonify({
            'errors': [
                {
                    'field': 'username',
                    'message': 'Invalid username or password'
                },
                {
                    'field': 'email',
                    'message': 'Invalid username or password'
                }
            ]
        }), 400

    send_password_reset_email(requesting_user)

    return jsonify('Password recovery link is sent!'), 200


@user.route('{base_path}/user/password/reset'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def reset_password():

    new_password = request.json.get('newPassword')
    password_repeat = request.json.get('repeatPassword')
    token = request.json.get('token')
    requesting_user = User.verify_reset_password_token(token)
    if not requesting_user:
        return jsonify({
            'errors': [
                {
                    'field': 'newPassword',
                    'message': 'Invalid reset password token!'
                },
                {
                    'field': 'repeatPassword',
                    'message': 'Invalid reset password token!'
                }
            ]
        }), 401
    errors = []
    if requesting_user is None:
        return jsonify({
            'errors': [
                {
                    'field': 'newPassword',
                    'message': 'Invalid reset password token!'
                },
                {
                    'field': 'repeatPassword',
                    'message': 'Invalid reset password token!'
                }
            ]
        }), 401
    if not new_password:
        errors.append({
            'field': 'newPassword',
            'message': 'New password is missing!'
        })
    if not password_repeat:
        errors.append({
            'field': 'repeatPassword',
            'message': 'Password confirmation is missing!'
        })
    if new_password != password_repeat:
        errors.append({
            'field': 'repeatPassword',
            'message': 'Password confirmation does not match!'
        })
    if not re.match(app.config['PASSWORD_REGEXP'], new_password):
        errors.append({
            'field': 'newPassword',
            'message': app.config['PASSWORD_REQUIREMENTS']
        })

    if errors:
        return jsonify({
            'errors': errors
        }), 400

    requesting_user.set_password(new_password)
    db.session.commit()

    return jsonify('New password is saved!'), 200


@user.route('/user/reset_password/<token>', methods=['GET'])
@cross_origin()
def reset_password_form(token):

    user = User.verify_reset_password_token(token)
    if not user:
        return jsonify({
            'errors': [
                {
                    'message': 'Token is invalid!'
                }
            ]
        })

    return 'Here comes reset password form (under construction)!'


@user.route('{base_path}/user/password/new'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def new_password():
    current_password = request.json.get('currentPassword')
    token = request.json.get('token')
    new_password = request.json.get('newPassword')
    password_repeat = request.json.get('passwordRepeat')
    requesting_user = User.verify_api_auth_token(token)
    errors = []
    if requesting_user is None:
        return jsonify({
            'errors': [
                {
                    'message': 'Invalid username or authorization token!'
                }
            ]
        }), 401
    if not current_password:
        errors.append({
            'field': 'newPassword',
            'message': 'Incorrect current password!'
        })
    if not new_password:
        errors.append({
            'field': 'newPassword',
            'message': 'New password is missing!'
        })
    if not password_repeat:
        errors.append({
            'field': 'passwordRepeat',
            'message': 'Password confirmation is missing!'
        })
    if new_password != password_repeat:
        errors.append({
            'field': 'passwordRepeat',
            'message': 'Password confirmation does not match!'
        })
    if not requesting_user.check_password(current_password):
        errors.append({
            'field': 'currentPassword',
            'message': 'Incorrect current password!'
        })
    if not re.match(app.config['PASSWORD_REGEXP'], new_password):
        errors.append({
            'field': 'newPassword',
            'message': app.config['PASSWORD_REQUIREMENTS']
        })

    if errors:
        return jsonify({
            'errors': errors
        }), 400
    else:
        if app.debug:
            print('setting new password')
            print(new_password)
        requesting_user.set_password(new_password)
        db.session.commit()

        return jsonify('New password is saved!'), 200


@user.route('{base_path}/user/<username>/profilepic'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
@cross_origin()
def upload_profile_pic(username):
    token = request.form.get('token')
    username = username.casefold()
    for f in request.form:
        print(f)
    print(token)
    print(username)
    requesting_user = User.verify_api_auth_token(token)
    if requesting_user is None:
        return jsonify({
            'errors': [
                {
                    'message': 'Invalid username or authorization token!'
                }
            ]
        }), 401

    modified_user = User.query.filter_by(username=username).first()
    if modified_user is None:
        return jsonify({
            'errors': [
                {
                    'message': 'User {username} not found!'.format(username=username)
                }
            ]
        }), 404
    if modified_user != requesting_user:
        return jsonify({
            'errors': [
                {
                    'message': 'You can update only your own profile picture ({username})!'.format(
                        username=str(requesting_user.username))
                }
            ]
        }), 401
    if 'avatar' not in request.files:
        return jsonify({
            'errors': [
                {
                    'message': 'No file in request!'
                }
            ]
        }), 403
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({
            'errors': [
                {
                    'message': 'No file selected for uploading!'
                }
            ]
        }), 403
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    if file_extension not in app.config['CONTENT_ALLOWED_FORMATS']:
        return jsonify({
            'errors': [
                {
                    'message': 'Only {allowed_formats} files allowed!'.format(allowed_formats = app.config['CONTENT_ALLOWED_FORMATS'])
                }
            ]
        }), 403
    '''if 'content_length' not in file:
        return jsonify({
            'errors': [
                {
                    'message': 'File size is not specified!'
                }
            ]
        }), 403
    if file.content_length > app.config['MAX_CONTENT_SIZE']:
        return jsonify({
            'errors': [
                {
                    'message': 'File size exceeds limit of {limit}!'.format(limit = app.config('MAX_CONTENT_SIZE'))
                }
            ]
        }), 403'''
    filename = str(modified_user.username) + '.' + file_extension
    try:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    except Exception:
        return jsonify({
            'errors': [
                {
                    'message': "Couldn't upload file"
                }
            ]
        }), 403
    return jsonify(200)