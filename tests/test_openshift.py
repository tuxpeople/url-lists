from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_openshift import extract, parse_table


class OpenShiftTest(unittest.TestCase):
    def test_cloud_rowspans_and_placeholders(self):
        rows = parse_table([
            "Cloud", "URL", "Port", "Function", "AWS",
            "`*.amazonaws.com` Alternatively, use the following URLs:", "443", "AWS APIs",
            "`sts.<aws_region>.amazonaws.com`", "443", "Regional STS",
            "GCP", "`accounts.google.com`", "443", "Account",
        ], "Cloud APIs", "ifndef::oci-agent[]")
        self.assertEqual([row[1] for row in rows], ["AWS", "AWS", "GCP"])
        self.assertEqual(rows[0][4:6], ["*.amazonaws.com", "included"])
        self.assertEqual(rows[1][4:6], ["", "requires-substitution"])
        self.assertEqual(rows[2][2], "ifndef::oci-agent[]")

    def test_path_and_cluster_placeholder(self):
        rows = parse_table([
            "URL", "Port", "Function",
            "`storage.googleapis.com/openshift-release`", "443", "Signatures",
            "`*.apps.<cluster_name>.<base_domain>`", "443", "Cluster routes",
        ], "Cluster access", "")
        self.assertEqual(rows[0][3:6], ["storage.googleapis.com/openshift-release", "storage.googleapis.com", "included"])
        self.assertEqual(rows[1][5], "requires-substitution")

    def test_extract_ignores_comments_and_prose(self):
        hosts = ["quay.io", "registry.redhat.io", "api.openshift.com"] + [f"host{i}.example.com" for i in range(22)]
        source = "* `prose.example.com`\n. Registry category\nifdef::oci-agent[]\n|===\n|URL | Port | Function\n"
        source += "// |`comment.example.com`\n"
        source += "".join(f"|`{host}`\n|443\n|Description\n" for host in hosts)
        source += "|===\nendif::oci-agent[]\n"
        result, rows = extract(source)
        self.assertEqual(result, set(hosts))
        self.assertTrue(all(row[0] == "Registry category" and row[2] == "ifdef::oci-agent[]" for row in rows))

    def test_reject_changed_layout(self):
        for cells in (["Address", "Port", "Function"], ["URL", "Port", "Function", "`quay.io`", "443"]):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                parse_table(cells, "", "")
        with self.assertRaises(ValueError):
            extract("No tables")
