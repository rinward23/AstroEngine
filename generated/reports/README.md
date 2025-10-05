# Generated PDF Artifacts

The ``scripts/generate_sample_pdf.py`` helper writes chart reports into
this directory. Binary ``*.pdf`` files are ignored by version control so
developers can regenerate them locally without polluting the history.

To reproduce the sample report referenced in documentation run:

```bash
pip install -e .[reports]
pip install pyswisseph
python scripts/generate_sample_pdf.py
```

The script uses the same natal chart pipeline as the REST endpoint,
ensuring every value in the PDF comes from the ephemeris data shipped
with AstroEngine. If ``pyswisseph`` is missing the helper exits with a
clear message so contributors know to install the Swiss ephemeris
bindings before re-running it.
