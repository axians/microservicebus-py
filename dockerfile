FROM ubuntu:20.04
ENV TZ=Europe/Stockholm
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get update && apt-get install -y python3-gi python3.9-dev python3-pip dbus
COPY requirements.txt .
RUN pip3 install -r requirements.txt
RUN mkdir -p /data/home/
COPY . .
ENTRYPOINT ["python3"]
CMD [ "start.py" ]

