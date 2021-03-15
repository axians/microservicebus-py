import asyncio
from base_service import BaseService

class Logger(BaseService):
    async def Process(self, message):
       print(f"MSB:[{message.source}] DEGUG: {message.message[0]}")
       await self.SubmitAction("msb", "debug", message.message[0])

    async def Start(self):
        while True:
            await asyncio.sleep(1)