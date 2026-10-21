# Principal Shared Path source review

Reviewed 12 October 2026.

## Decision

The canonical source is the Main Roads Western Australia Road Network dataset,
published as open data under Creative Commons Attribution 4.0. Its ArcGIS Road
Network layer explicitly distinguishes `Main Roads Controlled Path` line
features from state roads, local roads, miscellaneous roads, and crossovers.

The importer retains every feature returned by that classification. It does not
filter by route name or geographic boundary. This avoids excluding connectors,
southern routes, and newly added route codes. A separate count request is
compared with the paginated download before files are written.

At review time the source returned:

- 987 line segments
- 20 parent route codes
- 415 connector segments
- 34 segments identified by Main Roads names as stairs or steps
- 32 local-government areas

All 987 records had a route code, route name, unique numeric object ID, and
valid `LineString` geometry. The source extent ran from approximately 31.56°S
to 33.40°S and 115.64°E to 116.03°E.

## Presentation rules

Main routes and connectors are both displayed. Connectors use a thinner line.
Named stairs and steps remain in the dataset, use a dashed grey line, and are
identified as not rideable in the popup. The PSP selector count represents the
20 parent routes rather than the 987 underlying geometry segments.

## Limitations

This layer represents paths controlled by Main Roads WA. It should not be
described as every shared path or every piece of cycling infrastructure in
Western Australia. Locally controlled shared paths can be absent, and changes
on the ground can precede updates to the source database.

The Transport WA Long-Term Cycle Network was reviewed but not merged. It is an
aspirational hierarchy of primary, secondary, and local routes rather than an
inventory of completed PSP infrastructure. OpenStreetMap was also not merged
because it does not provide the same authoritative and consistent PSP
classification.

## Sources

- [Main Roads WA Road Network](https://catalogue.data.wa.gov.au/dataset/mrwa-road-network)
- [Main Roads ArcGIS Road Network layer](https://gisservices.mainroads.wa.gov.au/arcgis/rest/services/OpenData/RoadAssets_DataPortal/MapServer/17)
- [Transport WA PSP Expansion Program](https://transport.wa.gov.au/active-transport/programs-initiatives/principal-shared-path-expansion-program)
- [Transport WA Long-Term Cycle Network](https://catalogue.data.wa.gov.au/dataset/long-term-cycle-network-ltcn-dot-035)
