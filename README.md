# microservicebus-py

## Overview
With the microservicebus-py Node, everything is about services communicating over a single queue managed by the `Orchestrator` (which is also a service). Some services are internal (inherits from BaseService), while others are custom (inherits from CustomService).

## Requirements
### Python 3.8 

### Pip3
```
sudo apt-get install python3-pip
```
### asyncio
```
pip install asyncio
```
### aiohttp
```
pip install aiohttp
```


## BaseService (base_service)
All services inherit from *BaseService* either directly or through *CustomService*. Inheriting from *BaseService* provides a number of functions such as `self.Debug(text)` and `self.SubmitMessage(message)`. Such methods are predefined to target specific destinations and functions. A service can also call `self.SubmitAction(destination, action, message)` to more flexibility is needed.

For instance, if you had a custom service called `emailhandler` which would send emails through the *Process* function and you'd like to send a message to it you would write:

```python
message = {'to':'foo@bar.com', 'subject':'Hello', 'body':'...from foo'}
await self.SubmitAction("emailhandler", "Process", message)
```

> Note that the action is set to "Process". All services inheriting from *BaseService* has a `Start`. `Stop` and `Proccess` function. However, you could have created a `SendEmail` function and set the action to "SendEmail". 


If, on the other hand, you'd like to send a message to the IoT Hub you would set the *destination* to "com". However, there is already a simplified function called *SubmitMessage* predefined with both *destination* and *action*:

```python
message = {'ts':'2021-01-01 01:01:01', 'temperature':22}
await self.SubmitMessage(message)
```

Similarly there is a predefined function to logging:
```python
await self.Debug("Hello from Python")
```


## Internal services
>Internal services are used as any other service but are never stopped. 

### Orchestrator (orchestrator_service)
The *Orchestrator* is responsible for starting up services and correlate messages between then. All messages on the queue are of type QueueMessage (base_service) and contains information such as the `destination` and `action`. When the Orchestrator receives a message on the queue, it will resolve the destination and call the function (*action*).

### microServiceBusHandler (msb_handler)
As the name implies the *microServiceBusHandler* is responsible for all communication with microServiceBus.com. When staring up the service will sign in to msb.com and receive a list of services and the iot hub provider service. After successful sign-in, the service will call the Orchestrator to start up the these services.

The *microServiceBusHandler* also has two other functions
* **_debug** - *used by the logger to forward console information to msb.com*
* **_start_custom_services** - *(accessable through self.StartCustomServices) Downloads and starts up all CustomServices (not Com)*

### Logger (logger_service)
The Logger service outputs data to the terminal and forward debugging info to *microServiceBusHandler* if enabled

### Com (downloaded at startup)
The *Com* service is responsible for all communication with the IoT Hub provider. The only implementation as for now is the *AzureIoT* service.

The *Com* service is also responsible to handle state changes. These is expected to be a `msb-state` in the desired state:
```json
"msb-state": {
    "enabled": true,
    "debug": false
},
```
If any of the elements in the `msb-state` changes, the *Com* service is responsible for taking actions, such as stopping and starting custom services. State changes will also get forwarded to all other services.

*Com* does not have any inbound functions and can not be stopped.

## Custom services
All custom services inherit from `BaseService` and must expose the following functions:

### Start
The *Start* function will be called when the when custom service is started. This is the where the services should start any kind of interval or work to produce readings.

Readings can be submitted using the `self.SubmitMessage(message)` function which forwards the message to the *Process* function of the *Com* service.

### Stop
The *Stop* function is called as the service is getting stopped and can be used for any cleanup.

### Process
The *Process* method can optionally be used for transmitting messages between services using the `self.SubmitAction(destination, action, message)` E.g
```python
await self.SubmitAction('MyOtherService', 'Process', message)
```

### StateUpdate
State updates received by the *Com* service are forwarded to all services and accessible through the StateUpdate function

