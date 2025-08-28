#!/usr/bin/env python3
"""
USA.gov Government Agency Scraper - Enhanced Desktop Application
Cross-platform desktop GUI with progress tracking and live logging
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import queue
import subprocess
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
        self.db_path = os.path.abspath("government_contacts.db")
        self.api_process = None
        
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

        # Pipeline & Tools
        tools_frame = ttk.LabelFrame(main_frame, text="Pipeline & Tools", padding="10")
        tools_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # Plain‑language explanation
        ttk.Label(tools_frame, text=(
            "This page helps you: 1) collect the official agency list,"
            " 2) find more government websites, 3) pull contacts (emails/phones),"
            " and 4) start/stop a small local website (API) to access your data."
        ), wraplength=700, foreground="#444").grid(row=0, column=0, columnspan=7, sticky=tk.W, pady=(0,8))

        # DB path
        ttk.Label(tools_frame, text="Where to save the database (file):").grid(row=1, column=0, sticky=tk.W)
        self.db_var = tk.StringVar(value=self.db_path)
        db_entry = ttk.Entry(tools_frame, textvariable=self.db_var, width=50)
        db_entry.grid(row=1, column=1, padx=(5,5))
        db_btn = ttk.Button(tools_frame, text="Browse DB...", command=self.browse_db)
        db_btn.grid(row=1, column=2)

        # Discovery options
        self.discovery_after_var = tk.BooleanVar(value=False)
        disc_after = ttk.Checkbutton(tools_frame, text="After scraping, also look for more government websites", variable=self.discovery_after_var)
        disc_after.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(8,0))
        ttk.Label(tools_frame, text="How many pages to look at (limit):").grid(row=3, column=0, sticky=tk.W)
        self.discover_limit_var = tk.IntVar(value=100)
        ttk.Entry(tools_frame, textvariable=self.discover_limit_var, width=8).grid(row=3, column=1, sticky=tk.W)
        ttk.Label(tools_frame, text="Rounds of link‑following (hops):").grid(row=3, column=2, sticky=tk.E)
        self.discover_hops_var = tk.IntVar(value=1)
        ttk.Entry(tools_frame, textvariable=self.discover_hops_var, width=6).grid(row=3, column=3, sticky=tk.W)
        ttk.Label(tools_frame, text="Start from which group:").grid(row=3, column=4, sticky=tk.E)
        self.seed_level_var = tk.StringVar(value="federal")
        ttk.Combobox(tools_frame, textvariable=self.seed_level_var, values=["federal","state","county","city","local"], width=12).grid(row=3, column=5, sticky=tk.W)

        # Crawl options
        ttk.Label(tools_frame, text="Find contacts (emails/phones) on these sites:").grid(row=4, column=0, sticky=tk.W, pady=(8,0))
        self.crawl_level_var = tk.StringVar(value="state")
        ttk.Combobox(tools_frame, textvariable=self.crawl_level_var, values=["federal","state","county","city","local"], width=10).grid(row=4, column=1, sticky=tk.W)
        ttk.Label(tools_frame, text="How many sites this run:").grid(row=4, column=2, sticky=tk.E)
        self.crawl_limit_var = tk.IntVar(value=50)
        ttk.Entry(tools_frame, textvariable=self.crawl_limit_var, width=8).grid(row=4, column=3, sticky=tk.W)
        ttk.Label(tools_frame, text="Pause between sites (seconds):").grid(row=4, column=4, sticky=tk.E)
        self.crawl_delay_var = tk.DoubleVar(value=1.0)
        ttk.Entry(tools_frame, textvariable=self.crawl_delay_var, width=8).grid(row=4, column=5, sticky=tk.W)

        # Tool buttons
        btn_pipeline = ttk.Button(tools_frame, text="Scrape and build the database", command=self.run_pipeline_btn)
        btn_pipeline.grid(row=5, column=0, pady=(10,0), sticky=tk.W)
        btn_discovery = ttk.Button(tools_frame, text="Find more government websites", command=self.run_discovery_btn)
        btn_discovery.grid(row=5, column=1, pady=(10,0), sticky=tk.W)
        btn_crawl = ttk.Button(tools_frame, text="Find contacts on selected sites", command=self.run_crawl_btn)
        btn_crawl.grid(row=5, column=2, pady=(10,0), sticky=tk.W)
        btn_schedule = ttk.Button(tools_frame, text="Process next batch (later refresh)", command=self.run_schedule_btn)
        btn_schedule.grid(row=5, column=3, pady=(10,0), sticky=tk.W)
        btn_api_start = ttk.Button(tools_frame, text="Start data website (API)", command=self.start_api)
        btn_api_start.grid(row=5, column=5, pady=(10,0), sticky=tk.E)
        btn_api_stop = ttk.Button(tools_frame, text="Stop data website", command=self.stop_api)
        btn_api_stop.grid(row=5, column=6, pady=(10,0), sticky=tk.W)

        # Attach simple tooltips (hover text)
        self._attach_tooltip(db_entry, "Choose where your data is saved. This is a single file database.")
        self._attach_tooltip(db_btn, "Pick a new place or name for the database file.")
        self._attach_tooltip(disc_after, "After scraping the official list, also scan those pages for links to more .gov/.us sites.")
        self._attach_tooltip(btn_pipeline, "Do everything for you: collect the agency list, clean it, make or update the database.")
        self._attach_tooltip(btn_discovery, "Look at the saved websites and add newly found .gov/.us sites to your database.")
        self._attach_tooltip(btn_crawl, "Visit the saved websites and try to collect emails and phone numbers from contact pages.")
        self._attach_tooltip(btn_schedule, "Process a small set now and more later. Useful for regular, gentle refreshes.")
        self._attach_tooltip(btn_api_start, "Start a small local website so other tools can read your data at http://localhost:5000")
        self._attach_tooltip(btn_api_stop, "Turn off the local website (API).")
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
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
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Log text area with scrollbar
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        self.results_label = ttk.Label(results_frame, text="No results yet")
        self.results_label.grid(row=0, column=0, sticky=tk.W)
        
        self.open_folder_btn = ttk.Button(results_frame, text="Open Results Folder", 
                                         command=self.open_results_folder, state=tk.DISABLED)
        self.open_folder_btn.grid(row=0, column=1, sticky=tk.E)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        config_frame.columnconfigure(3, weight=1)
        progress_frame.columnconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)

    # Simple tooltip helper
    def _attach_tooltip(self, widget, text: str):
        tip = Tooltip(self.root, text)
        def on_enter(_): tip.show(widget)
        def on_leave(_): tip.hide()
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)
        
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

    def browse_db(self):
        """Browse for DB file path."""
        file = filedialog.asksaveasfilename(defaultextension=".db", initialfile=os.path.basename(self.db_var.get()) or "government_contacts.db")
        if file:
            self.db_var.set(file)
            self.db_path = file
            
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

    # ---- Pipeline actions ----
    def run_pipeline_btn(self):
        def worker():
            db = self.db_var.get()
            cmd = ["python", "scripts/run_pipeline.py", "--db", db]
            if self.discovery_after_var.get():
                cmd += ["--discover", "--discover-limit", str(self.discover_limit_var.get())]
            self.run_command(cmd)
        threading.Thread(target=worker, daemon=True).start()

    def run_discovery_btn(self):
        def worker():
            db = self.db_var.get()
            cmd = [
                "python", "scripts/discover_gov_sites.py", "--db", db,
                "--from-level", self.seed_level_var.get(),
                "--limit", str(self.discover_limit_var.get()),
                "--hops", str(self.discover_hops_var.get())
            ]
            self.run_command(cmd)
        threading.Thread(target=worker, daemon=True).start()

    def run_crawl_btn(self):
        def worker():
            db = self.db_var.get()
            cmd = [
                "python", "scripts/crawl_contacts_from_db.py", "--db", db,
                "--level", self.crawl_level_var.get(),
                "--limit", str(self.crawl_limit_var.get()),
                "--delay", str(self.crawl_delay_var.get())
            ]
            self.run_command(cmd)
        threading.Thread(target=worker, daemon=True).start()

    def run_schedule_btn(self):
        def worker():
            db = self.db_var.get()
            cmd = [
                "python", "scripts/schedule_crawl.py", "--db", db,
                "--level", self.crawl_level_var.get(),
                "--batch", str(self.crawl_limit_var.get()),
                "--delay", str(self.crawl_delay_var.get())
            ]
            self.run_command(cmd)
        threading.Thread(target=worker, daemon=True).start()

    def start_api(self):
        if self.api_process and self.api_process.poll() is None:
            messagebox.showinfo("API", "API server already running.")
            return
        env = os.environ.copy()
        env['GOV_CONTACTS_DB_PATH'] = self.db_var.get()
        try:
            self.api_process = subprocess.Popen(["python", "src/api/government_contacts_api.py"], env=env)
            self.log_text.insert(tk.END, f"Started API at http://localhost:5000 (DB={env['GOV_CONTACTS_DB_PATH']})\n")
            self.log_text.see(tk.END)
        except Exception as e:
            messagebox.showerror("API", f"Failed to start API: {e}")

    def stop_api(self):
        if self.api_process and self.api_process.poll() is None:
            self.api_process.terminate()
            self.api_process = None
            self.log_text.insert(tk.END, "Stopped API server.\n")
            self.log_text.see(tk.END)
        else:
            messagebox.showinfo("API", "API server is not running.")

    def run_command(self, cmd):
        try:
            self.log_text.insert(tk.END, f"$ {' '.join(cmd)}\n")
            self.log_text.see(tk.END)
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                self.log_text.insert(tk.END, line)
                self.log_text.see(tk.END)
            proc.wait()
            self.log_text.insert(tk.END, f"[exit {proc.returncode}]\n")
            self.log_text.see(tk.END)
        except Exception as e:
            self.log_text.insert(tk.END, f"Command failed: {e}\n")
            self.log_text.see(tk.END)


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


# Lightweight tooltip implementation
class Tooltip:
    def __init__(self, root, text: str):
        self.root = root
        self.text = text
        self.tw = None

    def show(self, widget):
        if self.tw is not None:
            return
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + widget.winfo_height() + 5
        self.tw = tk.Toplevel(widget)
        self.tw.overrideredirect(True)
        self.tw.attributes("-topmost", True)
        label = tk.Label(self.tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         wraplength=360)
        label.pack(ipadx=6, ipy=4)
        self.tw.geometry(f"+{x}+{y}")

    def hide(self):
        if self.tw is not None:
            self.tw.destroy()
            self.tw = None
