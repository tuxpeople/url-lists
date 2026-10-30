"""Build strict domain lists using only the Python standard library."""

import argparse
import ipaddress
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 20 * 1024 * 1024


def parse_domains(text, origin):
    domains = set()
    for number, line in enumerate(text.splitlines(), 1):
        value = line.split("#", 1)[0].strip().lower().rstrip(".")
        if not value:
            continue
        try:
            value = value.encode("idna").decode("ascii")
            hostname = value[2:] if value.startswith("*.") else value
            labels = hostname.split(".")
            if len(value) > 253 or len(labels) < 2 or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in labels
            ):
                raise ValueError("invalid domain")
            try:
                ipaddress.ip_address(hostname)
            except ValueError:
                pass
            else:
                raise ValueError("IP addresses are not domains")
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"{origin}:{number}: invalid domain {line!r}") from error
        domains.add(value)
    return domains


def download(url):
    if urlsplit(url).scheme != "https":
        raise ValueError("Sources must use HTTPS")
    with urlopen(url, timeout=60) as response:
        if urlsplit(response.url).scheme != "https":
            raise ValueError("Redirect to non-HTTPS source")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Source exceeds 20 MiB")
    return data.decode("utf-8-sig")


def export_pihole(output, name, domains, kind="allow"):
    """Export allow wildcards as ABP subscriptions; retain deny regex behavior."""
    if kind not in {"allow", "block"}:
        raise ValueError(f"Invalid export type: {kind}")
    exact = {domain for domain in domains if not domain.startswith("*.")}
    wildcard_bases = {domain[2:] for domain in domains if domain.startswith("*.")}
    # Remove wildcards covered by an ancestor, respecting DNS label boundaries.
    # Check DNS label boundaries, rather than matching arbitrary string suffixes.
    minimal_bases = {
        base for base in wildcard_bases
        if not any(".".join(base.split(".")[index:]) in wildcard_bases
                   for index in range(1, len(base.split("."))))
    }
    if kind == "allow":
        # Keep the existing subscription filename for already configured clients.
        # ABP includes the base domain as well as all subdomains, intentionally.
        exact.update(f"@@||{base}^" for base in minimal_bases)
        regex = []
    else:
        regex = sorted(
            r"^([^.]+\.)+" + base.replace(".", r"\.") + "$"
            for base in minimal_bases
        )
    output.mkdir(exist_ok=True)
    for suffix, entries in (("exact", sorted(exact)), ("regex", regex)):
        (output / f"{name}-{suffix}.txt").write_text(
            "".join(entry + "\n" for entry in entries), encoding="utf-8"
        )


def build(root=ROOT, offline=False):
    config = json.loads((root / "sources.json").read_text(encoding="utf-8"))
    result = {kind: set() for kind in ("allow", "block")}
    for kind in result:
        for path in sorted((root / "lists" / kind).glob("*.txt")):
            result[kind].update(parse_domains(path.read_text(encoding="utf-8"), path))
    names = set()
    for source in config["sources"]:
        name = source["name"]
        if name in names:
            raise ValueError(f"Duplicate source name: {name}")
        names.add(name)
        kind = source["type"]
        if kind not in result:
            raise ValueError(f"Invalid source type: {kind}")
        if not source.get("enabled", True) or offline:
            continue
        if not source.get("license") or not source.get("homepage"):
            raise ValueError(f"{name}: homepage and license are required")
        domains = parse_domains(download(source["url"]), name)
        if not domains:
            raise ValueError(f"{name}: empty source")
        result[kind].update(domains)
    conflicts = result["allow"] & result["block"]
    if conflicts:
        raise ValueError("Allow/block conflict: " + ", ".join(sorted(conflicts)[:20]))
    microsoft = root / "metadata/microsoft365.json"
    patterns = set()
    if microsoft.exists():
        from update_microsoft365 import extract
        _, _, patterns = extract(json.loads(microsoft.read_text(encoding="utf-8")))
    # Do not change outputs until every input has passed validation.
    output = root / "dist"
    output.mkdir(exist_ok=True)
    for kind, domains in result.items():
        content = "".join(domain + "\n" for domain in sorted(domains))
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output, delete=False) as handle:
            handle.write(content)
            temporary = Path(handle.name)
        temporary.replace(output / f"{kind}.txt")
        print(f"{kind}: {len(domains)} domains")
        export_pihole(root / "pihole", kind, domains, kind=kind)
    for name in ("apple", "docker", "openshift", "microsoft365", "pihole-forum"):
        source = root / "lists" / "allow" / f"{name}.txt"
        if source.exists():
            export_pihole(root / "pihole", f"{name}-allow",
                          parse_domains(source.read_text(encoding="utf-8"), source))
    if patterns:
        for name in ("microsoft365-allow", "allow"):
            path = root / "pihole" / f"{name}-regex.txt"
            combined = set(path.read_text(encoding="utf-8").splitlines()) | patterns
            path.write_text("".join(pattern + "\n" for pattern in sorted(combined)), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Build local lists only")
    args = parser.parse_args()
    try:
        build(offline=args.offline)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Error: {error}\n")
