"""Setup script for realpython-reader"""

# Standard library imports
import pathlib

# Third party imports
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).resolve().parent

# The text of the README file is used as a description
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="microservicebus-py",
    version="1.0.0",
    description="Python agent for microServiceBus.com. Please visit https://microservicebus.com for more information."",
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
    packages=["reader"],
    include_package_data=True,
    install_requires=["feedparser", "html2text"],
    entry_points={"console_scripts": ["realpython=reader.__main__:main"]},
)
