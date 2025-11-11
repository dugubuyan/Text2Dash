#!/usr/bin/env python3
"""
Token Counter Tool
Calculate and compare token counts for different schema representations.
"""

import os
import sys
import argparse
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
import json

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("Warning: tiktoken not installed. Using approximate token counting.")
    print("Install with: pip install tiktoken")


class TokenCounter:
    """Token counting utility supporting multiple methods."""
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize token counter.
        
        Args:
            encoding_name: Tiktoken encoding name (cl100k_base for GPT-4, GPT-3.5-turbo)
        """
        self.encoding_name = encoding_name
        
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoder = tiktoken.get_encoding(encoding_name)
            except Exception as e:
                print(f"Warning: Could not load encoding {encoding_name}: {e}")
                self.encoder = None
        else:
            self.encoder = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.encoder:
            return len(self.encoder.encode(text))
        else:
            # Approximate: ~1.3 tokens per word for English, ~2.5 per character for Chinese
            words = text.split()
            # Rough heuristic: check if text is primarily Chinese
            chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            total_chars = len(text)
            
            if chinese_chars > total_chars * 0.3:  # Mostly Chinese
                return int(total_chars * 0.4)  # ~2.5 chars per token
            else:  # Mostly English
                return int(len(words) * 1.3)
    
    def count_tokens_by_line(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Count tokens for each line.
        
        Returns:
            List of (line_number, token_count, line_preview)
        """
        lines = text.split('\n')
        results = []
        
        for i, line in enumerate(lines, 1):
            if line.strip():
                token_count = self.count_tokens(line)
                preview = line[:80] + '...' if len(line) > 80 else line
                results.append((i, token_count, preview))
        
        return results


def get_database_schema(db_path: str) -> str:
    """Extract schema from SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    schemas = cursor.fetchall()
    
    conn.close()
    
    return "\n\n".join([schema[0] for schema in schemas if schema[0]])


def read_file(file_path: str) -> str:
    """Read file content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def analyze_file(file_path: str, counter: TokenCounter, label: str = None) -> Dict:
    """Analyze a file and return statistics."""
    if label is None:
        label = Path(file_path).name
    
    content = read_file(file_path)
    
    return {
        'label': label,
        'path': file_path,
        'chars': len(content),
        'words': len(content.split()),
        'lines': len(content.split('\n')),
        'tokens': counter.count_tokens(content),
        'content': content
    }


def analyze_database(db_path: str, counter: TokenCounter) -> Dict:
    """Analyze database schema and return statistics."""
    schema = get_database_schema(db_path)
    
    return {
        'label': f"DB Schema: {Path(db_path).name}",
        'path': db_path,
        'chars': len(schema),
        'words': len(schema.split()),
        'lines': len(schema.split('\n')),
        'tokens': counter.count_tokens(schema),
        'content': schema
    }


def print_comparison_table(results: List[Dict]):
    """Print comparison table of results."""
    print("\n" + "="*100)
    print("TOKEN COUNT COMPARISON")
    print("="*100)
    
    # Header
    print(f"{'Source':<40} {'Chars':>10} {'Words':>10} {'Lines':>8} {'Tokens':>10} {'Efficiency':>12}")
    print("-"*100)
    
    # Find baseline (first result)
    baseline_tokens = results[0]['tokens'] if results else 1
    
    # Print each result
    for result in results:
        efficiency = f"{(result['tokens'] / baseline_tokens * 100):.1f}%"
        print(f"{result['label']:<40} {result['chars']:>10,} {result['words']:>10,} "
              f"{result['lines']:>8,} {result['tokens']:>10,} {efficiency:>12}")
    
    print("="*100)
    
    # Summary
    if len(results) > 1:
        print(f"\nToken Reduction Summary:")
        for i, result in enumerate(results[1:], 1):
            reduction = (1 - result['tokens'] / baseline_tokens) * 100
            print(f"  {result['label']}: {reduction:+.1f}% vs baseline")
    
    print()


def print_detailed_analysis(result: Dict, counter: TokenCounter, top_n: int = 10):
    """Print detailed token analysis for a single file."""
    print(f"\n{'='*100}")
    print(f"DETAILED ANALYSIS: {result['label']}")
    print(f"{'='*100}")
    print(f"Path: {result['path']}")
    print(f"Total tokens: {result['tokens']:,}")
    print(f"Total chars: {result['chars']:,}")
    print(f"Total words: {result['words']:,}")
    print(f"Total lines: {result['lines']:,}")
    print(f"Avg tokens/line: {result['tokens'] / max(result['lines'], 1):.1f}")
    
    # Analyze by line
    line_tokens = counter.count_tokens_by_line(result['content'])
    
    if line_tokens:
        # Sort by token count
        top_lines = sorted(line_tokens, key=lambda x: x[1], reverse=True)[:top_n]
        
        print(f"\nTop {top_n} lines by token count:")
        print(f"{'Line':>6} {'Tokens':>8}  Preview")
        print("-"*100)
        for line_num, tokens, preview in top_lines:
            print(f"{line_num:>6} {tokens:>8}  {preview}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Count and compare tokens in schema representations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare database schema with markdown descriptions
  python token_counter.py data/test_medical.db data/schema_*.md
  
  # Detailed analysis of a single file
  python token_counter.py data/schema_compact.md --detailed
  
  # Use specific encoding
  python token_counter.py file.md --encoding cl100k_base
  
  # Export results to JSON
  python token_counter.py data/*.md --output results.json
        """
    )
    
    parser.add_argument('files', nargs='+', help='Files or databases to analyze')
    parser.add_argument('--encoding', default='cl100k_base', 
                       help='Tiktoken encoding (default: cl100k_base for GPT-4)')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed line-by-line analysis')
    parser.add_argument('--top', type=int, default=10,
                       help='Number of top lines to show in detailed mode (default: 10)')
    parser.add_argument('--output', help='Export results to JSON file')
    
    args = parser.parse_args()
    
    # Initialize counter
    counter = TokenCounter(args.encoding)
    
    if not TIKTOKEN_AVAILABLE:
        print("\n⚠️  Using approximate token counting. Install tiktoken for accurate counts.\n")
    
    # Analyze all files
    results = []
    
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"✗ File not found: {file_path}")
            continue
        
        try:
            # Check if it's a database
            if file_path.endswith('.db') or file_path.endswith('.sqlite'):
                result = analyze_database(file_path, counter)
            else:
                result = analyze_file(file_path, counter)
            
            results.append(result)
            print(f"✓ Analyzed: {result['label']}")
            
        except Exception as e:
            print(f"✗ Error analyzing {file_path}: {e}")
    
    if not results:
        print("\n✗ No files analyzed successfully")
        sys.exit(1)
    
    # Print comparison table
    print_comparison_table(results)
    
    # Print detailed analysis if requested
    if args.detailed:
        for result in results:
            print_detailed_analysis(result, counter, args.top)
    
    # Export to JSON if requested
    if args.output:
        export_data = []
        for result in results:
            export_data.append({
                'label': result['label'],
                'path': result['path'],
                'chars': result['chars'],
                'words': result['words'],
                'lines': result['lines'],
                'tokens': result['tokens']
            })
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Results exported to: {args.output}")


if __name__ == '__main__':
    main()
