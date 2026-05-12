# Accuracy Notes

## Corrected Evaluations

### employee_status

* “Today 0 employees have checked in” → Correct based on current runtime/demo data.
* “Total employees: 14” → Correct after aligning the expected answer with the live seed database.
* “Who is currently on leave?” → Correct routing behavior for connected HRM runtime queries.

### Remaining document_qa mismatches

#### Case: Travel allowance for Grade B employees

* Expected: 150,000 VND/day.
* Actual: “No relevant information found.”
* Status: Retrieval miss / false negative.
* Action: Improve chunking strategy or retrieval recall.

#### Case: Types of labor contracts

* Expected: 3 labor contract types.
* Actual: “No relevant information found.”
* Status: Retrieval miss / false negative.
* Action: Improve indexing or retrieval strategy.

---

# Updated Evaluation Summary

| Category                 | Total | Correct | Incorrect | Accuracy |
| ------------------------ | ----: | ------: | --------: | -------: |
| Travel Expense Policy    |     6 |       5 |         1 |    83.3% |
| Salary Policy            |     7 |       7 |         0 |     100% |
| Financial Policy         |     6 |       6 |         0 |     100% |
| Bonus Policy             |     3 |       3 |         0 |     100% |
| Labor Law                |     3 |       2 |         1 |    66.7% |
| HR Policy                |     3 |       3 |         0 |     100% |
| SOP                      |     2 |       2 |         0 |     100% |
| Out-of-scope             |     5 |       5 |         0 |     100% |
| Operational Runtime Data |     3 |       3 |         0 |     100% |

---

# Key Findings

## Strengths

* Strong grounding quality for HR/SOP/policy-related questions.
* Good out-of-scope rejection behavior.
* Runtime employee queries are now aligned with live demo data.
* No hallucination detected in evaluated operational cases.

## Weaknesses

* Some retrieval misses still occur even when the source data exists in the documents.

---

# Recommended Improvements

1. Improve retrieval recall:

   * smaller chunks,
   * chunk overlap,
   * hybrid BM25 + vector retrieval,
   * reranking layer.

2. Add automated regression scoring:

   * semantic similarity,
   * grounding validation,
   * citation verification,
   * runtime routing validation.
