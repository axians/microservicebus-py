import sys
import subprocess
import asyncio
import socket
from xmlrpc.client import Server
from base_service import BaseService
# from wireguard import Server
from signalrcore.hub_connection_builder import HubConnectionBuilder
# from azure.iot.device.aio import IoTHubDeviceClient


class VPNHelper(BaseService):
    def __init__(self, id, queue):
        print("start vpn helper")
        super(VPNHelper, self).__init__(id, queue)

    # async def Up(vpnConfigPath):
    #     try:
    #         # Downloads wireguard package
    #         subprocess.check_call(
    #             [sys.executable, '-m', 'pip', 'install', 'wireguard'])
    #         server = Server(vpnConfigPath)
    #         #Server('myvpnserver.com', '192.168.24.0/24',address='192.168.24.1')

    #         # Write out the server config to the default location: /etc/wireguard/wg0.conf
    #         server.config().write()
    #         server.config().post_up

    #     except Exception as e:
    #         print(f"Error in vpn_helper up: {e}")

    # async def Down(vpnConfigPath):
    #     try:
    #         # Downloads wireguard package
    #         subprocess.check_call(
    #             [sys.executable, '-m', 'pip', 'install', 'wireguard'])
    #         server = Server(vpnConfigPath)
    #         #Server('myvpnserver.com', '192.168.24.0/24',address='192.168.24.1')

    #         # Write out the server config to the default location: /etc/wireguard/wg0.conf
    #         server.config().write()
    #         server.config().post_down

    #     except Exception as e:
    #         print(f"Error in vpn_helper down: {e}")

    async def msb_signed_in(self, args):
        try:
            # Check if wireguard is installed
            response = subprocess.run(
                "wg", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
            if(response.returncode != 0):
                return

            # Use pip in utils.py
            # Downloads wireguard package
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', 'wireguard'])
            # server = Server(vpnConfigPath)

            await self.SubmitAction("msb", "refresh_vpn_settings", {})

        except subprocess.CalledProcessError as e:
            print(e.output)

#vpnConfigPath, server, vpnConfig, interfaceName, endpoint
    async def get_vpn_settings_response(self, args):
        try:
            if args.vpnConfig:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                print(local_ip)

                # No change, continue setup interface
                if local_ip == args.endpoint:
                    with open(args.vpnConfigPath, 'r') as vpnConfig:
                        data = vpnConfig.read()
                    with open(args.vpnConfigPath, 'w') as interface:
                        interface.write(data)
                        # wg = self.AddPipPackage(
                        #     "wireguard", "Server", "Server")
                        # server.config().post_down
                        # server.config().post_up

                else:
                    message = {'ip': local_ip}
                    await self.SubmitAction("msb", "update_vpn_endpoint", message)

            else:
                # server.config().post_down
                print("down")

        except Exception as e:
            print(f"Error in vpn_helper down: {e}")
