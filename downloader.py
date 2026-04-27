import os
import time
from playwright.sync_api import sync_playwright

class ECIDownloader:
    def __init__(self, download_dir="data"):
        self.url = "https://www.eci.gov.in/general-election-to-loksabha-2024-statistical-reports"
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            
        # Specific reports requested by user
        self.report_numbers = [
            "4", "9", "10", "11", "12", "13", 
            "17", "18", "20", "21", "22", 
            "23", "24", "25", "26", 
            "32", "33"
        ]

    def download_reports(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=['--start-maximized'])
            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            print(f"Navigating to {self.url}...")
            page.goto(self.url, wait_until="domcontentloaded")
            time.sleep(3) # Wait for page rendering
            
            # CRITICAL: Handle the "Agreement for Downloading" modal first
            try:
                print("Checking for Agreement modal...")
                agree_button = page.locator("button:has-text('I agree'), a:has-text('I agree')").first
                if agree_button.count() > 0:
                    print("Dismissing Agreement modal...")
                    agree_button.click()
                    time.sleep(2) # Wait for modal to clear
            except Exception as modal_e:
                print(f"No initial modal detected or failed to dismiss: {modal_e}")

            # Now iterate through the reports
            for num in self.report_numbers:
                try:
                    # ECI uses <li class="statistical-reports"> containing <h4 class="statistical-heading">32.Title</h4>
                    target_text = f"{num}."
                    
                    # Direct XPath to find the li container that has the appropriate h4/h5 title
                    container_xpath = f"//li[contains(@class, 'statistical-reports') and .//*[contains(text(), '{target_text}')]]"
                    row_container = page.locator(container_xpath).first
                    
                    if row_container.count() > 0:
                        print(f"Found container for Report {num}")
                        # The download trigger is not an <a> tag, it's an <i> icon tag with JS listener
                        xls_trigger = row_container.locator("i.fa-file-excel, i[title*='XLSX']").first
                        
                        if xls_trigger.count() > 0:
                            print(f"Clicking XLS icon for Report {num}...")
                            # Click the icon
                            xls_trigger.click()
                            
                            # Wait for the modal and click 'I agree'
                            try:
                                agree_button = page.locator("button:has-text('I agree'), a:has-text('I agree')").first
                                agree_button.wait_for(state="visible", timeout=6000)
                                
                                print(f"Accepting terms for Report {num}...")
                                with page.expect_download() as download_info:
                                    agree_button.click()
                                
                                download = download_info.value
                                path = os.path.join(self.download_dir, f"Report_{num}.xlsx")
                                download.save_as(path)
                                print(f"✅ Downloaded Report {num}")
                                
                                # Wait for modal to clear before next iteration
                                time.sleep(1)
                            except Exception as modal_e:
                                print(f"Modal handling failed for Report {num}: {modal_e}")
                                page.keyboard.press("Escape")
                        else:
                            print(f"XLS icon not found inside container for Report {num}")
                    else:
                        print(f"Container matching '{target_text}' not found for Report {num}")
                        
                except Exception as e:
                    print(f"Error processing Report {num}: {e}")
                    if "target closed" in str(e).lower(): break

            browser.close()

if __name__ == "__main__":
    downloader = ECIDownloader()
    downloader.download_reports()
