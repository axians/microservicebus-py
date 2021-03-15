import asyncio
import string
import uuid
from base_service import CustomService

class MyService(CustomService):
    def __init__(self, id, queue):
        self.run = True
        self.queue = queue
        self.interval = 10
        self.loop = asyncio.get_event_loop()
        super(MyService, self).__init__(id, queue)

    async def Start(self):
        choices = string.ascii_lowercase + string.digits
        await self.Debug(f"Started {self.id} interval={self.interval}")
        while self.run:
            msg_id = str(uuid.uuid4())
            await self.Debug(f"Submitting [{msg_id}]")
            await self.SubmitMessage("com", msg_id)
            await asyncio.sleep(self.interval)
    
    async def Stop(self):
        self.run = False
        await self.Debug(f"Stopped {self.id}")
    