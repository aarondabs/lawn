# Platform Dependencies

This app depends on baseline services managed outside this repository.

## Required External Dependencies

- Reverse proxy service (Caddy) with TLS termination.
- DNS entry for the chosen app hostname resolving to the homelab server.
- External Docker network named `homelab`.
- **`ntfy` push service, reachable as `http://ntfy` on the `homelab` network.** The API posts
  reminder alerts to it — `api/src/lawn_api/services/notifications.py` targets
  `http://ntfy/lawn-alerts`. This is currently **hardcoded, not env-configurable**; if the ntfy
  service name or topic ever changes, that file must change too. (Candidate for an env var —
  see the app backlog.)

## Expected Routing

- Caddy route for the chosen app hostname forwards to `lawn-web:3000`.
- Until `lawn-web` is running, a 502 from Caddy is expected behavior.
- The API reaches ntfy by service name over the `homelab` network — no route/DNS entry needed.

## Operational Boundaries

- Homelab repository owns proxy, DNS workflow, and shared platform networking.
- Lawn repository owns application code, schema, and app-level compose definitions.
