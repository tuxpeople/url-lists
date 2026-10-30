import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_pihole_forum import extract, update


class ForumTest(unittest.TestCase):
    def data(self, extra=""):
        domains = ["clients4.google.com", "itunes.apple.com", "www.msftncsi.com"]
        domains += [f"host{i}.example.com" for i in range(150)]
        cooked = '<h1>Google</h1><h2><a href="#anchor"></a>Maps and services</h2>'
        cooked += '<p>See <a href="https://unrelated.example.com">this link</a>.</p>'
        cooked += '<pre><code>pihole allow ' + ' '.join(domains) + '</code></pre>' + extra
        return {"post_stream": {"posts": [
            {"post_number": 1, "topic_id": 212, "cooked": cooked},
            {"post_number": 2, "topic_id": 212, "cooked": '<pre>pihole allow reply.example.com</pre>'},
        ]}}

    def test_categories_duplicate_assignments_and_boundaries(self):
        domains, _, rows = extract(self.data(
            '<h1>Other</h1><h2>Banks</h2><h3>Test bank</h3>'
            '<pre><code>pihole allow clients4.google.com # shared domain</code></pre>'
            '<h2>Other service</h2><pre>pihole allow bank.example.com</pre>'))
        shared = [row for row in rows if row[4] == "clients4.google.com"]
        self.assertEqual([row[:3] for row in shared],
                         [["Google", "Maps and services", ""], ["Other", "Banks", "Test bank"]])
        self.assertTrue(any(row[:3] == ["Other", "Other service", ""] for row in rows))
        self.assertNotIn("reply.example.com", domains)
        self.assertNotIn("unrelated.example.com", domains)

    def test_shell_range_comments_and_regex_backslashes(self):
        domains, patterns, rows = extract(self.data(
            '<h2>Skype</h2><pre>pihole allow s{1..5}.symcb.com # description</pre>'
            '<pre>pihole --white-regex "(\\.|^)reddit\\.com$"\n'
            'pihole --allow-regex ^mtalk\\.google\\.com$</pre>'))
        self.assertTrue({f"s{i}.symcb.com" for i in range(1, 6)} <= domains)
        self.assertEqual(patterns, {r"(\.|^)reddit\.com$", r"^mtalk\.google\.com$"})
        self.assertTrue(all(row[5] == "metadata-only" for row in rows if row[3] == "regex"))

    def test_duplicate_summary_and_prose_wildcard(self):
        domains, _, rows = extract(self.data(
            '<h2>Allow all Google Domains listed above (summary)</h2>'
            '<pre>pihole allow fires\ntore.googleapis.com</pre>'
            '<h1>Other</h1><h2>Rumble</h2><p>Subdomains of <code>rmbl.ws</code> require a wildcard.</p>'))
        self.assertIn("*.rmbl.ws", domains)
        self.assertNotIn("tore.googleapis.com", domains)
        self.assertTrue(any(row[5] == "excluded-duplicate-summary" for row in rows))

    def test_bad_or_changed_sources_abort(self):
        for extra in ('<pre>curl https://example.com</pre>', '<pre>pihole deny example.com</pre>',
                      '<pre>pihole allow $(touch /tmp/anything)</pre>', '<pre>pihole allow https://example.com/path</pre>'):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                extract(self.data(extra))
        with self.assertRaises(ValueError):
            extract({"post_stream": {"posts": []}})

    def test_csv_preserves_headings_and_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lists/allow").mkdir(parents=True)
            update(self.data(), root=root)
            rows = list(csv.DictReader(io.StringIO((root / "metadata/pihole-forum.csv").read_text())))
            self.assertEqual(rows[0]["category"], "Google")
            self.assertEqual(rows[0]["subcategory"], "Maps and services")
            self.assertEqual(rows[0]["target"], "clients4.google.com")
