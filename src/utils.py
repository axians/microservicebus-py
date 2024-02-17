import subprocess, sys, importlib, socket, array, struct, fcntl,json, urllib.request, tarfile, requests, shutil, os

def get_public_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', bytes(ifname, 'utf-8')[:15]))
    return ':'.join('%02x' % b for b in info[18:24])

def check_version():
    try:
        # Check if directory exists
        msb_dir = f"{os.environ['HOME']}/msb-py"
        if os.path.isdir(msb_dir) == False:
            return

        print("")
        print("*********************************************")
        print (f"current dir: {os.path.dirname(os.path.abspath(__file__))}")
        currentDirectory = os.path.dirname(os.path.abspath(__file__));
        preferedVersion = "latest"
        currentVersion = ""
        msb_settings_path = f"{msb_dir}/settings.json"
        print(f"msb_settings_path: {msb_settings_path}")
        if os.path.exists(msb_settings_path):
            with open(msb_settings_path) as f:
                settings = json.load(f)
                preferedVersion = settings["coreVersion"]
                print(f"preferedVersion: {preferedVersion}")
        else:
            print(f"{preferedVersion} does not exist")
            return
        
        with open(f"{currentDirectory}/package.json") as f:
            settings = json.load(f)
            currentVersion = settings["version"]
            print(f"currentVersion: {currentVersion}")

        if preferedVersion == "ignore":
            print("IGNORING VERSION")
            return
        elif preferedVersion == "latest":
            gitUri = "https://api.github.com/repos/axians/microservicebus-py/releases/latest"
            response = urllib.request.urlopen(gitUri)
            data = response.read()
            encoding = response.info().get_content_charset('utf-8')
            latest_release = json.loads(data.decode(encoding))
            preferedVersion = latest_release["tag_name"]
            print(f"preferedVersion: {preferedVersion}")
        
        if preferedVersion != currentVersion:
            print(f"Updating from {currentVersion} to {preferedVersion}")
            gitUri = f"https://api.github.com/repos/axians/microservicebus-py/releases"
            response = urllib.request.urlopen(gitUri)
            data = response.read()
            encoding = response.info().get_content_charset('utf-8')
            releases = json.loads(data.decode(encoding))
            filtered = [x for x in releases if x['tag_name'] == preferedVersion]
            if len(filtered) == 0:
                return
            release = releases[0]
            tarball_url = release["tarball_url"]
            response = requests.get(tarball_url, stream=True)

            if response.status_code == 200:
                install_dir = f"{currentDirectory}/../install"
                if os.path.exists(f"{currentDirectory}/../install"):
                    shutil.rmtree(f"{currentDirectory}/../install")
                    print("Removed install directory")

                tar_file = tarfile.open(fileobj=response.raw, mode="r|gz")
                tar_file.extractall(path=install_dir)
                top_directory = os.listdir(install_dir)[0]
                print(f"top_directory: {top_directory}")
                
                src_directory = f"{install_dir}/{top_directory}/src"
                dest_directory = f"{currentDirectory}/../src_new/"
                print(f"src_directory: {src_directory}")
                print(f"dest_directory: {dest_directory}")

                if os.path.exists(f"{currentDirectory}/../src_new"):
                    shutil.rmtree(f"{currentDirectory}/../src_new")
                    print("Removed src_new directory")

                shutil.copytree(src_directory, dest_directory)
                shutil.rmtree(src_directory)
                if os.path.exists(f"{currentDirectory}/../src_old"):
                    shutil.rmtree(f"{currentDirectory}/../src_old")
                    print("Removed src_old directory")
                
                shutil.copytree(f"{currentDirectory}", f"{currentDirectory}/../src_old")
                #os.rename(f"{currentDirectory}/src", f"{currentDirectory}/../src_old")
                for filename in os.listdir(currentDirectory):
                    print(f"\tRemoving {filename}")
                    os.remove(f"{currentDirectory}/{filename}")

                for filename in os.listdir(f"{currentDirectory}/../src_new"):
                    print(f"\tCopying {filename}")
                    shutil.copyfile(f"{currentDirectory}/../src_new/{filename}", f"{currentDirectory}/{filename}")
                #os.rename(f"{currentDirectory}/../src_new", f"{currentDirectory}")
                print("Successfully updated")
    
    except Exception as e:
        print(f"Failed to update version: {e}")

def red(str):
    return f"\033[1;31m{str}\033[0m"

def green(str):
    return f"\033[1;32m{str}\033[0m"

def yellow(str):
    return f"\033[1;33m{str}\033[0m"

def purple(str):
    return f"\033[95m{str}\033[0m"

