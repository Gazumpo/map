import unittest
from unittest.mock import patch

from scripts.extract_psp import extract_psp_routes, load_psp_geojson, psp_query_url


def source_feature(object_id=42, road="P015", name="Kwinana Fwy PSP"):
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[115.8, -32.0], [115.9, -32.1]],
        },
        "properties": {
            "ROAD": road,
            "ROAD_NAME": name,
            "COMMON_USAGE_NAME": name,
            "NETWORK_TYPE": "Main Roads Controlled Path",
            "LG_NAME": "Perth (C)",
            "OBJECTID": object_id,
            "GlobalID": "{EXAMPLE}",
        },
    }


class PspImportTests(unittest.TestCase):
    def test_query_requests_every_controlled_path_as_geojson(self):
        url = psp_query_url(offset=1000)

        self.assertIn("Main+Roads+Controlled+Path", url)
        self.assertIn("resultOffset=1000", url)
        self.assertIn("orderByFields=OBJECTID", url)
        self.assertIn("outSR=4326", url)
        self.assertIn("f=geojson", url)

    def test_preserves_main_routes_connectors_and_stairs(self):
        payload = {
            "type": "FeatureCollection",
            "features": [
                source_feature(),
                source_feature(
                    43,
                    "P015-R003",
                    "Kwinana Freeway PSP Stairs On Canning Hwy Ramp",
                ),
            ],
        }

        routes, stats = extract_psp_routes(payload, expected_count=2)

        self.assertEqual(len(routes), 2)
        self.assertFalse(routes[0]["properties"]["isConnector"])
        self.assertTrue(routes[1]["properties"]["isConnector"])
        self.assertTrue(routes[1]["properties"]["isStairs"])
        self.assertEqual(routes[1]["properties"]["parentRouteCode"], "P015")
        self.assertEqual(stats["mainRouteCount"], 1)
        self.assertEqual(stats["stairSegmentCount"], 1)

    @patch("scripts.extract_psp.download_json")
    def test_downloads_every_paginated_feature(self, download_json):
        first_page = [source_feature(index) for index in range(1, 1001)]
        second_page = [source_feature(1001)]
        download_json.side_effect = [
            {"count": 1001},
            {"type": "FeatureCollection", "features": first_page},
            {"type": "FeatureCollection", "features": second_page},
        ]

        payload, source = load_psp_geojson(None)

        self.assertEqual(len(payload["features"]), 1001)
        self.assertEqual(source["expectedFeatureCount"], 1001)
        self.assertEqual(download_json.call_count, 3)

    def test_rejects_partial_downloads(self):
        payload = {
            "type": "FeatureCollection",
            "features": [source_feature()],
        }

        with self.assertRaisesRegex(ValueError, "1 of 2"):
            extract_psp_routes(payload, expected_count=2)

    def test_rejects_wrong_network_type(self):
        feature = source_feature()
        feature["properties"]["NETWORK_TYPE"] = "Local Road"

        with self.assertRaisesRegex(ValueError, "unexpected network type"):
            extract_psp_routes(
                {"type": "FeatureCollection", "features": [feature]}
            )


if __name__ == "__main__":
    unittest.main()
