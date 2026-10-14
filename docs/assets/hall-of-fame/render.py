"""Render original plaque frames around attributed public profile images.

Run with Python 3.11+: python3 docs/assets/hall-of-fame/render.py
No network, packages, generated portraits or font files required.
"""

import base64
import hashlib
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def render(person):
    onyx = person["badge"] == "Onyx"
    accent = "#b6c7d9" if onyx else "#d9b574"
    portrait = person.get("file")
    if portrait:
        data = (ROOT / portrait).read_bytes()
        if hashlib.sha256(data).hexdigest() != person["sha256"]:
            raise ValueError(f"source image hash mismatch: {portrait}")
        encoded = base64.b64encode(data).decode("ascii")
        image = f'<image x="62" y="126" width="246" height="246" href="data:{person["mime"]};base64,{encoded}" clip-path="url(#portrait)" preserveAspectRatio="xMidYMid slice"/>'
    else:
        image = '<circle cx="185" cy="249" r="123" fill="#202632"/><text x="185" y="270" text-anchor="middle" font-family="Georgia,serif" font-size="68" fill="#d9b574">YC</text>'
    # Pen nib for intellectual contributions; a faceted onyx for polish.
    mark = ('<path d="M700 96l24 18-8 29h-32l-8-29zM676 114h48M700 96l-16 47M700 96l16 47"/>'
            if onyx else '<path d="M693 99l18 18-13 30-18-18zM693 99l-13 30M698 147l-23 7 5-25M693 119l-18 35"/><circle cx="693" cy="119" r="3"/>')
    name, handle, title, subtitle = [escape(person[key]) for key in ("name", "handle", "title", "subtitle")]
    label = escape(person["image_kind"])
    badge = person["badge"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="460" viewBox="0 0 800 460" role="img" aria-labelledby="title desc">
<title id="title">{name} — {badge} Badge</title>
<desc id="desc">{title}. {subtitle}. {label}. A sparks acknowledgement, not an endorsement.</desc>
<defs>
  <linearGradient id="surface" x2="1" y2="1"><stop stop-color="#232938"/><stop offset="1" stop-color="#0b1019"/></linearGradient>
  <linearGradient id="metal"><stop stop-color="{accent}"/><stop offset=".5" stop-color="#f5e8cc"/><stop offset="1" stop-color="{accent}"/></linearGradient>
  <clipPath id="portrait"><circle cx="185" cy="249" r="123"/></clipPath>
</defs>
<rect width="800" height="460" rx="22" fill="#090d14"/>
<rect x="9" y="9" width="782" height="442" rx="17" fill="url(#surface)" stroke="url(#metal)" stroke-width="2"/>
<rect x="22" y="22" width="756" height="416" rx="10" fill="none" stroke="{accent}" stroke-opacity=".32"/>
<g fill="{accent}"><circle cx="34" cy="34" r="3"/><circle cx="766" cy="34" r="3"/><circle cx="34" cy="426" r="3"/><circle cx="766" cy="426" r="3"/></g>
<text x="54" y="68" font-family="sans-serif" font-size="16" letter-spacing="4" fill="{accent}">SPARKS / HALL OF FAME</text>
<path d="M54 87h692" stroke="{accent}" stroke-opacity=".35"/>
<circle cx="185" cy="249" r="130" fill="none" stroke="url(#metal)" stroke-width="3"/>
{image}
<g fill="none" stroke="{accent}" stroke-width="2.5" stroke-linejoin="round">{mark}</g>
<text x="352" y="148" font-family="sans-serif" font-size="15" letter-spacing="3" fill="{accent}">{badge.upper()} BADGE</text>
<text x="352" y="205" font-family="Georgia,serif" font-size="35" fill="#f4efe6">{name}</text>
<text x="353" y="235" font-family="sans-serif" font-size="17" fill="#b9c2d0">@{handle}</text>
<path d="M352 261h364" stroke="{accent}" stroke-opacity=".35"/>
<text x="352" y="299" font-family="sans-serif" font-size="20" fill="#f4efe6">{title}</text>
<text x="352" y="328" font-family="sans-serif" font-size="17" fill="#b9c2d0">{subtitle}</text>
<text x="54" y="409" font-family="sans-serif" font-size="13" fill="#8e9aaf">{label}</text>
</svg>
'''


def main():
    for person in json.loads((ROOT / "sources.json").read_text(encoding="utf-8")):
        (ROOT / f'{person["handle"]}.svg').write_text(render(person), encoding="utf-8")


if __name__ == "__main__":
    main()
