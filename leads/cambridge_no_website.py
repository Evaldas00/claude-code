#!/usr/bin/env python3
"""
Find businesses near Cambridge, UK that have no website listed on their
Google Business Profile, using the Google Places API (New) Text Search
endpoint.

Setup:
    1. Create a Google Cloud project, enable "Places API (New)", and
       create an API key: https://console.cloud.google.com/apis/credentials
    2. export GOOGLE_PLACES_API_KEY="your-key-here"
    3. pip install -r requirements.txt
    4. python leads/cambridge_no_website.py --output leads.csv

Notes:
    - Google does not expose a business owner's name through the Places
      API. For limited companies, cross-reference the business name on
      Companies House (https://find-and-update.company-information.service.gov.uk/)
      to find registered directors; sole traders have no public owner
      registry.
    - Each search/page request is billed by Google Maps Platform (Pro
      SKU, since this requests phone/website/rating fields). Check
      pricing and your project's quota before running large category
      lists: https://mapsplatform.google.com/pricing/
    - Per Google's Maps Platform Terms of Service, Place data may only be
      cached/stored for a limited time (currently 30 days) except for the
      place ID itself. Don't keep this CSV around indefinitely — re-run
      the script if you need fresh data later.
"""

import argparse
import csv
import os
import sys
import time

import requests

PLACES_API_URL = "https://places.googleapis.com/v1/places:searchText"

# Cambridge, UK city centre. Used as a location bias so queries aren't
# confused with Cambridge, MA / ON / OH / MD etc.
CAMBRIDGE_UK_LAT = 52.2053
CAMBRIDGE_UK_LNG = 0.1218
DEFAULT_RADIUS_M = 8000

DEFAULT_CATEGORIES = [
    "plumber", "electrician", "builder", "roofer", "painter and decorator",
    "gardener", "landscaper", "locksmith", "handyman", "carpet cleaner",
    "hairdresser", "barber", "beauty salon", "nail salon", "dog groomer",
    "cafe", "takeaway", "bakery", "butcher", "florist",
    "accountant", "driving instructor", "car mechanic", "taxi firm",
    "photographer", "personal trainer", "physiotherapist", "tailor",
    "dry cleaner", "pet shop",
]

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.websiteUri",
    "places.rating",
    "places.userRatingCount",
    "places.businessStatus",
    "places.googleMapsUri",
    "places.primaryTypeDisplayName",
    "nextPageToken",
])


def search_category(api_key: str, category: str, lat: float, lng: float,
                     radius_m: float, max_pages: int) -> list[dict]:
    results = []
    page_token = None

    for _ in range(max_pages):
        body = {
            "textQuery": f"{category} in Cambridge, Cambridgeshire, UK",
            "languageCode": "en",
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius_m,
                }
            },
        }
        if page_token:
            body["pageToken"] = page_token

        resp = requests.post(
            PLACES_API_URL,
            json=body,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"  [!] {category}: HTTP {resp.status_code} {resp.text[:200]}",
                  file=sys.stderr)
            break

        data = resp.json()
        results.extend(data.get("places", []))

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        # A freshly issued page token needs a moment before it's valid.
        time.sleep(2)

    return results


def find_no_website_leads(api_key: str, categories: list[str], lat: float,
                           lng: float, radius_m: float,
                           max_pages: int) -> list[dict]:
    seen_ids = set()
    leads = []

    for category in categories:
        print(f"[*] Searching: {category}")
        places = search_category(api_key, category, lat, lng, radius_m, max_pages)

        for place in places:
            place_id = place.get("id")
            if not place_id or place_id in seen_ids:
                continue
            seen_ids.add(place_id)

            if place.get("websiteUri"):
                continue  # has a website, not a lead

            leads.append({
                "name": place.get("displayName", {}).get("text", ""),
                "category": category,
                "type": place.get("primaryTypeDisplayName", {}).get("text", ""),
                "phone": place.get("internationalPhoneNumber")
                    or place.get("nationalPhoneNumber", ""),
                "address": place.get("formattedAddress", ""),
                "rating": place.get("rating", ""),
                "rating_count": place.get("userRatingCount", ""),
                "business_status": place.get("businessStatus", ""),
                "google_maps_url": place.get("googleMapsUri", ""),
            })

    return leads


def main():
    parser = argparse.ArgumentParser(
        description="Find Cambridge, UK businesses with no website on Google.")
    parser.add_argument("--output", default="leads.csv", help="CSV output path")
    parser.add_argument("--categories", help="Comma-separated category list "
                         "(overrides the built-in default list)")
    parser.add_argument("--lat", type=float, default=CAMBRIDGE_UK_LAT)
    parser.add_argument("--lng", type=float, default=CAMBRIDGE_UK_LNG)
    parser.add_argument("--radius", type=float, default=DEFAULT_RADIUS_M,
                         help="Search radius in metres around --lat/--lng")
    parser.add_argument("--max-pages", type=int, default=3,
                         help="Max result pages (20 results each) per category")
    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        print("Error: set GOOGLE_PLACES_API_KEY in your environment.",
              file=sys.stderr)
        sys.exit(1)

    categories = (
        [c.strip() for c in args.categories.split(",") if c.strip()]
        if args.categories else DEFAULT_CATEGORIES
    )

    leads = find_no_website_leads(
        api_key, categories, args.lat, args.lng, args.radius, args.max_pages)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "name", "category", "type", "phone", "address", "rating",
            "rating_count", "business_status", "google_maps_url",
        ])
        writer.writeheader()
        writer.writerows(leads)

    print(f"\n[+] Found {len(leads)} businesses with no website. "
          f"Saved to {args.output}")


if __name__ == "__main__":
    main()
