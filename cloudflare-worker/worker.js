/**
 * Cloudflare Worker — FIT Demo API Proxy
 *
 * Forwards requests to the FIT diet plan API server, adding CORS headers
 * so the app can run on GitHub Pages (or any HTTPS host).
 *
 * Deploy to Cloudflare Workers (free tier):
 *   1. Go to https://dash.cloudflare.com → Workers & Pages → Create
 *   2. Paste this file, deploy
 *   3. Note your worker URL: https://<name>.<account>.workers.dev
 *   4. Set that URL as WORKER_BASE_URL in index.html (see comment there)
 *
 * Request format:
 *   Browser calls:  https://<worker>/rest/s1/fit/dietPlan/v3/generate
 *   Worker calls:   http://185.143.103.106:8080/rest/s1/fit/dietPlan/v3/generate
 */

// Cloudflare Workers cannot connect to bare IP addresses (error 1003).
// Use the reverse-DNS hostname that resolves to the same server.
const API_ORIGIN = "http://ov-9a74e5.infomaniak.ch:8080";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

export default {
  async fetch(request) {
    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    // Rewrite URL: replace worker origin with API origin
    const url = new URL(request.url);
    const targetUrl = API_ORIGIN + url.pathname + url.search;

    // Forward the request (preserve method, headers, body)
    const proxyRequest = new Request(targetUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: "follow",
    });

    try {
      const response = await fetch(proxyRequest);

      // Clone response and inject CORS headers
      const newHeaders = new Headers(response.headers);
      Object.entries(CORS_HEADERS).forEach(([k, v]) => newHeaders.set(k, v));

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: newHeaders,
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: "Proxy error: " + err.message }), {
        status: 502,
        headers: { "Content-Type": "application/json", ...CORS_HEADERS },
      });
    }
  },
};
