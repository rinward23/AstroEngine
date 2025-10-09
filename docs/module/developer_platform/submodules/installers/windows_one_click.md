# AstroEngine Windows One-Click Installer Specification (SPEC-02)

- **Author:** ChatGPT (OpenAI Assistant)
- **Date:** 2024-05-15
- **Scope:** Developer Platform → Installers → Windows
- **Source Inputs:** `requirements/base.txt`, `requirements/dev.txt`, `alembic` migrations, `datasets/` optional Swiss Ephemeris payloads, Windows packaging standards (WiX/Inno, MSIX, Squirrel), Microsoft documentation for per-user installs, Streamlit and Uvicorn launch contracts.
- **Related Profiles/Rulesets:** `profiles/development.yaml` (env defaults), `rulesets` runtime invariants, API health contract in `docs/OBSERVABILITY_SPEC.md`.

## 1. Objectives

Deliver a telemetry-free, GUI-driven Windows setup experience that allows non-technical stakeholders to install, configure, launch, and remove AstroEngine without manual terminal usage. The installer must respect module integrity (no loss of channels/subchannels), rely exclusively on verified datasets (Solar Fire exports, Swiss Ephemeris where available), and prepare the app so every runtime response is sourced from real data.

### 1.1 MVP Reliability & Operations Enhancements

The MVP scope now locks in the following high-impact upgrades from the reliability and operations backlog:

1. **Self-Service Repair / Re-run Post-Install** – Provide a single entry point (Start Menu shortcut + `PostInstallRepair.ps1`) that recreates the virtual environment, reinstalls hashed dependencies, reapplies Alembic migrations, and reruns health probes. The workflow preserves `var/dev.db`, appends to rotating logs, and surfaces a consolidated success/failure banner.
2. **Automatic Port Conflict Resolution** – Launch orchestrators must probe 8000 (API) and 8501 (UI), selecting the next free ports in the range 8000-8010 / 8501-8511 when conflicts arise. Resolved port numbers are persisted to `.env`/`config.json`, echoed to the console, and printed in the Start Menu status page so operators know which endpoints to hit.
3. **Rotating Installer & Runtime Logs** – Ship PowerShell helpers that rotate `%LOCALAPPDATA%\AstroEngine\logs\*.log` daily with a 10 MB cap per file (3 historical archives). Add a Start Menu shortcut labeled **Open Logs Folder** that targets the log directory for quick troubleshooting.

## 2. Release Targets & Editions

| Edition | Packaging | Internet Requirement | Notes |
| --- | --- | --- | --- |
| Online bootstrapper (default) | `Setup.exe` (~<50 MB) | Requires download of Python and wheels at install time. | Minimizes distribution size; validates SHA256 for downloads and stores manifest in `%LOCALAPPDATA%\AstroEngine\installer\downloads.json`. |
| Offline bundle (optional) | `SetupOffline.exe` (~>700 MB) | None once downloaded. | Ships pinned Python 3.11.x embeddable ZIP + all wheel files from `requirements.lock/py311.txt`; integrity validated via included hashes. |

Both editions share the same MSI logic executed through a single scripted wizard (WiX Burn chain) and reuse installer scripts under `installer/`.

## 3. Installation Flow (Per-User Default)

1. **Bootstrap Wizard**
   - Display license/terms (placeholder until legal doc delivered).
   - Prompt for install scope: *Just Me* (default, `%LOCALAPPDATA%\AstroEngine`) vs *All Users* (requires elevation, configurable path).
   - Offer optional Swiss Ephemeris import: allow user to select a folder; if skipped, installer leaves placeholder instructions.
2. **Python Runtime Acquisition**
   - Online: download official Python 3.11.x embedded distribution; verify signature & checksum before extracting to `runtime\python311` inside install directory.
   - Offline: unpack bundled runtime; confirm `python.exe` present and version check `python --version` during silent validation step.
3. **Environment Construction**
   - Create `env\` virtual environment via embedded `python -m venv`.
   - Copy pinned `requirements.lock/py311.txt`; run `env\Scripts\python -m pip install --no-warn-script-location --require-hashes -r requirements.lock/py311.txt`.
   - Install dev extras flagged for runtime (Streamlit, Uvicorn, Alembic) ensuring hash compliance.
4. **Database Initialization**
   - Run `env\Scripts\python -m alembic upgrade head` targeting `%LOCALAPPDATA%\AstroEngine\var\dev.db`.
   - Capture log to `logs\install\alembic.log`; display wizard message on failure with remediation link.
5. **Configuration & Env Vars**
   - Generate `.env` with defaults from `profiles/development.yaml` (API host/port, Streamlit port, dataset paths).
   - If Swiss Ephemeris path chosen, record `SWISS_EPHEMERIS_PATH`; otherwise leave commented instructions referencing `docs/SWISS_EPHEMERIS.md`.
   - Register `%APPDATA%\AstroEngine\config.json` referencing runtime directories and logging level.
6. **Post-Install Verification**
   - Invoke `Start API` launcher silently: `env\Scripts\uvicorn app.main:app --port 8000 --host 127.0.0.1` with timeout 30s.
   - Hit `http://127.0.0.1:8000/health`; require HTTP 200 with `{"status":"ok"}`.
   - Stop API process, then mark installation successful in wizard with log summary.

### 3.1 Silent / Unattended Mode

Support `/VERYSILENT /SUPPRESSMSGBOXES` execution with optional `Mode=Online|Offline` and `Scope=PerUser|AllUsers` public properties. Silent runs inherit the same verification pipeline as interactive installs, emit progress to `%LOCALAPPDATA%\AstroEngine\logs\install\silent.log`, and exit with non-zero status when any validation fails. Documentation must include example invocations for enterprise software deployment tools (SCCM, Intune, PDQ).

## 4. Shortcut & Launcher Design

Create the following artifacts under `%APPDATA%\Microsoft\Windows\Start Menu\Programs\AstroEngine` and optional Desktop:

| Shortcut | Target | Working Dir | Notes |
| --- | --- | --- | --- |
| Start AstroEngine | `env\Scripts\python.exe installer\windows_portal_entry.py --launch both` | Install root | Script orchestrates sequential startup: API then UI, auto-selects conflict-free ports, waits for readiness, opens default browser to the resolved Streamlit URL. |
| Start API Only | `env\Scripts\python.exe installer\windows_portal_entry.py --launch api` | Install root | Creates console window; ensures idempotent start, auto-picks free port when 8000 is busy, and prints resolved port in banner/log. |
| Start UI Only | `env\Scripts\python.exe installer\windows_portal_entry.py --launch ui` | Install root | Blocks until `/health` returns OK before launching UI and honors auto-selected port from API health metadata. |
| Uninstall AstroEngine | `"%LOCALAPPDATA%\AstroEngine\uninstall.exe"` | n/a | Launches WiX Burn uninstaller with custom data preservation prompt. |
| Open Logs Folder | `explorer.exe` | n/a | Opens `%LOCALAPPDATA%\AstroEngine\logs` to expose rotating logs and diagnostic bundles. |

Desktop shortcut for **Start AstroEngine** is offered via checkbox (default on). Shortcuts default to the Python launcher icon; a branded icon can be supplied later at packaging time without changing installer logic.

## 5. Uninstall & Repair

1. **Repair** option (from Control Panel or the Start Menu **Repair AstroEngine** shortcut) runs the same script pipeline: recreate virtual environment, reinstall hashed wheels, replay Alembic migrations, reprovision `.env`/`config.json` from templates, and re-execute health probes. Failures emit actionable guidance to console and `logs\install\repair-*.log` before returning a non-zero exit code.
2. **Modify** step allows toggling Desktop shortcut and Swiss Ephemeris path (without re-downloading Python).
3. **Uninstall** flow:
   - Prompt: remove application files and optional user data (`dev.db`, logs, imported ephemeris). Default preserves data.
- Remove `%LOCALAPPDATA%\AstroEngine` runtime, `%APPDATA%\AstroEngine` config, Start Menu/Desktop shortcuts, firewall rules, and the virtual environment.
   - If user requested data purge, delete `%LOCALAPPDATA%\AstroEngine\var\dev.db` after backup prompt.

## 6. Firewall & Networking Considerations

- During installation, prompt to create Windows Defender Firewall inbound rules for TCP 8000 and 8501. Consent required; decline leaves runtime prompting user on first launch.
- Document how to update ports if conflicts occur (`config.json` + `.env`).
- Health check uses loopback only; no external telemetry or analytics are sent.

## 7. Security & Signing

- Support optional code-signing certificate (PFX) provided at build time; `make signing` pipeline injects via WiX `SignTool` custom action.
- macOS notarization and Linux signing tracked separately (`docs/module/developer_platform/submodules/installers/cross_platform.md` TBD); Windows installer must still operate unsigned but warn about SmartScreen.
- Store install logs in `%LOCALAPPDATA%\AstroEngine\logs\install` with timestamped files for troubleshooting.
- Rotate install/runtime logs daily with 10 MB caps (`astroengine_api.log`, `astroengine_ui.log`, `post_install.log`, `repair.log`). Retain three archived copies per log file and prune older entries automatically. Include rotation metadata (timestamp, size, checksum) at the top of each new log file.

## 8. Upgrade Strategy

- No in-place auto-updates. Subsequent versions ship as new Setup.exe. Installer detects existing version via registry key `HKCU\Software\AstroEngine\Installer` and offers upgrade-in-place (retains env/db). If downgrade detected, warn and block unless `/repair` flag used.
- Migration guard: before upgrade, export `requirements.lock/py311.txt` and compare hashed entries; mismatches prompt to rerun download phase.

## 9. Build & Packaging Pipeline

1. **Source Preparation**
   - Freeze dependencies via `pip-compile`. Ensure `requirements.lock/py311.txt` exists before packaging.
   - Pre-stage `installer/windows_portal_entry.py` and any optional icon assets supplied during packaging.
2. **WiX Toolset**
   - Use `Heat` to harvest installed tree structure for offline bundle skeleton.
   - Burn bootstrapper chain orchestrates: (a) install VC runtime if needed, (b) copy files, (c) run custom action for Python/venv setup, (d) execute verification.
3. **Build Steps** (CI-friendly PowerShell):
   ```powershell
   python scripts\freeze_requirements.py
   wix build installer\AstroEngine.wxs -o dist\Setup.exe
   wix burn bundle installer\Bootstrapper.wixproj
   scripts\sign_artifact.ps1 dist\Setup.exe -CertPath $env:ASTROENGINE_CERT
   ```
4. **Artifacts**
- Publish `Setup.exe`, `SetupOffline.exe`, and checksum manifest `SHA256SUMS.txt`.
- Include `INSTALLER_QUICKSTART.md` with manual install instructions and troubleshooting matrix.
- Publish `logs\diag-YYYYMMDD.zip` bundles on demand via PowerShell helper invoked from the Start Menu (collects rotating logs, health probe output, Python version, installed package hashes).

## 10. Telemetry & Privacy

- No analytics, crash reporting, or usage tracking.
- Log files contain only installer diagnostics (timestamps, step status, error stack traces). Sensitive data (paths, usernames) masked except when essential for debugging.

## 11. Validation Matrix

| Scenario | Expectation | Verification |
| --- | --- | --- |
| Fresh per-user install | Wizard completes, creates env, health check passes. | Automated QA script invoking `Setup.exe /quiet /log install.log`. |
| Upgrade existing install | Env reused, migrations reapplied, shortcuts updated. | Regression test launching both API and UI. |
| Uninstall preserve data | Runtime removed, `dev.db` remains, reinstall reuses DB. | Manual check: reinstall and confirm data retained. |
| Uninstall purge data | Database removed after confirmation. | Inspect `%LOCALAPPDATA%\AstroEngine\var` empty. |
| Firewall declined | Launchers detect blocked ports, show actionable error. | Start API with blocked ports and verify message. |
| Offline mode | Setup completes without network; hashed wheels verify. | Simulated offline VM run. |

## 12. Documentation & Support Deliverables

- Update `docs/DEV_SETUP.md` with reference to installer for Windows users.
- Author `docs/runbook/windows_installer_support.md` (future work) covering troubleshooting steps, log locations, repair instructions.
- Provide FAQ entry for Swiss Ephemeris import and dataset integrity commitments.

## 13. Open Questions

1. Preferred installer technology (WiX vs. MSIX) if stakeholders demand Windows Store distribution?
2. Source for code-signing certificate (internal CA vs. commercial) and timeline.
3. Policy for bundling GPU runtimes if future features require them.
4. Should the installer detect and migrate data from existing manual installs in `%USERPROFILE%\astroengine`?

