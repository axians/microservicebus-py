import asyncio, logging
from base_service import BaseService

class AzureIoT(BaseService):
    def __init__(self, id, queue, provider_info):
        logger = logging.getLogger('azure.iot.device')
        logger.setLevel(logging.WARNING)
        
        try:
            IoTHubDeviceClient = self.AddPipPackage("azure-iot-device", "azure.iot.device.aio", "IoTHubDeviceClient")
        except Exception as e:
            self.printf(f"Error installing azure-iot-device: {e}")

        self.device_client = IoTHubDeviceClient.create_from_connection_string(provider_info["connectionString"])
        self.device_client.on_method_request_received = self.method_request_handler
        self.device_client.on_twin_desired_properties_patch_received = self.twin_patch_handler
        self.twin = None
        super(AzureIoT, self).__init__(id, queue)

    async def Start(self):
        if self.device_client == None:
            await self.Debug("azure-iot-device is not installed")
            return

        await self.device_client.connect()
        self.twin = await self.device_client.get_twin()
        await self.SubmitAction("*", "StateUpdate", self.twin)

        state_exists = "msb-state" in self.twin["desired"]
        if state_exists:
            if(self.twin["desired"]["msb-state"]["enabled"] == False):
                await self.StopCustomServices()
        else:
            await self.Debug("msb-state does not exist in twin")
                
        await self.Debug("Com is started")
        while True:
            await asyncio.sleep(0.1)

    async def Stop(self):
        await self.Debug("Disconnecting device_client")
        await self.device_client.disconnect()

    async def _sendEvent(self, message):
        if self.device_client.connected:
            await self.device_client.send_message(message.message[0])
            await self.Debug("Message sent to IoT Hub")
        else:
            await self.Debug("Unable to send message to IoT Hub. Reason: Not connected")
    
    async def twin_patch_handler(self, patch):
        
        local_state_exists = "msb-state" in self.twin["desired"]
        patch_state_exists = "msb-state" in patch

        if local_state_exists == False:
            self.twin["desired"] = patch

        if patch_state_exists:
            print("patch_state_exists")
            if(self.twin["desired"]["msb-state"]["enabled"] != patch["msb-state"]["enabled"]):
                if(patch["msb-state"]["enabled"] == False):
                    await self.StopCustomServices()
                else:
                    await self.StartCustomServices()
                    
        self.twin = await self.device_client.get_twin()
        await self.SubmitAction("*", "StateUpdate", self.twin)
            
    async def method_request_handler(self, method_request):
        await self.Debug(f"Inbound call: {method_request.name}")
        # Determine how to respond to the method request based on the method name
        if method_request.name == "stop":
            await self.StopCustomServices()
            payload = {"result":"All services stopped"}
            status = 200 
        elif method_request.name == "start":
            await self.StartCustomServices()
            payload = {"result":"All services started"}
            status = 200 
        else:
            payload = {"result": False, "data": "unknown method"}  # set response payload
            status = 400  # set return status code
            print("executed unknown method: " + method_request.name)

        # Send the response
        MethodResponse = self.AddPipPackage("azure-iot-device", "azure.iot.device.aio", "MethodResponse")
        method_response = MethodResponse.create_from_method_request(method_request, status, payload)
        await self.device_client.send_method_response(method_response)
