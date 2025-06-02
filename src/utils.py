import subprocess, sys, importlib, socket, array, struct, json, urllib.request, tarfile, requests, shutil, os
from sys import platform
from pathlib import Path

if platform == "linux" or platform == "linux2":
    import fcntl

def get_public_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def getHwAddr(ifname):
    try:
        if platform == "linux" or platform == "linux2":
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', bytes(ifname, 'utf-8')[:15]))
            return ':'.join('%02x' % b for b in info[18:24])
        elif platform == "win32":
            from uuid import getnode as get_mac
            mac = get_mac()
            mac_address = hex(mac)[2:]
            mac_address = ':'.join(mac_address[i:i+2] for i in range(0, len(mac_address), 2))
            return mac_address
    except Exception as e:
        return "00:00:00:00:00:00"
    
async def debug(self, msg):
    print(msg)

async def check_version(self, msb_dir, log):
    """
    Check and update the version of the microservicebus-py.

    Args:
        msb_dir (str): The directory where MSB is installed.
        log (function): The logging function to use for logging messages.

    Returns:
        bool: True if the version was updated, False otherwise.
    """
    try:
        if log is None:
            log = self.debug  # Use the debug log if no log function is provided
        else:
            await log("Debug enabled")

        # Check if the directory is provided, if not, set it based on the OS
        if msb_dir == "":
            if platform.system() == "Linux":
                msb_dir = f"{os.environ['HOME']}/msb-py"
            elif platform.system() == "Windows":
                home = str(Path.home())
                msb_dir = f"{home}/msb-py"

        # Check if the MSB directory exists
        if not os.path.isdir(msb_dir):
            await log("Installation directory does not exist")
            return False

        currentDirectory = os.path.dirname(os.path.abspath(__file__))
        preferedVersion = "latest"
        currentVersion = ""
        msb_settings_path = f"{msb_dir}/settings.json"
        await log(f"msb_settings_path: {msb_settings_path}")

        # Load settings from the settings file if it exists
        if os.path.exists(msb_settings_path):
            with open(msb_settings_path) as f:
                settings = json.load(f)
                preferedVersion = settings["pythonVersion"]
                await log(f"preferedVersion: {preferedVersion}")
        else:
            await log(f"{preferedVersion} does not exist")
            return False

        # Load the current version from the package.json file
        with open(f"{currentDirectory}/package.json") as f:
            settings = json.load(f)
            currentVersion = settings["version"]
            await log(f"currentVersion: {currentVersion}")

        # Determine the preferred version to update to
        if preferedVersion == "ignore":
            await log("IGNORING VERSION")
            return False
        elif preferedVersion == "latest":
            gitUri = "https://api.github.com/repos/axians/microservicebus-py/releases/latest"
            response = urllib.request.urlopen(gitUri)
            data = response.read()
            encoding = response.info().get_content_charset('utf-8')
            latest_release = json.loads(data.decode(encoding))
            preferedVersion = latest_release["tag_name"]
            await log(f"preferedVersion: {preferedVersion}")
        elif preferedVersion == "beta":
            gitUri = "https://api.github.com/repos/axians/microservicebus-py/releases"
            response = urllib.request.urlopen(gitUri)
            data = response.read()
            encoding = response.info().get_content_charset('utf-8')
            releases = json.loads(data.decode(encoding))
            pre_releases = [x for x in releases if x['prerelease'] == True]
            pre_releases.sort(key=lambda x: x['published_at'], reverse=True)
            if len(pre_releases) == 0:
                return False

            preferedVersion = pre_releases[0]["tag_name"]
            await log(f"preferedVersion: {preferedVersion}")

        # If the preferred version is different from the current version, update
        if preferedVersion != currentVersion:
            await log(f"Updating from {currentVersion} to {preferedVersion}")
            gitUri = f"https://api.github.com/repos/axians/microservicebus-py/releases"
            response = urllib.request.urlopen(gitUri)
            data = response.read()
            encoding = response.info().get_content_charset('utf-8')
            releases = json.loads(data.decode(encoding))
            filtered = [x for x in releases if x['tag_name'] == preferedVersion]
            if len(filtered) == 0:
                return False
            release = releases[0]
            tarball_url = filtered["tarball_url"]
            
            await log(f"tarball_url {tarball_url}")
            response = requests.get(tarball_url, stream=True, verify=False)

            if response.status_code == 200:
                install_dir = f"{currentDirectory}/../install"
                if os.path.exists(f"{currentDirectory}/../install"):
                    shutil.rmtree(f"{currentDirectory}/../install")
                    await log("Removed install directory")

                tar_file = tarfile.open(fileobj=response.raw, mode="r|gz")
                tar_file.extractall(path=install_dir)
                top_directory = os.listdir(install_dir)[0]
                await log(f"top_directory: {top_directory}")

                src_directory = f"{install_dir}/{top_directory}/src"
                dest_directory = f"{currentDirectory}/../src_new/"
                await log(f"src_directory: {src_directory}")
                await log(f"dest_directory: {dest_directory}")

                if os.path.exists(f"{currentDirectory}/../src_new"):
                    shutil.rmtree(f"{currentDirectory}/../src_new")
                    await log("Removed src_new directory")

                shutil.copytree(src_directory, dest_directory)
                shutil.rmtree(src_directory)
                if os.path.exists(f"{currentDirectory}/../src_old"):
                    shutil.rmtree(f"{currentDirectory}/../src_old")
                    await log("Removed src_old directory")

                shutil.copytree(f"{currentDirectory}", f"{currentDirectory}/../src_old")
                for filename in os.listdir(currentDirectory):
                    await log(f"\tRemoving {filename}")
                    os.remove(f"{currentDirectory}/{filename}")

                for filename in os.listdir(f"{currentDirectory}/../src_new"):
                    await log(f"\tCopying {filename}")
                    shutil.copyfile(f"{currentDirectory}/../src_new/{filename}", f"{currentDirectory}/{filename}")
                await log("Successfully updated")
                return True

    except Exception as e:
        await log(f"Failed to update version: {e}")
        return False

def red(str):
    return f"\033[1;31m{str}\033[0m"

def green(str):
    return f"\033[1;32m{str}\033[0m"

def yellow(str):
    return f"\033[1;33m{str}\033[0m"

def purple(str):
    return f"\033[95m{str}\033[0m"

async def upload_to_blob_storage(self, storage_account, storage_key, container_name, file_path):
        try:
            from datetime import datetime, timedelta, timezone
            ContainerClient = self.AddPipPackage("azure-storage-blob", "azure.storage.blob", "ContainerClient")
            ResourceTypes = self.AddPipPackage("azure-storage-blob", "azure.storage.blob", "ResourceTypes")
            AccountSasPermissions = self.AddPipPackage("azure-storage-blob", "azure.storage.blob", "AccountSasPermissions")
            BlobSasPermissions = self.AddPipPackage("azure-storage-blob", "azure.storage.blob", "BlobSasPermissions")
            generate_account_sas = self.AddPipPackage("azure-storage-blob", "azure.storage.blob", "generate_account_sas")
            generate_blob_sas = self.AddPipPackage("azure-storage-blob", "azure.storage.blob", "generate_blob_sas")
            account_url = f"https://{storage_account}.blob.core.windows.net"
            file_name = os.path.basename(file_path)

            sas_token = generate_account_sas(
                account_name=storage_account,
                account_key=storage_key,
                resource_types=ResourceTypes(service=True, container=True, object=True),
                permission=AccountSasPermissions(read=True, create=True, write=True, delete=True, list=True),
                expiry=datetime.utcnow() + timedelta(hours=1)
            )
            blob_container_client = ContainerClient(account_url=account_url, container_name=container_name, credential=sas_token)
            try:
                await blob_container_client.create_container()
            except Exception:
                pass

            blob_client = blob_container_client.get_blob_client(file_name)
            
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            blob_sas_token = generate_blob_sas(
                account_name=storage_account,
                container_name=container_name,
                blob_name=file_name,
                account_key=storage_key,
                permission=BlobSasPermissions(read=True, write=True),
                expiry=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            sas_url = f"https://{storage_account}.blob.core.windows.net/{container_name}/{file_name}?{blob_sas_token}"
            #sas_url = f"{blob_container_client.url}/{file_name}?{blob_sas_token}"
            return sas_url
        except Exception as ex:
            return