# Perth map data

The files in this directory combine imported datasets and curated location guides:

- Water points combine current City of Perth drinking-fountain assets, National
  Public Toilet Map facilities explicitly marked as having drinking water,
  unmatched records from the public **Water in Perth** Google My Map, and
  unrestricted public drinking-water candidates from OpenStreetMap.
- Toilets come from the Australian Government
  [National Public Toilet Map](https://data.gov.au/data/dataset/national-public-toilet-map),
  published under the Creative Commons Attribution 3.0 Australia licence.
- Showers combine National Public Toilet Map facilities marked as having a
  shower with public shower candidates from OpenStreetMap. Government records
  take priority when an OpenStreetMap point is within 50 m.
- Public BBQs come from current City of Perth street-appurtenance assets,
  published under the Creative Commons Attribution 4.0 licence.
- Principal Shared Paths come from the Main Roads WA Road Network, published
  under the Creative Commons Attribution 4.0 licence.
- Climbing locations come from the geolocated outdoor entries in the Perth
  region index on [theCrag](https://www.thecrag.com/en/climbing/australia/western-australia/perth).
- Surf spots are curated from Surf-Forecast, Surf Life Saving WA, Wave Explorers,
  and WannaSurf. See [surf-source-review.md](surf-source-review.md).
- Snorkelling spots are curated from DBCA, Rottnest Island Authority, local
  councils, Surf Life Saving WA, Transport WA and regional tourism resources.
  See [snorkelling-source-review.md](snorkelling-source-review.md).

- `water-points.geojson` contains merged drinking-water points with source
  provenance and cross-source corroboration.
- `toilets.geojson` contains official toilet facilities within 100 km of Perth
  CBD, including addresses, hours, accessibility, change facilities, water,
  showers, entry requirements, and links to the official listings.
- `showers.geojson` contains merged government and OpenStreetMap public shower
  points, including standalone beach showers absent from the toilet dataset.
- `adult-change.geojson` and `baby-change.geojson` are focused layers derived
  from the corresponding National Public Toilet Map attributes.
- `bbqs.geojson` contains City of Perth public BBQ assets.
- `psp-routes.geojson` contains every statewide feature classified as a Main
  Roads Controlled Path. Main PSP corridors, connectors, and stair links are
  retained so gaps are not introduced by name-based filtering.
- `climbing-locations.geojson` contains 41 outdoor climbing and bouldering
  locations, with route counts, primary styles, guide links, and the centres of
  the area bounds published by theCrag as retrieved on 12 October 2026.
- `rejected-points.geojson` keeps excluded source records and their rejection
  reasons for auditing.
- `surf-spots.geojson` contains 32 surf areas with break types, seasonal notes,
  resource links, and coordinate provenance, reviewed on 13 October 2026.
- `snorkelling-spots.geojson` contains 27 snorkelling areas with descriptions,
  seasonal and condition notes, access restrictions and resource links,
  reviewed on 13 October 2026.
- `import-report.json` records counts and the cleaning rules used.

The usable datasets are also written to `public/data/` for the website.
The rejected records and import report are not deployed.

Known broken, out-of-order, or private water points are excluded from the water
dataset. City of Perth assets have first priority, National Public Toilet Map
drinking-water records have second priority, community points have third
priority, and OpenStreetMap candidates add coverage where no existing record is
within 50 m. OpenStreetMap records marked `private`, `customers`, `permit`, or
`no` access are excluded. Records more than 100 km from Perth CBD, non-point
geometry, and exact duplicate community records are excluded.
Community toilet candidates are not deployed. They are compared with the
official facilities by nearest-point distance and the results are recorded in
`import-report.json`.

## Water source review

See [water-source-review.md](water-source-review.md) for the dated source
comparison, merge decision, counts, and validation limitations.

## Other toilet sources reviewed

See [toilet-source-review.md](toilet-source-review.md) for the dated comparison,
query counts, integration decision, and validation limitations.

## Shower source review

See [shower-source-review.md](shower-source-review.md) for the beach-shower gap
review, access exclusions, merge counts, and OpenStreetMap licensing notes.

## Principal Shared Path source review

See [psp-source-review.md](psp-source-review.md) for the source decision,
completeness checks, route counts, display rules, and limitations.

## Climbing source review

See [climbing-source-review.md](climbing-source-review.md) for the theCrag
scope, exclusions, marker classification, coordinate method, and limitations.

- The City of Perth [Toilet Accessibility](https://catalogue.data.wa.gov.au/dataset/perth-toilet-accessibility)
  layer is useful as a City-centre cross-check, but its catalogue says the data
  was last updated in 2022 and may contain errors or duplicates.
- OpenStreetMap has broad coverage and is used for explicit drinking-water and
  shower amenities. Its records retain source links and ODbL provenance, and the
  site provides OpenStreetMap attribution.

The National Public Toilet Map is the canonical toilet source because it is
maintained by the Australian Government, refreshed monthly, has stable facility
IDs, and provides substantially richer access information.

To refresh the files from the public map:

```sh
python3 scripts/extract_points.py
python3 scripts/extract_psp.py
```

The importer resolves the current monthly government CSV through the stable
data.gov.au package API, so no dated download URL is stored in the script. It
uses only the Python standard library. For an offline refresh, pass local source
files:

```sh
python3 scripts/extract_points.py source.kml \
  --toilet-csv toiletmap.csv \
  --city-water-geojson city-water.geojson \
  --city-bbq-geojson city-bbqs.geojson \
  --osm-water-json osm-water.json \
  --osm-showers-json osm-showers.json
```

The PSP importer also supports an offline source file:

```sh
python3 scripts/extract_psp.py --input road-network-psp.geojson
```
