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

The hosted page starts empty and does not include placeholder addresses. Paste real listing CSV data into the page to generate the report. The HTML report uses a stacked mobile layout in narrow browsers, so it is easier to scan in Mobile Chrome.

## How To Use

1. Copy Zillow candidate listings into a CSV using the columns in `sample_listings.csv`.
2. Put each listing's exact Zillow URL in the `url` column.
3. Put the first Zillow photo URL in the `image_url` column to show a listing picture.
4. Include real `lat` and `lon` values for each listing so distance and Google Maps links work.
5. Paste the CSV into the hosted page and click `Generate report`, or run:

```powershell
python .\screen_zillow_rentals.py .\sample_listings.csv -o .\index.html
```

If you still want Markdown, use a `.md` output filename:

```powershell
python .\screen_zillow_rentals.py .\sample_listings.csv -o .\zillow_screening_report.md
```

## Notes

The first version avoids direct Zillow scraping. That keeps the workflow simpler and less brittle while still automating the actual screening and ranking. You can feed it listings from Zillow saved-search alerts, copied rows, or another compliant listing source.

Latitude and longitude are optional for the Python report, but the hosted browser report requires them for rows to be scored. They enable the SJSU, VillaSport, Lam Research, and Northrop destination columns. VillaSport commute and Northrop Drive are rough estimates, not live traffic.

Some Zillow image URLs may block hotlinking. If a photo does not render, open the listing and use a directly accessible image URL.

Click destination distances in the generated report to open Google Maps driving directions from the listing coordinates.
