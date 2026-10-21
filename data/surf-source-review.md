# Perth surf source review

Reviewed 13 October 2026. The curated layer covers 32 established surf areas
from Lancelin and Ledge Point through the metro coast to Mandurah and Tims
Thicket, plus four Rottnest breaks. It covers board surfing, including breaks
used for longboarding and bodyboarding. It is a selection of main public
spots, not an inventory of every unnamed bank or offshore reef.

## Sources

- [Surf-Forecast regional index](https://www.surf-forecast.com/countries/Australia/breaks)
  and individual spot guides provide break classifications, approximate area
  coordinates and seasonal guidance for 27 locations. Each record links to its
  guide rather than a search page.
- [Surf Life Saving WA Brighton guide](https://www.mybeach.com.au/beaches/brighton-beach/)
  identifies Brighton as a surf beach with better winter surf.
- [Surf Life Saving WA Pyramids guide](https://www.mybeach.com.au/beaches/pyramids-beach/)
  describes beach breaks and the southern reef.
- [Wave Explorers Cottesloe guide](https://waveexplorers.com/guide/australia/perth/surfing-cottesloe/)
  identifies the Cove, Seconds and Isolators and their reef-wave styles.
- [WannaSurf Tims Thicket entry](https://www.wannasurf.com/spot/Australia_Pacific/Australia/WA/Perth_South/tims_thicket/)
  supplies an approximate GPS location and a spot resource.
- [Rottnest Island Authority surfing guide](https://www.rottnestisland.com/see-do/beaches-water-activities/surfing)
  corroborates the island's reef surfing and winter swell season.
- [Visit Mandurah](https://visitmandurah.com/things-to-do/beaches-boating-and-fishing/beaches-and-surfing/)
  corroborates Avalon and Pyramids as main surf destinations.

## Coordinates and scope

GeoJSON coordinates are longitude, latitude. Markers represent approximate
surf areas, not exact take-off positions or entry routes. Most coordinates
come from Surf-Forecast, which rounds them to two decimal places. Trigg,
Floreat, Brighton and Pyramids use coastal positions near named facilities in
the existing National Public Toilet Map dataset where the surf guide's
rounded location is misleading. Cove and Isolators use approximate positions
south of the Cottesloe groyne as described in the area guide. Chicken Reef and
Salmon Point are separated slightly within their shared rounded source area
so both markers remain clickable. Each feature records its coordinate source.

The Surf layer is off initially and has its own teal marker style, count and
toggle. Existing importer scripts do not overwrite this hand-maintained
dataset. Keep `data/surf-spots.geojson` and `public/data/surf-spots.geojson`
identical when making updates.

## Seasonal interpretation

Season means the usual useful swell period, not a patrol season or a live
forecast. Southern hemisphere seasons apply. Autumn/winter notes broaden
individual autumn peak statistics to include the regional winter swell
period. Some Surf-Forecast statistical headings conflict with their own prose
(notably Avalon and Cozies/Geeries) or contain no season. Those records use
broader regional guidance instead of repeating inconsistent peak months.
Pyramids, Tims Thicket, Cove/Seconds and Isolators also use an inferred regional
autumn/winter swell season. Small summer waves can still be useful for lessons.

Only short factual classifications and original seasonal summaries are
stored, with links to the original resources. No source descriptions or
forecast tables are copied. Swell, wind, tide and changing sandbanks determine
conditions on the day.
