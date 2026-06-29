"""
Data lake integrity checker using SHA256 checksums.

Bronze layer files are immutable (raw sources) — their checksums should never change.
Silver/Gold checksums are regenerated after each pipeline run.

Usage:
    python src/utils/checksums.py generate   # create/update checksums.sha256
    python src/utils/checksums.py verify     # check integrity, exit 1 if mismatch
    python src/utils/checksums.py verify --layer bronze   # check only bronze
"""

import hashlib
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CHECKSUM_FILE = DATA_DIR / "checksums.sha256"

LAYERS = {
    "bronze":  DATA_DIR / "bronze",
    "silver":  DATA_DIR / "silver",
    "gold":    DATA_DIR / "gold",
    "exports": DATA_DIR / "exports",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files(layer: str | None = None) -> list[Path]:
    dirs = [LAYERS[layer]] if layer else list(LAYERS.values())
    files = []
    for d in dirs:
        if d.exists():
            files.extend(sorted(p for p in d.rglob("*") if p.is_file()))
    return files


def generate(layer: str | None = None):
    files = collect_files(layer)

    existing: dict[str, str] = {}
    if CHECKSUM_FILE.exists():
        for line in CHECKSUM_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            parts = line.split("  ", 1)
            if len(parts) == 2:
                existing[parts[1]] = parts[0]

    updated: dict[str, str] = dict(existing)
    new_count = changed_count = 0

    for path in files:
        rel = str(path.relative_to(DATA_DIR)).replace("\\", "/")
        digest = sha256_file(path)
        if rel not in existing:
            new_count += 1
        elif existing[rel] != digest:
            changed_count += 1
            print(f"  [UPDATED] {rel}")
        updated[rel] = digest

    lines = [
        f"# checksums.sha256 — generated {datetime.now(timezone.utc).isoformat()}",
        "# Format: sha256  relative/path/from/data/",
        "",
    ]
    for rel in sorted(updated):
        lines.append(f"{updated[rel]}  {rel}")

    CHECKSUM_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] checksums.sha256 updated — {len(updated)} files ({new_count} new, {changed_count} changed)")


def verify(layer: str | None = None) -> bool:
    if not CHECKSUM_FILE.exists():
        print("[FAIL] checksums.sha256 not found — run: python src/utils/checksums.py generate")
        return False

    recorded: dict[str, str] = {}
    for line in CHECKSUM_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        parts = line.split("  ", 1)
        if len(parts) == 2:
            recorded[parts[1]] = parts[0]

    files = collect_files(layer)
    prefix = f"{layer}/" if layer else ""

    errors = []
    ok_count = 0

    for path in files:
        rel = str(path.relative_to(DATA_DIR)).replace("\\", "/")
        if not rel.startswith(prefix):
            continue
        if rel not in recorded:
            errors.append(f"  [NEW/UNTRACKED] {rel}")
            continue
        digest = sha256_file(path)
        if digest != recorded[rel]:
            errors.append(f"  [TAMPERED]  {rel}")
        else:
            ok_count += 1

    # Files recorded but missing on disk
    for rel in recorded:
        if rel.startswith(prefix):
            if not (DATA_DIR / rel.replace("/", "\\")).exists():
                errors.append(f"  [MISSING]   {rel}")

    if errors:
        print(f"[FAIL] Integrity check failed ({len(errors)} issue(s)):")
        for e in errors:
            print(e)
        return False

    target = f"layer '{layer}'" if layer else "all layers"
    print(f"[OK] Integrity verified — {ok_count} files checked ({target})")
    return True


def main():
    parser = argparse.ArgumentParser(description="Data lake integrity tool")
    parser.add_argument("command", choices=["generate", "verify"])
    parser.add_argument("--layer", choices=list(LAYERS.keys()), default=None,
                        help="Restrict to a specific layer (default: all)")
    args = parser.parse_args()

    if args.command == "generate":
        generate(args.layer)
    elif args.command == "verify":
        ok = verify(args.layer)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
