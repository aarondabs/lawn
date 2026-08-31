# Platform Dependencies

This app depends on baseline services managed outside this repository.

## Required External Dependencies

- Reverse proxy service (Caddy) with TLS termination.
- DNS entry for the chosen app hostname resolving to the homelab server.
- External Docker network named `homelab`.
- **`ntfy` push service, reachable as `http://ntfy` on the `homelab` network.** The API posts
  reminder alerts to `<NTFY_URL>/<NTFY_ALERTS_TOPIC>` (default `http://ntfy/lawn-alerts`) and
  assistant briefings to `<NTFY_URL>/<NTFY_BRIEFINGS_TOPIC>` (default `http://ntfy/lawn-briefings`).
  All three are env-configurable via `.env` (formerly hardcoded). Subscribe to both topics on
  the phone to receive both streams.

## Expected Routing

- Caddy route for the chosen app hostname forwards to `lawn-web:3000`.
- Until `lawn-web` is running, a 502 from Caddy is expected behavior.
- The API reaches ntfy by service name over the `homelab` network — no route/DNS entry needed.

## Operational Boundaries

- Homelab repository owns proxy, DNS workflow, and shared platform networking.
- Lawn repository owns application code, schema, and app-level compose definitions.
