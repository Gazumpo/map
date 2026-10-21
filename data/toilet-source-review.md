# Toilet source review

Review date: 11 October 2026

## Decision

Use the Australian Government National Public Toilet Map as the canonical
toilet source. Keep the community Google My Map toilet points only as an audit
input. Do not merge secondary datasets automatically because their records can
have different access rules, freshness, geometry, and licensing.

## Sources assessed

### National Public Toilet Map

- Publisher: Australian Government Department of Health, Disability and Ageing
- Dataset: https://data.gov.au/data/dataset/national-public-toilet-map
- Licence: Creative Commons Attribution 3.0 Australia
- Update model: a new CSV is published at the beginning of each month
- Current CSV metadata date at review: 30 September 2026
- Records in current national CSV: 25,624
- Records selected within 100 km of Perth CBD: 1,388
- Useful fields include stable facility IDs, address, opening hours,
  accessibility, transfer side, adult and baby change facilities, MLAK access,
  payment, drinking water, showers, parking, and disposal facilities.

This source has the best combination of authority, coverage, freshness, stable
identifiers, and useful attributes.

### Existing Water in Perth Google My Map

- Toilet candidates: 152
- Candidates with an official facility within 100 m: 124
- Candidates between 100 m and 500 m from an official facility: 18
- Candidates more than 500 m from an official facility: 10

The source remains valuable for finding possible omissions, especially the ten
points beyond 500 m. It is not suitable as the deployed source because names and
notes are often generic or stale, attributes are sparse, and there is no stated
refresh schedule. The full nearest-point review is in `import-report.json`.

### City of Perth Toilet Accessibility

- Catalogue: https://catalogue.data.wa.gov.au/dataset/perth-toilet-accessibility
- Licence: Creative Commons Attribution 4.0
- Records returned by the public ArcGIS layer: 126
- Records with a National Public Toilet Map facility within 100 m: 73

This is a useful independent City-centre review source. The catalogue states
that the data was last updated on 8 September 2022 and that errors or duplicates
may exist, so it was not merged into the newer national feed.

### OpenStreetMap

- Query: `amenity=toilets` within 20 km of Perth CBD through Overpass
- Elements returned: 746
- Elements with a National Public Toilet Map facility within 100 m: 383
- Licence: Open Data Commons Open Database License

OpenStreetMap is the strongest lead source for identifying possible additions.
The raw result is not a clean public-toilet facility list. It can contain both a
node and a way for one place, indoor or customer-only toilets, incomplete access
tags, and geometry centroids. A merge would also require ODbL-specific database
attribution and sharing treatment. Use it for manual review rather than an
automatic union.

## Validation method and limits

The importer compares each community toilet candidate with the nearest official
facility using haversine distance. A point within 100 m is counted as a spatial
match. Points from 100 m to 500 m are nearby review items, and points beyond 500
m are unmatched review items.

This is a coverage check, not proof that two records describe the same physical
facility. Dense precincts can contain several toilets within 100 m, while large
parks and buildings can place equivalent records more than 100 m apart. The
report therefore retains names, coordinates, official facility IDs, and
distances for human review.
