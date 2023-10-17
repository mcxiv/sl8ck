# --------------------------------------------------
# server.py - Flask server for sl8ck
# Quentin Dufournet, 2023
# --------------------------------------------------
# Built-in
import datetime
import os
import sys

# 3rd party
from flask import Flask, redirect, url_for, request
from cryptography.fernet import Fernet
# --------------------------------------------------

app = Flask(__name__)


@app.route('/success/<text>')
def success(text):
    """ Return a success message (200)

    :param text: message to return
    :return: success message as a dict
    """

    return {'success': text}, 200


@app.route('/error/<text>')
def error(text):
    """ Return an error message (400)

    :param text: message to return
    :return: error message as a dict
    """

    return {'error': text}, 400


def store_message(user, message):
    """ Store a message in a file

    :param user: user who sent the message
    :param message: message to store
    """

    message = decrypt_message(message)
    date = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    with open('messages', 'a') as f:
        f.write(f'{date} - {user} : {message}\n')


def encrypt_message(message):
    """ Encrypt a message

    :param message: message to encrypt
    :return: encrypted message
    """

    key = os.environ['SL8CK_KEY'].encode()
    f = Fernet(key)

    return f.encrypt(message.encode()).decode()


def decrypt_message(message):
    """ Decrypt a message

    :param message: message to decrypt
    :param key: key to use for decryption
    :return: decrypted message
    """

    key = os.environ['SL8CK_KEY'].encode()
    f = Fernet(key)

    return f.decrypt(message.encode()).decode()


def retrieve_messages(size):
    """ Retrieve the last messages

    :param size: number of messages to retrieve
    :return: list of messages (Which are dicts)
    """

    with open('messages', 'r') as f:
        messages = f.readlines()[-int(size):]

    messages_as_dict = []
    for message in messages:
        message = {
            'date': message.split(' - ')[0],
            'user': message.split(' - ')[1].split(' : ')[0],
            'message': message.split(' - ')[1].split(' : ')[1].strip('\n')
        }
        if "'" in message['message']:
            message['message'] = message['message'].replace("'", '`')
        messages_as_dict.append(message)

    return messages_as_dict


@app.route('/message', methods=['POST', 'GET'])
def message():
    """ Store a message or retrieve the last messages

    :return: success message or error message
    """

    if request.method == 'POST':
        message = request.form['message']
        user = request.form['user']
        store_message(user, message)
        return redirect(url_for('success', text=message))
    elif request.method == 'GET':
        size = request.args.get('size')
        return redirect(url_for('success', text=encrypt_message(str(retrieve_messages(size)))))
    else:
        return redirect(url_for('error', text='Method not allowed'))


@app.route('/login', methods=['POST'])
def login():
    """ Store a login message

    :return: success message or error message
    """

    if request.method == 'POST':
        user = request.form['user']
        store_message(user, encrypt_message('Logged in'))
        return redirect(url_for('success', text=user))
    else:
        return redirect(url_for('error', text='Method not allowed'))


if __name__ == '__main__':
    try:
        os.environ['SL8CK_KEY']
    except KeyError:
        sys.exit('Please set the SL8CK_KEY environment variable')

    app.run(debug=True)
