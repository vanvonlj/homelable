# Patches

Local patches applied by `.github/workflows/build-mcp.yml` over upstream
`Pouzor/homelable` before building our `homelable-mcp` image. Each patch
is a unified diff designed to **fail loudly** (not silently) if upstream
changes in a way that makes the patch no longer applicable.

## Workflow behaviour

For every `.patch` file in this directory:

1. `patch --dry-run -p1` checks whether the patch still applies cleanly.
2. **Applies cleanly** → patch is applied, image is tagged with a `-patched`
   suffix (e.g. `1.11.0-patched`), workflow logs "patch applied".
3. **Fails to apply** → patch is skipped (upstream likely fixed the
   underlying bug), image is tagged without the suffix (e.g. `1.12.0`),
   workflow logs "patch no longer applies — upstream may have fixed it".
4. **Hunk conflict** (upstream restructured but bug still present) →
   workflow fails with a clear error pointing at the failing hunk. Patch
   author reviews upstream changes, updates the `.patch`, re-runs.

This makes the fork self-healing: once a patch's upstream bug is fixed, the
patch silently retires itself. The `.patch` file stays in this directory as
inert dead code until someone chooses to delete it.

## Current patches

### `fix-streamable-http-mount.patch`

**Targets:** `mcp/app/main.py`
**Upstream bug:** Upstream wraps `session_manager.handle_request()` inside a
`@app.api_route("/mcp")` FastAPI handler. `StreamableHTTPSessionManager` is
an ASGI app — it sends its own `http.response.start`. FastAPI then tries to
send its own response.start after the handler returns, raising:

```
RuntimeError: Unexpected ASGI message 'http.response.start' sent,
after response already completed.
```

Every `POST /mcp` fails this way, rendering the MCP server unreachable from
any MCP client.

**Fix:** Mount the session manager via `starlette.routing.Mount("/mcp", app=...)`
so the session manager owns the response cycle directly, without FastAPI's
route handler interfering.

**Upstream status:** PR filed at https://github.com/Pouzor/homelable/pull/105.
Remove this patch once merged and a release containing the fix is tagged.
