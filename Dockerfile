FROM python:latest
COPY ./src /src
COPY ./requirements.txt .
COPY ./docker/tools/tail.sh /tail.sh
RUN chmod +x /tail.sh
RUN pip3 install -r requirements.txt
RUN apt update && apt install -y wireguard && apt install -y vim && apt install -y iputils-ping
RUN cd /src
ENTRYPOINT ["python3"]
CMD [ "/src/start.py" ]


#  docker run -v ${PWD}:/app -it python bash
