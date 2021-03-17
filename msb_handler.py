import aiohttp, utils, importlib, asyncio, uuid, re, socket, os, json
from pathlib import Path
from base_service import BaseService

class microServiceBusHandler(BaseService):
    def __init__(self, id, queue):
        self.ready = False
        self.base_uri = "https://microservicebus-functions-stage.azurewebsites.net"
        home = str(Path.home())
        self.msb_dir = f"{home}/microServiceBus-pytest"
        self.msb_settings_path = f"{home}/microServiceBus-pytest/settings.json"

        super(microServiceBusHandler, self).__init__(id, queue)
        

    async def Start(self):
        
        settings = await self.get_settings()

        # If no sas key, try provision using mac address
        sas_exists = "sas" in settings
        if(sas_exists == False):
            await self.Debug("First time signing in to mSB.com.")

            create_node_request = await self.create_node(self.base_uri)
        
            sas_exists = "sas" in create_node_request
            if(sas_exists == False):
                print(f"FAILED TO SIGN IN TO {self.base_uri}")
                return

            await self.Debug("...Node created successfully")
                
            settings = create_node_request
            # Save settings file
            await self.save_settings(create_node_request)

        # Sign in
        signin_response = await self.sign_in()

        if(signin_response != False):
            await self.start_com_service(signin_response)
            await self.start_services(signin_response)

        await self.Debug("Started")
        if self.ready:
            await self.Debug("...Node signed in successfully")

            while True:
                await asyncio.sleep(0.1)

    async def get_settings(self):
        settings = {
            "hubUri": self.base_uri
        }
        # Check if directory exists
        if os.path.isdir(self.msb_dir) == False:
            os.mkdir(self.msb_dir)

        # Load settings file if exists 
        if os.path.isfile(self.msb_settings_path):
            with open(self.msb_settings_path) as f:
                settings = json.load(f)
        
        return settings

    async def save_settings(self, settings):
        with open( self.msb_settings_path, 'w') as settings_file:
                    json.dump(settings, settings_file)

    async def start_com_service(self, signin_response):
        utils.install_module(signin_response["iotProvider"]["module"])

        Com = getattr(importlib.import_module(signin_response["iotProvider"]["module"]["module"]),signin_response["iotProvider"]["module"]["name"])
        com = Com("com", self.queue, signin_response["iotProvider"])
        await self.StartService(com)
        self.ready = True

    async def start_services(self, signin_response):
        for service in signin_response["services"]:
            utils.install_module(service)
            MicroService = getattr(importlib.import_module(service["module"]),service["name"])
            microService = MicroService(service["name"], self.queue)
            await self.StartService(microService)

    async def _start_custom_services(self, args):
        signin_response = await self.sign_in()
        if(signin_response != False):
            await self.start_services(signin_response)

    async def _debug(self, message):
        if self.ready == True:
            async with aiohttp.ClientSession() as session:
                # create get request
                headers = {'Content-Type' : 'application-json'}
                await session.post(f"{self.base_uri}/api/debug", json = {"message": message.message[0]}, headers = headers)
    
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

    async def sign_in(self):
        async with aiohttp.ClientSession() as session:
            headers = {'Content-Type' : 'application/json'}
            settings = await self.get_settings()
            async with session.post(f"{self.base_uri}/api/signin", json = settings, headers = headers) as response:
                if(response.ok):
                    signin_response =  await response.json()
                    return signin_response
                else:
                    await self.Debug("Unable to sign in")
                    return False
        
                
        