# Schema Tools Quick Start

## 🚀 Quick Commands

### Compare Token Counts
```bash
python tools/token_counter.py data/test_medical.db data/schema_*.md
```

### Generate Compact Schema
```bash
python tools/schema_compactor.py data/test_medical.db -o data/schema_compact.md
```

### Detailed Analysis
```bash
python tools/token_counter.py data/schema.md --detailed --top 20
```

---

## 📊 Expected Results

| Format | Tokens | Efficiency | Use Case |
|--------|--------|------------|----------|
| Raw SQL Schema | ~6,700 | Baseline | Need exact DDL |
| Detailed MD (Chinese) | ~7,200 | -8% | Human documentation |
| **Compact MD (English)** | **~1,600** | **+76%** | **LLM context** ✅ |

---

## 💡 Why Use Compact Format?

### Cost Savings (GPT-4)
- Raw Schema: $0.20 per query → $200 per 1K queries
- **Compact: $0.05 per query → $48 per 1K queries**
- **Savings: $152 per 1K queries (76% reduction)**

### Better LLM Performance
- ✅ Clearer business logic
- ✅ Faster processing
- ✅ More accurate SQL generation
- ✅ Fits in smaller context windows

---

## 🔧 Setup (One-time)

### 1. Install tiktoken (optional but recommended)
```bash
pip install tiktoken
```

### 2. Configure LLM for schema_compactor
Add to `.env`:
```bash
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_API_KEY=your_key_here
LLM_MODEL=qwen2.5:32b
```

---

## 📝 Common Workflows

### Workflow 1: Optimize Existing Schema
```bash
# 1. Check current token count
python tools/token_counter.py data/current_schema.md

# 2. Generate compact version
python tools/schema_compactor.py data/database.db -o data/schema_compact.md

# 3. Compare
python tools/token_counter.py data/current_schema.md data/schema_compact.md
```

### Workflow 2: Batch Process Multiple Databases
```bash
# Process all databases
for db in data/*.db; do
  output="data/$(basename $db .db)_compact.md"
  python tools/schema_compactor.py "$db" -o "$output"
done

# Compare all results
python tools/token_counter.py data/*_compact.md
```

### Workflow 3: Monitor Token Usage
```bash
# Export to JSON for tracking
python tools/token_counter.py data/schema_*.md --output metrics.json

# Track over time
git add metrics.json
git commit -m "Update schema token metrics"
```

---

## 🎯 Best Practices

### DO ✅
- Use compact format for LLM context
- Keep raw schema for reference
- Monitor token counts regularly
- Test SQL generation accuracy

### DON'T ❌
- Don't send raw SQL to LLM (wasteful)
- Don't use Chinese for LLM context (2-3x tokens)
- Don't include sample data (security + tokens)
- Don't over-abbreviate (clarity matters)

---

## 🐛 Troubleshooting

### "tiktoken not installed"
```bash
pip install tiktoken
```
Or continue with approximate counting (still useful for comparisons)

### "LLM service connection error"
1. Check LLM service is running: `curl $LLM_API_URL`
2. Verify `.env` configuration
3. Test with simple query

### "Database locked"
Close other connections to the database

---

## 📚 Learn More

- [SCHEMA_TOOLS.md](./SCHEMA_TOOLS.md) - Complete documentation
- [README.md](./README.md) - All tools overview
- [test_schema_tools.sh](./test_schema_tools.sh) - Test suite

---

## 🎓 Example Output

### Token Counter
```
====================================================================================================
TOKEN COUNT COMPARISON
====================================================================================================
Source                                        Chars      Words    Lines     Tokens   Efficiency
----------------------------------------------------------------------------------------------------
DB Schema: test_medical.db                   32,210      3,318    1,034      6,671       100.0%
test_medical_db_schema_compact.md             6,956        656      158      1,609        24.1%
====================================================================================================

Token Reduction Summary:
  test_medical_db_schema_compact.md: +75.9% vs baseline
```

### Schema Compactor
```
✓ Compact description generated: data/schema_compact.md
  Tables analyzed: 100
  Relationships found: 87
  
✓ Success! Compact schema saved to: data/schema_compact.md
```

---

**Ready to save 76% on LLM API costs? Start with token_counter.py!** 🚀
