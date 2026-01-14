import asyncio, logging, uuid, json, base64
from logging.handlers import RotatingFileHandler
from base_service import BaseService
from ttl_collection import TTLCollection
from urllib import request
from datetime import datetime
import platform, os

class Logger(BaseService):
    def __init__(self, id, queue):
        self.debug = False

        if platform.system() == "Linux":
            self.msb_dir = f"{os.environ['HOME']}/msb-py"
        elif platform.system() == "Windows":
            home = str(Path.home())
            self.msb_dir = f"{home}\\msb-py"
        

        super(Logger, self).__init__(id, queue)

    def _on_ttl_event(self, message):
        print(f"_on_ttl_event event: {message}")
        asyncio.run(self.Debug(f"_on_ttl_event event: {message}"))
    
    async def Start(self):
        self.settings = self.get_settings()
        self.debug = self.settings["debug"]
        await self.Debug(f"Started. Debug: {self.debug}")
        await self._start_persist()
        
        sb_namespace = self.settings["sbNamespace"]
        trackingHubName = self.settings["trackingHubName"]
        self.tracking_uri = f"https://{sb_namespace}.servicebus.windows.net/{trackingHubName}/messages?timeout=60"

        while True:
            await asyncio.sleep(0.1)
    
    async def msb_signed_in(self, args):
        try:
            await self.Debug(f"STARTING msb_signed_in")
            self.event_history_collection.push(False, 'Connected')
            await self.Debug(f"ADDED ENTRY TO event_history_collection")
        except Exception as e:
            await self.Debug(f"Error pushing to event_history_collection: {e}")
            await self.Warning(f"Error pushing to event_history_collection: {e}")
    
    async def _start_persist(self):
        try:
            TTL_HISTORY_TTL = 7 * 24 * 60 * 60  # one week
            TTL_HISTORY_CHECKINTERVAL = 5 * 60  # every 5 minutes
            TTL_HISTORY_PERSISTINTERVAL = 5 * 60  # every 5 minutes

            TTL_EXCEPTION_PERSISTINTERVAL = 5 * 60  # every 5 minutes
            TTL_EXCEPTION_INTERVAL = 15 * 60  # every hour

            self.history_collection = TTLCollection(
                persist_dir=os.path.join(self.msb_dir, "history"),
                persist_file_name="TRANSMIT_SUCCESS_HISTORY.json",
                ttl=TTL_HISTORY_TTL,
                check_period=TTL_HISTORY_CHECKINTERVAL,
                persist_period=TTL_HISTORY_PERSISTINTERVAL
            )
            self.failed_history_collection = TTLCollection(
                persist_dir=os.path.join(self.msb_dir, "history"),
                persist_file_name="TRANSMIT_FAILED_HISTORY.json",
                ttl=TTL_HISTORY_TTL,
                check_period=TTL_HISTORY_CHECKINTERVAL,
                persist_period=TTL_HISTORY_PERSISTINTERVAL
            )
            self.event_history_collection = TTLCollection(
                persist_dir=os.path.join(self.msb_dir, "history"),
                persist_file_name="TRANSMIT_EVENTS_HISTORY.json",
                ttl=TTL_HISTORY_TTL,
                check_period=TTL_HISTORY_CHECKINTERVAL,
                persist_period=TTL_EXCEPTION_PERSISTINTERVAL
            )

            # Register event listeners
            self.history_collection.add_event_listener(self._on_ttl_event)
            self.failed_history_collection.add_event_listener(self._on_ttl_event)
            self.event_history_collection.add_event_listener(self._on_ttl_event)
            
            await self.history_collection.start_async_loops()
            await self.failed_history_collection.start_async_loops()
            await self.event_history_collection.start_async_loops()

            await self.Debug(f"Persisting event started")
        except Exception as e:
            await self.Debug(f"Error setting up TTL containers: {e}")

    async def _on_submit_success(self, args):
        try:
            print(f"on_submit_success triggered")
            await self.Debug(f"on_submit_success triggered")
            self.history_collection.push(True)
        except Exception as e:
            await self.Warning(f"Error pushing to history_collection: {e}")

    async def StateUpdate(self, message):
        state = message.message[0]

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
       try:
            self.failed_history_collection.push(False)
       except Exception as e:
            logging.error(f"Error pushing to failed_history_collection: {e}")

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

    async def request_history(self, message):
       try:
            await self.Debug(f"request_history called")
            msg = message.message[0]

            startdate = msg["startdate"]
            enddate = msg["enddate"]
            conn_id = msg["connId"]
            
            history_collection = self.history_collection.filter_collection(startdate, enddate, 'hour')
            failed_history_collection = self.failed_history_collection.filter_collection(startdate, enddate, 'hour')
            event_history_collection = self.event_history_collection.filter_collection(startdate, enddate, 'hour')

            history = {
                    'connId': conn_id,
                    'history': history_collection,
                    'failed': failed_history_collection,
                    'events': event_history_collection
                }
            
            await self.SubmitAction("msb", "request_history_response", history)

       except Exception as e:
            await self.Warning(f"Error calling _request_history: {e}")
       

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