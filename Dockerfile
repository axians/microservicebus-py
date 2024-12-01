FROM python:latest
COPY ./src /src
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt
RUN cd /src
ENTRYPOINT ["python3"]
CMD [ "/src/start.py" ]


#  docker run -v ${PWD}:/app -it python bash
