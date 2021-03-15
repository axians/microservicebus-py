import asyncio

class QueueMessage:
    def __init__(self, source, destination, action, message):
        self.source = source
        self.destination = destination
        self.message = message,
        self.action = action

    def __repr__(self):
        return f"source:{self.source} destination:{self.destination} message:{self.message}"

class BaseService:
    def __init__(self, id, queue):
        self.id = id
        self.queue = queue
        self.task = None

    async def Start(self):
        pass

    async def Stop(self):
        pass

    async def Process(self, message):
        pass
    
    async def Debug(self, message):
        msg = QueueMessage(self.id, "logger", "Process", message)
        task = asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)
            
    async def SubmitMessage(self, message):
        msg = QueueMessage(self.id, "com", "Process", message)
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)
        
    async def SubmitAction(self, destination, action, message):
        msg = QueueMessage(self.id, destination, action, message)
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)
    
    async def StartService(self, service):
        msg = QueueMessage(self.id, "orchestrator", "_start_service", service)
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)

    async def StopAllServices(self):
        msg = QueueMessage(self.id, "orchestrator", "_stop_all_services", "")
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)
    
    async def Restart(self):
        msg = QueueMessage(self.id, "msb", "_restart", "")
        asyncio.create_task(self.queue.put(msg))
        await asyncio.sleep(0)

class CustomService(BaseService):
     def __init__(self, id, queue):
        self.queue = queue
        super(CustomService, self).__init__(id, queue)