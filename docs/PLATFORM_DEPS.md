# Platform Dependencies

This app depends on baseline services managed outside this repository.

## Required External Dependencies

- Reverse proxy service (Caddy) with TLS termination.
- DNS entry for the chosen app hostname resolving to the homelab server.
- External Docker network named homelab.

## Expected Routing

- Caddy route for the chosen app hostname forwards to lawn-web:3000.
- Until lawn-web is running, 502 from Caddy is expected behavior.

## Operational Boundaries

- Homelab repository owns proxy, DNS workflow, and shared platform networking.
- Lawn repository owns application code, schema, and app-level compose definitions.
