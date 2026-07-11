from copy import deepcopy
from typing import Any, Dict, Optional


FEATURE_TREE_HOLE = "tree_hole"
FEATURE_COMMUNITY = "community"
FEATURE_MOOD_ANALYSIS = "mood_analysis"
FEATURE_ASSESSMENT_ANALYSIS = "assessment_analysis"

FEATURES: Dict[str, Dict[str, str]] = {
    FEATURE_TREE_HOLE: {
        "name": "心情树洞",
        "unit": "次",
    },
    FEATURE_COMMUNITY: {
        "name": "心灵社区",
        "unit": "次",
    },
    FEATURE_MOOD_ANALYSIS: {
        "name": "单项心情分析",
        "unit": "次",
    },
    FEATURE_ASSESSMENT_ANALYSIS: {
        "name": "AI 测评分析",
        "unit": "次",
    },
}

FREE_MONTHLY_QUOTAS = {
    FEATURE_TREE_HOLE: 30,
    FEATURE_COMMUNITY: 30,
    FEATURE_MOOD_ANALYSIS: 4,
    FEATURE_ASSESSMENT_ANALYSIS: 2,
}

PLAN_PRODUCTS: Dict[str, Dict[str, Any]] = {
    "vip_light": {
        "code": "vip_light",
        "product_type": "membership",
        "plan_code": "light",
        "name": "轻语会员",
        "description": "适合低频使用和轻量陪伴",
        "rank": 1,
        "price_fen": 899,
        "planned_standard_price_fen": 1799,
        "pricing_label": "首发体验价",
        "duration_months": 1,
        "quotas": {
            FEATURE_TREE_HOLE: 300,
            FEATURE_COMMUNITY: 500,
            FEATURE_MOOD_ANALYSIS: 40,
            FEATURE_ASSESSMENT_ANALYSIS: 50,
        },
    },
    "vip_knowing": {
        "code": "vip_knowing",
        "product_type": "membership",
        "plan_code": "knowing",
        "name": "相知会员",
        "description": "适合稳定使用和持续互动",
        "rank": 2,
        "recommended": True,
        "price_fen": 1399,
        "planned_standard_price_fen": 2799,
        "pricing_label": "首发体验价",
        "duration_months": 1,
        "quotas": {
            FEATURE_TREE_HOLE: 600,
            FEATURE_COMMUNITY: 1200,
            FEATURE_MOOD_ANALYSIS: 80,
            FEATURE_ASSESSMENT_ANALYSIS: 100,
        },
    },
    "vip_companion": {
        "code": "vip_companion",
        "product_type": "membership",
        "plan_code": "companion",
        "name": "长伴会员",
        "description": "适合高频互动和长期陪伴",
        "rank": 3,
        "price_fen": 1899,
        "planned_standard_price_fen": 3799,
        "pricing_label": "首发体验价",
        "duration_months": 1,
        "quotas": {
            FEATURE_TREE_HOLE: 1200,
            FEATURE_COMMUNITY: 2400,
            FEATURE_MOOD_ANALYSIS: 120,
            FEATURE_ASSESSMENT_ANALYSIS: 200,
        },
    },
}

ADDON_PRODUCTS: Dict[str, Dict[str, Any]] = {
    "addon_tree_300": {
        "code": "addon_tree_300",
        "product_type": "addon",
        "name": "树洞加量包",
        "description": "增加 300 次心情树洞额度",
        "feature": FEATURE_TREE_HOLE,
        "amount": 300,
        "price_fen": 399,
        "planned_standard_price_fen": 499,
        "pricing_label": "首发加量价",
        "valid_days": 90,
    },
    "addon_community_300": {
        "code": "addon_community_300",
        "product_type": "addon",
        "name": "社区加量包",
        "description": "增加 300 次心灵社区额度",
        "feature": FEATURE_COMMUNITY,
        "amount": 300,
        "price_fen": 799,
        "planned_standard_price_fen": 999,
        "pricing_label": "首发加量价",
        "valid_days": 90,
    },
    "addon_mood_20": {
        "code": "addon_mood_20",
        "product_type": "addon",
        "name": "心情分析包",
        "description": "增加 20 次单项心情分析额度",
        "feature": FEATURE_MOOD_ANALYSIS,
        "amount": 20,
        "price_fen": 199,
        "planned_standard_price_fen": 299,
        "pricing_label": "首发加量价",
        "valid_days": 90,
    },
    "addon_assessment_20": {
        "code": "addon_assessment_20",
        "product_type": "addon",
        "name": "测评分析包",
        "description": "增加 20 次 AI 测评分析额度",
        "feature": FEATURE_ASSESSMENT_ANALYSIS,
        "amount": 20,
        "price_fen": 199,
        "planned_standard_price_fen": 299,
        "pricing_label": "首发加量价",
        "valid_days": 90,
    },
}

ALL_PRODUCTS = {
    **PLAN_PRODUCTS,
    **ADDON_PRODUCTS,
}


def get_product(product_code: str) -> Optional[Dict[str, Any]]:
    product = ALL_PRODUCTS.get(product_code)
    return deepcopy(product) if product else None


def get_plan_by_code(plan_code: str) -> Optional[Dict[str, Any]]:
    for product in PLAN_PRODUCTS.values():
        if product["plan_code"] == plan_code:
            return deepcopy(product)
    return None


def public_catalog() -> Dict[str, Any]:
    return {
        "pricing_phase": "launch",
        "features": [
            {"code": code, **deepcopy(metadata)}
            for code, metadata in FEATURES.items()
        ],
        "free_monthly_quotas": deepcopy(FREE_MONTHLY_QUOTAS),
        "membership_products": [deepcopy(item) for item in PLAN_PRODUCTS.values()],
        "addon_products": [deepcopy(item) for item in ADDON_PRODUCTS.values()],
    }
