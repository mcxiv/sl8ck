# --------------------------------------------------
# server.py - Flask server for sl8ck
# Quentin Dufournet, 2023
# --------------------------------------------------
# Built-in
import os

# 3rd party
from flask import Flask, redirect, url_for, request
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


def store_message(room, message):
    """ Store a message in a file

    :param user: user who sent the message
    :param message: message to store
    """

    with open(f'dbs/messages_{room}.db', 'a') as f:
        f.write(message)


def retrieve_messages(room, size):
    """ Retrieve the last messages

    :param size: number of messages to retrieve
    :return: list of messages
    """

    if not os.path.exists(f'dbs/messages_{room}.db'):
        return []
    with open(f'dbs/messages_{room}.db', 'r') as f:
        messages = f.readlines()[-int(size):]

    return messages


@app.route('/message/<room>', methods=['POST', 'GET'])
def message(room):
    """ Store a message or retrieve the last messages

    :return: success message or error message
    """

    if request.method == 'POST':
        message = request.form['message']
        store_message(room, message)
        return redirect(url_for('success', text=message))
    elif request.method == 'GET':
        size = request.args.get('size')
        return redirect(url_for('success', text=retrieve_messages(room, size)))
    else:
        return redirect(url_for('error', text='Method not allowed'))


@app.route('/login', methods=['POST'])
def login():
    """ Store a login message

    :return: success message or error message
    """

    if request.method == 'POST':
        user = request.form['user']
        return redirect(url_for('success', text=user))
    else:
        return redirect(url_for('error', text='Method not allowed'))


if __name__ == '__main__':
    if not os.path.exists('./dbs/'):
        os.mkdir('./dbs/')
    app.run()
