# microservicebus-py

## Installation

How to install pip package:

```
python3 -m pip install microservicebus-py
```

## Overview

With the microservicebus-py Node, everything is about services communicating over a single queue managed by the `Orchestrator` (which is also a service). Some services are internal (inherits from BaseService), while others are custom (inherits from CustomService).

## Requirements

### Prerequisites

```
apt-get install pkg-config libcairo2-dev gcc python3-dev libgirepository1.0-dev
```

### Python 3.8

### Pip3

```
sudo apt-get install python3-pip
```

### Install required packages

```
pip install -r requirements.txt
```

## Run using Docker

```
docker build -t microservicebus-py .;
docker run -it --rm microservicebus-py
```

## Publish to pip
1. To be able to upload package
```
pip install twine
```
2. To be able to build package 
```
pip install wheel
```
3. Before building the project, remove all files in /dist folder
4. To build and convert to tar
```
python3 setup.py sdist bdist_wheel
```
5. Check if created correctly : twine check dist/*
```
twine check dist/*
```
6. To publish to TestPyPi
```
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```
7. Publish to PyPi
```
twine upload dist/*
```

## BaseService (base_service)

All services inherit from _BaseService_ either directly or through _CustomService_. Inheriting from _BaseService_ provides a number of functions such as `self.Debug(text)` and `self.SubmitMessage(message)`. Such methods are predefined to target specific destinations and functions. A service can also call `self.SubmitAction(destination, action, message)` to more flexibility is needed.

For instance, if you had a custom service called `emailhandler` which would send emails through the _Process_ function and you'd like to send a message to it you would write:

```python
message = {'to':'foo@bar.com', 'subject':'Hello', 'body':'...from foo'}
await self.SubmitAction("emailhandler", "Process", message)
```

> Note that the action is set to "Process". All services inheriting from _BaseService_ has a `Start`. `Stop` and `Proccess` function. However, you could have created a `SendEmail` function and set the action to "SendEmail".

If, on the other hand, you'd like to send a message to the IoT Hub you would set the _destination_ to "com". However, there is already a simplified function called _SubmitMessage_ predefined with both _destination_ and _action_:

```python
message = {'ts':'2021-01-01 01:01:01', 'temperature':22}
await self.SubmitMessage(message)
```

Similarly there is a predefined function to logging:

```python
await self.Debug("Hello from Python")
```

## Internal services

> Internal services are used as any other service but are never stopped.

### Orchestrator (orchestrator_service)

The _Orchestrator_ is responsible for starting up services and correlate messages between then. All messages on the queue are of type QueueMessage (base*service) and contains information such as the `destination` and `action`. When the Orchestrator receives a message on the queue, it will resolve the destination and call the function (\_action*).

### microServiceBusHandler (msb_handler)

As the name implies the _microServiceBusHandler_ is responsible for all communication with microServiceBus.com. When staring up the service will sign in to msb.com and set up channels for different commands in msb. After successful sign-in, the service will call the Orchestrator to start up the these services.

### Logger (logger_service)

The Logger service outputs data to the terminal and forward debugging info to _microServiceBusHandler_ if enabled

### Com (downloaded at startup) (Currently not used)

The _Com_ service is responsible for all communication with the IoT Hub provider. The only implementation as for now is the _AzureIoT_ service.

The _Com_ service is also responsible to handle state changes. These is expected to be a `msb-state` in the desired state:

```json
"msb-state": {
    "enabled": true,
    "debug": false
},
```

If any of the elements in the `msb-state` changes, the _Com_ service is responsible for taking actions, such as stopping and starting custom services. State changes will also get forwarded to all other services.

_Com_ does not have any inbound functions and can not be stopped.

## Custom services

All custom services inherit from `BaseService` and must expose the following functions:

### Start

The _Start_ function will be called when the when custom service is started. This is the where the services should start any kind of interval or work to produce readings.

Readings can be submitted using the `self.SubmitMessage(message)` function which forwards the message to the _Process_ function of the _Com_ service.

### Stop

The _Stop_ function is called as the service is getting stopped and can be used for any cleanup.

### Process

The _Process_ method can optionally be used for transmitting messages between services using the `self.SubmitAction(destination, action, message)` E.g

```python
await self.SubmitAction('MyOtherService', 'Process', message)
```

### StateUpdate

State updates received by the _Com_ service are forwarded to all services and accessible through the StateUpdate function
