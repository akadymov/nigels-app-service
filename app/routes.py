from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm
from app.models import User, Room
from app.social_login import OAuthSignIn
from datetime import datetime


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