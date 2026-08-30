# xmltv-gateway

Fetches TV listings from a provider and serves them as XMLTV over HTTP.

Jellyfin, Plex, Emby, Channels and TVHeadend all accept an XMLTV URL, so any of
them can consume it.

## Run

```yaml
services:
  xmltv-gateway:
    image: ghcr.io/cl-ansy/xmltv-gateway:latest   # or build: .
    environment:
      PROVIDER: hdhomerun
      HDHOMERUN_HOST: <tuner-address>
    restart: unless-stopped
```

The guide is at `http://xmltv-gateway:8080/xmltv.xml`.

## Jellyfin setup

Put the container on the same Docker network as Jellyfin so the service name
resolves. There is no shared volume and Jellyfin needs no credentials.

Confirm the guide is being served before touching Jellyfin. The service name
resolves only from other containers on that network, and no port is published to
the host, so check from inside the container.

```bash
docker compose logs xmltv-gateway     # expect "refreshed guide (N bytes)"
docker compose exec xmltv-gateway wget -qO- http://localhost:8080/xmltv.xml | wc -c
```

A `404` means no guide has been fetched yet. The logs say why.

Add `ports: ["8080:8080"]` if you want to reach it from the host as well.

1. **Add the tuner** if it isn't already there. Dashboard > Live TV > Tuner
   Devices > **+**. For an HDHomeRun pick that type and let it discover, or
   enter the tuner's address.
2. **Add the guide.** Dashboard > Live TV > TV Guide Data Providers > **+** >
   **XMLTV**. Put `http://xmltv-gateway:8080/xmltv.xml` in the file-or-URL
   field. Leave the rest alone and save.
3. **Map the channels.** Dashboard > Live TV > Channels. Most map themselves
   against the tuner lineup. Fix the rest with the pencil icon.
4. **Refresh the guide.** Dashboard > Scheduled Tasks > **Refresh Guide**.

Jellyfin caches what it fetches for an hour, so `CRON_SCHEDULE` controls load on
the provider rather than how often Jellyfin asks.

Channel logos come from the XMLTV feed where the provider supplies them.
Jellyfin caches logos aggressively, and they sometimes only appear after
removing the tuner and adding it back.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `PROVIDER` | required | Which provider to run |
| `CRON_SCHEDULE` | `0 3 * * *` | When to fetch, in cron syntax |
| `CACHE_FILE` | `/srv/xmltv.xml` | Where the guide is written. Its directory is what gets served |
| `RUN_AS` | `nobody` | User the fetch and the server run as |
| `MAX_AGE` | `172800` | Guide age at which the healthcheck fails |

Every one of these has an image default. Providers add their own variables.

The container always listens on 8080. Remap it with `-p` if you need a
different port on the host.

## Testing a provider

`fetch` runs one fetch and exits instead of starting the service, which checks
credentials and reachability without leaving anything running.

```bash
docker build -t xmltv-gateway .
docker run --rm -e PROVIDER=hdhomerun -e HDHOMERUN_HOST=<tuner-address> \
    xmltv-gateway fetch
```

It logs why a fetch failed and exits non-zero. The same works against a running
stack.

```bash
docker compose run --rm xmltv-gateway fetch
```

## Providers

### `hdhomerun`

SiliconDust HDHomeRun tuners.

| Variable | Meaning |
|---|---|
| `HDHOMERUN_HOST` | Address of the tuner, with or without a scheme |

Reads a fresh `DeviceAuth` from the tuner's `discover.json` on every refresh,
because SiliconDust rotates it and a stored copy goes stale.

The endpoint works without a Full Guide subscription and returns roughly three
days of listings. The subscription extends that to fourteen.

### Adding one

A provider is a callable that returns XMLTV bytes, raises to signal failure, and
reads its configuration from the environment. Write a module in
`xmltv_gateway/providers/` and list it in `PROVIDERS`.

```python
PROVIDERS = {
    "hdhomerun": hdhomerun.fetch,
}
```

Validation, the atomic write and the keep-the-old-guide-on-failure behaviour all
live in the caller. A provider only has to fetch.

## Behaviour

`crond` runs `python -m xmltv_gateway.guide` on `CRON_SCHEDULE`, writing to
`CACHE_FILE`. `darkhttpd` serves that file. A request never waits on a provider.

Only `crond` runs as root, which is what it needs in order to drop to `RUN_AS`
for each job. The fetch and the server both run as `RUN_AS`, with darkhttpd
privdropping after it binds. The server keeps the container alive, so `crond`
runs in the background.

- An `@reboot` line fetches when crond starts, so the guide is there without
  waiting for the schedule. The URL returns 404 until it lands.
- A failed fetch leaves the previous guide in place and logs the error.
- A response that is not XMLTV, or one truncated mid-transfer, is discarded
  rather than written.
- The write is a temp file plus `os.replace`, so a reader gets either the old
  guide or the new one, never a partial file.

The `HEALTHCHECK` fails when the guide is older than `MAX_AGE`. One check covers
a dead scheduler, a failing provider and a dead network.

darkhttpd is used rather than `python -m http.server` because it is 43KB, sends
`Last-Modified` and answers conditional requests with `304`. A consumer polling
hourly transfers nothing while the guide is unchanged.
