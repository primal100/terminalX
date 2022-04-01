import logging
import os
from terminalX.connections import Client
from terminalX.types import CharSeq
import curses
from curses import ascii
from pathlib import Path
from terminalX.utils import static


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


class Terminal:
    def __init__(self, client: Client, stdscr: curses.window, fixed_colors: tuple[str, str] = None):
        self.client = client
        self.stdscr = stdscr
        curses.use_default_colors()
        self.color_pair = get_color_pair(*fixed_colors) if fixed_colors else None
        height, width = self.stdscr.getmaxyx()
        self.stdscr.keypad(True)
        self.stdscr.timeout(50)
        self.stdscr.scrollok(True)
        self.stdscr.idcok(False)
        client.invoke_shell(height=height, recv_callback=self.on_recv)
        self.send_input()

    def send_input(self):
        while self.client.shell_active:
            char = self.stdscr.getch()
            if self.client.shell_active and not char == -1:
                value = special_keys.get(char) or chr(char)
                self.client.send(value)
        self.close()

    def addstr(self, lineno, char_seq: CharSeq):
        self.stdscr.addstr(
            lineno, char_seq['column'], char_seq['text'], char_seq['attrs'])

    def on_recv(self, data: bytes):
        if self.client.shell_active:
            cursors = self.client.cursors()
            cursors = (cursors[0], cursors[1])
            self.stdscr.move(*cursors)
            changes = self.client.display_screen_line_changes()
            for lineno, chars in changes.items():
                current_char_seq: CharSeq = {'column': 0, 'text': '', 'attrs': 0}  # Create first sequence for line
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

                if current_char_seq['text']:
                    self.addstr(lineno, current_char_seq)  # Write final sequence for this line
            self.stdscr.refresh()

    def close(self):
        self.stdscr.scrollok(False)
        self.client.close()
        self.client.wait_closed()


def main(stdscr: curses.window):
    host = '127.0.0.1'
    port = 22
    client = Client(host, port=port, x11=True, term='xterm-256color')
    client.connect()
    Terminal(client, stdscr)


if __name__ == "__main__":
    curses.wrapper(main)
