#!/usr/bin/env python3
"""Generate a personal Zillow rental screening report from listing CSV rows."""

from __future__ import annotations

import argparse
import csv
import html
import math
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

TARGET_CITIES = {"san jose", "fremont", "milpitas"}
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
CRITERIA = "$3,000-$5,000 rent, 1,200+ sqft, 3bd/2ba or 4bd+/2ba, San Jose/Fremont/Milpitas, Zillow listing, single-family house or townhome."


@dataclass(frozen=True)
class Listing:
    address: str
    city: str
    url: str
    image_url: str
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
                image_url=(row.get("image_url") or row.get("image") or row.get("photo_url") or "").strip(),
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


def photo_html(listing: Listing) -> str:
    if not listing.image_url.startswith(("http://", "https://")):
        return '<span class="no-photo">No photo</span>'
    return f'<img class="photo" src="{html.escape(listing.image_url, quote=True)}" alt="{html.escape(listing.address)}" loading="lazy" referrerpolicy="no-referrer">'


def bedroom_bath_fit(listing: Listing) -> bool:
    return (listing.bedrooms == 3 and listing.bathrooms >= 2) or (listing.bedrooms >= 4 and listing.bathrooms >= 2)


def is_zillow_url(url: str) -> bool:
    return url.startswith("https://www.zillow.com/") or url.startswith("http://www.zillow.com/") or url.startswith("https://zillow.com/") or url.startswith("http://zillow.com/")


def required_failures(listing: Listing) -> list[str]:
    failures = []
    if not is_zillow_url(listing.url):
        failures.append("not a Zillow listing URL")
    if listing.city.lower() not in TARGET_CITIES:
        failures.append("outside San Jose/Fremont/Milpitas")
    if not 3000 <= listing.rent <= 5000:
        failures.append("rent outside $3,000-$5,000")
    if listing.sqft < 1200:
        failures.append("under 1,200 sqft")
    if not bedroom_bath_fit(listing):
        failures.append("does not meet 3bd/2ba or 4bd+/2ba")
    if listing.home_type.lower() not in ALLOWED_HOME_TYPES:
        failures.append("not single-family house or townhome")
    return failures


def score_listing(listing: Listing) -> tuple[int, list[str]]:
    failures = required_failures(listing)
    score = len(failures) * -20 if failures else 60
    reasons = list(failures) if failures else ["meets all hard filters"]
    city = listing.city.lower()
    if city == "san jose":
        score += 16; reasons.append("target city: San Jose")
    elif city == "milpitas":
        score += 14; reasons.append("target city: Milpitas")
    elif city == "fremont":
        score += 12; reasons.append("target city: Fremont")
    listing_coords = coords(listing)
    if listing_coords is not None:
        corridor_distance = haversine_miles(listing_coords, CORRIDOR_MIDPOINT)
        if corridor_distance <= 8:
            score += 12; reasons.append(f"near Fremont/Sunnyvale midpoint ({corridor_distance:.1f} mi)")
        elif corridor_distance <= 15:
            score += 6; reasons.append(f"reasonable corridor distance ({corridor_distance:.1f} mi)")
        for key, label, max_miles, bonus in [("sjsu", "SJSU", 12, 3), ("villa_sport", "VillaSport", 8, 4), ("lam_research", "Lam Research", 15, 4), ("northrop_grumman", "Northrop Grumman", 15, 4)]:
            distance = destination_distance(listing, key)
            if distance is not None and distance <= max_miles:
                score += bonus; reasons.append(f"close to {label} ({distance:.1f} mi)")
    if listing.parks_nearby >= 2:
        score += 8; reasons.append("multiple nearby parks")
    elif listing.parks_nearby == 1:
        score += 4; reasons.append("nearby park")
    if listing.rent <= 4200:
        score += 5; reasons.append("stronger rent value")
    if listing.sqft >= 1600:
        score += 5; reasons.append("larger floor plan")
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
    lines = ["# Jon's Zillow Rental Screening Report", "", f"Default criteria: {CRITERIA}", "", "| Rank | Photo | Verdict | Score | Rent | Beds/Baths | Sqft | Type | City | Address | SJSU | VillaSport | Villa Commute | Lam Research | Northrop Drive | Notes |", "|---:|---|---|---:|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|---|"]
    for rank, (score, item_verdict, listing, reasons) in enumerate(ranked_listings(listings), start=1):
        address = f"[{listing.address}]({listing.url})" if listing.url else listing.address
        photo = f"![{listing.address}]({listing.image_url})" if listing.image_url else ""
        sjsu = destination_distance(listing, "sjsu"); villa = destination_distance(listing, "villa_sport"); lam = destination_distance(listing, "lam_research"); northrop = destination_distance(listing, "northrop_grumman")
        lines.append(f"| {rank} | {photo} | {item_verdict} | {score} | ${listing.rent:,} | {listing.bedrooms}/{listing.bathrooms:g} | {listing.sqft:,} | {listing.home_type} | {listing.city} | {address} | {md_link(listing, 'sjsu', fmt_distance(sjsu))} | {md_link(listing, 'villa_sport', fmt_distance(villa))} | {fmt_commute(villa_commute_minutes(villa))} | {md_link(listing, 'lam_research', fmt_distance(lam))} | {md_link(listing, 'northrop_grumman', fmt_drive(northrop))} | {'; '.join(reasons)} |")
    return "\n".join(lines) + "\n"


def html_report(listings: list[Listing]) -> str:
    rows = []
    for rank, (score, item_verdict, listing, reasons) in enumerate(ranked_listings(listings), start=1):
        sjsu = destination_distance(listing, "sjsu"); villa = destination_distance(listing, "villa_sport"); lam = destination_distance(listing, "lam_research"); northrop = destination_distance(listing, "northrop_grumman")
        zillow_link = f'<a class="listing-link" href="{html.escape(listing.url, quote=True)}" target="_blank" rel="noopener noreferrer">Open Zillow</a>' if listing.url else "No link"
        rows.append("<tr>" + f"<td>{rank}</td><td>{photo_html(listing)}</td><td><span class='verdict {item_verdict.lower().replace(' ', '-')}'>{item_verdict}</span></td><td>{score}</td><td>${listing.rent:,}</td><td>{listing.bedrooms}/{listing.bathrooms:g}</td><td>{listing.sqft:,}</td><td>{html.escape(listing.home_type)}</td><td>{html.escape(listing.city)}</td><td>{html.escape(listing.address)}</td><td>{zillow_link}</td><td>{html_link(listing, 'sjsu', fmt_distance(sjsu))}</td><td>{html_link(listing, 'villa_sport', fmt_distance(villa))}</td><td>{fmt_commute(villa_commute_minutes(villa))}</td><td>{html_link(listing, 'lam_research', fmt_distance(lam))}</td><td>{html_link(listing, 'northrop_grumman', fmt_drive(northrop))}</td><td>{html.escape('; '.join(reasons))}</td></tr>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Jon's Zillow Rental Screening Report</title><style>:root{{font-family:Arial,Helvetica,sans-serif;background:#f5f7f8;color:#1f2933}}body{{margin:0;padding:32px}}main{{max-width:1280px;margin:0 auto}}table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d9e2ec}}th,td{{padding:12px;border-bottom:1px solid #d9e2ec;text-align:left;vertical-align:top;font-size:14px}}th{{background:#e6f0f2}}.photo{{display:block;width:132px;aspect-ratio:4/3;object-fit:cover;border-radius:8px;border:1px solid #d9e2ec}}.verdict{{display:inline-block;min-width:86px;padding:4px 8px;border-radius:6px;text-align:center;font-weight:700}}.top-fit{{background:#d8f3dc;color:#1b5e20}}.worth-touring{{background:#fff3bf;color:#6c4f00}}.maybe{{background:#dbeafe;color:#1e3a8a}}.reject{{background:#ffd7d7;color:#8a1f1f}}.listing-link,.maps-link{{color:#0b6b75;font-weight:700}}</style></head><body><main><h1>Jon's Zillow Rental Screening Report</h1><p>Default criteria: {html.escape(CRITERIA)}</p><table><thead><tr><th>Rank</th><th>Photo</th><th>Verdict</th><th>Score</th><th>Rent</th><th>Beds/Baths</th><th>Sqft</th><th>Type</th><th>City</th><th>Address</th><th>Zillow</th><th>SJSU</th><th>VillaSport</th><th>Villa Commute</th><th>Lam Research</th><th>Northrop Drive</th><th>Notes</th></tr></thead><tbody>{''.join(rows)}</tbody></table></main></body></html>"""


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
