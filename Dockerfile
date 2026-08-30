# Fetches TV listings from a provider on a cron schedule and serves the result
# as XMLTV over HTTP.
FROM python:3-alpine

RUN apk add --no-cache darkhttpd

COPY xmltv_gateway/ /app/xmltv_gateway/
COPY bin/ /usr/local/bin/

RUN chmod +x /usr/local/bin/entrypoint /usr/local/bin/healthcheck \
    && mkdir -p /srv \
    && chown nobody:nobody /srv \
    && rm -f /etc/crontabs/root

ENV CACHE_FILE=/srv/xmltv.xml \
    CRON_SCHEDULE="0 3 * * *" \
    RUN_AS=nobody \
    MAX_AGE=172800

WORKDIR /app
EXPOSE 8080

HEALTHCHECK --interval=5m --timeout=5s --start-period=60s \
    CMD ["/usr/local/bin/healthcheck"]

ENTRYPOINT ["/usr/local/bin/entrypoint"]
