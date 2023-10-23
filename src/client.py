# --------------------------------------------------
# client.py - Client (CLI) for sl8ck
# Quentin Dufournet, 2023
# --------------------------------------------------
# Built-in
from datetime import datetime
import sys
import threading
import time
import argparse
import os

# 3rd party
import requests
from rich import print as rprint
from cryptography.fernet import Fernet, InvalidToken

# --------------------------------------------------


class MySl8ck():
    def __init__(self, url, room):
        self.url = url
        self.kill_thread = False
        self.previous_messages = None
        self.new_messages = None
        self.room = room

        if self.login() != 200:
            sys.exit('Login failed')

        try:
            self.new_messages = self.get_messages()['success']
            self.new_messages = raw_messages_to_list(self.new_messages)
            self.new_messages = [decrypt_message(
                message) for message in self.new_messages]
        except InvalidToken:
            sys.exit(f'Wrong key for room {args.room}')

        self.send_message('joined the room')

    def login(self):
        """ Login to the server

        :return: True if login was successful, False otherwise
        """

        self.user = input('Enter username: ')
        print()
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

        date = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        message = encrypt_message(f'{date} - {self.user} : {message}') + '\n'
        response = requests.post(
            f'{self.url}/message/{self.room}', data={'user': self.user, 'message': message})
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

        response = requests.get(
            f'{self.url}/message/{self.room}', params={'size': 25})
        if response.status_code != 200:
            sys.exit('Error while retrieving messages')
        return response.json()

    def refresh_screen(self):
        """ Refresh the screen and print the last messages """

        os.system('clear') if os.name == 'posix' else os.system('cls')
        refresh_messages = self.get_messages()['success']
        refresh_messages = raw_messages_to_list(refresh_messages)
        refresh_messages = [decrypt_message(
            message) for message in refresh_messages]
        refresh_messages = messages_to_dict(refresh_messages)

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

    return f.encrypt(message.encode()).decode()


def decrypt_message(message):
    """ Decrypt a message

    :param message: Message to decrypt
    :return: Decrypted message
    """

    key = os.environ['SL8CK_KEY'].encode()
    f = Fernet(key)

    try:
        return f.decrypt(message.encode()).decode()
    except InvalidToken:
        sys.exit(f'Wrong key for room {args.room}')


def parse_args():
    """ Arguments parser """

    parser = argparse.ArgumentParser(description='Client for sl8ck')

    parser.add_argument('-u', '--url', type=str, default='http://localhost:5000',
                        help='URL of the server')
    parser.add_argument('-k', '--key', type=str, default=None,
                        help='Key to encrypt/decrypt messages')
    parser.add_argument('-r', '--room', type=str, default='1114',
                        help='Room to join')

    return parser.parse_args()


def raw_messages_to_list(messages):
    """ Convert raw messages to a list of messages

    :param messages: Raw messages
    :return: List of messages
    """

    return messages.strip(
        '[]').replace(
        "'", '').replace(
        ', ', '').split(
        '\\n')[:-1]


def messages_to_dict(messages):
    """ Convert messages to a list of dict 

    :param messages: List of messages
    """

    messages_as_dict = []
    for message in messages:
        message = {
            'date': message.split(' - ')[0],
            'user': message.split(' - ')[1].split(' : ')[0],
            'message': message.split(' - ')[1].split(' : ')[1].strip('\n')
        }
        messages_as_dict.append(message)
    return messages_as_dict


def main_thread(sl):
    """ Main thread (Fetch messages and print them)

    :param sl: MySl8ck object
    """

    started = time.time()
    while not sl.kill_thread:
        if time.time() - started >= 5:
            sl.new_messages = sl.get_messages()['success']
            sl.new_messages = raw_messages_to_list(sl.new_messages)
            sl.new_messages = [decrypt_message(
                message) for message in sl.new_messages]
            sl.new_messages = messages_to_dict(sl.new_messages)
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
        sl.send_message('left the room')
        sl.kill_thread = True
        sys.exit()
    elif command == ':clear':
        os.system('clear') if os.name == 'posix' else os.system('cls')
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
    if args.key:
        os.environ['SL8CK_KEY'] = args.key
    try:
        os.environ['SL8CK_KEY']
    except KeyError:
        sys.exit('Please set the SL8CK_KEY environment variable')

    print_welcome()

    sl = MySl8ck(args.url, args.room)

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
            sl.send_message('left the room')
            sl.kill_thread = True
            sys.exit()
