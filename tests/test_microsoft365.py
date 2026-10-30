import copy
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_microsoft365 import extract, SPECIAL


class Microsoft365Test(unittest.TestCase):
    def data(self):
        result = []
        for number, area in ((1, "Exchange"), (12, "Skype"), (31, "SharePoint"), (184, "Common")):
            result.append({"id": number, "serviceArea": area, "required": number != 12,
                           "category": "Default", "urls": [f"host{i}.area{number}.example.com" for i in range(15)]})
        result[0]["urls"] += list(SPECIAL)
        result[0]["ips"] = ["192.0.2.0/24", "2001:db8::/32"]
        result[1]["urls"].append(result[0]["urls"][0])
        return result

    def test_preserves_categories_requirements_and_ips(self):
        hosts, rows, patterns = extract(self.data())
        shared = [row for row in rows if row[-2] == "host0.area1.example.com"]
        self.assertEqual({row[4] for row in shared}, {"Required", "Optional"})
        self.assertEqual({row[1] for row in shared}, {"Exchange Online", "Microsoft Teams"})
        self.assertTrue(any(row[1] == "Microsoft 365 Unified Domains" for row in rows))
        self.assertNotIn("192.0.2.0/24", hosts)
        self.assertTrue(any(row[-1] == "metadata-only" for row in rows))
        self.assertEqual(patterns, set(SPECIAL.values()))

    def test_special_patterns(self):
        tenant = SPECIAL["autodiscover.*.onmicrosoft.com"]
        self.assertIsNotNone(re.search(tenant, "autodiscover.contoso.onmicrosoft.com"))
        self.assertIsNone(re.search(tenant, "autodiscover.a.b.onmicrosoft.com"))
        suffix = SPECIAL["*cdn.onenote.net"]
        self.assertIsNotNone(re.search(suffix, "az123cdn.onenote.net"))
        self.assertIsNone(re.search(suffix, "az123cdn.onenote.net.evil"))

    def test_reject_bad_or_incomplete_data(self):
        for field, value in (("required", "false"), ("category", "NewCategory"),
                             ("serviceArea", "Unknown"), ("urls", ["https://example.com/path"]),
                             ("ips", ["invalid-network"])):
            data = copy.deepcopy(self.data())
            data[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                extract(data)
        with self.assertRaises(ValueError):
            extract(self.data()[:1])
