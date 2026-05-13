# Operations Runbook

Runtime gotchas, deployment workflows, and known-working patterns for the Lawn Command Center. This is the first place to check when something isn't behaving as expected.

---

## Environment changes and service reloads

A plain `docker restart` does **not** pick up changes to `.env`. Docker injects environment variables at container creation time, so the container must be recreated to see new values.

Use the helper script instead:

```sh
# Recreate api only (most common — after RACHIO_API_KEY, DATABASE_URL changes, etc.)
./ops/reload-env.sh

# Recreate all services (api, web, db)
./ops/reload-env.sh all

# Recreate specific services
./ops/reload-env.sh api web
```

This wraps `docker compose up --force-recreate` for the named services without rebuilding images.

---

## Dev mode vs. production mode

The production `docker-compose.yml` sets `NODE_ENV: production` for the `web` service. `docker-compose.dev.yml` **must** override this with `NODE_ENV: development` — without it, the Next.js dev server gets a conflicting environment and the CSS/PostCSS pipeline breaks (all routes return 500).

To start the dev stack:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d api web
```

To run production (no overlay):

```sh
docker compose -f docker-compose.yml up -d --build api web
```

`postcss.config.js` uses CommonJS `module.exports` — do not convert it to ESM `export default`. The Next.js build resolves this file before the ESM loader is set up.

---

## Frontend component conventions (@base-ui/react)

This project uses `@base-ui/react` (shadcn style: `base-nova`). **It is not Radix UI.** The APIs differ in one critical way: base-ui uses a `render` prop instead of `asChild`.

```tsx
// ❌ Wrong — Radix pattern, does not work with base-ui
<DropdownMenuTrigger asChild><Button>Open</Button></DropdownMenuTrigger>

// ✅ Correct — base-ui render prop pattern
<DropdownMenuTrigger render={<Button />}>Open</DropdownMenuTrigger>
```

The `Button` component in `web/src/components/ui/button.tsx` intercepts the `asChild` prop and converts it to `render` for backward compatibility with any code that passes `asChild`. When `Button` renders a non-`<button>` element (e.g., a Next.js `Link`), pass `nativeButton={false}` to suppress the a11y warning:

```tsx
<Button asChild nativeButton={false}><Link href="/foo">Go</Link></Button>
```

base-ui `Select` does not support `defaultValue`. It must be used in controlled mode:

```tsx
// ❌ Wrong
<Select defaultValue={field.value} ... />

// ✅ Correct
<Select value={field.value} onValueChange={field.onChange} ... />
```

---

## Adding shadcn components

Because `node_modules` are not bind-mounted in production (and the base-nova style requires the component be generated inside the container against the correct package versions), new shadcn components must be installed via the container, then copied back to the host.

```sh
# 1. Install inside the running dev container
docker exec -it lawn-web sh -c "npx shadcn@latest add <component-name> --overwrite --yes"

# 2. Copy back to host (use docker cp — never a shell redirect)
docker cp lawn-web:/app/src/components/ui/<name>.tsx \
  /opt/apps/lawn/web/src/components/ui/<name>.tsx
```

**Never use a shell redirect (`cat > file`) to copy back from the container.** The redirect opens and truncates the file before the command runs, resulting in an empty file. Use `docker cp` exclusively.

---

## API client — 204 No Content responses

All DELETE endpoints return HTTP 204 with no response body. The `apiRequest` wrapper in `web/src/lib/api.ts` handles this by skipping JSON parsing when the status is 204:

```ts
if (response.status === 204) return undefined as TResponse;
```

Without this guard, `response.json()` throws "Unexpected end of JSON input". If you add new endpoints that return 204, this is already handled — no change needed. If you change a DELETE to return 200 with a body, update the callers to pass the correct response type.

---

## Database backups

Nightly backup via cron:

- Script: `ops/backup-db.sh` — dumps the live `lawn` database with `pg_dump`, gzips, writes to `ops/private/db-backups/`.
- Cron file: `/etc/cron.d/lawn-db-backup` (installed by `ops/install-db-backup-cron.sh`). Runs at 03:30 daily. 14-day retention.
- Logs: `ops/private/db-backups/backup.log`.

To take an ad-hoc backup before any manual schema work:

```sh
./ops/backup-db.sh
```

To restore from a backup:

```sh
./ops/restore-db.sh ops/private/db-backups/<filename>.sql.gz
```

---

## Running tests

Use the test helper — do not run pytest directly on the host:

```sh
./ops/test.sh
```

This runs pytest inside the API container against a dedicated test database (`lawn_test`), not the live database. The test DB must be initialized first if it doesn't exist:

```sh
./ops/init-test-db.sh
```

See `README.md` for the full testing workflow including `TEST_DATABASE_URL` usage for host-side runs.

---

## Caddy reverse proxy and DNS

The app is served at `lawn.home.daber.co`. DNS and reverse-proxy configuration live in the **homelab repo** (`/opt/docker/`), not this repo.

- DNS: Pi-hole CNAME `lawn.home.daber.co` → `mediaserver.home.daber.co` (the NUC's LAN IP).
- Caddy: block in `/opt/docker/proxy/Caddyfile` — `reverse_proxy lawn-web:3000`.
- TLS: handled automatically by Caddy via ACME DNS-01 challenge to Route53.

To modify the reverse proxy entry or add a new hostname, edit the Caddyfile in the homelab repo and reload Caddy. Do not modify this repo for DNS/proxy changes.
