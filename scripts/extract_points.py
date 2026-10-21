#!/usr/bin/env python3
"""Build Perth water and toilet GeoJSON from community and official sources."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


SOURCE_NAME = "Water in Perth"
SOURCE_MAP_URL = (
    "https://www.google.com/maps/d/edit?mid=1n7QEPGo4tzhELbNhme4okzij4ao"
    "&usp=sharing"
)
SOURCE_KML_URL = (
    "https://www.google.com/maps/d/kml?mid=1n7QEPGo4tzhELbNhme4okzij4ao"
    "&forcekml=1"
)

TOILET_SOURCE_NAME = "National Public Toilet Map"
TOILET_DATASET_URL = "https://data.gov.au/data/dataset/national-public-toilet-map"
TOILET_PACKAGE_API_URL = (
    "https://data.gov.au/data/api/3/action/package_show"
    "?id=553b3049-2b8b-46a2-95e6-640d7986a8c1"
)
TOILET_RESOURCE_ID = "34076296-6692-4e30-b627-67b7c4eb1027"
TOILET_LICENCE = "Creative Commons Attribution 3.0 Australia"
TOILET_MATCH_METRES = 100.0
TOILET_NEARBY_METRES = 500.0

CITY_WATER_SOURCE_NAME = "City of Perth Street Appurtenances"
CITY_WATER_DATASET_URL = (
    "https://catalogue.data.wa.gov.au/dataset/perth-street-appurtenances"
)
CITY_WATER_SERVICE_URL = (
    "https://services7.arcgis.com/v8XBa2naYNQGOjlG/arcgis/rest/services/"
    "INF_AST_APPURTENANCES_PT_PV/FeatureServer/0"
)
CITY_WATER_LICENCE = "Creative Commons Attribution 4.0"
CITY_WATER_TYPES = {
    "DRINK_BF",
    "DRINK_BFDB",
    "DRINK_BSP",
    "DRINK_DB",
    "DRINK_STND",
}
WATER_MATCH_METRES = 50.0

CITY_BBQ_SOURCE_NAME = "City of Perth Street Appurtenances"
CITY_BBQ_DATASET_URL = CITY_WATER_DATASET_URL
CITY_BBQ_SERVICE_URL = CITY_WATER_SERVICE_URL
CITY_BBQ_LICENCE = CITY_WATER_LICENCE
CITY_BBQ_TYPES = {"BBQ_DOUBLE", "BBQ_SINGLE"}

OSM_SOURCE_NAME = "OpenStreetMap"
OSM_SOURCE_URL = "https://www.openstreetmap.org"
OSM_LICENCE = "Open Data Commons Open Database License 1.0"
OSM_LICENCE_URL = "https://www.openstreetmap.org/copyright"
OSM_OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
OSM_SHOWER_QUERY = """[out:json][timeout:90];
nwr["amenity"="shower"](-32.85,114.75,-31.05,116.95);
out center tags;
"""
OSM_WATER_QUERY = """[out:json][timeout:120];
node["amenity"="drinking_water"](-32.85,114.75,-31.05,116.95);
out tags meta;
"""
AMENITY_MATCH_METRES = 50.0
RESTRICTED_OSM_ACCESS = {"customers", "no", "permit", "private"}

PERTH_CENTRE = (-31.9523, 115.8613)
MAX_DISTANCE_KM = 100.0
TOILET_STYLE_TOKEN = "4186F0"

TOILET_RE = re.compile(r"toilets?|restrooms?|\bwc\b", re.I)
WATER_RE = re.compile(
    r"\b(water|drink|drinking|fountain|fountains|tap|taps|bubbler|hose)\b",
    re.I,
)
INACTIVE_WATER_PATTERNS = (
    (re.compile(r"\bbroken\b", re.I), "marked-broken"),
    (re.compile(r"\bout of order\b", re.I), "marked-out-of-order"),
    (re.compile(r"\bprivate\b", re.I), "private-property"),
)


def normalise_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value).replace("\u00a0", " ")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def distance_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    lat1_value, lon1_value = first
    lat2_value, lon2_value = second
    lat1 = math.radians(lat1_value)
    lat2 = math.radians(lat2_value)
    delta_lat = math.radians(lat2_value - lat1_value)
    delta_lon = math.radians(lon2_value - lon1_value)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def haversine_km(lat: float, lon: float) -> float:
    return distance_km(PERTH_CENTRE, (lat, lon))


def stable_id(name: str, style: str, lon: float, lat: float) -> str:
    identity = f"{name.casefold()}|{style}|{lon:.7f}|{lat:.7f}"
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()[:12]


def water_kind(name: str) -> str:
    lowered = name.casefold()
    if "fountain" in lowered or "bubbler" in lowered:
        return "fountain"
    if "tap" in lowered or "hose" in lowered:
        return "tap"
    return "water-point"


def make_feature(
    *,
    feature_id: str,
    name: str,
    description: str,
    style: str,
    lon: float,
    lat: float,
    category: str,
    classification_basis: list[str],
    mixed_amenities: bool,
) -> dict:
    properties = {
        "id": feature_id,
        "name": name or ("Public toilet" if category == "toilet" else "Water point"),
        "description": description,
        "category": category,
        "kind": "toilet" if category == "toilet" else water_kind(name),
        "mixedAmenities": mixed_amenities,
        "classificationBasis": classification_basis,
        "source": SOURCE_NAME,
        "sourceUrl": SOURCE_MAP_URL,
        "sourceStyle": style,
    }
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": properties,
    }


def load_kml(input_path: Path | None) -> bytes:
    if input_path:
        return input_path.read_bytes()

    request = urllib.request.Request(
        SOURCE_KML_URL,
        headers={"User-Agent": "PerthWaterMapDataImporter/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def download_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PerthWaterMapDataImporter/2.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def download_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PerthWaterMapDataImporter/2.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def load_official_toilet_csv(input_path: Path | None) -> tuple[bytes, dict]:
    if input_path:
        return input_path.read_bytes(), {
            "resourceId": TOILET_RESOURCE_ID,
            "datasetUrl": TOILET_DATASET_URL,
            "localInput": str(input_path),
        }

    package = download_json(TOILET_PACKAGE_API_URL)
    if not package.get("success"):
        raise ValueError("The data.gov.au package metadata request was unsuccessful")

    resources = package.get("result", {}).get("resources", [])
    resource = next(
        (item for item in resources if item.get("id") == TOILET_RESOURCE_ID),
        None,
    )
    if not resource or not resource.get("url"):
        raise ValueError("The National Public Toilet Map CSV resource was not found")

    return download_bytes(resource["url"]), {
        "resourceId": TOILET_RESOURCE_ID,
        "datasetUrl": TOILET_DATASET_URL,
        "downloadUrl": resource["url"],
        "lastModified": resource.get("last_modified"),
        "resourceSizeBytes": resource.get("size"),
        "packageMetadataModified": package.get("result", {}).get("metadata_modified"),
    }


def city_water_query_url() -> str:
    query = urllib.parse.urlencode(
        {
            "where": "UNIT_TYPE LIKE 'DRINK%'",
            "outFields": "*",
            "outSR": "4326",
            "f": "geojson",
        }
    )
    return f"{CITY_WATER_SERVICE_URL}/query?{query}"


def city_bbq_query_url() -> str:
    types = ",".join(f"'{value}'" for value in sorted(CITY_BBQ_TYPES))
    query = urllib.parse.urlencode(
        {
            "where": f"UNIT_TYPE IN ({types})",
            "outFields": "*",
            "outSR": "4326",
            "f": "geojson",
        }
    )
    return f"{CITY_BBQ_SERVICE_URL}/query?{query}"


def load_city_water_geojson(input_path: Path | None) -> tuple[dict, dict]:
    if input_path:
        return json.loads(input_path.read_text()), {
            "datasetUrl": CITY_WATER_DATASET_URL,
            "serviceUrl": CITY_WATER_SERVICE_URL,
            "localInput": str(input_path),
        }

    query_url = city_water_query_url()
    payload = download_json(query_url)
    if payload.get("error"):
        raise ValueError(
            "The City of Perth drinking-fountain request failed: "
            + str(payload["error"])
        )
    return payload, {
        "datasetUrl": CITY_WATER_DATASET_URL,
        "serviceUrl": CITY_WATER_SERVICE_URL,
        "queryUrl": query_url,
    }


def load_city_bbq_geojson(input_path: Path | None) -> tuple[dict, dict]:
    if input_path:
        return json.loads(input_path.read_text()), {
            "datasetUrl": CITY_BBQ_DATASET_URL,
            "serviceUrl": CITY_BBQ_SERVICE_URL,
            "localInput": str(input_path),
        }

    query_url = city_bbq_query_url()
    payload = download_json(query_url)
    if payload.get("error"):
        raise ValueError(
            "The City of Perth public BBQ request failed: " + str(payload["error"])
        )
    return payload, {
        "datasetUrl": CITY_BBQ_DATASET_URL,
        "serviceUrl": CITY_BBQ_SERVICE_URL,
        "queryUrl": query_url,
    }


def load_osm_amenities(
    input_path: Path | None, query: str, amenity_name: str
) -> tuple[dict, dict]:
    if input_path:
        payload = json.loads(input_path.read_text())
        return payload, {
            "sourceUrl": OSM_SOURCE_URL,
            "licence": OSM_LICENCE,
            "licenceUrl": OSM_LICENCE_URL,
            "localInput": str(input_path),
        }

    request_body = urllib.parse.urlencode({"data": query}).encode()
    errors = []
    for endpoint in OSM_OVERPASS_ENDPOINTS:
        request = urllib.request.Request(
            endpoint,
            data=request_body,
            headers={
                "User-Agent": "PerthWaterMapDataImporter/3.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.load(response)
            if not isinstance(payload.get("elements"), list):
                raise ValueError("response did not contain an elements array")
            return payload, {
                "sourceUrl": OSM_SOURCE_URL,
                "licence": OSM_LICENCE,
                "licenceUrl": OSM_LICENCE_URL,
                "overpassEndpoint": endpoint,
                "osmTimestamp": payload.get("osm3s", {}).get("timestamp_osm_base"),
            }
        except Exception as error:  # Try the next public mirror.
            errors.append(f"{endpoint}: {error}")
    raise ValueError(
        f"OpenStreetMap {amenity_name} query failed: " + "; ".join(errors)
    )


def load_osm_showers(input_path: Path | None) -> tuple[dict, dict]:
    return load_osm_amenities(input_path, OSM_SHOWER_QUERY, "shower")


def load_osm_water(input_path: Path | None) -> tuple[dict, dict]:
    return load_osm_amenities(input_path, OSM_WATER_QUERY, "drinking-water")


def official_bool(value: str | None) -> bool | None:
    value = normalise_text(value).casefold()
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def official_text(row: dict[str, str], key: str) -> str:
    return normalise_text(row.get(key))


def official_address(row: dict[str, str]) -> str:
    parts = [
        official_text(row, "Address1"),
        official_text(row, "Town"),
        official_text(row, "State"),
    ]
    return ", ".join(part for part in parts if part)


def make_official_toilet_feature(
    row: dict[str, str], lon: float, lat: float
) -> dict:
    facility_id = official_text(row, "FacilityID")
    feature_id = f"nptm-{facility_id}"
    drinking_water = official_bool(row.get("DrinkingWater"))
    properties = {
        "id": feature_id,
        "facilityId": facility_id,
        "name": official_text(row, "Name") or "Public toilet",
        "description": official_text(row, "ToiletNote"),
        "category": "toilet",
        "kind": "toilet",
        "mixedAmenities": drinking_water is True,
        "classificationBasis": ["official-national-public-toilet-map"],
        "facilityType": official_text(row, "FacilityType"),
        "address": official_address(row),
        "addressNote": official_text(row, "AddressNote"),
        "openingHours": official_text(row, "OpeningHours"),
        "openingHoursNote": official_text(row, "OpeningHoursNote"),
        "accessNote": official_text(row, "AccessNote"),
        "adultChangeNote": official_text(row, "AdultChangeNote"),
        "babyChangeNote": official_text(row, "BabyChangeNote"),
        "parkingNote": official_text(row, "ParkingNote"),
        "accessible": official_bool(row.get("Accessible")),
        "ambulant": official_bool(row.get("Ambulant")),
        "leftHandTransfer": official_bool(row.get("LHTransfer")),
        "rightHandTransfer": official_bool(row.get("RHTransfer")),
        "adultChange": official_bool(row.get("AdultChange")),
        "changingPlaces": official_bool(row.get("ChangingPlaces")),
        "babyChange": official_bool(row.get("BabyChange")),
        "babyCareRoom": official_bool(row.get("BabyCareRoom")),
        "drinkingWater": drinking_water,
        "shower": official_bool(row.get("Shower")),
        "sharpsDisposal": official_bool(row.get("SharpsDisposal")),
        "sanitaryDisposal": official_bool(row.get("SanitaryDisposal")),
        "parking": official_bool(row.get("Parking")),
        "parkingAccessible": official_bool(row.get("ParkingAccessible")),
        "keyRequired": official_bool(row.get("KeyRequired")),
        "mlak24": official_bool(row.get("MLAK24")),
        "mlakAfterHours": official_bool(row.get("MLAKAfterHours")),
        "paymentRequired": official_bool(row.get("PaymentRequired")),
        "male": official_bool(row.get("Male")),
        "female": official_bool(row.get("Female")),
        "unisex": official_bool(row.get("Unisex")),
        "allGender": official_bool(row.get("AllGender")),
        "source": TOILET_SOURCE_NAME,
        "sourceUrl": TOILET_DATASET_URL,
        "facilityUrl": official_text(row, "URL"),
        "licence": TOILET_LICENCE,
    }
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": properties,
    }


def extract_official_toilets(csv_bytes: bytes) -> tuple[list[dict], dict]:
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    required_fields = {"FacilityID", "Name", "State", "Latitude", "Longitude"}
    missing_fields = required_fields.difference(reader.fieldnames or [])
    if missing_fields:
        raise ValueError(
            "The National Public Toilet Map CSV is missing required fields: "
            + ", ".join(sorted(missing_fields))
        )

    toilets: list[dict] = []
    source_record_count = 0
    invalid_coordinate_count = 0
    missing_facility_id_count = 0
    duplicate_facility_id_count = 0
    outside_scope_count = 0
    seen_ids: set[str] = set()

    for row in reader:
        source_record_count += 1
        facility_id = official_text(row, "FacilityID")
        if not facility_id:
            missing_facility_id_count += 1
            continue
        if facility_id in seen_ids:
            duplicate_facility_id_count += 1
            continue
        seen_ids.add(facility_id)

        try:
            lat = float(official_text(row, "Latitude"))
            lon = float(official_text(row, "Longitude"))
        except ValueError:
            invalid_coordinate_count += 1
            continue
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            invalid_coordinate_count += 1
            continue
        if official_text(row, "State") != "WA" or haversine_km(lat, lon) > MAX_DISTANCE_KM:
            outside_scope_count += 1
            continue

        toilets.append(make_official_toilet_feature(row, lon, lat))

    toilets.sort(
        key=lambda feature: (
            feature["properties"]["name"].casefold(),
            feature["properties"]["facilityId"],
        )
    )
    stats = {
        "sourceRecordCount": source_record_count,
        "selectedRecordCount": len(toilets),
        "outsidePerth100kmOrNonWaCount": outside_scope_count,
        "invalidCoordinateCount": invalid_coordinate_count,
        "missingFacilityIdCount": missing_facility_id_count,
        "duplicateFacilityIdCount": duplicate_facility_id_count,
        "accessibleCount": sum(
            feature["properties"]["accessible"] is True for feature in toilets
        ),
        "babyChangeCount": sum(
            feature["properties"]["babyChange"] is True for feature in toilets
        ),
        "drinkingWaterCount": sum(
            feature["properties"]["drinkingWater"] is True for feature in toilets
        ),
        "showerCount": sum(
            feature["properties"]["shower"] is True for feature in toilets
        ),
    }
    return toilets, stats


def feature_lat_lon(feature: dict) -> tuple[float, float]:
    lon, lat = feature["geometry"]["coordinates"]
    return lat, lon


def validate_community_toilets(
    community_toilets: list[dict], official_toilets: list[dict]
) -> dict:
    if not official_toilets:
        raise ValueError("No official toilets were selected for the Perth area")

    matches = []
    for community in community_toilets:
        community_point = feature_lat_lon(community)
        nearest = min(
            official_toilets,
            key=lambda official: distance_km(
                community_point, feature_lat_lon(official)
            ),
        )
        distance_metres = (
            distance_km(community_point, feature_lat_lon(nearest)) * 1000
        )
        matches.append((distance_metres, community, nearest))

    review = []
    for distance_metres, community, nearest in matches:
        if distance_metres <= TOILET_MATCH_METRES:
            continue
        review.append(
            {
                "communityName": community["properties"]["name"],
                "communityCoordinates": community["geometry"]["coordinates"],
                "nearestOfficialFacilityId": nearest["properties"]["facilityId"],
                "nearestOfficialName": nearest["properties"]["name"],
                "distanceMetres": round(distance_metres),
            }
        )
    review.sort(key=lambda item: item["distanceMetres"], reverse=True)

    official_with_community_match = sum(
        any(
            distance_km(feature_lat_lon(official), feature_lat_lon(community))
            * 1000
            <= TOILET_MATCH_METRES
            for community in community_toilets
        )
        for official in official_toilets
    )
    return {
        "method": "nearest point by haversine distance",
        "matchDistanceMetres": TOILET_MATCH_METRES,
        "nearbyReviewDistanceMetres": TOILET_NEARBY_METRES,
        "communityRecordCount": len(community_toilets),
        "matchedWithin100mCount": sum(
            distance <= TOILET_MATCH_METRES for distance, _, _ in matches
        ),
        "nearby100mTo500mCount": sum(
            TOILET_MATCH_METRES < distance <= TOILET_NEARBY_METRES
            for distance, _, _ in matches
        ),
        "unmatchedBeyond500mCount": sum(
            distance > TOILET_NEARBY_METRES for distance, _, _ in matches
        ),
        "officialRecordsWithCommunityMatchCount": official_with_community_match,
        "officialRecordsAddingCoverageCount": len(official_toilets)
        - official_with_community_match,
        "communityRecordsForReview": review,
    }


def timestamp_iso(milliseconds: int | float | None) -> str:
    if not milliseconds:
        return ""
    return datetime.fromtimestamp(
        float(milliseconds) / 1000, timezone.utc
    ).isoformat().replace("+00:00", "Z")


def city_water_location(properties: dict) -> str:
    unit_id = normalise_text(properties.get("UNIT_ID"))
    stem = re.sub(r"DRF.*$", "", unit_id, flags=re.I)
    stem = re.sub(r"\d+[NSEW]?$", "", stem)
    stem = stem.replace("JHAbrahams", "JH Abrahams")
    stem = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", stem)
    stem = stem.replace("Fr Shr", "Foreshore")
    replacements = {
        "Gdns": "Gardens",
        "Res": "Reserve",
        "Int": "Interchange",
        "Sq": "Square",
        "Pl": "Place",
        "Ct": "Court",
        "St": "Street",
        "Tce": "Terrace",
        "Ck": "Creek",
    }
    stem = " ".join(replacements.get(token, token) for token in stem.split())
    stem = stem.replace("Street Georges", "St Georges")
    stem = re.sub(r"\b(?:COP|MRT)\b", "", stem)
    return re.sub(r"\s+", " ", stem).strip()


def make_city_water_feature(source_feature: dict) -> dict:
    source_properties = source_feature.get("properties", {})
    lon, lat = source_feature["geometry"]["coordinates"][:2]
    unit_id = normalise_text(source_properties.get("UNIT_ID"))
    location = city_water_location(source_properties)
    raw_description = normalise_text(source_properties.get("UNIT_DESC"))
    location_note = normalise_text(source_properties.get("LOCATION_DESC"))
    combined_description = f"{raw_description} {location_note}".casefold()
    name = (
        f"{location} drinking fountain"
        if location
        else "City of Perth drinking fountain"
    )
    feature_id = f"cop-water-{unit_id}"
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "id": feature_id,
            "assetId": unit_id,
            "name": name,
            "description": location_note,
            "category": "water",
            "kind": "fountain",
            "mixedAmenities": False,
            "drinkingWater": True,
            "classificationBasis": ["official-city-of-perth-drinking-fountain"],
            "assetDescription": raw_description,
            "assetType": normalise_text(source_properties.get("UNIT_TYPE")),
            "bottleFilling": "bottle fill" in combined_description,
            "dogBowl": "dog bowl" in combined_description,
            "lastUpdated": timestamp_iso(source_properties.get("EditDate")),
            "source": CITY_WATER_SOURCE_NAME,
            "sourceUrl": CITY_WATER_DATASET_URL,
            "licence": CITY_WATER_LICENCE,
        },
    }


def extract_city_water(geojson: dict) -> tuple[list[dict], dict]:
    source_features = geojson.get("features", [])
    water: list[dict] = []
    unsupported_type_count = 0
    invalid_record_count = 0
    duplicate_asset_id_count = 0
    seen_ids: set[str] = set()

    for source_feature in source_features:
        properties = source_feature.get("properties", {})
        if normalise_text(properties.get("UNIT_TYPE")) not in CITY_WATER_TYPES:
            unsupported_type_count += 1
            continue
        asset_id = normalise_text(properties.get("UNIT_ID"))
        geometry = source_feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if not asset_id or geometry.get("type") != "Point" or len(coordinates) < 2:
            invalid_record_count += 1
            continue
        if asset_id in seen_ids:
            duplicate_asset_id_count += 1
            continue
        seen_ids.add(asset_id)
        try:
            lon, lat = float(coordinates[0]), float(coordinates[1])
        except (TypeError, ValueError):
            invalid_record_count += 1
            continue
        if (
            not (-180 <= lon <= 180 and -90 <= lat <= 90)
            or haversine_km(lat, lon) > MAX_DISTANCE_KM
        ):
            invalid_record_count += 1
            continue
        source_feature = {
            **source_feature,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        }
        water.append(make_city_water_feature(source_feature))

    water.sort(key=lambda feature: feature["id"])
    updates = [
        feature["properties"]["lastUpdated"]
        for feature in water
        if feature["properties"]["lastUpdated"]
    ]
    return water, {
        "sourceRecordCount": len(source_features),
        "selectedRecordCount": len(water),
        "unsupportedAssetTypeCount": unsupported_type_count,
        "invalidRecordCount": invalid_record_count,
        "duplicateAssetIdCount": duplicate_asset_id_count,
        "latestSelectedAssetUpdate": max(updates, default=None),
        "bottleFillingCount": sum(
            feature["properties"]["bottleFilling"] for feature in water
        ),
        "dogBowlCount": sum(feature["properties"]["dogBowl"] for feature in water),
    }


def city_bbq_location(properties: dict) -> str:
    unit_id = normalise_text(properties.get("UNIT_ID"))
    stem = re.sub(r"BBQ.*$", "", unit_id, flags=re.I)
    stem = stem.replace("FrShr", " Foreshore")
    stem = stem.replace("Gdns", " Gardens")
    stem = stem.replace("Res", " Reserve")
    stem = stem.replace("Int", " Interchange")
    stem = stem.replace("Ck", " Creek")
    stem = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", stem)
    stem = re.sub(r"\bCOP\b", "", stem)
    return re.sub(r"\s+", " ", stem).strip()


def extract_city_bbqs(geojson: dict) -> tuple[list[dict], dict]:
    source_features = geojson.get("features", [])
    bbqs: list[dict] = []
    invalid_record_count = 0
    unsupported_type_count = 0
    seen_ids: set[str] = set()

    for source_feature in source_features:
        properties = source_feature.get("properties", {})
        asset_type = normalise_text(properties.get("UNIT_TYPE"))
        if asset_type not in CITY_BBQ_TYPES:
            unsupported_type_count += 1
            continue
        asset_id = normalise_text(properties.get("UNIT_ID"))
        geometry = source_feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if not asset_id or geometry.get("type") != "Point" or len(coordinates) < 2:
            invalid_record_count += 1
            continue
        if asset_id in seen_ids:
            continue
        seen_ids.add(asset_id)
        try:
            lon, lat = float(coordinates[0]), float(coordinates[1])
        except (TypeError, ValueError):
            invalid_record_count += 1
            continue
        if (
            not (-180 <= lon <= 180 and -90 <= lat <= 90)
            or haversine_km(lat, lon) > MAX_DISTANCE_KM
        ):
            invalid_record_count += 1
            continue

        location = city_bbq_location(properties)
        feature_id = f"cop-bbq-{asset_id}"
        description = normalise_text(properties.get("LOCATION_DESC"))
        bbqs.append(
            {
                "type": "Feature",
                "id": feature_id,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "id": feature_id,
                    "assetId": asset_id,
                    "name": f"{location} public BBQ" if location else "Public BBQ",
                    "description": description,
                    "category": "bbq",
                    "kind": "double" if asset_type == "BBQ_DOUBLE" else "single",
                    "assetDescription": normalise_text(properties.get("UNIT_DESC")),
                    "assetType": asset_type,
                    "lastUpdated": timestamp_iso(properties.get("EditDate")),
                    "source": CITY_BBQ_SOURCE_NAME,
                    "sourceUrl": CITY_BBQ_DATASET_URL,
                    "licence": CITY_BBQ_LICENCE,
                },
            }
        )

    bbqs.sort(key=lambda feature: feature["id"])
    updates = [
        feature["properties"]["lastUpdated"]
        for feature in bbqs
        if feature["properties"]["lastUpdated"]
    ]
    return bbqs, {
        "sourceRecordCount": len(source_features),
        "selectedRecordCount": len(bbqs),
        "unsupportedAssetTypeCount": unsupported_type_count,
        "invalidRecordCount": invalid_record_count,
        "latestSelectedAssetUpdate": max(updates, default=None),
        "singlePlateAssetCount": sum(
            feature["properties"]["kind"] == "single" for feature in bbqs
        ),
        "doublePlateAssetCount": sum(
            feature["properties"]["kind"] == "double" for feature in bbqs
        ),
    }


def make_toilet_amenity_feature(toilet: dict, category: str) -> dict:
    source = toilet["properties"]
    feature_id = f"nptm-{category}-{source['facilityId']}"
    properties = dict(source)
    properties.update(
        {
            "id": feature_id,
            "category": category,
            "parentCategory": "toilet",
            "kind": category,
        }
    )
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": toilet["geometry"],
        "properties": properties,
    }


def osm_element_coordinates(element: dict) -> tuple[float, float] | None:
    centre = element.get("center") or {}
    lat = element.get("lat", centre.get("lat"))
    lon = element.get("lon", centre.get("lon"))
    try:
        lat_value, lon_value = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (-180 <= lon_value <= 180 and -90 <= lat_value <= 90):
        return None
    return lat_value, lon_value


def extract_osm_showers(payload: dict) -> tuple[list[dict], dict]:
    showers: list[dict] = []
    restricted_count = 0
    unsupported_count = 0
    invalid_count = 0
    seen_ids: set[str] = set()

    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        access = normalise_text(tags.get("access")).casefold()
        if access in RESTRICTED_OSM_ACCESS:
            restricted_count += 1
            continue
        amenity = normalise_text(tags.get("amenity")).casefold()
        shower = normalise_text(tags.get("shower")).casefold()
        if amenity != "shower":
            unsupported_count += 1
            continue
        coordinates = osm_element_coordinates(element)
        if not coordinates or haversine_km(*coordinates) > MAX_DISTANCE_KM:
            invalid_count += 1
            continue
        element_type = normalise_text(element.get("type"))
        element_id = element.get("id")
        source_id = f"{element_type}/{element_id}"
        if not element_type or element_id is None or source_id in seen_ids:
            invalid_count += 1
            continue
        seen_ids.add(source_id)
        lat, lon = coordinates
        feature_id = f"osm-shower-{element_type}-{element_id}"
        fee = normalise_text(tags.get("fee"))
        description_parts = []
        if normalise_text(tags.get("description")):
            description_parts.append(normalise_text(tags.get("description")))
        if not access:
            description_parts.append("Public access is not specified in the source data.")
        showers.append(
            {
                "type": "Feature",
                "id": feature_id,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "id": feature_id,
                    "name": normalise_text(tags.get("name")) or "Public shower",
                    "description": " ".join(description_parts),
                    "category": "shower",
                    "kind": "shower",
                    "shower": True,
                    "accessNote": normalise_text(tags.get("access")),
                    "openingHours": normalise_text(tags.get("opening_hours")),
                    "paymentRequired": fee.casefold() == "yes",
                    "fee": fee,
                    "coldWater": normalise_text(tags.get("hot_water")).casefold() == "no",
                    "outdoor": normalise_text(tags.get("outdoor")).casefold() == "yes"
                    or shower == "outdoor",
                    "source": OSM_SOURCE_NAME,
                    "sourceId": source_id,
                    "sourceUrl": f"{OSM_SOURCE_URL}/{source_id}",
                    "licence": OSM_LICENCE,
                    "licenceUrl": OSM_LICENCE_URL,
                    "classificationBasis": ["openstreetmap-amenity-shower"],
                },
            }
        )

    showers.sort(key=lambda feature: feature["id"])
    return showers, {
        "sourceElementCount": len(payload.get("elements", [])),
        "selectedPublicCandidateCount": len(showers),
        "restrictedAccessExcludedCount": restricted_count,
        "unsupportedElementCount": unsupported_count,
        "invalidOrOutsideScopeCount": invalid_count,
    }


def osm_survey_date(tags: dict) -> str:
    for key in ("check_date", "survey:date", "survey_date"):
        value = normalise_text(tags.get(key))
        if value:
            return value
    return ""


def extract_osm_water(payload: dict) -> tuple[list[dict], dict]:
    water: list[dict] = []
    restricted_count = 0
    unsupported_count = 0
    invalid_count = 0
    seen_ids: set[str] = set()

    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        access = normalise_text(tags.get("access")).casefold()
        if access in RESTRICTED_OSM_ACCESS:
            restricted_count += 1
            continue
        if normalise_text(tags.get("amenity")).casefold() != "drinking_water":
            unsupported_count += 1
            continue
        if normalise_text(tags.get("drinking_water")).casefold() == "no":
            unsupported_count += 1
            continue
        coordinates = osm_element_coordinates(element)
        if not coordinates or haversine_km(*coordinates) > MAX_DISTANCE_KM:
            invalid_count += 1
            continue
        element_type = normalise_text(element.get("type"))
        element_id = element.get("id")
        source_id = f"{element_type}/{element_id}"
        if not element_type or element_id is None or source_id in seen_ids:
            invalid_count += 1
            continue
        seen_ids.add(source_id)

        lat, lon = coordinates
        feature_id = f"osm-water-{element_type}-{element_id}"
        fountain = normalise_text(tags.get("fountain")).casefold()
        bottle = normalise_text(tags.get("bottle")).casefold()
        dog = normalise_text(tags.get("dog")).casefold()
        fee = normalise_text(tags.get("fee"))
        description_parts = []
        if normalise_text(tags.get("description")):
            description_parts.append(normalise_text(tags.get("description")))
        if not access:
            description_parts.append("Public access is not specified in the source data.")

        water.append(
            {
                "type": "Feature",
                "id": feature_id,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "id": feature_id,
                    "name": normalise_text(tags.get("name")) or "Drinking water",
                    "description": " ".join(description_parts),
                    "category": "water",
                    "kind": "fountain" if fountain else "water-point",
                    "mixedAmenities": False,
                    "drinkingWater": True,
                    "accessNote": normalise_text(tags.get("access")),
                    "openingHours": normalise_text(tags.get("opening_hours")),
                    "paymentRequired": fee.casefold() == "yes",
                    "fee": fee,
                    "bottleFilling": bottle == "yes",
                    "dogBowl": dog == "yes",
                    "wheelchair": normalise_text(tags.get("wheelchair")),
                    "indoor": normalise_text(tags.get("indoor")).casefold() == "yes",
                    "lastChecked": osm_survey_date(tags),
                    "sourceUpdated": normalise_text(element.get("timestamp")),
                    "source": OSM_SOURCE_NAME,
                    "sourceId": source_id,
                    "sourceUrl": f"{OSM_SOURCE_URL}/{source_id}",
                    "licence": OSM_LICENCE,
                    "licenceUrl": OSM_LICENCE_URL,
                    "classificationBasis": ["openstreetmap-amenity-drinking-water"],
                },
            }
        )

    water.sort(key=lambda feature: feature["id"])
    return water, {
        "sourceElementCount": len(payload.get("elements", [])),
        "selectedPublicCandidateCount": len(water),
        "restrictedAccessExcludedCount": restricted_count,
        "unsupportedElementCount": unsupported_count,
        "invalidOrOutsideScopeCount": invalid_count,
        "explicitPublicAccessCount": sum(
            feature["properties"]["accessNote"].casefold() in {"yes", "public"}
            for feature in water
        ),
    }


def merge_showers(
    toilet_showers: list[dict], osm_showers: list[dict]
) -> tuple[list[dict], dict]:
    merged = list(toilet_showers)
    replacements = []
    for feature in osm_showers:
        match = nearest_water_match(feature, toilet_showers)
        if match and match[0] <= AMENITY_MATCH_METRES:
            distance_metres, nearest = match
            add_corroboration(nearest, feature)
            replacements.append(
                {
                    "osmId": feature["properties"]["sourceId"],
                    "nationalFacilityId": nearest["properties"]["facilityId"],
                    "nationalName": nearest["properties"]["name"],
                    "distanceMetres": round(distance_metres),
                }
            )
        else:
            merged.append(feature)
    merged.sort(
        key=lambda feature: (
            feature["properties"]["name"].casefold(),
            feature["properties"]["id"],
        )
    )
    return merged, {
        "method": "source-priority merge using nearest-point haversine distance",
        "sourcePriority": [TOILET_SOURCE_NAME, OSM_SOURCE_NAME],
        "crossSourceMatchDistanceMetres": AMENITY_MATCH_METRES,
        "nationalToiletMapShowerCount": len(toilet_showers),
        "openStreetMapPublicCandidateCount": len(osm_showers),
        "openStreetMapRecordsMatchedToOfficialCount": len(replacements),
        "openStreetMapRecordsAddingCoverageCount": len(osm_showers)
        - len(replacements),
        "mergedRecordCount": len(merged),
        "matchedRecords": replacements,
    }


def make_toilet_water_feature(toilet: dict) -> dict:
    source = toilet["properties"]
    facility_id = source["facilityId"]
    feature_id = f"nptm-water-{facility_id}"
    copied_fields = (
        "facilityId",
        "facilityType",
        "address",
        "addressNote",
        "openingHours",
        "openingHoursNote",
        "accessNote",
        "accessible",
        "paymentRequired",
        "keyRequired",
        "mlak24",
        "mlakAfterHours",
        "source",
        "sourceUrl",
        "facilityUrl",
        "licence",
    )
    properties = {key: source.get(key) for key in copied_fields}
    properties.update(
        {
            "id": feature_id,
            "name": source["name"],
            "description": source["description"],
            "category": "water",
            "kind": "water-point",
            "mixedAmenities": True,
            "drinkingWater": True,
            "classificationBasis": [
                "official-national-public-toilet-map-drinking-water"
            ],
        }
    )
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": toilet["geometry"],
        "properties": properties,
    }


def add_corroboration(target: dict, corroborating: dict) -> None:
    properties = target["properties"]
    source = corroborating["properties"]["source"]
    source_id = corroborating["properties"]["id"]
    sources = properties.setdefault("corroboratedSources", [])
    source_ids = properties.setdefault("corroboratedSourceIds", [])
    if source not in sources:
        sources.append(source)
    if source_id not in source_ids:
        source_ids.append(source_id)


def nearest_water_match(
    feature: dict, candidates: list[dict]
) -> tuple[float, dict] | None:
    if not candidates:
        return None
    point = feature_lat_lon(feature)
    nearest = min(
        candidates,
        key=lambda candidate: distance_km(point, feature_lat_lon(candidate)),
    )
    return distance_km(point, feature_lat_lon(nearest)) * 1000, nearest


def merge_water_sources(
    community_water: list[dict],
    toilet_water: list[dict],
    city_water: list[dict],
    osm_water: list[dict],
) -> tuple[list[dict], dict]:
    official_water = list(city_water)
    toilet_replacements = []
    for feature in toilet_water:
        match = nearest_water_match(feature, city_water)
        if match and match[0] <= WATER_MATCH_METRES:
            distance_metres, nearest = match
            add_corroboration(nearest, feature)
            toilet_replacements.append(
                {
                    "nationalFacilityId": feature["properties"]["facilityId"],
                    "nationalName": feature["properties"]["name"],
                    "cityAssetId": nearest["properties"]["assetId"],
                    "cityName": nearest["properties"]["name"],
                    "distanceMetres": round(distance_metres),
                }
            )
        else:
            official_water.append(feature)

    merged = list(official_water)
    community_replacements = []
    corroborated_official_ids: set[str] = set()
    for feature in community_water:
        match = nearest_water_match(feature, official_water)
        if match and match[0] <= WATER_MATCH_METRES:
            distance_metres, nearest = match
            add_corroboration(nearest, feature)
            corroborated_official_ids.add(nearest["id"])
            community_replacements.append(
                {
                    "communityId": feature["properties"]["id"],
                    "communityName": feature["properties"]["name"],
                    "communityCoordinates": feature["geometry"]["coordinates"],
                    "officialId": nearest["properties"]["id"],
                    "officialName": nearest["properties"]["name"],
                    "officialSource": nearest["properties"]["source"],
                    "distanceMetres": round(distance_metres),
                }
            )
        else:
            merged.append(feature)

    osm_replacements = []
    for feature in osm_water:
        match = nearest_water_match(feature, merged)
        if match and match[0] <= WATER_MATCH_METRES:
            distance_metres, nearest = match
            add_corroboration(nearest, feature)
            osm_replacements.append(
                {
                    "osmId": feature["properties"]["sourceId"],
                    "existingId": nearest["properties"]["id"],
                    "existingName": nearest["properties"]["name"],
                    "existingSource": nearest["properties"]["source"],
                    "distanceMetres": round(distance_metres),
                }
            )
        else:
            merged.append(feature)

    merged.sort(
        key=lambda feature: (
            feature["properties"]["name"].casefold(),
            feature["properties"]["id"],
        )
    )
    source_counts: dict[str, int] = {}
    for feature in merged:
        source = feature["properties"]["source"]
        source_counts[source] = source_counts.get(source, 0) + 1

    return merged, {
        "method": "source-priority merge using nearest-point haversine distance",
        "sourcePriority": [
            CITY_WATER_SOURCE_NAME,
            TOILET_SOURCE_NAME,
            SOURCE_NAME,
            OSM_SOURCE_NAME,
        ],
        "crossSourceMatchDistanceMetres": WATER_MATCH_METRES,
        "communityCandidateCount": len(community_water),
        "nationalToiletMapDrinkingWaterCount": len(toilet_water),
        "cityOfPerthDrinkingFountainCount": len(city_water),
        "nationalRecordsReplacedByCityCount": len(toilet_replacements),
        "communityRecordsReplacedByOfficialCount": len(community_replacements),
        "communityRecordsRetainedCount": len(community_water)
        - len(community_replacements),
        "openStreetMapPublicCandidateCount": len(osm_water),
        "openStreetMapRecordsMatchedToExistingCount": len(osm_replacements),
        "openStreetMapRecordsAddingCoverageCount": len(osm_water)
        - len(osm_replacements),
        "officialRecordsWithCommunityCorroborationCount": len(
            corroborated_official_ids
        ),
        "officialRecordsAddingCoverageCount": len(official_water)
        - len(corroborated_official_ids),
        "mergedRecordCount": len(merged),
        "mergedRecordsByPrimarySource": source_counts,
        "nationalRecordsReplacedByCity": toilet_replacements,
        "communityRecordsReplacedByOfficial": community_replacements,
        "openStreetMapRecordsMatchedToExisting": osm_replacements,
    }


def extract(kml: bytes) -> tuple[list[dict], list[dict], list[dict], dict]:
    root = ET.fromstring(kml)
    placemarks = root.findall(".//{*}Placemark")
    water: list[dict] = []
    toilets: list[dict] = []
    rejected: list[dict] = []
    seen: set[tuple[float, float, str, str]] = set()
    classification_review: list[dict] = []

    for source_index, placemark in enumerate(placemarks, start=1):
        name = normalise_text(placemark.findtext("./{*}name"))
        description = normalise_text(placemark.findtext("./{*}description"))
        style = normalise_text(placemark.findtext("./{*}styleUrl"))
        coordinate_text = placemark.findtext("./{*}Point/{*}coordinates")
        reasons: list[str] = []
        lon = lat = None

        if not coordinate_text:
            reasons.append("non-point-geometry")
        else:
            parts = [part.strip() for part in coordinate_text.split(",")]
            try:
                lon, lat = float(parts[0]), float(parts[1])
            except (IndexError, ValueError):
                reasons.append("invalid-coordinates")

        if lon is not None and lat is not None:
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                reasons.append("invalid-coordinates")
            elif haversine_km(lat, lon) > MAX_DISTANCE_KM:
                reasons.append("outside-perth-100km")

            duplicate_key = (round(lon, 7), round(lat, 7), name.casefold(), style)
            if duplicate_key in seen:
                reasons.append("duplicate")
            else:
                seen.add(duplicate_key)

        combined_text = f"{name} {description}"
        inactive_reasons = [
            reason
            for pattern, reason in INACTIVE_WATER_PATTERNS
            if pattern.search(combined_text)
        ]

        if reasons:
            rejected.append(
                {
                    "type": "Feature",
                    "geometry": (
                        {"type": "Point", "coordinates": [lon, lat]}
                        if lon is not None and lat is not None
                        else None
                    ),
                    "properties": {
                        "sourceIndex": source_index,
                        "name": name,
                        "description": description,
                        "sourceStyle": style,
                        "reasons": reasons,
                    },
                }
            )
            continue

        assert lon is not None and lat is not None
        style_says_toilet = TOILET_STYLE_TOKEN in style.upper()
        name_says_toilet = bool(TOILET_RE.search(name))
        name_says_water = bool(WATER_RE.search(name))

        # Names override a conflicting colour style. Mixed amenities are retained
        # in both datasets, while a blue marker explicitly named "Water Fountain"
        # remains water-only.
        is_toilet = name_says_toilet or (style_says_toilet and not name_says_water)
        is_water = name_says_water or (
            not style_says_toilet and not (name_says_toilet and not name_says_water)
        )

        if style_says_toilet != name_says_toilet and (name_says_toilet or name_says_water):
            classification_review.append(
                {
                    "name": name,
                    "sourceStyle": style,
                    "coordinates": [lon, lat],
                    "savedAs": [
                        category
                        for category, included in (
                            ("water", is_water and not inactive_reasons),
                            ("toilet", is_toilet),
                        )
                        if included
                    ],
                }
            )

        feature_id = stable_id(name, style, lon, lat)
        mixed_amenities = is_water and is_toilet

        if is_toilet:
            basis = []
            if style_says_toilet:
                basis.append("source-toilet-style")
            if name_says_toilet:
                basis.append("toilet-name")
            toilets.append(
                make_feature(
                    feature_id=feature_id,
                    name=name,
                    description=description,
                    style=style,
                    lon=lon,
                    lat=lat,
                    category="toilet",
                    classification_basis=basis,
                    mixed_amenities=mixed_amenities,
                )
            )

        if is_water and not inactive_reasons:
            basis = []
            if not style_says_toilet:
                basis.append("source-water-style")
            if name_says_water:
                basis.append("water-name")
            water.append(
                make_feature(
                    feature_id=feature_id,
                    name=name,
                    description=description,
                    style=style,
                    lon=lon,
                    lat=lat,
                    category="water",
                    classification_basis=basis,
                    mixed_amenities=mixed_amenities,
                )
            )
        elif is_water:
            rejected.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "sourceIndex": source_index,
                        "name": name,
                        "description": description,
                        "sourceStyle": style,
                        "reasons": inactive_reasons,
                    },
                }
            )

    report = {
        "communityWaterSource": {
            "name": SOURCE_NAME,
            "mapUrl": SOURCE_MAP_URL,
            "kmlUrl": SOURCE_KML_URL,
            "sourcePlacemarkCount": len(placemarks),
        },
        "communityWaterCandidateCount": len(water),
        "communityToiletCandidateCount": len(toilets),
        "communityMixedAmenityCount": sum(
            1 for feature in water if feature["properties"]["mixedAmenities"]
        ),
        "rejectedRecordCount": len(rejected),
        "classificationConflictCount": len(classification_review),
        "classificationReview": classification_review,
        "cleaningRules": {
            "perthCentre": {"latitude": PERTH_CENTRE[0], "longitude": PERTH_CENTRE[1]},
            "maximumDistanceKm": MAX_DISTANCE_KM,
            "deduplication": "same rounded coordinates, normalised name, and source style",
            "inactiveWaterMarkers": [reason for _, reason in INACTIVE_WATER_PATTERNS],
            "toiletHandling": (
                "community toilet candidates are audit inputs only; the deployable "
                "toilet dataset comes from the National Public Toilet Map"
            ),
        },
        "rejectionsByReason": {},
    }
    for feature in rejected:
        for reason in feature["properties"]["reasons"]:
            report["rejectionsByReason"][reason] = (
                report["rejectionsByReason"].get(reason, 0) + 1
            )

    return water, toilets, rejected, report


def write_feature_collection(path: Path, features: list[dict]) -> None:
    payload = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="Local KML file. If omitted, download the public source map.",
    )
    parser.add_argument(
        "--toilet-csv",
        type=Path,
        help=(
            "Local National Public Toilet Map CSV. If omitted, resolve and "
            "download the current CSV through data.gov.au."
        ),
    )
    parser.add_argument(
        "--city-water-geojson",
        type=Path,
        help=(
            "Local City of Perth Street Appurtenances GeoJSON. If omitted, "
            "download current drinking-fountain assets from ArcGIS."
        ),
    )
    parser.add_argument(
        "--city-bbq-geojson",
        type=Path,
        help=(
            "Local City of Perth Street Appurtenances BBQ GeoJSON. If omitted, "
            "download current public BBQ assets from ArcGIS."
        ),
    )
    parser.add_argument(
        "--osm-water-json",
        type=Path,
        help=(
            "Local Overpass JSON containing drinking-water candidates. If omitted, "
            "query current OpenStreetMap data through a public Overpass endpoint."
        ),
    )
    parser.add_argument(
        "--osm-showers-json",
        type=Path,
        help=(
            "Local Overpass JSON containing shower candidates. If omitted, "
            "query current OpenStreetMap data through a public Overpass endpoint."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="Directory for generated GeoJSON and the import report.",
    )
    parser.add_argument(
        "--public-data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "public" / "data",
        help="Directory for the GeoJSON files deployed with the website.",
    )
    args = parser.parse_args()

    community_water, community_toilets, rejected, report = extract(
        load_kml(args.input)
    )
    toilet_csv, toilet_source = load_official_toilet_csv(args.toilet_csv)
    toilets, toilet_stats = extract_official_toilets(toilet_csv)
    toilet_water = [
        make_toilet_water_feature(feature)
        for feature in toilets
        if feature["properties"]["drinkingWater"] is True
    ]
    city_water_geojson, city_water_source = load_city_water_geojson(
        args.city_water_geojson
    )
    city_water, city_water_stats = extract_city_water(city_water_geojson)
    osm_water_payload, osm_water_source = load_osm_water(args.osm_water_json)
    osm_water, osm_water_stats = extract_osm_water(osm_water_payload)
    water, water_merge = merge_water_sources(
        community_water, toilet_water, city_water, osm_water
    )
    adult_change = [
        make_toilet_amenity_feature(feature, "adult-change")
        for feature in toilets
        if feature["properties"]["adultChange"] is True
    ]
    baby_change = [
        make_toilet_amenity_feature(feature, "baby-change")
        for feature in toilets
        if feature["properties"]["babyChange"] is True
    ]
    toilet_showers = [
        make_toilet_amenity_feature(feature, "shower")
        for feature in toilets
        if feature["properties"]["shower"] is True
    ]
    osm_shower_payload, osm_shower_source = load_osm_showers(
        args.osm_showers_json
    )
    osm_showers, osm_shower_stats = extract_osm_showers(osm_shower_payload)
    showers, shower_merge = merge_showers(toilet_showers, osm_showers)
    city_bbq_geojson, city_bbq_source = load_city_bbq_geojson(
        args.city_bbq_geojson
    )
    bbqs, city_bbq_stats = extract_city_bbqs(city_bbq_geojson)
    report["waterPointCount"] = len(water)
    report["officialWaterSources"] = {
        "cityOfPerth": {
            "name": CITY_WATER_SOURCE_NAME,
            "licence": CITY_WATER_LICENCE,
            **city_water_source,
            **city_water_stats,
        },
        "nationalPublicToiletMap": {
            "name": TOILET_SOURCE_NAME,
            "datasetUrl": TOILET_DATASET_URL,
            "licence": TOILET_LICENCE,
            "drinkingWaterRecordCount": len(toilet_water),
        },
        "openStreetMap": {
            "name": OSM_SOURCE_NAME,
            **osm_water_source,
            **osm_water_stats,
        },
    }
    report["waterMerge"] = water_merge
    report["toiletPointCount"] = len(toilets)
    report["toiletSource"] = {
        "name": TOILET_SOURCE_NAME,
        "licence": TOILET_LICENCE,
        **toilet_source,
        **toilet_stats,
    }
    report["toiletValidation"] = validate_community_toilets(
        community_toilets, toilets
    )
    report["amenityLayers"] = {
        "adultChange": {
            "recordCount": len(adult_change),
            "source": TOILET_SOURCE_NAME,
        },
        "babyChange": {
            "recordCount": len(baby_change),
            "source": TOILET_SOURCE_NAME,
        },
        "showers": {
            "recordCount": len(showers),
            "openStreetMap": {**osm_shower_source, **osm_shower_stats},
            "merge": shower_merge,
        },
        "bbqs": {
            "recordCount": len(bbqs),
            "source": {
                "name": CITY_BBQ_SOURCE_NAME,
                "licence": CITY_BBQ_LICENCE,
                **city_bbq_source,
                **city_bbq_stats,
            },
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_feature_collection(args.output_dir / "water-points.geojson", water)
    write_feature_collection(args.output_dir / "toilets.geojson", toilets)
    write_feature_collection(args.output_dir / "showers.geojson", showers)
    write_feature_collection(args.output_dir / "adult-change.geojson", adult_change)
    write_feature_collection(args.output_dir / "baby-change.geojson", baby_change)
    write_feature_collection(args.output_dir / "bbqs.geojson", bbqs)
    write_feature_collection(args.output_dir / "rejected-points.geojson", rejected)
    (args.output_dir / "import-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )

    args.public_data_dir.mkdir(parents=True, exist_ok=True)
    write_feature_collection(args.public_data_dir / "water-points.geojson", water)
    write_feature_collection(args.public_data_dir / "toilets.geojson", toilets)
    write_feature_collection(args.public_data_dir / "showers.geojson", showers)
    write_feature_collection(
        args.public_data_dir / "adult-change.geojson", adult_change
    )
    write_feature_collection(
        args.public_data_dir / "baby-change.geojson", baby_change
    )
    write_feature_collection(args.public_data_dir / "bbqs.geojson", bbqs)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
