import aiohttp, utils, importlib, asyncio, uuid, re, socket, os, json
from pathlib import Path
from base_service import BaseService

class microServiceBusHandler(BaseService):
    def __init__(self, id, queue):
        self.ready = False
        super(microServiceBusHandler, self).__init__(id, queue)
        

    async def Start(self):
        base_uri = "http://localhost:7071"
        settings = {
            "hubUri": base_uri
        }
        home = str(Path.home())
        msb_dir = f"{home}/microServiceBus-pytest"
        msb_settings_path = f"{home}/microServiceBus-pytest/settings.json"

        # Check if directory exists
        if os.path.isdir(msb_dir) == False:
            os.mkdir(msb_dir)

        # Load settings file if exists 
        if os.path.isfile(msb_settings_path):
            with open(msb_settings_path) as f:
                settings = json.load(f)

        # If no sas key, try provision using mac address
        sas_exists = "sas" in settings
        if(sas_exists == False):
            create_node_request = await self.create_node(base_uri)
        
            sas_exists = "sas" in create_node_request
            if(sas_exists == False):
                print(f"FAILED TO SIGN IN TO {base_uri}")
                return
                
            settings = create_node_request
            # Save settings file
            with open( msb_settings_path, 'w') as settings_file:
                    json.dump(create_node_request, settings_file)
        
        # Sign in
        await self.sign_in(base_uri, settings)
        
        if self.ready:
            while True:
                await asyncio.sleep(0)

    async def _start_custom_services(self, args):
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
    
    async def create_node(self, base_uri):
        async with aiohttp.ClientSession() as session:
            # create get request
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            mac =':'.join(re.findall('..', '%012x' % uuid.getnode()))
            create_request = {
                'hostname':hostname, 
                'ip':ip, 
                'mac':mac
            }
            headers = {'Content-Type' : 'application/json'}

            async with session.post(f"{base_uri}/api/create", json=create_request, headers = headers) as response:
                if(response.ok):
                    create_response =  await response.json()
                    return create_response
                else:
                    return None

    async def sign_in(self, base_uri, signin_request):
        async with aiohttp.ClientSession() as session:
            headers = {'Content-Type' : 'application/json'}

            async with session.post(f"{base_uri}/api/signin", json = signin_request, headers = headers) as response:
                if(response.ok):
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
        
                
        