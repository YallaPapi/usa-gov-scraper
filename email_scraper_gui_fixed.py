#!/usr/bin/env python3
"""
Government Email Scraper - Desktop GUI Application
Botasaurus-powered interface for scraping government contacts
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import queue
import os
import json
import csv
from datetime import datetime
from scrapers.email_scraper import GovernmentEmailScraper
from scrapers.local_gov_crawler import LocalGovernmentCrawler
import logging

class EmailScraperGUI:
    """Enhanced Desktop GUI for Government Email Scraping with progress tracking."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Government Email Scraper - Botasaurus Powered")
        self.root.geometry("900x700")
        
        # Application state
        self.is_scraping = False
        self.output_dir = "scraped_contacts"
        self.scraper = None
        
        # Threading and logging
        self.log_queue = queue.Queue()
        self.scraper_thread = None
        
        # Statistics
        self.stats = {
            'federal_agencies': 0,
            'federal_emails': 0,
            'local_sites': 0,
            'local_contacts': 0,
            'total_time': 0
        }
        
        self.setup_ui()
        self.setup_logging()
        
    def setup_ui(self):
        """Create the comprehensive user interface."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title with emoji
        title_label = ttk.Label(main_frame, text="🏛️ Government Email Scraper - Botasaurus Edition", 
                               font=('TkDefaultFont', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Scraping Configuration", padding="10")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Scraping mode selection
        ttk.Label(config_frame, text="Scraping Mode:").grid(row=0, column=0, sticky=tk.W)
        self.mode_var = tk.StringVar(value="Federal Only")
        mode_combo = ttk.Combobox(config_frame, textvariable=self.mode_var, width=20)
        mode_combo['values'] = ['Federal Only', 'Local Only', 'Single Agency Test']
        mode_combo.grid(row=0, column=1, padx=(5, 20), sticky=tk.W)
        
        # Input file selection
        ttk.Label(config_frame, text="Agencies CSV File:").grid(row=0, column=2, sticky=tk.W)
        self.file_var = tk.StringVar(value="scraped_data/all_agencies_20250825_150513.csv")
        file_entry = ttk.Entry(config_frame, textvariable=self.file_var, width=30)
        file_entry.grid(row=0, column=3, padx=(5, 5))
        
        browse_btn = ttk.Button(config_frame, text="Browse...", command=self.browse_input_file)
        browse_btn.grid(row=0, column=4, padx=(5, 0))
        
        # Output directory
        ttk.Label(config_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.output_var = tk.StringVar(value=self.output_dir)
        output_entry = ttk.Entry(config_frame, textvariable=self.output_var, width=30)
        output_entry.grid(row=1, column=1, columnspan=2, padx=(5, 5), pady=(10, 0), sticky=(tk.W, tk.E))
        
        output_browse_btn = ttk.Button(config_frame, text="Browse...", command=self.browse_output_dir)
        output_browse_btn.grid(row=1, column=3, padx=(5, 0), pady=(10, 0))
        
        # Control section
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Control buttons
        self.start_btn = ttk.Button(control_frame, text="🚀 Start Scraping", 
                                   command=self.start_scraping)
        self.start_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_btn = ttk.Button(control_frame, text="⏹️ Stop", 
                                  command=self.stop_scraping, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=(0, 10))
        
        self.clear_btn = ttk.Button(control_frame, text="🗑️ Clear Log", command=self.clear_log)
        self.clear_btn.grid(row=0, column=2, padx=(0, 10))
        
        self.open_folder_btn = ttk.Button(control_frame, text="📁 Results Folder", 
                                         command=self.open_results_folder, state=tk.DISABLED)
        self.open_folder_btn.grid(row=0, column=3)
        
        # Statistics section
        stats_frame = ttk.LabelFrame(main_frame, text="Real-time Statistics", padding="10")
        stats_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(stats_frame, variable=self.progress_var, 
                                           maximum=100, length=500)
        self.progress_bar.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Statistics labels
        self.status_label = ttk.Label(stats_frame, text="Ready to start scraping", font=('TkDefaultFont', 10, 'bold'))
        self.status_label.grid(row=1, column=0, columnspan=4, pady=(5, 0))
        
        # Stats grid
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.grid(row=2, column=0, columnspan=4, pady=(10, 0))
        
        ttk.Label(stats_grid, text="Federal Agencies:").grid(row=0, column=0, sticky=tk.W)
        self.federal_label = ttk.Label(stats_grid, text="0", font=('TkDefaultFont', 10, 'bold'))
        self.federal_label.grid(row=0, column=1, padx=(5, 20))
        
        ttk.Label(stats_grid, text="Emails Found:").grid(row=0, column=2, sticky=tk.W)
        self.emails_label = ttk.Label(stats_grid, text="0", font=('TkDefaultFont', 10, 'bold'))
        self.emails_label.grid(row=0, column=3, padx=(5, 20))
        
        ttk.Label(stats_grid, text="Local Sites:").grid(row=1, column=0, sticky=tk.W)
        self.local_label = ttk.Label(stats_grid, text="0", font=('TkDefaultFont', 10, 'bold'))
        self.local_label.grid(row=1, column=1, padx=(5, 20))
        
        ttk.Label(stats_grid, text="Total Contacts:").grid(row=1, column=2, sticky=tk.W)
        self.contacts_label = ttk.Label(stats_grid, text="0", font=('TkDefaultFont', 10, 'bold'))
        self.contacts_label.grid(row=1, column=3, padx=(5, 20))
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Scraping Log", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Log text area with scrollbar
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80, 
                                                 font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Results Summary", padding="10")
        results_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        self.results_label = ttk.Label(results_frame, text="No results yet - start scraping to see contacts found")
        self.results_label.grid(row=0, column=0, sticky=tk.W)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        config_frame.columnconfigure(3, weight=1)
        stats_frame.columnconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)
        
    def setup_logging(self):
        """Set up logging to capture scraper output."""
        # Create custom handler that sends logs to queue
        class QueueHandler(logging.Handler):
            def __init__(self, queue):
                super().__init__()
                self.queue = queue
            
            def emit(self, record):
                self.queue.put(self.format(record))
        
        # Set up logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Add queue handler
        queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        queue_handler.setFormatter(formatter)
        logger.addHandler(queue_handler)
        
        # Start log processing
        self.process_log_queue()
        
    def process_log_queue(self):
        """Process log messages from the queue and display them."""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, message + '\n')
                self.log_text.see(tk.END)
                
                # Update statistics based on log messages
                self.update_stats_from_log(message)
                
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_log_queue)
        
    def update_stats_from_log(self, message: str):
        """Update statistics display based on log messages."""
        if "Scraping" in message and "agency" in message.lower():
            self.stats['federal_agencies'] += 1
            self.federal_label.config(text=str(self.stats['federal_agencies']))
            
        if "Found" in message and "unique emails" in message:
            try:
                # Extract number from message like "Found 5 unique emails"
                import re
                match = re.search(r'Found (\d+)', message)
                if match:
                    self.stats['federal_emails'] = int(match.group(1))
                    self.emails_label.config(text=str(self.stats['federal_emails']))
            except:
                pass
                
        if "sites discovered" in message.lower():
            try:
                import re
                match = re.search(r'(\d+)', message)
                if match:
                    self.stats['local_sites'] = int(match.group(1))
                    self.local_label.config(text=str(self.stats['local_sites']))
            except:
                pass
        
        # Update total contacts
        total = self.stats['federal_emails'] + self.stats['local_contacts']
        self.contacts_label.config(text=str(total))
        
    def browse_input_file(self):
        """Browse for input agencies CSV file."""
        file_path = filedialog.askopenfilename(
            title="Select Agencies CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir="scraped_data"
        )
        if file_path:
            self.file_var.set(file_path)
            
    def browse_output_dir(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(initialdir=self.output_var.get())
        if directory:
            self.output_var.set(directory)
            self.output_dir = directory
            
    def clear_log(self):
        """Clear the log text area."""
        self.log_text.delete(1.0, tk.END)
        
    def update_progress(self, current, total, message=""):
        """Update progress bar and status."""
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)
        
        if message:
            self.status_label.config(text=message)
            
    def start_scraping(self):
        """Start the scraping process in a separate thread."""
        if self.is_scraping:
            return
        
        # Validate input file
        input_file = self.file_var.get()
        if not os.path.exists(input_file):
            messagebox.showerror("Error", f"Input file not found: {input_file}")
            return
            
        self.is_scraping = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.open_folder_btn.config(state=tk.DISABLED)
        
        # Reset statistics
        self.stats = {'federal_agencies': 0, 'federal_emails': 0, 'local_sites': 0, 'local_contacts': 0}
        
        # Get configuration
        mode = self.mode_var.get()
        output_dir = self.output_var.get()
        
        self.update_progress(0, 1, f"Starting {mode} scraping...")
        
        # Start scraping thread
        self.scraper_thread = threading.Thread(
            target=self.scrape_worker, 
            args=(mode, input_file, output_dir),
            daemon=True
        )
        self.scraper_thread.start()
        
    def scrape_worker(self, mode: str, input_file: str, output_dir: str):
        """Worker function for scraping in separate thread."""
        try:
            logger = logging.getLogger()
            logger.info(f"Starting {mode} scraping with Botasaurus")
            
            if mode == "Federal Only":
                # Federal agencies only
                scraper = GovernmentEmailScraper(output_dir)
                self.update_progress(10, 100, "Scraping federal agencies...")
                result = scraper.scrape_federal_agencies(input_file)
                self.update_progress(100, 100, "Federal scraping completed")
                
            elif mode == "Local Only":
                # Local government only
                crawler = LocalGovernmentCrawler(output_dir)
                self.update_progress(10, 100, "Discovering local government sites...")
                discovery = crawler.discover_by_search(['New York', 'California', 'Texas'])
                
                if discovery['success']:
                    self.update_progress(50, 100, "Crawling discovered sites...")
                    result = crawler.crawl_discovered_sites(max_sites=25)
                    self.update_progress(100, 100, "Local scraping completed")
                    
            elif mode == "Single Agency Test":
                # Single agency test
                scraper = GovernmentEmailScraper(output_dir)
                # Create a single-agency CSV for testing
                test_csv = os.path.join(output_dir, 'single_agency_test.csv')
                with open(input_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    first_row = next(reader)
                    
                with open(test_csv, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=first_row.keys())
                    writer.writeheader()
                    writer.writerow(first_row)
                
                result = scraper.scrape_federal_agencies(test_csv)
                os.remove(test_csv)  # Cleanup
            
            logger.info("Scraping process completed successfully!")
            self.scraping_finished(True)
            
        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}", exc_info=True)
            self.scraping_finished(False)
            
    def stop_scraping(self):
        """Stop the scraping process."""
        self.is_scraping = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_progress(0, 1, "Stopped by user")
        
    def scraping_finished(self, success: bool):
        """Handle scraping completion."""
        self.is_scraping = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.open_folder_btn.config(state=tk.NORMAL)
        
        if success:
            total_contacts = self.stats['federal_emails'] + self.stats['local_contacts']
            self.results_label.config(text=f"✅ Scraping complete! Found {total_contacts} contacts")
            messagebox.showinfo("Success", f"Scraping completed successfully!\nFound {total_contacts} contacts")
        else:
            self.results_label.config(text="❌ Scraping failed - check log for details")
            messagebox.showerror("Error", "Scraping failed. Check the log for details.")
    
    def open_results_folder(self):
        """Open the results folder in file explorer."""
        try:
            os.startfile(self.output_dir)
        except AttributeError:
            # For non-Windows systems
            import subprocess
            subprocess.call(['xdg-open', self.output_dir])


def main():
    """Main entry point for email scraper GUI."""
    root = tk.Tk()
    
    app = EmailScraperGUI(root)
    
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