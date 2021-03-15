import pip
import importlib

def install(package):
    pip.main(['install', package])

def uninstall(package):
    pip.main(['uninstall', '-y', package])

def install_module(module):
    for package in module["packages"]:
        try:
            importlib.import_module(package["name"])
            print(f'{package["package"]} is already installed..')
        except ImportError:
            pip.main(['install', package])
            print(f'{package["package"]} has been installed..')