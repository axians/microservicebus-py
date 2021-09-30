import asyncio
import logging
import sys
import time
import signal
import requests
from signalrcore.hub_connection_builder import HubConnectionBuilder
verificationcode = "G7HW3OSD"
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

connection = HubConnectionBuilder()\
    .with_url("https://microservicebus.com/nodeHub", options={"verify_ssl": False}) \
    .with_automatic_reconnect({
        "type": "interval",
        "keep_alive_interval": 10,
        "intervals": [1, 3, 5, 6, 7, 87, 3]
    }).build()
    # .configure_logging(logging.DEBUG, socket_trace=True, handler=handler) \
    
connection.keepAliveIntervalInMilliseconds = 1000 * 60 * 3
connection.serverTimeoutInMilliseconds = 1000 * 60 * 6

connection.on_open(lambda: print("connection opened and handshake received ready to send messages"))
connection.on_close(lambda: print("connection closed"))
connection.on_error(lambda data: print(f"An exception was thrown closed{data.error}"))

connection.on("heartBeat", lambda messageList: print("Heartbeat received: " + " ".join(messageList)))
connection.on("nodeCreated", lambda signInInfo: signIn(signInInfo))
connection.on("signInMessage", print)
connection.on('ping', lambda connId: pingResponse(connId[0]))
connection.on('errorMessage', print)
connection.start()
time.sleep(3)
def sendHeartbeat():
    while True:
        connection.send("heartBeat", ["hej"])
        time.sleep(5)

def createNode():
    print("Creating node")
    connection.send("createNodeFromMacAddress",["80:80:80:80:80"])
    

def signIn(signInInfo):
    print("Signing in")
    print(signInInfo)
    print(signInInfo[0]["sas"])
    hostData = {
        "id": "",
        "connectionId": "",
        "Name": "patrik-py",
        "machineName": "Macbook pro",
        "OrganizationID": signInInfo[0]["organizationId"],
        "npmVersion": "3.12.3",
        "sas": signInInfo[0]["sas"],
        "recoveredSignIn": False,
        "ipAddresses": "",
        "macAddresses": ""
    }
    print(hostData)
    connection.send("signInAsync", [hostData])   

def signal_handler(signal, frame):
     print("Closing connection")
     connection.stop()
     sys.exit(0)

def pingResponse(connId):
    print("Responding to ping")
    print(connId)
    connection.send("pingResponse", ["patrik-py", "Macbook pro", "Online", connId, False])

signal.signal(signal.SIGINT, signal_handler)

createNode()
sendHeartbeat()



