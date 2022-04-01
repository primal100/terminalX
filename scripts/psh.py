import logging
import os
import threading
import time

from terminalX.connections import Client
import curses
from pathlib import Path


file_path = Path(os.path.realpath(__file__)).parent
log_file = file_path / "log.txt"


logger = logging.getLogger()
handler = logging.FileHandler(log_file, mode='w')
# handler.setFormatter(logging.Formatter('%(asctime)s %(level)s %(module)s %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


esc = chr(0x1b)

# https://www.gnu.org/software/screen/manual/html_node/Input-Translation.html
special_keys = {
    curses.KEY_UP: esc + "OA",
    curses.KEY_DOWN: esc + "OB",
    curses.KEY_RIGHT: esc + "OC",
    curses.KEY_LEFT: esc + "OD",
    curses.KEY_HOME: esc + "[1~",
    curses.KEY_END: esc + "[4~",
    curses.KEY_IC: esc + "[2~",
    curses.KEY_DC: esc + "[3~",
    curses.KEY_NPAGE: esc + "[5~",
    curses.KEY_PPAGE: esc + "[6~",
    curses.KEY_F0: esc + "[10~",
    curses.KEY_F1: esc + "OP",
    curses.KEY_F2: esc + "OQ",
    curses.KEY_F3: esc + "OR",
    curses.KEY_F4: esc + "OS",
    curses.KEY_F5: esc + "O[15~",
    curses.KEY_F6: esc + "O[17~",
    curses.KEY_F7: esc + "O[18~",
    curses.KEY_F8: esc + "O[19~",
    curses.KEY_F9: esc + "O[20~",
    curses.KEY_F10: esc + "O[21~",
    curses.KEY_F11: esc + "O[23~",
    curses.KEY_F12: esc + "O[24~",
    curses.PADENTER: esc + "OM",
    curses.PADSTOP: esc + "On",
    curses.PADPLUS: esc + "Ok",
    curses.PADMINUS: esc + "Om",
    curses.PADSLASH: esc + "Oo",
    curses.PADSTAR: esc + "Oj",
    curses.PAD0: esc + "Op",

    curses.KEY_C1: '1',
    curses.KEY_C2: '2',
    curses.KEY_C3: '3',
    curses.KEY_B1: '4',
    curses.KEY_B2: '5',
    curses.KEY_B3: '6',
    curses.KEY_A1: '7',
    curses.KEY_A2: '8',
    curses.KEY_A3: '9'

    # Application Codes:
    # curses.KEY_C1: esc + "Oq",
    # curses.KEY_C2: esc + "Oq",
    # curses.KEY_C3: esc + "Os",
    # curses.KEY_B1: esc + "Ot",
    # curses.KEY_B2: esc + "Ou",
    # curses.KEY_B3: esc + "Ov",
    # curses.KEY_A1: esc + "Ow",
    # curses.KEY_A2: esc + "Ox",
    # curses.KEY_A3: esc + "Oy"
}


class Terminal:
    def __init__(self, client: Client, stdscr: curses.window):
        self.client = client
        self.stdscr = stdscr
        begin_x = 20
        begin_y = 7
        print('MAX SIZE:')
        print(self.stdscr.getmaxyx())
        height, width = self.stdscr.getmaxyx()
        self.stdscr.keypad(True)
        # self.stdscr.timeout(250)
        self.stdscr.scrollok(True)
        self.stdscr.idcok(True)
        client.invoke_shell(height=height, recv_callback=self.on_recv)
        self.send_input()

    def send_input(self):
        logger.debug('send chars')
        while self.client.shell_active:
            logger.debug('getch')
            char = self.stdscr.getch()
            if self.client.shell_active and not char == -1:
                print('Following char received')
                print(char)
                logger.debug('Following char was input and being sent %s', char)
                value = special_keys.get(char) or chr(char)
                print('sending', char)
                self.client.send(value)
        self.close()

    def on_recv(self, data: bytes):
        logger.debug('Received data')
        logger.debug(data)
        text = self.client.display_screen_as_text()
        logger.debug(text)
        print(text)
        logger.debug('Adding String')
        self.stdscr.addstr(0, 0, text)
        logger.debug('String added')
        cursors = self.client.cursors()
        print(cursors)
        cursors = (cursors[0], cursors[1])
        logger.debug('Cursors current position %s', curses.getsyx())
        logger.debug('Cursors window current position %s', self.stdscr.getyx())
        logger.debug('Setting cursors to %s', cursors)
        self.stdscr.move(*cursors)
        logger.debug('Cursors set to %s', cursors)
        logger.debug('Cursors current position %s', curses.getsyx())
        logger.debug('Cursors window current position %s', self.stdscr.getyx())
        self.stdscr.refresh()
        logger.debug('screen refreshed')

    def close(self):
        logger.debug('closing')
        self.stdscr.scrollok(False)
        self.client.close()
        logger.debug('waiting client closed')
        self.client.wait_closed()
        logger.debug('client closed')


def main(stdscr: curses.window):
    host = '127.0.0.1'
    port = 22
    client = Client(host, port=port, x11=False, term='xterm')
    client.connect()
    Terminal(client, stdscr)


if __name__ == "__main__":
    curses.wrapper(main)
