FROM python:3.13-alpine

RUN apk add --no-cache ca-certificates chromium build-base
RUN pip install --no-cache-dir --disable-pip-version-check paho-mqtt==2.1.0 requests==2.32.4 pyotp==2.9.0 pyee==13.0.0
ARG BUILD_ARCH
RUN case "${BUILD_ARCH}" in \
      amd64) PLAYWRIGHT_PLATFORM=manylinux1_x86_64 ;; \
      aarch64) PLAYWRIGHT_PLATFORM=manylinux_2_17_aarch64 ;; \
      armv7) PLAYWRIGHT_PLATFORM=manylinux_2_17_armv7l ;; \
      *) echo "Unsupported Playwright architecture: ${BUILD_ARCH}"; exit 1 ;; \
    esac \
    && pip install --no-cache-dir --disable-pip-version-check --index-url https://pypi.org/simple --only-binary=:all: --platform "${PLAYWRIGHT_PLATFORM}" --target /usr/local/lib/python3.13/site-packages --no-deps playwright==1.52.0 \
    && apk del build-base

COPY rootfs /
RUN chmod a+x /usr/bin/web-keyword-sensor /usr/bin/web_ui.py

CMD ["/usr/bin/web-keyword-sensor"]
