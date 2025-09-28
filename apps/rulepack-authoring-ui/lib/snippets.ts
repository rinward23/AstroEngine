export interface RuleSnippet {
  id: string;
  label: string;
  description: string;
  content: string;
}

export const RULE_SNIPPETS: RuleSnippet[] = [
  {
    id: "sun-moon-major",
    label: "Sun ↔ Moon major aspect",
    description: "Highlights a major luminary aspect for synastry interpretations.",
    content: `- id: synastry.sun_moon_major\n  scope: synastry\n  if:\n    bodies: [Sun, Moon]\n    aspect: 120\n    tags: [major]\n  then:\n    summary: >-\n      Harmonious luminary resonance fosters intuitive understanding.\n    severity: 0.7\n    tags: [growth, compatibility]\n`
  },
  {
    id: "saturn-binding",
    label: "Saturn binding lesson",
    description: "Adds a Saturnian bonding interpretation when discipline is required.",
    content: `- id: synastry.saturn_binding\n  scope: synastry\n  min_severity: 0.3\n  if:\n    bodies: [Saturn, Venus]\n    aspect: 90\n    tags: [binding]\n  then:\n    summary: >-\n      Saturn's tests demand patience; shared commitment stabilises affection.\n    severity: 0.4\n    tags: [challenge]\n`
  },
  {
    id: "composite-sun-asc",
    label: "Composite Sun on Ascendant",
    description: "Composite emphasis on visible purpose and shared direction.",
    content: `- id: composite.sun_ascendant\n  scope: composite\n  if:\n    bodies: [Sun, Ascendant]\n    aspect: 0\n  then:\n    summary: >-\n      Shared purpose shines brightly; the relationship radiates unmistakably.\n    severity: 0.6\n    tags: [major]\n`
  }
];
