import json
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

from llm_config import HEPAI_MODEL, client


HEALTH_ASSESSMENT_SHORT_NAMES = {
    "SDS",
    "BDI-II",
    "SAS",
    "BRMS",
    "SAD",
    "IAS",
    "Lonely",
    "DLS",
}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


ASSESSMENT_AI_TIMEOUT_SECONDS = _env_float("ASSESSMENT_AI_TIMEOUT_SECONDS", 90.0)


class AssessmentAiDimension(BaseModel):
    key: str = ""
    label: str = ""
    level: str = ""
    score: Optional[float] = None
    summary: str = ""
    evidence: List[str] = Field(default_factory=list)


class AssessmentAiSupport(BaseModel):
    recommended: bool = False
    urgency: str = ""
    text: str = ""


class AssessmentAiRecording(BaseModel):
    recommended: bool = False
    focus: List[str] = Field(default_factory=list)
    text: str = ""


class AssessmentAiRiskNote(BaseModel):
    triggered: bool = False
    level: str = "none"
    text: str = ""


class AssessmentAiAnalysis(BaseModel):
    state_summary: str = ""
    dimensions: List[AssessmentAiDimension] = Field(default_factory=list)
    possible_causes: List[str] = Field(default_factory=list)
    small_actions: List[str] = Field(default_factory=list)
    professional_support: AssessmentAiSupport = Field(default_factory=AssessmentAiSupport)
    emotion_recording: AssessmentAiRecording = Field(default_factory=AssessmentAiRecording)
    risk_note: AssessmentAiRiskNote = Field(default_factory=AssessmentAiRiskNote)


def is_health_assessment(short_name: str, category: str = "") -> bool:
    return short_name in HEALTH_ASSESSMENT_SHORT_NAMES or category == "心理健康"


def _choice_text(question: Dict[str, Any], answer: Any, common_choices: List[Dict[str, Any]]) -> str:
    choices = question.get("options") or question.get("choices") or common_choices
    for choice in choices or []:
        if str(choice.get("id")) == str(answer) or str(choice.get("score")) == str(answer):
            return str(choice.get("text") or choice.get("label") or answer)
    return str(answer)


def build_assessment_ai_prompt(
    scale_data: Dict[str, Any],
    result_data: Dict[str, Any],
    answers: Dict[str, Any],
) -> str:
    scale_info = scale_data.get("scale_info") or {}
    questions = {
        str(question.get("order")): question
        for question in scale_data.get("questions", [])
        if question.get("order") is not None
    }
    common_choices = scale_data.get("choices") or []
    answer_lines = []
    for order, answer in answers.items():
        question = questions.get(str(order))
        if not question:
            continue
        answer_lines.append(
            f"- 第{order}题：{question.get('text', '')}\n"
            f"  选择：{_choice_text(question, answer, common_choices)}"
        )

    return f"""
你是一名谨慎、温和、不过度诊断化的心理测评解读助手。
请根据一份心理健康问卷的标准结果和用户答案，生成一份可选的辅助分析。
这不是医学诊断，不要下诊断结论，不要把问卷结果说成疾病或确定事实。
如果出现自伤、自杀或明显安全风险相关答案，必须优先给出清晰、克制的安全提醒，
建议联系可信任的人和当地专业/紧急支持资源，不要只给一般生活建议。

量表名称：{scale_info.get('name') or '心理健康测评'}
结果等级：{result_data.get('result_level') or '未匹配'}
最终得分：{result_data.get('final_score')}
标准结果解读：{result_data.get('result_interpretation') or ''}
标准建议：{result_data.get('result_recommendation') or ''}

用户答案：
{chr(10).join(answer_lines)}

请只返回 JSON，不要添加 Markdown 代码块。JSON 必须包含以下字段：
{{
  "state_summary": "对当前状态的谨慎概括",
  "dimensions": [
    {{
      "key": "稳定英文键",
      "label": "维度名称",
      "level": "相对稳定/有些波动/需要关注/明显承压",
      "score": null,
      "summary": "该维度的简短解读",
      "evidence": ["来自答案的具体表现"]
    }}
  ],
  "possible_causes": ["可能相关因素，不要当成确定原因"],
  "small_actions": ["1-3条今天或近期可执行的小行动"],
  "professional_support": {{
    "recommended": false,
    "urgency": "optional/suggested/urgent",
    "text": "何时考虑寻求专业支持"
  }},
  "emotion_recording": {{
    "recommended": true,
    "focus": ["建议观察的方面"],
    "text": "记录建议"
  }},
  "risk_note": {{
    "triggered": false,
    "level": "none/medium/high",
    "text": "有风险时的安全提醒，否则为空字符串"
  }}
}}
""".strip()


def _normalize_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    analysis = AssessmentAiAnalysis.model_validate(payload)
    analysis.dimensions = [
        dimension
        for dimension in analysis.dimensions
        if dimension.label or dimension.summary or dimension.evidence
    ]
    return analysis.model_dump()


def _apply_safety_overrides(
    analysis: Dict[str, Any],
    scale_data: Dict[str, Any],
    answers: Dict[str, Any],
) -> Dict[str, Any]:
    short_name = (scale_data.get("scale_info") or {}).get("short_name", "")
    if short_name not in {"SDS", "BDI-II"}:
        return analysis

    try:
        risk_score = float(answers.get("9", 0))
    except (TypeError, ValueError):
        risk_score = 0
    if risk_score <= 0:
        return analysis

    high_risk = risk_score >= 2
    analysis["risk_note"] = {
        "triggered": True,
        "level": "high" if high_risk else "medium",
        "text": (
            "这份结果提示需要优先保障安全。请尽快告诉身边可信任的人，并联系当地专业或紧急支持资源。"
            if high_risk
            else "你提到过与自伤或自杀相关的念头，这值得被认真照顾。请尽快找可信任的人或专业人士聊聊。"
        ),
    }
    analysis["professional_support"] = {
        "recommended": True,
        "urgency": "urgent" if high_risk else "suggested",
        "text": (
            "如果你担心自己可能会伤害自己，请立即联系身边可信任的人、当地急救服务或心理危机支持资源。"
            if high_risk
            else "建议尽快联系心理咨询师、精神科医生或可信任的支持者，获得更具体的帮助。"
        ),
    }
    return analysis


def generate_assessment_ai_analysis(
    scale_data: Dict[str, Any],
    result_data: Dict[str, Any],
    answers: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not client:
        return None

    prompt = build_assessment_ai_prompt(scale_data, result_data, answers)
    llm_client = client.with_options(max_retries=0) if hasattr(client, "with_options") else client

    try:
        response = llm_client.chat.completions.create(
            model=HEPAI_MODEL,
            messages=[
                {"role": "system", "content": "你只输出符合要求的 JSON。"},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.35,
            max_tokens=2400,
            timeout=ASSESSMENT_AI_TIMEOUT_SECONDS,
        )
        raw_content = response.choices[0].message.content or ""
        analysis = _normalize_analysis(json.loads(raw_content))
        return _apply_safety_overrides(analysis, scale_data, answers)
    except (json.JSONDecodeError, ValidationError, TypeError, AttributeError) as exc:
        print(f"[assessment_ai] response validation failed: {type(exc).__name__}")
        return None
    except Exception as exc:
        print(f"[assessment_ai] model request failed: {type(exc).__name__}")
        return None
