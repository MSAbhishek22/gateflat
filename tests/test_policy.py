"""Policy tests — ADAPTED 9 Nov 2026 from CageCheck's test_cagecheck.py.

Only the TestPolicy cases are ported here: policy.scan is the module
this scaffold reuses. CageCheck's TestCage (runtime sandbox) and
TestReceipts (redact) cases are NOT ported — the runtime cage and the
CageCheck redact helper are not part of this project; they stay in
CageCheck, where they pass 10/10.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from policy import scan


class TestPolicy(unittest.TestCase):
    def test_ssh_read_blocked(self):
        v, rule, _ = scan("with open('/home/dev/.ssh/id_ed25519') as f:\n    x = f.read()")
        self.assertEqual(v, "BLOCKED")
        self.assertEqual(rule, "secret_path_read")

    def test_network_connect_blocked(self):
        v, rule, _ = scan("import socket\ns = socket.socket()\ns.connect(('example.com', 80))")
        self.assertEqual(v, "BLOCKED")

    def test_subprocess_blocked(self):
        v, _, _ = scan("import subprocess\nsubprocess.run(['ls'])")
        self.assertEqual(v, "BLOCKED")

    def test_policy_toggle_write_blocked(self):
        v, _, _ = scan("open('/app/policy.json', 'w').write('allow_all=True')")
        self.assertEqual(v, "BLOCKED")

    def test_clean_passes(self):
        v, rule, _ = scan("def total(p):\n    return sum(p)\n\nprint(total([10, 20, 30]))")
        self.assertEqual(v, "CLEAN")

    def test_network_import_held(self):
        v, _, _ = scan("import socket\nprint('hi')")
        self.assertEqual(v, "HELD")


if __name__ == "__main__":
    unittest.main()
