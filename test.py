import utils, pip, importlib

# ********************************************************************

# Normalt skulle du göra detta:

# from azure.iot.device.aio import IoTHubDeviceClient
# client = IoTHubDeviceClient.create_from_connection_string(connectionstring)

# ********************************************************************

# Men eftersom vi måste göra det dynamiskt så kan vi göra så här istället från din service
connectionstring = "HostName=AxiansHub.azure-devices.net;DeviceId=poja-rpi;SharedAccessKey=b/Ewy6Eo7A+WidZ1BRabChMO7bwaC+7k+aOZgh8IOH0="
package = "azure-iot-device"
module = "azure.iot.device.aio"
name = "IoTHubDeviceClient"

IoTHubDeviceClient = self.await AddPipPackage(package, module, name)
client = IoTHubDeviceClient.create_from_connection_string(connectionstring)
print("failed")

