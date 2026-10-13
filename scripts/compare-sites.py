#!/usr/bin/env python3
"""Compare saved Hugo builds without a browser or screenshots (Python stdlib)."""
import argparse
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET


def normalized(value):
    return re.sub(r"\s+", " ", value).strip()


class Page(HTMLParser):
    def __init__(self, root):
        super().__init__()
        self.root = root
        self.body = False
        self.style = False
        self.jsonld = False
        self.events = []
        self.styles = []
        self.stylesheets = []
        self.metadata = {}
        self.structured_data = []
        self.references = []

    def local_file(self, url):
        parsed = urlparse(url)
        return self.root / unquote(parsed.path).lstrip("/")

    def asset(self, url):
        file = self.local_file(url)
        if file.is_file():
            return "sha256:" + hashlib.sha256(file.read_bytes()).hexdigest()
        return url

    def handle_starttag(self, tag, attrs):
        attrs = {key: normalized(value) if value is not None else None for key, value in attrs}
        # The removed framework marker had no styling or script behavior.
        if attrs.get("class"):
            attrs["class"] = " ".join(c for c in attrs["class"].split() if c != "blox-_")
        for key in ("src", "srcset"):
            if attrs.get(key):
                attrs[key] = re.sub(r"/media/[^ ,]+", lambda m: self.asset(m[0]), attrs[key])
        if tag == "body":
            self.body = True
        if self.body:
            self.events.append(("start", tag, sorted(attrs.items())))
        if tag == "style":
            self.style = True
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.jsonld = True
        if tag == "meta":
            key = attrs.get("name") or attrs.get("property") or attrs.get("http-equiv")
            if key != "generator":
                value = attrs.get("content", "")
                self.metadata[key] = re.sub(r"https?://[^ /]+/media/[^ ]+", lambda m: self.asset(m[0]), value)
        if tag == "link" and attrs.get("rel") == "stylesheet":
            url = attrs["href"]
            if not urlparse(url).scheme:
                css = self.local_file(url).read_text()
                self.stylesheets.append(re.sub(r"/\*.*?\*/", "", css, flags=re.S).strip())
            else:
                self.stylesheets.append(url)
        if tag in ("script", "img", "link", "a"):
            for key in ("src", "href"):
                if attrs.get(key, "").startswith("/"):
                    self.references.append(attrs[key])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.body:
            self.events.append(("end", tag))
        if tag == "body":
            self.body = False
        if tag == "style":
            self.style = False
        if tag == "script":
            self.jsonld = False

    def handle_data(self, value):
        if self.style:
            self.styles.append(value.strip())
        if self.jsonld:
            self.structured_data.append(json.loads(value))
        if self.body and normalized(value):
            self.events.append(("text", normalized(value)))


def parse(root, name):
    page = Page(root)
    page.feed((root / name).read_text())
    return page


def feed_signature(path):
    tree = ET.parse(path)
    channel = tree.getroot().find("channel")
    if channel is None:
        # Sitemaps are compared in full.
        return ET.tostring(tree.getroot())
    metadata = [(element.tag, element.text) for element in channel if element.tag not in ("generator", "item", "image")]
    entries = [tuple((key, item.findtext(key)) for key in ("title", "link", "pubDate", "guid")) for item in channel.findall("item")]
    return metadata, entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    before, after = args.before.resolve(), args.after.resolve()
    if not before.is_dir() or not after.is_dir():
        parser.error("Both builds must be existing directories")
    old_routes = {p.relative_to(before) for p in before.rglob("*.html")}
    new_routes = {p.relative_to(after) for p in after.rglob("*.html")}
    failures = []
    if not old_routes:
        parser.error("The baseline has no HTML pages")
    if old_routes != new_routes:
        failures.append(f"HTML routes differ: missing {old_routes - new_routes}; added {new_routes - old_routes}")
    for name in sorted(old_routes & new_routes):
        old, new = parse(before, name), parse(after, name)
        for label, left, right in (
            ("body markup/links/images", old.events, new.events),
            ("inline styles", old.styles, new.styles),
            ("stylesheets/fonts", old.stylesheets, new.stylesheets),
            ("metadata", old.metadata, new.metadata),
            ("structured data", old.structured_data, new.structured_data),
        ):
            if left != right:
                failures.append(f"{name}: changed {label}")
        for url in new.references:
            file = new.local_file(url)
            if not file.exists():
                failures.append(f"{name}: missing {url}")
    old_xml = {p.relative_to(before) for p in before.rglob("*.xml")}
    new_xml = {p.relative_to(after) for p in after.rglob("*.xml")}
    if old_xml != new_xml:
        failures.append("Feed/sitemap routes differ")
    for name in sorted(old_xml & new_xml):
        if feed_signature(before / name) != feed_signature(after / name):
            failures.append(f"{name}: changed feed entry metadata or sitemap")
    for name in (Path("robots.txt"), Path("en/backlinks.json"), Path("zh/backlinks.json")):
        if (before / name).exists() and (before / name).read_bytes() != (after / name).read_bytes():
            failures.append(f"{name}: changed output")
    if failures:
        print("\n".join(failures[:30]))
        print(f"FAIL: {len(failures)} differences")
        return 1
    print(f"PASS: {len(old_routes)} HTML routes and {len(old_xml)} feed/sitemap routes; matching body markup, styles, links, image bytes, and metadata")
    return 0


if __name__ == "__main__":
    sys.exit(main())
