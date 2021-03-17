import asyncio, json, string, uuid, utils
from base_service import CustomService
from azure.iot.device.aio import IoTHubDeviceClient

class MyService(CustomService):
    def __init__(self, id, queue):
        self.run = True
        self.queue = queue
        self.interval = 10,
        utils.install_module("azure.iot.device")
        IoTHubDeviceClient = getattr("azure.iot.device.aio")

        #from azure.iot.device.aio import IoTHubDeviceClient
        super(MyService, self).__init__(id, queue)

    async def Start(self):
        await self.Debug(f"Started (interval={self.interval})")
        while self.run:
            data = str(uuid.uuid4())
            reading = {'data':f"{data}"}
            msg = json.dumps(reading)
            await self.Debug(f"Submitting {msg}")
            await self.SubmitMessage( msg)

            await asyncio.sleep(self.interval)
    
    async def Stop(self):
        self.run = False
        #await asyncio.sleep(self.interval)
        await self.Debug(f"Stopped {self.id}")
    
    async def StateUpdate(self, state):
        await self.Debug(f"Received new state")