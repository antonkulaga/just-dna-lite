from __future__ import annotations

import html
import os
import re

DEFAULT_UMAMI_SCRIPT_URL = "https://umami.just-dna.life/script.js"
DEFAULT_UMAMI_WEBSITE_ID = "7f9afbbf-3ab8-4570-87c4-4bdf78a2ea31"

_HEAD_CLOSE_RE = re.compile(r"</head\s*>", flags=re.IGNORECASE)


def umami_config() -> tuple[str, str, str, str]:
    """Return Umami script settings from environment, with production defaults."""

    script_url = os.environ.get("UMAMI_SCRIPT_URL", DEFAULT_UMAMI_SCRIPT_URL).strip()
    website_id = os.environ.get("UMAMI_WEBSITE_ID", DEFAULT_UMAMI_WEBSITE_ID).strip()
    domains = os.environ.get("UMAMI_DOMAINS", "").strip()
    host_url = os.environ.get("UMAMI_HOST_URL", "").strip()
    return script_url, website_id, domains, host_url


def umami_script_tag() -> str:
    """Build the static Umami script tag for non-Reflex HTML pages."""

    script_url, website_id, domains, host_url = umami_config()
    if not script_url or not website_id:
        return ""

    attrs = [
        "defer",
        f'src="{html.escape(script_url, quote=True)}"',
        f'data-website-id="{html.escape(website_id, quote=True)}"',
    ]
    if domains:
        attrs.append(f'data-domains="{html.escape(domains, quote=True)}"')
    if host_url:
        attrs.append(f'data-host-url="{html.escape(host_url, quote=True)}"')

    return f"<script {' '.join(attrs)}></script>"


def inject_umami_tracker(html_text: str) -> str:
    """Inject Umami into an HTML document if it is configured and not present."""

    tag = umami_script_tag()
    if not tag or "data-website-id=" in html_text:
        return html_text

    match = _HEAD_CLOSE_RE.search(html_text)
    if not match:
        return f"{tag}\n{html_text}"

    return f"{html_text[:match.start()]}    {tag}\n{html_text[match.start():]}"
