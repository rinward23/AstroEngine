# >>> AUTO-GEN BEGIN: validate fences v1.0
from __future__ import annotations
import re, sys, pathlib
COMMENT_PREFIX = r"(?:#|//|<!--)?"
BEGIN = re.compile(rf"^{COMMENT_PREFIX}\s*>>> AUTO-GEN BEGIN: (.+) v(\d+\.\d+).*$")
END = re.compile(rf"^{COMMENT_PREFIX}\s*>>> AUTO-GEN END: (.+) v(\d+\.\d+).*$")
errors = []
for p in pathlib.Path(".").rglob("*.*"):
    if p.suffix in {".py", ".md", ".yml", ".yaml", ".json", ".toml", ".txt"}:
        lines = p.read_text(errors="ignore").splitlines()
        stack, names = [], {}
        for i, line in enumerate(lines, 1):
            mb, me = BEGIN.match(line), END.match(line)
            if mb:
                name, ver = mb.group(1), mb.group(2)
                if name in names and names[name] != ver:
                    prev = names[name]
                    if tuple(map(float, ver.split('.'))) < tuple(map(float, prev.split('.'))):
                        errors.append(f"{p}:{i} version decrease for block '{name}' {ver} < {prev}")
                names[name] = ver
                stack.append((name, ver, i))
            elif me:
                if not stack:
                    errors.append(f"{p}:{i} stray AUTO-GEN END without BEGIN")
                else:
                    name, ver, bi = stack.pop()
                    if (me.group(1), me.group(2)) != (name, ver):
                        errors.append(f"{p}:{i} mismatched END for '{name} v{ver}'")
        if stack:
            errors.append(f"{p}: unclosed AUTO-GEN block starting line {stack[-1][2]}")
if errors:
    sys.stderr.write("\n".join(errors)+"\n"); sys.exit(2)
# >>> AUTO-GEN END: validate fences v1.0
