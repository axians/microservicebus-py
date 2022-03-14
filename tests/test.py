import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("msb/5")
    print("on_connect complete")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

def on_subscribe(client, userdata, mid, granted_qos):
    print("on_subscribe")
    publish.single("msb/5", "payload", hostname="localhost")
    print("published")


def on_unsubscribe(client, userdata, mid):
    print("on_unsubscribe")

client = mqtt.Client()
client.on_connect = on_connect
client.on_subscribe = on_subscribe
client.on_unsubscribe = on_unsubscribe
client.on_message = on_message
client.connect("localhost", port=1883, keepalive=60)
#client.connect_async("localhost", port=1883, keepalive=60, bind_address="")

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()