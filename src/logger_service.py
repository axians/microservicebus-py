import asyncio, logging
from logging.handlers import RotatingFileHandler
from base_service import BaseService


logging.basicConfig (
    handlers=[RotatingFileHandler('/var/log/microservicebus-py.log', maxBytes=100000, backupCount=7)],
    format='%(asctime)s: %(message)s',
    encoding='utf-8',
    level=logging.WARNING
)

class Logger(BaseService):
    def __init__(self, id, queue):
        self.debug = True
        super(Logger, self).__init__(id, queue)

    async def Start(self):
        await self.Debug("Started")
        while True:
            await asyncio.sleep(0.1)
    async def msb_signed_in(self, args):
        pass
    
    async def StateUpdate(self, message):
        state = message.message[0]
        await self.Debug(f"Received: {message}")

    async def _change_debug(self, message):
        self.debug = message.message[0]
 
    async def _debug(self, message):
       logging.warning(f"[{message.source}] {bcolors.OKGREEN}DEGUG:{bcolors.ENDC} {message.message[0]}")
       if self.debug:
           await self.SubmitAction("msb", "_debug", message.message[0])
    
    async def _error(self, message):
       logging.error(f"mSB:[{message.source}] {bcolors.FAIL}ERROR:{bcolors.ENDC} {message.message[0]}")
       if self.debug:
           await self.SubmitAction("msb", "_debug", message.message[0])

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'