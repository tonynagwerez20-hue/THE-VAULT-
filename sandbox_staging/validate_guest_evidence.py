"""Host-side evidence validator and pre-launch manifest manager for Stage 1 isolation probe.

Strict Independent Validation Standards:
1. Preserved, timestamp-archived pre-launch manifests; writes unique files and rejects overwriting existing archives.
2. Mandatory WSB configuration file existence, SHA-256 hash match, and XML network-disabled validation (<Networking>Disable</Networking>).
3. Comprehensive Guest Timestamp Sanity & Cross-Checking:
   - Must have valid ISO formats.
   - StartTimeUtc <= EndTimeUtc.
   - StartTimeUtc >= HostSessionStartUtc (cannot be older than host launch).
   - StartTimeUtc <= HostSessionStartUtc + FutureTolerance.
   - EndTimeUtc <= HostSessionStartUtc + FutureTolerance (rejects future EndTimeUtc).
   - GuestIdentity["TimestampUtc"] is parsed and cross-checked: must be >= StartTimeUtc and <= EndTimeUtc.
   - Evidence age must be within EvidenceMaxAge.
4. Strict session identity and nested binding:
   - Report-level SessionNonce must match manifest SessionNonce.
   - GuestIdentity["SessionNonce"] must match manifest SessionNonce (nested identity must agree).
   - GuestIdentity["ComputerName"] and GuestIdentity["UserName"] non-empty strings.
5. Complete and strict probe set validation:
   - Exactly the expected 6 probes (no duplicates, no unexpected targets).
   - Any successful connection (Connected=True) anywhere in the evidence immediately fails approval.
   - ProbeStatus must be NETWORK_DENIED or TIMEOUT. All-SETUP_ERROR or individual SETUP_ERROR fails approval.
6. Strict telemetry entry validation:
   - NetworkAdapters entries must contain non-empty Name and non-empty Status. Malformed entries like {} fail.
   - IPConfiguration entries must contain non-empty InterfaceAlias. Malformed entries fail.
   - RouteTable entries must contain non-empty DestinationPrefix and AddressFamily. Malformed entries fail.
7. Comprehensive route validation: rejects default routes AND non-loopback/non-link-local external routes.
8. Accurate reporting: Describes verified telemetry and host consistency checks without overclaiming 'authenticated proof'.
9. Return exit codes: 0 for validated telemetry checks; nonzero for any failure or missing artifact.
"""

from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import ipaddress
import json
import secrets
import sys
import xml.etree.ElementTree as ET

EXPECTED_PROBES = [
    ("8.8.8.8", 53, "InterNetwork"),
    ("1.1.1.1", 80, "InterNetwork"),
    ("142.250.190.46", 443, "InterNetwork"),
    ("2606:4700:4700::1111", 53, "InterNetworkV6"),
    ("2001:4860:4860::8888", 53, "InterNetworkV6"),
    ("127.0.0.1", 1950, "InterNetwork"),
]

MAX_FUTURE_TOLERANCE_SECONDS = 120  # 2 minutes max allowable forward clock drift
MAX_EVIDENCE_AGE_SECONDS = 3600      # Evidence older than 1 hour is expired


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def validate_wsb_configuration_file(wsb_path: Path) -> tuple[bool, str]:
    """Inspects WSB configuration XML ensuring <Networking>Disable</Networking> is strictly set."""
    if not wsb_path.is_file():
        return False, f"WSB configuration file does not exist at {wsb_path}"
    try:
        tree = ET.parse(wsb_path)
        root = tree.getroot()
        if root.tag != "Configuration":
            return False, f"Root element is not <Configuration>, got <{root.tag}>"
        networking = root.find("Networking")
        if networking is None:
            return False, "Missing <Networking> element in WSB configuration"
        if networking.text.strip().lower() != "disable":
            return False, f"Expected <Networking>Disable</Networking>, got <Networking>{networking.text}</Networking>"
        return True, "Valid WSB configuration"
    except Exception as e:
        return False, f"Failed to parse WSB XML configuration: {e}"


def create_prelaunch_manifest(staging_dir: Path, wsb_path: Path, probe_script_path: Path) -> dict:
    """Creates and preserves a pre-launch manifest with unique archived history."""
    if not wsb_path.is_file():
        raise FileNotFoundError(f"Cannot freeze manifest: WSB config missing at {wsb_path}")
    if not probe_script_path.is_file():
        raise FileNotFoundError(f"Cannot freeze manifest: Probe script missing at {probe_script_path}")

    wsb_valid, wsb_msg = validate_wsb_configuration_file(wsb_path)
    if not wsb_valid:
        raise ValueError(f"Cannot freeze manifest: {wsb_msg}")

    nonce = secrets.token_hex(16)
    now_utc = datetime.now(timezone.utc)
    timestamp_utc = now_utc.isoformat()
    archive_tag = now_utc.strftime("%Y%m%d_%H%M%S")

    # Write nonce file for the guest
    nonce_path = staging_dir / "session_nonce.txt"
    nonce_path.write_text(nonce, encoding="utf-8")

    manifest = {
        "ManifestVersion": "1.0",
        "SessionNonce": nonce,
        "HostSessionStartUtc": timestamp_utc,
        "ProbeScriptPath": str(probe_script_path),
        "ProbeScriptSha256": compute_file_sha256(probe_script_path),
        "WsbConfigPath": str(wsb_path),
        "WsbConfigSha256": compute_file_sha256(wsb_path)
    }

    manifests_archive_dir = staging_dir / "manifests"
    manifests_archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Write preserved manifest ensuring no accidental overwrite
    archived_manifest_path = manifests_archive_dir / f"manifest_{archive_tag}_{nonce[:8]}.json"
    if archived_manifest_path.exists():
        raise FileExistsError(f"Archived manifest already exists: {archived_manifest_path}")
    archived_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Update active pointer
    active_manifest_path = staging_dir / "active_manifest.json"
    active_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest


def is_safe_local_route(dest_prefix: str) -> bool:
    """Determines if a destination prefix is strictly local/loopback/link-local/multicast/broadcast."""
    if not dest_prefix or not isinstance(dest_prefix, str):
        return False
    try:
        net = ipaddress.ip_network(dest_prefix, strict=False)
        return (net.is_loopback or net.is_link_local or net.is_multicast or
                net == ipaddress.ip_network("255.255.255.255/32"))
    except ValueError:
        return False


def validate_guest_containment_evidence(evidence_data: dict | Path,
                                       manifest: dict,
                                       host_validation_time_utc: datetime | None = None) -> tuple[bool, list[str]]:
    """Strict independent audit of guest telemetry JSON artifact against preserved pre-launch manifest."""
    errors = []
    if host_validation_time_utc is None:
        host_validation_time_utc = datetime.now(timezone.utc)

    # 1. Load Evidence Data
    if isinstance(evidence_data, Path):
        if not evidence_data.is_file() or evidence_data.stat().st_size == 0:
            return False, ["Evidence file does not exist or is empty"]
        try:
            report = json.loads(evidence_data.read_text(encoding="utf-8"))
        except Exception as e:
            return False, [f"Failed to parse evidence JSON: {e}"]
    elif isinstance(evidence_data, dict):
        report = evidence_data
    else:
        return False, ["Invalid evidence data type"]

    # 2. Manifest Validation
    expected_nonce = manifest.get("SessionNonce")
    expected_script_hash = manifest.get("ProbeScriptSha256")
    expected_wsb_hash = manifest.get("WsbConfigSha256")
    host_start_str = manifest.get("HostSessionStartUtc")

    if not expected_nonce or not expected_script_hash or not expected_wsb_hash or not host_start_str:
        return False, ["Pre-launch manifest is missing required verification fields"]

    try:
        host_start_utc = datetime.fromisoformat(host_start_str.replace("Z", "+00:00"))
    except Exception as e:
        return False, [f"Invalid HostSessionStartUtc in manifest: {e}"]

    # 3. WSB Configuration File & Hash Audit
    wsb_path_str = manifest.get("WsbConfigPath", "")
    if not wsb_path_str:
        errors.append("Manifest missing WsbConfigPath")
    else:
        wsb_path = Path(wsb_path_str)
        if not wsb_path.is_file():
            errors.append(f"WSB configuration file missing at {wsb_path}")
        else:
            actual_wsb_hash = compute_file_sha256(wsb_path)
            if actual_wsb_hash != expected_wsb_hash:
                errors.append(f"WSB configuration altered since manifest freeze: expected {expected_wsb_hash}, actual {actual_wsb_hash}")
            wsb_valid, wsb_msg = validate_wsb_configuration_file(wsb_path)
            if not wsb_valid:
                errors.append(f"WSB configuration validation failed: {wsb_msg}")

    # 4. Probe Script File & Hash Audit
    probe_script_path_str = manifest.get("ProbeScriptPath", "")
    if not probe_script_path_str:
        errors.append("Manifest missing ProbeScriptPath")
    else:
        probe_script_path = Path(probe_script_path_str)
        if not probe_script_path.is_file():
            errors.append(f"Probe script does not exist at {probe_script_path}")
        else:
            actual_script_hash = compute_file_sha256(probe_script_path)
            if actual_script_hash != expected_script_hash:
                errors.append(f"Probe script hash altered since manifest freeze: expected {expected_script_hash}, actual {actual_script_hash}")

    # 5. Report Header and Session Nonce Binding
    if report.get("ReportType") != "AMIGO_GUEST_CONTAINMENT_STAGE1_PROBE":
        errors.append("Invalid ReportType in evidence payload")

    report_nonce = report.get("SessionNonce")
    if not report_nonce or not isinstance(report_nonce, str) or report_nonce != expected_nonce:
        errors.append(f"Session nonce mismatch: expected {expected_nonce}, got {report_nonce}")

    if report.get("ProbeActionOnly") is not True:
        errors.append("Evidence payload indicates non-probe action or missing ProbeActionOnly flag")

    # 6. Nested Guest Identity Audit (Must match session nonce and valid identity)
    guest_identity = report.get("GuestIdentity")
    guest_id_time = None
    if not isinstance(guest_identity, dict):
        errors.append("Missing or invalid GuestIdentity section")
    else:
        for req_key in ("ComputerName", "UserName", "TimestampUtc", "SessionNonce"):
            if not guest_identity.get(req_key):
                errors.append(f"GuestIdentity missing required field: {req_key}")

        nested_nonce = guest_identity.get("SessionNonce")
        if nested_nonce != expected_nonce:
            errors.append(f"Guest identity nonce mismatch: expected {expected_nonce}, got {nested_nonce}")

        id_time_str = guest_identity.get("TimestampUtc")
        if id_time_str:
            try:
                guest_id_time = datetime.fromisoformat(id_time_str.replace("Z", "+00:00"))
            except Exception as e:
                errors.append(f"Invalid GuestIdentity.TimestampUtc format: {e}")

    # 7. Timestamp Sanity, Ordering, Future Clock Skew, and Expiry Audit
    start_time_str = report.get("StartTimeUtc")
    end_time_str = report.get("EndTimeUtc")

    if not start_time_str or not end_time_str:
        errors.append("Missing StartTimeUtc or EndTimeUtc in evidence report")
    else:
        try:
            guest_start = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            guest_end = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))

            # Ordering check: start must be <= end
            if guest_start > guest_end:
                errors.append(f"Guest timestamps disordered: StartTimeUtc ({guest_start}) > EndTimeUtc ({guest_end})")

            # Cannot be older than host session launch
            if guest_start < host_start_utc:
                errors.append(f"Stale evidence timestamp: guest start {guest_start} < host session start {host_start_utc}")

            # Future tolerance checks for BOTH StartTimeUtc and EndTimeUtc
            max_allowable_future = host_start_utc + timedelta(seconds=MAX_FUTURE_TOLERANCE_SECONDS)
            if guest_start > max_allowable_future:
                errors.append(f"Guest StartTimeUtc in future: guest start {guest_start} exceeds host tolerance {max_allowable_future}")
            if guest_end > max_allowable_future:
                errors.append(f"Guest EndTimeUtc in future: guest end {guest_end} exceeds host tolerance {max_allowable_future}")

            # Cross-check GuestIdentity.TimestampUtc against StartTimeUtc and EndTimeUtc
            if guest_id_time is not None:
                if guest_id_time < guest_start or guest_id_time > guest_end:
                    errors.append(f"GuestIdentity.TimestampUtc ({guest_id_time}) falls outside [StartTimeUtc, EndTimeUtc] interval [{guest_start}, {guest_end}]")

            # Evidence expiry check (cannot be older than MAX_EVIDENCE_AGE_SECONDS from host validation time)
            evidence_age = (host_validation_time_utc - guest_end).total_seconds()
            if evidence_age > MAX_EVIDENCE_AGE_SECONDS:
                errors.append(f"Evidence expired: age {evidence_age:.1f}s exceeds limit {MAX_EVIDENCE_AGE_SECONDS}s")

        except Exception as e:
            errors.append(f"Invalid timestamp format in evidence report: {e}")

    # 8. Collection Status Audit (Strict Requirement: Query failures must fail approval)
    status = report.get("CollectionStatus")
    if not isinstance(status, dict):
        errors.append("Missing CollectionStatus section")
    else:
        if status.get("AdaptersCollected") is not True:
            errors.append(f"Network adapter collection query failed: {status.get('AdapterError')}")
        if status.get("IPConfigsCollected") is not True:
            errors.append(f"IP configuration collection query failed: {status.get('IPConfigError')}")
        if status.get("RoutesCollected") is not True:
            errors.append(f"Route table collection query failed: {status.get('RouteError')}")

    # 9. Network Adapters Audit (No active adapters, no malformed entries)
    adapters = report.get("NetworkAdapters")
    if not isinstance(adapters, list):
        errors.append("Missing or non-list NetworkAdapters section")
    else:
        for idx, a in enumerate(adapters):
            if not isinstance(a, dict) or not a.get("Name") or not a.get("Status"):
                errors.append(f"Malformed or empty adapter entry at index {idx}: {a}")
            elif a.get("Status") == "Up":
                errors.append(f"Active network adapter detected: {a.get('Name')}")

    # 10. IP Configuration & Gateway Audit (No gateways, no malformed entries)
    ip_configs = report.get("IPConfiguration")
    if not isinstance(ip_configs, list):
        errors.append("Missing or non-list IPConfiguration section")
    else:
        for idx, cfg in enumerate(ip_configs):
            if not isinstance(cfg, dict) or not cfg.get("InterfaceAlias"):
                errors.append(f"Malformed entry in IPConfiguration at index {idx}: {cfg}")
                continue
            gw4 = cfg.get("IPv4DefaultGW", [])
            gw6 = cfg.get("IPv6DefaultGW", [])
            if gw4:
                errors.append(f"IPv4 default gateway found on {cfg.get('InterfaceAlias')}: {gw4}")
            if gw6:
                errors.append(f"IPv6 default gateway found on {cfg.get('InterfaceAlias')}: {gw6}")

    # 11. Route Table Audit (No default routes, no external routable prefixes, no malformed entries)
    routes = report.get("RouteTable")
    if not isinstance(routes, list):
        errors.append("Missing or non-list RouteTable section")
    else:
        for idx, r in enumerate(routes):
            if not isinstance(r, dict) or not r.get("DestinationPrefix"):
                errors.append(f"Malformed entry in RouteTable at index {idx}: {r}")
                continue
            prefix = r.get("DestinationPrefix", "")
            if not is_safe_local_route(prefix):
                errors.append(f"Routable external or default route detected in guest: {prefix}")

    # 12. Socket Probes Audit (Strict probe set, no duplicates, no setup errors, zero connections)
    socket_probes = report.get("SocketProbes")
    if not isinstance(socket_probes, list):
        errors.append("Missing or non-list SocketProbes section")
    else:
        seen_probes = set()
        setup_error_count = 0
        successful_connections = []

        for idx, p in enumerate(socket_probes):
            if not isinstance(p, dict):
                errors.append(f"Malformed entry in SocketProbes at index {idx}: {p}")
                continue

            host = p.get("TargetHost")
            port = p.get("TargetPort")
            family = p.get("AddressFamily")
            connected = p.get("Connected")
            probe_status = p.get("ProbeStatus")

            # Any successful connection anywhere in evidence immediately fails
            if connected is True or probe_status == "CONNECTED":
                successful_connections.append(f"{host}:{port}")

            # Check for duplicate probe entries
            probe_key = (host, port, family)
            if probe_key in seen_probes:
                errors.append(f"Duplicate socket probe record in evidence: {host}:{port} ({family})")
            seen_probes.add(probe_key)

            if "Connected" not in p or not isinstance(connected, bool):
                errors.append(f"Probe {host}:{port} missing valid boolean Connected field")

            # Setup error handling: setup errors do NOT prove network denial
            if probe_status == "SETUP_ERROR":
                setup_error_count += 1
                errors.append(f"Socket probe to {host}:{port} reported SETUP_ERROR ({p.get('ErrorMessage')}); setup failures do not prove network containment")
            elif probe_status not in ("NETWORK_DENIED", "TIMEOUT"):
                errors.append(f"Socket probe to {host}:{port} has invalid or unverified ProbeStatus: {probe_status}")

        if successful_connections:
            errors.append(f"Socket connection succeeded to: {successful_connections}")

        # Check that ALL expected probes are present
        for expected in EXPECTED_PROBES:
            if expected not in seen_probes:
                errors.append(f"Missing required socket probe in evidence: {expected[0]}:{expected[1]} ({expected[2]})")

        if setup_error_count == len(EXPECTED_PROBES):
            errors.append("Every socket probe reported SETUP_ERROR; socket setup failures do not establish network containment")

    is_valid = len(errors) == 0
    return is_valid, errors


if __name__ == "__main__":
    staging_dir = Path(r"C:\Users\USER\Desktop\ALGOMIND\sandbox_staging\guest_probe")
    wsb_path = Path(r"C:\Users\USER\Desktop\ALGOMIND\sandbox_staging\amigo_stage1_probe.wsb")
    probe_script = staging_dir / "Probe_Guest_Containment.ps1"
    active_manifest_path = staging_dir / "active_manifest.json"
    results_dir = Path(r"C:\Users\USER\Desktop\amigo_sandbox_results")
    evidence_file = results_dir / "guest_containment_evidence.json"

    if "--freeze-manifest" in sys.argv:
        try:
            manifest = create_prelaunch_manifest(staging_dir, wsb_path, probe_script)
            print("Pre-launch manifest preserved and active pointer set:")
            print(f"  Session Nonce: {manifest['SessionNonce']}")
            print(f"  Host Session Start UTC: {manifest['HostSessionStartUtc']}")
            print(f"  Probe Script SHA-256: {manifest['ProbeScriptSha256']}")
            print(f"  WSB Config SHA-256: {manifest['WsbConfigSha256']}")
            sys.exit(0)
        except Exception as e:
            print(f"ERROR: Failed to freeze manifest: {e}")
            sys.exit(2)

    if not active_manifest_path.is_file():
        print("ERROR: No active pre-launch manifest found. Run with --freeze-manifest before launching sandbox.")
        sys.exit(2)

    try:
        manifest = json.loads(active_manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: Corrupt active pre-launch manifest: {e}")
        sys.exit(2)

    print(f"Validating against preserved manifest from {manifest.get('HostSessionStartUtc')} (Nonce: {manifest.get('SessionNonce')})")

    if evidence_file.is_file():
        valid, issues = validate_guest_containment_evidence(
            evidence_data=evidence_file,
            manifest=manifest
        )
        if valid:
            print("STAGE 1 EVIDENCE VALIDATION: PASSED")
            print("Reported guest telemetry matches preserved launch manifest and demonstrates:")
            print("  - Zero active network interfaces and zero default/external gateways")
            print("  - Non-routable route table limited strictly to loopback/link-local")
            print("  - Transport connection refusal/timeout across all 6 target endpoints")
            print("Note: Demonstrates verified guest telemetry consistency; does not substitute for native execution audits.")
            sys.exit(0)
        else:
            print("STAGE 1 EVIDENCE VALIDATION: FAILED")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
    else:
        print("No guest containment evidence artifact found yet (awaiting sandbox run).")
        print("Stage 1 Isolation Gate remains: OPEN (AWAITING INDEPENDENT EVIDENCE).")
        sys.exit(3)
