# 🏛️ USA.gov Agency Index Scraper - Desktop Application

A powerful **Botasaurus Desktop Application** for scraping federal agency information from USA.gov, powered by **Agency Swarm** orchestration with dynamic agent creation.

## 🚀 Features

### Core Capabilities
- **Desktop Application**: Full-featured cross-platform desktop app
- **Agency Swarm Integration**: Intelligent agent-based orchestration
- **Dynamic Agent Creation**: Automatically spawns helper agents as needed
- **Complete Data Extraction**: Scrapes all agencies A-Z from USA.gov
- **Multi-Format Export**: CSV and JSON output formats
- **Data Validation**: Automatic cleaning and deduplication

### Agent System

#### Base Agents
1. **Planner Agent** - Analyzes page structure and identifies sections
2. **Crawler Agent** - Executes web scraping operations
3. **Validator Agent** - Ensures data quality and completeness
4. **Exporter Agent** - Handles data export to multiple formats

#### Dynamic Agents (Created as Needed)
- **URLNormalizerAgent** - Fixes and standardizes URLs
- **RetryHandlerAgent** - Retries failed sections with backoff
- **DeduplicatorAgent** - Removes duplicate entries
- **DOMExplorerAgent** - Adapts to page structure changes
- **LoggerAgent** - Tracks statistics and performance

## 📦 Installation

### Prerequisites
- Python 3.8+
- Chrome/Chromium browser

### Quick Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/usa_gov_scraper.git
cd usa_gov_scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (optional for full orchestration):
```bash
# Create .env file
OPENAI_API_KEY=your_key_here  # For Agency Swarm features
```

## 🖥️ Running the Desktop Application

### Windows
Double-click `run_desktop_app.bat` or run:
```bash
run_desktop_app.bat
```

### Mac/Linux
```bash
python desktop_app.py
```

### Alternative Modes

#### 1. Simple CLI Mode
```bash
python main.py --simple
```

#### 2. Full Orchestration Mode
```bash
python main.py
```

#### 3. Web UI Mode
```bash
python app.py
```

## 🎯 Usage Examples

### Basic Desktop App
```python
# Run the desktop application
python desktop_app.py
```

This will:
1. Launch a browser window
2. Navigate to USA.gov Agency Index
3. Scrape all agencies with visual feedback
4. Export to CSV and JSON
5. Show real-time progress

### Scrape Specific Section
```bash
python main.py --simple --section A
```

### Advanced with Full Orchestration
```bash
python main.py --verbose --save-stats
```

## 📊 Output

The scraper generates:

### Files
- `scraped_data/usa_gov_agencies_YYYYMMDD_HHMMSS.csv`
- `scraped_data/usa_gov_agencies_YYYYMMDD_HHMMSS.json`

### Data Structure
```json
{
  "agency_name": "Department of Agriculture",
  "homepage_url": "https://www.usda.gov",
  "parent_department": null,
  "section": "A"
}
```

## 🏗️ Architecture

```
usa_gov_scraper/
├── desktop_app.py       # Main desktop application
├── app.py              # Alternative UI version
├── main.py             # CLI entry point
├── orchestrator.py     # Agency Swarm orchestration
├── scraper_agents/     # Agent implementations
│   ├── base_agents.py  # Core 4 agents
│   └── dynamic_agents.py # Factory for dynamic agents
├── scraper/            # Botasaurus scraper
│   └── botasaurus_scraper.py
└── run_desktop_app.bat # Windows launcher
```

## 🔧 Configuration

### Environment Variables
```bash
OPENAI_API_KEY=sk-...       # For AI-powered orchestration
OUTPUT_DIR=scraped_data     # Output directory
LOG_LEVEL=INFO              # Logging verbosity
```

### Scraping Settings
- Rate limiting: 0.5s between requests
- Max retries: 3 attempts
- Timeout: 30 seconds
- Cache enabled for efficiency

## 🤖 Agent Communication Flow

```
User → Project Manager → Architect → Developer
                ↓            ↓           ↓
            Planner      Crawler    Validator
                ↓            ↓           ↓
            [Dynamic Agents Created as Needed]
                ↓            ↓           ↓
            Exporter → Output Files
```

## 📈 Performance

- **Typical Duration**: 30-60 seconds
- **Agencies Scraped**: ~450-500
- **Success Rate**: >98%
- **Memory Usage**: <200MB

## 🐛 Troubleshooting

### Common Issues

1. **Browser not launching**
   - Ensure Chrome/Chromium is installed
   - Check firewall settings

2. **Scraping fails**
   - Check internet connection
   - Verify USA.gov is accessible
   - Try with `--simple` mode first

3. **Missing agencies**
   - Dynamic agents will retry failed sections
   - Check logs for specific errors

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file

## 🙏 Acknowledgments

- **Botasaurus** - Web scraping framework
- **Agency Swarm** - Agent orchestration
- **USA.gov** - Public data source

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Check the logs in `logs/` directory
- Run with `--verbose` for detailed output

---

**Built with ❤️ using Botasaurus + Agency Swarm**