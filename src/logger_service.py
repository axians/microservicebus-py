import asyncio, logging, uuid, json, base64
from logging.handlers import RotatingFileHandler
from base_service import BaseService
# from urllib.error import HTTPError, URLError
# from urllib.request import urlopen, Request
# from urllib.parse import urlencode
from urllib import request
from datetime import datetime

logging.basicConfig (
    handlers=[RotatingFileHandler('/var/log/microservicebus-py.log', maxBytes=100000, backupCount=7)],
    format='%(asctime)s: %(message)s',
    encoding='utf-8',
    level=logging.WARNING
)

class Logger(BaseService):
    def __init__(self, id, queue):
        self.debug = False
        super(Logger, self).__init__(id, queue)

    async def Start(self):
        self.settings = self.get_settings()
        self.debug = self.settings["debug"]
        await self.Debug(f"Started. Debug: {self.debug}")
        sb_namespace = self.settings["sbNamespace"]
        trackingHubName = self.settings["trackingHubName"]
        self.tracking_uri = f"https://{sb_namespace}.servicebus.windows.net/{trackingHubName}/messages?timeout=60"

        while True:
            await asyncio.sleep(0.1)
    async def msb_signed_in(self, args):
        pass
    
    async def StateUpdate(self, message):
        state = message.message[0]
        #await self.Debug(f"Received: {message}")

    async def _change_debug(self, message):
        self.debug = message.message[0]
 
    async def _debug(self, message):
       logging.warning(f"[{message.source}] {bcolors.OKGREEN}DEGUG:{bcolors.ENDC} {message.message[0]}")
       if self.debug:
           await self.SubmitAction("msb", "_debug", message.message[0])
    
    async def _warning(self, message):
       logging.warning(f"[{message.source}] {bcolors.WARNING}WARNING:{bcolors.ENDC} {message.message[0]}")
       if self.debug:
           await self.SubmitAction("msb", "_debug", message.message[0])

    async def _error(self, message):
       logging.error(f"[{message.source}] {bcolors.FAIL}ERROR:{bcolors.ENDC} {message.message[0]}")
       await self._track(message)

       if self.debug:
           await self.SubmitAction("msb", "_debug", message.message[0])
        
    async def _track(self, message):
        try:
            if isinstance(message.message[0],dict) != True:
                await self.Debug(f"Ignoring tracking message")
                return
            else:
                message = message.message[0]
                fault_code = ""
                fault_description = "N/A"
                isFault = False
                state = "Started"
                msg = json.dumps(message)
                base64_bytes = base64.b64encode(msg.encode('utf-8')).decode('utf-8')
                                
                if "fault_code" in message:
                    fault_code = message["fault_code"]
                    isFault = True
                    state = "Failed"
                if "description" in message:
                    fault_description = message["description"]   

                if "fault_description" in message:
                    fault_description = message["fault_description"]                    

                tracking_message = {
                    "NodeId":self.settings["id"],
                    "Node":self.settings["nodeName"],
                    "OrganizationId":self.settings["organizationId"],
                    "TimeStamp": datetime.now().isoformat(),
                    "ContentType": "application/json",
                    "LastActivity": "",
                    "NextActivity": "",
                    "InterchangeId": str(uuid.uuid4()),
                    "MessageId": str(uuid.uuid4()),
                    "_message": base64_bytes,
                    "IntegrationName": fault_description,
                    "IsBinary": False,
                    "IsLargeMessage": False,
                    "IsCorrelation": False,
                    "IsFirstAction": True,
                    "IsFault": isFault,
                    "IsEncrypted": False,
                    "Variables": [],
                    "State": state,
                    "FaultCode": fault_code,
                    "FaultDescription": fault_description
                }

            # create message
            data = json.dumps(tracking_message)
            data = data.encode('utf-8')

            req =  request.Request(self.tracking_uri, data=data, method="POST")
            req.add_header('Content-Type', 'application/json')
            req.add_header('Authorization', self.settings["trackingToken"])

            resp = request.urlopen(req)
            if resp.getcode()>=400:
                await self.Debug(f"Tracking sent. STATUS CODE:: {resp.getcode()}")

        except Exception as e:
            await self.Debug(f"Unable to send tracking message: {e}")
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'