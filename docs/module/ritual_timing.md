# Ritual Timing Module

- **Module**: `ritual`
- **Scope**: Planetary days, planetary hours, void-of-course filters, electional windows
- **Status**: Prototype – reference tables wired into registry for downstream schedulers

The ritual timing module catalogs published day/hour rulers and electional guidance so
that Solar Fire–derived event scans can be filtered for auspicious windows without
fabricating synthetic astrology. All values trace back to traditional authors (Agrippa,
Picatrix, Dorotheus, Lilly) or modern researchers documenting void-of-course usage.

## Registry layout

```
ritual/
  timing/
    planetary_days/
      day_rulers
    planetary_hours/
      hour_table
  filters/
    void_of_course/
      lunar_filters
  elections/
    windows/
      guidelines
```

### Planetary days and hours

- `timing/planetary_days/day_rulers` lists the seven weekday rulers, their ritual
  themes, and the Chaldean order source references.
- `timing/planetary_hours/hour_table` exposes a 24-hour table for each weekday derived
  from the same Chaldean sequence. The payload includes the base order so external
  engines can recompute variable seasonal hour lengths while reusing the planetary
  cadence.

### Void-of-course rules

- `filters/void_of_course/lunar_filters` stores both the classical definition (Moon void
  after last Ptolemaic aspect before sign change) and modern extensions that continue
  the void until the next applying aspect. These entries cite Lilly, Barclay, Lavoie, and
  Brady so electional scripts can quote their methodology.

### Electional windows

- `elections/windows/guidelines` documents three baseline electional windows: waxing
  Moon launches, planetary day/hour reinforcement, and Picatrix-style protection
talisman timing. Each entry includes bullet criteria and source citations to ensure
transparency when surfaced to users.

## Sources

- Heinrich Cornelius Agrippa — *Three Books of Occult Philosophy* (1533)
- *Picatrix (Ghayat al-Hakim)*
- William Lilly — *Christian Astrology* (1647)
- Olivia Barclay — *Horary Astrology Rediscovered* (1990)
- Alphee Lavoie — Void-of-course Moon research (1999)
- Bernadette Brady — *The Eagle and the Lark* (1992)
- Dorotheus of Sidon — *Carmen Astrologicum* (1st century)
- Christopher Warnock — *The Mansions of the Moon* (2010)
