import asyncio
from base_service import BaseService
import pty
import subprocess
import struct

import select
import os
import termios
import time
import threading
import signal
from sys import platform

if platform == "linux" or platform == "linux2":
    import fcntl

fd = None
child_pid = None

class Terminal(BaseService):
    
    def __init__(self, id, queue):
        self.debug = True
        super(Terminal, self).__init__(id, queue)

    async def Start(self):
        await self.Debug("Started")

    async def _connect(self, args):
        try:
            global fd
            global child_pid
            message = args.message[0]
            self.connectionId = message["connectionId"]
            self.user = message["user"]
            await self.Debug(f"Starting terminal for {self.user} ")
            if child_pid:
                # already started child process, don't start another
                # write a new line so that when a client refresh the shell prompt is printed
                os.write(fd, "\n".encode())
                return

            # create child process attached to a pty we can read from and write to
            (child_pid, fd) = pty.fork()

            if child_pid == 0:
                # this is the child process fork.
                # anything printed here will show up in the pty, including the output
                # of this subprocess
                subprocess.run('bash')

            else:
                # this is the parent process fork.
                self.background_thread = threading.Thread(target=self.read_and_forward_pty_output)
                self.background_thread.start()

        except Exception as e:
            await self.Debug(f"Unable to start terminal: {e}")
    
    async def _disconnect(self, args):
        global fd
        global child_pid

        if child_pid:
            # kill pty process
            os.kill(child_pid,signal.SIGKILL)
            os.wait()
            await self.Debug(f"Terminated terminal for {self.user} ")

        # reset the variables
        fd = None
        child_pid = None
    
    async def _forward_command(self, args):
        try:
            # create child process attached to a pty we can read from and write to
            os.write(fd, args.message[0].encode())

        except Exception as e:
            await self.Debug(f"Unable to start terminal: {e}")

    def read_and_forward_pty_output(self):
        global fd
        max_read_bytes = 1024 * 20
        while True:
            time.sleep(0.01)
            if fd:
                timeout_sec = 0
                (data_ready, _, _) = select.select([fd], [], [], timeout_sec)
                if data_ready:
                    output = os.read(fd, max_read_bytes).decode()
                    message = {
                        'connectionId': self.connectionId,
                        'data': output
                    }
                    asyncio.run(self.SubmitAction("msb", "terminal_output", message))
                    
            else:
                asyncio.run(self.Debug("Process killed"))
                return 

    def set_winsize(self, fd, row, col, xpix=0, ypix=0):
        if platform == "linux" or platform == "linux2":
            winsize = struct.pack("HHHH", row, col, xpix, ypix)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)