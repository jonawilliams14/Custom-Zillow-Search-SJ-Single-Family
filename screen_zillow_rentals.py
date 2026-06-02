#!/usr/bin/env python3
"""
Screen Zillow rental candidates against a Fremont/Sunnyvale commute-oriented
housing brief.

Input:  CSV with listing rows.
Output: HTML or Markdown report ranked by criteria fit.
"""

from __future__ import annotations

import argparse
import csv
import html
import math
from dataclasses import dataclass
from pathlib import Path


PREFERRED_CITIES = {"san jose", "milpitas"}
ACCEPTABLE_CITIES = {"fremont", "sunnyvale", "santa clara", "newark", "cupertino"}
ALLOWED_HOME_TYPES = {"single family", "single-family", "sfh", "house", "townhome", "townhouse"}

FREMONT = (37.5485, -121.9886)
SUNNYVALE = (37.3688, -122.0363)
CORRIDOR_MIDPOINT = ((FREMONT[0] + SUNNYVALE[0]) / 2, (FREMONT[1] + SUNNYVALE[1]) / 2)


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
    if not cleaned:
        return default
    return int(float(cleaned))


def parse_float(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    return float(value)


def load_listings(csv_path: Path) -> list[Listing]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
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
            for row in rows
        ]


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    radius_miles = 3958.8
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    inner = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius_miles * math.asin(math.sqrt(inner))


def bedroom_bath_fit(listing: Listing) -> bool:
    return (listing.bedrooms == 3 and listing.bathrooms >= 2) or (
        listing.bedrooms >= 4 and listing.bathrooms >= 2
    )


def required_passes(listing: Listing) -> list[str]:
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
    reasons = []

    failures = required_passes(listing)
    if not failures:
        score += 60
        reasons.append("meets all hard filters")
    else:
        score -= len(failures) * 20
        reasons.extend(failures)

    city = listing.city.lower()
    if city in PREFERRED_CITIES:
        score += 20
        reasons.append("preferred city")
    elif city in ACCEPTABLE_CITIES:
        score += 8
        reasons.append("acceptable corridor city")

    if listing.lat is not None and listing.lon is not None:
        distance = haversine_miles((listing.lat, listing.lon), CORRIDOR_MIDPOINT)
        if distance <= 8:
            score += 12
            reasons.append(f"near Fremont/Sunnyvale midpoint ({distance:.1f} mi)")
        elif distance <= 15:
            score += 6
            reasons.append(f"reasonable corridor distance ({distance:.1f} mi)")

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
    ranked = []
    for listing in listings:
        score, reasons = score_listing(listing)
        failures = required_passes(listing)
        ranked.append((score, verdict(score, failures), listing, reasons))
    return sorted(ranked, key=lambda item: item[0], reverse=True)


def markdown_report(listings: list[Listing]) -> str:
    ranked = ranked_listings(listings)
    lines = [
        "# Zillow Rental Screening Report",
        "",
        "Criteria: $3,000-$5,000 rent, at least 1,200 sqft, 3bd/2ba or 4bd+/2ba, "
        "single-family house or townhome, optimized between Fremont and Sunnyvale with "
        "San Jose or Milpitas preferred. Nearby parks add bonus points.",
        "",
        "| Rank | Verdict | Score | Rent | Beds/Baths | Sqft | Type | City | Address | Notes |",
        "|---:|---|---:|---:|---|---:|---|---|---|---|",
    ]

    for index, (score, item_verdict, listing, reasons) in enumerate(ranked, start=1):
        address = f"[{listing.address}]({listing.url})" if listing.url else listing.address
        reason_text = "; ".join(reasons)
        lines.append(
            f"| {index} | {item_verdict} | {score} | ${listing.rent:,} | "
            f"{listing.bedrooms}/{listing.bathrooms:g} | {listing.sqft:,} | "
            f"{listing.home_type} | {listing.city} | {address} | {reason_text} |"
        )

    lines.extend(
        [
            "",
            "## Follow-up Checklist",
            "",
            "- Confirm lease terms, pet policy, parking, utilities, HOA restrictions, and move-in costs.",
            "- Check commute time during the hours you actually travel.",
            "- Verify nearby parks by map and inspect neighborhood noise/safety in person.",
            "- Ask whether the listing is still available before scheduling a tour.",
        ]
    )
    return "\n".join(lines) + "\n"


def css_class(value: str) -> str:
    return value.lower().replace(" ", "-")


def html_report(listings: list[Listing]) -> str:
    rows = []
    for index, (score, item_verdict, listing, reasons) in enumerate(ranked_listings(listings), start=1):
        zillow_link = (
            f'<a class="listing-link" href="{html.escape(listing.url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">Open Zillow</a>'
            if listing.url
            else '<span class="missing-link">No link</span>'
        )
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f'<td><span class="verdict {css_class(item_verdict)}">{html.escape(item_verdict)}</span></td>'
            f"<td>{score}</td>"
            f"<td>${listing.rent:,}</td>"
            f"<td>{listing.bedrooms}/{listing.bathrooms:g}</td>"
            f"<td>{listing.sqft:,}</td>"
            f"<td>{html.escape(listing.home_type)}</td>"
            f"<td>{html.escape(listing.city)}</td>"
            f"<td>{html.escape(listing.address)}</td>"
            f"<td>{zillow_link}</td>"
            f"<td>{html.escape('; '.join(reasons))}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zillow Rental Screening Report</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, Helvetica, sans-serif;
      background: #f5f7f8;
      color: #1f2933;
    }}
    body {{
      margin: 0;
      padding: 32px;
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: 0;
    }}
    .summary {{
      margin: 0 0 24px;
      max-width: 880px;
      color: #52606d;
      line-height: 1.5;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
      border: 1px solid #d9e2ec;
    }}
    th, td {{
      padding: 12px;
      border-bottom: 1px solid #d9e2ec;
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      background: #e6f0f2;
      color: #243b53;
      font-weight: 700;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    .verdict {{
      display: inline-block;
      min-width: 86px;
      padding: 4px 8px;
      border-radius: 6px;
      text-align: center;
      font-weight: 700;
      white-space: nowrap;
    }}
    .top-fit {{
      background: #d8f3dc;
      color: #1b5e20;
    }}
    .worth-touring {{
      background: #fff3bf;
      color: #6c4f00;
    }}
    .maybe {{
      background: #dbeafe;
      color: #1e3a8a;
    }}
    .reject {{
      background: #ffd7d7;
      color: #8a1f1f;
    }}
    .listing-link {{
      color: #0b6b75;
      font-weight: 700;
      white-space: nowrap;
    }}
    .missing-link {{
      color: #829ab1;
      white-space: nowrap;
    }}
    .checklist {{
      margin-top: 24px;
      line-height: 1.6;
    }}
    @media (max-width: 860px) {{
      body {{
        padding: 16px;
      }}
      table {{
        display: block;
        overflow-x: auto;
      }}
      th, td {{
        min-width: 110px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Zillow Rental Screening Report</h1>
    <p class="summary">
      Criteria: $3,000-$5,000 rent, at least 1,200 sqft, 3bd/2ba or 4bd+/2ba,
      single-family house or townhome, optimized between Fremont and Sunnyvale
      with San Jose or Milpitas preferred. Nearby parks add bonus points.
    </p>
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Verdict</th>
          <th>Score</th>
          <th>Rent</th>
          <th>Beds/Baths</th>
          <th>Sqft</th>
          <th>Type</th>
          <th>City</th>
          <th>Address</th>
          <th>Zillow</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
    <section class="checklist">
      <h2>Follow-up Checklist</h2>
      <ul>
        <li>Confirm lease terms, pet policy, parking, utilities, HOA restrictions, and move-in costs.</li>
        <li>Check commute time during the hours you actually travel.</li>
        <li>Verify nearby parks by map and inspect neighborhood noise/safety in person.</li>
        <li>Ask whether the listing is still available before scheduling a tour.</li>
      </ul>
    </section>
  </main>
</body>
</html>
"""


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
