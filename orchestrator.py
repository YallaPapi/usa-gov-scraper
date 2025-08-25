"""
Orchestration System for USA.gov Agency Index Scraper
Coordinates base agents and dynamically created agents using Agency Swarm
"""

from agency_swarm import Agency
import openai
from scraper_agents.base_agents import PlannerAgent, CrawlerAgent, ValidatorAgent, ExporterAgent
from scraper_agents.dynamic_agents import DynamicAgentFactory
from scraper.botasaurus_scraper import AgencyIndexScraper
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AgencyIndexOrchestratorSystem:
    """Orchestration system for the USA.gov Agency Index scraper."""
    
    def __init__(self, use_openai: bool = True):
        """
        Initialize the orchestration system.
        
        Args:
            use_openai: Whether to use OpenAI for agent communication
        """
        # Set OpenAI key if using OpenAI
        if use_openai:
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                openai.api_key = openai_key
            else:
                print("Warning: OPENAI_API_KEY not found in environment")
        
        # Initialize base agents
        self.planner = PlannerAgent()
        self.crawler = CrawlerAgent()
        self.validator = ValidatorAgent()
        self.exporter = ExporterAgent()
        
        # Initialize Agency Swarm
        self.swarm = Agency(
            agents=[self.planner, self.crawler, self.validator, self.exporter],
            shared_instructions="""
            You are part of a specialized agency tasked with scraping the USA.gov Agency Index.
            Work collaboratively to ensure complete and accurate data extraction.
            Follow these principles:
            1. Be thorough - capture all agencies without missing any
            2. Be accurate - ensure data quality and validation
            3. Be efficient - minimize redundant work
            4. Be adaptive - create helper agents when needed
            5. Be transparent - log all activities and issues
            """,
            temperature=0.3,
            max_prompt_tokens=25000
        )
        
        # Track dynamically created agents
        self.dynamic_agents = {}
        
        # Initialize the Botasaurus scraper
        self.scraper = AgencyIndexScraper()
        
        # Track orchestration state
        self.orchestration_state = {
            'status': 'initialized',
            'sections_planned': [],
            'sections_completed': [],
            'agencies_scraped': [],
            'validation_results': None,
            'export_results': None,
            'dynamic_agents_created': [],
            'errors': [],
            'start_time': None,
            'end_time': None
        }
    
    def create_dynamic_agent(self, agent_type: str, reason: str = "", **kwargs) -> Any:
        """
        Dynamically create and register a new agent.
        
        Args:
            agent_type: Type of agent to create
            reason: Reason for creating this agent
            **kwargs: Additional parameters for agent creation
            
        Returns:
            The created agent instance
        """
        try:
            # Create the agent
            agent = DynamicAgentFactory.create_agent(agent_type, **kwargs)
            
            # Add to swarm
            self.swarm.add_agent(agent)
            
            # Track the agent
            self.dynamic_agents[agent.name] = agent
            self.orchestration_state['dynamic_agents_created'].append({
                'type': agent_type,
                'name': agent.name,
                'reason': reason,
                'created_at': datetime.now().isoformat()
            })
            
            print(f"✓ Created dynamic agent: {agent.name} (Reason: {reason})")
            
            return agent
            
        except Exception as e:
            error_msg = f"Failed to create {agent_type} agent: {str(e)}"
            self.orchestration_state['errors'].append(error_msg)
            print(f"✗ {error_msg}")
            return None
    
    def run_scraping_process(self, target_url: str = "https://www.usa.gov/agency-index") -> Dict[str, Any]:
        """
        Run the complete scraping process with orchestration.
        
        Args:
            target_url: URL of the USA.gov Agency Index
            
        Returns:
            Dictionary with scraping results and statistics
        """
        print("=" * 60)
        print("Starting USA.gov Agency Index Scraping Process")
        print("=" * 60)
        
        self.orchestration_state['start_time'] = datetime.now()
        self.orchestration_state['status'] = 'running'
        
        try:
            # Phase 1: Planning
            print("\n▶ Phase 1: Planning")
            print("-" * 40)
            sections = self._planning_phase(target_url)
            
            # Phase 2: Crawling
            print("\n▶ Phase 2: Crawling")
            print("-" * 40)
            all_agencies = self._crawling_phase(sections)
            
            # Phase 3: Validation
            print("\n▶ Phase 3: Validation")
            print("-" * 40)
            validated_agencies = self._validation_phase(all_agencies)
            
            # Phase 4: Export
            print("\n▶ Phase 4: Export")
            print("-" * 40)
            export_results = self._export_phase(validated_agencies)
            
            # Complete orchestration
            self.orchestration_state['end_time'] = datetime.now()
            self.orchestration_state['status'] = 'completed'
            
            # Calculate duration
            duration = (self.orchestration_state['end_time'] - self.orchestration_state['start_time']).total_seconds()
            
            # Prepare final results
            results = {
                'success': True,
                'agencies': validated_agencies,
                'statistics': {
                    'total_agencies': len(validated_agencies),
                    'sections_scraped': len(self.orchestration_state['sections_completed']),
                    'dynamic_agents_created': len(self.orchestration_state['dynamic_agents_created']),
                    'duration_seconds': duration,
                    'errors_encountered': len(self.orchestration_state['errors'])
                },
                'export_paths': export_results,
                'dynamic_agents': [a['name'] for a in self.orchestration_state['dynamic_agents_created']]
            }
            
            print("\n" + "=" * 60)
            print("✓ Scraping Process Completed Successfully!")
            print(f"  • Total agencies: {len(validated_agencies)}")
            print(f"  • Duration: {duration:.2f} seconds")
            print(f"  • Files exported: {', '.join(export_results.values())}")
            print("=" * 60)
            
            return results
            
        except Exception as e:
            self.orchestration_state['status'] = 'failed'
            self.orchestration_state['errors'].append(str(e))
            
            print(f"\n✗ Scraping process failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'agencies': [],
                'orchestration_state': self.orchestration_state
            }
    
    def _planning_phase(self, target_url: str) -> List[str]:
        """
        Planning phase: Identify target sections.
        
        Args:
            target_url: URL to analyze
            
        Returns:
            List of section IDs to scrape
        """
        print("• Analyzing page structure...")
        
        # Use the planner agent's tool directly
        from scraper_agents.base_agents import IdentifyTargetSectionsTool
        tool = IdentifyTargetSectionsTool(url=target_url)
        result = json.loads(tool.run())
        
        sections = [s['id'] for s in result.get('sections', [])]
        self.orchestration_state['sections_planned'] = sections
        
        print(f"✓ Found {len(sections)} sections to scrape")
        print(f"  Sections: {', '.join(sections)}")
        print(f"  Estimated agencies: {result.get('total_agencies_estimated', 'unknown')}")
        
        return sections
    
    def _crawling_phase(self, sections: List[str]) -> List[Dict[str, Any]]:
        """
        Crawling phase: Scrape all sections.
        
        Args:
            sections: List of section IDs to scrape
            
        Returns:
            List of all scraped agencies
        """
        all_agencies = []
        failed_sections = []
        
        print(f"• Scraping {len(sections)} sections...")
        
        for i, section_id in enumerate(sections, 1):
            print(f"  [{i}/{len(sections)}] Scraping section {section_id}...", end=" ")
            
            try:
                # Use the crawler agent's tool directly
                from scraper_agents.base_agents import ScrapeSectionTool
                tool = ScrapeSectionTool(section_id=section_id)
                result = json.loads(tool.run())
                
                if 'agencies' in result and result['agencies']:
                    agencies = result['agencies']
                    all_agencies.extend(agencies)
                    self.orchestration_state['sections_completed'].append(section_id)
                    print(f"✓ ({len(agencies)} agencies)")
                else:
                    print(f"✗ (no agencies found)")
                    failed_sections.append(section_id)
                    
            except Exception as e:
                print(f"✗ (error: {str(e)})")
                failed_sections.append(section_id)
                self.orchestration_state['errors'].append(f"Failed to scrape section {section_id}: {str(e)}")
        
        # Handle failed sections with retry agent if needed
        if failed_sections:
            print(f"\n• Handling {len(failed_sections)} failed sections...")
            
            # Create retry agent if not exists
            if 'retry' not in self.dynamic_agents:
                self.create_dynamic_agent(
                    'retry',
                    reason=f"Retry failed sections: {', '.join(failed_sections)}"
                )
            
            # Retry failed sections
            for section_id in failed_sections:
                print(f"  Retrying section {section_id}...", end=" ")
                
                from scraper_agents.dynamic_agents import RetryScrapeTool
                tool = RetryScrapeTool(
                    failed_item={'section_id': section_id, 'url': 'https://www.usa.gov/agency-index'}
                )
                result = json.loads(tool.run())
                
                if result.get('success') and result.get('agencies'):
                    agencies = result['agencies']
                    all_agencies.extend(agencies)
                    self.orchestration_state['sections_completed'].append(section_id)
                    print(f"✓ ({len(agencies)} agencies)")
                else:
                    print(f"✗ (retry failed)")
        
        self.orchestration_state['agencies_scraped'] = all_agencies
        print(f"\n✓ Total agencies scraped: {len(all_agencies)}")
        
        return all_agencies
    
    def _validation_phase(self, agencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validation phase: Validate and clean the data.
        
        Args:
            agencies: List of scraped agencies
            
        Returns:
            List of validated and cleaned agencies
        """
        print(f"• Validating {len(agencies)} agencies...")
        
        # Use the validator agent's tool
        from scraper_agents.base_agents import ValidateDataTool
        tool = ValidateDataTool(data=agencies)
        result = json.loads(tool.run())
        
        self.orchestration_state['validation_results'] = result
        
        print(f"  Valid records: {result['valid_records']}")
        print(f"  Invalid records: {result['invalid_records']}")
        
        # If there are issues, handle them with dynamic agents
        if not result['validation_passed']:
            print(f"\n• Found {len(result['issues'])} validation issues")
            
            # Check issue types and create appropriate agents
            issues_str = ' '.join(result['issues'])
            
            # URL issues - create normalizer agent
            if 'url' in issues_str.lower() or 'http' in issues_str.lower():
                print("  Creating URL Normalizer agent...")
                if 'normalizer' not in self.dynamic_agents:
                    self.create_dynamic_agent(
                        'normalizer',
                        reason="Fix URL formatting issues"
                    )
                
                # Normalize URLs
                from scraper_agents.dynamic_agents import NormalizeURLsTool
                tool = NormalizeURLsTool(urls=agencies)
                result = json.loads(tool.run())
                agencies = result['normalized_records']
                print(f"  ✓ Normalized {result['urls_normalized']} URLs")
            
            # Duplicate issues - create deduplicator agent
            if 'duplicate' in issues_str.lower():
                print("  Creating Deduplicator agent...")
                if 'deduplicator' not in self.dynamic_agents:
                    self.create_dynamic_agent(
                        'deduplicator',
                        reason="Remove duplicate agencies"
                    )
                
                # Remove duplicates
                from scraper_agents.dynamic_agents import RemoveDuplicatesTool
                tool = RemoveDuplicatesTool(data=agencies)
                result = json.loads(tool.run())
                agencies = result['unique_records']
                print(f"  ✓ Removed {result['duplicates_removed']} duplicates")
        
        # Final validation
        print("\n• Final validation check...")
        tool = ValidateDataTool(data=agencies)
        final_result = json.loads(tool.run())
        
        if final_result['validation_passed']:
            print("✓ All agencies passed validation")
        else:
            print(f"⚠ {final_result['invalid_records']} agencies still have issues")
        
        return agencies
    
    def _export_phase(self, agencies: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Export phase: Export data to multiple formats.
        
        Args:
            agencies: List of validated agencies
            
        Returns:
            Dictionary with export file paths
        """
        print(f"• Exporting {len(agencies)} agencies...")
        
        # Use the exporter agent's tool
        from scraper_agents.base_agents import ExportDataTool
        tool = ExportDataTool(
            data=agencies,
            formats=["csv", "json"]
        )
        result = json.loads(tool.run())
        
        self.orchestration_state['export_results'] = result
        
        export_paths = {}
        if result['success']:
            for file_info in result['exported_files']:
                format_type = file_info['format']
                file_path = file_info['path']
                file_size = file_info['size']
                
                export_paths[format_type] = file_path
                print(f"  ✓ {format_type.upper()}: {file_path} ({file_size:,} bytes)")
        
        # Create logger agent to compile statistics
        if 'logger' not in self.dynamic_agents:
            self.create_dynamic_agent(
                'logger',
                reason="Compile final statistics and activity log"
            )
        
        # Log completion
        from scraper_agents.dynamic_agents import LogActivityTool
        tool = LogActivityTool(
            activity_type='scraping_complete',
            details={
                'total_agencies': len(agencies),
                'sections_scraped': len(self.orchestration_state['sections_completed']),
                'export_formats': list(export_paths.keys())
            }
        )
        log_result = tool.run()
        
        return export_paths
    
    def get_orchestration_report(self) -> str:
        """
        Generate a detailed orchestration report.
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("USA.gov Agency Index Scraper - Orchestration Report")
        report.append("=" * 60)
        
        # Status
        report.append(f"\nStatus: {self.orchestration_state['status'].upper()}")
        
        # Timing
        if self.orchestration_state['start_time']:
            report.append(f"Start Time: {self.orchestration_state['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        if self.orchestration_state['end_time']:
            report.append(f"End Time: {self.orchestration_state['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            duration = (self.orchestration_state['end_time'] - self.orchestration_state['start_time']).total_seconds()
            report.append(f"Duration: {duration:.2f} seconds")
        
        # Results
        report.append(f"\nSections Planned: {len(self.orchestration_state['sections_planned'])}")
        report.append(f"Sections Completed: {len(self.orchestration_state['sections_completed'])}")
        report.append(f"Agencies Scraped: {len(self.orchestration_state['agencies_scraped'])}")
        
        # Validation
        if self.orchestration_state['validation_results']:
            val = self.orchestration_state['validation_results']
            report.append(f"\nValidation Results:")
            report.append(f"  • Valid Records: {val.get('valid_records', 0)}")
            report.append(f"  • Invalid Records: {val.get('invalid_records', 0)}")
        
        # Dynamic Agents
        if self.orchestration_state['dynamic_agents_created']:
            report.append(f"\nDynamic Agents Created: {len(self.orchestration_state['dynamic_agents_created'])}")
            for agent in self.orchestration_state['dynamic_agents_created']:
                report.append(f"  • {agent['name']} ({agent['type']}): {agent['reason']}")
        
        # Errors
        if self.orchestration_state['errors']:
            report.append(f"\nErrors Encountered: {len(self.orchestration_state['errors'])}")
            for error in self.orchestration_state['errors'][:5]:  # Show first 5 errors
                report.append(f"  • {error}")
        
        # Export
        if self.orchestration_state['export_results'] and self.orchestration_state['export_results'].get('success'):
            report.append(f"\nExport Results:")
            for file_info in self.orchestration_state['export_results']['exported_files']:
                report.append(f"  • {file_info['format'].upper()}: {file_info['path']}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)