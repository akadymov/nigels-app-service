# -*- coding: utf-8 -*-

from flask import render_template, flash, redirect, url_for, request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm
from app.models import User, Room
from app.social_login import OAuthSignIn
from datetime import datetime
import re


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    return 'This is Nigels App Service Home! Work In Progress!'


@app.route('{base_path}/user'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def new_user():
    username = request.json.get('username')
    email = request.json.get('email')
    preferred_lang = request.json.get('preferred_lang') or 'en'
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
        {'Location': url_for('get_user', username=username, _external=True)}


@app.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
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


@app.route('{base_path}/user/token'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
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


@app.route('{base_path}/user/<username>'.format(base_path=app.config['API_BASE_PATH']), methods=['PUT'])
def update_user(username):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

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


@app.route('{base_path}/room'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def create_room():

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    hosted_room = Room.query.filter_by(host=requesting_user, closed=None).first()
    if hosted_room:
        abort(403, 'User {username} already has opened room {room_name}! Close it by POST {close_room_url} before creating new one.'.format(
            username=requesting_user.username,
            room_name=hosted_room.room_name,
            close_room_url=url_for('close_room', room_id=hosted_room.id)
        ))

    room_name = request.json.get('room_name')
    new_room = Room(room_name=room_name, host=requesting_user, created=datetime.utcnow())
    db.session.add(new_room)
    new_room.connect(requesting_user)
    db.session.commit()

    return jsonify({
        'room_id': new_room.id,
        'room_name': new_room.room_name,
        'host': new_room.host.username,
        'created': new_room.created,
        'closed': new_room.closed,
        'connected_users': new_room.connected_users.count(),
        'status': 'open' if new_room.closed is None else 'closed',
        'connect': url_for('connect_room', room_id=new_room.id)
    }), 201


@app.route('{base_path}/room/<room_id>/close'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def close_room(room_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    target_room = Room.query.filter_by(id=room_id).first()
    if target_room is None:
        abort(404, 'Room with id {room_id} is not found!'.format(room_id=room_id))
    if target_room.closed is not None:
        abort(400, 'Room {room_name} is already closed!'.format(room_name=target_room.room_name))
    if target_room.host != requesting_user:
        abort(403, 'Only host can close the room!')

    for user in target_room.connected_users:
        target_room.disconnect(user)

    target_room.closed = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'room_id': target_room.id,
        'room_name': target_room.room_name,
        'host': target_room.host.username,
        'created': target_room.created,
        'status': 'open' if target_room.closed is None else 'closed',
        'closed': target_room.closed
    }), 201


@app.route('{base_path}/room/<room_id>/connect'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def connect_room(room_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    target_room = Room.query.filter_by(id=room_id).first()
    if target_room is None:
        abort(404, 'Room with id {room_id} is not found!'.format(room_id=room_id))
    if target_room.closed is not None:
        abort(400, 'Room {room_name} is closed!'.format(room_name=target_room.room_name))
    if target_room.is_connected(requesting_user):
        abort(400, 'User {username} is already connected to room {room_name}!'.format(username=requesting_user.username, room_name=target_room.room_name))
    if target_room.connected_users.count() >= app.config['MAX_USERS_PER_ROOM']:
        abort(403, 'Maximum number of players exceeded for room {room_name}!'.format(room_name=target_room.room_name))

    target_room.connect(requesting_user)
    db.session.commit()

    return jsonify(200)


@app.route('{base_path}/room/<room_id>/disconnect'.format(base_path=app.config['API_BASE_PATH']), methods=['POST'])
def disconnect_room(room_id):

    token = request.json.get('token')
    if token is None:
        abort(401, 'Authentication token is absent! You should request token by POST {post_token_url}'.format(post_token_url=url_for('post_token')))
    requesting_user = User.verify_auth_token(token)
    if requesting_user is None:
        abort(401, 'Authentication token is invalid! You should request new one by POST {post_token_url}'.format(post_token_url=url_for('post_token')))

    target_room = Room.query.filter_by(id=room_id).first()
    if target_room is None:
        abort(404, 'Room with id {room_id} is not found!'.format(room_id=room_id))
    if target_room.closed is not None:
        abort(400, 'Room {room_name} is closed!'.format(room_name=target_room.room_name))
    if not target_room.is_connected(requesting_user):
        abort(400, 'User {username} is not connected to room {room_name}!'.format(username=requesting_user.username, room_name=target_room.room_name))
    if target_room.host == requesting_user:
        abort(403, 'Host cannot disconnect the room!')

    target_room.disconnect(requesting_user)
    db.session.commit()

    return jsonify(200)


@app.route('{base_path}/room/all'.format(base_path=app.config['API_BASE_PATH']), methods=['GET'])
def get_rooms():
    rooms = Room.query.filter_by(closed=None).all()
    if str(request.args.get('closed')).lower() == 'y':
        rooms = Room.query.all()
    rooms_json = []
    for room in rooms:
        rooms_json.append({
            'room_id': room.id,
            'room_name': room.room_name,
            'host': room.host.username,
            'status': 'open' if room.closed is None else 'closed',
            'created': room.created,
            'closed': room.closed,
            'connected_users': room.connected_users.count(),
            'connect': url_for('connect_room', room_id=room.id)
        })

    return jsonify({'rooms': rooms_json}), 200


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            last_seen=datetime.utcnow(),
            registered=datetime.utcnow(),
            preferred_language=form.preferred_language.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


# social login oauth
@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


# social login callback oauth
@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    social_id, username, email, gender, timezone, locale, pic = oauth.callback()
    if social_id is None:
        flash('Authentication failed.')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()
    if user:
        user.facebook_pic = pic
        user.social_id = social_id
    else:
        user = User(social_id=social_id, username=username, email=email, facebook_pic=pic)
        db.session.add(user)
    db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))
