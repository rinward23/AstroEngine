# Offline Payload Staging

Place the Python 3.11 embedded runtime ZIP and all wheel files required for AstroEngine here when building the offline edition of the installer. The post-install script enumerates these assets dynamically:

- `python-3.11.*-embed-amd64.zip`
- Wheel files matching the hashes in `requirements.lock/py311.txt`

Files are never checked into source control; use the build pipeline to copy artifacts into this directory prior to running `iscc`.
