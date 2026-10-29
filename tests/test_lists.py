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
