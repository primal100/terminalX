import sys
from .connections import Client


class Terminal:
    def __init__(self, client: Client = None, width: int = 80, height: int = 24,
                 width_pixels: int = 0, height_pixels: int = 0, history: int = 100):
        self.client = client    # Client should be connected already
        self.width = width
        self.height = height
        self.width_pixels = width_pixels
        self.height_pixels = height_pixels
        self.history = history

    def start(self):
        self.client.invoke_shell(width=self.width, height=self.height, width_pixels=self.width_pixels,
                                 history=self.history, recv_callback=self.on_recv)
        try:
            while True:
                data = sys.stdin.read(1)
                if not data:
                    break
                self.client.send(data)
        except EOFError:
            # user hit ^Z or F6
            pass

    def on_recv(self):
        print(self.client.display_screen_as_text())


def start_local_terminal():
    client = Client('127.0.0.1')
    client.connect()
    t = Terminal(client)
    t.start()
