import sys, os, json, platform
import subprocess
import asyncio
import urllib.request
from pathlib import Path
from xmlrpc.client import Server
from base_service import BaseService

class UpdateHandler(BaseService):
    def __init__(self, id, queue):
        super(UpdateHandler, self).__init__(id, queue)

    async def Start(self):
        await self.Debug("Started")  

    async def msb_signed_in(self, args):
        try:
            await self.Debug("UpdateHandler started")
            install_dir = os.path.dirname(__file__)
            await self.Debug(f"install_dir: {install_dir}")
            
            current_version = ""
            with open(f"{install_dir}/package.json") as f:
                packageSettings = json.load(f)
                current_version = packageSettings["version"]
            
            await self.Debug(f"current_version: {current_version}")
            settings = self.get_settings()

            if "pythonVersion" in settings:
                desiredVersion = settings["pythonVersion"]
            else:
                await self.Debug("No pythonVersion in settings")
                return
            
            if(desiredVersion == None or desiredVersion == "ignore"):
                await self.Debug("Ignoring version check")
                return
            
            await self.Debug(f"desiredVersion: {desiredVersion}")
            # Check if utils.py is updated
            if self.versiontuple(current_version) < self.versiontuple("1.0.15"):
                await self.Debug(f"utils.py needs updating...")
                #settings_path = "/usr/local/etc/"
                utils_installation_path = f"{install_dir}/utils.py"
                utils_uri = "https://raw.githubusercontent.com/axians/microservicebus-py/dev/src/utils.py"
                urllib.request.urlretrieve(utils_uri, utils_installation_path)

                update_installation_path = f"{install_dir}/updateMsb.py"
                update_uri = "https://raw.githubusercontent.com/axians/microservicebus-py/dev/src/updateMsb.py"
                urllib.request.urlretrieve(update_uri, update_installation_path)

                command =  f"rm {install_dir}/utils.pyc"
                response = subprocess.run( command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
                if(response.returncode != 0):
                    await self.Debug("Failed to delete utils.pyc")
                
                await self.Debug(f"utils.py updated. Proceeding with installation")
            else:
                await self.Debug(f"Version requirements are met. Proceeding with checking version")

            import utils
            if platform.system() == "Linux":
                msb_dir = f"{os.environ['HOME']}/msb-py"
            elif platform.system() == "Windows":
                home = str(Path.home())
                msb_dir = f"{home}\\msb-py"
            
            #msb_dir = f"{os.environ['HOME']}msb-py"
            await self.Debug(f"msb_dir: {msb_dir}")

            updated = await utils.check_version(self, msb_dir, self.Debug)

            if updated:
                await asyncio.sleep(1)
                command =  f"cp {install_dir}/../src_old/run_portal.py {install_dir}/run_portal.py"
                response = subprocess.run( command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
                if(response.returncode != 0):
                    await self.Debug("Failed to copy run_portal.py")
                else:
                    await self.Debug("copy run_portal.py successfully")

                await self.Debug("Update complate")
                await self.Debug("Restarting node")
                await asyncio.sleep(2)
                os.execv(sys.executable, ['python'] + sys.argv)
            else:
                await self.Debug("No update performed")



            

        except subprocess.CalledProcessError as e:
            self.printf(e.output)

    def versiontuple(self, v):
        return tuple(map(int, (v.split("."))))