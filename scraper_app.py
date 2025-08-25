"""
USA.gov Agency Scraper - Working Desktop App
"""

import tkinter as tk
from tkinter import ttk
import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
import threading

class ScraperApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("USA.gov Agency Scraper")
        self.root.geometry("800x600")
        
        # Button
        self.button = tk.Button(self.root, text="SCRAPE USA.GOV AGENCIES", 
                                command=self.start_scraping,
                                font=("Arial", 14, "bold"),
                                bg="green", fg="white",
                                padx=20, pady=10)
        self.button.pack(pady=20)
        
        # Progress
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(fill="x", padx=20, pady=10)
        
        # Text area
        self.text = tk.Text(self.root, font=("Courier", 10))
        self.text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(self.text)
        scrollbar.pack(side="right", fill="y")
        self.text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text.yview)
        
    def log(self, msg):
        self.text.insert(tk.END, msg + "\n")
        self.text.see(tk.END)
        self.root.update()
        
    def start_scraping(self):
        self.button.config(state="disabled")
        self.progress.start()
        thread = threading.Thread(target=self.scrape)
        thread.daemon = True
        thread.start()
        
    def scrape(self):
        try:
            self.log("="*60)
            self.log("SCRAPING USA.GOV AGENCIES")
            self.log("="*60)
            self.log("\nFetching page...")
            
            url = "https://www.usa.gov/agency-index"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=30)
            
            self.log(f"Status: {response.status_code}")
            
            self.log("Parsing HTML...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            all_h2 = soup.find_all('h2')
            self.log(f"Found {len(all_h2)} h2 elements\n")
            
            agencies = []
            current_section = 'A'
            
            for h2 in all_h2:
                text = h2.text.strip()
                h2_id = h2.get('id', '')
                
                # Update section
                if h2_id in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and len(h2_id) == 1:
                    current_section = h2_id
                    continue
                    
                # Skip single letters and meta
                if text in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and len(text) == 1:
                    continue
                if 'Have a question?' in text:
                    continue
                    
                text = ' '.join(text.split())
                
                if len(text) > 2:
                    # Get URL if available
                    url = 'See USA.gov'
                    parent = h2.parent
                    if parent:
                        links = parent.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            if href and not href.startswith('#'):
                                url = href
                                break
                    
                    agencies.append({
                        'agency_name': text,
                        'homepage_url': url,
                        'section': current_section
                    })
                    self.log(f"[{current_section}] {text}")
            
            self.log(f"\n{'='*60}")
            self.log(f"TOTAL AGENCIES FOUND: {len(agencies)}")
            self.log("="*60)
            
            # Save files
            self.log("\nSaving data...")
            os.makedirs("scraped_data", exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # CSV
            csv_file = f"scraped_data/agencies_{timestamp}.csv"
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['agency_name', 'homepage_url', 'section'])
                writer.writeheader()
                writer.writerows(agencies)
            self.log(f"CSV saved: {csv_file}")
            
            # JSON
            json_file = f"scraped_data/agencies_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(agencies, f, indent=2, ensure_ascii=False)
            self.log(f"JSON saved: {json_file}")
            
            self.log("\n✅ SCRAPING COMPLETE!")
            
        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            
        finally:
            self.progress.stop()
            self.button.config(state="normal")
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ScraperApp()
    app.run()