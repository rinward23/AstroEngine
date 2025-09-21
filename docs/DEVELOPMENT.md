# >>> AUTO-GEN BEGIN: dev policy v1.0
## Generated-Only Mode
- Truth lives in `/registry` YAMLs. Ask Codex to edit those.
- Code lives under `/generated` and must be wrapped in named, versioned **AUTO-GEN** fences.
- Public exports go in `generated/astroengine/__init__.py` via ENSURE-LINE.
- CI blocks fence mistakes and duplicate IDs.
- Legacy `/src` is ignored by packaging; migrate gradually if present.
# >>> AUTO-GEN END: dev policy v1.0
