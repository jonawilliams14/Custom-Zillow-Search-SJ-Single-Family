# Zillow Rental Screening Report

This repository hosts a small CSV-in, HTML-out screening tool for rental listings.

## Your Criteria

- Rent: $3,000 to $5,000.
- Size: at least 1,200 sqft.
- Layout: 3 bed / 2 bath or 4+ bed / 2+ bath.
- Type: single-family house or townhome.
- Location: optimized between Fremont and Sunnyvale, with San Jose or Milpitas preferred.
- Bonus: nearby parks.
- Added destination checks:
  - San Jose State University, One Washington Square, San Jose, CA 95192.
  - VillaSport San Jose, 1167 N Capitol Ave, San Jose, CA 95132.
  - Lam Research Fremont, 4650 Cushing Pkwy, Fremont, CA 94538.
  - Northrop Grumman Sunnyvale, 401 E Hendy Ave, Sunnyvale, CA 94086.

## Hosted Report

Open `index.html` in the repository to view the current screening report. If GitHub Pages is enabled for this repository, `index.html` can be served as the project homepage.

## How To Use

1. Copy Zillow candidate listings into a CSV using the columns in `sample_listings.csv`.
   Put each listing's exact Zillow URL in the `url` column.
2. Run:

```powershell
python .\screen_zillow_rentals.py .\sample_listings.csv -o .\index.html
```

3. Commit the updated `index.html` and `sample_listings.csv`.

If you still want Markdown, use a `.md` output filename:

```powershell
python .\screen_zillow_rentals.py .\sample_listings.csv -o .\zillow_screening_report.md
```

## Notes

The first version avoids direct Zillow scraping. That keeps the workflow simpler and less brittle while still automating the actual screening and ranking. You can feed it listings from Zillow saved-search alerts, copied rows, or another compliant listing source.

Latitude and longitude are optional, but including them improves the corridor score between Fremont and Sunnyvale. They also enable the SJSU, VillaSport, Lam Research, and Northrop destination columns. VillaSport commute and Northrop Drive are rough estimates, not live traffic.

Click destination distances in the generated report to open Google Maps driving directions from the listing coordinates.
