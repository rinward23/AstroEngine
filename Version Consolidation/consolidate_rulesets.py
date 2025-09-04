#!/usr/bin/env python3
import argparse, os, sys, json, re, hashlib, csv, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Please `pip install pyyaml` and rerun.", file=sys.stderr); sys.exit(1)

REQUIRED_MODULE_IDS = {"aspects","transits","scoring","narrative"}
TS_FMT_FILE = "%Y%m%d-%H%M"   # for filenames

def iso_to_dt(s: str):
    try:
        s = s.strip()
        if s.endswith("Z"):
            s = s[:-1]
        # try multiple formats
        fmts = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d")
        for fmt in fmts:
            try:
                return datetime.datetime.strptime(s, fmt)
            except ValueError:
                continue
    except Exception:
        pass
    return None

def load_any(path: Path):
    txt = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() in (".yaml",".yml"):
            data = yaml.safe_load(txt)
        elif path.suffix.lower() == ".json":
            data = json.loads(txt)
        else:
            return None, "Unsupported extension"
        return data, None
    except Exception as e:
        return None, f"Parse error: {e}"

def extract_header(doc: dict, src: Path):
    if not isinstance(doc, dict):
        return None, "Top-level must be a mapping"
    hdr = {
        "id": doc.get("id"),
        "name": doc.get("name"),
        "version": doc.get("version"),
        "status": doc.get("status","active"),
        "supersedes": doc.get("supersedes"),
        "source_file": str(src),
    }
    errs = []
    if not hdr["id"]:
        errs.append("Missing 'id'")
    if not hdr["version"]:
        errs.append("Missing 'version'")
    dt = iso_to_dt(hdr["version"]) if hdr["version"] else None
    if not dt:
        errs.append("Bad 'version' (expect ISO like 2025-09-03T22:41Z)")
    hdr["_version_dt"] = dt
    return (hdr if not errs else None), (", ".join(errs) if errs else None)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def main():
    ap = argparse.ArgumentParser(description="Rebuild consolidated astrology ruleset from all iterations (append-only).")
    ap.add_argument("--in", dest="in_dir", required=True, help="Folder containing ALL past iterations (yaml/json)")
    ap.add_argument("--out", dest="out_dir", default="./rulesets", help="Output folder (default ./rulesets)")
    ap.add_argument("--single", dest="emit_single", action="store_true", help="Emit combined ruleset.main.yaml")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_root = Path(args.out_dir)
    base_dir = out_root / "base"
    overrides_dir = out_root / "overrides"
    report_dir = out_root / "_reports"

    for d in (base_dir, overrides_dir, report_dir):
        ensure_dir(d)

    manifest_rows = []
    registry = {}   # id -> list of entries
    parsing_errors = []
    files = sorted([p for p in in_dir.rglob("*") if p.suffix.lower() in (".yaml",".yml",".json")])

    if not files:
        print("No YAML/JSON files found in input directory.", file=sys.stderr)
        sys.exit(2)

    for p in files:
        data, perr = load_any(p)
        if perr:
            parsing_errors.append((str(p), perr))
            continue
        hdr, herr = extract_header(data, p)
        if herr:
            parsing_errors.append((str(p), herr))
            continue
        body = data
        entry = {
            "id": hdr["id"],
            "name": hdr["name"],
            "version": hdr["version"],
            "status": hdr["status"],
            "supersedes": hdr["supersedes"],
            "_version_dt": hdr["_version_dt"],
            "source_file": hdr["source_file"],
            "body": body,
        }
        registry.setdefault(hdr["id"], []).append(entry)

    latest_by_id = {}
    lineage_by_id = {}
    for mid, entries in registry.items():
        entries = [e for e in entries if e["_version_dt"] is not None]
        entries.sort(key=lambda e: e["_version_dt"])
        if not entries:
            continue
        latest_by_id[mid] = entries[-1]
        lineage_by_id[mid] = entries

    missing_required = sorted([m for m in REQUIRED_MODULE_IDS if m not in latest_by_id])

    now = datetime.datetime.utcnow()
    ts_file = now.strftime(TS_FMT_FILE)

    manifest_path = report_dir / f"RULESET__MANIFEST_{ts_file}.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module_id","name","version","status","supersedes","source_file","is_latest"])
        for mid, entries in lineage_by_id.items():
            for e in entries:
                w.writerow([e["id"], e["name"], e["version"], e["status"], e["supersedes"], e["source_file"], "yes" if e is latest_by_id[mid] else "no"])

    val_path = report_dir / f"RULESET__VALIDATION_{ts_file}.md"
    with val_path.open("w", encoding="utf-8") as f:
        f.write("# Validation Report\n\n")
        if parsing_errors:
            f.write("## Parsing / Header Errors\n")
            for p, err in parsing_errors:
                f.write(f"- {p}: {err}\n")
            f.write("\n")
        if missing_required:
            f.write("## Missing Required Modules\n")
            for m in missing_required:
                f.write(f"- {m}\n")
            f.write("\n")
        else:
            f.write("All required modules present: aspects, transits, scoring, narrative.\n\n")

        f.write("## Module Counts\n")
        f.write(f"- Unique module ids found: {len(registry)}\n")
        f.write(f"- Latest modules selected: {len(latest_by_id)}\n")

    if missing_required:
        print(f"Missing required modules: {', '.join(missing_required)}", file=sys.stderr)
        print(f"See validation: {val_path}", file=sys.stderr)
        sys.exit(3)

    emitted_paths = []
    for mid, e in sorted(latest_by_id.items()):
        body = e["body"]
        body["id"] = e["id"]
        if e["name"] is not None:
            body["name"] = e["name"]
        body["version"] = e["version"]
        body["status"] = e["status"]
        if e["supersedes"] is not None:
            body["supersedes"] = e["supersedes"]

        tgt = overrides_dir / f"{mid}__v{ts_file}.yaml"
        with tgt.open("w", encoding="utf-8") as f:
            yaml.safe_dump(body, f, sort_keys=False, allow_unicode=True)
        emitted_paths.append(str(tgt))

    if args.emit_single:
        main_path = out_root / f"ruleset.main.yaml"
        stitched = {"modules": {}}
        for mid, e in latest_by_id.items():
            stitched["modules"][mid] = e["body"]
        with main_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(stitched, f, sort_keys=False, allow_unicode=True)

    changelog_path = report_dir / f"RULESET__CHANGELOG_{ts_file}.md"
    with changelog_path.open("w", encoding="utf-8") as f:
        f.write("# Ruleset Change Log (Consolidation)\n\n")
        f.write(f"- Consolidation time (UTC): {now.isoformat(timespec='seconds')}Z\n")
        f.write(f"- Output (overrides): {overrides_dir}\n\n")
        for mid, entries in sorted(lineage_by_id.items()):
            f.write(f"## {mid}\n")
            for e in entries:
                mark = " (latest)" if e is latest_by_id[mid] else ""
                f.write(f"- {e['version']} — {e.get('name') or ''} [{e['status']}]{mark}\n")
            f.write("\n")

    print("Consolidation complete.")
    print(f"- Manifest: {manifest_path}")
    print(f"- Validation: {val_path}")
    print(f"- Changelog: {changelog_path}")
    if args.emit_single:
        print(f"- Stitched: {out_root / 'ruleset.main.yaml'}")
    print(f"- Latest modules written to: {overrides_dir}")

if __name__ == "__main__":
    main()
