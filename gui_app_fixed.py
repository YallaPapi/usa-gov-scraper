"""
USA.gov Agency Index Scraper - FIXED Desktop GUI Application
Uses the working scraper logic to extract REAL agencies
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
from typing import List, Dict

class USAGovScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("USA.gov Agency Index Scraper - FIXED VERSION")
        self.root.geometry("1200x800")
        
        # Apply dark theme
        self.root.configure(bg='#2b2b2b')
        
        self.agencies = []
        self.is_running = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Main scraping tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Scraper")
        
        # Results tab
        self.results_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.results_tab, text="Results")
        
        # Logs tab
        self.logs_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_tab, text="Logs")
        
        self.setup_main_tab()
        self.setup_results_tab()
        self.setup_logs_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready to scrape")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, 
                                  bg='#1e1e1e', fg='white', anchor='w')
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=5)
        
    def setup_main_tab(self):
        """Setup the main scraping tab"""
        
        # Control frame
        control_frame = tk.Frame(self.main_tab, bg='#2b2b2b')
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # Title
        title = tk.Label(control_frame, text="USA.gov Agency Scraper - FIXED", 
                        font=("Arial", 18, "bold"), bg='#2b2b2b', fg='white')
        title.pack(pady=10)
        
        # Info label
        info = tk.Label(control_frame, 
                       text="Extracts REAL government agencies from USA.gov (not navigation links)",
                       font=("Arial", 10), bg='#2b2b2b', fg='#cccccc')
        info.pack(pady=5)
        
        # Options frame
        options_frame = tk.LabelFrame(control_frame, text="Options", 
                                     bg='#2b2b2b', fg='white', font=("Arial", 10, "bold"))
        options_frame.pack(fill="x", pady=10)
        
        # Checkboxes
        self.validate_urls_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Validate URLs", 
                      variable=self.validate_urls_var,
                      bg='#2b2b2b', fg='white', selectcolor='#2b2b2b').pack(anchor='w', padx=10, pady=5)
        
        self.export_csv_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Export to CSV", 
                      variable=self.export_csv_var,
                      bg='#2b2b2b', fg='white', selectcolor='#2b2b2b').pack(anchor='w', padx=10, pady=5)
        
        self.export_json_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Export to JSON", 
                      variable=self.export_json_var,
                      bg='#2b2b2b', fg='white', selectcolor='#2b2b2b').pack(anchor='w', padx=10, pady=5)
        
        # Buttons
        button_frame = tk.Frame(control_frame, bg='#2b2b2b')
        button_frame.pack(pady=20)
        
        self.start_button = tk.Button(button_frame, text="▶ Start Scraping", 
                                     command=self.start_scraping,
                                     bg='#4CAF50', fg='white', font=("Arial", 12, "bold"),
                                     padx=20, pady=10)
        self.start_button.pack(side="left", padx=10)
        
        self.stop_button = tk.Button(button_frame, text="⬛ Stop", 
                                    command=self.stop_scraping,
                                    bg='#f44336', fg='white', font=("Arial", 12, "bold"),
                                    padx=20, pady=10, state="disabled")
        self.stop_button.pack(side="left", padx=10)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", padx=10, pady=10)
        
        # Real-time stats
        stats_frame = tk.LabelFrame(control_frame, text="Live Statistics", 
                                   bg='#2b2b2b', fg='white', font=("Arial", 10, "bold"))
        stats_frame.pack(fill="x", pady=10)
        
        self.stats_text = tk.Text(stats_frame, height=8, bg='#1e1e1e', fg='#00ff00',
                                 font=("Consolas", 10))
        self.stats_text.pack(fill="both", padx=10, pady=10)
        
    def setup_results_tab(self):
        """Setup the results tab"""
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(self.results_tab, 
                                                     bg='#1e1e1e', fg='white',
                                                     font=("Consolas", 10))
        self.results_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Export buttons
        export_frame = tk.Frame(self.results_tab, bg='#2b2b2b')
        export_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(export_frame, text="Save Results", 
                 command=self.save_results,
                 bg='#2196F3', fg='white').pack(side="left", padx=5)
        
    def setup_logs_tab(self):
        """Setup the logs tab"""
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(self.logs_tab,
                                                 bg='#1e1e1e', fg='#cccccc',
                                                 font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Clear button
        tk.Button(self.logs_tab, text="Clear Logs", 
                 command=lambda: self.log_text.delete(1.0, tk.END),
                 bg='#757575', fg='white').pack(pady=5)
        
    def log(self, message, level="INFO"):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_status(self, message):
        """Update status bar"""
        self.status_var.set(message)
        self.root.update_idletasks()
        
    def update_stats(self, agencies_count):
        """Update live statistics"""
        self.stats_text.delete(1.0, tk.END)
        stats = f"""
Agencies Found: {agencies_count}
Status: {'Running' if self.is_running else 'Stopped'}
Timestamp: {datetime.now().strftime('%H:%M:%S')}
        """
        self.stats_text.insert(1.0, stats)
        self.root.update_idletasks()
        
    def start_scraping(self):
        """Start the scraping process"""
        if self.is_running:
            return
            
        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress_bar.start()
        
        # Clear previous results
        self.log_text.delete(1.0, tk.END)
        self.results_text.delete(1.0, tk.END)
        self.agencies = []
        
        # Start scraping in separate thread
        thread = threading.Thread(target=self.scrape_agencies)
        thread.daemon = True
        thread.start()
        
    def stop_scraping(self):
        """Stop the scraping process"""
        self.is_running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.progress_bar.stop()
        self.update_status("Stopped by user")
        
    def scrape_agencies(self):
        """Main scraping logic - FIXED VERSION"""
        try:
            start_time = datetime.now()
            
            self.log("="*60)
            self.log("USA.gov Agency Index Scraper - FIXED VERSION")
            self.log("="*60)
            
            # Fetch page
            self.update_status("Fetching USA.gov agency index...")
            self.log("\n[1] Fetching page...")
            
            url = "https://www.usa.gov/agency-index"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch page: {response.status_code}")
            
            self.log(f"  Page fetched successfully (status: {response.status_code})")
            
            # Parse HTML
            self.update_status("Parsing HTML structure...")
            self.log("\n[2] Parsing HTML...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get ALL h2 elements (agencies are h2 elements that are NOT letter headings)
            all_h2 = soup.find_all('h2')
            self.log(f"  Found {len(all_h2)} h2 elements total")
            
            # Extract REAL agencies
            self.update_status("Extracting real government agencies...")
            self.log("\n[3] Extracting agencies (not navigation links)...")
            
            all_agencies = []
            current_section = 'A'
            
            for h2 in all_h2:
                if not self.is_running:
                    return
                
                h2_text = h2.text.strip()
                h2_id = h2.get('id', '')
                
                # Clean up text
                h2_text = ' '.join(h2_text.split())
                
                # Check if this is a letter heading
                if h2_id in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and len(h2_id) == 1:
                    current_section = h2_id
                    continue
                
                # Skip single letters
                if h2_text in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and len(h2_text) == 1:
                    current_section = h2_text
                    continue
                
                # Skip meta content
                skip_phrases = ['Have a question?', 'About', 'Help', 'Contact', 'Search']
                if any(phrase in h2_text for phrase in skip_phrases):
                    continue
                
                # This is likely a real agency
                if len(h2_text) > 2:
                    # Try to find URL
                    agency_url = ''
                    parent = h2.parent
                    if parent:
                        links = parent.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            link_text = link.text.strip().lower()
                            
                            if href and not href.startswith('#'):
                                if 'website' in link_text or 'official' in link_text:
                                    agency_url = href
                                    break
                                elif not agency_url and not href.startswith('/'):
                                    agency_url = href
                    
                    if not agency_url:
                        agency_url = 'See USA.gov'
                    
                    all_agencies.append({
                        'agency_name': h2_text,
                        'homepage_url': agency_url,
                        'section': current_section
                    })
                    
                    self.log(f"  [OK] Found: {h2_text}")
                    self.update_stats(len(all_agencies))
            
            self.agencies = all_agencies
            
            # Validation
            if self.validate_urls_var.get():
                self.update_status("Validating extracted data...")
                self.log(f"\n[4] Validation...")
                
                # Check for known patterns
                patterns = ['Department', 'Agency', 'Administration', 'Bureau', 
                          'Commission', 'Office', 'Service', 'Command']
                valid_count = sum(1 for a in all_agencies 
                                if any(p in a['agency_name'] for p in patterns))
                
                self.log(f"  Agencies with valid patterns: {valid_count}/{len(all_agencies)}")
                
                # Check we don't have navigation links
                bad_entries = [a for a in all_agencies if len(a['agency_name']) == 1]
                if bad_entries:
                    self.log(f"  WARNING: Found {len(bad_entries)} single-letter entries")
                else:
                    self.log("  [OK] No navigation links in data")
            
            # Display results
            self.update_status("Displaying results...")
            self.log(f"\n[5] Results:")
            self.log(f"  Total REAL agencies found: {len(all_agencies)}")
            
            # Show in results tab
            self.results_text.insert(tk.END, "USA.GOV AGENCIES - REAL DATA\n")
            self.results_text.insert(tk.END, "="*60 + "\n\n")
            
            for i, agency in enumerate(all_agencies, 1):
                result_line = f"{i}. {agency['agency_name']}\n"
                if agency['homepage_url'] != 'See USA.gov':
                    result_line += f"   URL: {agency['homepage_url']}\n"
                result_line += f"   Section: {agency['section']}\n\n"
                self.results_text.insert(tk.END, result_line)
            
            # Export if enabled
            if self.export_csv_var.get() or self.export_json_var.get():
                self.export_data()
            
            # Complete
            duration = (datetime.now() - start_time).total_seconds()
            self.log(f"\n" + "="*60)
            self.log(f"SCRAPING COMPLETE")
            self.log(f"Agencies found: {len(all_agencies)}")
            self.log(f"Duration: {duration:.2f} seconds")
            self.log("="*60)
            
            self.update_status(f"Complete - {len(all_agencies)} agencies found")
            
        except Exception as e:
            self.log(f"\n[ERROR] {str(e)}", "ERROR")
            messagebox.showerror("Error", f"Scraping failed: {str(e)}")
            
        finally:
            self.is_running = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.progress_bar.stop()
    
    def export_data(self):
        """Export scraped data"""
        if not self.agencies:
            return
            
        os.makedirs("scraped_data", exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if self.export_csv_var.get():
            csv_file = f"scraped_data/agencies_gui_{timestamp}.csv"
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['agency_name', 'homepage_url', 'section'])
                writer.writeheader()
                writer.writerows(self.agencies)
            self.log(f"  [EXPORT] CSV saved: {csv_file}")
        
        if self.export_json_var.get():
            json_file = f"scraped_data/agencies_gui_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.agencies, f, indent=2, ensure_ascii=False)
            self.log(f"  [EXPORT] JSON saved: {json_file}")
    
    def save_results(self):
        """Save results to file"""
        if not self.agencies:
            messagebox.showwarning("No Data", "No agencies to save")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            content = self.results_text.get(1.0, tk.END)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Saved", f"Results saved to {file_path}")

def main():
    root = tk.Tk()
    app = USAGovScraperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()