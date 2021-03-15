import asyncio
from base_service import BaseService

class Logger(BaseService):
    async def _debug(self, message):
       print(f"mSB:[{message.source}] DEGUG: {message.message[0]}")
       await self.SubmitAction("msb", "_debug", message.message[0])

    async def Start(self):
        while True:
            await asyncio.sleep(0)