# -*- coding: utf-8 -*-

from flask import url_for, request, jsonify, Blueprint
from flask_cors import cross_origin
from app import app, db
from app.models import User, Token
from datetime import datetime
import re
import os
from app.email import send_password_reset_email, send_registration_notification
from config import get_settings, get_environment


user = Blueprint('user', __name__)

auth = get_settings('AUTH')
regexps = get_settings('REGEXP')
requirements = get_settings('REQUIREMENTS')
langs = get_settings('LANGS')
content = get_settings('CONTENT')
env = get_environment()


@user.route('{base_path}/user/regexps'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['GET'])
def get_user_regexps():
    return jsonify({
        'email_regexp': regexps['EMAIL'][env],
        'password_regexp': regexps['PASSWORD'][env],
        'password_requirements': requirements['PASSWORD'][env]
    }), 200


@user.route('{base_path}/user'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
@cross_origin()
def create_user():
    username = request.json.get('username')
    email = request.json.get('email')
    preferred_lang = request.json.get('preferredLang') or langs['DEFAULT'][env]
    password = request.json.get('password')
    repeat_password = request.json.get('repeatPassword')
    admin_secret = request.headers.get('ADMIN_SECRET')
    last_seen = datetime.utcnow()
    registered = datetime.utcnow()
    errors = []
    if auth['REGISTRATION_RESTRICTED'][env] and admin_secret != auth['ADMIN_SECRET'][env]:
        return jsonify({
            'errors': [
                {'field': 'username', 'message': 'Registration is restricted! Please, use feedback form or contact site admins to apply for registration.'},
                {'field': 'email', 'message': ' '},
                {'field': 'password', 'message': ' '},
                {'field': 'repeatPassword', 'message': ' '}
            ]
        }), 400
    if username is None:
        errors.append({'field': 'username', 'message': 'Required'})
    if password is None:
        errors.append({'field': 'password', 'message': 'Required'})
    if email is None:
        errors.append({'field': 'email', 'message': 'Required'})
    if password != repeat_password:
        errors.append({'field': 'repeatPassword', 'message': 'Password confirmation is invalid!'})
    if not re.match(regexps['USERNAME'][env], username):
        errors.append({'field': 'username', 'message': 'Bad username!'})
    if not re.match(regexps['EMAIL'][env], email):
        errors.append({'field': 'email', 'message': 'Bad email!'})
    if not re.match(regexps['PASSWORD'][env], password):
        errors.append({'field': 'password', 'message': requirements['PASSWORD'][env]})
    if User.query.filter_by(username=username.casefold()).count() > 0:
        errors.append(
            {'field': 'username', 'message': 'Username "{username}" is unavailable!'.format(username=username)})
    if User.query.filter_by(email=email).first() is not None:
        errors.append({'field': 'email', 'message': 'User with email {email} already exists!'.format(email=email)})
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


@user.route('{base_path}/user/<username>'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['GET'])
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
        'connectedRoomId': user.get_connected_room_id(),
        'stats': user.get_stats()
    }), 200


@user.route('{base_path}/user/token'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
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
            'expiresIn': auth['TOKEN_LIFETIME'][env],
            'connectedRoomId': user.get_connected_room_id()
        }), 201


@user.route('{base_path}/user/<username>'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['PUT'])
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
    preferred_lang = request.json.get('preferredLang') or langs['DEFAULT'][env]
    about_me = request.json.get('aboutMe')
    errors = []
    if not re.match(regexps['EMAIL'][env], email):
        errors.append({'field': 'email', 'message': 'Bad email!'})
    email_user = User.query.filter_by(email=email).first()
    if email_user is not None and email_user != modified_user:
        errors.append({'field': 'email', 'message': 'User with email {email} already exists!'.format(email=email)})
    if len(about_me) >= content['MAX_SYMBOLS'][env]:
        errors.append(
            {'field': 'aboutMe', 'message': 'About me section must be {max_symbols} symbols long'.format(max_symbols=content['MAX_SYMBOLS'][env])}
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
        'aboutMe': modified_user.about_me,
        'connectedRoomId': modified_user.get_connected_room_id(),
        'stats': modified_user.get_stats()
    }), 200


@user.route('{base_path}/user/password/recover'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
@cross_origin()
def send_password_recovery():

    email = request.json.get('email')
    username = request.json.get('username')
    if app.debug:
        print(email)
        print(username)
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


@user.route('{base_path}/user/password/reset'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
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
    if not re.match(regexps['PASSWORD'][env], new_password):
        errors.append({
            'field': 'newPassword',
            'message': requirements['PASSWORD'][env]
        })

    if errors:
        return jsonify({
            'errors': errors
        }), 400

    saved_token = Token.query.filter_by(token=token).first()
    requesting_user.set_password(new_password)
    saved_token.status='used'
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


@user.route('{base_path}/user/password/new'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
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
    if not re.match(regexps['PASSWORD'][env], new_password):
        errors.append({
            'field': 'newPassword',
            'message': requirements['PASSWORD'][env]
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


@user.route('{base_path}/user/<username>/profilepic'.format(base_path=get_settings('API_BASE_PATH')[env]), methods=['POST'])
@cross_origin()
def upload_profile_pic(username):
    token = request.headers.get('Token')
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
                    'message': 'You can update only your own profile picture ({username})!'.format(
                        username=str(requesting_user.username))
                }
            ]
        }), 401
    '''if 'avatar' not in request.files:
        return jsonify({
            'errors': [
                {
                    'message': 'No file in request!'
                }
            ]
        }), 403'''
    file = request.files['avatar']
    if app.debug:
        print(file.filename)
    if file.filename == '':
        return jsonify({
            'errors': [
                {
                    'message': 'No file selected for uploading!'
                }
            ]
        }), 403
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    if file_extension not in content['ALLOWED_FORMATS'][env].split(','):
        return jsonify({
            'errors': [
                {
                    'message': 'Only {allowed_formats} files allowed!'.format(allowed_formats = content['ALLOWED_FORMATS'][env])
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
    if file.content_length > content['MAX_SIZE'][env]:
        return jsonify({
            'errors': [
                {
                    'message': 'File size exceeds limit of {limit}!'.format(limit = app.config('MAX_CONTENT_SIZE'))
                }
            ]
        }), 403'''
    filename = str(modified_user.username) + '.' + file_extension
    try:
        file.save(os.path.join(content['UPLOAD_FOLDER'][env], filename))
    except Exception:
        return jsonify({
            'errors': [
                {
                    'message': "Couldn't upload file"
                }
            ]
        }), 403
    return jsonify(200)