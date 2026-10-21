# Water source review

Review date: 11 October 2026

## Decision

Use a source-priority merge because no single authoritative dataset covers
public drinking water across metropolitan Perth:

1. City of Perth drinking-fountain assets
2. National Public Toilet Map facilities explicitly marked `DrinkingWater=True`
3. Unmatched Water in Perth community records
4. Unmatched public drinking-water candidates from OpenStreetMap

Records from a lower-priority source within 50 m of a higher-priority point are
treated as the same likely facility. The higher-priority point is retained and
records the corroborating source. The 50 m threshold allows for differences
between an asset location, a toilet-building coordinate, and a community GPS
pin without collapsing distinct fountains across a larger park or precinct.

## Sources assessed

### City of Perth Street Appurtenances

- Dataset: https://catalogue.data.wa.gov.au/dataset/perth-street-appurtenances
- Publisher: City of Perth
- Licence: Creative Commons Attribution 4.0
- Drinking-fountain asset records selected: 79
- Latest selected asset edit at review: 25 June 2026
- Useful fields include stable asset ID, location description, asset type,
  bottle-filling information, dog-bowl information, coordinates, and edit date.

Only `DRINK_*` asset types are selected. Decorative water features such as
ponds, nozzles, sculptures, and fountain machinery use `WATERF` or `WATERFS`
types and are excluded.

### National Public Toilet Map

- Dataset: https://data.gov.au/data/dataset/national-public-toilet-map
- Publisher: Australian Government Department of Health, Disability and Ageing
- Licence: Creative Commons Attribution 3.0 Australia
- Perth-scope facilities explicitly marked as providing drinking water: 219

These records add broad metropolitan coverage and useful place names,
addresses, opening hours, access details, and stable facility IDs. They do not
identify whether the water hardware is a bubbler, bottle filler, or tap, so the
map classifies them generically as water points.

### Water in Perth Google My Map

- Clean community candidates: 487
- Candidates replaced by an official point within 50 m: 37
- Candidates retained after the official merge: 450

The community source remains essential outside the City of Perth because local
government drinking-fountain registers are fragmented or unavailable. Its weak
points are generic names, sparse metadata, unknown licensing, and no stated
refresh schedule. Known broken, out-of-order, and private points remain
excluded by the importer.

### OpenStreetMap

- Query: explicit `amenity=drinking_water` nodes in a Perth-region bounding box
- Elements returned at review: 796
- Public candidates retained within 100 km: 789
- Restricted records excluded: 6
- Invalid or outside-scope records excluded: 1
- Candidates matched to an existing record within 50 m: 297
- Candidates adding coverage: 492
- Licence: Open Data Commons Open Database License 1.0

Records marked `private`, `customers`, `permit`, or `no` access are excluded.
Records with no access tag are retained only when explicitly mapped as the
`drinking_water` amenity, and their popups state that public access was not
specified. Each retained record carries a direct OSM source link and licence
metadata. The map already provides OpenStreetMap attribution for its base map
and amenity data.

The Lake Claremont audit found five OSM records in the immediate lake area. Two
matched existing community records within 50 m and now corroborate them. Three
were missing and have been added. The east-side record is particularly strong:
it is explicitly marked public, free, outdoor, wheelchair accessible, suitable
for bottle filling, and was updated in July 2026.

### Other government water datasets

WA public drinking-water-source-area datasets describe protected catchments,
reservoir recharge areas, bores, and water-supply infrastructure. They do not
represent public taps or fountains and are not suitable for this map. The
data.gov.au dataset named `Drinking Fountain` covers the Gold Coast, with its
latest downloadable records dated 2015, so it is not a Perth source.

## Merge result

The reviewed merge contains 1,239 water points:

- 79 City of Perth assets
- 218 National Public Toilet Map water facilities after one City duplicate
- 450 retained community records
- 492 unmatched OpenStreetMap records

The 789 accepted OpenStreetMap candidates corroborate 297 existing points and
add 492 previously missing locations. Full match details and distances are
stored in `import-report.json`.

## Validation limits

Proximity is evidence of a likely shared facility, not proof. Large buildings,
parks, beaches, and recreation precincts may have multiple real fountains close
together. Conversely, an official facility coordinate may identify a building
or toilet block rather than the exact water outlet. The importer therefore
deduplicates only across different sources and never collapses two records from
the same source. OpenStreetMap is community maintained, and a missing access tag
is not proof that a point is unrestricted. Direct source links and provenance
are retained so questionable records can be checked individually.
