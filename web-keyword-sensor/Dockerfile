FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache ca-certificates chromium python3 py3-pip py3-greenlet
RUN python3 -m pip install --break-system-packages --no-cache-dir --disable-pip-version-check paho-mqtt==2.1.0 requests==2.32.4 pyotp==2.9.0 pyee==13.0.0 --no-deps \
    && python3 -m pip install --break-system-packages --no-cache-dir --disable-pip-version-check --index-url https://pypi.org/simple playwright==1.62.0 --no-deps

COPY rootfs /
RUN chmod a+x /usr/bin/web-keyword-sensor /usr/bin/web_ui.py

CMD ["/usr/bin/web-keyword-sensor"]
