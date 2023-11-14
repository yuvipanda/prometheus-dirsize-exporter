FROM python:3.11-alpine

RUN apk add tini

ADD . /tmp/src

RUN pip install /tmp/src

ENTRYPOINT ["tini", "--"]