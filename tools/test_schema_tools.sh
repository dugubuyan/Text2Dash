#!/bin/bash
# Test script for schema tools

set -e

echo "=================================="
echo "Schema Tools Test Suite"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Token Counter Basic
echo -e "${BLUE}Test 1: Token Counter - Basic Comparison${NC}"
python tools/token_counter.py \
  data/test_medical.db \
  data/test_medical_db_schema_description.md \
  data/test_medical_db_schema_compact.md

echo -e "${GREEN}✓ Test 1 passed${NC}"
echo ""

# Test 2: Token Counter Detailed
echo -e "${BLUE}Test 2: Token Counter - Detailed Analysis${NC}"
python tools/token_counter.py \
  data/test_medical_db_schema_compact.md \
  --detailed \
  --top 5

echo -e "${GREEN}✓ Test 2 passed${NC}"
echo ""

# Test 3: Token Counter JSON Export
echo -e "${BLUE}Test 3: Token Counter - JSON Export${NC}"
python tools/token_counter.py \
  data/test_medical_db_schema_compact.md \
  --output /tmp/token_results.json

if [ -f /tmp/token_results.json ]; then
  echo "JSON output:"
  cat /tmp/token_results.json
  echo ""
  echo -e "${GREEN}✓ Test 3 passed${NC}"
else
  echo "✗ Test 3 failed: JSON file not created"
  exit 1
fi
echo ""

# Test 4: Schema Compactor (only if LLM service is configured)
echo -e "${BLUE}Test 4: Schema Compactor${NC}"
if [ -f .env ] && grep -q "LLM_API_URL" .env; then
  echo "LLM service configured, testing schema compactor..."
  
  # Create a small test database
  TEST_DB="/tmp/test_small.db"
  sqlite3 $TEST_DB <<EOF
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    title TEXT,
    content TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
EOF
  
  python tools/schema_compactor.py \
    $TEST_DB \
    -o /tmp/test_compact.md
  
  if [ -f /tmp/test_compact.md ]; then
    echo "Generated compact schema:"
    head -20 /tmp/test_compact.md
    echo ""
    echo -e "${GREEN}✓ Test 4 passed${NC}"
  else
    echo "✗ Test 4 failed: Compact schema not created"
    exit 1
  fi
else
  echo "⚠️  Skipping Test 4: LLM service not configured in .env"
  echo "   To enable: Set LLM_API_URL, LLM_API_KEY, LLM_MODEL in .env"
fi
echo ""

# Test 5: Error Handling
echo -e "${BLUE}Test 5: Error Handling${NC}"
python tools/token_counter.py nonexistent_file.md 2>&1 | grep -q "not found" && \
  echo -e "${GREEN}✓ Test 5 passed (error handling works)${NC}" || \
  echo "✗ Test 5 failed"
echo ""

# Summary
echo "=================================="
echo "All tests completed!"
echo "=================================="
echo ""
echo "Usage examples:"
echo "  1. Compare token counts:"
echo "     python tools/token_counter.py data/*.md"
echo ""
echo "  2. Generate compact schema:"
echo "     python tools/schema_compactor.py data/test_medical.db -o output.md"
echo ""
echo "  3. Detailed analysis:"
echo "     python tools/token_counter.py file.md --detailed"
echo ""
echo "See tools/SCHEMA_TOOLS.md for full documentation"
