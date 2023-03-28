from threading import Thread
from flask import render_template
from flask_mail import Message
from app import app, mail
from config import get_settings, get_environment

auth = get_settings('AUTH')
mail_settings = get_settings('MAIL')
env = get_environment()

def send_async_email(app, msg):
    #if app.config['ENVIRONMENT'] != 'TEST':  # no sending mails within auto-tests
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    if app.debug:
        print('Sending message with subject "' + str(subject) + '" from sender ' + str(sender) + ' to emails ' + str(recipients) + ')...')
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email('[Nigels App] Reset Your Password',
               sender=auth['ADMINS'][env].split(',')[0],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt',
                                         user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token))


def send_registration_notification(user):
    send_email('[Nigels App] Welcome letter',
               sender=auth['ADMINS'][env].split(',')[0],
               recipients=[user.email],
               text_body=render_template('email/register.txt',
                                         user=user),
               html_body=render_template('email/register.html',
                                         user=user))

def send_feedback(message, sender_email=None, sender_name=None):
    if not sender_email:
        sender_email = mail_settings['USERNAME'][env]
    if not sender_name:
        sender_name = 'Nigels app anonymous user'
    send_email(
        '[Nigels App] Feedback from user',
        sender=(sender_name, sender_email),
        recipients=auth['ADMINS'][env].split(','),
        text_body=render_template('email/feedback.txt', message=message, sender_name=sender_name),
        html_body=render_template('email/feedback.html', message=message, sender_name=sender_name)
    )

