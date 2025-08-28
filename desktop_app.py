#!/usr/bin/env python3
"""
USA.gov Government Agency Scraper - Enhanced Desktop Application
Cross-platform desktop GUI with progress tracking and live logging
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import queue
import os
import json
from datetime import datetime
# Prefer Botasaurus scraper if available; fallback to requests-based core
try:
    from scraper.botasaurus_core import GovernmentAgencyScraper  # type: ignore
    _SCRAPER_IMPL = "botasaurus"
except Exception:
    from scraper.core import GovernmentAgencyScraper  # type: ignore
    _SCRAPER_IMPL = "core"
import logging


class DesktopScraperApp:
    """Enhanced Desktop GUI for USA.gov Agency Scraper with progress tracking."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("USA.gov Government Agency Scraper")
        self.root.geometry("800x600")
        
        # Application state
        self.scraper = None
        self.is_scraping = False
        self.output_dir = "scraped_data"
        
        # Threading and logging
        self.log_queue = queue.Queue()
        self.scraper_thread = None
        
        self.setup_ui()
        self.setup_logging()
        
    def setup_ui(self):
        """Create the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="USA.gov Government Agency Scraper", 
                               font=('TkDefaultFont', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Section selection
        ttk.Label(config_frame, text="Section:").grid(row=0, column=0, sticky=tk.W)
        self.section_var = tk.StringVar(value="All")
        section_combo = ttk.Combobox(config_frame, textvariable=self.section_var, width=10)
        section_combo['values'] = ['All'] + list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        section_combo.grid(row=0, column=1, padx=(5, 20))
        
        # Output directory
        ttk.Label(config_frame, text="Output Directory:").grid(row=0, column=2, sticky=tk.W)
        self.output_var = tk.StringVar(value=self.output_dir)
        output_entry = ttk.Entry(config_frame, textvariable=self.output_var, width=30)
        output_entry.grid(row=0, column=3, padx=(5, 5))
        
        browse_btn = ttk.Button(config_frame, text="Browse...", command=self.browse_output_dir)
        browse_btn.grid(row=0, column=4, padx=(5, 0))
        
        # Control section
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Start/Stop buttons
        self.start_btn = ttk.Button(control_frame, text="Start Scraping", 
                                   command=self.start_scraping, style="Accent.TButton")
        self.start_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_btn = ttk.Button(control_frame, text="Stop", 
                                  command=self.stop_scraping, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=(0, 10))
        
        self.clear_btn = ttk.Button(control_frame, text="Clear Log", command=self.clear_log)
        self.clear_btn.grid(row=0, column=2)
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Status labels
        self.status_label = ttk.Label(progress_frame, text="Ready to start scraping")
        self.status_label.grid(row=1, column=0, sticky=tk.W)
        
        self.count_label = ttk.Label(progress_frame, text="Agencies found: 0")
        self.count_label.grid(row=1, column=1, sticky=tk.E)
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Log text area with scrollbar
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        self.results_label = ttk.Label(results_frame, text="No results yet")
        self.results_label.grid(row=0, column=0, sticky=tk.W)
        
        self.open_folder_btn = ttk.Button(results_frame, text="Open Results Folder", 
                                         command=self.open_results_folder, state=tk.DISABLED)
        self.open_folder_btn.grid(row=0, column=1, sticky=tk.E)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        config_frame.columnconfigure(3, weight=1)
        progress_frame.columnconfigure(0, weight=1)
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
        logger = logging.getLogger('usa_gov_scraper')
        logger.setLevel(logging.INFO)
        
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
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_log_queue)
        
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
            
    def update_count(self, count):
        """Update agency count display."""
        self.count_label.config(text=f"Agencies found: {count}")
        
    def start_scraping(self):
        """Start the scraping process in a separate thread."""
        if self.is_scraping:
            return
            
        self.is_scraping = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.open_folder_btn.config(state=tk.DISABLED)
        
        # Get configuration
        section = self.section_var.get()
        if section == "All":
            section = None
            
        self.output_dir = self.output_var.get()
        
        # Start scraping thread
        self.scraper_thread = threading.Thread(
            target=self.scrape_worker, 
            args=(section,),
            daemon=True
        )
        self.scraper_thread.start()
        
    def stop_scraping(self):
        """Stop the scraping process."""
        self.is_scraping = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_progress(0, 1, "Stopped by user")
        
    def scrape_worker(self, section):
        """Worker function for scraping in separate thread."""
        try:
            logger = logging.getLogger('usa_gov_scraper')
            logger.info("Starting USA.gov Agency Scraper Desktop Application")
            
            # Initialize scraper
            scraper = GovernmentAgencyScraper(rate_limit=0.5, max_retries=3)
            
            self.update_progress(0, 26 if not section else 1, "Initializing scraper...")
            
            if section:
                # Scrape specific section
                logger.info(f"Scraping section: {section}")
                self.update_progress(0, 1, f"Scraping section {section}...")
                
                result = scraper.scrape_section(section)
                
                if result['success']:
                    agencies = result['agencies']
                    self.update_count(len(agencies))
                    self.update_progress(1, 1, "Section scraping completed")
                else:
                    logger.error(f"Failed to scrape section {section}")
                    self.scraping_finished(False)
                    return
            else:
                # Scrape all sections
                logger.info("Scraping all sections A-Z")
                self.update_progress(0, 26, "Starting comprehensive scrape...")
                
                result = scraper.scrape_all_sections()
                
                if result['success']:
                    agencies = result['agencies']
                    stats = result['statistics']
                    self.update_count(len(agencies))
                    self.update_progress(26, 26, f"Scraping completed in {stats['duration_seconds']:.1f}s")
                    logger.info(f"Found {len(agencies)} agencies across {stats['sections_scraped']} sections")
                else:
                    logger.error("Failed to scrape agencies")
                    self.scraping_finished(False)
                    return
            
            # Validate data
            logger.info("Validating scraped data...")
            self.update_progress(26, 30, "Validating data...")
            
            validation = scraper.validate_data(agencies)
            logger.info(f"Validation: {validation['valid_agencies']}/{validation['total_agencies']} valid agencies")
            
            if not validation['validation_passed']:
                logger.warning(f"Found {len(validation['issues'])} validation issues")
                for issue in validation['issues'][:3]:
                    logger.warning(f"  - {issue}")
            
            # Export data
            logger.info("Exporting data to files...")
            self.update_progress(28, 30, "Exporting data...")
            
            os.makedirs(self.output_dir, exist_ok=True)
            export_paths = scraper.export_data(agencies, self.output_dir)
            
            logger.info("Export completed:")
            logger.info(f"  CSV: {export_paths['csv']}")
            logger.info(f"  JSON: {export_paths['json']}")
            
            self.update_progress(30, 30, "Export completed successfully")
            
            # Update results display
            result_text = f"Successfully scraped {len(agencies)} agencies. Files saved to {self.output_dir}"
            self.results_label.config(text=result_text)
            self.open_folder_btn.config(state=tk.NORMAL)
            
            logger.info("Scraping process completed successfully!")
            self.scraping_finished(True, export_paths)
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            self.scraping_finished(False)
            
    def scraping_finished(self, success, export_paths=None):
        """Handle scraping completion."""
        self.is_scraping = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        if success:
            messagebox.showinfo("Success", "Scraping completed successfully!")
            if export_paths:
                self.open_folder_btn.config(state=tk.NORMAL)
        else:
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
    """Main entry point for desktop application."""
    root = tk.Tk()
    
    # Set application icon and style
    try:
        root.tk.call('source', os.path.join(os.path.dirname(__file__), 'theme', 'forest-light.tcl'))
        ttk.Style().theme_use('forest-light')
    except:
        pass  # Use default theme if custom theme not available
    
    app = DesktopScraperApp(root)
    
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
