# 2026-06-26 Assessment Grouping And AI Analysis

## Goal

Implement the backend part of product iteration 010 for the assessment module:

- Return four display groups for assessment list rendering.
- Add structured AI analysis for SDS / BDI-II results.
- Ensure both newly submitted results and history detail responses can provide the same AI analysis.

## Changes

- Added backend display metadata mapping for all 18 assessments:
  - `display_group`
  - `display_group_order`
  - `display_order`
- Sorted `GET /api/v1/assessments/` by group order and display order.
- Added the same display metadata to single assessment detail, `scale_info`, and `scale_details`.
- Implemented SDS / BDI-II AI analysis in `UserAssessment.result_details.ai_analysis`.
- Also exposed `ai_analysis` at the top level of `UserAssessmentResponse` for easier frontend access.
- AI analysis dimensions:
  - emotion
  - interest
  - body
  - cognition
  - risk
- Q9 risk is handled separately:
  - `0`: no strong risk note
  - `1`: medium risk note and suggested support
  - `>=2`: high risk note and urgent safety support wording
- Existing historical SDS records are lazily backfilled with AI analysis when history/detail responses are built.
- Fixed `AImental_backend/assessment_data/APS.json` internal `scale_info.short_name` from `TPS` to `APS`.
- Existing scale metadata is refreshed from JSON files during initialization so corrected JSON and category text are reflected in the database.
- Added fallback defaults for empty `category` / `assessment_type` values in JSON metadata, covering CLT and old database rows.

## API Shape

Assessment list and scale details now include:

```json
{
  "display_group": "心理健康",
  "display_group_order": 1,
  "display_order": 1
}
```

Assessment submit and history detail responses now include:

```json
{
  "ai_analysis": {},
  "result_details": {
    "ai_analysis": {}
  }
}
```

## Verification

- `python -m py_compile model/assessment.py router/assessment.py` passed.
- Verified assessment list returns 18 items with four display groups and ordered SDS first in 心理健康.
- Verified SDS detail returns display metadata, 21 questions, and 4 choices.
- Verified SDS scoring with sample answers generates five AI analysis dimensions.
- Verified Q9 risk levels:
  - Q9 = 1 produces medium risk support.
  - Q9 = 2 produces urgent safety support wording.
- Created and deleted a temporary SDS assessment record to verify stored nested analysis and top-level `ai_analysis` response.
- Validated assessment list items and SDS response payloads against their Pydantic response models.

## Notes

- No database schema migration was needed.
- AI analysis is deterministic and local; it does not call an external LLM.
- The original `result_level`, `result_interpretation`, and `result_recommendation` are preserved.
