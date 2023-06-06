FROM python:3.11-alpine

ADD . /tmp/src

RUN pip install /tmp/src