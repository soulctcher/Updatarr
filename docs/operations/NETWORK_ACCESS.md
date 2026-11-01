# Trusted network and reverse-proxy access

Updatarr listens only on `127.0.0.1` by default. Direct public-Internet exposure
is not supported. Remote software changes still wait for confirmation on the
managed computer, and administrator work still waits for Polkit.

## Recommended: VPN or reverse proxy to loopback

Keep `UPDATARR_BIND_HOST=127.0.0.1`. Put the authenticated HTTPS address in
`UPDATARR_PUBLIC_ORIGIN` and list its exact host in
`UPDATARR_ALLOWED_HOSTS`. For example:

```text
UPDATARR_BIND_HOST=127.0.0.1
UPDATARR_PUBLIC_ORIGIN=https://updates.example.internal
UPDATARR_ALLOWED_HOSTS=updates.example.internal
UPDATARR_REVERSE_PROXY=1
```

The proxy must:

- accept HTTPS only;
- preserve the exact `Host` header;
- proxy to `http://127.0.0.1:8788` on the same computer;
- remove the standardized `Forwarded` header before the upstream request;
- support long-lived event responses without buffering;
- limit access to the trusted LAN or VPN.

In explicit reverse-proxy mode, Updatarr accepts forwarding headers only from a
proxy connected through loopback and ignores their values. Uvicorn proxy-header
processing remains off. Caddy recreates its normal `X-Forwarded-*` fields after
custom request-header operations, so Updatarr does not use those fields for
client identity, scheme, Host or authorization. Every non-loopback peer that
sends forwarding headers is rejected. If a URL prefix is used, set the same
`UPDATARR_URL_BASE` in Updatarr and the proxy without stripping or adding it
twice.

Example Caddy shape (review paths and access controls for the actual host):

```text
updates.example.internal {
    # Replace these examples with the exact managed LAN and VPN ranges.
    @trusted remote_ip 192.168.50.0/24 10.20.0.0/24
    handle @trusted {
        reverse_proxy 127.0.0.1:8788 {
            header_up -Forwarded
        }
    }
    respond 403
}
```

## Direct HTTPS listener

Direct non-loopback use requires all of the following:

- a specific address in `UPDATARR_BIND_HOST`, never a wildcard;
- an `https://` public origin;
- exact allowed hosts;
- both `UPDATARR_TLS_CERTFILE` and `UPDATARR_TLS_KEYFILE`;
- a unique production password;
- host firewall rules limited to the trusted LAN or VPN.

Startup rejects cleartext non-loopback use, missing certificate pairs, wildcard
allowed hosts and development mode on a non-loopback listener.

## Verification and recovery

Before remote use, verify the exact Caddy configuration with a header-recording
test upstream, then verify that HTTP is unavailable remotely, the certificate
matches the configured name, an unknown Host is rejected, a foreign Origin
cannot change state, forwarding headers from non-loopback peers are rejected,
forwarding-header values from the configured loopback proxy do not affect
request security, and the session cookie is Secure. Confirm that unauthenticated
health output contains no inventory.

If access fails, return to the loopback sample configuration and restart only
after validation. Never recover by binding to every interface, removing the
password or permitting cleartext credentials.
