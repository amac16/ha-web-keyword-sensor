FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache ca-certificates python3 py3-pip
RUN python3 -m pip install --break-system-packages --no-cache-dir --disable-pip-version-check paho-mqtt==2.1.0 requests==2.32.4

COPY rootfs /
RUN chmod a+x /usr/bin/web-keyword-sensor /usr/bin/web_ui.py

CMD ["/usr/bin/web-keyword-sensor"]
