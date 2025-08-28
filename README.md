# 🏛️ USA.gov Government Agency Scraper

A reliable, comprehensive scraper for extracting federal agency information from USA.gov with two supported modes: CLI and Desktop GUI. An optional “orchestrated/agent” layer is provided as experimental and is not required for production use.

> Status: Core scraping, cleaning, export utilities, and REST API are supported. Orchestrated/agent components are optional. See `docs/DATA_GUIDANCE.md` for data provenance and recommended pipeline.

## 🎯 Features

- **Complete Agency Coverage**: Scrapes all 400-500+ federal agencies from USA.gov
- **Multiple Interfaces**: Desktop GUI, CLI, and Claude-Flow orchestration  
- **Data Quality**: Built-in validation, deduplication, and error handling
- **Export Formats**: CSV and JSON with timestamped outputs
- **Robust Operation**: Rate limiting, retry logic, and comprehensive logging
- **Progress Tracking**: Real-time progress updates and live log display

## 📊 Output Schema

Each agency record contains:
```json
{
  "agency_name": "Department of Agriculture",
  "homepage_url": "https://www.usda.gov", 
  "parent_department": null,
  "section": "A"
}
```

Output files: `scraped_data/usa_gov_agencies_YYYYMMDD_HHMMSS.csv` and `.json`

## 🚀 Quick Start

### 1. Installation

```bash
# Clone and setup
git clone <repository-url>
cd usa-gov-scraper

# Install dependencies  
pip install -r requirements.txt
```

### 2. Choose Your Interface

#### 🖥️ Desktop GUI (Recommended)
```bash
python desktop_app.py
```
- Visual progress tracking
- Live log output
- Section selection (A-Z or All)
- Output directory selection
- Start/Stop/Clear controls

#### 💻 Command Line Interface
```bash
# Scrape all agencies (default)
python main.py --simple

# Scrape specific section with verbose output  
python main.py --simple --section A --verbose

# Quiet mode with statistics
python main.py --simple --quiet --save-stats
```

#### 🔄 Orchestrated/Agent Mode (Optional)
This path depends on extra, optional packages and is not required. If unavailable, the CLI will fall back to simple mode automatically.

## 🛠️ Command Line Options

```bash
python main.py [OPTIONS]

Options:
   --orchestrated        Run full orchestrated scrape with advanced features (recommended)
   --simple              Run simple scrape without orchestration
   --section LETTER      Scrape only specific section (A-Z)
   --verbose             Enable detailed output and statistics
   --quiet               Suppress console output (logs to file only)
   --save-stats          Save scraping statistics to JSON
   --log-level LEVEL     Set logging level (DEBUG/INFO/WARNING/ERROR)
   -h, --help           Show help message
```

## 📁 Project Structure

```
usa-gov-scraper/
├── main.py              # CLI interface
├── desktop_app.py       # Desktop GUI application  
├── scraper/
│   └── core.py         # Core scraping functionality
├── tests/
│   └── test_scraper.py # Comprehensive test suite
├── scraped_data/       # Output directory for CSV/JSON files
├── logs/              # Application logs
└── requirements.txt   # Python dependencies
```

## 🧪 Testing

Run the comprehensive test suite:
```bash
# Run all tests
pytest tests/ -v

# Test specific functionality
pytest tests/test_scraper.py::TestGovernmentAgencyScraper -v
```

Test coverage varies by implementation status. Run tests to see current results.

## 📋 Usage Examples

### Desktop GUI Workflow
1. Launch: `python desktop_app.py`
2. Select section (or "All" for complete scrape)
3. Choose output directory
4. Click "Start Scraping"
5. Monitor progress and logs in real-time
6. Click "Open Results Folder" when complete

### CLI Workflow Examples
```bash
# Full orchestrated scraping (recommended)
python main.py --orchestrated

# Simple scraping without orchestration
python main.py --simple

# Orchestrated scrape of specific section
python main.py --orchestrated --section D --verbose

# Production mode with statistics
python main.py --quiet --save-stats --log-level WARNING
```

### Sample Output
```
============================================================
USA.gov Government Agency Scraper  
============================================================

INFO - Starting orchestrated government agency scrape
INFO - Orchestrating all sections A-Z
INFO - Orchestrated scraping completed successfully!
INFO - Found agencies across sections
INFO - Duration: XX.X seconds
INFO - Dynamic agents created: X
INFO - Validation: XXX/XXX valid agencies
INFO - Data exported to:
INFO -   CSV: output/government_contacts_20250826_XXXXXX.csv
INFO -   JSON: output/government_contacts_20250826_XXXXXX.json

✓ Scraping completed successfully!
```

## ⚙️ Configuration

### Environment Variables
```bash
# Optional: For advanced features
OPENAI_API_KEY=sk-...    # For Flow orchestration (optional)
```

### Rate Limiting
- Default: 0.5 seconds between requests
- Configurable in `scraper/core.py`
- Respects USA.gov servers

## 🔧 Advanced Features

### Data Validation
- Automatic URL format validation
- Empty field detection
- Duplicate removal
- Schema compliance checking

### Error Handling  
- Automatic retry with exponential backoff
- Comprehensive error logging
- Graceful degradation on partial failures
- Resume capability for interrupted scrapes

### Performance Optimization
- Request session reuse
- Intelligent caching
- Parallel processing capability
- Memory-efficient parsing

## 🤝 Orchestration (Optional)
Experimental agent-based components exist but are not required for the main pipeline. They may need additional dependencies and configuration.

## 📊 Performance Metrics

Performance varies based on implementation status and network conditions:

- **Typical Runtime**: Varies by mode and network speed
- **Success Rate**: Depends on current implementation completeness
- **Data Quality**: Validation removes fake/demo content automatically
- **Coverage**: Federal agencies from USA.gov directory
- **Memory Usage**: Efficient processing with proper cleanup

## 🧰 End-to-End Runbook (Recommended)

1) Scrape (Simple)
   - `python main.py --simple --log-level INFO`

2) Clean data
   - `python data_cleanup.py --input-dir scraped_data --output-dir output_clean`

3) Initialize DB schema
   - `python scripts/db_init.py --db government_contacts.db`

4) Load agencies into DB
   - `python scripts/load_from_csv.py --db government_contacts.db --agencies output_clean/usa_gov_agencies_*.csv`

5) Run REST API
   - Set `GOV_CONTACTS_DB_PATH` to the DB (or place it at project root)
   - `python src/api/government_contacts_api.py`

See `docs/DATA_GUIDANCE.md` for authoritative vs. non-authoritative data.

## 🐛 Troubleshooting

### Common Issues

**Empty results or low count:**
- Check internet connection
- Verify USA.gov is accessible
- Try single section first: `--section A`

**Import errors:**
```bash
# Install missing dependencies
pip install -r requirements.txt

# For development/testing
pip install pytest pytest-mock
```

**Permission errors:**
```bash
# Create output directory manually
mkdir scraped_data logs
```

### Debug Mode
```bash
# Maximum verbosity for debugging
python main.py --simple --log-level DEBUG --verbose
```

## 🎯 Acceptance Criteria

✅ **CLI Tests**:
- `python main.py --orchestrated --section A` → Valid CSV/JSON output
- `pytest tests/ -v` → Tests pass based on implementation status
- Progress tracking and error handling work

✅ **Desktop Tests**: 
- GUI launches and controls work
- Progress bar updates during scraping  
- Log output displays in real-time
- Results folder opens correctly

✅ **Data Quality**:
- CSV/JSON format compliance
- Schema validation passes
- Unique URLs per agency
- No empty required fields

## ⚠️ Known Limitations & Current Status

### Implementation Status
This project is under active development. While core functionality works, some advanced features are partially implemented or contain placeholder code.

### Current Limitations

#### 🚫 Not Yet Implemented
- **Distributed Processing**: The distributed processing coordinator framework exists but requires network communication layer implementation
- **Cloud Backup**: Cloud storage integration (S3, GCS) requires appropriate libraries and credentials
- **Advanced Analytics**: Some analytics features use placeholder implementations
- **Real-time Monitoring**: Some monitoring components are simulation-based

#### ⚠️ Partially Implemented
- **Orchestration Mode**: Basic orchestration framework exists but some agents are placeholders
- **Performance Optimization**: Optimization modules exist but may not be fully integrated
- **Error Recovery**: Some error handling uses generic fallbacks

#### ✅ Working Features
- **Core Scraping**: USA.gov agency scraping works reliably
- **Data Export**: CSV/JSON export with validation
- **Desktop GUI**: Full Tkinter interface with progress tracking
- **CLI Interface**: Command-line operation with all basic features
- **Data Cleanup**: Tools to remove fake/demo content from production data

### Development Recommendations

1. **For Production Use**: Stick to `--simple` mode for reliable operation
2. **Data Validation**: Always run data cleanup script on production data
3. **Testing**: Test coverage varies - run tests to verify current status
4. **Dependencies**: Some advanced features require additional libraries

### Getting Help
- Check logs for detailed error information
- Use `--verbose` flag for debugging
- Run `data_cleanup.py` if you suspect data quality issues

## 📝 License

MIT License - See LICENSE file for details.

## 🙏 Acknowledgments

- **USA.gov** for providing public agency data
- **BeautifulSoup** for HTML parsing
- **Requests** for HTTP client functionality
- **Claude-Flow** for AI orchestration capabilities

---

**Built with ❤️ for government transparency and civic engagement**
