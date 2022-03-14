import subprocess, sys, importlib, socket
import pip._internal as pip

def install(package):
    pip.main(['install', package])

def uninstall(package):
    pip.main(['uninstall', '-y', package])

def install_module(module):
    for package in module["packages"]:
        try:            
            importlib.import_module(package["name"])
            #print(f'{package["package"]} is already installed..')
        except ImportError:
            #print(f'Trying to install {package["package"]}..')
            try:
                pip.main(['install', package["package"]])
                # cmd = f"{sys.executable} -m pip install {package["package"]}"
                # print(f"command: {cmd}")
                # subprocess.check_call(cmd, shell=True)
                #subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                #subprocess.call([sys.executable, "-m", "pip", "install", "--user", package])
                print(f'{package["package"]} has been installed..')
            except TypeError as err:
                print('Handling run-time error:', err)

def get_public_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip