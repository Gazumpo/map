# Shower source review

Review date: 11 October 2026

## Decision

Combine Australian Government National Public Toilet Map records explicitly
marked as having a shower with public shower candidates from OpenStreetMap.
The government record is retained when an OpenStreetMap point is within 50 m.
Unmatched OpenStreetMap records are added because the government source is
facility-focused and omits many standalone outdoor showers along beaches.

## Sources assessed

### National Public Toilet Map

- Publisher: Australian Government Department of Health, Disability and Ageing
- Licence: Creative Commons Attribution 3.0 Australia
- Shower facilities selected within 100 km of Perth CBD: 152
- Strengths: stable facility IDs, names, addresses, opening hours, access notes,
  and other toilet attributes
- Limitation: showers are recorded only as attributes of toilet facilities, so
  standalone beach shower fixtures are not comprehensively represented

### OpenStreetMap

- Query: explicit `amenity=shower` records in a Perth-region bounding box
- Elements returned at review: 154
- Public candidates retained within 100 km: 146
- Restricted records excluded: 7
- Unsupported shower-tagged features excluded: 0
- Invalid or outside-scope records excluded: 1
- Licence: Open Data Commons Open Database License 1.0

Records marked `private`, `customers`, `permit`, or `no` access are excluded.
Records with no access tag are retained only when they are explicitly mapped as
a shower amenity. Their popups state that public access was not specified in
the source data.

### Other public data

The WA public-data catalogue and relevant Perth local-government results were
reviewed for a current metropolitan or statewide beach-shower asset dataset.
No authoritative dataset dedicated to beach showers was found. The Perth
Coastal Recreation Use Study includes older infrastructure snapshots from 2018
and has no supplied reusable licence, so it was not merged. Council web pages
and park finders can mention showers, but no consistent metropolitan export was
available for automated refresh.

## Merge result

The merged layer contains 264 shower locations:

- 152 National Public Toilet Map shower facilities
- 34 OpenStreetMap candidates matched to a government record within 50 m
- 112 unmatched OpenStreetMap candidates adding coverage

Many of the added records form clear sequences along the metropolitan coast,
including Rottnest Island and beaches from the northern suburbs through
Mandurah. This materially improves beach-shower coverage over the government
facility source alone.

## Validation limits

OpenStreetMap is community maintained. A missing access tag is not proof that a
shower is unrestricted, and individual beach shower heads may be mapped as
separate nearby points. Proximity matching is evidence of the same facility,
not proof. The generated layer therefore retains source links and provenance so
questionable points can be checked individually.
