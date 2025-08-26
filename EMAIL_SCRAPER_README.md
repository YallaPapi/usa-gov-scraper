# 🏛️ Government Email Scraper - Botasaurus Powered

**Complete email and contact scraping system for federal agencies and local government websites**

## 🎯 What This System Does

This is a **comprehensive government contact extraction platform** that:

1. **Scrapes emails from all 400+ federal agency websites** we already discovered
2. **Discovers and scrapes local government sites** (cities, counties, states) 
3. **Extracts contact information** including emails, phone numbers, and addresses
4. **Provides multiple interfaces** for different use cases

## 🚀 Key Features

### ✅ **Federal Agency Email Extraction**
- **Input**: Uses our existing CSV files with 400+ federal agency URLs
- **Output**: Comprehensive contact database with emails, phone numbers, addresses
- **Performance**: Botasaurus-powered with caching, retry logic, parallel processing
- **Discovery**: Also discovers related government sites during scraping

### ✅ **Local Government Site Discovery**
- **Search-Based Discovery**: Uses DuckDuckGo to find city, county, state websites
- **Intelligent Classification**: Automatically categorizes sites by government type
- **Contact Extraction**: Scrapes emails, phones, addresses from discovered sites
- **Scalable**: Can target specific states, cities, or regions

### ✅ **Advanced Web Scraping Technology**
- **Botasaurus Framework**: Enterprise-grade scraping with anti-detection
- **Browser Automation**: Can handle JavaScript-heavy sites when needed
- **Rate Limiting**: Respectful scraping with configurable delays
- **Error Handling**: Automatic retries with exponential backoff
- **Data Validation**: Ensures high-quality, properly formatted contact data

## 📁 File Structure

```
scrapers/
├── email_scraper.py          # Federal agency email scraper
├── local_gov_crawler.py      # Local government site discovery
├── comprehensive_scraper.py  # Orchestrator for both federal + local
└── botasaurus_core.py        # Enhanced core with Botasaurus

interfaces/
├── email_scraper_gui_fixed.py  # Desktop GUI application
├── main.py                     # CLI interface (original)
└── desktop_app.py             # Original desktop app

output_directories/
├── scraped_contacts/          # Federal agency emails
├── local_gov_sites/          # Local government contacts
└── comprehensive_contacts/   # Combined results
```

## 🖥️ How to Use

### Method 1: Desktop GUI (Recommended)
```bash
python email_scraper_gui_fixed.py
```

**Features:**
- 🎯 **Scraping Modes**: Federal Only, Local Only, Single Agency Test
- 📊 **Real-time Statistics**: Live progress tracking and contact counts
- 📝 **Live Logging**: See exactly what's happening during scraping
- 📁 **Easy Results Access**: One-click folder opening
- ⚙️ **Simple Configuration**: Browse for input files and output directories

**GUI Usage:**
1. Select scraping mode (Federal/Local/Test)
2. Choose your agencies CSV file (we have several good ones)
3. Set output directory 
4. Click "🚀 Start Scraping"
5. Watch real-time progress and logs
6. Click "📁 Results Folder" when complete

### Method 2: Command Line Interface
```bash
# Scrape federal agencies only
python scrapers/email_scraper.py

# Discover and scrape local government sites  
python scrapers/local_gov_crawler.py

# Comprehensive scraping (both federal and local)
python scrapers/comprehensive_scraper.py
```

## 📊 Current Results

**From our test runs:**

### Federal Agency Scraping (Single Agency Test)
- **AbilityOne Commission**: Found **11 unique emails** including:
  - `info@abilityone.gov`
  - `slesko@abilityone.gov` 
  - `awards@abilityone.gov`
  - `policy@abilityone.gov`
  - `mjurkowski@abilityone.gov`
- **Sites Discovered**: 113 related government sites found during scraping
- **Performance**: 50 sites scraped in ~70 seconds

### Local Government Discovery
- **Sites Discovered**: 189 local government websites across major cities
- **Sample Sites**: 
  - `https://www.nyc.gov/` (New York City)
  - `https://www.miami.gov/` (Miami)
  - `https://www.tampa.gov/` (Tampa)
  - `https://www.jacksonville.gov/` (Jacksonville)
- **Contacts Found**: Phone numbers, addresses, some emails
- **Example Contact**: `305-468-5900` from Miami government

## 🎯 Scaling Up

**To scrape ALL federal agencies:**
1. Use our comprehensive CSV: `scraped_data/all_agencies_20250825_150513.csv` (579 agencies)
2. Run Federal Only mode in GUI
3. Expected results: **500-1000+ unique government emails**
4. Runtime: ~2-4 hours for complete federal scraping

**To discover thousands of local government sites:**
1. Run Local Only mode with expanded city lists
2. Target specific states or regions
3. Expected results: **1000+ local government sites with contacts**

## 🛠️ Technical Architecture

### Botasaurus Integration
```python
@request(
    cache=True,           # Caches responses to avoid re-requests
    max_retry=3,          # Automatic retry on failures  
    parallel=5            # Parallel processing for speed
)
def scrape_website_emails(request, url):
    # Advanced email extraction with multiple patterns
    # Government site discovery and link following
    # Contact information extraction
```

### Data Quality Features
- **Email Validation**: Regex patterns for proper email format
- **Deduplication**: Automatic removal of duplicate contacts
- **Phone Number Extraction**: Multiple US phone number formats
- **Address Recognition**: Street address pattern matching
- **Site Classification**: Automatic government type detection

### Export Formats
- **CSV**: Structured data for spreadsheet analysis
- **JSON**: Machine-readable format for further processing
- **Timestamped Files**: All outputs include date/time stamps
- **Consolidated Databases**: Master contact databases combining all sources

## 🔍 Data Schema

### Federal Agency Contacts
```csv
agency_name,website,email,phone,contact_type
AbilityOne Commission,https://www.abilityone.gov/,info@abilityone.gov,,email
AbilityOne Commission,https://www.abilityone.gov/,slesko@abilityone.gov,,email
```

### Local Government Contacts  
```csv
site_url,site_title,site_type,contact_type,contact_value
https://www.miami.gov/,Miami Government,city,phone,305-468-5900
https://www.nyc.gov/,New York City,city,email,info@nyc.gov
```

## 🚨 Important Notes

### Ethical Usage
- **Respectful Scraping**: Built-in rate limiting and delays
- **Public Information Only**: Scrapes only publicly available contact information
- **Government Transparency**: Supports civic engagement and public access

### Performance Considerations
- **Federal Scraping**: ~400+ sites will take 2-4 hours
- **Local Discovery**: Can generate thousands of sites to scrape
- **Resource Usage**: Moderate CPU/memory, network intensive
- **Caching**: Botasaurus caching prevents redundant requests

### Output Management
- **Large Datasets**: Federal + Local scraping can generate 10,000+ contacts
- **File Organization**: Timestamped files prevent overwrites
- **Directory Structure**: Organized by source type (federal/local)

## 🏆 Success Metrics

**What Success Looks Like:**
- ✅ **Federal**: 400+ agencies → 500-1000+ unique government emails
- ✅ **Local**: Major cities → 1000+ local government contacts  
- ✅ **Quality**: >95% valid email addresses and phone numbers
- ✅ **Completeness**: Contact info for all levels of government
- ✅ **Usability**: Easy-to-use interfaces for non-technical users

## 🎯 Next Steps

1. **Run Full Federal Scraping**: Use GUI with "Federal Only" mode
2. **Expand Local Discovery**: Target all 50 states
3. **Create Master Database**: Combine all federal + local contacts
4. **Export for CRM**: Create formats suitable for contact management systems
5. **Schedule Regular Updates**: Set up periodic re-scraping for fresh data

---

**This system transforms the basic USA.gov agency list into a comprehensive government contact database spanning federal, state, and local levels! 🚀**