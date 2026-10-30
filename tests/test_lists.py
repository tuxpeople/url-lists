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
            entries = set((output / "all-exact.txt").read_text().splitlines())
            self.assertEqual(entries, {"@@||microsoft.com^", "@@||notmicrosoft.com^",
                                       "@@||com.example^", "security.microsoft.com"})
            self.assertEqual((output / "all-regex.txt").read_text(), "")
            self.assertEqual(len(domains), 6)
            # Filtering precedes minimization, so the narrower rule is restored.
            export_pihole(output, "required", {"*.security.microsoft.com"})
            self.assertEqual((output / "required-exact.txt").read_text(),
                             "@@||security.microsoft.com^\n")

    def test_pihole_allow_wildcard_includes_base_and_subdomains(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            export_pihole(output, "apple-allow", {"*.push.apple.com", "albert.apple.com"})
            self.assertEqual((output / "apple-allow-exact.txt").read_text(),
                             "@@||push.apple.com^\nalbert.apple.com\n")
            self.assertEqual((output / "apple-allow-regex.txt").read_text(), "")
            self.assertEqual(sorted(path.suffix for path in output.iterdir()), [".txt", ".txt"])

    def test_deny_wildcards_keep_subdomain_only_regex(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            export_pihole(output, "block", {"*.example.com", "*.child.example.com", "exact.example.org"}, kind="block")
            pattern = (output / "block-regex.txt").read_text().strip()
            self.assertEqual(pattern, r"^([^.]+\.)+example\.com$")
            self.assertEqual((output / "block-exact.txt").read_text(), "exact.example.org\n")
            self.assertIsNotNone(re.search(pattern, "a.b.example.com"))
            self.assertIsNone(re.search(pattern, "example.com"))
            self.assertIsNone(re.search(pattern, "notexample.com"))

    def test_microsoft_special_regex_survives_build(self):
        from update_microsoft365 import SPECIAL
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sources.json").write_text('{"sources": []}')
            (root / "metadata").mkdir()
            # Real checked-in API snapshot verifies integration of both export paths.
            snapshot = Path(__file__).resolve().parents[1] / "metadata/microsoft365.json"
            data = json.loads(snapshot.read_text())
            (root / "metadata/microsoft365.json").write_text(json.dumps(data))
            for kind in ("allow", "block"):
                (root / "lists" / kind).mkdir(parents=True)
            (root / "lists/allow/microsoft365.txt").write_text("*.microsoft.com\nlogin.microsoftonline.com\n")
            build(root, offline=True)
            for name in ("allow", "microsoft365-allow"):
                self.assertEqual(set((root / f"pihole/{name}-regex.txt").read_text().splitlines()),
                                 set(SPECIAL.values()))
                self.assertIn("@@||microsoft.com^", (root / f"pihole/{name}-exact.txt").read_text().splitlines())

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
