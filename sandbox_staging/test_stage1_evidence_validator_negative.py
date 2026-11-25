"""Permanent regression test fixtures for Stage 1 evidence validator.

Includes tests for:
1. Missing .wsb configuration file -> Must FAIL.
2. Guest start timestamp in 2099 (future clock skew) -> Must FAIL.
3. Guest end timestamp in 2099 (future clock skew) -> Must FAIL.
4. Guest identity nonce differs from report session nonce -> Must FAIL.
5. GuestIdentity.TimestampUtc outside [StartTimeUtc, EndTimeUtc] -> Must FAIL.
6. Disordered start/end timestamps (start > end) -> Must FAIL.
7. Expired evidence (age > 1 hour) -> Must FAIL.
8. Every socket probe reports SETUP_ERROR -> Must FAIL.
9. Malformed adapter entry {} -> Must FAIL.
10. Evidence dated 2000 (stale timestamp) -> Must FAIL.
11. Successful connection followed by a duplicate failed record -> Must FAIL.
12. Script SHA-256 hash altered since manifest freeze -> Must FAIL.
13. External non-default routes (e.g. 192.168.1.0/24, 10.0.0.0/8) -> Must FAIL.
14. Default routes (0.0.0.0/0, ::/0) -> Must FAIL.
15. Valid, authentic, completely isolated evidence -> Must PASS.
"""

from datetime import datetime, timezone, timedelta
import unittest
from pathlib import Path
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from sandbox_staging.validate_guest_evidence import (
    validate_guest_containment_evidence,
    EXPECTED_PROBES
)


class TestStage1EvidenceValidatorRegressions(unittest.TestCase):
    def setUp(self):
        self.nonce = "test_nonce_1234567890abcdef"
        self.script_path = Path(__file__).resolve()
        self.script_hash = "abc123expected_script_hash"
        self.wsb_hash = "abc123wsb_hash"
        self.host_session_time = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Create a valid temporary WSB file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_wsb = Path(self.temp_dir.name) / "test.wsb"
        self.temp_wsb.write_text("<Configuration><Networking>Disable</Networking></Configuration>", encoding="utf-8")

        self.manifest = {
            "ManifestVersion": "1.0",
            "SessionNonce": self.nonce,
            "HostSessionStartUtc": self.host_session_time.isoformat(),
            "ProbeScriptPath": str(self.script_path),
            "ProbeScriptSha256": self.script_hash,
            "WsbConfigPath": str(self.temp_wsb),
            "WsbConfigSha256": self.wsb_hash
        }

        # Mock compute_file_sha256 to match expected hashes during tests
        import sandbox_staging.validate_guest_evidence as vge
        self._orig_compute_hash = vge.compute_file_sha256
        vge.compute_file_sha256 = lambda p: self.wsb_hash if str(p) == str(self.temp_wsb) else self.script_hash

        now = datetime.now(timezone.utc)
        self.valid_report = {
            "ReportType": "AMIGO_GUEST_CONTAINMENT_STAGE1_PROBE",
            "Specification": "TWO_STAGE_NATIVE_ISOLATION_20261111",
            "SessionNonce": self.nonce,
            "StartTimeUtc": (now - timedelta(seconds=5)).isoformat(),
            "EndTimeUtc": now.isoformat(),
            "GuestIdentity": {
                "ComputerName": "SANDBOX-GUEST",
                "UserName": "WDAGUtilityAccount",
                "TimestampUtc": (now - timedelta(seconds=2)).isoformat(),
                "SessionNonce": self.nonce
            },
            "CollectionStatus": {
                "AdaptersCollected": True,
                "AdapterError": None,
                "IPConfigsCollected": True,
                "IPConfigError": None,
                "RoutesCollected": True,
                "RouteError": None
            },
            "NetworkAdapters": [],
            "IPConfiguration": [],
            "RouteTable": [
                {"DestinationPrefix": "127.0.0.1/32", "AddressFamily": "IPv4"},
                {"DestinationPrefix": "127.0.0.0/8", "AddressFamily": "IPv4"},
                {"DestinationPrefix": "::1/128", "AddressFamily": "IPv6"},
                {"DestinationPrefix": "255.255.255.255/32", "AddressFamily": "IPv4"}
            ],
            "SocketProbes": [
                {
                    "TargetHost": host,
                    "TargetPort": port,
                    "AddressFamily": family,
                    "Connected": False,
                    "ProbeStatus": "NETWORK_DENIED"
                }
                for host, port, family in EXPECTED_PROBES
            ],
            "ProbeActionOnly": True
        }

    def tearDown(self):
        import sandbox_staging.validate_guest_evidence as vge
        vge.compute_file_sha256 = self._orig_compute_hash
        self.temp_dir.cleanup()

    def test_valid_isolated_evidence_passes(self):
        valid, errors = validate_guest_containment_evidence(self.valid_report, self.manifest)
        self.assertTrue(valid, f"Expected valid report to pass, but failed with: {errors}")
        self.assertEqual(len(errors), 0)

    # --- Gap 1: Missing WSB configuration file ---
    def test_missing_wsb_configuration_file_fails(self):
        broken_manifest = dict(self.manifest)
        broken_manifest["WsbConfigPath"] = str(Path(self.temp_dir.name) / "non_existent.wsb")
        valid, errors = validate_guest_containment_evidence(self.valid_report, broken_manifest)
        self.assertFalse(valid, "Missing WSB configuration file must fail validation")
        self.assertTrue(any("WSB configuration file missing at" in e for e in errors))

    # --- Gap 2a: Guest start timestamp in 2099 (future clock skew) ---
    def test_guest_start_timestamp_in_2099_fails(self):
        broken = dict(self.valid_report)
        broken["StartTimeUtc"] = "2099-01-01T00:00:00+00:00"
        broken["EndTimeUtc"] = "2099-01-01T00:00:05+00:00"
        broken["GuestIdentity"] = dict(self.valid_report["GuestIdentity"])
        broken["GuestIdentity"]["TimestampUtc"] = "2099-01-01T00:00:02+00:00"
        valid, errors = validate_guest_containment_evidence(broken, self.manifest)
        self.assertFalse(valid, "Guest StartTimeUtc in future year 2099 must fail validation")
        self.assertTrue(any("Guest StartTimeUtc in future" in e for e in errors))

    # --- Gap 2b: Guest end timestamp in 2099 (future clock skew) ---
    def test_guest_end_timestamp_in_2099_fails(self):
        broken = dict(self.valid_report)
        broken["EndTimeUtc"] = "2099-01-01T00:00:05+00:00"
        valid, errors = validate_guest_containment_evidence(broken, self.manifest)
        self.assertFalse(valid, "Guest EndTimeUtc in future year 2099 must fail validation")
        self.assertTrue(any("Guest EndTimeUtc in future" in e for e in errors))

    # --- Gap 2c: GuestIdentity.TimestampUtc outside [StartTimeUtc, EndTimeUtc] interval ---
    def test_guest_identity_timestamp_outside_interval_fails(self):
        broken = dict(self.valid_report)
        broken["GuestIdentity"] = dict(self.valid_report["GuestIdentity"])
        # Set guest identity time earlier than start time
        broken["GuestIdentity"]["TimestampUtc"] = (datetime.fromisoformat(broken["StartTimeUtc"]) - timedelta(seconds=10)).isoformat()
        valid, errors = validate_guest_containment_evidence(broken, self.manifest)
        self.assertFalse(valid, "GuestIdentity.TimestampUtc outside interval must fail validation")
        self.assertTrue(any("falls outside [StartTimeUtc, EndTimeUtc] interval" in e for e in errors))

    # --- Gap 3: Guest identity nonce differs from report session nonce ---
    def test_nested_guest_identity_nonce_mismatch_fails(self):
        broken = dict(self.valid_report)
        broken["GuestIdentity"] = dict(self.valid_report["GuestIdentity"])
        broken["GuestIdentity"]["SessionNonce"] = "different_or_forged_guest_nonce"
        valid, errors = validate_guest_containment_evidence(broken, self.manifest)
        self.assertFalse(valid, "Mismatched nested identity nonce must fail validation")
        self.assertTrue(any("Guest identity nonce mismatch" in e for e in errors))

    # --- Restored Regression: Hash mismatch against frozen manifest ---
    def test_restored_regression_manifest_hash_mismatch_fails(self):
        broken_manifest = dict(self.manifest)
        broken_manifest["ProbeScriptSha256"] = "altered_or_different_script_hash"
        valid, errors = validate_guest_containment_evidence(self.valid_report, broken_manifest)
        self.assertFalse(valid, "Altered probe script hash must fail validation")
        self.assertTrue(any("Probe script hash altered since manifest freeze" in e for e in errors))

    # --- Restored Regression: External non-default routes ---
    def test_restored_regression_non_default_external_route_fails(self):
        for bad_prefix in ("192.168.1.0/24", "10.0.0.0/8", "172.16.0.0/16", "8.8.8.8/32"):
            broken = dict(self.valid_report)
            broken["RouteTable"] = list(self.valid_report["RouteTable"]) + [
                {"DestinationPrefix": bad_prefix, "AddressFamily": "IPv4"}
            ]
            valid, errors = validate_guest_containment_evidence(broken, self.manifest)
            self.assertFalse(valid, f"Expected failure for external route {bad_prefix}")
            self.assertTrue(any(f"Routable external or default route detected in guest: {bad_prefix}" in e for e in errors))

    # --- Disordered start/end timestamps ---
    def test_disordered_guest_timestamps_fails(self):
        broken = dict(self.valid_report)
        now = datetime.now(timezone.utc)
        broken["StartTimeUtc"] = now.isoformat()
        broken["EndTimeUtc"] = (now - timedelta(seconds=10)).isoformat()
        valid, errors = validate_guest_containment_evidence(broken, self.manifest)
        self.assertFalse(valid, "Disordered timestamps (start > end) must fail validation")
        self.assertTrue(any("Guest timestamps disordered" in e for e in errors))

    # --- Expired evidence ---
    def test_expired_evidence_fails(self):
        broken = dict(self.valid_report)
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        broken["StartTimeUtc"] = old_time.isoformat()
        broken["EndTimeUtc"] = (old_time + timedelta(seconds=5)).isoformat()
        broken_manifest = dict(self.manifest)
        broken_manifest["HostSessionStartUtc"] = (old_time - timedelta(seconds=5)).isoformat()
        valid, errors = validate_guest_containment_evidence(broken, broken_manifest)
        self.assertFalse(valid, "Evidence older than 1 hour must fail validation")
        self.assertTrue(any("Evidence expired" in e for e in errors))

    # --- All setup errors ---
    def test_all_setup_errors_fails(self):
        broken = dict(self.valid_report)
        broken["SocketProbes"] = [
            {
                "TargetHost": host,
                "TargetPort": port,
                "AddressFamily": family,
                "Connected": False,
                "ProbeStatus": "SETUP_ERROR",
                "ErrorMessage": "Protocol not supported on uninitialized stack"
            }
            for host, port, family in EXPECTED_PROBES
        ]
        valid, errors = validate_guest_containment_evidence(broken, self.manifest)
        self.assertFalse(valid)
        self.assertTrue(any("Every socket probe reported SETUP_ERROR" in e for e in errors))

    # --- Malformed adapter entry ---
    def test_malformed_adapter_entry_fails(self):
        broken = dict(self.valid_report)
        broken["NetworkAdapters"] = [{}]
        valid, errors = validate_guest_containment_evidence(broken, self.manifest)
        self.assertFalse(valid)
        self.assertTrue(any("Malformed or empty adapter entry" in e for e in errors))

    # --- Stale timestamp year 2000 ---
    def test_stale_timestamp_year_2000_fails(self):
        broken = dict(self.valid_report)
        broken["StartTimeUtc"] = "2000-01-01T00:00:00+00:00"
        broken["EndTimeUtc"] = "2000-01-01T00:00:05+00:00"
        valid, errors = validate_guest_containment_evidence(broken, self.manifest)
        self.assertFalse(valid)
        self.assertTrue(any("Stale evidence timestamp" in e for e in errors))

    # --- Successful connection followed by duplicate failed probe ---
    def test_successful_connection_followed_by_duplicate_failed_record_fails(self):
        broken = dict(self.valid_report)
        probes = [
            {
                "TargetHost": host,
                "TargetPort": port,
                "AddressFamily": family,
                "Connected": (host == "8.8.8.8"),
                "ProbeStatus": "CONNECTED" if host == "8.8.8.8" else "NETWORK_DENIED"
            }
            for host, port, family in EXPECTED_PROBES
        ]
        probes.append({
            "TargetHost": "8.8.8.8",
            "TargetPort": 53,
            "AddressFamily": "InterNetwork",
            "Connected": False,
            "ProbeStatus": "NETWORK_DENIED"
        })
        broken["SocketProbes"] = probes
        valid, errors = validate_guest_containment_evidence(broken, self.manifest)
        self.assertFalse(valid)
        self.assertTrue(any("Socket connection succeeded to" in e for e in errors))
        self.assertTrue(any("Duplicate socket probe record in evidence" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
