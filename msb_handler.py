import aiohttp, utils, importlib, asyncio
from base_service import BaseService

class microServiceBusHandler(BaseService):
    def __init__(self, id, queue):
        self.ready = False
        super(microServiceBusHandler, self).__init__(id, queue)
        

    async def Start(self):
        async with aiohttp.ClientSession() as session:
            # create get request
            headers = {'Content-Type' : 'application-json'}
            async with session.post('http://localhost:7071/api/signin', json = {}, headers = headers) as response:
                signin_response =  await response.json()
                
                for service in signin_response["services"]:
                    utils.install_module(service)
                    MicroService = getattr(importlib.import_module(service["module"]),service["name"])
                    microService = MicroService(service["name"], self.queue)
                    await self.StartService(microService)

                # Install IoT Provider
                utils.install_module(signin_response["iotProvider"]["module"])

                Com = getattr(importlib.import_module(signin_response["iotProvider"]["module"]["module"]),signin_response["iotProvider"]["module"]["name"])
                com = Com("com", self.queue, signin_response["iotProvider"])
                await self.StartService(com)
                self.ready = True
        
        while True:
            await asyncio.sleep(1)

    async def _restart(self, args):
        async with aiohttp.ClientSession() as session:
            # create get request
            headers = {'Content-Type' : 'application-json'}
            async with session.post('http://localhost:7071/api/signin', json = {}, headers = headers) as response:
                signin_response =  await response.json()
                
                for service in signin_response["services"]:
                    utils.install_module(service)
                    MicroService = getattr(importlib.import_module(service["module"]),service["name"])
                    microService = MicroService(service["name"], self.queue)
                    await self.StartService(microService)
    
    async def _debug(self, message):
        if self.ready == True:
            async with aiohttp.ClientSession() as session:
                # create get request
                headers = {'Content-Type' : 'application-json'}
                await session.post('http://localhost:7071/api/debug', json = {"message": message.message[0]}, headers = headers)
    