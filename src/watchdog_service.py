import asyncio, threading, datetime, os
from datetime import datetime
from base_service import BaseService
from urllib import request
from pathlib import Path

class Watchdog(BaseService):
    def __init__(self, id, queue):
        self.debug = True
        super(Watchdog, self).__init__(id, queue)

    async def Start(self):
        await self.Debug("Started.")
        self.base_uri = os.getenv('MSB_HOST') if os.getenv('MSB_HOST') != None else "https://microservicebus.com"
        self.settings = self.get_settings()
        self.msb_dir = f"{os.environ['HOME']}/msb-py"

    async def _heartbeat(self, message):
        try:
            await self.Debug("Perfoming health check")
            internet_ok = self.internet_check()

            file_path = f"{self.msb_dir}/wachdog"

            with open(file_path, 'w') as watchdog_file:
                watchdog_file.write(datetime.now().isoformat())

        except Exception as err: 
            await self.ThrowError(f"Faild to write to watchdog file: {err}")
        
    async def internet_check(self):
        try:
            request.urlopen(self.base_uri, timeout=5)
            return True
        except request.URLError as err: 
            return False
