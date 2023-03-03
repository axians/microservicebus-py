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
apt-get install pkg-config libcairo2 gcc python3 libgirepository1.0
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

### Install using pip
```
pip install microservicebus-py
```
For more information:
https://pypi.org/project/microservicebus-py/