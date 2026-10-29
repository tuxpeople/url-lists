from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_docker import extract


class DockerTest(unittest.TestCase):
    def table(self, extra=""):
        hosts = ["auth.docker.io", "registry-1.docker.io"] + [f"host{i}.example.com" for i in range(8)]
        return ("# Example\nhttps://unrelated.example.com\n\n"
                "| Domains | Description |\n| --- | --- |\n" +
                "".join(f"| https://{host} | Example service |\n" for host in hosts) + extra)

    def test_extract_table_only(self):
        hosts, rows = extract(self.table("| https://*.example.org | Wildcard |\n"))
        self.assertEqual(len(hosts), 11)
        self.assertIn("*.example.org", hosts)
        self.assertNotIn("unrelated.example.com", hosts)
        self.assertEqual(rows[0], ["auth.docker.io", "https://auth.docker.io", "Example service"])

    def test_reject_incomplete_source(self):
        for text in ("", "# Layout changed", "| Domains | Description |\n| --- | --- |\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                extract(text)

    def test_reject_unsupported_rows(self):
        for url in ("http://example.com", "https://example.com/path", "https://example.com:443",
                    "https://user@example.com", "https://example.com?q=x", "not-a-domain"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                extract(self.table(f"| {url} | Unsupported |\n"))
