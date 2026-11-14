FROM node:22-slim

# Lighthouse in its own container, so the measurement does not open a browser on the machine it runs on.
RUN apt-get update \
 && apt-get install -y --no-install-recommends chromium ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g lighthouse@12.8.2

ENV CHROME_PATH=/usr/bin/chromium
WORKDIR /out
