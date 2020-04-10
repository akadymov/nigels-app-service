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


@app.route('/user', methods=['POST'])
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
            'registered': user.registered
        }), \
        201, \
        {'Location': url_for('get_user', username=username, _external=True)}


@app.route('/user/<username>', methods=['GET'])
def get_user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404, 'User {username} not found!'.format(username=username))
    return jsonify({
        'username': user.username,
        'email': user.email,
        'preferred_lang': user.preferred_language,
        'registered': user.registered,
        'about_me': user.about_me
    }), 201



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


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
@app.route('/rooms', methods=['GET'])
def index():
    rooms = Room.query.all()
    rooms_json = []
    """for room in rooms:
        rooms_json.append({
            'room_id': room.id,
            'room_name': room.room_name,
            'host': room.host.username,
            'created': room.created,
            'finished': room.finished,
            'connected_users': room.connected_users.count()
        })"""

    # temporary mock up

    rooms = [
        {
            'id': 1,
            'room_name': u'First Room',
            'host':  'akadymov',
            'created': '2020-04-08 14:00:00 GMT',
            'finished': None,
            'connected_users': 2
        },
        {
            'id': 2,
            'room_name': u'Second Room',
            'host': 'gsukhy',
            'created': '2020-04-08 14:30:00 GMT',
            'finished': None,
            'connected_users': 0
        }
    ]
    for room in rooms:
        rooms_json.append({
            'room_id': room['id'],
            'room_name': room['room_name'],
            'host': room['host'],
            'created': room['created'],
            'finished': room['finished'],
            'connected_users': room['connected_users'],
        })
    if not current_user.is_anonymous:
        u = User.query.filter_by(username=current_user.username).first()
        rooms_json.append({
            'current_user': {
                'username': u.username,
                'email': u.email,
                'preferred_lang': u.preferred_language,
                'facebook_pic': u.facebook_pic
            }
        })

    return jsonify({'rooms': rooms_json})


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
