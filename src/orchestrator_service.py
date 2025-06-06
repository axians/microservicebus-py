import asyncio, sys, traceback
import signal
import os
import urllib3
import platform
from logger_service import Logger
from msb_handler import microServiceBusHandler
from base_service import BaseService, CustomService
from watchdog_service import Watchdog
from vpn_helper import VPNHelper
from update_handler import UpdateHandler

if platform.system() == "Linux":
    from terminal_service import Terminal

class Orchestrator(BaseService):
    def __init__(self, id, queue):

        self.run = True
        self.services = [self]
        self.queue = queue
        self.state = "Active"
        self.loop = asyncio.get_event_loop()
        urllib3.disable_warnings()

        super(Orchestrator, self).__init__(id, queue)

    async def Start(self):
        # signals are not implemented in windows :(
        if os.name != 'nt':
            signals = (signal.SIGTERM, signal.SIGINT)
            for s in signals:
                self.loop.add_signal_handler(
                    s, lambda s=s: asyncio.create_task(self.shutdown(s, self.loop)))

        logger = Logger("logger", self.queue)
        await self.StartService(logger)
        msbHandler = microServiceBusHandler("msb", self.queue)
        await self.StartService(msbHandler)
        wachdog = Watchdog("watchdog", self.queue)
        await self.StartService(wachdog)
        vpnHelper = VPNHelper("vpnhelper", self.queue)
        await self.StartService(vpnHelper)
        updateHandler = UpdateHandler("updatehandler", self.queue)
        await self.StartService(updateHandler)

        if platform.system() == "Linux":
            terminal = Terminal("terminal", self.queue)
            await self.StartService(terminal)
        
        # region
        text = """\033[92m
           _               ____                  _          ____             
 _ __ ___ (_) ___ _ __ ___/ ___|  ___ _ ____   _(_) ___ ___| __ ) _   _ ___  
| '_ ` _ \\| |/ __| '__/ _ \\___ \\ / _ \\ '__\\ \\ / / |/ __/ _ \\  _ \\| | | / __| 
| | | | | | | (__| | | (_) |__) |  __/ |   \\ V /| | (_|  __/ |_) | |_| \\__ \\ 
|_| |_| |_|_|\\___|_|  \\___/____/ \\___|_|    \\_/ |_|\\___\\___|____/ \\__,_|___/ \n\033[1mAXIANS IoT Operations - Python IoT agent\nfor more information visit https://microservicebus.com\n\033[0m"""
        await self.Debug(text)
        # endregion

        await self.Debug("Started Python Node agent for microServicebus.com")

        while self.run:
            try:
                msg = await self.queue.get()

                if msg.destination == "*":  # Send to all services
                    for service in self.services:
                        try:
                            function = getattr(service, msg.action)
                            self.loop.create_task(function(msg))
                        except:
                            pass
                            #await self.Debug(f"{service.id} has no function called {msg.action}")
                else:  # Send to one service
                    service = next(
                        (srv for srv in self.services if srv.id == msg.destination), None)
                    if service != None:
                        function = getattr(service, msg.action)
                        self.loop.create_task(function(msg))
                    else:
                        await self.Debug(f"There is no service called {msg.destination}")
            except Exception as tex:
                self.printf(tex)
                
            await asyncio.sleep(0.1)

    async def _set_state(self, args):
        try:
            self.state = args.message[0]["state"]
            await self.Debug(f"Node state => {self.state}")
        except Exception as ex:
                self.printf(ex)

    async def _start_service(self, message):
        try:
            service = message.message[0]
            self.services.append(service)
            
            await self.Debug(f"Starting {service.id} state: {self.state}")
            
            if isinstance(service, CustomService):
                await self.Debug(f"config: {service.GetState()}")
                if self.state == "Active" and service.GetState() == True:
                    task = self.loop.create_task(service.Start())
                else:
                    task = self.loop.create_task(service.Stop())
            else:
                task = self.loop.create_task(service.Start())
            
            service.task = task
            task.set_name(f"{task.get_name()} : {service.id}")
            task.add_done_callback(self.service_completed)
            await self.Debug(f"Running {len(self.services)} services")
        except Exception as ex:
                self.printf(ex)

    async def _start_custom_services(self, message):
        await self.Debug(f"Starting custom services")
        self.state = "Active"
        customServices = [
            service for service in self.services if isinstance(service, CustomService)]

        for srv in customServices:
            srv.task.cancel()
            
        [await service.Start() for service in customServices]
        # [self.services.remove(service) for service in customServices]
        # customServices = [
        #     service for service in self.services if isinstance(service, CustomService)]
        
        await self.Debug(f"Running {len(self.services)} services")
    
    async def _stop_custom_services(self, message):
        await self.Debug(f"Stopping custom services")
        self.state = "InActive"
        customServices = [
            service for service in self.services if isinstance(service, CustomService)]

        for srv in customServices:
            srv.task.cancel()
            
        [await service.Stop() for service in customServices]
        # [self.services.remove(service) for service in customServices]
        # customServices = [
        #     service for service in self.services if isinstance(service, CustomService)]
        
        await self.Debug(f"Running {len(self.services)-len(customServices)} services")

    def service_completed(self, fn):
        # self.printf("*************************")
        # self.printf(f"{fn.get_name()} stopped")
        # self.printf("*************************")
        if fn.exception():
            task_name = fn.get_name()
            service_name = task_name.split(" : ")[-1]
            exception = fn.exception()
            tb = ''.join(traceback.format_exception(None, exception, exception.__traceback__))
        
            asyncio.ensure_future(self.ThrowError(f"Unhandled exception in {service_name}: {exception} {tb}"))
            asyncio.ensure_future(self.Warning(f"{fn.get_name()} stopped"))
            msg = {
                "fault_code": "90000",
                "fault_description": f"Unhandled exception in {service_name}",
                "source": service_name,
                "description": str(exception),
                "callstack": tb
            }
            asyncio.ensure_future(self.Track(msg))

    async def shutdown(self, signal, loop, *args):
        self.printf("")
        self.printf(f"Shutting down ...")
        self.printf(f"Running {len(self.services)} services")
        self.run = False
        
        # Calling all services to shutdown
        [await service.Stop() for service in self.services]

        # Terminating all tasks
        tasks = [t for t in asyncio.all_tasks() if t is not
                 asyncio.current_task()]

        [task.cancel() for task in tasks]

        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()

