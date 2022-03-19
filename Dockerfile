FROM ubuntu:21.10 

RUN apt-get update -y
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata
RUN apt-get install -y python
RUN apt-get install -y python3-pip

RUN python3 --version

WORKDIR /usr/src/app

RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

RUN DEBIAN_FRONTEND=dialog

RUN adduser --system --group app 
RUN chown -R app:app .
USER app
