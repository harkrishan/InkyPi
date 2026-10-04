"""Exercise transition ordering with sandboxed command stubs, not host services."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'install/wifi-setup'

class ScriptTests(unittest.TestCase):
    def exercise(self, name, state='false', connected=False):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            log = d / 'calls'
            stubs = {
                'systemctl': 'echo "systemctl $*" >> "$CALLS"; exit 0',
                'python3': 'echo "$DISPLAY_STATE"',
                'sleep': ':',
                'flock': ':',
                'nmcli': '''case "$*" in
                    *GENERAL.CONNECTION*) echo Home ;;
                    *GENERAL.STATE*) echo "$NM_STATE" ;;
                    *) echo "nmcli $*" >> "$CALLS" ;;
                esac''',
            }
            for command, body in stubs.items():
                p = d / command
                p.write_text('#!/bin/bash\n' + body + '\n')
                p.chmod(0o755)
            # Redirect every writable/installed location into the temporary fixture.
            text = (ROOT / name).read_text().replace('/var/lib/inkypi-wifi', str(d / 'state')).replace('/run/inkypi-wifi-transition.lock', str(d / 'lock')).replace('/usr/local/sbin', str(d))
            script = d / name
            script.write_text(text)
            (d / 'inkypi-wifi-show-setup.sh').write_text('echo show-setup >> "$CALLS"\n') if name != 'inkypi-wifi-show-setup.sh' else None
            env = dict(os.environ, PATH=str(d)+':'+os.environ['PATH'], CALLS=str(log), DISPLAY_STATE=state, NM_STATE='100 (connected)' if connected else '30 (disconnected)')
            completed = subprocess.run(['bash', str(script)], env=env, capture_output=True, text=True)
            return completed, log.read_text().splitlines() if log.exists() else []

    def test_completed_refresh_hands_port_to_portal(self):
        result, calls = self.exercise('inkypi-wifi-show-setup.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['systemctl stop inkypi-wifi-setup.service inkypi.service', 'systemctl start inkypi.service', 'systemctl stop inkypi.service', 'systemctl start inkypi-wifi-setup.service'])

    def test_unfinished_refresh_is_not_stopped(self):
        result, calls = self.exercise('inkypi-wifi-show-setup.sh', state='true')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('systemctl stop inkypi.service', calls)
        self.assertNotIn('systemctl start inkypi-wifi-setup.service', calls)

    def test_connected_wifi_does_not_activate_hotspot(self):
        result, calls = self.exercise('inkypi-wifi-fallback.sh', connected=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])

    def test_disconnected_wifi_activates_hotspot_before_display(self):
        result, calls = self.exercise('inkypi-wifi-fallback.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['nmcli connection up id inkypi-hotspot', 'show-setup'])
