"""Import Microsoft 365 Worldwide endpoint sets from the official web service."""

import argparse
import csv
import io
import ipaddress
import json
from pathlib import Path
import uuid

from build_lists import ROOT, download, parse_domains

URL = "https://endpoints.office.com/endpoints/worldwide"
PAGE = "https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges"
HEADINGS = {
    "Exchange": "Exchange Online",
    "SharePoint": "SharePoint Online and OneDrive for Business",
    "Skype": "Microsoft Teams",
    "Common": "Microsoft 365 Common and Office Online",
}
SPECIAL = {
    "autodiscover.*.onmicrosoft.com": r"^autodiscover\.[^.]+\.onmicrosoft\.com$",
    "*cdn.onenote.net": r"^.*cdn\.onenote\.net$",
}


def extract(data):
    if not isinstance(data, list) or not data:
        raise ValueError("Empty or invalid Microsoft 365 response")
    hosts, rows, patterns, ids, areas = set(), [], set(), set(), set()
    for item in data:
        endpoint_id = item["id"]
        area = item["serviceArea"]
        required = item["required"]
        if (type(endpoint_id) is not int or endpoint_id in ids or area not in HEADINGS
                or type(required) is not bool or item["category"] not in {"Optimize", "Allow", "Default"}):
            raise ValueError("Invalid endpoint ID, service area, required flag or category")
        ids.add(endpoint_id)
        areas.add(area)
        heading = "Microsoft 365 Unified Domains" if endpoint_id == 184 else HEADINGS[area]
        base = [endpoint_id, heading, area, item.get("serviceAreaDisplayName", ""),
                "Required" if required else "Optional", item["category"],
                item.get("tcpPorts", ""), item.get("udpPorts", ""),
                item.get("expressRoute", ""), item.get("notes", "")]
        for target in item.get("urls", []):
            if target in SPECIAL:
                patterns.add(SPECIAL[target])
                status = "special-wildcard"
            else:
                parsed = parse_domains(target, URL)
                if len(parsed) != 1:
                    raise ValueError("Expected one domain per URL entry")
                hosts.update(parsed)
                status = "wildcard" if target.startswith("*.") else "exact"
            rows.append([*base, "domain", target, status])
        for target in item.get("ips", []):
            ipaddress.ip_network(target)
            rows.append([*base, "ip", target, "metadata-only"])
        if not item.get("urls") and not item.get("ips"):
            raise ValueError(f"Endpoint set {endpoint_id} has no destinations")
    if areas != set(HEADINGS) or not {1, 12, 31, 184} <= ids or len(hosts) < 50:
        raise ValueError("Microsoft 365 extraction incomplete; review source")
    return hosts, rows, patterns


def update(data, root=ROOT):
    hosts, rows, _ = extract(data)
    content = f"# Source: {URL}\n# Worldwide; Required and Optional included. Special wildcards are in metadata/microsoft365.json.\n"
    content += "".join(host + "\n" for host in sorted(hosts))
    details = io.StringIO()
    writer = csv.writer(details)
    writer.writerow(["endpoint_id", "category", "service_area", "service_area_display_name",
                     "requirement", "network_category", "tcp_ports", "udp_ports",
                     "express_route", "notes", "target_type", "target", "export_status"])
    writer.writerows(rows)
    (root / "lists/allow/microsoft365.txt").write_text(content, encoding="utf-8")
    directory = root / "metadata"
    directory.mkdir(exist_ok=True)
    (directory / "microsoft365.csv").write_text(details.getvalue(), encoding="utf-8")
    (directory / "microsoft365.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Microsoft 365: {len(data)} endpoint sets, {len(hosts)} normal domain entries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="Use previously downloaded JSON")
    args = parser.parse_args()
    data = json.loads(args.json.read_text(encoding="utf-8") if args.json else
                      download(f"{URL}?ClientRequestId={uuid.uuid4()}"))
    update(data)
