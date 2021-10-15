#region Imports
import time
import asyncio
import uuid
import re
import os
import sys
import socket
import os
import json
import schedule
import time
import logging,threading
from signalrcore.hub_connection_builder import HubConnectionBuilder
from pathlib import Path
from base_service import BaseService
#endregion
class microServiceBusHandler(BaseService):
    #region Constructor
    def __init__(self, id, queue):
        self.ready = False
        self.base_uri = "https://microservicebus.com/nodeHub"
        home = str(Path.home())
        self.msb_dir = f"{home}/msb-py"
        self.service_path = f"{self.msb_dir}/services"
        self.msb_settings_path = f"{home}/msb-py/settings.json"
        
        super(microServiceBusHandler, self).__init__(id, queue)
    #endregion
    #region Base functions
    async def Start(self):
        try:
            await self.set_up_signalr()
            settings = self.get_settings()
            
            # If no sas key, try provision using mac address
            sas_exists = "sas" in settings
            if(sas_exists == False):
                await self.Debug("Create node using mac address")

                await self.create_node()
            else:
                self.sign_in(settings, False)

            while True:
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Error in msb.start: {e}")
    
    async def _debug(self, message):
        #print(message)
        pass
    #endregion
    #region Helpers
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
        with open( self.msb_settings_path, 'w') as settings_file:
                    json.dump(settings, settings_file)
    #endregion
    #region SignalR event listeners
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
        self.connection.on_open(lambda: print("connection opened and handshake received ready to send messages"))
        self.connection.on_close(lambda: print("connection closed"))
        self.connection.on_error(lambda data: print(f"An exception was thrown closed{data.error}"))
        
        # mSB.com listeners
        self.connection.on("nodeCreated", lambda sign_in_info: self.sign_in(sign_in_info[0], True))
        self.connection.on("signInMessage", lambda sign_in_response: self.successful_sign_in(sign_in_response[0]))
        self.connection.on("ping", lambda conn_id: self.ping_response(conn_id[0]))
        #self.connection.on('ping', lambda x: print("BAJS"))
        self.connection.on('errorMessage', print)
        self.connection.on('restart', lambda args: os.execv(sys.executable, ['python'] + sys.argv))
        self.connection.on('reboot', lambda args: os.system("sudo reboot"))
        self.connection.on("heartBeat", lambda messageList: print("Heartbeat received: " + " ".join(messageList)))
        self.connection.start()
        time.sleep(1)
        self.set_interval(self.sendHeartbeat, 60 * 3)
    #endregion
    #region SignalR callback functions
    async def create_node(self):
        mac =':'.join(re.findall('..', '%012x' % uuid.getnode()))
        await self.Debug(mac)
        self.connection.send("createNodeFromMacAddress", [mac])

    def sign_in(self, settings, first_sign_in):
        if(first_sign_in == True):
            print("Node created successfully")
            self.save_settings(settings)

        print("Signing in")
        hostData = {
            "id": "",
            "connectionId": "",
            "Name": settings["nodeName"],
            "machineName": socket.gethostname(),
            "OrganizationID": settings["organizationId"],
            "npmVersion": "3.12.3",
            "sas": settings["sas"],
            "recoveredSignIn": False,
            "ipAddresses": socket.gethostbyname(socket.gethostname()),
            "macAddresses": ':'.join(re.findall('..', '%012x' % uuid.getnode()))
        }
        print(hostData)
        self.connection.send("signIn", [hostData])

    def successful_sign_in(self, sign_in_response):
        print('Node ' + sign_in_response["nodeName"] + ' signed in successfully')
        self.save_settings(sign_in_response)
        self.sendHeartbeat()

    def ping_response(self, conn_id):
        print("Ping response")
        settings = self.get_settings()
        self.connection.send("pingResponse", [settings["nodeName"], socket.gethostname(), "Online", conn_id, False])

    def sendHeartbeat(self):
        print("Sending heartbeat")
        self.connection.send("heartBeat", ["hej"])

    def set_interval(self,func, sec):
        def func_wrapper():
            self.set_interval(func, sec)
            func()
        t = threading.Timer(sec, func_wrapper)
        t.start()
        return t

    #endregion

