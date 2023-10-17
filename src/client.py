# --------------------------------------------------
# client.py - Client (CLI) for sl8ck
# Quentin Dufournet, 2023
# --------------------------------------------------
# Built-in
import sys
import threading
import time
import json
import argparse
import os

# 3rd party
import requests
from rich import print as rprint
from cryptography.fernet import Fernet

# --------------------------------------------------


class MySl8ck():
    def __init__(self, url):
        self.url = url
        if self.login() != 200:
            sys.exit('Login failed')

    def login(self):
        """ Login to the server

        :return: True if login was successful, False otherwise
        """

        self.user = input('Enter username: ')
        if self.user in ['', ' ', '\n']:
            sys.exit('Username cannot be empty')
        response = requests.post(f'{self.url}/login', data={'user': self.user})
        if response.status_code != 200:
            return False
        return 200

    def print_message(self, message):
        """ Print a message

        :param message: Message to print
        """

        rprint(
            f'[bold][blue][{message["date"]}][/blue] [magenta]{message["user"]}[/magenta][/bold] : {message["message"]}')

    def send_message(self, message):
        """ Send a message to the server

        :param message: Message to send
        """

        message = encrypt_message(message)
        response = requests.post(
            f'{self.url}/message', data={'user': self.user, 'message': message})
        if response.status_code != 200:
            sys.exit('Error while sending message')

    def diff_messages(self, previous, new):
        """ Print the difference between two lists of messages

        :param previous: List of previous messages
        :param new: List of new messages
        """

        if previous != new:
            for message in new:
                if message not in previous:
                    self.print_message(message)

    def get_messages(self):
        """ Get messages from the server

        :return: List of messages
        """

        response = requests.get(f'{self.url}/message', params={'size': 25})
        if response.status_code != 200:
            sys.exit('Error while retrieving messages')
        return response.json()


def encrypt_message(message):
    """ Encrypt a message

    :param message: Message to encrypt
    :return: Encrypted message
    """

    key = os.environ['SL8CK_KEY'].encode()
    f = Fernet(key)

    return f.encrypt(message.encode()).decode(), key.decode()


def decrypt_message(message):
    """ Decrypt a message

    :param message: Message to decrypt
    :return: Decrypted message
    """

    key = os.environ['SL8CK_KEY'].encode()
    f = Fernet(key)

    return f.decrypt(message.encode()).decode()


def parse_args():
    """ Arguments parser """

    parser = argparse.ArgumentParser(description='Client for sl8ck')

    parser.add_argument('-u', '--url', type=str, default='http://localhost:5000',
                        help='URL of the server')

    return parser.parse_args()


def message_as_str_to_dict(messages):
    """ Convert a list of messages as string to a list of messages as dict

    :param messages: List of messages as string
    :return: List of messages as dict
    """

    messages = messages.strip('[]').split('}, ')
    for message in messages:
        if not message.endswith('}'):
            message += '}'
        message = message.replace("'", '"')
        message = json.loads(message)
        yield message


def main_thread(sl):
    """ Main thread (Fetch messages and print them)

    :param sl: MySl8ck object
    """

    previous_messages = sl.get_messages()['success']
    previous_messages = decrypt_message(previous_messages)
    previous_messages = list(message_as_str_to_dict(previous_messages))
    for message in previous_messages:
        sl.print_message(message)

    while True:
        new_messages = sl.get_messages()['success']
        new_messages = decrypt_message(new_messages)
        new_messages = list(message_as_str_to_dict(new_messages))
        sl.diff_messages(previous_messages, new_messages)
        previous_messages = new_messages
        time.sleep(5)


if __name__ == '__main__':
    args = parse_args()

    try:
        os.environ['SL8CK_KEY']
    except KeyError:
        sys.exit('Please set the SL8CK_KEY environment variable')

    sl = MySl8ck(args.url)

    messages = sl.get_messages()['success']
    messages = decrypt_message(messages)
    messages = list(message_as_str_to_dict(messages))

    main = threading.Thread(target=main_thread, args=(sl,))
    main.start()

    while 1:
        message = input()
        if message not in ['', ' ', '\n']:
            sl.send_message(message)
