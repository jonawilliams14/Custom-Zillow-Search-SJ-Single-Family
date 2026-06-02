#!/usr/bin/env python3
"""Fetch RentCast rental listings for Jon's Bay Area rental report."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://api.rentcast.io/v1/listings/rental/long-term"
TARGET_CITIES = ("San Jose", "Milpitas", "Fremont")
PROPERTY_TYPES = ("Single Family", "Townhouse")
OUTPUT_PATH = Path("listings.json")


def fetch_json(api_key: str, params: dict[str, str | int]) -> list[dict[str, Any]]:
    url = f"{API_URL}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "accept": "application/json",
            "X-Api-Key": api_key,
            "User-Agent": "custom-rental-screening-report/1.0",
        },
    )
    with urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_listing(item: dict[str, Any]) -> dict[str, Any]:
    address = item.get("formattedAddress") or ", ".join(
        str(part) for part in [item.get("addressLine1"), item.get("city"), item.get("state"), item.get("zipCode")] if part
    )
    return {
        "id": item.get("id") or address,
        "address": address,
        "city": item.get("city") or "",
        "state": item.get("state") or "CA",
        "zipCode": item.get("zipCode") or "",
        "rent": item.get("price") or 0,
        "bedrooms": item.get("bedrooms") or 0,
        "bathrooms": item.get("bathrooms") or 0,
        "sqft": item.get("squareFootage") or 0,
        "home_type": item.get("propertyType") or "",
        "lat": item.get("latitude"),
        "lon": item.get("longitude"),
        "status": item.get("status") or "",
        "listingType": item.get("listingType") or "",
        "listedDate": item.get("listedDate"),
        "lastSeenDate": item.get("lastSeenDate"),
        "daysOnMarket": item.get("daysOnMarket"),
        "mlsName": item.get("mlsName"),
        "mlsNumber": item.get("mlsNumber"),
        "source": "RentCast",
    }


def keep_listing(item: dict[str, Any]) -> bool:
    rent = item.get("rent") or 0
    beds = item.get("bedrooms") or 0
    baths = item.get("bathrooms") or 0
    sqft = item.get("sqft") or 0
    home_type = str(item.get("home_type") or "").lower()
    city = str(item.get("city") or "").lower()
    return (
        city in {city.lower() for city in TARGET_CITIES}
        and 3000 <= rent <= 5000
        and sqft >= 1200
        and ((beds == 3 and baths >= 2) or (beds >= 4 and baths >= 2))
        and home_type in {"single family", "townhouse"}
        and item.get("lat") is not None
        and item.get("lon") is not None
    )


def main() -> int:
    api_key = os.environ.get("RENTCAST_API_KEY")
    if not api_key:
        print("Missing RENTCAST_API_KEY environment variable", file=sys.stderr)
        return 1

    listings: dict[str, dict[str, Any]] = {}
    for city in TARGET_CITIES:
        for property_type in PROPERTY_TYPES:
            params = {
                "city": city,
                "state": "CA",
                "status": "Active",
                "propertyType": property_type,
                "price": "3000:5000",
                "bedrooms": "3:",
                "bathrooms": "2:",
                "squareFootage": "1200:",
                "limit": 500,
            }
            for item in fetch_json(api_key, params):
                normalized = normalize_listing(item)
                if keep_listing(normalized):
                    listings[str(normalized["id"])] = normalized

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "RentCast rental listings API",
        "criteria": {
            "cities": list(TARGET_CITIES),
            "state": "CA",
            "rent": "$3,000-$5,000",
            "minimumSqft": 1200,
            "layouts": ["3bd/2ba", "4bd+/2ba"],
            "homeTypes": list(PROPERTY_TYPES),
        },
        "listings": sorted(listings.values(), key=lambda row: (row["city"], row["rent"], row["address"])),
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['listings'])} listings to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
