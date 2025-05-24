FROM python:3.13-alpine

RUN apk add tini

ADD . /tmp/src

RUN pip install /tmp/src

ENTRYPOINT ["tini", "--"]
