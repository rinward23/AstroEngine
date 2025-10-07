# Metrics

## Chart Integration Index

- **Integration Index (0–1):** Weighted connectivity of the natal aspect web.
- **Dense (>0.66):** Highly interlinked, fate-heavy feedback loops.
- **Balanced (0.33–0.66):** Cohesive but adaptable.
- **Loose (<0.33):** Compartmentalized, offering more freedom and less systemic reactivity.

**Inputs**

- Longitudes per body
- Orb policy
- Include/exclude minor aspects

**Outputs**

- `density_weighted`
- `largest_component_ratio`
- `exactness_mean`
- `anti_isolates`
- `tight_count`
- `edges`
- `avg_degree`
