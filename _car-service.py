import asyncio, json, uuid, utils
from Motor import * 
from base_service import CustomService
from azure.iot.device.aio import IoTHubDeviceClient

class CarService(CustomService):
    def __init__(self, id, queue):
        super(CarService, self).__init__(id, queue)
        self.run = True
        self.queue = queue
        self.PWM=Motor()

    async def Start(self):
       while True:
            await asyncio.sleep(0.1)
    
    async def Stop(self):
        await self.Debug(f"Stopped {self.id}")
    
    async def StateUpdate(self, state):
        await self.Debug(f"Received new state")

    async def move(self, carstate):
        motor1 = carstate.y
        motor2 = carstate.y
        motor3 = carstate.y
        motor4 = carstate.y
