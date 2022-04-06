import subprocess, sys, importlib, socket, array, struct, fcntl 
import pip._internal as pip

def install(package):
    pip.main(['install', package])

def uninstall(package):
    pip.main(['uninstall', '-y', package])

def install_module(module):
    for package in module["packages"]:
        try:            
            importlib.import_module(package["name"])
        except ImportError:
            try:
                pip.main(['install', package["package"]])
                print(f'{package["package"]} has been installed..', flush=True)
            except TypeError as err:
                print(f'Handling run-time error:{err}', flush=True)

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
