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
        self.kill_thread = False
        self.previous_messages = None
        self.new_messages = None

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
        self.refresh_screen()

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

    def refresh_screen(self):
        """ Refresh the screen and print the last messages """
        
        os.system('clear')
        refresh_messages = self.get_messages()['success']
        refresh_messages = decrypt_message(refresh_messages)
        refresh_messages = list(message_as_str_to_dict(refresh_messages))
        for message in refresh_messages:
            self.print_message(message)
        self.previous_messages = refresh_messages


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

    sl.previous_messages = sl.get_messages()['success']
    sl.previous_messages = decrypt_message(sl.previous_messages)
    sl.previous_messages = list(message_as_str_to_dict(sl.previous_messages))
    for message in sl.previous_messages:
        sl.print_message(message)

    started = time.time()
    while not sl.kill_thread:
        if time.time() - started >= 5:
            sl.new_messages = sl.get_messages()['success']
            sl.new_messages = decrypt_message(sl.new_messages)
            sl.new_messages = list(message_as_str_to_dict(sl.new_messages))
            sl.diff_messages(sl.previous_messages, sl.new_messages)
            sl.previous_messages = sl.new_messages
            started = time.time()
        else:
            time.sleep(0.1)


def internal_commands(sl, command):
    """ Internal commands 
    
    :param sl: MySl8ck object
    :param command: Command to execute
    """

    if command == ':help':
        rprint()
        rprint('[#36C5F0]' +
               '==============================\n' +
               '|[#E01E5A]       Commands list:       [/#E01E5A]|\n' +
               '==============================\n'
               '| :help - Show this help     |\n' +
               '| :exit - Exit the chat      |\n' +
               '| :clear - Clear the screen  |\n' +
               '| :cr - Clear and Refresh    |\n' +
               '=============================='
               '[/#36C5F0]'
               )
        rprint()
    elif command == ':exit':
        sl.send_message('left the chat')
        sl.kill_thread = True
        sys.exit()
    elif command == ':clear':
        os.system('clear')
    elif command == ':cr':
        sl.refresh_screen()


def print_welcome():
    """ Print the welcome message and the commands list """

    rprint('[#E01E5A]' +
           '==============================\n' +
           '|[#36C5F0]        Welcome on...       [/#36C5F0]|\n' +
           '==============================\n' +
           '|  ____  _  ___       _      |\n' +
           '| / ___|| |( _ )  ___| | __  |\n' +
           '| \___ \| |/ _ \ / __| |/ /  |\n' +
           '|  ___) | | (_) | (__|   <   |\n' +
           '| |____/|_|\___/ \___|_|\_\\  |\n' +
           '|                            |\n' +
           '==============================' +
           '[/#E01E5A]'
           )
    internal_commands(None, ':help')


if __name__ == '__main__':
    args = parse_args()

    try:
        os.environ['SL8CK_KEY']
    except KeyError:
        sys.exit('Please set the SL8CK_KEY environment variable')

    print_welcome()

    sl = MySl8ck(args.url)

    messages = sl.get_messages()['success']
    messages = decrypt_message(messages)
    messages = list(message_as_str_to_dict(messages))

    main = threading.Thread(target=main_thread, args=(sl,))
    main.start()

    commands_list = [':help', ':exit', ':clear', ':cr']

    while 1:
        try:
            message = input()
            if message not in ['', ' ', '\n'] and message not in commands_list:
                sl.send_message(message)
            elif message in commands_list:
                internal_commands(sl, message)
        except KeyboardInterrupt:
            sl.send_message('left the chat')
            sl.kill_thread = True
            sys.exit()
