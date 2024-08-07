FROM python:3.12-alpine

COPY requirements.txt /srv/aanmelden/requirements.txt

RUN apk update && \
    apk add --no-cache nginx mariadb-dev zlib-dev gcc musl-dev sqlite build-base && \
    pip install -U pip setuptools && \
    pip install --no-cache-dir -r /srv/aanmelden/requirements.txt && \
    apk --purge del gcc musl-dev build-base

WORKDIR /srv
RUN mkdir static logs

COPY nginx.conf /etc/nginx/nginx.conf

# Port to expose
EXPOSE 80

COPY aanmelden/ /srv/aanmelden/
COPY manage.py  /srv

WORKDIR /srv
COPY start.sh /
COPY ./jobs.sh /
ENTRYPOINT ["/start.sh"]
