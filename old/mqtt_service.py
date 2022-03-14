import asyncio, json, string, uuid, utils
from base_service import BaseService
#import paho.mqtt.client as mqtt

class MqttService(BaseService):
    def __init__(self, id, queue):
        self.run = True
        self.queue = queue
        self.interval = 10,
        super(MqttService, self).__init__(id, queue)

    async def Start(self):
        while True:
            await asyncio.sleep(0.1)

    async def msb_signed_in(self, args):
        try:
            MqttClient = self.AddPipPackage("paho-mqtt", "paho.mqtt.client", "Client")
            client = MqttClient()
            client.on_connect = self.on_connect
            client.on_message = self.on_message

            client.connect_async("localhost", 1883, 60)
            client.loop_start()

            await self.Debug("Started")
        except Exception as e:
            print(e)
            await self.ThrowError(e)

    def on_connect(self, client, userdata, flags, rc):
        asyncio.run(self.Debug(f"Connected with result code: {str(rc)}"))
        client.subscribe("iot-events")

    def on_message(self, client, userdata, msg):
        asyncio.run(self.Debug(f"Received message on {msg.topic}: {str(msg.payload)}"))
        asyncio.run(self.SubmitAction("iotHub", "send_event", msg.payload))