#!/usr/bin/env python3
"""
Government Contacts REST API
===========================

Comprehensive REST API for accessing government contact data with advanced
search, filtering, and export capabilities.

Features:
- RESTful endpoints for contacts, departments, and jurisdictions
- Advanced search with full-text capabilities
- Geographic and categorical filtering
- Bulk export endpoints with multiple formats
- Real-time data validation
- Pagination and sorting
- OpenAPI documentation
- Rate limiting and authentication
"""

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import tempfile
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from export_utilities import GovernmentContactExporter, ExportFilter, ExportResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'government-contacts-api-2025'
app.config['JSON_SORT_KEYS'] = False

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"]
)

# Caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Global database path (configurable)
# Uses env var GOV_CONTACTS_DB_PATH; defaults to project root 'government_contacts.db'
default_db = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'government_contacts.db'))
DB_PATH = os.environ.get('GOV_CONTACTS_DB_PATH', default_db)

REQUIRED_TABLES = {
    'jurisdictions', 'departments', 'contacts', 'websites'
}

# API configuration
API_VERSION = "1.0"
API_TITLE = "Government Contacts API"
API_DESCRIPTION = "REST API for accessing comprehensive government contact information"


class APIError(Exception):
    """Custom API exception."""
    def __init__(self, message: str, status_code: int = 400, payload: Optional[Dict] = None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload


@app.errorhandler(APIError)
def handle_api_error(error: APIError):
    """Handle custom API errors."""
    response = {'error': error.message}
    if error.payload:
        response.update(error.payload)
    
    return jsonify(response), error.status_code


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


def _validate_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")
    names = {row[0] for row in cur.fetchall()}
    missing = [t for t in REQUIRED_TABLES if t not in names]
    if missing:
        raise APIError(
            "Database schema incomplete",
            500,
            {
                'missing_tables': missing,
                'hint': 'Run scripts/db_init.py to create schema, then scripts/load_from_csv.py to load data.'
            }
        )


def _has_table(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cur.fetchone() is not None


def get_db_connection() -> sqlite3.Connection:
    """Get database connection with row factory."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        _validate_schema(conn)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise APIError("Database connection failed", 500)


def validate_pagination_params(args: Dict) -> Tuple[int, int]:
    """Validate and return pagination parameters."""
    try:
        page = int(args.get('page', 1))
        per_page = int(args.get('per_page', 50))
        
        if page < 1:
            raise ValueError("Page must be >= 1")
        if per_page < 1 or per_page > 1000:
            raise ValueError("Per page must be between 1 and 1000")
        
        return page, per_page
    
    except ValueError as e:
        raise APIError(f"Invalid pagination parameters: {e}")


def build_filter_from_args(args: Dict) -> ExportFilter:
    """Build export filter from request arguments."""
    filter_params = {}
    
    # Government levels
    if 'government_levels' in args:
        levels = [level.strip() for level in args['government_levels'].split(',') if level.strip()]
        if levels:
            filter_params['government_levels'] = levels
    
    # States
    if 'states' in args:
        states = [state.strip().upper() for state in args['states'].split(',') if state.strip()]
        if states:
            filter_params['states'] = states
    
    # Counties
    if 'counties' in args:
        counties = [county.strip() for county in args['counties'].split(',') if county.strip()]
        if counties:
            filter_params['counties'] = counties
    
    # Cities
    if 'cities' in args:
        cities = [city.strip() for city in args['cities'].split(',') if city.strip()]
        if cities:
            filter_params['cities'] = cities
    
    # Department categories
    if 'department_categories' in args:
        categories = [cat.strip() for cat in args['department_categories'].split(',') if cat.strip()]
        if categories:
            filter_params['department_categories'] = categories
    
    # Contact types
    if 'contact_types' in args:
        types = [t.strip() for t in args['contact_types'].split(',') if t.strip()]
        if types:
            filter_params['contact_types'] = types
    
    # Validation status
    if 'validation_status' in args:
        statuses = [status.strip() for status in args['validation_status'].split(',') if status.strip()]
        if statuses:
            filter_params['validation_status'] = statuses
    
    # Boolean filters
    if 'has_email' in args:
        filter_params['has_email'] = args['has_email'].lower() in ['true', '1', 'yes']
    
    if 'has_phone' in args:
        filter_params['has_phone'] = args['has_phone'].lower() in ['true', '1', 'yes']
    
    # Domain filter
    if 'domain' in args:
        filter_params['domain_filter'] = args['domain']
    
    # Date filters
    if 'date_from' in args:
        filter_params['date_from'] = args['date_from']
    
    if 'date_to' in args:
        filter_params['date_to'] = args['date_to']
    
    return ExportFilter(**filter_params)


def paginate_results(data: List[Dict], page: int, per_page: int) -> Dict[str, Any]:
    """Paginate results and return metadata."""
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page
    
    paginated_data = data[start:end]
    
    return {
        'data': paginated_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'has_next': end < total,
            'has_prev': page > 1
        }
    }


# API Routes

@app.route('/api', methods=['GET'])
def api_info():
    """Get API information."""
    return jsonify({
        'name': API_TITLE,
        'version': API_VERSION,
        'description': API_DESCRIPTION,
        'endpoints': {
            'contacts': '/api/contacts',
            'departments': '/api/departments',
            'jurisdictions': '/api/jurisdictions',
            'search': '/api/search',
            'export': '/api/export',
            'validate': '/api/validate',
            'statistics': '/api/statistics',
            'filters': '/api/filters'
        },
        'documentation': '/api/docs'
    })


@app.route('/api/contacts', methods=['GET'])
@limiter.limit("200 per minute")
@cache.cached(timeout=300, query_string=True)
def get_contacts():
    """
    Get contacts with filtering and pagination.
    
    Query Parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 1000)
    - government_levels: Comma-separated levels (federal,state,county,city,local)
    - states: Comma-separated state codes
    - counties: Comma-separated county names
    - cities: Comma-separated city names
    - department_categories: Comma-separated categories
    - contact_types: Comma-separated types (official,staff,general,emergency)
    - validation_status: Comma-separated statuses
    - has_email: Filter by email presence (true/false)
    - has_phone: Filter by phone presence (true/false)
    - domain: Filter by website domain
    - search: Full-text search query
    - sort: Sort field (default: name)
    - order: Sort order (asc/desc, default: asc)
    """
    try:
        # Validate pagination
        page, per_page = validate_pagination_params(request.args)
        
        # Build filter
        export_filter = build_filter_from_args(request.args)
        
        # Get data using exporter
        exporter = GovernmentContactExporter(DB_PATH)
        data = exporter.get_export_data(export_filter)
        exporter.disconnect_db()
        
        # Apply search if provided
        search_query = request.args.get('search', '').strip()
        if search_query:
            search_lower = search_query.lower()
            data = [
                record for record in data
                if any(
                    search_lower in str(value).lower()
                    for value in record.values()
                    if value is not None
                )
            ]
        
        # Apply sorting
        sort_field = request.args.get('sort', 'contact_name')
        sort_order = request.args.get('order', 'asc').lower()
        
        if sort_field in ['contact_name', 'department_name', 'jurisdiction_name', 'email', 'phone']:
            reverse = sort_order == 'desc'
            data.sort(key=lambda x: str(x.get(sort_field, '')).lower(), reverse=reverse)
        
        # Paginate results
        result = paginate_results(data, page, per_page)
        
        return jsonify({
            'success': True,
            'contacts': result['data'],
            'pagination': result['pagination'],
            'filters_applied': export_filter.to_dict(),
            'search_query': search_query if search_query else None
        })
    
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Error in get_contacts: {e}")
        raise APIError("Failed to retrieve contacts", 500)


@app.route('/api/contacts/<int:contact_id>', methods=['GET'])
@cache.cached(timeout=600)
def get_contact(contact_id: int):
    """Get specific contact by ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT 
            j.name as jurisdiction_name,
            j.level as government_level,
            j.state_code,
            j.county_name,
            j.city_name,
            j.website_url as jurisdiction_website,
            d.name as department_name,
            d.category as department_category,
            d.description as department_description,
            d.main_phone as department_phone,
            d.main_email as department_email,
            d.website_url as department_website,
            d.address_street,
            d.address_city,
            d.address_state,
            d.address_zip,
            c.*
        FROM contacts c
        JOIN departments d ON c.department_id = d.department_id
        JOIN jurisdictions j ON d.jurisdiction_id = j.jurisdiction_id
        WHERE c.contact_id = ?
        """
        
        cursor.execute(query, (contact_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise APIError("Contact not found", 404)
        
        # Convert row to dictionary
        contact = dict(row)
        
        # Parse JSON fields
        for json_field in ['specializations', 'languages_spoken']:
            if contact.get(json_field):
                try:
                    contact[json_field] = json.loads(contact[json_field])
                except:
                    pass
        
        return jsonify({
            'success': True,
            'contact': contact
        })
    
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Error in get_contact: {e}")
        raise APIError("Failed to retrieve contact", 500)


@app.route('/api/departments', methods=['GET'])
@limiter.limit("200 per minute")
@cache.cached(timeout=300, query_string=True)
def get_departments():
    """Get departments with filtering and pagination."""
    try:
        # Validate pagination
        page, per_page = validate_pagination_params(request.args)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query with filters
        where_conditions = []
        parameters = []
        
        # Government level filter
        if 'government_levels' in request.args:
            levels = [level.strip() for level in request.args['government_levels'].split(',')]
            placeholders = ','.join(['?' for _ in levels])
            where_conditions.append(f"j.level IN ({placeholders})")
            parameters.extend(levels)
        
        # Category filter
        if 'categories' in request.args:
            categories = [cat.strip() for cat in request.args['categories'].split(',')]
            placeholders = ','.join(['?' for _ in categories])
            where_conditions.append(f"d.category IN ({placeholders})")
            parameters.extend(categories)
        
        # Base query
        query = """
        SELECT 
            d.*,
            j.name as jurisdiction_name,
            j.level as government_level,
            j.state_code,
            COUNT(c.contact_id) as contact_count
        FROM departments d
        JOIN jurisdictions j ON d.jurisdiction_id = j.jurisdiction_id
        LEFT JOIN contacts c ON d.department_id = c.department_id
        """
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        query += " GROUP BY d.department_id ORDER BY j.level_order, j.name, d.name"
        
        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        data = [dict(row) for row in rows]
        
        # Apply search if provided
        search_query = request.args.get('search', '').strip()
        if search_query:
            search_lower = search_query.lower()
            data = [
                record for record in data
                if search_lower in record.get('name', '').lower() or 
                   search_lower in record.get('description', '').lower()
            ]
        
        # Paginate results
        result = paginate_results(data, page, per_page)
        
        return jsonify({
            'success': True,
            'departments': result['data'],
            'pagination': result['pagination']
        })
    
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Error in get_departments: {e}")
        raise APIError("Failed to retrieve departments", 500)


@app.route('/api/jurisdictions', methods=['GET'])
@limiter.limit("200 per minute")
@cache.cached(timeout=600, query_string=True)
def get_jurisdictions():
    """Get jurisdictions with hierarchical structure."""
    try:
        # Validate pagination
        page, per_page = validate_pagination_params(request.args)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query with filters
        where_conditions = []
        parameters = []
        
        # Level filter
        if 'levels' in request.args:
            levels = [level.strip() for level in request.args['levels'].split(',')]
            placeholders = ','.join(['?' for _ in levels])
            where_conditions.append(f"j.level IN ({placeholders})")
            parameters.extend(levels)
        
        # State filter
        if 'states' in request.args:
            states = [state.strip().upper() for state in request.args['states'].split(',')]
            placeholders = ','.join(['?' for _ in states])
            where_conditions.append(f"j.state_code IN ({placeholders})")
            parameters.extend(states)
        
        # Base query
        query = """
        SELECT 
            j.*,
            COUNT(DISTINCT d.department_id) as department_count,
            COUNT(DISTINCT c.contact_id) as contact_count
        FROM jurisdictions j
        LEFT JOIN departments d ON j.jurisdiction_id = d.jurisdiction_id
        LEFT JOIN contacts c ON d.department_id = c.department_id
        """
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        query += " GROUP BY j.jurisdiction_id ORDER BY j.level_order, j.name"
        
        cursor.execute(query, parameters)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        data = [dict(row) for row in rows]
        
        # Paginate results
        result = paginate_results(data, page, per_page)
        
        return jsonify({
            'success': True,
            'jurisdictions': result['data'],
            'pagination': result['pagination']
        })
    
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Error in get_jurisdictions: {e}")
        raise APIError("Failed to retrieve jurisdictions", 500)


@app.route('/api/search', methods=['GET'])
@limiter.limit("100 per minute")
def search_contacts():
    """
    Full-text search across contacts, departments, and jurisdictions.
    
    Query Parameters:
    - q: Search query (required)
    - type: Search type (contacts, departments, jurisdictions, all)
    - page: Page number
    - per_page: Items per page
    """
    try:
        search_query = request.args.get('q', '').strip()
        if not search_query:
            raise APIError("Search query is required", 400)
        
        search_type = request.args.get('type', 'all').lower()
        page, per_page = validate_pagination_params(request.args)
        
        conn = get_db_connection()
        cursor = conn.cursor()

        results = {}

        use_fts = (_has_table(conn, 'contacts_fts') and
                   _has_table(conn, 'departments_fts') and
                   _has_table(conn, 'jurisdictions_fts'))

        if search_type in ['contacts', 'all']:
            if use_fts:
                cursor.execute("""
                    SELECT c.*, d.name as department_name, j.name as jurisdiction_name
                    FROM contacts_fts fts
                    JOIN contacts c ON c.contact_id = fts.rowid
                    JOIN departments d ON c.department_id = d.department_id
                    JOIN jurisdictions j ON d.jurisdiction_id = j.jurisdiction_id
                    WHERE contacts_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (search_query, per_page * 3))
            else:
                # Fallback LIKE-based search
                like = f"%{search_query}%"
                cursor.execute("""
                    SELECT c.*, d.name as department_name, j.name as jurisdiction_name
                    FROM contacts c
                    JOIN departments d ON c.department_id = d.department_id
                    JOIN jurisdictions j ON d.jurisdiction_id = j.jurisdiction_id
                    WHERE (c.name LIKE ? OR c.title LIKE ? OR c.email LIKE ? OR c.phone LIKE ?)
                    LIMIT ?
                """, (like, like, like, like, per_page * 3))
            contacts = [dict(row) for row in cursor.fetchall()]
            results['contacts'] = contacts

        if search_type in ['departments', 'all']:
            if use_fts:
                cursor.execute("""
                    SELECT d.*, j.name as jurisdiction_name
                    FROM departments_fts fts
                    JOIN departments d ON d.department_id = fts.rowid
                    JOIN jurisdictions j ON d.jurisdiction_id = j.jurisdiction_id
                    WHERE departments_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (search_query, per_page * 2))
            else:
                like = f"%{search_query}%"
                cursor.execute("""
                    SELECT d.*, j.name as jurisdiction_name
                    FROM departments d
                    JOIN jurisdictions j ON d.jurisdiction_id = j.jurisdiction_id
                    WHERE (d.name LIKE ? OR IFNULL(d.description,'') LIKE ? OR d.category LIKE ?)
                    LIMIT ?
                """, (like, like, like, per_page * 2))
            departments = [dict(row) for row in cursor.fetchall()]
            results['departments'] = departments

        if search_type in ['jurisdictions', 'all']:
            if use_fts:
                cursor.execute("""
                    SELECT j.*
                    FROM jurisdictions_fts fts
                    JOIN jurisdictions j ON j.jurisdiction_id = fts.rowid
                    WHERE jurisdictions_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (search_query, per_page))
            else:
                like = f"%{search_query}%"
                cursor.execute("""
                    SELECT j.*
                    FROM jurisdictions j
                    WHERE (j.name LIKE ? OR j.level LIKE ? OR IFNULL(j.state_code,'') LIKE ?
                           OR IFNULL(j.county_name,'') LIKE ? OR IFNULL(j.city_name,'') LIKE ?)
                    LIMIT ?
                """, (like, like, like, like, like, per_page))
            jurisdictions = [dict(row) for row in cursor.fetchall()]
            results['jurisdictions'] = jurisdictions
        
        conn.close()
        
        return jsonify({
            'success': True,
            'query': search_query,
            'type': search_type,
            'results': results,
            'result_counts': {key: len(value) for key, value in results.items()}
        })
    
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Error in search_contacts: {e}")
        raise APIError("Search failed", 500)


@app.route('/api/export/<format_type>', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def export_data(format_type: str):
    """
    Export data in specified format.
    
    Supported formats: csv, json, excel, vcard
    """
    try:
        if format_type not in ['csv', 'json', 'excel', 'vcard']:
            raise APIError("Unsupported export format", 400)
        
        # Get filters from request
        if request.method == 'POST':
            filter_data = request.get_json() or {}
        else:
            filter_data = request.args.to_dict()
        
        export_filter = build_filter_from_args(filter_data)
        
        # Initialize exporter
        exporter = GovernmentContactExporter(DB_PATH)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as tmp_file:
            tmp_path = tmp_file.name
        
        # Export based on format
        if format_type == 'csv':
            result = exporter.export_to_csv(export_filter, tmp_path)
            mimetype = 'text/csv'
        elif format_type == 'json':
            result = exporter.export_to_json(export_filter, tmp_path)
            mimetype = 'application/json'
        elif format_type == 'excel':
            result = exporter.export_to_excel(export_filter, tmp_path)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif format_type == 'vcard':
            result = exporter.export_to_vcard(export_filter, tmp_path)
            mimetype = 'text/vcard'
        
        exporter.disconnect_db()
        
        if not result.success:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise APIError(f"Export failed: {result.error_message}", 500)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = format_type if format_type != 'excel' else 'xlsx'
        filename = f"government_contacts_{timestamp}.{extension}"
        
        # Return file
        return send_file(
            tmp_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename,
            max_age=0
        )
    
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Error in export_data: {e}")
        raise APIError("Export failed", 500)


@app.route('/api/validate/contact', methods=['POST'])
@limiter.limit("50 per minute")
def validate_contact():
    """
    Validate contact information.
    
    Request body:
    {
        "email": "contact@example.gov",
        "phone": "+1-555-123-4567"
    }
    """
    try:
        data = request.get_json()
        if not data:
            raise APIError("Request body is required", 400)
        
        exporter = GovernmentContactExporter(DB_PATH)
        results = {}
        
        # Validate email
        if 'email' in data:
            email_valid, email_confidence = exporter.validate_email(data['email'])
            results['email'] = {
                'value': data['email'],
                'valid': email_valid,
                'confidence': email_confidence,
                'is_government': any(domain in data['email'].lower() for domain in ['.gov', '.mil', '.edu'])
            }
        
        # Validate phone
        if 'phone' in data:
            phone_valid, phone_confidence = exporter.validate_phone(data['phone'])
            results['phone'] = {
                'value': data['phone'],
                'valid': phone_valid,
                'confidence': phone_confidence
            }
        
        exporter.disconnect_db()
        
        return jsonify({
            'success': True,
            'validation_results': results
        })
    
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Error in validate_contact: {e}")
        raise APIError("Validation failed", 500)


@app.route('/api/statistics', methods=['GET'])
@cache.cached(timeout=3600)
def get_statistics():
    """Get comprehensive database statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM jurisdictions")
        stats['total_jurisdictions'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM departments")
        stats['total_departments'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM contacts")
        stats['total_contacts'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM websites")
        stats['total_websites'] = cursor.fetchone()[0]
        
        # Contact statistics
        cursor.execute("SELECT COUNT(*) FROM contacts WHERE email IS NOT NULL AND email != ''")
        stats['contacts_with_email'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM contacts WHERE phone IS NOT NULL AND phone != ''")
        stats['contacts_with_phone'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM contacts WHERE validation_status = 'valid'")
        stats['valid_contacts'] = cursor.fetchone()[0]
        
        # Level breakdown
        cursor.execute("""
            SELECT level, COUNT(*) as count 
            FROM jurisdictions 
            GROUP BY level 
            ORDER BY level_order
        """)
        stats['jurisdictions_by_level'] = dict(cursor.fetchall())
        
        # Category breakdown
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM departments 
            GROUP BY category 
            ORDER BY count DESC
        """)
        stats['departments_by_category'] = dict(cursor.fetchall())
        
        # Contact type breakdown
        cursor.execute("""
            SELECT contact_type, COUNT(*) as count 
            FROM contacts 
            GROUP BY contact_type 
            ORDER BY count DESC
        """)
        stats['contacts_by_type'] = dict(cursor.fetchall())
        
        # Validation status breakdown
        cursor.execute("""
            SELECT validation_status, COUNT(*) as count 
            FROM contacts 
            GROUP BY validation_status 
            ORDER BY count DESC
        """)
        stats['contacts_by_validation'] = dict(cursor.fetchall())
        
        # Data quality metrics
        total_possible_quality = stats['total_contacts'] * 2  # email + phone
        actual_quality = stats['contacts_with_email'] + stats['contacts_with_phone']
        stats['data_quality_score'] = (actual_quality / total_possible_quality * 100) if total_possible_quality > 0 else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'statistics': stats,
            'generated_at': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in get_statistics: {e}")
        raise APIError("Failed to retrieve statistics", 500)


@app.route('/api/filters', methods=['GET'])
@cache.cached(timeout=3600)
def get_available_filters():
    """Get available filter options."""
    try:
        exporter = GovernmentContactExporter(DB_PATH)
        filters = exporter.get_available_filters()
        exporter.disconnect_db()
        
        return jsonify({
            'success': True,
            'available_filters': filters
        })
    
    except Exception as e:
        logger.error(f"Error in get_available_filters: {e}")
        raise APIError("Failed to retrieve filters", 500)


@app.route('/api/docs', methods=['GET'])
def get_api_docs():
    """Get OpenAPI documentation."""
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": API_TITLE,
            "version": API_VERSION,
            "description": API_DESCRIPTION,
            "contact": {
                "name": "Government Contacts API Support",
                "url": "https://github.com/government-contacts/api"
            }
        },
        "servers": [
            {
                "url": request.host_url.rstrip('/'),
                "description": "API Server"
            }
        ],
        "paths": {
            "/api": {
                "get": {
                    "summary": "Get API information",
                    "tags": ["General"],
                    "responses": {
                        "200": {
                            "description": "API information",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/contacts": {
                "get": {
                    "summary": "Get contacts with filtering and pagination",
                    "tags": ["Contacts"],
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "description": "Page number",
                            "schema": {"type": "integer", "default": 1, "minimum": 1}
                        },
                        {
                            "name": "per_page",
                            "in": "query",
                            "description": "Items per page",
                            "schema": {"type": "integer", "default": 50, "minimum": 1, "maximum": 1000}
                        },
                        {
                            "name": "government_levels",
                            "in": "query",
                            "description": "Comma-separated government levels",
                            "schema": {"type": "string"},
                            "example": "federal,state"
                        },
                        {
                            "name": "has_email",
                            "in": "query",
                            "description": "Filter by email presence",
                            "schema": {"type": "boolean"}
                        },
                        {
                            "name": "search",
                            "in": "query",
                            "description": "Search query",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "List of contacts",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean"},
                                            "contacts": {"type": "array"},
                                            "pagination": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/export/{format}": {
                "get": {
                    "summary": "Export data in specified format",
                    "tags": ["Export"],
                    "parameters": [
                        {
                            "name": "format",
                            "in": "path",
                            "required": True,
                            "description": "Export format",
                            "schema": {
                                "type": "string",
                                "enum": ["csv", "json", "excel", "vcard"]
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Exported file",
                            "content": {
                                "application/octet-stream": {
                                    "schema": {"type": "string", "format": "binary"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Contact": {
                    "type": "object",
                    "properties": {
                        "contact_id": {"type": "integer"},
                        "contact_name": {"type": "string"},
                        "title": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "department_name": {"type": "string"},
                        "jurisdiction_name": {"type": "string"},
                        "government_level": {"type": "string"}
                    }
                },
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"}
                    }
                }
            }
        },
        "tags": [
            {"name": "General", "description": "General API information"},
            {"name": "Contacts", "description": "Contact management"},
            {"name": "Departments", "description": "Department information"},
            {"name": "Jurisdictions", "description": "Government jurisdictions"},
            {"name": "Search", "description": "Search functionality"},
            {"name": "Export", "description": "Data export"},
            {"name": "Validation", "description": "Data validation"},
            {"name": "Statistics", "description": "Database statistics"}
        ]
    }
    
    return jsonify(openapi_spec)


def main():
    """Run the API server."""
    print("\n" + "="*80)
    print("GOVERNMENT CONTACTS REST API")
    print("="*80)
    print(f"API Title: {API_TITLE}")
    print(f"Version: {API_VERSION}")
    print(f"Database: {DB_PATH}")
    print("\nAvailable Endpoints:")
    print("  GET  /api                    - API information")
    print("  GET  /api/contacts           - List contacts with filtering")
    print("  GET  /api/contacts/<id>      - Get specific contact")
    print("  GET  /api/departments        - List departments")
    print("  GET  /api/jurisdictions      - List jurisdictions")
    print("  GET  /api/search             - Full-text search")
    print("  GET  /api/export/<format>    - Export data (csv, json, excel, vcard)")
    print("  POST /api/validate/contact   - Validate contact information")
    print("  GET  /api/statistics         - Database statistics")
    print("  GET  /api/filters            - Available filter options")
    print("  GET  /api/docs               - OpenAPI documentation")
    print("\nStarting server on http://localhost:5000")
    print("="*80 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
