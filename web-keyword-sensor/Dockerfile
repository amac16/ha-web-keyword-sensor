ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache ca-certificates
RUN pip install --no-cache-dir --disable-pip-version-check paho-mqtt==2.1.0 requests==2.32.4

COPY rootfs /
RUN chmod a+x /usr/bin/web-keyword-sensor

CMD ["/usr/bin/web-keyword-sensor"]
