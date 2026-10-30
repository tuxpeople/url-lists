"""Extract allowlist recommendations from the first post of Pi-hole topic 212."""

import argparse
import csv
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import shlex

from build_lists import ROOT, download, parse_domains

URL = "https://discourse.pi-hole.net/t/commonly-whitelisted-domains/212"
API = "https://discourse.pi-hole.net/t/212.json"


class Content(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings = ["", "", ""]
        self.capture = None
        self.parts = []
        self.events = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3", "pre", "p") and self.capture is None:
            self.capture = tag
            self.parts = []
        elif tag == "br" and self.capture:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != self.capture:
            return
        text = "".join(self.parts).strip()
        if tag in ("h1", "h2", "h3"):
            level = int(tag[1]) - 1
            self.headings[level:] = [" ".join(text.split())] + [""] * (2 - level)
        else:
            self.events.append((tuple(self.headings), tag, text))
        self.capture = None


def expand_domain(target):
    match = re.fullmatch(r"([^{}]*)\{(\d+)\.\.(\d+)\}([^{}]*)", target)
    if not match:
        return [target]
    prefix, start, end, suffix = match.groups()
    if not 0 <= int(end) - int(start) <= 100:
        raise ValueError("Unexpected shell range")
    return [f"{prefix}{number}{suffix}" for number in range(int(start), int(end) + 1)]


def extract(data):
    posts = [post for post in data["post_stream"]["posts"] if post["post_number"] == 1]
    if len(posts) != 1 or posts[0].get("topic_id") != 212:
        raise ValueError("Missing or unexpected forum wiki post")
    parser = Content()
    parser.feed(posts[0]["cooked"])
    domains, patterns, rows = set(), set(), []
    for headings, tag, text in parser.events:
        if tag == "p":
            # This one recommendation is prose rather than a command.
            if headings[1] == "Rumble" and "wildcard" in text and "rmbl.ws" in text:
                domains.add("*.rmbl.ws")
                rows.append([*headings, "domain", "*.rmbl.ws", "included", "prose wildcard recommendation"])
            continue
        if headings[1].startswith("Allow all Google Domains listed above"):
            # This redundant summary has a line-broken 'firestore.googleapis.com'.
            # Individual recommendations above are authoritative for this import.
            rows.append([*headings, "summary", "", "excluded-duplicate-summary", text])
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line == "*Or Try:*":
                continue
            tokens = shlex.split(line, comments=True, posix=False)
            if len(tokens) < 3 or tokens[0] != "pihole":
                raise ValueError(f"Unexpected forum command: {line}")
            if not headings[0] or not headings[1]:
                raise ValueError("Forum recommendation has no category")
            option = tokens[1]
            for token in tokens[2:]:
                if len(token) >= 2 and token[0] in "\"'" and token[-1] == token[0]:
                    token = token[1:-1]
                if option in ("--allow-regex", "--white-regex"):
                    # Preserve original expressions; no execution or automatic import.
                    patterns.add(token)
                    rows.append([*headings, "regex", token, "metadata-only", line])
                elif option in ("allow", "-w", "--white"):
                    for domain in expand_domain(token):
                        parsed = parse_domains(domain, URL)
                        if len(parsed) != 1:
                            raise ValueError("Expected one domain per argument")
                        domain = next(iter(parsed))
                        domains.add(domain)
                        rows.append([*headings, "domain", domain, "included", line])
                else:
                    raise ValueError(f"Unsupported forum command: {option}")
    if len(domains) < 150 or not {"clients4.google.com", "itunes.apple.com", "www.msftncsi.com"} <= domains:
        raise ValueError("Forum extraction incomplete; review source layout")
    return domains, patterns, rows


def update(data, root=ROOT):
    domains, patterns, rows = extract(data)
    content = f"# Source: {URL}\n# Wiki post 1 only; community recommendations; regex commands kept in metadata.\n"
    content += "".join(domain + "\n" for domain in sorted(domains))
    details = io.StringIO()
    writer = csv.writer(details)
    writer.writerow(["category", "subcategory", "detail", "target_type", "target", "status", "source_command"])
    writer.writerows(rows)
    (root / "lists/allow/pihole-forum.txt").write_text(content, encoding="utf-8")
    directory = root / "metadata"
    directory.mkdir(exist_ok=True)
    (directory / "pihole-forum.csv").write_text(details.getvalue(), encoding="utf-8")
    (directory / "pihole-forum-regex.txt").write_text(
        "".join(pattern + "\n" for pattern in sorted(patterns)), encoding="utf-8")
    print(f"Pi-hole forum: {len(domains)} unique domains/wildcards, {len(patterns)} metadata-only regex rules")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="Use a previously downloaded topic response")
    args = parser.parse_args()
    data = json.loads(args.json.read_text(encoding="utf-8") if args.json else download(API))
    update(data)
