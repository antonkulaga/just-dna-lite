from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import reflex as rx  # noqa: E402
from reflex.plugins.sitemap import SitemapPlugin  # noqa: E402

os.environ.setdefault("REFLEX_SSR", "true")
os.environ.setdefault("REFLEX_SOCKET_MAX_HTTP_BUFFER_SIZE", "50000000")

_IN_CONTAINER = os.path.exists("/.dockerenv") or os.environ.get("container") == "podman"


def _configured_hosts() -> list[str] | bool:
    if _IN_CONTAINER:
        return True

    hosts = {"lite.just-dna.life"}
    for env_name in ("DEPLOY_URL", "PUBLIC_APP_URL"):
        parsed = urlparse(os.environ.get(env_name, "").strip())
        if parsed.hostname:
            hosts.add(parsed.hostname)
    extra_hosts = os.environ.get("VITE_ALLOWED_HOSTS", "").strip()
    if extra_hosts:
        hosts.update(host.strip() for host in extra_hosts.split(",") if host.strip())
    return sorted(hosts)


_vite_hosts = _configured_hosts()

_UMAMI_SCRIPT_URL = os.environ.get(
    "UMAMI_SCRIPT_URL",
    "https://umami.just-dna.life/script.js",
).strip()
_UMAMI_WEBSITE_ID = os.environ.get(
    "UMAMI_WEBSITE_ID",
    "7f9afbbf-3ab8-4570-87c4-4bdf78a2ea31",
).strip()
_UMAMI_DOMAINS = os.environ.get("UMAMI_DOMAINS", "").strip()
_UMAMI_HOST_URL = os.environ.get("UMAMI_HOST_URL", "").strip()


def _head_components() -> list[rx.Component]:
    """Build static head scripts compiled into the Reflex frontend."""

    components: list[rx.Component] = [
        rx.script(src="https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js"),
        rx.script(src="https://cdn.jsdelivr.net/npm/fomantic-ui@2.9.4/dist/semantic.min.js"),
    ]
    if _UMAMI_SCRIPT_URL and _UMAMI_WEBSITE_ID:
        umami_attrs: dict[str, str] = {"data-website-id": _UMAMI_WEBSITE_ID}
        if _UMAMI_DOMAINS:
            umami_attrs["data-domains"] = _UMAMI_DOMAINS
        if _UMAMI_HOST_URL:
            umami_attrs["data-host-url"] = _UMAMI_HOST_URL
        components.append(rx.script(src=_UMAMI_SCRIPT_URL, custom_attrs=umami_attrs))
    return components

config = rx.Config(
    app_name="webui",
    plugins=[rx.plugins.RadixThemesPlugin()],
    disable_plugins=[SitemapPlugin],
    vite_allowed_hosts=_vite_hosts,
    stylesheets=[
        "https://cdn.jsdelivr.net/npm/fomantic-ui@2.9.4/dist/semantic.min.css",
    ],
    head_components=_head_components(),
    tailwind=None,
    show_built_with_reflex=False,
)
