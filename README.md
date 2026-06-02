# Jon's Rental Screening Report

This repository hosts my personal rental screener for my Bay Area move. It is intentionally configured for my situation, not as a generic rental-search app.

## Default Hard Requirements

Every generated report uses these defaults:

- Source: RentCast long-term rental listings API.
- Cities: San Jose, Fremont, or Milpitas, CA.
- Rent: $3,000 to $5,000.
- Size: at least 1,200 sqft.
- Layout: 3 bed / 2 bath or 4+ bed / 2+ bath.
- Type: single-family house or townhouse.

## Bonus Criteria

- Nearby parks, when known.
- Stronger value below $4,200.
- Larger floor plans at or above 1,600 sqft.
- Proximity to San Jose State University.
- Distance and rough commute to VillaSport San Jose.
- Distance to Lam Research Fremont.
- Rough driving distance to Northrop Grumman Sunnyvale.

## Hosted Report

Open the GitHub Pages report here:

https://jonawilliams14.github.io/Custom-Zillow-Search-SJ-Single-Family/

The hosted page automatically loads and screens `listings.json` every time the browser page refreshes. There is no report-generation button to click and no CSV upload step.

## RentCast Setup

1. Create a RentCast API key from the RentCast API dashboard.
2. In this GitHub repo, add a repository secret named `RENTCAST_API_KEY`.
3. Run the `Update RentCast listings` GitHub Actions workflow manually, or wait for its daily scheduled run.
4. Refresh the GitHub Pages report.

The workflow runs `fetch_rentcast_listings.py`, calls RentCast's long-term rental listings endpoint, writes the filtered results to `listings.json`, and commits that file back to the repository.

## Data Notes

RentCast listing responses include listing data such as address, city, coordinates, property type, bedrooms, bathrooms, square footage, listed rent, status, listed date, and MLS fields when available.

RentCast's documented rental listing schema does not include Zillow listing URLs or listing photo URLs. The report therefore links each row to a Google search for the listing address and leaves the photo field empty unless a future data source provides image URLs.

The HTML report uses a stacked mobile layout in narrow browsers, so it is easier to scan in Mobile Chrome.
