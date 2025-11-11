# Schema Tools Documentation

Two utilities for optimizing database schema representations for LLM consumption.

## Tools Overview

### 1. token_counter.py
Calculate and compare token counts across different schema representations.

### 2. schema_compactor.py
Generate compact English schema descriptions using LLM.

---

## Token Counter

### Installation

```bash
# Optional: Install tiktoken for accurate token counting
pip install tiktoken
```

Without tiktoken, the tool uses approximate counting (still useful for comparisons).

### Basic Usage

```bash
# Compare multiple files
python tools/token_counter.py data/test_medical.db data/schema_*.md

# Analyze single file
python tools/token_counter.py data/schema_compact.md

# Detailed line-by-line analysis
python tools/token_counter.py data/schema.md --detailed

# Show top 20 lines by token count
python tools/token_counter.py data/schema.md --detailed --top 20

# Export results to JSON
python tools/token_counter.py data/*.md --output results.json

# Use specific encoding (for different models)
python tools/token_counter.py file.md --encoding cl100k_base  # GPT-4, GPT-3.5-turbo
python tools/token_counter.py file.md --encoding p50k_base    # GPT-3 (davinci)
```

### Output Example

```
====================================================================================================
TOKEN COUNT COMPARISON
====================================================================================================
Source                                        Chars      Words    Lines     Tokens   Efficiency
----------------------------------------------------------------------------------------------------
DB Schema: test_medical.db                   32,210      3,318    1,034      6,671       100.0%
test_medical_db_schema_description.md        12,862        978      603      7,221       108.2%
test_medical_db_schema_compact.md             6,956        656      158      1,609        24.1%
====================================================================================================

Token Reduction Summary:
  test_medical_db_schema_description.md: -8.2% vs baseline
  test_medical_db_schema_compact.md: +75.9% vs baseline
```

### Interpretation

- **Efficiency**: Percentage relative to baseline (first file)
- **Token Reduction**: Positive % means fewer tokens (better)
- Lower token count = lower API costs and faster processing

---

## Schema Compactor

### Prerequisites

1. Configure LLM service in `.env`:
```bash
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_API_KEY=your_key_here
LLM_MODEL=qwen2.5:32b
```

2. Ensure LLM service is running (e.g., Ollama)

### Basic Usage

```bash
# Generate compact description
python tools/schema_compactor.py data/test_medical.db -o data/schema_compact.md

# Use custom LLM endpoint
python tools/schema_compactor.py data/test_medical.db -o output.md \
  --api-url http://localhost:11434 \
  --model llama3:8b

# Specify API key
python tools/schema_compactor.py data/test_medical.db -o output.md \
  --api-key sk-xxxxx
```

### What It Does

1. Extracts schema from SQLite database
2. Analyzes table relationships (foreign keys)
3. Sends to LLM with optimization prompt
4. Generates compact English description
5. Saves to markdown file

### Output Format

The generated file includes:
- Grouped tables by business domain
- Key relationships with arrows (→)
- Primary/foreign keys (PK:, FK:)
- Important constraints
- Common query patterns
- Design features

---

## Workflow Example

### Step 1: Analyze Current State

```bash
# Check token counts of existing representations
python tools/token_counter.py \
  data/test_medical.db \
  data/existing_schema.md
```

### Step 2: Generate Compact Version

```bash
# Generate optimized description
python tools/schema_compactor.py \
  data/test_medical.db \
  -o data/schema_compact.md
```

### Step 3: Compare Results

```bash
# Compare all versions
python tools/token_counter.py \
  data/test_medical.db \
  data/existing_schema.md \
  data/schema_compact.md \
  --detailed
```

### Step 4: Use in Production

```python
# In your application
with open('data/schema_compact.md', 'r') as f:
    schema_context = f.read()

# Send to LLM with user query
prompt = f"""Database Schema:
{schema_context}

User Query: {user_question}

Generate SQL:"""
```

---

## Token Optimization Tips

### Best Practices

1. **Use English**: 60-70% fewer tokens than Chinese
2. **Remove redundancy**: Eliminate verbose explanations
3. **Use symbols**: → for relationships, PK:/FK: for keys
4. **Group logically**: By business domain, not alphabetically
5. **Focus on structure**: Relationships over field descriptions
6. **Abbreviate wisely**: Common terms (ID, FK, PK, etc.)

### Token Reduction Strategies

| Strategy | Token Reduction | Trade-off |
|----------|----------------|-----------|
| English vs Chinese | 60-70% | None (if LLM supports English) |
| Compact format | 40-50% | Slightly less readable |
| Remove examples | 20-30% | Less context for LLM |
| Abbreviations | 10-20% | Must be clear |
| Remove comments | 10-15% | Less explanation |

### When to Use Each Format

**Raw SQL Schema** (6,671 tokens)
- ✓ Complete field definitions needed
- ✓ Exact data types required
- ✗ High token cost
- ✗ Harder for LLM to parse

**Detailed Description** (7,221 tokens)
- ✓ Human-readable documentation
- ✓ Business context included
- ✗ Higher token cost than raw schema
- ✗ Redundant for LLM

**Compact Description** (1,609 tokens)
- ✓ 75% token reduction
- ✓ Preserves key relationships
- ✓ Optimized for LLM parsing
- ✓ Lower API costs
- ✗ Less detail for complex queries

---

## Advanced Usage

### Batch Processing

```bash
# Process multiple databases
for db in data/*.db; do
  output="data/$(basename $db .db)_compact.md"
  python tools/schema_compactor.py "$db" -o "$output"
done

# Compare all results
python tools/token_counter.py data/*_compact.md --output comparison.json
```

### Integration with CI/CD

```yaml
# .github/workflows/schema-optimization.yml
name: Schema Optimization Check

on: [pull_request]

jobs:
  check-tokens:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install tiktoken
      - name: Check token counts
        run: |
          python tools/token_counter.py data/schema.md --output tokens.json
          # Fail if tokens exceed threshold
          python -c "import json; data=json.load(open('tokens.json')); exit(1 if data[0]['tokens'] > 5000 else 0)"
```

### Custom Encoding

```python
# For different LLM models
from tools.token_counter import TokenCounter

# GPT-4, GPT-3.5-turbo
counter = TokenCounter("cl100k_base")

# GPT-3 (davinci, curie, babbage, ada)
counter = TokenCounter("p50k_base")

# Count tokens
tokens = counter.count_tokens(text)
```

---

## Troubleshooting

### tiktoken not installed
```
Warning: tiktoken not installed. Using approximate token counting.
```
**Solution**: `pip install tiktoken` for accurate counts

### LLM service connection error
```
✗ Error generating description: Connection refused
```
**Solution**: 
1. Check LLM service is running
2. Verify `LLM_API_URL` in `.env`
3. Test with: `curl $LLM_API_URL`

### Database locked
```
✗ Error analyzing database: database is locked
```
**Solution**: Close other connections to the database

### Out of memory
```
✗ Error: Memory error
```
**Solution**: For large databases, the schema_compactor truncates schema to 15KB. Adjust in code if needed.

---

## Performance Benchmarks

Based on test_medical.db (100 tables):

| Operation | Time | Memory |
|-----------|------|--------|
| Token counting | <1s | <50MB |
| Schema extraction | <1s | <100MB |
| LLM generation | 10-30s | Depends on LLM |
| Batch processing (10 DBs) | 2-5min | <500MB |

---

## API Cost Comparison

Assuming GPT-4 pricing ($0.03/1K input tokens):

| Format | Tokens | Cost per Query | Cost per 1000 Queries |
|--------|--------|----------------|----------------------|
| Raw Schema | 6,671 | $0.20 | $200 |
| Detailed MD | 7,221 | $0.22 | $217 |
| Compact MD | 1,609 | $0.05 | $48 |

**Savings with compact format: 76% reduction in API costs**

---

## Contributing

To add new features:

1. **New encoding support**: Add to `TokenCounter.__init__`
2. **New output formats**: Extend `print_comparison_table`
3. **New LLM providers**: Modify `schema_compactor.py` LLM service initialization

---

## See Also

- [db_schema_analyzer.py](./db_schema_analyzer.py) - Detailed schema analysis
- [Backend LLM Service](../backend/services/llm_service.py) - LLM integration
- [tiktoken documentation](https://github.com/openai/tiktoken) - Token counting library
