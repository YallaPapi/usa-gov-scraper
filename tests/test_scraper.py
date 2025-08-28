"""
Comprehensive test suite for USA.gov Government Agency Scraper
Tests core functionality, CLI interface, and data validation
"""

import pytest
import json
import csv
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

from scraper.core import GovernmentAgencyScraper


class TestGovernmentAgencyScraper:
    """Test the core scraper functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = GovernmentAgencyScraper(rate_limit=0.1, max_retries=2)
        
        # Mock HTML content for testing
        self.mock_html = """
        <html>
            <body>
                <h2>Agriculture Department (USDA)</h2>
                <p>Leading agriculture policy...</p>
                <a href="https://www.usda.gov">Visit USDA</a>
                
                <h2>Army</h2>
                <p>Military branch...</p>
                <a href="https://www.army.mil">Visit Army</a>
                
                <h2>Bureau of Labor Statistics</h2>
                <p>Labor data and statistics...</p>
                <a href="https://www.bls.gov">Visit BLS</a>
            </body>
        </html>
        """
    
    def test_parse_agency_section_a(self):
        """Test parsing section A agencies."""
        soup = BeautifulSoup(self.mock_html, 'html.parser')
        agencies = self.scraper.parse_agency_section(soup, 'A')
        
        # Should find Agriculture Department and Army
        assert len(agencies) == 2
        
        # Check Agriculture Department
        ag_dept = next((a for a in agencies if 'Agriculture' in a['agency_name']), None)
        assert ag_dept is not None
        assert ag_dept['homepage_url'] == 'https://www.usda.gov'
        assert ag_dept['section'] == 'A'
        
        # Check Army
        army = next((a for a in agencies if 'Army' in a['agency_name']), None)
        assert army is not None
        assert army['homepage_url'] == 'https://www.army.mil'
    
    def test_parse_agency_section_b(self):
        """Test parsing section B agencies."""
        soup = BeautifulSoup(self.mock_html, 'html.parser')
        agencies = self.scraper.parse_agency_section(soup, 'B')
        
        # Should find Bureau of Labor Statistics
        assert len(agencies) == 1
        
        bls = agencies[0]
        assert 'Bureau of Labor Statistics' in bls['agency_name']
        assert bls['homepage_url'] == 'https://www.bls.gov'
        assert bls['section'] == 'B'
    
    def test_parse_agency_section_empty(self):
        """Test parsing section with no matching agencies."""
        soup = BeautifulSoup(self.mock_html, 'html.parser')
        agencies = self.scraper.parse_agency_section(soup, 'Z')
        
        assert len(agencies) == 0
    
    @patch('scraper.core.requests.Session.get')
    def test_scrape_section_success(self, mock_get):
        """Test successful section scraping."""
        mock_response = Mock()
        mock_response.text = self.mock_html
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.scraper.scrape_section('A')
        
        assert result['success'] is True
        assert result['section'] == 'A'
        assert result['agency_count'] == 2
        assert len(result['agencies']) == 2
    
    @patch('scraper.core.requests.Session.get')
    def test_scrape_section_http_error(self, mock_get):
        """Test section scraping with HTTP error."""
        mock_get.side_effect = Exception("HTTP 500 Error")
        
        result = self.scraper.scrape_section('A')
        
        assert result['success'] is False
        assert 'error' in result
        assert result['agencies'] == []
    
    @patch('scraper.core.requests.Session.get')
    def test_scrape_section_retry_logic(self, mock_get):
        """Test retry logic on failures."""
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.text = self.mock_html
        mock_response.raise_for_status.return_value = None
        
        mock_get.side_effect = [Exception("Network error"), mock_response]
        
        result = self.scraper.scrape_section('A')
        
        assert result['success'] is True
        assert mock_get.call_count == 2
    
    def test_validate_data_valid(self):
        """Test data validation with valid data."""
        agencies = [
            {
                'agency_name': 'Test Agency',
                'homepage_url': 'https://example.gov',
                'parent_department': None,
                'section': 'T'
            }
        ]
        
        validation = self.scraper.validate_data(agencies)
        
        assert validation['validation_passed'] is True
        assert validation['valid_agencies'] == 1
        assert validation['invalid_agencies'] == 0
        assert len(validation['issues']) == 0
    
    def test_validate_data_invalid(self):
        """Test data validation with invalid data."""
        agencies = [
            {
                'agency_name': '',  # Empty name
                'homepage_url': 'invalid-url',  # Invalid URL
                'parent_department': None,
                'section': ''  # Missing section
            }
        ]
        
        validation = self.scraper.validate_data(agencies)
        
        assert validation['validation_passed'] is False
        assert validation['valid_agencies'] == 0
        assert validation['invalid_agencies'] == 1
        assert len(validation['issues']) == 3
    
    def test_export_data_csv_json(self):
        """Test data export to CSV and JSON."""
        agencies = [
            {
                'agency_name': 'Test Agency',
                'homepage_url': 'https://example.gov',
                'parent_department': None,
                'section': 'T'
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            export_paths = self.scraper.export_data(agencies, temp_dir)
            
            # Check files were created
            assert os.path.exists(export_paths['csv'])
            assert os.path.exists(export_paths['json'])
            
            # Check CSV content
            with open(export_paths['csv'], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                csv_data = list(reader)
                assert len(csv_data) == 1
                assert csv_data[0]['agency_name'] == 'Test Agency'
            
            # Check JSON content
            with open(export_paths['json'], 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                assert len(json_data) == 1
                assert json_data[0]['agency_name'] == 'Test Agency'
    
    def test_export_data_empty(self):
        """Test data export with empty dataset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_paths = self.scraper.export_data([], temp_dir)
            
            # Files should still be created
            assert os.path.exists(export_paths['csv'])
            assert os.path.exists(export_paths['json'])
            
            # Check empty CSV has headers
            with open(export_paths['csv'], 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'agency_name,homepage_url' in content


class TestCLIInterface:
    """Test the CLI interface functionality."""
    
    def test_argument_parsing_simple(self):
        """Test basic argument parsing."""
        from main import main
        import sys
        
        # Test --simple flag
        test_args = ['main.py', '--simple']
        with patch.object(sys, 'argv', test_args):
            with patch('main.run_simple_scrape', return_value=0):
                with patch('main.setup_logging'):
                    try:
                        main()
                    except SystemExit as e:
                        assert e.code == 0
    
    def test_argument_parsing_section(self):
        """Test section argument parsing."""
        from main import main
        import sys
        
        test_args = ['main.py', '--simple', '--section', 'A']
        with patch.object(sys, 'argv', test_args):
            with patch('main.run_simple_scrape', return_value=0):
                with patch('main.setup_logging'):
                    try:
                        main()
                    except SystemExit as e:
                        assert e.code == 0
    
    def test_invalid_section_argument(self):
        """Test invalid section argument handling."""
        from main import main
        import sys
        
        test_args = ['main.py', '--simple', '--section', 'ABC']
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit):
                main()


class TestDataSchema:
    """Test data schema and format compliance."""
    
    def test_agency_record_schema(self):
        """Test that agency records have required fields."""
        required_fields = {'agency_name', 'homepage_url', 'parent_department', 'section'}
        
        agency = {
            'agency_name': 'Test Agency',
            'homepage_url': 'https://example.gov',
            'parent_department': None,
            'section': 'T'
        }
        
        assert set(agency.keys()) == required_fields
    
    def test_csv_json_parity(self):
        """Test that CSV and JSON exports contain same data."""
        scraper = GovernmentAgencyScraper()
        
        agencies = [
            {
                'agency_name': 'Test Agency 1',
                'homepage_url': 'https://example1.gov',
                'parent_department': None,
                'section': 'T'
            },
            {
                'agency_name': 'Test Agency 2',
                'homepage_url': 'https://example2.gov',
                'parent_department': 'Parent Dept',
                'section': 'T'
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            export_paths = scraper.export_data(agencies, temp_dir)
            
            # Load CSV data
            with open(export_paths['csv'], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                csv_data = list(reader)
            
            # Load JSON data
            with open(export_paths['json'], 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Compare data
            assert len(csv_data) == len(json_data)
            
            for csv_row, json_row in zip(csv_data, json_data):
                assert csv_row['agency_name'] == json_row['agency_name']
                assert csv_row['homepage_url'] == json_row['homepage_url']
                assert csv_row['section'] == json_row['section']


# Integration test
class TestEndToEnd:
    """End-to-end integration tests."""
    
    @patch('scraper.core.requests.Session.get')
    def test_full_workflow(self, mock_get):
        """Test complete scraping workflow."""
        mock_html = """
        <html><body>
            <h2>Agriculture Department</h2>
            <a href="https://www.usda.gov">USDA</a>
        </body></html>
        """
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        scraper = GovernmentAgencyScraper(rate_limit=0.1)
        
        # Test section scraping
        result = scraper.scrape_section('A')
        assert result['success'] is True
        assert len(result['agencies']) == 1
        
        # Test validation
        validation = scraper.validate_data(result['agencies'])
        assert validation['validation_passed'] is True
        
        # Test export
        with tempfile.TemporaryDirectory() as temp_dir:
            export_paths = scraper.export_data(result['agencies'], temp_dir)
            assert os.path.exists(export_paths['csv'])
            assert os.path.exists(export_paths['json'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
