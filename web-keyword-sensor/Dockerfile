FROM python:3.13-alpine

RUN apk add --no-cache ca-certificates chromium build-base unzip
RUN pip install --no-cache-dir --disable-pip-version-check paho-mqtt==2.1.0 requests==2.32.4 pyotp==2.9.0 pyee==13.0.0 greenlet==3.2.4
ARG BUILD_ARCH
RUN case "${BUILD_ARCH}" in \
      amd64) PLAYWRIGHT_PLATFORM=manylinux1_x86_64 ;; \
      aarch64) PLAYWRIGHT_PLATFORM=manylinux_2_17_aarch64 ;; \
      armv7) PLAYWRIGHT_PLATFORM=manylinux_2_17_armv7l ;; \
      *) echo "Unsupported Playwright architecture: ${BUILD_ARCH}"; exit 1 ;; \
    esac \
    && mkdir -p /tmp/playwright \
    && pip download --no-cache-dir --disable-pip-version-check --index-url https://pypi.org/simple --only-binary=:all: --platform "${PLAYWRIGHT_PLATFORM}" --python-version 313 --implementation cp --abi cp313 --no-deps --dest /tmp/playwright playwright==1.52.0 \
    && unzip -q /tmp/playwright/playwright-*.whl -d /usr/local/lib/python3.13/site-packages \
    && rm -rf /tmp/playwright \
    && apk del build-base unzip

COPY rootfs /
RUN chmod a+x /usr/bin/web-keyword-sensor /usr/bin/web_ui.py

CMD ["/usr/bin/web-keyword-sensor"]
