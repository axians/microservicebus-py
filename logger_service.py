import asyncio
from base_service import BaseService

class Logger(BaseService):
    def __init__(self, id, queue):
        self.debug = True
        super(Logger, self).__init__(id, queue)

    async def Start(self):
        await self.Debug("Started")
        while True:
            await asyncio.sleep(0.1)
    
    async def StateUpdate(self, message):
        state = message.message[0]
        state_exists = "msb-state" in state["desired"]
        if state_exists:
            if self.debug != state["desired"]["msb-state"]["debug"]:
                self.debug = state["desired"]["msb-state"]["debug"]
                await self.Debug(f"Console debugging is set to {self.debug}")

    async def _debug(self, message):
       print(f"mSB:[{message.source}] {bcolors.OKGREEN}DEGUG:{bcolors.ENDC} {message.message[0]}")
       if self.debug:
           await self.SubmitAction("msb", "_debug", message.message[0])
    
    async def _error(self, message):
       print(f"mSB:[{message.source}] {bcolors.FAIL}ERROR:{bcolors.ENDC} {message.message[0]}")
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