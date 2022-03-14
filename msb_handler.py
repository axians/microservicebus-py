import time
import asyncio
import uuid
import re
import os
import sys
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
from packaging import version
from signalrcore.hub_connection_builder import HubConnectionBuilder
from pathlib import Path
from base_service import BaseService
from rauc_handler import RaucHandler

class microServiceBusHandler(BaseService):
    # region Constructor
    def __init__(self, id, queue):
        self.ready = False
        self.base_uri = "https://microservicebus.com/nodeHub"
        home = str(Path.home())
        self.msb_dir = f"{os.environ['HOME']}/msb-py"
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
                self.sign_in(self.settings, False)

            while True:
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Error in msb.start: {e}")

    async def _debug(self, message):
        # print(message)
        pass
    # endregion
    # region Helpers

    def get_settings(self):
        settings = {
            "hubUri": self.base_uri
        }
        # Check if directory exists
        if os.path.isdir(self.msb_dir) == False:
            os.mkdir(self.msb_dir)

        # Load settings file if exists
        if os.path.isfile(self.msb_settings_path):
            with open(self.msb_settings_path) as f:
                settings = json.load(f)
        return settings

    def save_settings(self, settings):
        with open(self.msb_settings_path, 'w') as settings_file:
            json.dump(settings, settings_file)
    # endregion
    # region SignalR event listeners

    async def set_up_signalr(self):
        self.handler = logging.StreamHandler()
        self.handler.setLevel(logging.DEBUG)
        # Settings
        self.connection = HubConnectionBuilder()\
            .with_url(self.base_uri, options={"verify_ssl": False}) \
            .with_automatic_reconnect({
                "type": "interval",
                "keep_alive_interval": 10,
                "intervals": [1, 3, 5, 6, 7, 87, 3]
            }).build()

        self.connection.keepAliveIntervalInMilliseconds = 1000 * 60 * 3
        self.connection.serverTimeoutInMilliseconds = 1000 * 60 * 6
        # Default listeners
        self.connection.on_open(lambda: print(
            "connection opened and handshake received ready to send messages"))
        self.connection.on_close(lambda: print("connection closed"))
        self.connection.on_error(lambda data: print(
            f"An exception was thrown closed{data.error}"))

        # mSB.com listeners
        self.connection.on(
            "nodeCreated", lambda sign_in_info: self.sign_in(sign_in_info[0], True))
        self.connection.on(
            "signInMessage", lambda sign_in_response: self.successful_sign_in(sign_in_response[0]))
        self.connection.on(
            "ping", lambda conn_id: self.ping_response(conn_id[0]))
        #self.connection.on('ping', lambda x: print("BAJS"))
        self.connection.on('errorMessage', print)
        self.connection.on('restart', lambda args: os.execv(
            sys.executable, ['python'] + sys.argv))
        self.connection.on('reboot', lambda args: os.system("/sbin/reboot"))
        self.connection.on("heartBeat", lambda messageList: print(
            "Heartbeat received: " + " ".join(messageList)))
        self.connection.on("reportState", lambda id: self.report_state(id[0]))
        self.connection.on("updateFirmware", lambda firmware_response: self.update_firmware(firmware_response[0], firmware_response[1]))
        self.connection.on("setBootPartition", lambda boot_info: self.set_boot_partition(boot_info[0], boot_info[1]))
        self.connection.start()
        time.sleep(1)
        self.set_interval(self.sendHeartbeat, 60 * 3)
    # endregion
    # region SignalR callback functions

    async def create_node(self):
        mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
        await self.Debug(mac)
        self.connection.send("createNodeFromMacAddress", [mac])

    def sign_in(self, settings, first_sign_in):
        if(first_sign_in == True):
            print("Node created successfully")
            self.save_settings(settings)

        print("Signing in")
        print(settings["nodeName"])
        print(settings["organizationId"])
        print(':'.join(re.findall('..', '%012x' % uuid.getnode())))
        hostData = {
            "id": "",
            "connectionId": "",
            "Name": settings["nodeName"],
            "machineName": "",
            "OrganizationID": settings["organizationId"],
            "npmVersion": "3.12.3",
            "sas": settings["sas"],
            "recoveredSignIn": False,
            "ipAddresses": "",
            "macAddresses": ':'.join(re.findall('..', '%012x' % uuid.getnode()))
        }
        print(hostData)
        self.connection.send("signIn", [hostData])

    def successful_sign_in(self, sign_in_response):
        print(
            'Node ' + sign_in_response["nodeName"] + ' signed in successfully')
        self.save_settings(sign_in_response)
        self.sendHeartbeat()

    def ping_response(self, conn_id):
        print("Ping response")
        settings = self.get_settings()
        self.connection.send("pingResponse", [
                             settings["nodeName"], socket.gethostname(), "Online", conn_id, False])

    def sendHeartbeat(self):
        print("Sending heartbeat")
        self.connection.send("heartBeat", ["hej"])

    def report_state(self, id):
            self.connection.send('notify', [
                                id, 'Fetching environment state from ' + self.settings["nodeName"], 'INFO'])
            memory_info = psutil.virtual_memory()
            if_addrs = psutil.net_if_addrs()
            cpu_times = psutil.cpu_times()
            disk_info = psutil.disk_usage('/')
            slot_status = self.rauc_handler.get_slot_status()
            state = {
                "networks": [],
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
            print(state)
            # Get all internet interfaces
            # for interface_name, interface_addresses in if_addrs.items():
            #     for address in interface_addresses:
            #         if str(address.family) == 'AddressFamily.AF_INET':
            #             print(address)
            #             print(interface_name)
            # gateway_ip, ip_address, mac_address, name, netmask, type
            self.connection.send('reportStateResponse', [state, id])
    def update_firmware(self, force, connid):
        print(force)
        print(connid)
        platform_status = dict(self.rauc_handler.get_slot_status())
        rootfs0_status = platform_status["rootfs.0"]["state"]
        current_platform = platform_status["rootfs.0"] if rootfs0_status == "booted" else platform_status["rootfs.1"]
        platform = current_platform["bundle.compatible"]
        current_version = current_platform["bundle.version"]
        boot_status = current_platform["boot-status"]
        installed = current_platform["installed.timestamp"]

        uri = "https://microservicebus.com/api/nodeimages/" + self.get_settings()["organizationId"] + "/" + platform
        print("Notified on new firmware");
        print("Current firmware platform: "+ platform)
        print("Current firmware version: " + current_version)
        print("Current boot status: " + boot_status)
        print("Current firmware installed: " + installed)

        print("Fetching meta data from: " + uri)

        response = requests.get(uri)
        if(response.status_code != 200):
            print("No firmware image found")
            return
        metamodel = response.json()
        if(force or version.parse(metamodel["version"]) > version.parse(current_version)):
            print("New firmware version found")
            dir = "/data/home/msb-py/firmwareimages/"
            # Check if directory exists
            if os.path.isdir(dir) == False:
                os.mkdir(dir)
            files = glob.glob(dir + "*")
            for f in files:
                os.remove(f)
            print("Files removed")
            file_name = os.path.join(dir, os.path.basename(metamodel["uri"]))
            print(file_name)
            urllib.request.urlretrieve(metamodel["uri"], file_name)
            print("Download complete")
            print("Calling RAUC")
            print(f"Installing {file_name}")

            self.rauc_handler.install(file_name)

    def set_boot_partition(self, partition, connid):
        print(f"Marking partition {partition}")
        self.rauc_handler.mark_partition("active", partition)
        print("Successfully marked partition")
        self.connection.send("notify", [connid, f"Successfully marked partition.", "INFO"])
        time.sleep(10)
        os.system("sudo /sbin/reboot")
    def set_interval(self, func, sec):
        def func_wrapper():
            self.set_interval(func, sec)
            func()
        t = threading.Timer(sec, func_wrapper)
        t.start()
        return t

    # endregion
