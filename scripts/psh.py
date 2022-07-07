import logging
import os
import sys
from terminalX.connections import Client
from terminalX.types import CharSeq
import curses
from pathlib import Path
from terminalX.utils import static
import pdb
import threading


file_path = Path(os.path.realpath(__file__)).parent
log_file = file_path / "log.txt"


logger = logging.getLogger()
handler = logging.FileHandler(log_file, mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s %(lineno)d %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.info('Version %s', 1.0)


def exc_handler(type, value, tb):
    logger.exception("Uncaught exception: {0}".format(str(value)))


# Install exception handler
sys.excepthook = exc_handler


esc = chr(0x1b)

# https://www.gnu.org/software/screen/manual/html_node/Input-Translation.html
# https://unix.stackexchange.com/questions/659649/how-to-find-the-escape-sequence-for-shift-pageup-shift-pagedown
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
    curses.KEY_SPREVIOUS: esc + "0[5;2~",
    curses.KEY_SNEXT: esc + "0[6;2~",

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


color_translation = {
    'default': -1,
    'black': curses.COLOR_BLACK,
    'blue': curses.COLOR_BLUE,
    'cyan': curses.COLOR_CYAN,
    'green': curses.COLOR_GREEN,
    'magenta': curses.COLOR_MAGENTA,
    'red': curses.COLOR_RED,
    'white': curses.COLOR_WHITE,
    'yellow': curses.COLOR_YELLOW,
}


color_pairs = {
    'black': {
         'white': 0
    }
}


@static(last_color_pair_no=0)
def get_color_pair(bg: str, fg: str) -> int:
    if all(color == 'default' for color in (bg, fg)):
        return 0
    if not (color_pair_no := color_pairs.get(bg, {}).get(fg, None)):
        color_pair_no = get_color_pair.last_color_pair_no + 1

        colors = color_translation.get(bg), color_translation.get(fg)   # Color couple has not been initialized
        if not colors[0] or not colors[1]:
            # If one color is not available, better to use default for both to avoid a color conflict
            return 0

        curses.init_pair(color_pair_no, *colors)
        get_color_pair.last_color_pair_no = color_pair_no
        color_pairs[bg] = color_pairs.get(bg, {})
        color_pairs[bg][fg] = color_pair_no
    return curses.color_pair(color_pair_no)


indexes = {'i': 0}
scrolls = [0, 2, 3, 4, 6, 0]


class Terminal:
    def __init__(self, client: Client, stdscr: curses.window, fixed_colors: tuple[str, str] = None):
        self.resized = threading.Event()
        self.client = client
        self.stdscr = stdscr
        self.height, self.width = self.stdscr.getmaxyx()
        logger.info('Height: %s Width: %s', self.height, self.width)
        curses.use_default_colors()
        self.color_pair = get_color_pair(*fixed_colors) if fixed_colors else None
        self.stdscr.keypad(True)
        self.stdscr.timeout(50)
        self.stdscr.scrollok(True)
        self.stdscr.idcok(False)
        self.client.invoke_shell(height=self.height, width=self.width, recv_callback=self.on_recv)
        self.send_input()

    def resize_terminal(self):
        self.height, self.width = self.stdscr.getmaxyx()
        logger.info('Resizing to Height: %s Width: %s', self.height, self.width)
        self.stdscr.refresh()
        self.client.resize_terminal(height=self.height, width=self.width, logger=logger)
        self.resized.set()
        value = special_keys.get(curses.KEY_SNEXT)
        logger.info('Sending curses.KEY_SNEXT as %s', value)
        self.client.send(value)
        logger.info('Resize complete')

    def send_input(self):
        try:
            while self.client.shell_active:
                char = self.stdscr.getch()
                if self.client.shell_active and not char == -1:
                    logger.info('Captured %s', char)
                    if char == curses.KEY_RESIZE:
                        self.resize_terminal()
                    elif char == curses.KEY_SPREVIOUS:
                        self.client.scroll_up()
                    elif char == curses.KEY_SNEXT:
                        self.client.scroll_down()
                    else:
                        value = special_keys.get(char) or chr(char)
                        logger.info('Sending %s as %s', char, value)
                        self.client.send(value)
        except BaseException as e:
            logger.exception("Uncaught exception: {0}".format(str(e)))
        finally:
            self.close()

    def addstr(self, lineno, char_seq: CharSeq):
        logger.info('Adding %s chars to curses lineno %s column %s: %s', len(char_seq['text']), lineno, char_seq['column'], char_seq['text'])
        height, width = self.stdscr.getmaxyx()
        logger.info('Height: %s Width: %s', height, width)
        self.stdscr.addstr(lineno, char_seq['column'], char_seq['text'], char_seq['attrs'])

    def on_recv(self, data: bytes):
        logger.info('RECEIVED')
        logger.info(data)
        try:
            if self.client.shell_active:
                changes = self.client.display_screen_line_changes()
                logger.info('The following lines have changed: %s', list(changes.keys()))
                for lineno, chars in changes.items():
                    logger.info('Line %s has %s chars', lineno, len(chars))
                    column = 0
                    current_char_seq: CharSeq = {'column': column, 'text': '', 'attrs': 0}  # Create first sequence for line
                    for column, char in chars.items():
                        text = char.data
                        attrs = self.color_pair if self.color_pair else get_color_pair(char.fg, char.bg)
                        if char.bold:
                            attrs += curses.A_BOLD
                        if char.italics:
                            attrs += curses.A_ITALIC
                        if char.underscore:
                            attrs += curses.A_UNDERLINE
                        if char.strikethrough:
                            text = text + "\u0336"   # Strikethrough not directly supported in curses
                        if char.reverse:
                            attrs += curses.A_REVERSE
                        if getattr(char, "blink", False):       # Blink added to pyte but not in latest official release yet
                            attrs += curses.A_BLINK
                        if not text:
                            current_char_seq['text'] = text     # Initial char sequence
                            current_char_seq['attrs'] = attrs
                        elif attrs == current_char_seq['attrs']:
                            current_char_seq['text'] += text   # Append to existing string with same attrs
                        else:
                            # Attrs have changed. Write old character sequence and create new
                            self.addstr(lineno, current_char_seq)
                            current_char_seq = {'text': char.data, 'attrs': attrs, 'column': column}

                    logger.info('Adding line 1')
                    if current_char_seq['text']:
                        logger.info('Adding line 2')
                        self.addstr(lineno, current_char_seq)  # Write final sequence for this line

                    # Delete remaining characters in line
                    logger.info('Adding line 3')
                    column += 1
                    text = ' '.join(['' for _ in range(column, self.width)])
                    if text:
                        logger.info('Deleting remaining chars')
                        current_char_seq: CharSeq = {'column': column, 'text': text, 'attrs': 0}
                        self.addstr(lineno, current_char_seq)

                cursors = self.client.cursors()
                cursors = (cursors[0], cursors[1])
                logger.info('Setting cursors to %s %s', cursors[0], cursors[1])
                self.stdscr.move(*cursors)
                self.stdscr.refresh()

                logger.info('Cursors are at %s', self.stdscr.getyx())
        except BaseException as e:
            logger.exception("Uncaught exception: {0}".format(str(e)))
            self.client.close()

    def close(self):
        self.stdscr.scrollok(False)
        self.client.close()
        self.client.wait_closed()


def main(stdscr: curses.window, client: Client):
    Terminal(client, stdscr)


def connect() -> Client:
    host = '127.0.0.1'
    port = 22
    logger.info('Connecting to %s', host)
    client = Client(host, port=port, x11=True, term='xterm-256color', known_hosts_policy="auto")
    client.connect()
    return client


if __name__ == "__main__":
    client = connect()
    curses.wrapper(main, client)
