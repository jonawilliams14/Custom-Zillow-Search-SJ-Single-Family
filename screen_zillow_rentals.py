#!/usr/bin/env python3
"""Generate an HTML or Markdown rental screening report from listing CSV rows."""

from __future__ import annotations

import argparse
import csv
import html
import math
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

PREFERRED_CITIES = {"san jose", "milpitas"}
ACCEPTABLE_CITIES = {"fremont", "sunnyvale", "santa clara", "newark", "cupertino"}
ALLOWED_HOME_TYPES = {"single family", "single-family", "sfh", "house", "townhome", "townhouse"}
FREMONT = (37.5485, -121.9886)
SUNNYVALE = (37.3688, -122.0363)
CORRIDOR_MIDPOINT = ((FREMONT[0] + SUNNYVALE[0]) / 2, (FREMONT[1] + SUNNYVALE[1]) / 2)
DESTINATIONS = {
    "sjsu": ("San Jose State University", "One Washington Square, San Jose, CA 95192", (37.3349064, -121.8845519)),
    "villa_sport": ("VillaSport San Jose", "1167 N Capitol Ave, San Jose, CA 95132", (37.405989, -121.847750)),
    "lam_research": ("Lam Research Fremont", "4650 Cushing Pkwy, Fremont, CA 94538", (37.4886, -121.95694)),
    "northrop_grumman": ("Northrop Grumman Sunnyvale", "401 E Hendy Ave, Sunnyvale, CA 94086", (37.377395, -122.0250165)),
}


@dataclass(frozen=True)
class Listing:
    address: str
    city: str
    url: str
    rent: int
    bedrooms: int
    bathrooms: float
    sqft: int
    home_type: str
    lat: float | None
    lon: float | None
    parks_nearby: int
    notes: str


def parse_int(value: str, default: int = 0) -> int:
    cleaned = value.replace("$", "").replace(",", "").strip()
    return int(float(cleaned)) if cleaned else default


def parse_float(value: str) -> float | None:
    return float(value.strip()) if value.strip() else None


def load_listings(csv_path: Path) -> list[Listing]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return [
            Listing(
                address=row.get("address", "").strip(),
                city=row.get("city", "").strip(),
                url=row.get("url", "").strip(),
                rent=parse_int(row.get("rent", "")),
                bedrooms=parse_int(row.get("bedrooms", "")),
                bathrooms=float(row.get("bathrooms", "0") or 0),
                sqft=parse_int(row.get("sqft", "")),
                home_type=row.get("home_type", "").strip(),
                lat=parse_float(row.get("lat", "")),
                lon=parse_float(row.get("lon", "")),
                parks_nearby=parse_int(row.get("parks_nearby", "")),
                notes=row.get("notes", "").strip(),
            )
            for row in csv.DictReader(handle)
        ]


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    radius_miles = 3958.8
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    inner = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius_miles * math.asin(math.sqrt(inner))


def coords(listing: Listing) -> tuple[float, float] | None:
    return None if listing.lat is None or listing.lon is None else (listing.lat, listing.lon)


def destination_distance(listing: Listing, key: str) -> float | None:
    listing_coords = coords(listing)
    return None if listing_coords is None else haversine_miles(listing_coords, DESTINATIONS[key][2])


def maps_url(listing: Listing, key: str) -> str | None:
    listing_coords = coords(listing)
    if listing_coords is None:
        return None
    origin = f"{listing_coords[0]:.6f},{listing_coords[1]:.6f}"
    destination = quote_plus(DESTINATIONS[key][1])
    return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=driving"


def villa_commute_minutes(distance_miles: float | None) -> int | None:
    if distance_miles is None:
        return None
    road_miles = distance_miles * 1.3
    average_mph = 24 if road_miles <= 8 else 32 if road_miles <= 18 else 40
    return round((road_miles / average_mph) * 60)


def fmt_distance(distance_miles: float | None) -> str:
    return "n/a" if distance_miles is None else f"{distance_miles:.1f} mi"


def fmt_drive(distance_miles: float | None) -> str:
    return "n/a" if distance_miles is None else f"~{distance_miles * 1.3:.1f} mi drive"


def fmt_commute(minutes: int | None) -> str:
    return "n/a" if minutes is None else f"~{minutes} min"


def md_link(listing: Listing, key: str, text: str) -> str:
    url = maps_url(listing, key)
    return text if url is None else f"[{text}]({url})"


def html_link(listing: Listing, key: str, text: str) -> str:
    url = maps_url(listing, key)
    if url is None:
        return html.escape(text)
    label = html.escape(DESTINATIONS[key][0])
    return f'<a class="maps-link" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer" title="Open Google Maps directions to {label}">{html.escape(text)}</a>'


def bedroom_bath_fit(listing: Listing) -> bool:
    return (listing.bedrooms == 3 and listing.bathrooms >= 2) or (listing.bedrooms >= 4 and listing.bathrooms >= 2)


def required_failures(listing: Listing) -> list[str]:
    failures = []
    if not 3000 <= listing.rent <= 5000:
        failures.append("rent outside $3,000-$5,000")
    if listing.sqft < 1200:
        failures.append("under 1,200 sqft")
    if not bedroom_bath_fit(listing):
        failures.append("does not meet 3bd/2ba or 4bd+/2ba")
    if listing.home_type.lower() not in ALLOWED_HOME_TYPES:
        failures.append("not single-family house or townhome")
    if listing.city.lower() not in PREFERRED_CITIES | ACCEPTABLE_CITIES:
        failures.append("outside target corridor")
    return failures


def score_listing(listing: Listing) -> tuple[int, list[str]]:
    score = 0
    failures = required_failures(listing)
    reasons = list(failures)
    if failures:
        score -= len(failures) * 20
    else:
        score += 60
        reasons.append("meets all hard filters")

    city = listing.city.lower()
    if city in PREFERRED_CITIES:
        score += 20
        reasons.append("preferred city")
    elif city in ACCEPTABLE_CITIES:
        score += 8
        reasons.append("acceptable corridor city")

    listing_coords = coords(listing)
    if listing_coords is not None:
        corridor_distance = haversine_miles(listing_coords, CORRIDOR_MIDPOINT)
        if corridor_distance <= 8:
            score += 12
            reasons.append(f"near Fremont/Sunnyvale midpoint ({corridor_distance:.1f} mi)")
        elif corridor_distance <= 15:
            score += 6
            reasons.append(f"reasonable corridor distance ({corridor_distance:.1f} mi)")
        for key, label, max_miles, bonus in [
            ("sjsu", "SJSU", 12, 3),
            ("villa_sport", "VillaSport", 8, 4),
            ("lam_research", "Lam Research", 15, 4),
            ("northrop_grumman", "Northrop Grumman", 15, 4),
        ]:
            distance = destination_distance(listing, key)
            if distance is not None and distance <= max_miles:
                score += bonus
                reasons.append(f"close to {label} ({distance:.1f} mi)")

    if listing.parks_nearby >= 2:
        score += 8
        reasons.append("multiple nearby parks")
    elif listing.parks_nearby == 1:
        score += 4
        reasons.append("nearby park")
    if listing.rent <= 4200:
        score += 5
        reasons.append("stronger rent value")
    if listing.sqft >= 1600:
        score += 5
        reasons.append("larger floor plan")
    return score, reasons


def verdict(score: int, failures: list[str]) -> str:
    if failures:
        return "Reject"
    if score >= 90:
        return "Top fit"
    if score >= 75:
        return "Worth touring"
    return "Maybe"


def ranked_listings(listings: list[Listing]) -> list[tuple[int, str, Listing, list[str]]]:
    rows = []
    for listing in listings:
        score, reasons = score_listing(listing)
        rows.append((score, verdict(score, required_failures(listing)), listing, reasons))
    return sorted(rows, key=lambda item: item[0], reverse=True)


def markdown_report(listings: list[Listing]) -> str:
    lines = [
        "# Zillow Rental Screening Report",
        "",
        "Criteria: $3,000-$5,000 rent, at least 1,200 sqft, 3bd/2ba or 4bd+/2ba, single-family house or townhome, optimized between Fremont and Sunnyvale with San Jose or Milpitas preferred. Nearby parks add bonus points.",
        "",
        "| Rank | Verdict | Score | Rent | Beds/Baths | Sqft | Type | City | Address | SJSU | VillaSport | Villa Commute | Lam Research | Northrop Drive | Notes |",
        "|---:|---|---:|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for rank, (score, item_verdict, listing, reasons) in enumerate(ranked_listings(listings), start=1):
        address = f"[{listing.address}]({listing.url})" if listing.url else listing.address
        sjsu = destination_distance(listing, "sjsu")
        villa = destination_distance(listing, "villa_sport")
        lam = destination_distance(listing, "lam_research")
        northrop = destination_distance(listing, "northrop_grumman")
        lines.append(
            f"| {rank} | {item_verdict} | {score} | ${listing.rent:,} | {listing.bedrooms}/{listing.bathrooms:g} | {listing.sqft:,} | {listing.home_type} | {listing.city} | {address} | {md_link(listing, 'sjsu', fmt_distance(sjsu))} | {md_link(listing, 'villa_sport', fmt_distance(villa))} | {fmt_commute(villa_commute_minutes(villa))} | {md_link(listing, 'lam_research', fmt_distance(lam))} | {md_link(listing, 'northrop_grumman', fmt_drive(northrop))} | {'; '.join(reasons)} |"
        )
    lines.extend([
        "",
        "Distance values are straight-line estimates except Northrop Drive, which is a rough driving-distance estimate. VillaSport commute is a rough driving estimate, not live traffic.",
        "Click destination distances to open Google Maps driving directions.",
    ])
    return "\n".join(lines) + "\n"


def html_report(listings: list[Listing]) -> str:
    rows = []
    for rank, (score, item_verdict, listing, reasons) in enumerate(ranked_listings(listings), start=1):
        sjsu = destination_distance(listing, "sjsu")
        villa = destination_distance(listing, "villa_sport")
        lam = destination_distance(listing, "lam_research")
        northrop = destination_distance(listing, "northrop_grumman")
        zillow_link = f'<a class="listing-link" href="{html.escape(listing.url, quote=True)}" target="_blank" rel="noopener noreferrer">Open Zillow</a>' if listing.url else "No link"
        rows.append(
            "<tr>"
            f"<td>{rank}</td><td><span class='verdict {item_verdict.lower().replace(' ', '-')}'>{item_verdict}</span></td><td>{score}</td>"
            f"<td>${listing.rent:,}</td><td>{listing.bedrooms}/{listing.bathrooms:g}</td><td>{listing.sqft:,}</td><td>{html.escape(listing.home_type)}</td><td>{html.escape(listing.city)}</td><td>{html.escape(listing.address)}</td><td>{zillow_link}</td>"
            f"<td>{html_link(listing, 'sjsu', fmt_distance(sjsu))}</td><td>{html_link(listing, 'villa_sport', fmt_distance(villa))}</td><td>{fmt_commute(villa_commute_minutes(villa))}</td><td>{html_link(listing, 'lam_research', fmt_distance(lam))}</td><td>{html_link(listing, 'northrop_grumman', fmt_drive(northrop))}</td><td>{html.escape('; '.join(reasons))}</td></tr>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Zillow Rental Screening Report</title><style>
:root{{color-scheme:light;font-family:Arial,Helvetica,sans-serif;background:#f5f7f8;color:#1f2933}}body{{margin:0;padding:32px}}main{{max-width:1280px;margin:0 auto}}h1{{margin:0 0 8px;font-size:30px;letter-spacing:0}}.summary{{margin:0 0 24px;max-width:940px;color:#52606d;line-height:1.5}}table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d9e2ec}}th,td{{padding:12px;border-bottom:1px solid #d9e2ec;text-align:left;vertical-align:top;font-size:14px}}th{{background:#e6f0f2;color:#243b53;font-weight:700}}.verdict{{display:inline-block;min-width:86px;padding:4px 8px;border-radius:6px;text-align:center;font-weight:700;white-space:nowrap}}.top-fit{{background:#d8f3dc;color:#1b5e20}}.worth-touring{{background:#fff3bf;color:#6c4f00}}.maybe{{background:#dbeafe;color:#1e3a8a}}.reject{{background:#ffd7d7;color:#8a1f1f}}.listing-link,.maps-link{{color:#0b6b75;font-weight:700;white-space:nowrap}}@media(max-width:900px){{body{{padding:16px}}table{{display:block;overflow-x:auto}}th,td{{min-width:110px}}}}
</style></head><body><main><h1>Zillow Rental Screening Report</h1><p class="summary">Criteria: $3,000-$5,000 rent, at least 1,200 sqft, 3bd/2ba or 4bd+/2ba, single-family house or townhome, optimized between Fremont and Sunnyvale with San Jose or Milpitas preferred. Destination links open Google Maps driving directions.</p><table><thead><tr><th>Rank</th><th>Verdict</th><th>Score</th><th>Rent</th><th>Beds/Baths</th><th>Sqft</th><th>Type</th><th>City</th><th>Address</th><th>Zillow</th><th>SJSU</th><th>VillaSport</th><th>Villa Commute</th><th>Lam Research</th><th>Northrop Drive</th><th>Notes</th></tr></thead><tbody>{''.join(rows)}</tbody></table><p class="summary">Distance values are straight-line estimates except Northrop Drive, which is a rough driving-distance estimate. VillaSport commute is a rough driving estimate, not live traffic.</p></main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen Zillow rental listings from CSV.")
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("zillow_screening_report.html"))
    args = parser.parse_args()
    listings = load_listings(args.input_csv)
    report = html_report(listings) if args.output.suffix.lower() == ".html" else markdown_report(listings)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
