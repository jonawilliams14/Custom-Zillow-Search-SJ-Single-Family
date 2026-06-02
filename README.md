# Jon's Zillow Rental Screening Report

This repository hosts my personal rental screener for my Bay Area move. It is intentionally configured for my situation, not as a generic rental-search app.

## Default Hard Requirements

Every report uses these defaults:

- Source: Zillow rental listing URL.
- Cities: San Jose, Fremont, or Milpitas, CA.
- Rent: $3,000 to $5,000.
- Size: at least 1,200 sqft.
- Layout: 3 bed / 2 bath or 4+ bed / 2+ bath.
- Type: single-family house or townhome.

## Bonus Criteria

- Nearby parks.
- Stronger value below $4,200.
- Larger floor plans at or above 1,600 sqft.
- Proximity to San Jose State University.
- Distance and rough commute to VillaSport San Jose.
- Distance to Lam Research Fremont.
- Rough driving distance to Northrop Grumman Sunnyvale.

## Hosted Report

Open the GitHub Pages report here:

https://jonawilliams14.github.io/Custom-Zillow-Search-SJ-Single-Family/

The hosted page automatically loads `sample_listings.csv` every time the browser page refreshes. It uses a cache-busting request so the page should pull the latest committed CSV from the repo instead of relying on old browser data.

To update the report, edit `sample_listings.csv` with real Zillow listing rows, commit the CSV change, and refresh the GitHub Pages page. If `sample_listings.csv` only has the header row, the report will intentionally show no listings.

You can still paste temporary CSV data into the text box and press "Generate report" for a quick manual check. Refreshing the page will reload the committed `sample_listings.csv` from the repo.

The HTML report uses a stacked mobile layout in narrow browsers, so it is easier to scan in Mobile Chrome.

## CSV Columns

```csv
address,city,url,image_url,rent,bedrooms,bathrooms,sqft,home_type,lat,lon,parks_nearby,notes
```

Put each listing's exact Zillow URL in `url`, the first Zillow photo URL in `image_url`, and real coordinates in `lat`/`lon` so distance and Google Maps links work.

## Notes

This version avoids direct Zillow scraping. You can feed it listings from Zillow saved-search alerts, copied rows, or another compliant listing source.

Some Zillow image URLs may block hotlinking. If a photo does not render, open the listing and use a directly accessible image URL.
