import time
import re
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class GoogleMapsScraper:
    def __init__(self):
        self.base_url = "https://www.google.com/maps/search/"
    
    def scrape(self, keyword, location, max_results=100, callback=None):
        """Main scraping function using Playwright"""
        businesses = []
        search_query = f"{keyword} in {location}"
        
        if callback:
            callback({
                'type': 'info',
                'message': f'Starting search: {search_query}',
                'count': 0
            })
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )
            
            page = context.new_page()
            
            try:
                # Navigate to Google Maps search
                search_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
                page.goto(search_url, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(3000)
                
                # Handle consent dialog if present
                try:
                    accept_btn = page.locator('button:has-text("Accept all"), button:has-text("Reject all"), form:has(button) button').first
                    if accept_btn.is_visible(timeout=3000):
                        accept_btn.click()
                        page.wait_for_timeout(2000)
                except:
                    pass
                
                # Scroll and collect listings
                listings_collected = 0
                max_scrolls = max_results // 5 + 20
                
                for scroll_num in range(max_scrolls):
                    if listings_collected >= max_results:
                        break
                    
                    # Find all listing elements
                    listings = page.locator('div[role="feed"] > div > div[jsaction]').all()
                    
                    for listing in listings:
                        if listings_collected >= max_results:
                            break
                        
                        try:
                            # Click on listing to get details
                            listing.click()
                            page.wait_for_timeout(2000)
                            
                            # Extract business data from detail panel
                            biz_data = self._extract_business_details(page)
                            
                            if biz_data and biz_data.get('name'):
                                # Check for duplicates
                                if not any(b.get('name') == biz_data['name'] for b in businesses):
                                    businesses.append(biz_data)
                                    listings_collected += 1
                                    
                                    if callback:
                                        callback({
                                            'type': 'business_found',
                                            'message': f'Found: {biz_data["name"]}',
                                            'business': biz_data,
                                            'count': listings_collected,
                                            'total': max_results
                                        })
                        except Exception as e:
                            print(f"Error extracting listing: {e}")
                            continue
                    
                    # Scroll the feed to load more
                    try:
                        feed = page.locator('div[role="feed"]')
                        feed.evaluate("el => el.scrollBy(0, 1000)")
                        page.wait_for_timeout(2000)
                        
                        # Check if end of results
                        end_text = page.locator('span:has-text("end of list"), span:has-text("You\'ve reached")').first
                        if end_text.is_visible(timeout=1000):
                            break
                    except:
                        break
                
                if callback:
                    callback({
                        'type': 'info',
                        'message': f'Scraping complete. Found {len(businesses)} businesses.',
                        'count': len(businesses)
                    })
                    
            except Exception as e:
                if callback:
                    callback({
                        'type': 'error',
                        'message': f'Scraping error: {str(e)}'
                    })
                raise e
            finally:
                browser.close()
        
        return businesses
    
    def _extract_business_details(self, page):
        """Extract detailed information from a business listing"""
        data = {}
        
        try:
            # Business Name
            name_el = page.locator('h1.DUwDvf, h1[class*="fontHeadlineLarge"]').first
            if name_el.is_visible(timeout=2000):
                data['name'] = name_el.inner_text().strip()
            
            # Rating
            rating_el = page.locator('div.F7nice span[aria-hidden="true"]').first
            if rating_el.is_visible(timeout=1000):
                try:
                    data['rating'] = float(rating_el.inner_text().strip())
                except:
                    pass
            
            # Review Count
            review_el = page.locator('div.F7nice span[aria-label*="reviews"]').first
            if review_el.is_visible(timeout=1000):
                review_text = review_el.get_attribute('aria-label') or ''
                numbers = re.findall(r'[\d,]+', review_text)
                if numbers:
                    data['review_count'] = int(numbers[0].replace(',', ''))
            
            # Business Type
            type_el = page.locator('button.DkEaL, span.YhemCb, div[jsaction*="category"]').first
            if type_el.is_visible(timeout=1000):
                data['type'] = type_el.inner_text().strip()
            
            # Address
            addr_el = page.locator('button[data-item-id="address"] div.rogA2c, [data-tooltip="Copy address"] div').first
            if addr_el.is_visible(timeout=1000):
                data['address'] = addr_el.inner_text().strip()
            
            # Phone
            phone_el = page.locator('button[data-tooltip="Copy phone number"] div.rogA2c, [data-item-id*="phone"] div').first
            if phone_el.is_visible(timeout=1000):
                data['phone'] = phone_el.inner_text().strip()
            
            # Website
            website_el = page.locator('a[data-item-id="authority"] div.rogA2c, a[data-tooltip="Open website"]').first
            if website_el.is_visible(timeout=1000):
                data['website'] = website_el.inner_text().strip()
            
            # Hours
            hours_el = page.locator('div[aria-label*="Hours"], div.t39EBf').first
            if hours_el.is_visible(timeout=1000):
                data['hours'] = hours_el.inner_text().strip()
                data['status'] = 'Open' if 'Open' in data['hours'] else 'Closed'
            
            # Price Level
            price_el = page.locator('span.mgr77e').first
            if price_el.is_visible(timeout=1000):
                data['price_level'] = price_el.inner_text().strip()
            
            # Maps URL
            try:
                current_url = page.url
                if '/maps/place/' in current_url:
                    data['maps_url'] = current_url
            except:
                pass
            
            # Place ID from URL
            try:
                url = page.url
                place_match = re.search(r'place/([^/]+)/|ChIJ[A-Za-z0-9_-]+', url)
                if place_match:
                    data['place_id'] = place_match.group(0)
                else:
                    data['place_id'] = data.get('name', '') + '_' + data.get('address', '')[:20]
            except:
                data['place_id'] = str(time.time())
            
            # Claimed status (has owner response)
            try:
                claimed_el = page.locator('[aria-label*="claimed"], div.m6QErb span:has-text("owner")').first
                data['is_claimed'] = claimed_el.is_visible(timeout=500)
            except:
                data['is_claimed'] = False
            
            # Thumbnail
            try:
                img_el = page.locator('img.t0eI8b, div.RZ66Rb img').first
                if img_el.is_visible(timeout=500):
                    data['thumbnail'] = img_el.get_attribute('src', timeout=500) or ''
            except:
                data['thumbnail'] = ''
            
            # Latitude/Longitude from URL
            try:
                url = page.url
                coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
                if coords_match:
                    data['lat'] = float(coords_match.group(1))
                    data['lng'] = float(coords_match.group(2))
            except:
                pass
                
        except Exception as e:
            print(f"Error in detail extraction: {e}")
        
        return data
