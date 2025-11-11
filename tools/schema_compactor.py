#!/usr/bin/env python3
"""
Schema Compactor Tool
Generates compact English schema descriptions from database schemas using LLM.
"""

import os
import sys
import sqlite3
import argparse
from pathlib import Path
from typing import Optional
import requests
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.llm_service import LLMService


def get_database_schema(db_path: str) -> str:
    """Extract schema from SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    schemas = cursor.fetchall()
    
    conn.close()
    
    return "\n\n".join([schema[0] for schema in schemas if schema[0]])


def get_table_list(db_path: str) -> list:
    """Get list of all tables in database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return tables


def get_table_relationships(db_path: str) -> dict:
    """Analyze foreign key relationships between tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    relationships = {}
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        fks = cursor.fetchall()
        
        if fks:
            relationships[table] = []
            for fk in fks:
                relationships[table].append({
                    'from_column': fk[3],
                    'to_table': fk[2],
                    'to_column': fk[4]
                })
    
    conn.close()
    return relationships


def generate_compact_description(db_path: str, output_path: str, llm_service: Optional[LLMService] = None) -> str:
    """Generate compact schema description using LLM."""
    
    # Get schema information
    schema_sql = get_database_schema(db_path)
    tables = get_table_list(db_path)
    relationships = get_table_relationships(db_path)
    
    # Prepare prompt for LLM
    prompt = f"""Analyze this database schema and create a COMPACT English description optimized for minimal tokens.

Database has {len(tables)} tables: {', '.join(tables[:20])}{'...' if len(tables) > 20 else ''}

Requirements:
1. Use concise English (no Chinese)
2. Group tables by business domain
3. Show key relationships using arrows (→)
4. List primary/foreign keys briefly (PK:, FK:)
5. Include important constraints and field types only
6. Use abbreviations where clear
7. Focus on structure over explanation
8. Target 50-70% token reduction vs raw schema

Format:
## Domain Name
**table_name** (PK: id, FK: other_id → other_table)
- key_fields, important_constraints
- Links: related_tables

Full Schema:
{schema_sql[:15000]}

{'...[truncated]' if len(schema_sql) > 15000 else ''}

Relationships:
{json.dumps(relationships, indent=2)[:5000]}

Generate the compact description:"""

    # Use LLM service if provided, otherwise use environment config
    if llm_service is None:
        llm_service = LLMService()
    
    try:
        response = llm_service.generate_response(
            prompt=prompt,
            temperature=0.3,
            max_tokens=4000
        )
        
        compact_description = response.strip()
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Database Schema - Compact Description\n\n")
            f.write(f"*Auto-generated from: {Path(db_path).name}*\n\n")
            f.write(compact_description)
        
        print(f"✓ Compact description generated: {output_path}")
        print(f"  Tables analyzed: {len(tables)}")
        print(f"  Relationships found: {len(relationships)}")
        
        return compact_description
        
    except Exception as e:
        print(f"✗ Error generating description: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Generate compact schema descriptions using LLM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate compact description
  python schema_compactor.py data/test_medical.db -o data/schema_compact.md
  
  # Specify custom LLM endpoint
  python schema_compactor.py data/test_medical.db -o output.md --api-url http://localhost:11434
        """
    )
    
    parser.add_argument('database', help='Path to SQLite database file')
    parser.add_argument('-o', '--output', required=True, help='Output markdown file path')
    parser.add_argument('--api-url', help='LLM API URL (default: from .env)')
    parser.add_argument('--api-key', help='LLM API key (default: from .env)')
    parser.add_argument('--model', help='LLM model name (default: from .env)')
    
    args = parser.parse_args()
    
    # Validate input
    if not os.path.exists(args.database):
        print(f"✗ Database file not found: {args.database}")
        sys.exit(1)
    
    # Create output directory if needed
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize LLM service with custom config if provided
    llm_service = None
    if args.api_url or args.api_key or args.model:
        # Would need to modify LLMService to accept custom config
        # For now, use environment variables
        if args.api_url:
            os.environ['LLM_API_URL'] = args.api_url
        if args.api_key:
            os.environ['LLM_API_KEY'] = args.api_key
        if args.model:
            os.environ['LLM_MODEL'] = args.model
    
    try:
        generate_compact_description(args.database, args.output, llm_service)
        print(f"\n✓ Success! Compact schema saved to: {args.output}")
        
    except Exception as e:
        print(f"\n✗ Failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
