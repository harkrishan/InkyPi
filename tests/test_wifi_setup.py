"""Host-safe portal tests: no NetworkManager, systemd or display calls escape mocks."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('portal', ROOT / 'install/wifi-setup/inkypi-wifi-setup.py')
portal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portal)

def result(code=0, out='', err=''):
    return subprocess.CompletedProcess([], code, out, err)

class PortalTests(unittest.TestCase):
    def setUp(self):
        self.client = portal.app.test_client()
        with self.client.session_transaction() as session:
            session['csrf'] = 'test-token'

    def post(self, route, data):
        return self.client.post(route, data=dict(data, csrf='test-token'))

    def test_escaped_fields(self):
        self.assertEqual(portal.split_nmcli(r'Cafe\: WiFi:90:WPA2'), ['Cafe: WiFi', '90', 'WPA2'])
        self.assertEqual(portal.split_nmcli(r'a\\b:70:'), ['a\\b', '70', ''])

    @patch.object(portal, 'run')
    def test_csrf(self, run):
        self.assertEqual(self.client.post('/connect', data={'ssid':'test'}).status_code, 403)
        run.assert_not_called()

    @patch.object(portal, 'run')
    def test_connect_missing_network(self, run):
        self.assertEqual(self.post('/connect', {}).status_code, 400)
        run.assert_not_called()

    @patch.object(portal, 'run', return_value=result())
    def test_connect_preserves_special_names_and_password(self, run):
        response = self.post('/connect', {'ssid':' cafe:"\\ ', 'password':'a"$()\\b'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(' cafe:"\\ ', run.call_args_list[0].args[0])
        self.assertIn('a"$()\\b', run.call_args_list[0].args[0])
        self.assertEqual(run.call_args_list[1].args[0][0], 'systemd-run')
        self.assertIn('--collect', run.call_args_list[1].args[0])

    @patch.object(portal, 'run', side_effect=[result(1, err='secrets were required'), result()])
    def test_failed_connection_restores_hotspot(self, run):
        response = self.post('/connect', {'ssid':'test'})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Wrong password', response.data)
        self.assertEqual(run.call_args.args[0], ['nmcli','connection','up','inkypi-hotspot'])

    @patch.object(portal, 'run', side_effect=[result(), result(1), result()])
    def test_handoff_failure_restores_hotspot(self, run):
        self.assertEqual(self.post('/connect', {'ssid':'test'}).status_code, 500)
        self.assertEqual(run.call_args.args[0][-1], 'inkypi-hotspot')

    @patch.object(portal, 'run')
    def test_cannot_delete_hotspot(self, run):
        self.assertEqual(self.post('/delete-network', {'profile':'inkypi-hotspot'}).status_code, 400)
        run.assert_not_called()

    @patch.object(portal, 'saved_wifi_profiles', return_value=[('cafe:one','cafe', 'wlan0')])
    @patch.object(portal, 'run', side_effect=[result(out=r'cafe\:one:wlan0'), result()])
    def test_active_delete_is_delayed(self, run, profiles):
        self.assertEqual(self.post('/delete-network', {'profile':'cafe:one'}).status_code, 200)
        self.assertEqual(run.call_args.args[0][0], 'systemd-run')
        self.assertEqual(run.call_args.args[0][-1], 'cafe:one')

    @patch.object(portal, 'saved_wifi_profiles', return_value=[])
    def test_delete_unknown_profile(self, profiles):
        self.assertEqual(self.post('/delete-network', {'profile':'ethernet'}).status_code, 404)

    @patch.object(portal, 'scan_networks', return_value=[('<script>', '80', 'WPA2')])
    @patch.object(portal, 'saved_wifi_profiles', return_value=[("a');alert(1);//", '<script>', '')])
    def test_html_escape_and_static_confirmation(self, profiles, scan):
        page = self.client.get('/').data.decode()
        self.assertIn('&lt;script&gt;', page)
        self.assertIn("confirm('Delete this saved Wi-Fi network?')", page)
        self.assertIn('name="csrf"', page)

if __name__ == '__main__':
    unittest.main()
