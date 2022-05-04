"""Setup script for realpython-reader"""

# Standard library imports
import os
import pathlib

# Third party imports
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).resolve().parent

# The text of the README file is used as a description
README = (HERE / "README.md").read_text()


thelibFolder = os.path.dirname(os.path.realpath(__file__))
requirementPath = thelibFolder + '/requirements.txt'
install_req = []  # Here we'll get: ["gunicorn", "docutils>=0.3", "lxml==0.5a7"]
if os.path.isfile(requirementPath):
    with open(requirementPath) as f:
        install_req = f.read().splitlines()

# This call to setup() does all the work
setup(
    name="microservicebus-py",
    version="0.0.19",
    description="Python agent for microServiceBus.com. Please visit https://microservicebus.com for more information.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/axians/microservicebus-py",
    author="AXIANS IoT Operations",
    author_email="microservicebus@axians.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    packages=["src"],
    include_package_data=True,
    install_requires=install_req,
    entry_points={"console_scripts": ["microservicebus-py=src.start:main"]},
)
