#!/usr/bin/env python3
"""
Example: Token Optimization Workflow

This script demonstrates how to use the schema tools to optimize
token usage for LLM-based SQL generation.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.token_counter import TokenCounter
from tools.schema_compactor import generate_compact_description


def analyze_token_efficiency(db_path: str, output_dir: str = "data"):
    """
    Complete workflow: analyze, optimize, and compare token usage.
    
    Args:
        db_path: Path to SQLite database
        output_dir: Directory for output files
    """
    
    print("="*80)
    print("TOKEN OPTIMIZATION WORKFLOW")
    print("="*80)
    print()
    
    # Initialize token counter
    counter = TokenCounter()
    
    # Step 1: Analyze original schema
    print("Step 1: Analyzing original database schema...")
    print("-"*80)
    
    from tools.schema_compactor import get_database_schema
    original_schema = get_database_schema(db_path)
    original_tokens = counter.count_tokens(original_schema)
    
    print(f"Database: {Path(db_path).name}")
    print(f"Original schema tokens: {original_tokens:,}")
    print(f"Characters: {len(original_schema):,}")
    print()
    
    # Step 2: Generate compact version
    print("Step 2: Generating compact schema description...")
    print("-"*80)
    
    compact_path = Path(output_dir) / f"{Path(db_path).stem}_compact.md"
    
    try:
        generate_compact_description(db_path, str(compact_path))
        print(f"✓ Compact schema generated: {compact_path}")
        print()
    except Exception as e:
        print(f"✗ Failed to generate compact schema: {e}")
        print("  Make sure LLM service is configured in .env")
        return
    
    # Step 3: Compare token counts
    print("Step 3: Comparing token efficiency...")
    print("-"*80)
    
    with open(compact_path, 'r', encoding='utf-8') as f:
        compact_content = f.read()
    
    compact_tokens = counter.count_tokens(compact_content)
    
    print(f"Original schema: {original_tokens:,} tokens")
    print(f"Compact schema:  {compact_tokens:,} tokens")
    print()
    
    reduction = (1 - compact_tokens / original_tokens) * 100
    print(f"Token reduction: {reduction:.1f}%")
    print()
    
    # Step 4: Calculate cost savings
    print("Step 4: Calculating API cost savings...")
    print("-"*80)
    
    # GPT-4 pricing (example)
    cost_per_1k_tokens = 0.03
    queries_per_month = 1000
    
    original_cost = (original_tokens / 1000) * cost_per_1k_tokens * queries_per_month
    compact_cost = (compact_tokens / 1000) * cost_per_1k_tokens * queries_per_month
    savings = original_cost - compact_cost
    
    print(f"Assuming {queries_per_month:,} queries/month at ${cost_per_1k_tokens}/1K tokens:")
    print(f"  Original cost: ${original_cost:.2f}/month")
    print(f"  Compact cost:  ${compact_cost:.2f}/month")
    print(f"  Savings:       ${savings:.2f}/month (${savings*12:.2f}/year)")
    print()
    
    # Step 5: Recommendations
    print("Step 5: Recommendations")
    print("-"*80)
    
    if reduction > 70:
        print("✓ Excellent optimization! Use compact schema for LLM context.")
    elif reduction > 50:
        print("✓ Good optimization. Consider using compact schema.")
    elif reduction > 30:
        print("⚠ Moderate optimization. Review if further reduction is possible.")
    else:
        print("⚠ Limited optimization. Consider manual refinement.")
    
    print()
    print("Next steps:")
    print("  1. Review generated compact schema for accuracy")
    print("  2. Test SQL generation with compact schema")
    print("  3. Update your application to use compact schema")
    print("  4. Monitor query accuracy and adjust as needed")
    print()
    
    return {
        'original_tokens': original_tokens,
        'compact_tokens': compact_tokens,
        'reduction_percent': reduction,
        'monthly_savings': savings,
        'compact_path': str(compact_path)
    }


def compare_multiple_representations(db_path: str):
    """
    Compare different schema representation strategies.
    """
    
    print("="*80)
    print("SCHEMA REPRESENTATION COMPARISON")
    print("="*80)
    print()
    
    counter = TokenCounter()
    
    from tools.schema_compactor import (
        get_database_schema,
        get_table_list,
        get_table_relationships
    )
    
    # Strategy 1: Full SQL schema
    full_schema = get_database_schema(db_path)
    
    # Strategy 2: Table list only
    tables = get_table_list(db_path)
    table_list = "Tables: " + ", ".join(tables)
    
    # Strategy 3: Tables + relationships
    relationships = get_table_relationships(db_path)
    tables_and_rels = table_list + "\n\nRelationships:\n"
    for table, rels in relationships.items():
        for rel in rels:
            tables_and_rels += f"  {table}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}\n"
    
    # Compare
    strategies = [
        ("Full SQL Schema", full_schema),
        ("Table List Only", table_list),
        ("Tables + Relationships", tables_and_rels),
    ]
    
    print(f"{'Strategy':<30} {'Tokens':>10} {'Chars':>10} {'Efficiency':>12}")
    print("-"*80)
    
    baseline_tokens = counter.count_tokens(full_schema)
    
    for name, content in strategies:
        tokens = counter.count_tokens(content)
        chars = len(content)
        efficiency = f"{(tokens / baseline_tokens * 100):.1f}%"
        print(f"{name:<30} {tokens:>10,} {chars:>10,} {efficiency:>12}")
    
    print()
    print("Recommendation:")
    print("  - Use 'Full SQL Schema' when exact DDL is needed")
    print("  - Use 'Tables + Relationships' for basic queries")
    print("  - Use compact description (via schema_compactor.py) for best balance")
    print()


def main():
    """Main entry point."""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Token optimization workflow example',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('database', help='Path to SQLite database')
    parser.add_argument('--output-dir', default='data', help='Output directory')
    parser.add_argument('--compare-only', action='store_true',
                       help='Only compare strategies, don\'t generate compact schema')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.database):
        print(f"✗ Database not found: {args.database}")
        sys.exit(1)
    
    if args.compare_only:
        compare_multiple_representations(args.database)
    else:
        result = analyze_token_efficiency(args.database, args.output_dir)
        
        if result:
            print("="*80)
            print("SUMMARY")
            print("="*80)
            print(f"Token reduction: {result['reduction_percent']:.1f}%")
            print(f"Monthly savings: ${result['monthly_savings']:.2f}")
            print(f"Compact schema: {result['compact_path']}")
            print()


if __name__ == '__main__':
    main()
