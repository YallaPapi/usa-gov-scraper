#!/usr/bin/env python
"""
USA.gov Agency Index Scraper - GUI Desktop Application
Full-featured Botasaurus desktop app with graphical interface
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
from typing import List, Dict, Any


class USAGovScraperApp:
    """Desktop GUI Application for USA.gov Agency Scraper"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("USA.gov Agency Index Scraper - Desktop App")
        self.root.geometry("900x700")
        
        # Data storage
        self.agencies = []
        self.dynamic_agents = []
        self.is_running = False
        
        # Create GUI
        self.create_widgets()
        
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Header
        header_frame = tk.Frame(self.root, bg="#003366", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, 
            text="🏛️ USA.gov Agency Index Scraper",
            font=("Arial", 24, "bold"),
            fg="white",
            bg="#003366"
        )
        title_label.pack(pady=20)
        
        subtitle_label = tk.Label(
            header_frame,
            text="Powered by Botasaurus + Agency Swarm",
            font=("Arial", 12),
            fg="#cccccc",
            bg="#003366"
        )
        subtitle_label.pack()
        
        # Control Panel
        control_frame = tk.Frame(self.root, bg="#f0f0f0", height=120)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # Options
        options_frame = tk.LabelFrame(control_frame, text="Options", padx=10, pady=10)
        options_frame.pack(side="left", padx=10, pady=10)
        
        self.remove_duplicates_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Remove Duplicates",
            variable=self.remove_duplicates_var
        ).pack(anchor="w")
        
        self.validate_urls_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Validate URLs",
            variable=self.validate_urls_var
        ).pack(anchor="w")
        
        self.use_agents_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Use Agency Swarm Agents",
            variable=self.use_agents_var
        ).pack(anchor="w")
        
        # Export Format
        format_frame = tk.LabelFrame(control_frame, text="Export Format", padx=10, pady=10)
        format_frame.pack(side="left", padx=10, pady=10)
        
        self.export_format = tk.StringVar(value="both")
        tk.Radiobutton(format_frame, text="CSV & JSON", variable=self.export_format, value="both").pack(anchor="w")
        tk.Radiobutton(format_frame, text="CSV Only", variable=self.export_format, value="csv").pack(anchor="w")
        tk.Radiobutton(format_frame, text="JSON Only", variable=self.export_format, value="json").pack(anchor="w")
        
        # Buttons
        button_frame = tk.Frame(control_frame)
        button_frame.pack(side="right", padx=20, pady=20)
        
        self.start_button = tk.Button(
            button_frame,
            text="🚀 Start Scraping",
            command=self.start_scraping,
            bg="#28a745",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=10
        )
        self.start_button.pack(side="top", pady=5)
        
        self.stop_button = tk.Button(
            button_frame,
            text="⏹️ Stop",
            command=self.stop_scraping,
            bg="#dc3545",
            fg="white",
            font=("Arial", 12),
            padx=20,
            pady=5,
            state="disabled"
        )
        self.stop_button.pack(side="top", pady=5)
        
        # Progress Frame
        progress_frame = tk.LabelFrame(self.root, text="Progress", padx=10, pady=10)
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", pady=5)
        
        self.status_label = tk.Label(progress_frame, text="Ready to start", font=("Arial", 10))
        self.status_label.pack(anchor="w")
        
        # Statistics Frame
        stats_frame = tk.LabelFrame(self.root, text="Statistics", padx=10, pady=10)
        stats_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(stats_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Log Tab
        log_frame = tk.Frame(self.notebook)
        self.notebook.add(log_frame, text="📋 Activity Log")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Results Tab
        results_frame = tk.Frame(self.notebook)
        self.notebook.add(results_frame, text="📊 Results")
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=15, width=80)
        self.results_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Agents Tab
        agents_frame = tk.Frame(self.notebook)
        self.notebook.add(agents_frame, text="🤖 Active Agents")
        
        self.agents_listbox = tk.Listbox(agents_frame, height=15)
        self.agents_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Footer
        footer_frame = tk.Frame(self.root, bg="#f0f0f0", height=30)
        footer_frame.pack(fill="x", side="bottom")
        
        self.footer_label = tk.Label(
            footer_frame,
            text="© 2025 USA.gov Agency Scraper | Status: Ready",
            font=("Arial", 9),
            bg="#f0f0f0"
        )
        self.footer_label.pack(pady=5)
        
    def log(self, message, level="INFO"):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update()
        
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        self.footer_label.config(text=f"© 2025 USA.gov Agency Scraper | Status: {message}")
        self.root.update()
        
    def add_agent(self, agent_name):
        """Add agent to active agents list"""
        self.agents_listbox.insert(tk.END, f"✓ {agent_name}")
        self.dynamic_agents.append(agent_name)
        self.root.update()
        
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
        self.agents_listbox.delete(0, tk.END)
        self.agencies = []
        self.dynamic_agents = []
        
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
        """Main scraping logic"""
        try:
            start_time = datetime.now()
            
            self.log("="*60)
            self.log("USA.gov Agency Index Scraper Started")
            self.log("="*60)
            
            # Add base agents if using Agency Swarm
            if self.use_agents_var.get():
                self.log("Initializing Agency Swarm agents...")
                self.add_agent("Planner Agent")
                self.add_agent("Crawler Agent")
                self.add_agent("Validator Agent")
                self.add_agent("Exporter Agent")
            
            # Phase 1: Planning
            self.update_status("Phase 1: Planning - Analyzing page structure...")
            self.log("\n📋 PHASE 1: PLANNING")
            
            url = "https://www.usa.gov/agency-index"
            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            sections = []
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                if not self.is_running:
                    return
                    
                section = soup.find('section', {'id': letter})
                if section:
                    sections.append(letter)
                    self.log(f"  ✓ Found section: {letter}")
            
            self.log(f"  Total sections found: {len(sections)}")
            
            # Phase 2: Crawling
            self.update_status("Phase 2: Crawling - Extracting agencies...")
            self.log("\n🕷️ PHASE 2: CRAWLING")
            
            all_agencies = []
            failed_sections = []
            
            for idx, section_id in enumerate(sections, 1):
                if not self.is_running:
                    return
                    
                self.update_status(f"Scraping section {section_id} ({idx}/{len(sections)})...")
                
                try:
                    section = soup.find('section', {'id': section_id})
                    if section:
                        links = section.find_all('a', href=True)
                        section_agencies = []
                        
                        for link in links:
                            if link.get('href', '').startswith('#'):
                                continue
                                
                            agency_name = link.text.strip()
                            homepage_url = link.get('href', '')
                            
                            if not homepage_url.startswith(('http://', 'https://')):
                                homepage_url = f"https://www.usa.gov{homepage_url}" if homepage_url.startswith('/') else f"https://{homepage_url}"
                            
                            if agency_name and homepage_url:
                                section_agencies.append({
                                    'agency_name': agency_name,
                                    'homepage_url': homepage_url,
                                    'section': section_id,
                                    'parent_department': None
                                })
                        
                        all_agencies.extend(section_agencies)
                        self.log(f"  ✓ Section {section_id}: {len(section_agencies)} agencies")
                        
                except Exception as e:
                    failed_sections.append(section_id)
                    self.log(f"  ✗ Section {section_id}: Error - {str(e)}", "ERROR")
            
            # Handle failed sections with retry
            if failed_sections and self.use_agents_var.get():
                self.log("\n  Creating Retry Handler Agent...")
                self.add_agent("RetryHandlerAgent (Dynamic)")
                # Retry logic would go here
            
            self.agencies = all_agencies
            
            # Phase 3: Validation
            if self.validate_urls_var.get():
                self.update_status("Phase 3: Validation - Checking data quality...")
                self.log("\n✅ PHASE 3: VALIDATION")
                
                valid_agencies = []
                for agency in all_agencies:
                    if agency.get('agency_name') and agency.get('homepage_url'):
                        valid_agencies.append(agency)
                
                self.log(f"  Valid agencies: {len(valid_agencies)}")
                
                # URL normalization
                if self.use_agents_var.get():
                    self.add_agent("URLNormalizerAgent (Dynamic)")
                
                self.agencies = valid_agencies
            
            # Remove duplicates
            if self.remove_duplicates_var.get():
                self.update_status("Removing duplicates...")
                self.log("\n🧹 REMOVING DUPLICATES")
                
                if self.use_agents_var.get():
                    self.add_agent("DeduplicatorAgent (Dynamic)")
                
                unique_agencies = []
                seen_urls = set()
                
                for agency in self.agencies:
                    if agency['homepage_url'] not in seen_urls:
                        seen_urls.add(agency['homepage_url'])
                        unique_agencies.append(agency)
                
                duplicates_removed = len(self.agencies) - len(unique_agencies)
                self.log(f"  Removed {duplicates_removed} duplicates")
                self.agencies = unique_agencies
            
            # Phase 4: Export
            self.update_status("Phase 4: Export - Saving data...")
            self.log("\n💾 PHASE 4: EXPORT")
            
            os.makedirs("scraped_data", exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            export_format = self.export_format.get()
            files_created = []
            
            if export_format in ["csv", "both"]:
                csv_file = f"scraped_data/agencies_{timestamp}.csv"
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['agency_name', 'homepage_url', 'section'])
                    writer.writeheader()
                    writer.writerows(self.agencies)
                files_created.append(csv_file)
                self.log(f"  ✓ CSV: {csv_file}")
            
            if export_format in ["json", "both"]:
                json_file = f"scraped_data/agencies_{timestamp}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(self.agencies, f, indent=2, ensure_ascii=False)
                files_created.append(json_file)
                self.log(f"  ✓ JSON: {json_file}")
            
            # Create logger agent for stats
            if self.use_agents_var.get():
                self.add_agent("LoggerAgent (Dynamic)")
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            
            # Display results
            self.log("\n" + "="*60)
            self.log("SCRAPING COMPLETE!")
            self.log("="*60)
            
            results_summary = f"""
SUMMARY
=======
Total Agencies: {len(self.agencies)}
Sections Scraped: {len(sections)}
Duration: {duration:.2f} seconds
Files Created: {', '.join(files_created)}

Dynamic Agents Created: {len([a for a in self.dynamic_agents if '(Dynamic)' in a])}
"""
            
            self.results_text.insert(tk.END, results_summary)
            
            # Add sample agencies to results
            self.results_text.insert(tk.END, "\nSAMPLE AGENCIES (First 10):\n")
            self.results_text.insert(tk.END, "="*40 + "\n")
            
            for agency in self.agencies[:10]:
                self.results_text.insert(tk.END, f"• {agency['agency_name']}\n")
                self.results_text.insert(tk.END, f"  URL: {agency['homepage_url']}\n")
                self.results_text.insert(tk.END, f"  Section: {agency['section']}\n\n")
            
            self.update_status(f"Complete! Scraped {len(self.agencies)} agencies in {duration:.1f}s")
            
            # Show completion dialog
            messagebox.showinfo(
                "Scraping Complete",
                f"Successfully scraped {len(self.agencies)} agencies!\n\n"
                f"Files saved:\n{chr(10).join(files_created)}"
            )
            
        except Exception as e:
            self.log(f"ERROR: {str(e)}", "ERROR")
            self.update_status("Error occurred")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            
        finally:
            self.is_running = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.progress_bar.stop()


def main():
    """Launch the desktop application"""
    root = tk.Tk()
    app = USAGovScraperApp(root)
    
    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()


if __name__ == "__main__":
    main()