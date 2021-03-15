import pip, subprocess, sys, importlib

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
            print(f'Trying to install {package["package"]}...')
            #pip.main(['install', package])
            try:
                subprocess.call([sys.executable, "-m", "pip", "install", "--user", package])
                print(f'{package["package"]} has been installed..')
            except:
                e = sys.exc_info()[0]
                print( e )