FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium build-essential ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --disable-pip-version-check \
    paho-mqtt==2.1.0 requests==2.32.4 pyotp==2.9.0 playwright==1.52.0

COPY rootfs /
RUN chmod a+x /usr/bin/web-keyword-sensor /usr/bin/web_ui.py

CMD ["/usr/bin/web-keyword-sensor"]
