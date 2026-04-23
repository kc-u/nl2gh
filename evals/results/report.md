# nl2gh Eval Report

## Overall Accuracy

| Model | Passed | Total | Accuracy |
|-------|--------|-------|----------|
| gemini | 29 | 30 | 96.7% ✅ |
| llama | 27 | 30 | 90.0% ✅ |

## Per-Category Accuracy

| Category | claude | gemini | llama |
|----------|---------|---------|---------|
| adversarial | — | 4/4 (100%) | 4/4 (100%) |
| ambiguous | — | 3/4 (75%) | 4/4 (100%) |
| multi-filter | — | 8/8 (100%) | 7/8 (88%) |
| multilingual | — | 4/4 (100%) | 3/3 (100%) |
| simple | — | 5/5 (100%) | 5/5 (100%) |
| time-bounded | — | 5/5 (100%) | 4/5 (80%) |
| unknown | — | — | — |

## Per-Difficulty Accuracy

| Difficulty | claude | gemini | llama |
|------------|---------|---------|---------|
| 0 | — | — | — |
| 1 | — | 5/5 | 5/5 |
| 2 | — | 14/14 | 13/14 |
| 3 | — | 7/8 | 6/7 |
| 4 | — | 2/2 | 2/2 |
| 5 | — | 1/1 | 1/1 |

## Common Failure Patterns

### claude: no failures 🎉

### gemini — 1 failures

- **gh-026** (ambiguous) — failed fields: `clarification_set`  
  NL: *good TypeScript tools for developers*

### llama — 3 failures

- **gh-012** (multi-filter) — failed fields: `pushed`  
  NL: *Swift iOS frameworks updated in 2025 with between 500 and 5000 stars*
- **gh-018** (time-bounded) — failed fields: `pushed_date_approx`  
  NL: *JavaScript repositories updated in the last 30 days with more than 500 stars*
- **gh-022** (None) — failed fields: ``  
  NL: **
