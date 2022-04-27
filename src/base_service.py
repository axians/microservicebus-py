import asyncio
import subprocess
import importlib
from queue_message import QueueMessage


class BaseService:
    def __init__(self, id, queue):
        self.id = id
        self.queue = queue
        self.task = None

    def printf(self, msg):
        print(msg, flush=True)
        
    # region Default functions
    async def Start(self):
        pass

    async def Stop(self):
        pass

    async def Process(self, message):
        pass

    async def StateUpdate(self, state):
        pass

    # endregion

    # region Communication functions
    async def SubmitAction(self, destination, action, message):
        msg = QueueMessage(self.id, destination, action, message)
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)

    async def Debug(self, message):
        msg = QueueMessage(self.id, "logger", "_debug", message)
        task = asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)

    async def ThrowError(self, message):
        msg = QueueMessage(self.id, "logger", "_error", message)
        task = asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)

    async def SubmitMessage(self, message):
        msg = QueueMessage(self.id, "com", "_sendEvent", message)
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)

    async def StartService(self, service):
        msg = QueueMessage(self.id, "orchestrator", "_start_service", service)
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)

    async def StopCustomServices(self):
        msg = QueueMessage(self.id, "orchestrator",
                           "_stop_custom_services", "")
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)

    async def StartCustomServices(self):
        msg = QueueMessage(self.id, "msb", "_start_custom_services", "")
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)
    # endregion

    # region Private functions
    # package = pip package E.g "azure-iot-device"
    # module = module name E.g "azure.iot.device.aio"
    # name = name of object E.g "IoTHubDeviceClient". If you don't know the name, try dir(importlib.import_module("module name")

    # SAMPLES:
    # IoTHubDeviceClient = self.AddPipPackage("azure-iot-device", "azure.iot.device.aio", "IoTHubDeviceClient")
    # MqttClient = self.AddPipPackage("paho-mqtt", "paho.mqtt.client", "Client")

    # Think of it this way.... MqttClient = self.AddPipPackage("paho-mqtt", "paho.mqtt.client", "Client") ...is equivalent to:
    # pip install paho-mqtt
    # from paho.mqtt.client import Client
    def AddPipPackage(self, package, module, name):
        try:
            try:
                self.printf(f"Importing {module}")
                importlib.import_module(module)
            except Exception as e1:
                self.printf (f"Unable to import module:. \nTrying to install package {package}")

                response = subprocess.run(f"pip3 install {package}", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
                if(response.returncode != 0):
                    self.printf (f"Failed to install {package}")
                    raise Exception('InstallPackage', f"Failed to install {package}")
                else:
                     self.printf (f"Successfully installed {package}")
                    
        except Exception as e2:
            self.printf (f"Failed to install {package}")
            raise Exception('InstallPackage', f"Failed to install {package}")

        Package = getattr(importlib.import_module(module), name)
        return Package

    # endregion


class CustomService(BaseService):
     def __init__(self, id, queue, config):
        self.id = id
        self.queue = queue
        self.config = config
        super(CustomService, self).__init__(id, queue)
       
     def GetPropertyValue(self, category, prop):
         ## newDict = dict(filter(lambda elem: elem[0] % 2 == 0, dictOfNames.items()))
        try:
            category = category + "Config"
            values = [config for config in self.config[category] if config['id'] == prop]
            if len(values) > 0:
                return values[0]['value']
            else:
                return "undefined"
        except Exception as e:
                print(e, flush=True)
                return "undefined" 