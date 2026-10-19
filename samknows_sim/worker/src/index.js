// Simulated SamKnows archive server (Cloudflare Worker + Workers KV).
//
// Mirrors what pipeline/downloader.py expects from the real SamKnows server:
//   GET /                      -> HTTP Basic-auth protected "Index of /" page
//                                 linking to every YYYYMMDD-*.tar.gz archive
//   GET /<YYYYMMDD-...>.tar.gz -> the archive itself, streamed from KV
//
// Each archive is one KV entry keyed by its filename, uploaded with metadata
// {"size": <bytes>, "uploaded": "<ISO timestamp>"} for the index page and a
// TTL for retention (see .github/workflows/samknows-daily.yml).
//
// Bindings (see wrangler.toml): ARCHIVES (KV namespace)
// Secrets: SAMKNOWS_USER, SAMKNOWS_PASS  (wrangler secret put ...)

const ARCHIVE_RE = /^\d{8}-[A-Za-z0-9_-]+\.tar\.gz$/;

export default {
  async fetch(request, env) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
    }
    if (!isAuthorized(request, env)) {
      return new Response("Unauthorized", {
        status: 401,
        headers: { "WWW-Authenticate": 'Basic realm="SamKnows data", charset="UTF-8"' },
      });
    }

    const key = decodeURIComponent(new URL(request.url).pathname.slice(1));
    if (key === "") return indexPage(env);
    if (!ARCHIVE_RE.test(key)) return new Response("Not Found", { status: 404 });

    const { value, metadata } = await env.ARCHIVES.getWithMetadata(key, { type: "arrayBuffer" });
    if (value === null) return new Response("Not Found", { status: 404 });

    const headers = new Headers({
      "Content-Type": "application/gzip",
      "Content-Length": String(value.byteLength),
    });
    if (metadata?.uploaded) headers.set("Last-Modified", new Date(metadata.uploaded).toUTCString());
    return new Response(request.method === "HEAD" ? null : value, { headers });
  },
};

function isAuthorized(request, env) {
  if (!env.SAMKNOWS_USER || !env.SAMKNOWS_PASS) return false; // fail closed if secrets are missing
  const expected = new TextEncoder().encode("Basic " + btoa(`${env.SAMKNOWS_USER}:${env.SAMKNOWS_PASS}`));
  const got = new TextEncoder().encode(request.headers.get("Authorization") || "");
  return got.byteLength === expected.byteLength && crypto.subtle.timingSafeEqual(got, expected);
}

async function indexPage(env) {
  const keys = [];
  let cursor;
  do {
    const page = await env.ARCHIVES.list({ cursor, limit: 1000 });
    keys.push(...page.keys.filter((k) => ARCHIVE_RE.test(k.name)));
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);

  keys.sort((a, b) => a.name.localeCompare(b.name));
  const rows = keys.map(({ name, metadata }) => {
    const modified = metadata?.uploaded ? metadata.uploaded.slice(0, 16).replace("T", " ") : "-";
    const size = metadata?.size ? `${Math.ceil(metadata.size / 1024)}K` : "-";
    return `<a href="${name}">${name}</a>  ${modified}  ${size}`;
  });

  const html =
    "<html><head><title>Index of /</title></head><body><h1>Index of /</h1><pre>" +
    rows.join("\n") +
    "</pre></body></html>";
  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
}
