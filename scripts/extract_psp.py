#!/usr/bin/env python3
"""Build the official Main Roads controlled-path GeoJSON layer."""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PSP_SOURCE_NAME = "Main Roads Western Australia Road Network"
PSP_DATASET_URL = "https://catalogue.data.wa.gov.au/dataset/mrwa-road-network"
PSP_SERVICE_URL = (
    "https://gisservices.mainroads.wa.gov.au/arcgis/rest/services/"
    "OpenData/RoadAssets_DataPortal/MapServer/17"
)
PSP_LICENCE = "Creative Commons Attribution 4.0"
PSP_NETWORK_TYPE = "Main Roads Controlled Path"
PSP_PAGE_SIZE = 1000
PSP_FIELDS = (
    "ROAD",
    "ROAD_NAME",
    "COMMON_USAGE_NAME",
    "NETWORK_TYPE",
    "LG_NAME",
    "OBJECTID",
    "GlobalID",
)
STAIR_RE = re.compile(r"\b(stairs?|steps?)\b", re.I)


def download_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PerthWaterMapPSPImporter/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def psp_query_url(*, offset: int, page_size: int = PSP_PAGE_SIZE) -> str:
    query = urllib.parse.urlencode(
        {
            "where": f"NETWORK_TYPE='{PSP_NETWORK_TYPE}'",
            "outFields": ",".join(PSP_FIELDS),
            "returnGeometry": "true",
            "outSR": "4326",
            "orderByFields": "OBJECTID",
            "resultOffset": str(offset),
            "resultRecordCount": str(page_size),
            "f": "geojson",
        }
    )
    return f"{PSP_SERVICE_URL}/query?{query}"


def psp_count_url() -> str:
    query = urllib.parse.urlencode(
        {
            "where": f"NETWORK_TYPE='{PSP_NETWORK_TYPE}'",
            "returnCountOnly": "true",
            "f": "json",
        }
    )
    return f"{PSP_SERVICE_URL}/query?{query}"


def load_psp_geojson(input_path: Path | None) -> tuple[dict, dict]:
    if input_path:
        payload = json.loads(input_path.read_text())
        return payload, {
            "datasetUrl": PSP_DATASET_URL,
            "serviceUrl": PSP_SERVICE_URL,
            "localInput": str(input_path),
            "expectedFeatureCount": len(payload.get("features", [])),
        }

    count_payload = download_json(psp_count_url())
    expected_count = count_payload.get("count")
    if not isinstance(expected_count, int) or expected_count <= 0:
        raise ValueError("The Main Roads PSP count request returned no valid count")

    features: list[dict] = []
    for offset in range(0, expected_count, PSP_PAGE_SIZE):
        page = download_json(psp_query_url(offset=offset))
        if page.get("type") != "FeatureCollection":
            error = page.get("error", {}).get("message", "invalid GeoJSON response")
            raise ValueError(f"The Main Roads PSP request failed: {error}")
        page_features = page.get("features")
        if not isinstance(page_features, list) or not page_features:
            raise ValueError(
                f"The Main Roads PSP request returned an empty page at offset {offset}"
            )
        features.extend(page_features)

    if len(features) != expected_count:
        raise ValueError(
            "The Main Roads PSP download was incomplete: "
            f"expected {expected_count} features, received {len(features)}"
        )

    return {"type": "FeatureCollection", "features": features}, {
        "datasetUrl": PSP_DATASET_URL,
        "serviceUrl": PSP_SERVICE_URL,
        "expectedFeatureCount": expected_count,
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
    }


def validate_line_coordinates(coordinates: object, object_id: int) -> None:
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        raise ValueError(f"PSP feature {object_id} has an empty or one-point line")
    for coordinate in coordinates:
        if not isinstance(coordinate, list) or len(coordinate) < 2:
            raise ValueError(f"PSP feature {object_id} has an invalid coordinate")
        lon, lat = coordinate[:2]
        if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
            raise ValueError(f"PSP feature {object_id} has a non-numeric coordinate")
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError(f"PSP feature {object_id} has an out-of-range coordinate")


def extract_psp_routes(
    payload: dict, expected_count: int | None = None
) -> tuple[list[dict], dict]:
    if payload.get("type") != "FeatureCollection":
        raise ValueError("The PSP source is not a GeoJSON FeatureCollection")
    source_features = payload.get("features")
    if not isinstance(source_features, list) or not source_features:
        raise ValueError("The PSP source contains no features")
    if expected_count is not None and len(source_features) != expected_count:
        raise ValueError(
            f"The PSP source contains {len(source_features)} of {expected_count} features"
        )

    routes: list[dict] = []
    object_ids: set[int] = set()
    main_route_codes: set[str] = set()
    councils: set[str] = set()
    connector_count = 0
    stair_count = 0

    for source in source_features:
        properties = source.get("properties") or {}
        geometry = source.get("geometry") or {}
        object_id = properties.get("OBJECTID")
        route_code = str(properties.get("ROAD") or "").strip()
        name = str(properties.get("ROAD_NAME") or "").strip()
        network_type = properties.get("NETWORK_TYPE")

        if not isinstance(object_id, int):
            raise ValueError("A PSP feature is missing its numeric OBJECTID")
        if object_id in object_ids:
            raise ValueError(f"The PSP source contains duplicate OBJECTID {object_id}")
        object_ids.add(object_id)
        if not route_code or not name:
            raise ValueError(f"PSP feature {object_id} is missing its route code or name")
        if network_type != PSP_NETWORK_TYPE:
            raise ValueError(
                f"PSP feature {object_id} has unexpected network type {network_type!r}"
            )
        if geometry.get("type") != "LineString":
            raise ValueError(f"PSP feature {object_id} is not a LineString")
        validate_line_coordinates(geometry.get("coordinates"), object_id)

        is_connector = "-R" in route_code
        is_stairs = bool(STAIR_RE.search(name))
        parent_route_code = route_code.split("-R", 1)[0]
        main_route_codes.add(parent_route_code)
        connector_count += int(is_connector)
        stair_count += int(is_stairs)
        council = str(properties.get("LG_NAME") or "").strip()
        if council:
            councils.add(council)

        routes.append(
            {
                "type": "Feature",
                "id": f"psp-{object_id}",
                "geometry": geometry,
                "properties": {
                    "id": f"psp-{object_id}",
                    "name": name,
                    "category": "psp",
                    "routeCode": route_code,
                    "parentRouteCode": parent_route_code,
                    "commonName": str(
                        properties.get("COMMON_USAGE_NAME") or ""
                    ).strip(),
                    "council": council,
                    "isConnector": is_connector,
                    "isStairs": is_stairs,
                    "sourceObjectId": object_id,
                    "sourceGlobalId": str(properties.get("GlobalID") or "").strip(),
                    "source": PSP_SOURCE_NAME,
                    "sourceUrl": PSP_DATASET_URL,
                    "licence": PSP_LICENCE,
                },
            }
        )

    routes.sort(key=lambda feature: feature["properties"]["sourceObjectId"])
    return routes, {
        "recordCount": len(routes),
        "mainRouteCount": len(main_route_codes),
        "mainRouteCodes": sorted(main_route_codes),
        "connectorSegmentCount": connector_count,
        "stairSegmentCount": stair_count,
        "localGovernmentCount": len(councils),
        "networkType": PSP_NETWORK_TYPE,
        "coverage": "All Main Roads controlled paths returned by the statewide service",
        "filters": [f"NETWORK_TYPE = {PSP_NETWORK_TYPE}"],
    }


def write_feature_collection(path: Path, features: list[dict]) -> None:
    payload = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        help="Local Main Roads GeoJSON. If omitted, download the current PSP data.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="Directory for the generated source GeoJSON.",
    )
    parser.add_argument(
        "--public-data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "public" / "data",
        help="Directory for the GeoJSON deployed with the website.",
    )
    args = parser.parse_args()

    payload, source = load_psp_geojson(args.input)
    routes, stats = extract_psp_routes(payload, source["expectedFeatureCount"])
    for output_dir in (args.output_dir, args.public_data_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        write_feature_collection(output_dir / "psp-routes.geojson", routes)

    print(
        json.dumps(
            {
                "source": {
                    "name": PSP_SOURCE_NAME,
                    "licence": PSP_LICENCE,
                    **source,
                },
                **stats,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
