from rauc_handler import RaucHandler
from base_service import BaseService
from pathlib import Path
from signalrcore.hub_connection_builder import HubConnectionBuilder
from packaging import version
import time
import asyncio
import importlib
import uuid
import re
import os
import sys
import traceback
import socket
import requests
import os
import json
import psutil
import time
import logging
import glob
import urllib.request
import threading
import platform
import utils
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


class microServiceBusHandler(BaseService):
    # region Constructor
    def __init__(self, id, queue):
        self.ready = False
        self.base_uri = "https://microservicebus.com"
        home = str(Path.home())
        self.msb_dir = f"{os.environ['HOME']}/msb-py"

        self.printf(f"os.environ =  {os.environ}")

        self.service_path = f"{self.msb_dir}/services"
        self.msb_settings_path = f"{self.msb_dir}/settings.json"
        self.rauc_handler = RaucHandler()
        super(microServiceBusHandler, self).__init__(id, queue)
    # endregion
    # region Base functions

    async def Start(self):
        try:
            await self.set_up_signalr()
            self.settings = self.get_settings()

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
        pass

    # endregion
    # region Private methods
    def debug_sync(self, message):
        asyncio.run(self.Debug(message))

    def get_settings(self):
        settings = {
            "hubUri": self.base_uri
        }
        # Check if directory exists
        if os.path.isdir(self.msb_dir) == False:
            os.mkdir(self.msb_dir)

        # Load settings file if exists
        self.printf(self.msb_settings_path)
        if os.path.exists(self.msb_settings_path):
            self.printf("Settings exists")
            with open(self.msb_settings_path) as f:
                settings = json.load(f)
        else:
            self.printf("Creating settings")
            settings = {
                "hubUri": self.base_uri
            }
            self.save_settings(settings)
        return settings

    def save_settings(self, settings):
        with open(self.msb_settings_path, 'w') as settings_file:
            json.dump(settings, settings_file)

    async def sign_in(self, settings, first_sign_in):
        if(first_sign_in == True):
            self.printf("Node created successfully")
            self.settings = settings
            self.save_settings(settings)

        await self.Debug("Signing in")
        await self.Debug("Node id: \033[95m" + settings["nodeName"] + "\033[0m")
        await self.Debug("Organization id:\033[95m " + settings["organizationId"] + "\033[0m")
        await self.Debug("Mac addresses:\033[95m " + ':'.join(re.findall('..', '%012x' % uuid.getnode())) + "\033[0m")

        hostData = {
            "id": "",
            "connectionId": "",
            "Name": settings["nodeName"],
            "machineName": "",
            "OrganizationID": settings["organizationId"],
            "npmVersion": "3.12.3",
            "sas": settings["sas"],
            "recoveredSignIn": "False",
            # "ipAddresses": "",
            "macAddresses": [':'.join(re.findall('..', '%012x' % uuid.getnode()))]
        }

        # Use for debugging
        self.connection.send("signIn", [hostData])
        #self.connection.send("signInAsync", [hostData])

    def sign_in_sync(self, settings, first_sign_in):
        asyncio.run(self.sign_in(settings, first_sign_in))

    async def create_node(self):
        mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
        await self.Debug(mac)
        self.connection.send("createNodeFromMacAddress", [mac])

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
        self.connection.send("getVpnSettings", [""])

    async def update_vpn_endpoint(self, args):
        self.connection.send("updateVpnEndpoint", [args.message[0]["ip"]])

    # endregion
    # region SignalR event listeners

    async def set_up_signalr(self):
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.DEBUG)
        # Settings
        signalr_uri = f"{self.base_uri}/nodeHub"
        self.connection = HubConnectionBuilder()\
            .with_url(signalr_uri, options={"verify_ssl": False}) \
            .with_automatic_reconnect({
                "type": "interval",
                "keep_alive_interval": 10,
                "intervals": [1, 3, 5, 6, 7, 87, 3]
            }).build()

        self.connection.keepAliveIntervalInMilliseconds = 1000 * 60 * 3
        self.connection.serverTimeoutInMilliseconds = 1000 * 60 * 6
        # Default listeners
        self.connection.on_open(lambda: self.debug_sync(
            "connection opened and handshake received ready to send messages"))
        self.connection.on_close(lambda: self.debug_sync("connection closed"))
        self.connection.on_error(lambda data: self.debug_sync(
            f"An exception was thrown closed{data.error}"))

        # mSB.com listeners
        self.connection.on(
            "nodeCreated", lambda sign_in_info: self.sign_in_sync(sign_in_info[0], True))
        self.connection.on(
            "signInMessage", lambda sign_in_response: self.successful_sign_in(sign_in_response[0]))
        self.connection.on(
            "ping", lambda conn_id: self.ping_response(conn_id[0]))
        self.connection.on("errorMessage", lambda arg: self.debug_sync(arg[0]))
        self.connection.on("restart", lambda args: os.execv(
            sys.executable, ['python'] + sys.argv))
        self.connection.on("reboot", lambda args: os.system("/sbin/reboot"))
        self.connection.on("reset", lambda args: self.reset(args[0]))
        self.connection.on("heartBeat", lambda messageList: self.printf(
            "Heartbeat received: " + " ".join(messageList)))
        self.connection.on("reportState", lambda id: self.report_state(id[0]))
        self.connection.on("updateFirmware", lambda firmware_response: self.update_firmware(
            firmware_response[0], firmware_response[1]))
        self.connection.on("setBootPartition", lambda boot_info: self.set_boot_partition(
            boot_info[0], boot_info[1]))
        self.connection.on("getVpnSettingsResponse", lambda vpn_response: self.get_vpn_settings_response(
            vpn_response[0], vpn_response[1], vpn_response[2]))
        self.connection.on(
            "refreshVpnSettings", lambda response: self.refresh_vpn_settings_sync(response))
        self.connection.on(
            "sendMessage", lambda args: self.debug_sync(args[0]))

        # region Not implemented event handlers
        self.connection.on(
            "getEndpoints", lambda response: self.not_implemented("getEndpoints"))
        self.connection.on(
            "updateItinerary", lambda response: self.not_implemented("updateItinerary"))
        self.connection.on(
            "changeState", lambda response: self.not_implemented("changeState"))
        self.connection.on(
            "changeDebug", lambda response: self.not_implemented("changeDebug"))
        self.connection.on(
            "changeTracking", lambda response: self.not_implemented("changeTracking"))
        #self.connection.on("sendMessage", lambda response: self.not_implemented("sendMessage"))
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
            "startTerminal", lambda response: self.not_implemented("startTerminal"))
        self.connection.on(
            "stopTerminal", lambda response: self.not_implemented("stopTerminal"))
        self.connection.on(
            "terminalCommand", lambda response: self.not_implemented("terminalCommand"))
        self.connection.on(
            "downloadFile", lambda response: self.not_implemented("downloadFile"))
        self.connection.on(
            "uploadFile", lambda response: self.not_implemented("uploadFile"))
        # endregion

        self.connection.start()
        time.sleep(1)
        self.set_interval(self.sendHeartbeat, 60 * 3)
    # endregion
    # region SignalR callback functions

    def successful_sign_in(self, sign_in_response):
        node_name = sign_in_response["nodeName"]
        tag_list = sign_in_response["tags"]

        asyncio.run(self.Debug(f"Node {node_name} signed in successfully"))
        self.save_settings(sign_in_response)

        asyncio.run(self.SubmitAction("*", "msb_signed_in", {}))

        if sign_in_response['protocol'] == "AZUREIOT":
            self.start_azure_iot_service(sign_in_response)

        if os.path.isdir(self.service_path) == False:
            os.mkdir(self.service_path)

        if sign_in_response['itineraries'] is not None:
            for itinerary in sign_in_response['itineraries']:
                pythonActivities = [srv for srv in itinerary["activities"]
                                    if srv["userData"]["baseType"] == 'pythonfile']
                for pythonActivity in pythonActivities:

                    host_config = [srv for srv in pythonActivity["userData"]
                                   ["config"]["generalConfig"] if srv["id"] == 'host']

                    # Check if activity is set to run on node
                    if host_config[0]["value"] != node_name and host_config[0]["value"] not in tag_list:
                        continue

                    organization_id = sign_in_response["organizationId"]
                    file_name = pythonActivity["userData"]["type"].replace(
                        "_py", ".py")

                    uri = f"{self.base_uri}/api/Scripts/{organization_id}/{file_name}" if pythonActivity["userData"][
                        "isCustom"] == True else f"{self.base_uri}/api/Scripts/00000000-0000-0000-0000-000000000001/{file_name}"

                    service_file = requests.get(uri, allow_redirects=True)
                    service_file_name = os.path.join(
                        self.service_path, file_name)

                    file = open(service_file_name, 'wb+')
                    file.write(service_file.content)
                    file.close()

                    module_name = pythonActivity["userData"]["type"].replace(
                        "_py", "")
                    service_name = pythonActivity["userData"]["type"]
                    service_config = pythonActivity["userData"]["config"]

                    spec = importlib.util.spec_from_file_location(
                        module_name, service_file_name)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    MicroService = getattr(module, module_name)
                    microService = MicroService(service_name.lower(
                    ), self.queue, service_config)  # (id, queue, config)
                    asyncio.run(self.StartService(microService))
                    asyncio.run(self.Debug(f"Loading module {module_name}"))

        self.sendHeartbeat()

    def not_implemented(self, event_handler):
        asyncio.run(self.ThrowError(
            f'SignalR event handler \033[93m"{event_handler}"\033[0m is not implemented in the Python Node'))

    def ping_response(self, conn_id):
        self.printf("Ping response")
        settings = self.get_settings()
        self.connection.send("pingResponse", [
                             settings["nodeName"], socket.gethostname(), "Online", conn_id, False])

    def sendHeartbeat(self):
        self.connection.send("heartBeat", ["echo"])

    def report_state(self, id):
        node_name = self.settings["nodeName"]
        self.printf(f'Fetching environment state from {node_name}')
        self.connection.send(
            'notify', [id, f'Fetching environment state from {node_name}', 'INFO'])

        networks = []
        # interfaces = netifaces.interfaces()
        # for interface in interfaces:
        #     addrs = netifaces.ifaddresses(interface)
        #     if netifaces.AF_INET in addrs.keys():
        #         ni = {
        #                 "name": interface,
        #                 "ip_address":addrs[netifaces.AF_INET][0]["addr"],
        #                 "mac_address": utils.getHwAddr(interface),
        #                 "netmask":addrs[netifaces.AF_INET][0]["netmask"],
        #                 "type": ''}
        #         networks.append(ni)
        memory_info = psutil.virtual_memory()
        if_addrs = psutil.net_if_addrs()
        cpu_times = psutil.cpu_times()
        disk_info = psutil.disk_usage('/')
        slot_status = self.rauc_handler.get_slot_status()
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

    def update_firmware(self, force, connid):
        self.printf(force)
        self.printf(connid)
        platform_status = dict(self.rauc_handler.get_slot_status())
        print(platform_status)
        print(type(platform_status))
        rootfs0_status = platform_status["rootfs0"]["state"]
        current_platform = platform_status["rootfs0"] if rootfs0_status == "booted" else platform_status["rootfs1"]
        platform = current_platform["bundle.compatible"]
        current_version = current_platform["bundle.version"]
        boot_status = current_platform["boot-status"]
        installed = current_platform["installed.timestamp"]

        uri = "https://microservicebus.com/api/nodeimages/" + \
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
            dir = f"{self.msb_dir}/firmwareimages/"
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
        os.system("sudo /sbin/reboot")

    def set_interval(self, func, sec):
        def func_wrapper():
            self.set_interval(func, sec)
            func()
        t = threading.Timer(sec, func_wrapper)
        t.start()
        return t

    def refresh_vpn_settings_sync(self, args):
        self.connection.send("getVpnSettings", [""])

    def get_vpn_settings_response(self, vpnConfig, interfaceName, endpoint):
        message = {'vpnConfig': vpnConfig,
                   'interfaceName': interfaceName,
                   'endpoint': endpoint,
                   'vpnConfigPath': f"{self.msb_dir}/{interfaceName}.conf"}

        asyncio.run(self.SubmitAction(
            "vpnhelper", "get_vpn_settings_response", message))

    # endregion
