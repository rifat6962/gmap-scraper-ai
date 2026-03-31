from flask import Flask, request, send_file, render_template_string
import csv
from playwright.sync_api import sync_playwright

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head><title>Google Map Direct Scraper</title></head>
<body style="font-family: Arial; text-align: center; margin-top: 50px;">
    <h2>Google Map Lead Scraper (No API)</h2>
    <form action="/scrape" method="POST">
        <input type="text" name="keyword" placeholder="Keyword (e.g. Hospital)" required style="padding: 10px; margin: 5px;"><br>
        <input type="text" name="location" placeholder="Location (e.g. Dhaka)" required style="padding: 10px; margin: 5px;"><br>
        <button type="submit" style="padding: 10px 20px; background: red; color: white; border: none; cursor: pointer;">Scrape Map & Download CSV</button>
    </form>
    <p style="color:gray; font-size:14px; margin-top:20px;">Wait 1-2 minutes after clicking. Direct scraping takes time.</p>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/scrape', methods=['POST'])
def scrape():
    keyword = request.form['keyword']
    location = request.form['location']
    query = f"{keyword} in {location}"
    
    leads = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
            page.goto(search_url)
            page.wait_for_timeout(5000)
            
            elements = page.locator('a[href*="/maps/place/"]').all()
            
            for el in elements:
                name = el.get_attribute('aria-label')
                link = el.get_attribute('href')
                if name:
                    leads.append({
                        'Business Name': name,
                        'Google Map Link': link,
                        'Keyword Info': query
                    })
            
            browser.close()
            
    except Exception as e:
        return f"Scraping failed! Error: {str(e)}"
        
    if not leads:
        return "Kono lead pawa jayni! Hoyto Render er IP Google block koreche."

    # Pandas er bodole Python er built-in CSV use korlam (Fast and lightweight)
    csv_filename = 'leads_scraped.csv'
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        # Same link jate bar bar na ashe tai duplicate bad dicchi
        unique_leads = [dict(t) for t in {tuple(d.items()) for d in leads}]
        
        writer = csv.DictWriter(file, fieldnames=['Business Name', 'Google Map Link', 'Keyword Info'])
        writer.writeheader()
        writer.writerows(unique_leads)
    
    return send_file(csv_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
