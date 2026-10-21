# Map

Mapping useful stuff.

A phone-first map of public water points, toilets, showers, change facilities,
public BBQs, climbing and bouldering locations, surf and snorkelling spots, and Principal Shared Paths
around Perth. The website
uses plain HTML, CSS, JavaScript, Leaflet, and static GeoJSON files. It has no
frontend framework, application server, database, or build step.

The map type control switches between OpenStreetMap street tiles and Esri
satellite or topographic tiles. The most recently selected map type is saved in
the browser and restored on the next visit.

## Local preview

Build the combined Pickled Onion site without deploying it:

```sh
cd /Users/graeme/Projects
SKIP_DEPLOY=1 ./build-pickledonion-dev.sh site
python3 -m http.server 8000 --directory pickledonion.dev
```

Then open `http://localhost:8000/map/`.

## Refresh the map data

```sh
python3 scripts/extract_points.py
python3 scripts/extract_psp.py
```

The importer downloads the community water-source KML, current City of Perth
drinking-fountain and public-BBQ assets, the current Australian Government
National Public Toilet Map CSV, and public drinking-water and shower candidates
from OpenStreetMap. It excludes restricted OpenStreetMap records, merges water
and shower sources by authority and proximity, validates the community toilet
candidates against the official data, derives adult-change and baby-change
layers, updates the audit files in `data/`, and writes the deployable datasets
to `public/data/`.

The PSP importer downloads every feature classified as `Main Roads Controlled
Path` in the official Main Roads WA Road Network. It verifies the service count,
paginates deterministically, validates every line and source ID, and retains
main routes, connectors, and stair links. The data is published under CC BY 4.0.

`data/climbing-locations.geojson` contains the geolocated outdoor entries from
the Perth region index on theCrag. Each point includes its current route count,
primary climbing type, and a link to the corresponding guide. Bouldering-primary
locations and other climbing locations are displayed as separate map layers.

`data/surf-spots.geojson` contains 32 main surf areas from Lancelin to Tims
Thicket, including the Perth metro coast and Rottnest. The Surf layer can be
enabled in the map items menu. Popups show the name, break type, season, and a
link to the spot's guide or area information. See `data/surf-source-review.md`
for sources, approximate coordinate methods, and seasonal limitations.

`data/snorkelling-spots.geojson` contains 27 main snorkelling areas from
Lancelin to Mandurah, including the Perth coast, Shoalwater, Carnac and eight
Rottnest sites. Enable Snorkelling in the map items menu. Hover over a marker
for area information, seasonal guidance, access notes and a resource link;
tap or click for the same details plus directions. Ammo Jetty's construction
closure and Penguin Island's seasonal access restrictions are included.
See `data/snorkelling-source-review.md` for sources and coordinate limitations.

## Deploy

Map is mounted at `/map` inside the main Pickled Onion static bundle. Deploy
it through the workspace's canonical deployment wrapper:

```sh
cd /Users/graeme/Projects/.agents/skills/deploy-pickledonion
bash scripts/deploy.sh pickledonion
```
