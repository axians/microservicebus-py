from base_service import BaseService
from pathlib import Path
from logging.handlers import RotatingFileHandler
from signalrcore.hub_connection_builder import HubConnectionBuilder
from packaging import version
from urllib import parse
import asyncio, importlib, pathlib, uuid, re, sys, traceback, socket, requests, os, json, psutil
import platform, time, logging, glob, urllib. request, threading, utils, ssl

ssl._create_default_https_context = ssl._create_unverified_context

logging.basicConfig (
    handlers=[RotatingFileHandler('/var/log/microservicebus-py.log', maxBytes=100000, backupCount=7)],
    format='%(asctime)s: %(message)s',
    encoding='utf-8',
    level=logging.WARNING
)

class microServiceBusHandler(BaseService):
    # region Constructor
    def __init__(self, id, queue):
        self.ready = False
        self._connected = False
        self._reconnect = False
        self.signed_in = False
        self._missedheartbeat = 0
        self.rauc_handler = None

        self.base_uri = os.getenv('MSB_HOST') if os.getenv('MSB_HOST') != None else "https://microservicebus.com"
                
        home = str(Path.home())
        self.msb_dir = f"{os.environ['HOME']}/msb-py"
        
        self.service_path = f"{self.msb_dir}/services"
        self.msb_settings_path = f"{self.msb_dir}/settings.json"
        try:
            from rauc_handler import RaucHandler
            self.rauc_handler = RaucHandler()
        except Exception as e:
            self.printf("")
            self.printf(f"Unable to initiate RAUC. Proceeding without RAUC support.")

        super(microServiceBusHandler, self).__init__(id, queue)
    # endregion
    # region Base functions

    async def Start(self):
        try:
            self.settings = self.get_settings()
            if "hubUri" in self.settings:
                self.base_uri = self.settings["hubUri"]
            else:
                self.printf("hubUri not set")
                self.settings["hubUri"] = self.base_uri

            await self.Debug(f"instance: {self.base_uri}")

            await self.set_up_signalr()
            # If no sas key, try provision using mac address
            sas_exists = "sas" in self.settings
            if(sas_exists == False):
                await self.Debug("Create node using mac address")

                await self.create_node()

            else:
                await self.sign_in(self.settings, False)

            while True:
                await asyncio.sleep(0.1)
        except Exception as e:
            await self.ThrowError(f"Error in msb.start: {e}")
            await self.ThrowError(traceback.format_exc())

    async def _debug(self, message):
        if "nodeName" in self.settings and self._connected == True:
            self.connection.send("logMessage", [ self.settings["nodeName"], message.message[0], self.settings["organizationId"]])

    # endregion
    # region Private methods
    def debug_sync(self, message):
        self.printf(message)
        ##asyncio.run(self.Debug(message))

    def get_settings(self):
        settings = {
            "hubUri": self.base_uri
        }
        # Check if directory exists
        if os.path.isdir(self.msb_dir) == False:
            os.mkdir(self.msb_dir)

        # Load settings file if exists
        if os.path.exists(self.msb_settings_path):
            with open(self.msb_settings_path) as f:
                settings = json.load(f)

        else:
            self.printf("Creating settings")
            settings = {
                "hubUri": self.base_uri
            }
            self.save_settings(settings)
        
        return settings

    def get_package_info(self):
        root = pathlib.Path(__file__).resolve().parent
        content = (root / "package.json").read_text()
        packageInfo = json.loads(content)
        return packageInfo

    def save_settings(self, settings):
        with open(self.msb_settings_path, 'w') as settings_file:
            json.dump(settings, settings_file)
            self.settings = settings
            self.printf("Settings saved")

    async def sign_in(self, settings, first_sign_in):
        if(first_sign_in == True):
            self.printf("Node created successfully")
            settings["hubUri"] = self.settings["hubUri"] 
            self.settings = settings
            self.save_settings(settings)

        packageInfo = self.get_package_info()
        await self.Debug("Package version: \033[95m" + packageInfo["version"] + "\033[0m")
        await self.Debug("Node id: \033[95m" + settings["nodeName"] + "\033[0m")
        await self.Debug("Organization id:\033[95m " + settings["organizationId"] + "\033[0m")
        await self.Debug(f"Settings path:\033[95m {self.msb_settings_path}\033[0m")
        

        macAddresses = []
        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == socket.AF_INET:
                    macAddresses.append(utils.getHwAddr(interface))
        await self.Debug(f"Mac addresses:\033[95m {macAddresses} \033[0m")
 
        ipAddresses = []
        macAddresses = []

        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == socket.AF_INET:
                    ipAddresses.append(snic.address)
                    macAddresses.append(utils.getHwAddr(interface))

        firmware = None
        try:
            firmware = self.settings["firmware"]
        except Exception:
            pass

        hostData = {
            "id": "",
            "connectionId": "",
            "Name": settings["nodeName"],
            "machineName": socket.gethostname(),
            "OrganizationID": settings["organizationId"],
            "npmVersion": packageInfo["version"] ,
            "sas": settings["sas"],
            "ipAddresses": ipAddresses,
            "recoveredSignIn": "False",
            "macAddresses": macAddresses,
            "firmware": firmware
        }
        await self.Debug("Signing in")
        # Use for debugging
        #self.connection.send("signIn", [hostData])
        self.connection.send("signInAsync", [hostData])
        #await self.Debug("Signing in")

    def sign_in_sync(self, settings, first_sign_in):
        asyncio.run(self.sign_in(settings, first_sign_in))

    async def create_node(self):
        macAddresses = []
        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == socket.AF_INET:
                    macAddresses.append(utils.getHwAddr(interface))

        
        await self.Debug(macAddresses)
        request = {
            "hostName" :socket.gethostname(),
            "imei":None,
            "ipAddress":"",
            "macAddresses": ','.join(macAddresses),
            "isModule":False
        }
        self.printf(request)
        self.connection.send("assertNode", [request])
        hurUri = self.settings["hubUri"]
        await self.Debug("\033[93m Device information such as host name, MAC addresses and IP addresses\033[0m")
        await self.Debug(f"\033[93m has been submitted to {hurUri} to pre-register the Node.\033[0m")
        await self.Debug(f"\033[93m Please visit {hurUri} to claim this Node.\033[0m")

    def start_azure_iot_service(self, sign_in_response):
        try:
            state = sign_in_response["state"]
            asyncio.run(self.Debug(f"Device state is {state}"))
            if state == "InActive":
                return

            file_name = "pythonAzureIoTProvider.py"
            uri = f"{self.base_uri}/api/Scripts/00000000-0000-0000-0000-000000000001/{file_name}"
            service_file = requests.get(uri, allow_redirects=True)
            service_file_name = os.path.join(self.service_path, file_name)

            file = open(service_file_name, 'wb+')
            file.write(service_file.content)
            file.close()

            # pythonActivity["userData"]["type"].replace("_py", "")
            module_name = "AzureIoTService"
            # pythonActivity["userData"]["type"]
            service_name = "AzureIoTService"

            spec = importlib.util.spec_from_file_location(
                module_name, service_file_name)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            MicroService = getattr(module, module_name)
            microService = MicroService(service_name.lower(), self.queue, sign_in_response)  # (id, queue, config)
            asyncio.run(self.StartService(microService))
            asyncio.run(self.Debug(f"Loading module {module_name}"))

        except Exception as e:
            asyncio.run(self.ThrowError(
                f"Error in msb.start_azure_iot_service: {e}"))

    async def refresh_vpn_settings(self, args):
        try:
            await self.Debug(f"refresh_vpn_settings")
            self.connection.send("getVpnSettings", [""])
        except Exception as e:
            await self.Debug(f"Error in refresh_vpn_settings: {e}")

    async def update_vpn_endpoint(self, args):
        self.connection.send("updateVpnEndpoint", [args.message[0]["ip"]])

    # endregion
    # region SignalR event listeners

    async def set_up_signalr(self):
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.DEBUG)

        # Settings
        signalr_uri = f"{self.base_uri}/nodeHub"
        await self.Debug(f"Connecting to {signalr_uri}")
        self.connection = HubConnectionBuilder()\
            .with_url(signalr_uri, options={"verify_ssl": False}) \
            .with_automatic_reconnect({
                "type": "raw", # "raw" means it will continue to call the hub
                "enable_trace": False,
                "keep_alive_interval": 15,
                "reconnect_interval": 5, # The interval does not seam to to have any affect 
                #"intervals": [2000,5000,10000,15000]
                #"intervals": [2,5,5,5,5,5,5,5,10,10,30,30,60,60,120,120,1200,1200,1200,2400,2400]
            }).build()

        self.connection.keepAliveIntervalInMilliseconds = 1000 * 60 * 3
        self.connection.serverTimeoutInMilliseconds = 1000 * 60 * 6
        # Default listeners
        self.connection.on_open(lambda: self.connected())
        self.connection.on_close(lambda: self.disconnected())
        self.connection.on_error(lambda data: self.debug_sync(f"An exception was thrown: {data.error}"))
        self.connection.on_reconnect(lambda: self.reconnected())

        # mSB.com listeners
        self.connection.on("nodeCreated", lambda sign_in_info: self.sign_in_sync(sign_in_info[0], True))
        self.connection.on("signInMessage", lambda sign_in_response: self.successful_sign_in(sign_in_response[0]))
        self.connection.on("updatedToken", lambda args: self.update_token(args[0]))
        self.connection.on("ping", lambda conn_id: self.ping_response(conn_id[0]))
        self.connection.on("errorMessage", lambda arg: self.handle_error(arg))
        self.connection.on("restart", lambda args: self.restart())
        self.connection.on("reboot", lambda args: self.reboot())
        self.connection.on("reset", lambda args: self.reset(args[0]))
        self.connection.on("changeState", lambda args: self.change_state(args[0]))
        self.connection.on("changeDebug", lambda args: self.change_debug(args[0]))
        self.connection.on("changeTracking", lambda args: self.change_tracking(args[0]))
        self.connection.on("heartBeat", lambda args: self.receive_heartbeat(args[0]))
        self.connection.on("reportState", lambda id: self.report_state(id[0]))
        self.connection.on("updateFirmware", lambda firmware_response: self.update_firmware(
            firmware_response[0], firmware_response[1]))
        self.connection.on("setBootPartition", lambda boot_info: self.set_boot_partition(
            boot_info[0], boot_info[1]))
        self.connection.on("getVpnSettingsResponse", lambda vpn_response: self.get_vpn_settings_response(
            vpn_response[0], vpn_response[1], vpn_response[2]))
        self.connection.on("refreshVpnSettings", lambda response: self.refresh_vpn_settings_sync(response))
        self.connection.on("sendMessage", lambda args: self.debug_sync(args[0]))
        self.connection.on("startTerminal", lambda args: self.start_terminal(args[0], args[1]))
        self.connection.on("stopTerminal", lambda args: self.stop_terminal())
        self.connection.on("terminalCommand", lambda args: self.terminal_command(args[0]))
        self.connection.on("downloadFile", lambda args: self.download_file(args[0]))

        # region Not implemented event handlers
        self.connection.on(
            "getEndpoints", lambda response: self.not_implemented("getEndpoints"))
        self.connection.on(
            "updateItinerary", lambda response: self.not_implemented("updateItinerary"))
        # self.connection.on(
        #     "changeTracking", lambda response: self.not_implemented("changeTracking"))
        self.connection.on(
            "forceUpdate", lambda response: self.not_implemented("forceUpdate"))
        self.connection.on(
            "restartCom", lambda response: self.not_implemented("restartCom"))
        self.connection.on(
            "shutdown", lambda response: self.not_implemented("shutdown"))
        self.connection.on(
            "refreshSnap", lambda response: self.not_implemented("refreshSnap"))
        self.connection.on("resetKeepEnvironment", lambda response: self.not_implemented(
            "resetKeepEnvironment"))
        self.connection.on(
            "updateFlowState", lambda response: self.not_implemented("updateFlowState"))
        self.connection.on(
            "enableDebug", lambda response: self.not_implemented("enableDebug"))
        self.connection.on(
            "uploadSyslogs", lambda response: self.not_implemented("uploadSyslogs"))
        self.connection.on(
            "resendHistory", lambda response: self.not_implemented("resendHistory"))
        self.connection.on(
            "requestHistory", lambda response: self.not_implemented("requestHistory"))
        self.connection.on(
            "transferToPrivate", lambda response: self.not_implemented("transferToPrivate"))
        self.connection.on(
            "grantAccess", lambda response: self.not_implemented("grantAccess"))
        self.connection.on(
            "runTest", lambda response: self.not_implemented("runTest"))
        self.connection.on(
            "pingNodeTest", lambda response: self.not_implemented("pingNodeTest"))
        self.connection.on(
            "updatePolicies", lambda response: self.not_implemented("updatePolicies"))
        self.connection.on(
            "executeScript", lambda response: self.not_implemented("executeScript"))
        self.connection.on("updateVulnerabilities", lambda response: self.not_implemented(
            "updateVulnerabilities"))
        self.connection.on(
            "dockerListImages", lambda response: self.not_implemented("dockerListImages"))
        self.connection.on("dockerListContainers", lambda response: self.not_implemented(
            "dockerListContainers"))
        self.connection.on("dockerInstallImage", lambda response: self.not_implemented(
            "dockerInstallImage"))
        self.connection.on(
            "dockerDeleteImage", lambda response: self.not_implemented("dockerDeleteImage"))
        self.connection.on("dockerStartContainer", lambda response: self.not_implemented(
            "dockerStartContainer"))
        self.connection.on("dockerStopContainer", lambda response: self.not_implemented(
            "dockerStopContainer"))
        self.connection.on(
            "dockerComposeList", lambda response: self.not_implemented("dockerComposeList"))
        self.connection.on("dockerComposeInstall", lambda response: self.not_implemented(
            "dockerComposeInstall"))
        self.connection.on(
            "dockerComposeUp", lambda response: self.not_implemented("dockerComposeUp"))
        self.connection.on(
            "dockerComposeDown", lambda response: self.not_implemented("dockerComposeDown"))
        self.connection.on(
            "uploadFile", lambda response: self.not_implemented("uploadFile"))
        # endregion
        try:
            self.connection.start()
        except Exception as ex:
            await self.ThrowError(f"Unable to start SignalR!")
            self._missedheartbeat = 100

        time.sleep(2)

        if "policies" not in self.settings:
            self.settings["policies"] = { "disconnectPolicy": { "heartbeatTimeout": 180, "missedHearbeatLimit": 3}}

        heartbeatTimeout = self.settings["policies"]["disconnectPolicy"]["heartbeatTimeout"]
        self.set_interval(self.send_heartbeat, heartbeatTimeout)
        await self.Debug(f"Start hearbeat at {heartbeatTimeout} seconds interval")
    # endregion
    # region SignalR callback functions
    def successful_sign_in(self, sign_in_response):
        try:
            node_name = sign_in_response["nodeName"]
            tag_list = sign_in_response["tags"]
            
            # Keep some settings from previous sign in
            if "hubUri" not in self.settings:
                sign_in_response["hubUri"] = self.settings["hubUri"]
            
            if "firmware" in self.settings:
                sign_in_response["firmware"] = self.settings["firmware"]
            
            sign_in_response["hubUri"] = self.base_uri
            self.save_settings(sign_in_response)        
            
            asyncio.run(self.SubmitAction("*", "msb_signed_in", {}))
            
            if os.path.isdir(self.service_path) == False:
                os.mkdir(self.service_path)

            state = self.settings["state"]
            asyncio.run(self.Debug(f"Node state {state}"))
            asyncio.run(self.SubmitAction("orchestrator", "_set_state", {"state": state}))

            if self.settings["policies"]["backgroundServicePolicy"] != None and self.settings["policies"]["backgroundServicePolicy"]["backgroundService"] != None:
                backgroundService = self.settings["policies"]["backgroundServicePolicy"]["backgroundService"]
                asyncio.run(self.Debug(f"backgroundService: {backgroundService}"))
            
            if sign_in_response['itineraries'] is not None and state == "Active":
                for itinerary in sign_in_response['itineraries']:
                    if itinerary["enabled"] == False:
                        continue
                    
                    pythonActivities = [srv for srv in itinerary["activities"]
                                        if "baseType" in srv["userData"] and srv["userData"]["baseType"] == 'pythonfile']
                    
                    for pythonActivity in pythonActivities:
                        try:
                            general_config = pythonActivity["userData"]["config"]["generalConfig"]

                            name_config = next(filter(lambda x: x["id"] == "name", general_config))
                            activity_name = name_config["value"]
                            
                            host_config = next(filter(lambda x: x["id"] == "host", general_config))
                            
                            # Check if activity is set to run on node
                            if host_config["value"] != node_name and host_config["value"] not in tag_list:
                                continue
                            
                            enabled_config = next(filter(lambda x: x["id"] == "enabled", general_config))
                            if enabled_config["value"] == False:
                                continue
                            
                            organization_id = sign_in_response["organizationId"]
                            file_name = pythonActivity["userData"]["type"].replace("_py", ".py")

                            uri = f"{self.base_uri}/api/Scripts/{organization_id}/{file_name}" if pythonActivity["userData"]["isCustom"] == True else f"{self.base_uri}/api/Scripts/00000000-0000-0000-0000-000000000001/{file_name}"
                            asyncio.run(self.Debug(f"isCustom: {pythonActivity["userData"]["isCustom"]}"))
                            bind_to_version = pythonActivity["userData"]["bindToVersion"]
                            script_version = pythonActivity["userData"]["version"]

                            if bind_to_version == True:
                                uri = f"{uri}/{script_version}"

                            service_file = requests.get(uri, allow_redirects=True, verify=False)
                            service_file_name = os.path.join(
                                self.service_path, file_name)

                            file = open(service_file_name, 'wb+')
                            file.write(service_file.content)
                            file.close()

                            module_name = pythonActivity["userData"]["type"].replace("_py", "")
                            service_name = pythonActivity["userData"]["type"]
                            service_config = pythonActivity["userData"]["config"]
                            
                            try:
                                spec = importlib.util.spec_from_file_location(
                                    module_name, service_file_name)
                                module = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(module)
                                MicroService = getattr(module, module_name)
                                
                                microService = MicroService(service_name.lower(), self.queue, service_config)  # (id, queue, config)
                                asyncio.run(self.StartService(microService))
                                asyncio.run(self.Debug(f"Loading module \033[93m{module_name}\033[0m"))
                            except Exception as loadEx:
                                asyncio.run(self.ThrowError(f"Unable to load {module_name} service: Error: {loadEx}"))
                                
                        except Exception as ex:
                            asyncio.run(self.ThrowError(f"Unable to start service: {ex}"))

            settings = self.get_settings()
            self.connection.send("signedIn", [ settings["nodeName"], socket.gethostname(), "Online", settings["organizationId"], False])
            self.send_heartbeat()
            self.signed_in = True
            
            asyncio.run(self.Debug(f"\033[95mNode {node_name} signed in successfully\033[0m"))
            
        except Exception as ex:
            asyncio.run(self.Debug(f"sign_in_response error: {ex}"))
            asyncio.run(self.Debug(f"sign_in_response: {sign_in_response}"))

    def update_token(self, token):
        self.settings["sas"] = token
        self.save_settings(self.settings)
        self.debug_sync(f"SAS token has been updated.")
        #self.restart()

    def not_implemented(self, event_handler):
        asyncio.run(self.ThrowError(
            f'SignalR event handler \033[93m"{event_handler}"\033[0m is not implemented in the Python Node'))

    def ping_response(self, conn_id):
        try:
            settings = self.get_settings()
            self.connection.send("pingResponse", [ settings["nodeName"], socket.gethostname(), "Online", conn_id, False])
            asyncio.run(self.Debug("Ping response"))
        except Exception as e:
            asyncio.run(self.Debug(f"Error in ping_response: {e}"))
    
    def connected(self):
        asyncio.run(self.Debug("\033[95mConnected\033[0m"))
        self._connected = True

        if( (self._reconnect == True or self._connected == True) and "id" in self.settings):
            id = self.settings["id"]
            self._reconnect = False
            asyncio.run(self.Debug(f"Reconnecting: {id}"))
            self.connection.send("reconnected", [self.settings["id"]])

    def disconnected(self):
        asyncio.run(self.Debug("\033[95mDisconnected\033[0m"))
        self._connected = False
        #self._reconnect = True

    def reconnected(self):
        asyncio.run(self.Debug("\033[95mReconnected\033[0m"))
        if(self._reconnect == True):
            # Restarting is in progress, do nothing
            return
    
        asyncio.run(self.Debug("Stopping hub connection"))
        # self.restarting = True
        self.connection.stop()
        self._reconnect = True
        def func_wrapper():
            asyncio.run(self.Debug("Restarting hub connection"))
            self.connection.start()

        t = threading.Timer(20, func_wrapper)
        t.start()
        asyncio.run(self.Debug("Restarting connection in 20 seconds"))
 
    def send_heartbeat(self):
        if self._missedheartbeat > 1:
            missedHearbeatLimit = self.settings["policies"]["disconnectPolicy"]["missedHearbeatLimit"]
            asyncio.run(self.Debug(f"MISSING HEARTBEAT ({self._missedheartbeat}/{missedHearbeatLimit})"))
            if self._missedheartbeat >= missedHearbeatLimit or self.signed_in == False:
                asyncio.run(self.Debug(f"\033[93m{self._missedheartbeat} missing heartbeats exceeding limit ({missedHearbeatLimit}). Restarting process\033[0m"))
                self.restart()
        
        asyncio.run(self.Debug(f"Send heatbeat"))        
        self._missedheartbeat += 1
        self.connection.send("heartBeat", ["echo"])
        asyncio.run(self.SubmitAction("*", "_heartbeat", ""))
    
    def receive_heartbeat(self, message):
        if self.signed_in == False:
            asyncio.run(self.Debug(f"Received heatbeat but node has not successfully logged in yet"))
            self._missedheartbeat += 1
        else:
            self._missedheartbeat = 0

        try:
            connection_id = parse.parse_qs(parse.urlparse(self.connection.transport.url).query)['id'][0]
            asyncio.run(self.Debug(f"Received heatbeat => connection_id: {connection_id}"))

        except Exception as ex:
            asyncio.run(self.Debug(f"Received heatbeat => error: {ex}"))

    def handle_error(self, message):
        asyncio.run(self.ThrowError(f"HUB ERROR: {message[0]}"))
        logging.error(f"[msb] \033[91mERROR:\033[0m {message[0]}")
        self.printf(f"HUB ERROR: {message[0]}")
        
        time.sleep(1)

        if len(message) > 1 and message[1] == 9: #Secret is not valid        
            settings = {
                "hubUri": self.base_uri
            }
            self.save_settings(settings)
            os.execv(sys.executable, ['python'] + sys.argv)
        elif len(message) > 1 and message[1] == 101: # Connection is lost, reconnect
            asyncio.run(asyncio.sleep(10))
            self.restart()

    def report_state(self, id):
        node_name = self.settings["nodeName"]
        self.printf(f'Fetching environment state from {node_name}')
        self.connection.send(
            'notify', [id, f'Fetching environment state from {node_name}', 'INFO'])

        networks = []
        
        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == socket.AF_INET:
                    ni = {
                        "name": interface,
                        "ip_address":snic.address,
                        "mac_address": utils.getHwAddr(interface),
                        "netmask": snic.netmask,
                        "type": ''
                    }
                    networks.append(ni)
                else:
                    self.printf("ignore")

        memory_info = psutil.virtual_memory()
        if_addrs = psutil.net_if_addrs()
        cpu_times = psutil.cpu_times()
        disk_info = psutil.disk_usage('/')
        slot_status = None
        try:
            slot_status = self.rauc_handler.get_slot_status()
        except Exception:
            pass

        state = {
            "networks": networks,
            "memory": {
                "totalMem": f'{(memory_info.total / 1000 / 1000):9.2f} Mb',
                "freemem": f'{(memory_info.free / 1000 / 1000):9.2f} Mb'
            },
            "cpus": [{
                "model": platform.processor(),
                "speed": None,
                "times": {
                    "user": cpu_times.user,
                    "nice": cpu_times.nice,
                    "sys": cpu_times.system,
                    "idle": cpu_times.idle
                }
            }],
            "env": dict(os.environ),
            "storage": {
                "available": f'{(disk_info.total / 1000 / 1000):9.2f} Mb',
                "free": f'{(disk_info.free / 1000 / 1000):9.2f} Mb',
                "total": f'{(disk_info.total / 1000 / 1000):9.2f} Mb'
            },
            "raucState": slot_status
        }
        self.connection.send('reportStateResponse', [state, id])
    
    def reset(self, id):
        asyncio.run(self.Debug("\033[93mResetting node\033[0m"))
        node_name = self.settings["nodeName"]
        settings = {
            "hubUri": self.base_uri
        }
        self.save_settings(settings)
        self.connection.send(
            'notify', [id, f"Node {node_name} has been reset", "INFO"])
        os.execv(sys.executable, ['python'] + sys.argv)
    
    def restart(self):
        asyncio.run(self.Debug("\033[93mRestarting node\033[0m"))
        
        time.sleep(1)
        os.execv(sys.executable, ['python'] + sys.argv)

    def reboot(self):
        asyncio.run(self.Debug("\033[93mRebooting node\033[0m"))
        time.sleep(1)
        os.system("reboot")

    def change_state(self, args):
        asyncio.run(self.Debug(f"Change state to {args}"))
        self.settings["state"] = args
        self.save_settings(self.settings)
        if args == "InActive":
            asyncio.run(self.SubmitAction("orchestrator", "_stop_custom_services", args))
        else:
            asyncio.run(self.SubmitAction("orchestrator", "_start_custom_services", args))

    def change_debug(self, enableDebug):
        asyncio.run(self.Debug(f"Console debug {'enabled' if enableDebug else 'disabled'}"))
        time.sleep(0.1)
        self.settings["debug"] = enableDebug
        self.save_settings(self.settings)
        asyncio.run(self.SubmitAction("logger", "_change_debug", enableDebug))

    def change_tracking(self, enableTracking):
        asyncio.run(self.Debug(f"Tracking {'enabled' if enableTracking else 'disabled'}"))
        time.sleep(0.1)
        self.settings["enableTracking"] = enableTracking
        self.save_settings(self.settings)
        asyncio.run(self.SubmitAction("*", "_change_tracking", enableTracking))

    def update_firmware(self, force, connid):
        asyncio.run(self.Debug("test"))
        if self.rauc_handler == None:
            # If rauc is not installed, forward the request if there is another service that could handle it
            asyncio.run(self.SubmitAction("*", "_update_firmware", force))
            return
        
        slot_status = self.rauc_handler.get_slot_status();
        platform_status = dict(slot_status)
        rootfs0_status = platform_status["rootfs0"]["state"]
        current_platform = platform_status["rootfs0"] if rootfs0_status == "booted" else platform_status["rootfs1"]
        platform = current_platform["bundle.compatible"]
        current_version = current_platform["bundle.version"]
        boot_status = current_platform["boot-status"]
        installed = current_platform["installed.timestamp"]

        uri = f"{self.base_uri}/api/nodeimages/" + \
            self.get_settings()["organizationId"] + "/" + platform
        self.printf("Notified on new firmware")
        self.printf("Current firmware platform: " + platform)
        self.printf("Current firmware version: " + current_version)
        self.printf("Current boot status: " + boot_status)
        self.printf("Current firmware installed: " + installed)

        self.printf("Fetching meta data from: " + uri)

        response = requests.get(uri)
        if(response.status_code != 200):
            self.printf("No firmware image found")
            return
        metamodel = response.json()
        if(force or version.parse(metamodel["version"]) > version.parse(current_version)):
            self.printf("New firmware version found")
            dir = f"/tmp/firmwareimages/"
            # Check if directory exists
            if os.path.isdir(dir) == False:
                os.mkdir(dir)
            files = glob.glob(dir + "*")
            for f in files:
                os.remove(f)
            self.printf("Files removed")
            file_name = os.path.join(dir, os.path.basename(metamodel["uri"]))
            self.printf(file_name)
            urllib.request.urlretrieve(metamodel["uri"], file_name)
            self.printf("Download complete")
            self.printf("Calling RAUC")
            self.printf(f"Installing {file_name}")

            self.rauc_handler.install(file_name)
    
    def set_boot_partition(self, partition, connid):
        self.printf(f"Marking partition {partition}")
        self.rauc_handler.mark_partition("active", partition)
        self.printf("Successfully marked partition")
        self.connection.send(
            "notify", [connid, f"Successfully marked partition.", "INFO"])
        time.sleep(10)
        os.system("reboot")

    def set_interval(self, func, sec):
        def func_wrapper():
            self.set_interval(func, sec)
            func()
        t = threading.Timer(sec, func_wrapper)
        t.start()
        return t

    def refresh_vpn_settings_sync(self, args):
        asyncio.run(self.Debug(f"Fetching VPN settings"))
        self.connection.send("getVpnSettings", [""])
    
    def get_vpn_settings_response(self, vpnConfig, interfaceName, endpoint):
        message = {'vpnConfig': vpnConfig,
                   'interfaceName': interfaceName,
                   'endpoint': endpoint,
                   'vpnConfigPath': f"{self.msb_dir}/{interfaceName}.conf"}

        asyncio.run(self.SubmitAction("vpnhelper", "get_vpn_settings_response", message))
    
    def start_terminal(self, connectionId, user):
        message = {
            'connectionId': connectionId,
            'user': user
        }
        asyncio.run(self.SubmitAction("terminal", "_connect", message))
    
    def stop_terminal(self):
       asyncio.run(self.SubmitAction("terminal", "_disconnect", {}))
    
    def terminal_command(self, args):
        asyncio.run(self.SubmitAction("terminal", "_forward_command", args[0]))

    def download_file(self, request):
        try:
            file_name = request["fileName"]
            directory = request["directory"]
            uri = request["uri"]
            connId = request["connId"]
            node_name = self.settings["nodeName"]
            asyncio.run(self.Debug(f"downloading file ({file_name}) to {directory}"))
            urllib.request.urlretrieve(uri, f"/{directory}/{file_name}")
            asyncio.run(self.Debug(f"download complete"))
            message = f"{file_name} has successfully been saved in ${directory} on ${node_name}."
            self.connection.send("notify", [connId, message, "INFO"])

        except Exception as ex:
            asyncio.run(self.ThrowError(f"Error in msb.start: {ex}"))
    # endregion
    # region Service callbacks
    async def request_connectionstring(self, message):
        action = message.message[0]["action"]     
        await self.SubmitAction(message.source, action, self.settings["receiveConnectionString"])
    async def terminal_output(self, message):
        connectionId = message.message[0]["connectionId"]
        data = message.message[0]["data"]    
        self.connection.send("terminalData", [data, connectionId])
    
    # endregion
    