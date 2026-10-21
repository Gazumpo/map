import unittest

from scripts.extract_points import extract_osm_water, merge_water_sources


def feature(feature_id, lon, lat, source="Existing source"):
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "id": feature_id,
            "name": "Existing water point",
            "source": source,
        },
    }


class OpenStreetMapWaterTests(unittest.TestCase):
    def test_extracts_public_candidate_and_preserves_provenance(self):
        payload = {
            "elements": [
                {
                    "type": "node",
                    "id": 13514686159,
                    "lat": -31.9699836,
                    "lon": 115.7868853,
                    "timestamp": "2026-07-20T04:30:33Z",
                    "tags": {
                        "access": "yes",
                        "amenity": "drinking_water",
                        "bottle": "yes",
                        "dog": "yes",
                        "survey:date": "2026-07-19",
                    },
                }
            ]
        }

        water, stats = extract_osm_water(payload)

        self.assertEqual(len(water), 1)
        self.assertEqual(water[0]["properties"]["sourceId"], "node/13514686159")
        self.assertTrue(water[0]["properties"]["bottleFilling"])
        self.assertTrue(water[0]["properties"]["dogBowl"])
        self.assertEqual(water[0]["properties"]["lastChecked"], "2026-07-19")
        self.assertEqual(
            water[0]["properties"]["sourceUpdated"], "2026-07-20T04:30:33Z"
        )
        self.assertEqual(stats["explicitPublicAccessCount"], 1)

    def test_excludes_restricted_and_non_drinking_records(self):
        payload = {
            "elements": [
                {
                    "type": "node",
                    "id": 1,
                    "lat": -31.97,
                    "lon": 115.78,
                    "tags": {"amenity": "drinking_water", "access": "private"},
                },
                {
                    "type": "node",
                    "id": 2,
                    "lat": -31.97,
                    "lon": 115.78,
                    "tags": {"amenity": "drinking_water", "drinking_water": "no"},
                },
            ]
        }

        water, stats = extract_osm_water(payload)

        self.assertEqual(water, [])
        self.assertEqual(stats["restrictedAccessExcludedCount"], 1)
        self.assertEqual(stats["unsupportedElementCount"], 1)

    def test_nearby_osm_record_corroborates_instead_of_duplicating(self):
        existing = feature("community-1", 115.7814574, -31.9675182)
        osm = feature(
            "osm-water-node-907807825",
            115.7816523,
            -31.9672779,
            "OpenStreetMap",
        )
        osm["properties"]["sourceId"] = "node/907807825"

        merged, report = merge_water_sources([existing], [], [], [osm])

        self.assertEqual(len(merged), 1)
        self.assertEqual(
            merged[0]["properties"]["corroboratedSourceIds"],
            ["osm-water-node-907807825"],
        )
        self.assertEqual(report["openStreetMapRecordsMatchedToExistingCount"], 1)
        self.assertEqual(report["openStreetMapRecordsAddingCoverageCount"], 0)


if __name__ == "__main__":
    unittest.main()
