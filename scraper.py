from playwright.sync_api import sync_playwright
import pandas as pd
import time

def scrape_google_maps(niche, location, max_results=20):
    results = []
    search_query = f"{niche} in {location}"
    url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"

    with sync_playwright() as p:
        # Launch browser (headless=True for background running)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(3000) # Wait for page to load

        # Scroll and load results
        # Note: Google Maps uses dynamic scrolling. This is a basic scrolling logic.
        for _ in range(max_results // 5):
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(2000)

        # Extract data
        listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
        
        count = 0
        for listing in listings:
            if count >= max_results:
                break
            try:
                # Click on the listing to get details
                listing.click()
                page.wait_for_timeout(2000)

                name = page.locator('h1').first.inner_text() if page.locator('h1').count() > 0 else "N/A"
                
                # Extract Rating and Reviews
                rating_text = page.locator('div[aria-label*="stars"]').first.get_attribute('aria-label') if page.locator('div[aria-label*="stars"]').count() > 0 else "0 stars 0 Reviews"
                
                rating = 0.0
                reviews = 0
                if rating_text and "stars" in rating_text:
                    parts = rating_text.split(' ')
                    rating = float(parts[0])
                    reviews = int(parts[2].replace(',', '')) if len(parts) > 2 else 0

                # Extract Phone and Website
                phone = page.locator('button[data-tooltip*="Copy phone number"]').first.inner_text() if page.locator('button[data-tooltip*="Copy phone number"]').count() > 0 else "N/A"
                website = page.locator('a[data-tooltip*="Open website"]').first.get_attribute('href') if page.locator('a[data-tooltip*="Open website"]').count() > 0 else "N/A"

                results.append({
                    "Name": name,
                    "Rating": rating,
                    "Reviews": reviews,
                    "Phone": phone,
                    "Website": website
                })
                count += 1
            except Exception as e:
                print(f"Error scraping a listing: {e}")
                continue

        browser.close()
    
    return pd.DataFrame(results)
