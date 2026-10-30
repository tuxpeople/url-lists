import json
import re
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_lists import build, parse_domains, export_pihole
from update_apple import extract


class ListsTest(unittest.TestCase):
    def test_redundant_wildcards_removed_per_export(self):
        domains = {"*.microsoft.com", "*.security.microsoft.com", "*.a.security.microsoft.com",
                   "*.notmicrosoft.com", "*.com.example", "security.microsoft.com"}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            export_pihole(output, "all", domains)
            patterns = (output / "all-regex.txt").read_text().splitlines()
            self.assertEqual(len(patterns), 3)
            self.assertIn(r"^([^.]+\.)+microsoft\.com$", patterns)
            self.assertIn(r"^([^.]+\.)+notmicrosoft\.com$", patterns)
            self.assertEqual((output / "all-exact.txt").read_text(), "security.microsoft.com\n")
            self.assertEqual(len(domains), 6)
            # A later filtered export must restore the narrower rule automatically.
            export_pihole(output, "required", {"*.security.microsoft.com"})
            self.assertEqual((output / "required-regex.txt").read_text(),
                             "^([^.]+\\.)+security\\.microsoft\\.com$\n")
            for host in ("microsoft.com", "security.microsoft.com", "a.microsoft.com",
                         "a.security.microsoft.com", "a.b.security.microsoft.com",
                         "a.notmicrosoft.com", "a.com.example", "a.microsoft.com.evil"):
                before = any(re.search(r"^([^.]+\.)+" + re.escape(domain[2:]) + "$", host)
                             for domain in domains if domain.startswith("*."))
                after = any(re.search(pattern, host) for pattern in patterns)
                self.assertEqual(before, after, host)

    def test_pihole_wildcard_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            export_pihole(output, "apple-allow", {"*.push.apple.com", "albert.apple.com"})
            pattern = (output / "apple-allow-regex.txt").read_text().strip()
            for domain in ("a.push.apple.com", "a.b.push.apple.com"):
                self.assertIsNotNone(re.search(pattern, domain))
            for domain in ("push.apple.com", "evilpush.apple.com", "a.push.apple.com.evil", "a.pushXapple.com"):
                self.assertIsNone(re.search(pattern, domain))
            self.assertEqual((output / "apple-allow-exact.txt").read_text(), "albert.apple.com\n")
            self.assertEqual(sorted(path.suffix for path in output.iterdir()), [".txt", ".txt"])

    def test_normalization(self):
        self.assertEqual(parse_domains("EXAMPLE.com.\nexample.com # comment\n*.Example.org", "test"),
                         {"example.com", "*.example.org"})

    def test_reject_non_domains(self):
        for value in ("https://example.com/a", "0.0.0.0", "example.com:443", "foo", "*example.com", "a.com b.com"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_domains(value, "test")

    def test_conflict_preserves_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sources.json").write_text(json.dumps({"sources": []}))
            for kind in ("allow", "block"):
                folder = root / "lists" / kind
                folder.mkdir(parents=True)
                (folder / "custom.txt").write_text("example.com\n")
            (root / "dist").mkdir()
            output = root / "dist/allow.txt"
            output.write_text("previous.example\n")
            with self.assertRaises(ValueError):
                build(root)
            self.assertEqual(output.read_text(), "previous.example\n")

    def test_apple_layout_failure(self):
        with self.assertRaises(ValueError):
            extract("<html>No tables available</html>")

    def test_apple_table_extraction(self):
        hosts = ["albert.apple.com", "*.push.apple.com"] + [f"host{i}.example.com" for i in range(80)]
        html = "<h2>Device <span>management</span></h2><h3>Administrators</h3><table><tr><th>Hosts</th><th>Ports</th></tr>"
        for host in hosts:
            html += f"<tr><td><p>{host}</p></td><td>443</td><td>TCP</td><td>macOS</td><td></td><td>Yes</td></tr>"
        result, rows = extract(html + "</table>")
        self.assertEqual(result, set(hosts))
        self.assertEqual(len(rows), 82)
        self.assertTrue(all(row[:2] == ["Device management", "Administrators"] for row in rows))

        html += "</table><h2>Software updates</h2><table><tr><td>albert.apple.com</td><td>443</td><td>TCP</td><td>macOS</td><td></td><td>Yes</td></tr>"
        _, rows = extract(html + "</table>")
        self.assertEqual(rows[-1][:3], ["Software updates", "", "albert.apple.com"])
        self.assertEqual(rows[0][:3], ["Device management", "Administrators", "albert.apple.com"])

    def test_apple_requires_category(self):
        html = "<table><tr><td>albert.apple.com</td><td>443</td><td>TCP</td><td>macOS</td><td></td><td>Yes</td></tr></table>"
        with self.assertRaisesRegex(ValueError, "no category"):
            extract(html)
