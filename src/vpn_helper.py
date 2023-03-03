import sys
import subprocess
import asyncio
import utils
from xmlrpc.client import Server
from base_service import BaseService

class VPNHelper(BaseService):
    def __init__(self, id, queue):
        super(VPNHelper, self).__init__(id, queue)

    async def Start(self):
        await self.Debug("Started")
        while True:
            await asyncio.sleep(0.1)

    async def msb_signed_in(self, args):
        try:
            # Check if wireguard is installed
            response = subprocess.run("wg --help", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
            if(response.returncode != 0):
                return

            message = [1, 2, 3]
            await self.SubmitAction("msb", "refresh_vpn_settings", message[0])

        except subprocess.CalledProcessError as e:
            self.printf(e.output)

    async def get_vpn_settings_response(self, args):
        try:
            await self.Debug("Received VPN settings from cloud")
            message = args.message[0]
            if message["vpnConfigPath"]:
                self.vpnConfigPath = message["vpnConfigPath"];           
                ip = utils.get_public_ip()
                
                if ip != message["endpoint"]:
                    await self.Debug(f"IP has changed ({ip}). Calling cloud to update")
                    req = {'ip': ip}
                    await self.SubmitAction("msb", "update_vpn_endpoint", req)

                wg_config_file = open(message["vpnConfigPath"], "w")
                wg_config_file.write(message["vpnConfig"])
                wg_config_file.close()
                
                await self.Debug("wireguard config has been updated")
                await self.wg_down()
                await self.wg_up()
            else:
                # server.config().post_down
                await self.Debug("down")

        except Exception as e:
            await self.Debug(f"Error in vpn_helper down: {e}")
    
    async def wg_up(self):
        try:
            wg_command =  f"wg-quick up {self.vpnConfigPath}"
            response = subprocess.run( wg_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
            if(response.returncode != 0):
                await self.Debug("Failed to bring up VPN connection")
            else:
                await self.Debug("VPN connection established")
        except Exception as e:
            await self.Debug(f"Error trying to connect VPN: {e}")
            
    async def wg_down(self):
        try:
            wg_command =  f"wg-quick down {self.vpnConfigPath}"
            response = subprocess.run( wg_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
            if(response.returncode != 0):
                await self.Debug(f"Failed to bring down VPN connection. This is probobly ok")
            else:
                await self.Debug("VPN connection disconnected")
        except Exception as e:
            await self.Debug(f"Error trying to disconnect VPN: {e}")


