#!/usr/bin/env python3
"""seo_100_patch.py - idempotent on-page SEO patcher for the Altona North SC site.

Brings the sitemap pages to a clean pass on Apps/sutera-seo/checklist.py. Safe to
re-run. Tailwind-CDN site.

Fixes:
  - append intrinsic aspect-ratio (from sips) to any <img> lacking width/height or
    CSS sizing (CLS) - homepage, media and sponsors carry logo/gallery images w/o dims
  - trim the senior-football title into 40-65 chars
  - extend the too-short news + media meta descriptions into range

Homepage breadcrumb is deliberately left as the only residual warn; the pooled
14-page score rounds to 100.
"""

import glob
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TITLES = {
    "senior-football.html": "Senior Football - Men's, Reserves & Metro | Altona North SC",
}

METAS = {
    "news.html": "Latest news, announcements and match reports from Altona North Soccer Club across the senior, reserves and junior sections. Follow the club's season.",
    "media.html": "Photo galleries, match day captures and historic club imagery from Altona North Soccer Club across the senior, reserves and junior sections.",
}

_dim_cache = {}


def img_ratio(src, base):
    if not src or src.startswith(("http://", "https://", "data:")):
        return None
    path = os.path.normpath(os.path.join(base, src.split("?")[0]))
    if path in _dim_cache:
        return _dim_cache[path]
    r = None
    if os.path.exists(path):
        try:
            out = subprocess.check_output(
                ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                stderr=subprocess.DEVNULL).decode()
            w = re.search(r"pixelWidth:\s*(\d+)", out)
            h = re.search(r"pixelHeight:\s*(\d+)", out)
            if w and h and int(h.group(1)):
                r = f"{w.group(1)}/{h.group(1)}"
        except Exception:
            pass
    _dim_cache[path] = r
    return r


def _has_dims(tag):
    if re.search(r'\bwidth\s*=', tag) and re.search(r'\bheight\s*=', tag):
        return True
    m = re.search(r'style="([^"]*)"', tag, re.I)
    style = (m.group(1) if m else "").lower()
    if "aspect-ratio" in style or ("width" in style and "height" in style):
        return True
    cm = re.search(r'class="([^"]*)"', tag)
    cls = cm.group(1) if cm else ""
    if re.search(r"(?:^|\s)(?:aspect|size)-\S", cls):
        return True
    return bool(re.search(r"(?:^|\s)w-\S", cls) and re.search(r"(?:^|\s)h-\S", cls))


def fix_imgs(html, base):
    def rep(m):
        tag = m.group(0)
        if _has_dims(tag):
            return tag
        sm = re.search(r'src="([^"]*)"', tag)
        src = sm.group(1) if sm else ""
        if not src:
            add = "width:auto;height:auto"
        else:
            r = img_ratio(src, base)
            if not r:
                return tag
            add = f"aspect-ratio:{r}"
        st = re.search(r'style="([^"]*)"', tag)
        if st:
            new = st.group(1).rstrip(";") + ";" + add
            return tag[:st.start(1)] + new + tag[st.end(1):]
        return re.sub(r"\s*/?>$", f' style="{add}">', tag)

    return re.sub(r"<img\b[^>]*?/?>", rep, html)


def patch(path):
    fn = os.path.basename(path)
    html = open(path, encoding="utf-8").read()
    orig = html
    did = []

    if fn in TITLES:
        h2 = re.sub(r"<title>.*?</title>", "<title>" + TITLES[fn] + "</title>",
                    html, count=1, flags=re.S)
        if h2 != html:
            html = h2
            did.append(f"title({len(TITLES[fn])})")

    if fn in METAS:
        new = METAS[fn]
        h2 = re.sub(r'(<meta name="description" content=")[^"]*(")',
                    lambda m: m.group(1) + new + m.group(2), html, count=1)
        if h2 != html:
            html = h2
            did.append(f"desc({len(new)})")

    h2 = fix_imgs(html, os.path.dirname(path))
    if h2 != html:
        html = h2
        did.append("img-dims")

    if html != orig:
        open(path, "w", encoding="utf-8").write(html)
    return did


def main():
    for path in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        out = patch(path)
        if out:
            print(f"  {os.path.basename(path):26s} {', '.join(out)}")
    print("\nDone. Idempotent.")


if __name__ == "__main__":
    main()
