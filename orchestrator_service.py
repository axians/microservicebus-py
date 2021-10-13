import asyncio, signal, os
from logger_service import Logger
from msb_handler import microServiceBusHandler
from base_service import BaseService, CustomService

class Orchestrator(BaseService):
    def __init__(self, id, queue):
        
        self.run = True
        self.services = [self]
        self.queue = queue
        self.loop = asyncio.get_event_loop()

        super(Orchestrator, self).__init__(id, queue)

    async def Start(self):
        # signals are not implemented in windows :(
        if os.name != 'nt':
            signals = (signal.SIGTERM, signal.SIGINT)
            for s in signals:
                self.loop.add_signal_handler(
                    s, lambda s=s: asyncio.create_task(self.shutdown(s, self.loop)))

        #region    
        text = """
           _               ____                  _          ____             
 _ __ ___ (_) ___ _ __ ___/ ___|  ___ _ ____   _(_) ___ ___| __ ) _   _ ___  
| '_ ` _ \\| |/ __| '__/ _ \\___ \\ / _ \\ '__\\ \\ / / |/ __/ _ \\  _ \\| | | / __| 
| | | | | | | (__| | | (_) |__) |  __/ |   \\ V /| | (_|  __/ |_) | |_| \\__ \\ 
|_| |_| |_|_|\\___|_|  \\___/____/ \\___|_|    \\_/ |_|\\___\\___|____/ \\__,_|___/ \n\n"""
        #endregion
        await self.Debug(text)
        logger = Logger("logger", self.queue)
        await self.StartService(logger)
        msbHandler = microServiceBusHandler("msb", self.queue)
        await self.StartService(msbHandler)
        
        await self.Debug("Started")

        while self.run:
            msg = await self.queue.get()

            if msg.destination == "*": # Send to all services
                for service in self.services:
                    try:
                        function = getattr(service, msg.action)
                        self.loop.create_task(function(msg))
                    except:
                        await self.Debug(f"{service.id} has no function called {msg.action}")
            else: # Send to one service
                service = next((srv for srv in self.services if srv.id == msg.destination), None)   
                if service != None:
                    function = getattr(service, msg.action)
                    self.loop.create_task(function(msg))
                else:
                    await self.Debug(f"There is no service called {msg.destination}")

            await asyncio.sleep(0.1)

    async def _start_service(self, message):
        service = message.message[0]
        self.services.append(service)
        task = self.loop.create_task(service.Start())
        service.task = task
        task.set_name(f"{task.get_name()} : {service.id}")
        task.add_done_callback(self.service_completed)
        await self.Debug(f"Running {len(self.services)} services")
    
    async def _stop_custom_services(self, message):
        # First stop all custom services
        customServices = [service for service in self.services if isinstance(service, CustomService)]
        
        for srv in customServices:
            srv.task.cancel()

        [await service.Stop() for service in customServices]
        [self.services.remove(service) for service in customServices]
        customServices = [service for service in self.services if isinstance(service, CustomService)]
        await self.Debug(f"Running {len(self.services)} services")

    def service_completed(x, fn):
        print("*************************")
        print(f"{fn.get_name()} stopped")
        print("*************************")
    
    async def shutdown(self, signal, loop, *args):
        print()
        print(f"Shutting down ...")
        self.run = False
        # Shut down signalr connection
        # self.connection.stop()
        # Calling all services to shutdown
        [await service.Stop() for service in self.services]
        
        ## Terminating all tasks
        tasks = [t for t in asyncio.all_tasks() if t is not
                asyncio.current_task()]

        [task.cancel() for task in tasks]

        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()
        
