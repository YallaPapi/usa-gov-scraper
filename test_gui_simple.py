"""
Simple test to verify the GUI scraping works
"""

import tkinter as tk
from tkinter import ttk
import requests
from bs4 import BeautifulSoup
import threading

class SimpleScraperGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Simple Scraper Test")
        self.root.geometry("600x400")
        
        # Button
        self.button = tk.Button(self.root, text="Start Scraping", command=self.start_scraping)
        self.button.pack(pady=20)
        
        # Text area
        self.text = tk.Text(self.root)
        self.text.pack(fill="both", expand=True, padx=10, pady=10)
        
    def log(self, msg):
        """Add message to text area"""
        self.text.insert(tk.END, msg + "\n")
        self.text.see(tk.END)
        self.root.update()
        
    def start_scraping(self):
        """Start scraping in thread"""
        self.button.config(state="disabled")
        self.log("Starting scrape...")
        
        thread = threading.Thread(target=self.scrape)
        thread.daemon = True
        thread.start()
        
    def scrape(self):
        """Scrape agencies"""
        try:
            self.log("Fetching page...")
            
            url = "https://www.usa.gov/agency-index"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            response = requests.get(url, headers=headers, timeout=30)
            self.log(f"Status code: {response.status_code}")
            
            if response.status_code != 200:
                self.log(f"ERROR: Bad status code")
                return
                
            self.log("Parsing HTML...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find h2 elements
            all_h2 = soup.find_all('h2')
            self.log(f"Found {len(all_h2)} h2 elements")
            
            agencies = []
            for h2 in all_h2:
                text = h2.text.strip()
                h2_id = h2.get('id', '')
                
                # Skip letter headings
                if h2_id in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and len(h2_id) == 1:
                    continue
                if text in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and len(text) == 1:
                    continue
                if 'Have a question?' in text:
                    continue
                    
                # Clean text
                text = ' '.join(text.split())
                
                if len(text) > 2:
                    agencies.append(text)
                    self.log(f"Found: {text}")
                    
            self.log(f"\nTotal agencies: {len(agencies)}")
            
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            
        finally:
            self.button.config(state="normal")
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SimpleScraperGUI()
    app.run()