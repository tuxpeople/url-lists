import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/regex_import.sh"


class RegexImportTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.api = self.root / "api.json"
        self.write_api([])
        binary = self.root / "bin"
        binary.mkdir()
        curl = binary / "curl"
        curl.write_text("""#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import sys
args = sys.argv[1:]
name = args[-1].rsplit('/', 1)[-1]
if name == 'fail':
    sys.exit(22)
shutil.copyfile(Path(os.environ['REGEX_TEST_FIXTURES']) / name,
                args[args.index('--output') + 1])
""")
        curl.chmod(0o755)
        docker = binary / "docker"
        docker.write_text("""#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
root = Path(os.environ['REGEX_TEST_FIXTURES'])
args = sys.argv[1:]
with (root / 'docker-calls').open('a') as handle:
    handle.write(json.dumps(args) + '\\n')
if args[0] != 'exec' or args[2] != 'pihole':
    sys.exit(99)
if args[3] == 'api':
    if len(args) != 5:
        sys.exit(99)
    if (root / 'docker-fail').exists():
        sys.exit(1)
    data = json.loads((root / 'api.json').read_text()) if (root / 'drift').exists() else None
    if data is not None:
        count_file = root / 'queries'
        count = int(count_file.read_text()) + 1 if count_file.exists() else 1
        count_file.write_text(str(count))
        if count == 2:
            data['domains'][0]['comment'] = 'changed manually'
            (root / 'api.json').write_text(json.dumps(data))
    sys.stdout.write((root / 'api.json').read_text())
    sys.exit(0)
(root / 'mutation-attempted').touch()
data = json.loads((root / 'api.json').read_text())
if args[3] not in ('--allow-regex', '--regex'):
    sys.exit(99)
if (root / 'command-fail').exists():
    sys.exit(1)
if args[4] == 'remove':
    if not (root / 'remove-fail').exists():
        data['domains'] = [row for row in data['domains'] if row['domain'] not in args[5:]]
else:
    if args[4] != '--comment':
        sys.exit(99)
    additions = args[6:]
    if (root / 'partial-add').exists():
        additions = additions[:1]
    for domain in additions:
        data['domains'].append({'domain': domain, 'comment': args[5], 'enabled': True, 'groups': [0]})
(root / 'api.json').write_text(json.dumps(data))
""")
        docker.chmod(0o755)
        self.env = {**os.environ, "PATH": str(binary) + os.pathsep + os.environ["PATH"],
                    "REGEX_TEST_FIXTURES": str(self.root), "TMPDIR": str(self.root),
                    "XDG_STATE_HOME": str(self.root / "state")}

    def write_api(self, domains):
        self.api.write_text(json.dumps({"domains": domains}))

    def rule(self, domain, comment="managed by script", enabled=True, groups=None):
        return {"domain": domain, "comment": comment, "enabled": enabled,
                "groups": [0] if groups is None else groups}

    def run_script(self, *names, options=(), live=False):
        args = ["bash", str(SCRIPT), *options]
        if not live:
            args.append("--dry-run")
        for name in names:
            args += ["--url", "https://example.com/" + name]
        return subprocess.run(args, env=self.env, capture_output=True, text=True)

    def commands(self, result):
        return [shlex.split(line) for line in result.stdout.splitlines()
                if line.startswith("docker exec ")]

    def test_first_import_repeats_without_mutation(self):
        (self.root / "one").write_text("^new$\n")
        for _ in range(2):
            result = self.run_script("one")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.commands(result), [["docker", "exec", "pihole", "pihole",
                                                     "--allow-regex", "--comment", "managed by script", "^new$"]])
        calls = [json.loads(line) for line in (self.root / "docker-calls").read_text().splitlines()]
        self.assertEqual(calls, [["exec", "pihole", "pihole", "api", "domains/allow/regex"]] * 2)
        self.assertFalse((self.root / "mutation-attempted").exists())
        self.assertEqual(json.loads(self.api.read_text()), {"domains": []})
        self.assertFalse(list(self.root.glob('url-lists-regex.*')))

    def test_union_deduplication_and_missing_final_newline(self):
        self.write_api([self.rule("^keep$"), self.rule("^old$")])
        (self.root / "one").write_text("^keep$")
        (self.root / "two").write_bytes(b"^new$\r\n^keep$\r\n\n")
        result = self.run_script("one", "two")
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.commands(result)
        self.assertEqual(commands[0][-4:], ["--allow-regex", "--comment", "managed by script", "^new$"])
        self.assertEqual(commands[1][-3:], ["--allow-regex", "remove", "^old$"])

    def test_empty_list_removes_only_owned_rules(self):
        self.write_api([self.rule("^old$"), self.rule("^manual$", "zScaler PoC"),
                        self.rule("^similar$", "managed by script extra"), self.rule("^null$", None)])
        (self.root / "empty").write_text("")
        result = self.run_script("empty")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(result), [["docker", "exec", "pihole", "pihole",
                                                 "--allow-regex", "remove", "^old$"]])

    def test_existing_manual_and_disabled_rules_are_preserved(self):
        self.write_api([self.rule("^manual$", "personal", False, [2]), self.rule("^disabled$", enabled=False),
                        self.rule("^enabled$")])
        (self.root / "one").write_text("^manual$\n^disabled$\n^enabled$\n")
        result = self.run_script("one")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(result), [])
        self.assertIn("Existing unmanaged filters (left unchanged, including groups/enabled state)\n^manual$", result.stdout)
        self.assertIn("Disabled managed filters still desired (left disabled)\n^disabled$", result.stdout)

    def test_unmanaged_rules_outside_subscriptions_are_also_shown(self):
        manual = r"(\.|^)tdeutsch\.ch$"
        self.write_api([self.rule(manual, "Test")])
        (self.root / "empty").write_text("")
        result = self.run_script("empty")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Existing unmanaged filters (left unchanged, including groups/enabled state)\n" + manual,
                      result.stdout)
        self.assertEqual(self.commands(result), [])

    def test_partial_download_failure_aborts(self):
        (self.root / "one").write_text("^new$\n")
        result = self.run_script("one", "fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.commands(result), [])
        self.assertFalse((self.root / "docker-calls").exists())

    def test_invalid_download_aborts(self):
        for content in ("<html>failure</html>", "^[$", "^has space$"):
            (self.root / "bad").write_text(content)
            result = self.run_script("bad")
            self.assertNotEqual(result.returncode, 0, content)
            self.assertEqual(self.commands(result), [])

    def test_invalid_api_responses_never_propose_deletions(self):
        (self.root / "empty").write_text("")
        invalid_rule = self.rule("^bad$\n^injected$")
        responses = ["", "Status: 401\n{}", json.dumps({"error": {"message": "unauthorized"}}),
                     json.dumps({"domains": None}), json.dumps({"domains": [{"domain": "^bad$"}]}),
                     json.dumps({"domains": [invalid_rule]}),
                     json.dumps({"domains": [self.rule("^dup$"), self.rule("^dup$")]}),
                     '{"domains": []}\n{"domains": []}']
        for response in responses:
            self.api.write_text(response)
            result = self.run_script("empty")
            self.assertNotEqual(result.returncode, 0, response)
            self.assertEqual(self.commands(result), [])
            self.assertNotIn("Removed filters", result.stdout)

    def test_docker_failure_aborts(self):
        (self.root / "empty").write_text("")
        (self.root / "docker-fail").touch()
        result = self.run_script("empty")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.commands(result), [])

    def test_container_deny_type_and_marker(self):
        self.write_api([self.rule("^old$", "url-lists/deny"), self.rule("^foreign$")])
        (self.root / "one").write_text("^new$\n")
        result = self.run_script("one", options=("--type", "deny", "--container", "dns", "--comment", "url-lists/deny"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / "docker-calls").read_text()),
                         ["exec", "dns", "pihole", "api", "domains/deny/regex"])
        self.assertEqual(self.commands(result), [
            ["docker", "exec", "dns", "pihole", "--regex", "--comment", "url-lists/deny", "^new$"],
            ["docker", "exec", "dns", "pihole", "--regex", "remove", "^old$"],
        ])

    def test_command_arguments_and_batching(self):
        entries = sorted([r"^([^.]+\.)+example\.com$", r"^x;$(id)`id`$", "^it's$"] +
                         [f"^host{i}$" for i in range(202)])
        (self.root / "one").write_text("\n".join(entries) + "\n")
        result = self.run_script("one")
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.commands(result)
        self.assertEqual([len(command[7:]) for command in commands], [100, 100, 5])
        self.assertEqual([item for command in commands for item in command[7:]], entries)
        self.assertFalse((self.root / "mutation-attempted").exists())

    def test_baseline_option_is_no_longer_supported(self):
        result = self.run_script(options=("--accept-baseline",))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "docker-calls").exists())

    def test_live_default_source_sync_and_idempotence(self):
        (self.root / "allow-regex.txt").write_text("^new$\n^disabled$\n^manual$\n")
        manual = self.rule("^manual$", "personal", False, [2])
        disabled = self.rule("^disabled$", enabled=False)
        self.write_api([self.rule("^old$"), manual, disabled])
        result = self.run_script(live=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Synchronization verified successfully.", result.stdout)
        domains = json.loads(self.api.read_text())["domains"]
        self.assertEqual(sorted(domains, key=lambda row: row["domain"]),
                         sorted([self.rule("^new$"), manual, disabled], key=lambda row: row["domain"]))
        commands = self.commands(result)
        self.assertEqual(commands[0][-1], "^new$")
        self.assertEqual(commands[1][-2:], ["remove", "^old$"])
        result = self.run_script(live=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(result), [])
        self.assertFalse(list((self.root / "state/url-lists").glob('*.lock')))

    def test_partial_addition_aborts_before_any_deletion_and_can_retry(self):
        self.write_api([self.rule("^old$")])
        (self.root / "one").write_text("^new1$\n^new2$\n")
        (self.root / "partial-add").touch()
        result = self.run_script("one", live=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("partially applied", result.stderr)
        self.assertEqual({row["domain"] for row in json.loads(self.api.read_text())["domains"]},
                         {"^old$", "^new1$"})
        self.assertFalse(any("remove" in command for command in self.commands(result)))
        (self.root / "partial-add").unlink()
        result = self.run_script("one", live=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({row["domain"] for row in json.loads(self.api.read_text())["domains"]},
                         {"^new1$", "^new2$"})

    def test_failed_removal_is_detected_even_with_success_exit_code(self):
        self.write_api([self.rule("^old$")])
        (self.root / "empty").write_text("")
        (self.root / "remove-fail").touch()
        result = self.run_script("empty", live=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("differs from the plan", result.stderr)
        self.assertEqual(json.loads(self.api.read_text())["domains"], [self.rule("^old$")])

    def test_owner_changed_after_planning_is_not_deleted(self):
        self.write_api([self.rule("^old$")])
        (self.root / "empty").write_text("")
        (self.root / "drift").touch()
        result = self.run_script("empty", live=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("changed since planning", result.stderr)
        self.assertFalse((self.root / "mutation-attempted").exists())

    def test_failed_live_command_aborts_and_releases_lock(self):
        (self.root / "one").write_text("^new$\n")
        (self.root / "command-fail").touch()
        result = self.run_script("one", live=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("command failed", result.stderr)
        self.assertFalse(list((self.root / "state/url-lists").glob('*.lock')))

    def test_live_deny_defaults_to_combined_block_source(self):
        (self.root / "block-regex.txt").write_text("^deny$\n")
        result = self.run_script(options=("--type", "deny"), live=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(result)[0][4], "--regex")

    def test_live_lock_rejects_concurrent_sync(self):
        key = subprocess.check_output(["cksum"], input=b"pihole/allow").decode().split()[0]
        lock = self.root / "state/url-lists" / f"regex-sync-{key}.lock"
        lock.mkdir(parents=True)
        result = self.run_script(live=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Another sync holds the lock", result.stderr)
        self.assertTrue(lock.is_dir())
        self.assertFalse((self.root / "docker-calls").exists())
