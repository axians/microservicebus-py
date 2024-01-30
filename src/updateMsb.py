import utils, os
print("Start update microservicebus-py")

os.environ['HOME'] = "/usr/local/etc/"
print (f"{os.environ['HOME']}/msb-py")

utils.check_version()

print("Update microservicebus-py completed")
