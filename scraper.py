import json
import asyncio
import time
import requests
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os
from datetime import datetime
import re

class ECIScraper:
    def __init__(self):
        self.base_url = "https://results.eci.gov.in/ResultAcGenNov2025/index.htm"
        self.json_url = "https://results.eci.gov.in/ResultAcGenNov2025/election-json-S04-live.json"
        self.statewise_base = "https://results.eci.gov.in/ResultAcGenNov2025/statewiseS04" 
        self.snapshot_dir = "snapshots"
        self.local_file = "live_summary.json"
        
        if not os.path.exists(self.snapshot_dir):
            os.makedirs(self.snapshot_dir)

    def fetch_live_data_playwright(self):
        """Use Playwright to get data and update the local file."""
        print("Starting Playwright stealth fetch...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # Navigate to index
                page.goto(self.base_url, wait_until="networkidle")
                
                # Extract Summary JSON
                response = page.goto(self.json_url)
                summary = []
                if response and response.status == 200:
                    data = response.json()
                    table_data = data.get("S04", {}).get("tableData", [])
                    for entry in table_data:
                        if len(entry) >= 4:
                            summary.append({
                                "partyName": entry[0],
                                "won": int(entry[1]),
                                "leading": int(entry[2]),
                                "total": int(entry[3])
                            })
                
                # Extract Margins (First few pages for speed)
                margins = []
                for i in range(1, 4):
                    try:
                        page.goto(f"{self.statewise_base}{i}.htm", wait_until="domcontentloaded")
                        content = page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        table = soup.find('table', class_='table')
                        if table:
                            rows = table.find_all('tr')[1:]
                            for row in rows:
                                cols = row.find_all('td')
                                if len(cols) >= 5:
                                    margins.append({
                                        "constituency": cols[0].text.strip(),
                                        "winner": cols[1].text.strip(),
                                        "party": cols[2].text.strip(),
                                        "margin": cols[4].text.strip()
                                    })
                    except Exception as e:
                        print(f"Error on margin page {i}: {e}")
                
                browser.close()
                
                if summary:
                    final_data = {
                        "partyWise": summary,
                        "detailed": margins,
                        "timestamp": datetime.now().isoformat()
                    }
                    with open(self.local_file, 'w') as f:
                        json.dump(final_data, f, indent=4)
                    return final_data
                    
        except Exception as e:
            print(f"Playwright fetch failed: {e}")
        return None

    def save_snapshot(self, data):
        """Save a snapshot of the current data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.snapshot_dir}/election_data_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        return filename

    def get_full_data(self):
        """Try local file first, otherwise trigger a background refresh."""
        # Check if local file is fresh (e.g., < 10 mins)
        if os.path.exists(self.local_file):
            stats = os.stat(self.local_file)
            age_mins = (time.time() - stats.st_mtime) / 60
            if age_mins < 10:
                with open(self.local_file, 'r') as f:
                    data = json.load(f)
                    self.save_snapshot(data) # Always save snapshot for trends
                    return data

        # If missing or stale, trigger fetch
        # Note: This is blocking in streamlit for the first time
        data = self.fetch_live_data_playwright()
        if data:
            self.save_snapshot(data)
            return data
        
        # Final fallback to stale data if fetch failed
        if os.path.exists(self.local_file):
            with open(self.local_file, 'r') as f:
                return json.load(f)
                
        return None

if __name__ == "__main__":
    scraper = ECIScraper()
    scraper.fetch_live_data_playwright()
