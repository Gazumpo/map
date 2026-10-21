# Perth snorkelling source review

Reviewed 13 October 2026. This curated layer covers 27 main snorkelling areas
from Lancelin to Mandurah, with the Perth metro coast, Shoalwater, Carnac Island
and eight Wadjemup / Rottnest Island sites. It includes popular shore locations,
marked underwater trails and explicitly identified boat-access destinations.
It is a selection of established areas, not an inventory of every reef.

## Sources and scope

- DBCA's [Marmion Marine Park guide](https://exploreparks.dbca.wa.gov.au/park/marmion-marine-park)
  identifies Mettam's Pool and the MAAC Dive and Snorkel Trail. Its specific
  [Mettam's Pool](https://exploreparks.dbca.wa.gov.au/site/mettams-pool) and
  [Boyinaboat Reef](https://exploreparks.dbca.wa.gov.au/site/boyinaboat-reef)
  pages describe habitat, approximate depth and reef conditions.
- The City of Joondalup's [beach guide](https://www.joondalup.wa.gov.au/community-and-spaces/facilities%2C-venues-and-parks/beaches)
  names Burns Beach, the MAAC area and Boyinaboat as popular snorkelling spots.
  It also lists Little Island and North Lump as boat-only reefs; both are
  included with explicit boat-access notes.
- Surf Life Saving WA's [Yanchep Lagoon guide](https://www.mybeach.com.au/beaches/yanchep-lagoon/)
  describes the lagoon's permanent northern rip, an important qualification to
  its sheltered appearance.
- Destination Perth's [beach guide](https://www.destinationperth.com.au/blog/post/best-beaches-in-perth/)
  supports Lancelin's island reef snorkelling. Its
  [Sunset Coast itinerary](https://www.destinationperth.com.au/plan-your-visit/itineraries/sunset-coast-self-drive-trail/)
  supports the Watermans Bay area.
- The Town of Cottesloe's [beach page](https://www.cottesloe.wa.gov.au/community/families-youth-and-children/activities-for-youth/cottesloe-beach.aspx)
  identifies surrounding reef as snorkelling habitat. Cottesloe is represented
  as one area rather than separate markers for each reef patch.
- The City of Cockburn's [Coogee Maritime Trail guide](https://www.cockburn.wa.gov.au/Adventure-and-Leisure/Nature-and-Outdoors/Trails-and-Lookouts/Coogee-Maritime-Trail)
  supplies trail depths, shore access and wreck-care information. Omeo and the
  connected artificial reef trail are combined in one marker.
- Transport WA's [Ammo Jetty replacement page](https://transport.wa.gov.au/marine/projects-coastal-management/maritime-coastal-infrastructure-projects/new-woodman-point-ammo-jetty)
  says construction starts in October 2026 and prohibits snorkelling under and
  immediately beside the jetty during works. It identifies Sue's Groyne and
  Woodman Point Groyne as weather-dependent alternatives. The closed jetty is
  retained with a closure in its name and access notes, not presented as open.
- DBCA's [Cape Peron](https://exploreparks.dbca.wa.gov.au/site/cape-peron-rockingham-lakes),
  [Shoalwater Islands Marine Park](https://exploreparks.dbca.wa.gov.au/park/shoalwater-islands-marine-park),
  [Penguin Island](https://exploreparks.dbca.wa.gov.au/park/penguin-island-conservation-park)
  and [Carnac Island](https://exploreparks.dbca.wa.gov.au/park/carnac-island-nature-reserve)
  pages support the southern island sites and access restrictions. Penguin
  Island closes from June to October for breeding and on forecast summer days
  of 35 C or above. Check Park Alerts and ferry availability before visiting.
  Carnac beach access is prohibited November-March for fairy tern nesting;
  the water marker is not an invitation to land or approach wildlife.
- Visit Mandurah's [beach guide](https://visitmandurah.com/things-to-do/beaches-boating-and-fishing/beaches-and-surfing/)
  specifically recommends Blue Bay for snorkelling. Other nearby beaches
  described mainly for swimming or surfing are not assumed to be snorkel sites.
- Rottnest Island Authority's individual guides cover
  [The Basin](https://www.rottnestisland.com/see-do/beaches-water-activities/the-basin),
  [Little Parakeet Bay](https://www.rottnestisland.com/see-do/beaches-water-activities/little-parakeet-bay),
  [Little Armstrong Bay](https://www.rottnestisland.com/see-do/beaches-water-activities/little-armstrong-bay),
  [Rocky Bay](https://www.rottnestisland.com/see-do/beaches-water-activities/rocky-bay),
  [Salmon Bay](https://www.rottnestisland.com/see-do/beaches-water-activities/salmon-bay),
  [Little Salmon Bay trail](https://www.rottnestisland.com/see-do/beaches-water-activities/little-salmon-bay-snorkel-trail),
  [Parker Point trail](https://www.rottnestisland.com/see-do/beaches-water-activities/parker-point-snorkel-trail)
  and [Henrietta Rocks](https://www.rottnestisland.com/see-do/beaches-water-activities/henrietta-rocks).
  Its [wind-direction guide](https://www.rottnestisland.com/visit/guides-tips/best-beaches-by-wind-direction)
  supports choosing northern bays in southerlies and southern bays in northerlies.

## Coordinates

GeoJSON uses longitude, latitude. All markers represent approximate named
coastal areas, not surveyed reef positions, safe entry points or navigation
waypoints. Coordinates are deliberately rounded to three decimal places.
Mettam's Pool, Watermans, MAAC, Burns Beach, Yanchep, Cottesloe, Blue Bay and
The Basin use coastal positions near named facilities in the existing National
Public Toilet Map layer. Remaining markers are approximate positions at the
named bay, headland, groyne or island described in the linked guides. Offshore
and island markers require the transport described in their access notes;
Google Maps walking directions cannot provide an island crossing. Little Island
uses the approximate OpenStreetMap coastline location and North Lump uses a
GeoNames reef position, as published by [Mapcarta Little Island](https://mapcarta.com/16480916)
and [Mapcarta North Lump](https://mapcarta.com/16503200). Their coordinate source
links are retained in the data. These remain approximate area markers.

## Seasonal interpretation

Mainland December-April notes are an editorial inference about usual
warmer-weather comfort, not a site-specific authority guarantee of visibility
or safety. Rottnest December-May notes are general warmer-water guidance,
corroborated by the Authority's [autumn guide](https://www.rottnestisland.com/visit/weather/autumn),
which describes continued swimming and snorkelling before the colder months.
These are broad visiting windows, not months when a site is exclusively usable.
Penguin Island, Carnac beach access and Ammo Jetty use the explicit official
access restrictions instead. Each feature records its season basis.

Low swell, suitable wind direction, clear water, local restrictions and the
visitor's ability determine suitability on the day. Descriptions are original
short factual summaries; no guide text, forecast tables or photos are copied.

## Maintenance and display

Snorkelling is initially off and uses an indigo marker, toggle and count.
Hover details have an interactive guide link; click or tap opens the usual
popup with directions. Other map layers retain their existing interactions.
The importer scripts do not overwrite this hand-maintained layer. Keep
`data/snorkelling-spots.geojson` and `public/data/snorkelling-spots.geojson`
identical when updating it. Closure notes are dated research, not live status.
