import { NextResponse } from "next/server";

// Proxy CSV downloads through the Next origin: the API base is container-internal
// and not reachable from the browser, so a direct <a href> to it would fail.
const DEFAULT_API_BASE_URL = "http://lawn-api:8000";

function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? DEFAULT_API_BASE_URL;
}

// Only these entities are exportable; anything else 404s rather than proxying arbitrary paths.
const ENTITIES = new Set([
  "treatments",
  "cultural-practices",
  "irrigation-events",
  "products",
  "soil-tests",
  "weather-daily",
]);

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ entity: string }> },
) {
  const { entity } = await params;
  if (!ENTITIES.has(entity)) {
    return NextResponse.json({ error: "Unknown export" }, { status: 404 });
  }

  const upstream = await fetch(`${apiBaseUrl()}/api/v1/export/${entity}.csv`, {
    cache: "no-store",
  });
  if (!upstream.ok) {
    return NextResponse.json({ error: "Export failed" }, { status: 502 });
  }

  return new NextResponse(upstream.body, {
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": `attachment; filename="${entity}.csv"`,
    },
  });
}
