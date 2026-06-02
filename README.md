# Zillow Rental Screening Report

This repository hosts a small CSV-in, HTML-out screening tool for rental listings.

## Your Criteria

- Rent: $3,000 to $5,000.
- Size: at least 1,200 sqft.
- Layout: 3 bed / 2 bath or 4+ bed / 2+ bath.
- Type: single-family house or townhome.
- Location: optimized between Fremont and Sunnyvale, with San Jose or Milpitas preferred.
- Bonus: nearby parks.

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

Latitude and longitude are optional, but including them improves the corridor score between Fremont and Sunnyvale.
