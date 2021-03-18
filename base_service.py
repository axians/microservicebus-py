import asyncio, pip, importlib
from model import QueueMessage

class BaseService:
    def __init__(self, id, queue):
        self.id = id
        self.queue = queue
        self.task = None

    #region Default functions
    async def Start(self):
        pass

    async def Stop(self):
        pass

    async def Process(self, message):
        pass
    
    async def StateUpdate(self, state):
        pass

    #endregion

    #region Communication functions
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
        msg = QueueMessage(self.id, "orchestrator", "_stop_custom_services", "")
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)
    
    async def StartCustomServices(self):
        msg = QueueMessage(self.id, "msb", "_start_custom_services", "")
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)
    #endregion
    
    #region Private functions
    # package = pip package E.g "azure-iot-device"
    # module = module name E.g "azure.iot.device.aio" 
    # name = name of object E.g "IoTHubDeviceClient"
    async def AddPipPackage(self, package, module, name):
        try:
            try:
                importlib.import_module(module)
                print("success") 
            except:
                pip.main(['install', package])
                print("failed")
        except:
            importlib.import_module(module)

        Package = getattr(importlib.import_module(module),name)
        return Package

    #endregion
class CustomService(BaseService):
     def __init__(self, id, queue):
        self.queue = queue
        super(CustomService, self).__init__(id, queue)