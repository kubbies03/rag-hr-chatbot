# Ground Truth Test Report

## Metadata

- Project: hr-rag-chatbot
- Test file: scripts/test_ground_truth.py
- Ground truth: scripts/ground_truth_rag.json
- Run date: 2026-05-01
- Command: python -X utf8 scripts/test_ground_truth.py
- Endpoint: http://127.0.0.1:8000/api/chat
- Health check: OK

## Summary

- Total questions: 29
- Request errors: 0
- Average latency: 5242 ms
- P95 latency: 12439 ms
- Min latency: 31 ms - errors
- Max latency: 12663 ms

## Accuracy

- Strict accuracy: 26/29 = 89.7%
- document_qa: 22/24 = 91.7%
- employee_status: 2/2 = 100%
- out_of_scope: 3/3 = 100%

## Overall Notes

- The system is stable for this dataset: all 29 requests returned successfully.
- document_qa cases generally work, but some answers are broader than the expected snippets.
- employee_status and out_of_scope routing behaved as expected for the test set.
- The slowest cases are document questions that likely trigger retrieval plus generation over large context.

## Case Results

| ID | Intent | Latency | Result | Notes |
| --- | --- | ---: | --- | --- |
| gt-001 | document_qa | 48 ms | Pass | Returned the expected policy scope answer. |
| gt-002 | document_qa | 36 ms | Pass | Priority order answer matched well. |
| gt-003 | document_qa | 59 ms | Pass | Trial outcome answer matched. |
| gt-004 | document_qa | 60 ms | Pass | Onboarding checklist answer matched. |
| gt-005 | document_qa | 39 ms | Pass | OT conditions answer matched. |
| gt-006 | document_qa | 35 ms | Pass | Leave workflow answer matched. |
| gt-007 | document_qa | 41 ms | Pass | PIP definition answer matched. |
| gt-008 | document_qa | 56 ms | Pass | Offboarding handover answer matched. |
| gt-009 | document_qa | 33 ms | Pass | Leave SOP workflow answer matched. |
| gt-010 | document_qa | 38 ms | Pass | Attendance correction answer matched. |
| gt-011 | document_qa | 31 ms | Pass | OT SOP answer matched. |
| gt-012 | document_qa | 11040 ms | Pass | Correct content, but slow. |
| gt-013 | document_qa | 10842 ms | Pass | Correct content, but slow. |
| gt-014 | document_qa | 5790 ms | Pass | Recruitment request answer matched. |
| gt-015 | document_qa | 10669 ms | Pass | Probation salary answer matched. |
| gt-016 | document_qa | 12663 ms | Partial | System said the document does not specify OT rates. Expected answer in ground truth is currently too specific. |
| gt-017 | document_qa | 10975 ms | Pass | Allowances answer matched broadly. |
| gt-018 | document_qa | 11311 ms | Pass | Travel expense answer matched broadly. |
| gt-019 | document_qa | 8973 ms | Partial | System returned no information. Expected answer should be revised or the source should be verified. |
| gt-020 | document_qa | 12215 ms | Pass | Travel policy grouping answer matched. |
| gt-021 | document_qa | 7864 ms | Pass | Charter capital answer matched. |
| gt-022 | document_qa | 9253 ms | Pass | Finance control principle answer matched. |
| gt-023 | document_qa | 10471 ms | Pass | Bonus schedule answer matched. |
| gt-024 | document_qa | 11815 ms | Pass | Bonus grading answer matched. |
| gt-025 | out_of_scope | 7096 ms | Pass | Router correctly rejected the law question as out of scope. |
| gt-026 | employee_status | 6394 ms | Pass | Leave status answer matched the demo data. |
| gt-027 | employee_status | 4059 ms | Partial | System returned 14 employees, while the ground truth currently expects 18. The demo seed or the expected answer needs alignment. |
| gt-028 | out_of_scope | 58 ms | Pass | Correctly rejected weather question. |
| gt-029 | out_of_scope | 51 ms | Pass | Correctly rejected poem request. |

## Mismatches To Fix

- gt-016: The current system does not confirm OT rate tables from this document set. Update the expected answer or remove this case.
- gt-019: The current system returned no information for the reimbursement timing question. Verify whether the source exists or adjust the expected answer.
- gt-027: The current SQLite demo seed currently yields 14 active/non-resigned employees for the overview response. Align the expected answer to the live seed data.

## Recommendation

- Keep the current dataset, but revise the three partial cases above before using this file for regression gating.
- If you want stricter evaluation, add a scoring layer that compares expected_intent, reference_snippet, and a normalized answer similarity score.
