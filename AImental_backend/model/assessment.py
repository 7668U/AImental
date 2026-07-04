# model/assessment.py

import uuid
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple

from peewee import Model, CharField, IntegerField, DateTimeField, TextField, ForeignKeyField, FloatField
from pydantic import BaseModel, Field

from db import assessment_db
from .user import User  # 假设 User 模型可以从 .user 导入

# --- 静态配置 ---
ASSESSMENT_DATA_DIR = "assessment_data/"

ASSESSMENT_DISPLAY_GROUPS = {
    "SDS": ("心理健康", 1, 1),
    "SAS": ("心理健康", 1, 2),
    "BRMS": ("心理健康", 1, 3),
    "SAD": ("心理健康", 1, 4),
    "IAS": ("心理健康", 1, 5),
    "Lonely": ("心理健康", 1, 6),
    "SES": ("自我人格", 2, 1),
    "APS": ("自我人格", 2, 2),
    "CLT": ("自我人格", 2, 3),
    "mbti-93": ("自我人格", 2, 4),
    "AAS": ("亲密关系", 3, 1),
    "ECR": ("亲密关系", 3, 2),
    "LAMT": ("亲密关系", 3, 3),
    "LDCT": ("亲密关系", 3, 4),
    "TPS": ("趣味探索", 4, 1),
    "ICI": ("趣味探索", 4, 2),
    "REAL-MAJOR-V1": ("趣味探索", 4, 3),
    "AGLT": ("趣味探索", 4, 4),
    "RFLT": ("趣味探索", 4, 5),
    "SOUL-DRINK": ("趣味探索", 4, 6),
}

BDI_DIMENSIONS = {
    "emotion": {
        "label": "情绪",
        "questions": [1, 2, 10, 11],
        "evidence_labels": {
            1: "难过",
            2: "对未来悲观",
            10: "哭泣变化",
            11: "烦躁",
        },
        "stable": "情绪低落、无望感和烦躁目前不明显。",
        "mild": "情绪有一些波动，可能偶尔低落、悲观或更容易烦躁。",
        "moderate": "低落、悲观或烦躁已经比较明显，可能正在影响日常状态。",
        "high": "情绪困扰较重，低落、无望感或烦躁需要被认真关注。",
    },
    "interest": {
        "label": "兴趣",
        "questions": [4, 12, 20],
        "evidence_labels": {
            4: "日常兴趣下降",
            12: "对人与事的兴趣下降",
            20: "亲密或愉悦感相关兴趣变化",
        },
        "stable": "对日常事物和人际连接的兴趣整体保持得还可以。",
        "mild": "兴趣和连接感有一些下降，适合继续观察。",
        "moderate": "兴趣下降较明显，可能让日常行动和人际连接变得更费力。",
        "high": "兴趣和愉悦感受困扰较重，可能明显削弱生活动力。",
    },
    "body": {
        "label": "身体",
        "questions": [15, 16, 17, 18, 19],
        "evidence_labels": {
            15: "精力变化",
            16: "睡眠变化",
            17: "食欲变化",
            18: "体重变化",
            19: "健康担忧",
        },
        "stable": "精力、睡眠、食欲和身体担忧目前整体较稳定。",
        "mild": "身体状态有些波动，可能和精力、睡眠或食欲有关。",
        "moderate": "身体相关困扰比较明显，可能会放大情绪负担。",
        "high": "身体层面的压力较重，精力、睡眠、食欲或健康担忧需要认真照顾。",
    },
    "cognition": {
        "label": "认知",
        "questions": [3, 5, 6, 7, 8, 13, 14, 21],
        "evidence_labels": {
            3: "失败感",
            5: "罪恶感",
            6: "受惩罚感",
            7: "对自己失望",
            8: "自责",
            13: "决策困难",
            14: "无价值感",
            21: "注意力变化",
        },
        "stable": "自我评价、决策和注意力相关困扰目前不突出。",
        "mild": "自责、自我评价或专注力有一些波动，建议温和观察。",
        "moderate": "自责、自我价值感或决策专注困难比较明显，可能正在影响行动感。",
        "high": "认知层面的压力较重，自责、无价值感或专注困难需要被认真对待。",
    },
}

MENTAL_HEALTH_ANALYSIS_CONFIGS = {
    "SAS": {
        "analysis_name": "焦虑状态",
        "score_min": 1,
        "score_max": 4,
        "reverse_items": {5, 9, 13, 17, 19},
        "support_score": 60,
        "urgent_score": 70,
        "recording_focus": ["焦虑强度", "身体反应", "睡眠", "触发情境"],
        "recording_text": "建议接下来持续记录焦虑强度、身体反应、睡眠和触发情境，看看焦虑通常在什么时候升高。",
        "possible_causes": [
            "近期可能存在持续压力、任务不确定感或安全感不足的情况。",
            "当担心、身体紧绷和睡眠波动同时出现时，焦虑感容易被进一步放大。",
        ],
        "small_actions": [
            "先做 3 轮缓慢呼吸：吸气 4 秒，停 1 秒，呼气 6 秒。",
            "把今天最担心的事情写成一句话，再写下一个 10 分钟内能做的小动作。",
            "减少临睡前的信息刺激，给身体一点从紧绷里退下来的时间。",
        ],
        "support_text": "如果焦虑持续影响睡眠、学习、工作或人际互动，建议考虑联系心理咨询师或精神科医生获得支持。",
        "urgent_support_text": "如果焦虑已经明显影响日常生活，或伴随强烈惊恐、胸闷、失控感，建议尽快寻求专业支持。",
        "dimensions": {
            "worry": {
                "label": "担忧与紧张",
                "questions": [1, 2, 3, 4],
                "evidence_labels": {1: "紧张着急", 2: "无故害怕", 3: "烦乱惊恐", 4: "失控担心"},
                "stable": "担忧、害怕和惊恐感目前不明显。",
                "mild": "紧张和担心有一些波动，可能偶尔让你不太踏实。",
                "moderate": "担忧或惊恐感比较明显，可能正在占用不少注意力。",
                "high": "担忧、害怕或失控感较强，需要被认真照顾。",
            },
            "body": {
                "label": "身体唤起",
                "questions": [6, 10, 11, 12, 14, 18],
                "evidence_labels": {6: "手脚发抖", 10: "心跳加快", 11: "头晕", 12: "晕倒感", 14: "麻木刺痛", 18: "脸红发热"},
                "stable": "身体紧绷、心跳和头晕等反应目前不突出。",
                "mild": "身体偶尔会出现紧绷或不适，适合继续观察。",
                "moderate": "身体层面的焦虑反应较明显，可能让你更难放松。",
                "high": "身体唤起较强，心跳、发抖、头晕或麻木等反应需要重点关注。",
            },
            "fatigue_sleep": {
                "label": "疲惫与睡眠",
                "questions": [7, 8, 15, 16, 20, 19],
                "evidence_labels": {7: "疼痛困扰", 8: "疲乏", 15: "胃部不适", 16: "尿频", 20: "噩梦", 19: "睡眠不安"},
                "stable": "睡眠、精力和身体不适整体较稳定。",
                "mild": "疲惫、睡眠或身体不适有一些波动。",
                "moderate": "疲惫和睡眠相关困扰比较明显，可能影响恢复。",
                "high": "睡眠、疲惫或身体不适较重，需要给身体更多支持。",
            },
            "calm": {
                "label": "放松能力",
                "questions": [5, 9, 13, 17],
                "evidence_labels": {5: "难以安心", 9: "不易静坐", 13: "呼吸不顺", 17: "身体紧张"},
                "stable": "你仍能在不少时候保持安静、放松和可恢复的状态。",
                "mild": "放松能力有些起伏，压力上来时可能更难安定下来。",
                "moderate": "放松和恢复变得不太容易，焦虑可能正在拖长。",
                "high": "身心很难退回平静状态，建议优先安排恢复和支持。",
            },
        },
    },
    "BRMS": {
        "analysis_name": "情绪活跃度",
        "score_min": 0,
        "score_max": 4,
        "support_score": 15,
        "urgent_score": 22,
        "recording_focus": ["睡眠", "精力", "冲动", "消费或决策"],
        "recording_text": "建议接下来记录睡眠时长、精力高峰、冲动行为和重要决策，观察状态是否持续升高。",
        "possible_causes": [
            "近期睡眠减少、压力变化或生活节奏过快，都可能让情绪和行动速度被推高。",
            "当精力、表达和自我评价同时升高时，判断和边界感可能会受到影响。",
        ],
        "small_actions": [
            "今晚先把睡眠放到第一优先级，减少咖啡因、酒精和熬夜刺激。",
            "重要决定先延迟 24 小时，再找一个可信任的人一起确认。",
            "如果发现自己停不下来，先暂停高刺激社交、消费或争论场景。",
        ],
        "support_text": "如果情绪高涨、睡眠减少或冲动行为已经影响生活，建议尽快咨询心理咨询师或精神科医生。",
        "urgent_support_text": "如果近期几乎不睡、冲动明显、难以控制言行或严重影响生活，建议尽快联系精神科医生或前往医院评估。",
        "risk_note": {
            "threshold": 22,
            "text": "这份结果提示近期情绪和行为活跃度较高。请优先保证睡眠与安全，避免独自做重大决定，并尽快寻求专业支持。",
        },
        "dimensions": {
            "activation": {
                "label": "活动与表达",
                "questions": [1, 2, 4],
                "evidence_labels": {1: "活动增多", 2: "话多", 4: "音量升高"},
                "stable": "活动量、说话速度和表达强度目前较平稳。",
                "mild": "活动和表达略有升高，可能比平时更活跃。",
                "moderate": "活动量或表达强度比较明显，可能让人感觉难以慢下来。",
                "high": "活动和表达强度较高，需要留意是否已经影响休息或互动。",
            },
            "thought_self": {
                "label": "思维与自我评价",
                "questions": [3, 7],
                "evidence_labels": {3: "思绪跳跃", 7: "自我评价升高"},
                "stable": "思路连贯性和自我评价目前较稳定。",
                "mild": "思绪或自我评价有些升高，适合继续观察。",
                "moderate": "思维速度或自我评价升高较明显，可能影响判断。",
                "high": "思维跳跃或夸大感较强，建议尽快获得专业评估。",
            },
            "mood_control": {
                "label": "心境与控制",
                "questions": [5, 6],
                "evidence_labels": {5: "急躁易怒", 6: "情绪高涨"},
                "stable": "情绪高涨、急躁和控制感目前不突出。",
                "mild": "情绪活跃度有些升高，偶尔可能更急或更兴奋。",
                "moderate": "心境高涨或易激惹比较明显，需要留意人际影响。",
                "high": "情绪高涨或冲动控制较困难，建议尽快寻求支持。",
            },
            "boundary": {
                "label": "边界与冲动",
                "questions": [8, 10],
                "evidence_labels": {8: "支配他人", 10: "性兴趣增强"},
                "stable": "人际边界和冲动相关变化目前较少。",
                "mild": "边界感或冲动有轻微波动，适合提醒自己放慢。",
                "moderate": "边界或冲动相关变化较明显，可能带来后续压力。",
                "high": "冲动和边界风险较高，建议暂缓高风险决定并寻求支持。",
            },
            "sleep_function": {
                "label": "睡眠与功能",
                "questions": [9, 11],
                "evidence_labels": {9: "睡眠减少", 11: "日常功能下降"},
                "stable": "睡眠和日常功能目前比较稳定。",
                "mild": "睡眠或日常效率有些变化，建议尽早调整。",
                "moderate": "睡眠减少或功能受影响较明显，需要优先恢复节律。",
                "high": "睡眠和功能受影响较重，建议尽快获得专业支持。",
            },
        },
    },
    "SAD": {
        "analysis_name": "社交回避与苦恼",
        "score_min": 0,
        "score_max": 1,
        "reverse_items": {17},
        "support_score": 21,
        "recording_focus": ["社交场景", "紧张程度", "回避行为", "自我评价"],
        "recording_text": "建议记录让你想回避的社交场景、当时的紧张程度和事后真实结果，帮助你看见哪些担心被放大了。",
        "possible_causes": [
            "陌生场合、被关注或需要表达观点时，社交压力可能更容易升高。",
            "如果长期把社交当成考试，自我评价压力会让回避变得更容易发生。",
        ],
        "small_actions": [
            "先选一个低压力场景，完成一句问候或一个简短回应。",
            "社交前准备 2 个轻松话题，降低临场空白感。",
            "社交后写下一个实际发生的好结果，帮助大脑更新预期。",
        ],
        "support_text": "如果社交回避已经影响学习、工作、关系或生活范围，建议考虑心理咨询，循序渐进地练习应对。",
        "dimensions": {
            "avoidance": {
                "label": "回避倾向",
                "questions": [3, 9, 10, 15, 17],
                "evidence_labels": {3: "回避聚会", 9: "回避陌生人", 10: "人群不自在", 15: "不喜欢社交", 17: "难以镇定"},
                "stable": "你目前不太容易因为社交而明显回避。",
                "mild": "某些社交场景会让你有一点想退开。",
                "moderate": "回避倾向比较明显，可能限制了一些互动机会。",
                "high": "社交回避较强，可能已经让生活范围变窄。",
            },
            "interaction_distress": {
                "label": "互动紧张",
                "questions": [1, 2, 4, 6, 7, 12, 18, 22, 23, 25, 26],
                "evidence_labels": {1: "小组交谈困难", 2: "异性面前不自在", 4: "群体紧张", 6: "找不到话题", 7: "陌生人紧张", 12: "拘束", 18: "初见紧张", 22: "神经质", 23: "局促不安", 25: "不自在", 26: "交谈困难"},
                "stable": "日常互动中的紧张感目前不突出。",
                "mild": "互动时偶尔会紧张，但仍有可调整空间。",
                "moderate": "互动紧张比较明显，可能消耗不少精力。",
                "high": "人际互动带来的紧张较强，需要更温和地练习和支持。",
            },
            "attention_performance": {
                "label": "被关注压力",
                "questions": [5, 8, 13, 14, 27, 28],
                "evidence_labels": {5: "被关注焦虑", 8: "表达信心不足", 13: "正式场合不自在", 14: "眼神回避", 27: "担心说错", 28: "容易窘迫"},
                "stable": "被关注或正式表达时的压力目前较少。",
                "mild": "被关注时会有一些紧张，属于可以练习的范围。",
                "moderate": "被关注和表达压力比较明显，可能影响表现。",
                "high": "被关注时的压力较强，容易引发明显退缩或自责。",
            },
            "self_connection": {
                "label": "社交自我感",
                "questions": [11, 19, 20, 21, 24],
                "evidence_labels": {11: "结识新朋友困难", 19: "希望更会社交", 20: "社交比较低", 21: "不满意社交能力", 24: "在人群中孤单"},
                "stable": "你对自己的社交能力和连接感整体较稳定。",
                "mild": "社交自信有一些波动，偶尔会和别人比较。",
                "moderate": "社交自我评价压力较明显，可能让你更难放松。",
                "high": "社交自我感承压较重，需要减少苛责并获得支持。",
            },
        },
    },
    "IAS": {
        "analysis_name": "互动焦虑",
        "score_min": 1,
        "score_max": 5,
        "reverse_items": {3, 6, 10, 15},
        "support_score": 50,
        "urgent_score": 66,
        "recording_focus": ["互动对象", "紧张程度", "身体反应", "事后评价"],
        "recording_text": "建议记录不同互动对象带来的紧张程度、身体反应和事后评价，分辨哪些场景最容易触发焦虑。",
        "possible_causes": [
            "陌生人、权威人士、面试或电话沟通等高评价场景，可能更容易激活焦虑。",
            "如果总担心被评价，互动前后的反复回想会让焦虑维持得更久。",
        ],
        "small_actions": [
            "互动前先把目标降到“完成一次连接”，不用要求自己表现完美。",
            "给不熟的人发消息或打电话前，先写下 1 句开场白。",
            "互动后只复盘一个可改进点，也写下一个做得还可以的地方。",
        ],
        "support_text": "如果互动焦虑持续影响沟通、工作学习或亲密关系，心理咨询会很适合用来练习更稳定的互动方式。",
        "urgent_support_text": "如果大多数互动都带来强烈焦虑并明显影响生活，建议尽快寻求专业支持。",
        "dimensions": {
            "group": {
                "label": "群体场合",
                "questions": [1, 2, 5, 15],
                "evidence_labels": {1: "聚会紧张", 2: "陌生群体不自在", 5: "聚会焦虑", 15: "不同人群中难放松"},
                "stable": "群体场合中的紧张感目前不突出。",
                "mild": "群体互动有些紧张，但仍可逐步适应。",
                "moderate": "群体场合的焦虑比较明显，可能让你提前消耗。",
                "high": "群体互动压力较强，建议从更安全的小场景练习。",
            },
            "specific_interaction": {
                "label": "具体互动",
                "questions": [3, 7, 12, 13],
                "evidence_labels": {3: "异性交谈不放松", 7: "同性陌生人紧张", 12: "吸引对象前紧张", 13: "电话紧张"},
                "stable": "一对一或具体对象互动中的焦虑目前较少。",
                "mild": "某些互动对象会带来轻微紧张。",
                "moderate": "具体互动场景的紧张比较明显，可能影响表达。",
                "high": "具体互动带来的压力较强，容易让你回避或过度准备。",
            },
            "authority_evaluation": {
                "label": "评价压力",
                "questions": [4, 8, 14],
                "evidence_labels": {4: "老师或上司面前紧张", 8: "面试紧张", 14: "权威人士前紧张"},
                "stable": "面对评价或权威时的压力目前较可控。",
                "mild": "被评价时会有一些紧张，适度准备会有帮助。",
                "moderate": "评价压力比较明显，可能影响临场发挥。",
                "high": "评价场景带来的焦虑较强，建议更系统地练习应对。",
            },
            "self_confidence": {
                "label": "社交自信",
                "questions": [6, 9, 10, 11],
                "evidence_labels": {6: "羞怯感", 9: "希望更自信", 10: "社交焦虑", 11: "害羞"},
                "stable": "你对社交中的自己整体较有稳定感。",
                "mild": "社交自信有一些波动，偶尔会怀疑表现。",
                "moderate": "社交自信承压比较明显，可能让互动变得费力。",
                "high": "社交自信压力较高，需要减少自责并获得更多支持。",
            },
        },
    },
    "Lonely": {
        "analysis_name": "关系连接感",
        "score_min": 0,
        "score_max": 1,
        "reverse_items": {1, 4, 7, 9, 11, 14, 17, 18, 21, 22, 23, 24, 29, 31, 36, 37, 39, 42, 45, 47, 48, 50, 52, 56, 59, 60},
        "support_score": 31,
        "urgent_score": 46,
        "recording_focus": ["连接感", "支持来源", "主动联系", "孤独时刻"],
        "recording_text": "建议记录哪些时刻最容易感到孤独、哪些人或场景能带来一点连接感，慢慢找到可依靠的关系入口。",
        "possible_causes": [
            "当友情、家庭、亲密关系或社群中的支持感不足时，孤独感会更容易累积。",
            "长期缺少被理解和被回应的体验，可能会让人更难主动靠近别人。",
        ],
        "small_actions": [
            "先选一个相对安全的人，发出一句具体、低压力的问候。",
            "把“我需要被支持的地方”写成一句话，帮助自己更清楚地表达需求。",
            "尝试加入一个低门槛的小活动，让连接从固定频率开始，而不是一次聊很深。",
        ],
        "support_text": "如果孤独感持续存在，并明显影响情绪、自我价值感或生活动力，建议考虑心理咨询或支持性小组。",
        "urgent_support_text": "如果孤独感已经非常强烈，并伴随明显绝望、退缩或长期低落，建议尽快寻求专业支持。",
        "dimensions": {
            "family": {
                "label": "家庭连接",
                "questions": [1, 6, 10, 14, 20, 23, 25, 29, 32, 34, 36, 40, 42, 44, 47, 50, 54, 57, 59],
                "evidence_labels": {6: "家庭相处不佳", 20: "不被家人理解", 25: "亲戚难以支持", 32: "不易开放", 40: "缺少交流", 44: "家人挑剔", 54: "联系较少", 57: "回避家人"},
                "stable": "家庭关系中的支持和归属感整体较稳定。",
                "mild": "家庭连接有一些距离感，压力大时可能更明显。",
                "moderate": "家庭支持感不足比较明显，可能影响安全感。",
                "high": "家庭连接承压较重，需要为自己寻找更安全的支持来源。",
            },
            "friendship": {
                "label": "友情支持",
                "questions": [3, 4, 7, 11, 13, 16, 19, 22, 24, 26, 30, 33, 39, 43, 46, 48, 51, 53, 55, 60],
                "evidence_labels": {3: "被动等待邀约", 13: "交友受挫", 16: "朋友不多", 19: "难以求助朋友", 26: "少被理解", 30: "友谊失望", 43: "缺少坦诚朋友", 46: "可靠朋友少", 53: "难以邀约", 55: "担心朋友不长久"},
                "stable": "友情中的理解、支持和陪伴整体较足。",
                "mild": "友情连接有些空隙，适合用小互动慢慢补上。",
                "moderate": "友情支持感不足比较明显，可能让你在需要时觉得孤单。",
                "high": "友情连接承压较重，建议从一两个安全关系开始重建支持。",
            },
            "romance": {
                "label": "亲密关系",
                "questions": [5, 9, 15, 18, 21, 28, 31, 35, 41, 45, 52, 58],
                "evidence_labels": {5: "缺少重要恋爱关系", 15: "表达爱困难", 28: "关系契合不足", 35: "难以信任爱意", 41: "缺少被理解关系", 58: "缺少情感安全"},
                "stable": "亲密关系或亲密需求中的安全感整体较稳定。",
                "mild": "亲密连接有一些缺口，可能偶尔让你失落。",
                "moderate": "亲密关系中的理解和安全感不足比较明显。",
                "high": "亲密连接承压较重，需要温和地照顾自己的依恋和安全感需求。",
            },
            "community": {
                "label": "社群归属",
                "questions": [2, 8, 12, 17, 27, 38, 49, 56],
                "evidence_labels": {2: "身边人陌生", 8: "缺少团体支持", 12: "社区不关心", 27: "社区无人关心", 38: "团体满足少", 49: "邻里支持少"},
                "stable": "社群、邻里或团体中的归属感整体较稳定。",
                "mild": "社群归属有些薄弱，可以从低门槛活动开始增加连接。",
                "moderate": "社群支持感不足比较明显，可能让你觉得缺少外部依靠。",
                "high": "社群归属承压较重，需要寻找更稳定、更接纳的小群体。",
            },
        },
    },
    "DLS": "Lonely",
}


def get_assessment_display_meta(short_name: str) -> Dict[str, Any]:
    group, group_order, display_order = ASSESSMENT_DISPLAY_GROUPS.get(
        short_name,
        ("其他", 99, 99),
    )
    return {
        "display_group": group,
        "display_group_order": group_order,
        "display_order": display_order,
    }


def _level_from_average(score: float) -> str:
    if score < 0.75:
        return "相对稳定"
    if score < 1.5:
        return "有些波动"
    if score < 2.25:
        return "需要关注"
    return "明显承压"


def _level_from_ratio(score: float) -> str:
    if score < 0.25:
        return "相对稳定"
    if score < 0.5:
        return "有些波动"
    if score < 0.75:
        return "需要关注"
    return "明显承压"

# ---------------------------------------------------
# 1. Peewee 数据模型 (数据库表结构)
# ---------------------------------------------------

class Scale(Model):
    """量表定义表 (题库总表)"""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    short_name = CharField(max_length=50, unique=True, index=True, help_text="量表的唯一简称, 如 'PHQ-9'")
    name = CharField(max_length=255, help_text="量表的全称")
    description = TextField(help_text="对量表的简短描述")
    category = CharField(max_length=50, index=True, default='专业测试', help_text="前端分类: '专业测试' 或 '趣味测试'")
    assessment_type = CharField(max_length=50, index=True, default='scoring', help_text="后端类型: 'scoring' (打分) 或 'categorical' (分类)")
    json_data = TextField(help_text="存储量表完整结构(题目、选项、计分规则、解释)的JSON字符串")
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = assessment_db
        table_name = 'scales'

    @property
    def display_group(self) -> str:
        return get_assessment_display_meta(self.short_name)["display_group"]

    @property
    def display_group_order(self) -> int:
        return get_assessment_display_meta(self.short_name)["display_group_order"]

    @property
    def display_order(self) -> int:
        return get_assessment_display_meta(self.short_name)["display_order"]

class UserAssessment(Model):
    """用户测评记录表"""
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user = ForeignKeyField(User, backref='assessments', field='id', on_delete='CASCADE')
    scale = ForeignKeyField(Scale, backref='attempts', field='id', on_delete='SET NULL', null=True)
    answers = TextField(help_text="用户提交的答案详情 (JSON字符串)")
    raw_score = FloatField(null=True, help_text="原始总分")
    final_score = FloatField(null=True, help_text="最终标准分 (如果适用)")
    result_level = CharField(max_length=255, null=True, help_text="结果等级或分类名, 如 '轻度抑郁' 或 '图书馆生态信息学'")
    result_interpretation = TextField(null=True, help_text="对结果的详细文字解释")
    result_recommendation = TextField(null=True, help_text="给用户的建议")
    result_details = TextField(null=True, help_text="存储额外结果详情的JSON字符串")
    
    completed_at = DateTimeField(default=datetime.now, help_text="测评完成时间")

    class Meta:
        database = assessment_db
        table_name = 'user_assessments'

# ---------------------------------------------------
# 2. Pydantic 数据模型 (API接口数据结构)
# ---------------------------------------------------

class ScaleInfoResponse(BaseModel):
    id: str
    short_name: str
    name: str
    description: str
    instructions: Optional[str] = None  # <--- 在这里添加 instructions 字段
    cover_image_url: Optional[str] = None
    category: str
    assessment_type: str
    display_group: Optional[str] = None
    display_group_order: Optional[int] = None
    display_order: Optional[int] = None
    class Config:
        from_attributes = True

class ScaleDetailResponse(ScaleInfoResponse):
    json_data: Dict[str, Any]

class SubmitAnswersRequest(BaseModel):
    scale_id: str
    answers: Dict[str, str] 

class UserAssessmentResponse(BaseModel):
    id: str
    user_id: str
    scale_id: str
    answers: Dict[str, Any]
    raw_score: Optional[float] = None
    final_score: Optional[float] = None
    result_level: Optional[str] = None
    result_interpretation: Optional[str] = None
    result_recommendation: Optional[str] = None
    result_details: Optional[Dict[str, Any]] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    completed_at: datetime
    scale_info: Optional[ScaleInfoResponse] = None
    scale_details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

# ---------------------------------------------------
# 3. 数据表访问类 (封装所有数据库操作)
# ---------------------------------------------------

class AssessmentTables:
    """封装所有与测评相关的数据库操作"""
    def __init__(self, db_connection):
        self.db = db_connection
        # self.db.drop_tables([Scale, UserAssessment], safe=True)
        self.db.create_tables([Scale, UserAssessment])
        self.initialize_scales_from_json()

    def initialize_scales_from_json(self):
        """
        【修改版】从 /assessment_data/ 文件夹读取JSON文件并加载到数据库。
        如果数据库中已存在同名short_name的量表，则会跳过该文件。
        """
        print("🔍 Starting scale initialization from JSON files...")
        if not os.path.exists(ASSESSMENT_DATA_DIR):
            print(f"⚠️ Directory '{ASSESSMENT_DATA_DIR}' not found. Skipping initialization.")
            return

        for filename in os.listdir(ASSESSMENT_DATA_DIR):
            if filename.endswith(".json"):
                # 1. 从文件名直接获取 short_name (例如 'phq-9.json' -> 'phq-9')
                short_name_from_file = filename[:-5]

                # 2. 查询数据库，检查该 short_name 是否已存在
                # Peewee的 .get_or_none() 方法非常适合这个场景
                if Scale.get_or_none(Scale.short_name == short_name_from_file):
                    print(f"ℹ️ Scale '{short_name_from_file}' already exists. Refreshing metadata from '{filename}'.")
                    filepath = os.path.join(ASSESSMENT_DATA_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            scale_info = data.get('scale_info', {})
                            (
                                Scale.update(
                                    name=scale_info.get('name', 'N/A'),
                                    description=scale_info.get('description', ''),
                                    category=scale_info.get('category') or '专业测试',
                                    assessment_type=scale_info.get('assessment_type') or 'scoring',
                                    json_data=json.dumps(data, ensure_ascii=False),
                                    updated_at=datetime.now()
                                )
                                .where(Scale.short_name == short_name_from_file)
                                .execute()
                            )
                    except Exception as e:
                        print(f"❌ Error refreshing file {filename}: {e}")
                    continue
                
                # 4. 如果不存在，执行加载和创建逻辑
                print(f"➕ Scale '{short_name_from_file}' not found. Loading from '{filename}'...")
                filepath = os.path.join(ASSESSMENT_DATA_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        scale_info = data.get('scale_info', {})
                        
                        # 为确保数据一致性，我们优先使用文件名作为short_name
                        # 并使用 create() 方法，因为它明确表示创建新记录
                        Scale.create(
                            short_name=short_name_from_file,
                            name=scale_info.get('name', 'N/A'),
                            description=scale_info.get('description', ''),
                            category=scale_info.get('category') or '专业测试',
                            assessment_type=scale_info.get('assessment_type') or 'scoring',
                            json_data=json.dumps(data, ensure_ascii=False)
                        )
                        print(f"✅ Scale '{short_name_from_file}' loaded successfully.")
                except Exception as e:
                    # 增加错误处理，防止因单个文件格式错误导致整个初始化中断
                    print(f"❌ Error processing file {filename}: {e}")

        print("✨ Scale initialization complete.")

    # --- ▼▼▼ 在这里添加下面的新方法 ▼▼▼ ---
    def get_formatted_scale_details_by_id(self, scale_id: str) -> Optional[Dict[str, Any]]:
        """
        【新增】获取并格式化单个量表详情，专为API响应设计。
        这个方法会解析 json_data，提取出 instructions 和题目等信息，
        并整合成一个扁平的字典返回。
        """
        scale = self.get_scale_by_id(scale_id)
        if not scale:
            return None

        # 解析存储在数据库中的JSON字符串
        try:
            full_data = json.loads(scale.json_data)
        except json.JSONDecodeError:
            # 如果JSON格式错误，返回基础信息并忽略附加数据
            full_data = {}

        scale_info = full_data.get('scale_info', {})

        # 组装前端需要的最终数据结构
        display_meta = get_assessment_display_meta(scale.short_name)
        response_data = {
            "id": scale.id,
            "short_name": scale.short_name,
            "name": scale.name,
            "description": scale.description,
            "category": scale.category or "专业测试",
            "assessment_type": scale.assessment_type or "scoring",
            **display_meta,
            # 从解析后的JSON中提取 instructions
            "instructions": scale_info.get('instructions'),
            "cover_image_url": scale_info.get('cover_image_url'),
            # 同时也可以把题目和选项带上，供测试页面使用
            "questions": full_data.get('questions', []),
            "choices": full_data.get('choices', [])
        }
        return response_data
    def get_all_scales(self) -> List[Scale]:
        scales = list(Scale.select(
            Scale.id, Scale.short_name, Scale.name, Scale.description, Scale.category, Scale.assessment_type
        ))
        return sorted(scales, key=lambda scale: (scale.display_group_order, scale.display_order, scale.name))
        
    def get_scale_by_id(self, scale_id: str) -> Optional[Scale]:
        return Scale.get_or_none(Scale.id == scale_id)

    def _calculate_scoring_result(self, request_answers: Dict[str, Any], scale_data: Dict) -> Dict:
        """【修改版】处理打分测试的计分逻辑，支持反向计分和谎言量表"""
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        interpretations = scale_data.get('interpretations', [])
        questions = scale_data.get('questions', [])
        common_choice_scores = self._extract_choice_scores(scale_data.get('choices', []))
        default_score_bounds = self._get_score_bounds(common_choice_scores)
        question_score_bounds = self._build_question_score_bounds(questions, default_score_bounds)
        
        # 1. 获取计分规则
        # 兼容 "reverse_scoring_items" 和 "reverse_scored_items" 两种可能的拼写
        reverse_items = set(rules.get('reverse_scoring_items', []) + rules.get('reverse_scored_items', []))
        reverse_items.update(self._get_question_level_reverse_items(questions))
        scale_short_name = scale_data.get('scale_info', {}).get('short_name')
        analysis_config = self._get_mental_health_analysis_config(scale_short_name)
        if isinstance(analysis_config, dict):
            reverse_items.update(analysis_config.get("reverse_items", set()))
        
        # 新增：获取谎言量表题目，如果JSON中定义了的话
        lie_scale_items = set(rules.get('lie_scale_items', []))

        raw_score = 0
        # 2. 遍历用户答案进行计分
        for q_order_str, score_str in request_answers.items():
            try:
                q_order = int(q_order_str)
                score = float(score_str)
            except (ValueError, TypeError):
                continue # 如果题目序号或分数不是数字，则跳过

            # 3. 如果是谎言量表题目，则不计入总分
            if q_order in lie_scale_items:
                continue

            # 4. 应用反向计分逻辑
            if q_order in reverse_items:
                min_score, max_score = question_score_bounds.get(q_order, default_score_bounds)
                raw_score += (min_score + max_score - score)
            else:
                # 正常计分
                raw_score += score
                
        # 5. 最终分数计算 (例如乘以系数等，当前用不上但保留)
        final_score = raw_score * rules.get('multiplier', 1)
        post_action = rules.get('post_action')
        if post_action in {"to_integer", "round"}:
            final_score = round(final_score)

        result = {"raw_score": raw_score, "final_score": final_score, "result_details": None}
        
        # 6. 匹配分数解释
        for interp in interpretations:
            if interp.get('min_score', -1) <= final_score <= interp.get('max_score', float('inf')):
                result.update({
                    "result_level": interp.get('level'),
                    "result_interpretation": interp.get('interpretation', ''),
                    "result_recommendation": interp.get('recommendation', ''),
                })
                break
                
        return result

    def _extract_choice_scores(self, choices: List[Dict[str, Any]]) -> List[float]:
        scores = []
        for choice in choices or []:
            try:
                scores.append(float(choice.get("score")))
            except (TypeError, ValueError):
                continue
        return scores

    def _get_score_bounds(self, scores: List[float]) -> Tuple[float, float]:
        if not scores:
            return (0, 1)
        return (min(scores), max(scores))

    def _build_question_score_bounds(
        self,
        questions: List[Dict[str, Any]],
        default_bounds: Tuple[float, float],
    ) -> Dict[int, Tuple[float, float]]:
        bounds = {}
        for question in questions or []:
            try:
                order = int(question.get("order"))
            except (TypeError, ValueError):
                continue

            question_choices = question.get("choices") or question.get("options") or []
            question_scores = self._extract_choice_scores(question_choices)
            bounds[order] = self._get_score_bounds(question_scores) if question_scores else default_bounds
        return bounds

    def _get_question_level_reverse_items(self, questions: List[Dict[str, Any]]) -> Set[int]:
        reverse_items = set()
        for question in questions or []:
            if not (question.get("is_reverse_scored") or question.get("reverse_scored")):
                continue
            try:
                reverse_items.add(int(question.get("order")))
            except (TypeError, ValueError):
                continue
        return reverse_items

    def _scale_uses_reverse_scoring(self, scale_data: Dict[str, Any]) -> bool:
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        if rules.get('reverse_scoring_items') or rules.get('reverse_scored_items'):
            return True
        scale_short_name = scale_data.get('scale_info', {}).get('short_name')
        analysis_config = self._get_mental_health_analysis_config(scale_short_name)
        if isinstance(analysis_config, dict) and analysis_config.get("reverse_items"):
            return True
        return bool(self._get_question_level_reverse_items(scale_data.get('questions', [])))

    def ensure_scoring_result_for_record(self, record: UserAssessment) -> None:
        """Refresh historical scoring records that may have been saved before scoring fixes."""
        if not record or not record.scale or record.scale.assessment_type != "scoring":
            return

        try:
            scale_data = json.loads(record.scale.json_data)
        except json.JSONDecodeError:
            return

        should_refresh = record.result_level is None or self._scale_uses_reverse_scoring(scale_data)
        if not should_refresh:
            return

        try:
            answers = json.loads(record.answers) if record.answers else {}
        except json.JSONDecodeError:
            return

        result_data = self._calculate_scoring_result(answers, scale_data)
        result_data = self._attach_ai_analysis(record.scale.short_name, answers, result_data)

        has_changes = (
            record.raw_score != result_data.get("raw_score")
            or record.final_score != result_data.get("final_score")
            or record.result_level != result_data.get("result_level")
            or record.result_interpretation != result_data.get("result_interpretation")
            or record.result_recommendation != result_data.get("result_recommendation")
        )

        next_details = result_data.get("result_details")
        next_details_json = json.dumps(next_details, ensure_ascii=False) if next_details else None
        if record.result_details != next_details_json:
            has_changes = True

        if not has_changes:
            return

        record.raw_score = result_data.get("raw_score")
        record.final_score = result_data.get("final_score")
        record.result_level = result_data.get("result_level")
        record.result_interpretation = result_data.get("result_interpretation")
        record.result_recommendation = result_data.get("result_recommendation")
        record.result_details = next_details_json
        record.save()

    def _build_bdi_ai_analysis(
        self,
        request_answers: Dict[str, Any],
        result_level: Optional[str],
        final_score: Optional[float],
    ) -> Dict[str, Any]:
        numeric_answers: Dict[int, float] = {}
        for q_order_str, score_str in request_answers.items():
            try:
                numeric_answers[int(q_order_str)] = float(score_str)
            except (ValueError, TypeError):
                continue

        dimensions = []
        elevated_labels = []
        for key, config in BDI_DIMENSIONS.items():
            question_ids = config["questions"]
            scores = [numeric_answers.get(question_id, 0) for question_id in question_ids]
            average_score = sum(scores) / len(question_ids) if question_ids else 0
            level = _level_from_average(average_score)

            if level == "相对稳定":
                summary = config["stable"]
            elif level == "有些波动":
                summary = config["mild"]
            elif level == "需要关注":
                summary = config["moderate"]
            else:
                summary = config["high"]

            evidence = [
                config["evidence_labels"][question_id]
                for question_id in question_ids
                if numeric_answers.get(question_id, 0) > 0
            ][:4]

            if level in {"需要关注", "明显承压"}:
                elevated_labels.append(config["label"])

            dimensions.append({
                "key": key,
                "label": config["label"],
                "level": level,
                "score": round(average_score, 2),
                "summary": summary,
                "evidence": evidence,
            })

        q9_score = numeric_answers.get(9, 0)
        risk_dimension_level = _level_from_average(q9_score)
        if q9_score >= 2:
            risk_summary = "你在自伤或自杀念头题项上选择了较高分值，这需要被立即认真对待。"
        elif q9_score == 1:
            risk_summary = "你提到过相关念头，虽然不一定代表会付诸行动，但很值得尽快获得支持。"
        else:
            risk_summary = "当前未从 Q9 看到明显自伤或自杀念头信号。"

        dimensions.append({
            "key": "risk",
            "label": "风险",
            "level": risk_dimension_level,
            "score": q9_score,
            "summary": risk_summary,
            "evidence": ["自伤或自杀念头"] if q9_score > 0 else [],
        })

        if q9_score >= 2:
            professional_support = {
                "recommended": True,
                "urgency": "urgent",
                "text": "建议尽快联系身边可信任的人、心理咨询师或精神科医生；如果你担心自己可能会伤害自己，请立即联系当地紧急支持资源或急救服务。",
            }
            risk_note = {
                "triggered": True,
                "level": "high",
                "text": "这份结果提示需要优先保障安全。请不要独自承受，尽快告诉一个可信任的人，并寻求专业或紧急支持。",
            }
        elif q9_score == 1:
            professional_support = {
                "recommended": True,
                "urgency": "suggested",
                "text": "建议尽快找可信任的人聊聊，也建议考虑联系心理咨询师或精神科医生获得支持。",
            }
            risk_note = {
                "triggered": True,
                "level": "medium",
                "text": "你提到过相关念头，这已经值得被认真照顾。请优先让自己处在有人支持、相对安全的环境中。",
            }
        else:
            professional_support = {
                "recommended": bool(final_score is not None and final_score >= 20),
                "urgency": "suggested" if final_score is not None and final_score >= 20 else "optional",
                "text": "如果这种状态持续两周以上，或明显影响学习、工作、人际和生活，建议联系心理咨询师或精神科医生。",
            }
            risk_note = {
                "triggered": False,
                "level": "none",
                "text": "",
            }

        if q9_score >= 2:
            state_summary = f"你的结果为{result_level or '当前状态'}，并出现需要优先关注的安全风险信号，请先确保身边有人支持。"
        elif q9_score == 1:
            state_summary = f"你的结果为{result_level or '当前状态'}，同时出现过相关风险念头，建议尽快找可信任的人或专业人士聊聊。"
        elif elevated_labels:
            state_summary = f"你的结果为{result_level or '当前状态'}，主要需要关注{ '、'.join(elevated_labels[:3]) }相关变化。"
        else:
            state_summary = f"你的结果为{result_level or '当前状态'}，目前各维度整体较平稳，仍可以继续观察近期变化。"

        possible_causes = [
            "近期可能存在持续压力、恢复不足或生活节奏被打乱的情况。",
            "当情绪、身体和自我评价同时承压时，低落感可能会被进一步放大。",
        ]
        if any(item["key"] == "body" and item["level"] in {"需要关注", "明显承压"} for item in dimensions):
            possible_causes.append("睡眠、精力、食欲或身体担忧的变化，可能正在影响你的情绪恢复。")
        if any(item["key"] == "interest" and item["level"] in {"需要关注", "明显承压"} for item in dimensions):
            possible_causes.append("兴趣下降和与他人连接减少，可能让你更难从日常生活中获得支持感。")

        small_actions = [
            "今天先完成一件 10 分钟内能做完的小事，给自己一个可完成的起点。",
            "连续 3 天记录心情、睡眠、精力和触发事件，观察状态是否有规律。",
            "找一个可信任的人说一句真实近况，不需要一次讲完所有事情。",
        ]
        if q9_score > 0:
            small_actions.insert(0, "先把自己移动到更安全、有人陪伴或更容易求助的环境里。")

        return {
            "state_summary": state_summary,
            "dimensions": dimensions,
            "possible_causes": possible_causes,
            "small_actions": small_actions,
            "professional_support": professional_support,
            "emotion_recording": {
                "recommended": True,
                "focus": ["心情", "睡眠", "精力", "触发事件"],
                "text": "建议接下来持续记录情绪，重点观察低落、睡眠、精力和触发事件的变化。",
            },
            "risk_note": risk_note,
        }

    def _get_mental_health_analysis_config(self, scale_short_name: Optional[str]) -> Optional[Dict[str, Any]]:
        config = MENTAL_HEALTH_ANALYSIS_CONFIGS.get(scale_short_name)
        if isinstance(config, str):
            return MENTAL_HEALTH_ANALYSIS_CONFIGS.get(config)
        return config

    def _normalize_answer_scores(
        self,
        request_answers: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[int, float]:
        score_min = float(config.get("score_min", 0))
        score_max = float(config.get("score_max", 1))
        reverse_items = set(config.get("reverse_items", set()))
        normalized_scores: Dict[int, float] = {}

        for q_order_str, score_value in request_answers.items():
            try:
                q_order = int(q_order_str)
                score = float(score_value)
            except (ValueError, TypeError):
                continue

            if q_order in reverse_items:
                score = score_min + score_max - score

            normalized_scores[q_order] = score

        return normalized_scores

    def _build_configured_mental_health_analysis(
        self,
        scale_short_name: str,
        request_answers: Dict[str, Any],
        result_level: Optional[str],
        final_score: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        config = self._get_mental_health_analysis_config(scale_short_name)
        if not config:
            return None

        numeric_answers = self._normalize_answer_scores(request_answers, config)
        score_min = float(config.get("score_min", 0))
        score_max = float(config.get("score_max", 1))
        score_range = max(score_max - score_min, 1)

        dimensions = []
        elevated_labels = []
        for key, dimension_config in config.get("dimensions", {}).items():
            question_ids = dimension_config.get("questions", [])
            scores = [numeric_answers.get(question_id, score_min) for question_id in question_ids]
            average_score = sum(scores) / len(question_ids) if question_ids else score_min
            ratio_score = (average_score - score_min) / score_range
            level = _level_from_ratio(ratio_score)

            if level == "相对稳定":
                summary = dimension_config.get("stable", "")
            elif level == "有些波动":
                summary = dimension_config.get("mild", "")
            elif level == "需要关注":
                summary = dimension_config.get("moderate", "")
            else:
                summary = dimension_config.get("high", "")

            evidence_labels = dimension_config.get("evidence_labels", {})
            evidence = [
                evidence_labels[question_id]
                for question_id in question_ids
                if question_id in evidence_labels and numeric_answers.get(question_id, score_min) > score_min
            ][:4]

            if level in {"需要关注", "明显承压"}:
                elevated_labels.append(dimension_config.get("label", key))

            dimensions.append({
                "key": key,
                "label": dimension_config.get("label", key),
                "level": level,
                "score": round(average_score, 2),
                "summary": summary,
                "evidence": evidence,
            })

        score = float(final_score) if final_score is not None else None
        urgent_score = config.get("urgent_score")
        support_score = config.get("support_score")
        urgent_triggered = score is not None and urgent_score is not None and score >= urgent_score
        support_recommended = urgent_triggered or (
            score is not None and support_score is not None and score >= support_score
        )

        if urgent_triggered:
            professional_support = {
                "recommended": True,
                "urgency": "urgent",
                "text": config.get("urgent_support_text") or config.get("support_text") or "",
            }
        else:
            professional_support = {
                "recommended": bool(support_recommended),
                "urgency": "suggested" if support_recommended else "optional",
                "text": config.get("support_text") or "",
            }

        risk_config = config.get("risk_note", {})
        risk_threshold = risk_config.get("threshold")
        risk_triggered = score is not None and risk_threshold is not None and score >= risk_threshold
        risk_note = {
            "triggered": bool(risk_triggered),
            "level": "high" if risk_triggered else "none",
            "text": risk_config.get("text", "") if risk_triggered else "",
        }

        if risk_triggered:
            state_summary = f"你的结果为{result_level or '当前状态'}，并出现需要优先关注的信号，请先保证安全和稳定支持。"
        elif elevated_labels:
            state_summary = f"你的结果为{result_level or '当前状态'}，主要需要关注{ '、'.join(elevated_labels[:3]) }相关变化。"
        else:
            analysis_name = config.get("analysis_name", "心理状态")
            state_summary = f"你的结果为{result_level or '当前状态'}，目前{analysis_name}整体较平稳，可以继续观察近期变化。"

        return {
            "state_summary": state_summary,
            "dimensions": dimensions,
            "possible_causes": config.get("possible_causes", []),
            "small_actions": config.get("small_actions", []),
            "professional_support": professional_support,
            "emotion_recording": {
                "recommended": True,
                "focus": config.get("recording_focus", ["心情", "睡眠", "触发事件"]),
                "text": config.get("recording_text", "建议接下来持续记录情绪和触发事件，观察状态是否有规律。"),
            },
            "risk_note": risk_note,
        }

    def _attach_ai_analysis(
        self,
        scale_short_name: str,
        request_answers: Dict[str, Any],
        result_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        if scale_short_name == "SDS":
            ai_analysis = self._build_bdi_ai_analysis(
                request_answers=request_answers,
                result_level=result_data.get("result_level"),
                final_score=result_data.get("final_score"),
            )
        else:
            ai_analysis = self._build_configured_mental_health_analysis(
                scale_short_name=scale_short_name,
                request_answers=request_answers,
                result_level=result_data.get("result_level"),
                final_score=result_data.get("final_score"),
            )

        if not ai_analysis:
            return result_data

        result_details = result_data.get("result_details")
        if not isinstance(result_details, dict):
            result_details = {}
        result_details["ai_analysis"] = ai_analysis
        result_data["result_details"] = result_details
        result_data["ai_analysis"] = ai_analysis
        return result_data

    def _calculate_aglt_talent_radar_result(self, request_answers: Dict[str, str], scale_data: Dict) -> Dict:
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        sections = rules.get('sections', {})
        dimension_labels = rules.get('dimensions', {})
        questions = {str(q['order']): q for q in scale_data.get('questions', [])}
        interpretations = scale_data.get('interpretations', {})

        explicit_set = {str(order) for order in sections.get('explicit', [])}
        latent_set = {str(order) for order in sections.get('latent', [])}
        stress_set = {str(order) for order in sections.get('stress', [])}

        all_dimension_ids = list(dimension_labels.keys())
        explicit_scores = {dimension_id: 0 for dimension_id in all_dimension_ids}
        latent_scores = {dimension_id: 0 for dimension_id in all_dimension_ids}
        stress_scores = {dimension_id: 0 for dimension_id in all_dimension_ids}
        total_scores = {dimension_id: 0 for dimension_id in all_dimension_ids}

        for q_order, option_id in request_answers.items():
            question = questions.get(str(q_order))
            if not question:
                continue

            selected_option = next((opt for opt in question.get('options', []) if str(opt.get('id')) == str(option_id)), None)
            if not selected_option:
                continue

            dimension_id = selected_option.get('target_personality_id')
            if dimension_id not in total_scores:
                continue

            total_scores[dimension_id] += 1
            if str(q_order) in explicit_set:
                explicit_scores[dimension_id] += 1
            elif str(q_order) in latent_set:
                latent_scores[dimension_id] += 1
            elif str(q_order) in stress_set:
                stress_scores[dimension_id] += 1

        if not any(total_scores.values()):
            return {"result_level": "无法确定", "result_interpretation": "您的答案无法匹配到有效结果，请重试。"}

        def sort_dimension_scores(score_map: Dict[str, int]) -> List[Tuple[str, int]]:
            return sorted(score_map.items(), key=lambda item: (-item[1], item[0]))

        total_sorted = sort_dimension_scores(total_scores)
        explicit_sorted = sort_dimension_scores(explicit_scores)
        latent_sorted = sort_dimension_scores(latent_scores)
        stress_sorted = sort_dimension_scores(stress_scores)

        primary_id = total_sorted[0][0]
        support_id = total_sorted[1][0] if len(total_sorted) > 1 else primary_id
        latent_id = latent_sorted[0][0] if latent_sorted and latent_sorted[0][1] > 0 else support_id
        stress_id = stress_sorted[0][0] if stress_sorted and stress_sorted[0][1] > 0 else primary_id

        primary_profile = interpretations.get(primary_id, {})
        support_profile = interpretations.get(support_id, {})
        latent_profile = interpretations.get(latent_id, {})
        stress_profile = interpretations.get(stress_id, {})

        total_question_count = sum(total_scores.values()) or 1
        breakdown = []
        for dimension_id, score in total_sorted:
            profile = interpretations.get(dimension_id, {})
            breakdown.append({
                "id": dimension_id,
                "title": profile.get("title", dimension_labels.get(dimension_id, dimension_id)),
                "count": score,
                "ratio": round(score / total_question_count, 3),
                "explicit_score": explicit_scores.get(dimension_id, 0),
                "latent_score": latent_scores.get(dimension_id, 0),
                "stress_score": stress_scores.get(dimension_id, 0)
            })

        primary_total = total_scores.get(primary_id, 0)
        support_total = total_scores.get(support_id, 0)
        latent_total = latent_scores.get(latent_id, 0)
        stress_total = stress_scores.get(stress_id, 0)
        primary_label = primary_profile.get("title", dimension_labels.get(primary_id, primary_id))
        support_label = support_profile.get("title", dimension_labels.get(support_id, support_id))
        latent_label = latent_profile.get("title", dimension_labels.get(latent_id, latent_id))
        stress_label = stress_profile.get("title", dimension_labels.get(stress_id, stress_id))

        gap = primary_total - support_total
        if gap <= 1 and support_id != primary_id:
            radar_title = f"{primary_label} × {support_label}"
            radar_summary = f"你的显性天赋呈现出明显的双核特征：{primary_label}和{support_label}都很活跃。"
        else:
            radar_title = primary_label
            radar_summary = f"你的显性天赋更集中在“{primary_label}”。这是你最常自然启动、也最容易被别人感受到的优势。"

        if latent_total <= 0:
            latent_summary = "你的潜伏潜能暂时没有明显偏向，说明你目前更多是在依靠已经成型的强项做事。"
        elif latent_id == primary_id:
            latent_summary = f"你的潜伏潜能和显性天赋方向一致，说明这项能力不只是你会用，它也正是你心里最想继续放大的部分。"
        else:
            latent_summary = f"你的潜伏潜能更偏向“{latent_label}”。这说明你心里其实很向往这一类能力，只是现实里还没有被充分使用。"

        stress_summary = f"在压力或变化出现时，你更容易本能依赖“{stress_label}”来稳住自己。"

        pair_copy_map = {
            ("creative", "expression"): "你的主线像一台会发光的灵感扩音器。你不只是会想，也很擅长把想法讲出去、变得有感染力。",
            ("creative", "aesthetics"): "你很容易把点子和感觉揉在一起，做出既新鲜又有辨识度的东西。",
            ("creative", "exploration"): "你对新可能特别敏锐，常常不是沿着现成答案走，而是边试边找到自己的路。",
            ("creative", "craft"): "你的创意不太甘心只停在脑内，你更适合把灵感一点点做成可见的作品。",
            ("insight", "execution"): "你兼具判断和推进的能力，既能看懂问题，也能把解决方案真正往前带。",
            ("insight", "creative"): "你不是那种只会分析的人，你很擅长在看清结构之后，继续提出新角度。",
            ("insight", "empathy"): "你既会看逻辑，也会看人。你擅长把复杂问题解释成别人能接受、也愿意合作的样子。",
            ("insight", "expression"): "你容易把深的东西说清楚，这是很稀缺的能力。很多时候，你的洞察会因为表达而变得更有影响。",
            ("execution", "empathy"): "你不仅能把事推进，还会顾到人在过程里的感受，所以你常常是团队里又稳又让人放心的存在。",
            ("execution", "craft"): "你对“做成”这件事很有感觉，适合把计划、流程和实际产出连成一条线。",
            ("execution", "exploration"): "你并不是只会守成。你能一边开新局，一边把局面拉回可执行状态。",
            ("execution", "expression"): "你擅长把方向、节奏和重点说清楚，因此不仅能自己做，也能带着别人一起做。",
            ("empathy", "expression"): "你有一种温柔而有力量的说服感。你不是硬推观点，而是让人愿意听、愿意靠近、愿意一起动起来。",
            ("empathy", "aesthetics"): "你不仅能感受人的情绪，也能感受场域的氛围，所以很适合做有温度的体验设计和陪伴型创造。",
            ("empathy", "insight"): "你对人和问题都不只是停在表面，这让你很适合做深度理解、支持和判断并存的角色。",
            ("empathy", "execution"): "你不是只有感受力，你还会帮事情往前走，这让你的共情很容易转成真正的支持。",
            ("expression", "exploration"): "你像一个自带麦克风的探路者，既敢往外走，也敢把一路上的发现带回来讲给别人听。",
            ("expression", "creative"): "你对想法和表达都有天然兴奋点，适合去做那些需要风格、观点和感染力的事。",
            ("expression", "execution"): "你不仅会说，也会带动行动，所以你的影响力往往不是停在氛围，而是能推动结果。",
            ("expression", "aesthetics"): "你天生对表达的呈现感比较敏锐，很适合把内容、画面和氛围一起做完整。",
            ("exploration", "craft"): "你适合边试边做，在陌生场景里靠行动把方向一点点摸出来。",
            ("exploration", "creative"): "你对新鲜感和新可能都很敏锐，容易在变化中比别人更早看见机会。",
            ("exploration", "insight"): "你不是盲目冲，你会一边试、一边判断，所以很适合去开那些需要脑子和胆子的局。",
            ("exploration", "expression"): "你很适合把见闻、尝试和发现转成故事，让你的探索不仅属于自己，也能感染别人。",
            ("aesthetics", "creative"): "你很容易把“感觉”变成“新东西”，作品里常常同时有审美和想法。",
            ("aesthetics", "empathy"): "你对氛围和人的感受都很敏锐，所以很适合去创造让人觉得舒服、被照顾、被理解的体验。",
            ("aesthetics", "expression"): "你不只是会表达内容，也会表达气质。你的优势在于把东西呈现得有记忆点。",
            ("aesthetics", "craft"): "你不是停在审美判断上，你更容易把“我觉得这样更好”做成一个真正更好的版本。",
            ("craft", "execution"): "你很适合那种一边做、一边推进的任务。你会让抽象计划变成真正能运行的成果。",
            ("craft", "creative"): "你擅长把点子落成原型，所以很多别人停留在想法层面的东西，在你这里更容易长出实体。",
            ("craft", "aesthetics"): "你做出来的东西不只是能用，还常常会带着自己的质感和完成度。",
            ("craft", "insight"): "你不是只靠手感，你也会判断结构和可行性，所以很适合做需要脑和手一起上的工作。"
        }

        latent_copy_map = {
            ("creative", "execution"): "你心里想点亮的，其实是“把灵感变成稳定产出”的那部分能力。",
            ("insight", "expression"): "你潜意识里很想把自己的思考说出去，不只是想明白，还想被更多人听懂。",
            ("execution", "creative"): "你内在并不满足于只是把事做完，你其实也在渴望更大的新鲜感和创造空间。",
            ("empathy", "expression"): "你隐藏着一种想把理解力变成影响力的愿望，也许你并不只想默默支持别人。",
            ("expression", "insight"): "你潜在想长出来的，不只是更会说，而是更有自己的判断和观点深度。",
            ("exploration", "execution"): "你心里那部分还没完全亮起的能力，和“把试出来的路走成一条稳定路径”有关。",
            ("aesthetics", "craft"): "你不只是想有感觉，你其实也很想把那种感觉稳稳做成一个作品。",
            ("craft", "expression"): "你潜伏着一种把作品、过程和经验讲出来的能力，它会让你的成果被更多人看见。"
        }

        def compose_pair_copy(primary_dimension: str, support_dimension: str) -> str:
            if primary_dimension == support_dimension:
                return ""
            return pair_copy_map.get((primary_dimension, support_dimension)) or pair_copy_map.get((support_dimension, primary_dimension)) or ""

        def compose_latent_bridge(primary_dimension: str, latent_dimension: str) -> str:
            if primary_dimension == latent_dimension:
                return "你的潜伏潜能和显性主线同方向，说明你不只是已经擅长它，你也真心想继续放大它。"
            return latent_copy_map.get((primary_dimension, latent_dimension)) or f"如果给自己多一点空间，你很可能会逐渐点亮“{latent_label}”这条能力线。"

        pair_summary = compose_pair_copy(primary_id, support_id)
        latent_bridge = compose_latent_bridge(primary_id, latent_id)

        result_interpretation = " ".join([
            radar_summary,
            primary_profile.get("description", ""),
            pair_summary or (support_profile.get("description", "") if support_id != primary_id and support_total > 0 else "")
        ]).strip()

        result_recommendation = " ".join(filter(None, [
            primary_profile.get("growth_focus", ""),
            latent_profile.get("growth_focus", "") if latent_id != primary_id else "",
            f"最近可以有意识地给“{latent_label}”安排一点练习场景，看看它会不会被进一步点亮。" if latent_total > 0 else ""
        ])).strip()

        return {
            "raw_score": None,
            "final_score": None,
            "result_level": radar_title,
            "result_interpretation": result_interpretation,
            "result_recommendation": result_recommendation,
            "result_details": {
                "primary_id": primary_id,
                "secondary_id": support_id,
                "latent_id": latent_id,
                "stress_id": stress_id,
                "college": "天赋雷达",
                "college_motto": "看见你最常用的力量，也看见那部分还没被完全点亮的自己。",
                "career_teaser": "这次不是职业盲盒，而是一张关于你如何发光的雷达图。",
                "primary_title": primary_label,
                "primary_summary": primary_profile.get("description", ""),
                "primary_tagline": primary_profile.get("tagline", ""),
                "primary_best_scene": primary_profile.get("best_scene", ""),
                "primary_growth_focus": primary_profile.get("growth_focus", ""),
                "secondary_title": support_label,
                "secondary_description": support_profile.get("description", ""),
                "secondary_recommendation": support_profile.get("growth_focus", ""),
                "secondary_tagline": support_profile.get("tagline", ""),
                "latent_title": latent_label,
                "latent_description": latent_profile.get("description", ""),
                "latent_recommendation": latent_profile.get("growth_focus", ""),
                "latent_tagline": latent_profile.get("tagline", ""),
                "stress_title": stress_label,
                "stress_description": stress_summary,
                "stress_recommendation": stress_profile.get("growth_focus", ""),
                "radar_summary": radar_summary,
                "pair_summary": pair_summary,
                "latent_summary": latent_summary,
                "latent_bridge": latent_bridge,
                "stress_summary": stress_summary,
                "tendency_breakdown": breakdown,
                "explicit_scores": explicit_scores,
                "latent_scores": latent_scores,
                "stress_scores": stress_scores,
                "dimension_scores": total_scores,
                "image_url": primary_profile.get("image_url", "")
            }
        }


    def _calculate_categorical_result(self, request_answers: Dict[str, str], scale_data: Dict) -> Dict:
        """【最终完善版】处理分类测试的计分逻辑，支持多种计分模型"""
        
        rules = scale_data.get('scale_info', {}).get('scoring_rules', {})
        scoring_type = rules.get('type')
        interpretations = scale_data.get('interpretations', [])

        if scoring_type == 'talent_radar_dual_axis':
            return self._calculate_aglt_talent_radar_result(request_answers, scale_data)

        if scoring_type == 'soul_drink_3d':
            return self._calculate_soul_drink_result(request_answers, scale_data)

        # ==============================================================================
        # 规则 1: 处理 ECR 问卷的 "subscale_average_2d" (二维度平均分)
        # ==============================================================================
        if scoring_type == 'subscale_average_2d':
            # ... (这部分代码保持不变) ...
            subscale_scores = {"焦虑": [], "回避": []}
            questions_map = {str(q['order']): q for q in scale_data.get('questions', [])}
            choices_map = {str(c.get('id')): c.get('score', 0) for c in scale_data.get('choices', [])}

            for q_order_str, option_id in request_answers.items():
                question = questions_map.get(q_order_str)
                if not question: continue
                
                score = choices_map.get(option_id)
                if score is None: continue

                subscale = question.get('subscale')
                if question.get('reverse_scored'):
                    score = 8 - score
                if subscale in subscale_scores:
                    subscale_scores[subscale].append(score)

            avg_anxiety = sum(subscale_scores["焦虑"]) / len(subscale_scores["焦虑"]) if subscale_scores["焦虑"] else 0
            avg_avoidance = sum(subscale_scores["回避"]) / len(subscale_scores["回避"]) if subscale_scores["回避"] else 0
            
            anxiety_level = "高焦虑" if avg_anxiety > 4 else "低焦虑"
            avoidance_level = "高回避" if avg_avoidance > 4 else "低回避"
            condition_str = f"{anxiety_level} & {avoidance_level}"
            
            final_result_model = next((m for m in rules.get('model', []) if m['condition'] == condition_str), None)
            
            if final_result_model:
                result_level = final_result_model.get('level')
                interpretation_data = next((i for i in interpretations if i.get('level') == result_level), {})
                return {
                    "raw_score": None, "final_score": None, "result_level": result_level,
                    "result_interpretation": interpretation_data.get('interpretation', ''),
                    "result_recommendation": interpretation_data.get('recommendation', ''),
                    "result_details": { "anxiety_score": round(avg_anxiety, 2), "avoidance_score": round(avg_avoidance, 2), "condition": condition_str }
                }
            return {"result_level": "无法确定类型", "result_interpretation": "计算结果无法匹配到任何预设类型。"}

        # ==============================================================================
        # 规则 2: 处理 AAS 问卷的 "dominant_subscale" (优势维度总分) - 【已修正】
        # ==============================================================================
        elif scoring_type == 'dominant_subscale':
            # ✅ 关键修正：先创建一个从选项ID到分数的映射字典
            choices_map = {str(c.get('id')): c.get('score', 0) for c in scale_data.get('choices', [])}
            if not choices_map:
                return {"result_level": "配置错误", "result_interpretation": "问卷选项(choices)未定义或缺少ID。"}

            subscale_names = rules.get('subscales', [])
            subscale_scores = {name: 0 for name in subscale_names}
            questions_map = {str(q['order']): q for q in scale_data.get('questions', [])}
            
            # 这里的 `option_id` 现在被正确地理解为选项ID，而不是分数
            for q_order_str, option_id in request_answers.items():
                question = questions_map.get(q_order_str)
                if not question: continue

                # ✅ 关键修正：通过选项ID从映射中查找正确的分数
                score = choices_map.get(option_id)
                if score is None: 
                    continue # 如果ID无效，则跳过

                subscale = question.get('subscale')
                if subscale in subscale_scores:
                    subscale_scores[subscale] += score
            
            if not any(s > 0 for s in subscale_scores.values()):
                return {"result_level": "无法计算", "result_interpretation": "所有维度得分均为0，请检查提交数据。"}
            
            result_level = max(subscale_scores, key=subscale_scores.get)
            interpretation_data = next((i for i in interpretations if i.get('level') == result_level), {})
            
            return {
                "raw_score": None, "final_score": None, "result_level": result_level,
                "result_interpretation": interpretation_data.get('interpretation', ''),
                "result_recommendation": interpretation_data.get('recommendation', ''),
                "result_details": subscale_scores
            }
            
        # ==============================================================================
        # 规则 3 (默认): 处理 MBTI 和其他简单“投票计数”型问卷
        # ==============================================================================
        else:
            # (这部分代码保持不变)
            questions = scale_data.get('questions', [])
            if questions:
                first_question = questions[0]
                first_option = first_question.get('options', [{}])[0]
                first_target_id = first_option.get('target_personality_id', '')
                if first_target_id.startswith('mbti:'):
                    return self._calculate_mbti_dimensional_result(request_answers, scale_data)

            questions_dict = {str(q['order']): q for q in questions}
            interpretations_obj = scale_data.get('interpretations', {})
            personality_counts = {}
            
            for q_order, option_id in request_answers.items():
                question = questions_dict.get(q_order)
                if not question or not question.get('options'): continue
                
                selected_option = next((opt for opt in question.get('options', []) if opt.get('id') == option_id), None)
                
                if selected_option:
                    target_id = selected_option.get('target_personality_id')
                    if target_id:
                        personality_counts[target_id] = personality_counts.get(target_id, 0) + 1
            
            if not personality_counts:
                return {"result_level": "无法确定", "result_interpretation": "您的答案无法匹配到任何结果，请重试。"}

            sorted_personalities = sorted(
                personality_counts.items(),
                key=lambda item: (-item[1], item[0])
            )
            final_personality_id = sorted_personalities[0][0]
            final_result = interpretations_obj.get(final_personality_id, {})
            secondary_personality_id = sorted_personalities[1][0] if len(sorted_personalities) > 1 else None
            secondary_result = interpretations_obj.get(secondary_personality_id, {}) if secondary_personality_id else {}
            total_votes = sum(personality_counts.values()) or 1
            tendency_breakdown = [
                {
                    "id": personality_id,
                    "title": interpretations_obj.get(personality_id, {}).get("title", personality_id),
                    "count": count,
                    "ratio": round(count / total_votes, 3)
                }
                for personality_id, count in sorted_personalities[:4]
            ]
            
            return {
                "raw_score": None, "final_score": None,
                "result_level": final_result.get('title'),
                "result_interpretation": final_result.get('description'),
                "result_recommendation": final_result.get('recommendation'),
                "result_details": {
                    "college": final_result.get('college'),
                    "college_motto": final_result.get('college_motto'),
                    "career_teaser": final_result.get('career_teaser'),
                    "primary_career": final_result.get('primary_career'),
                    "recommended_careers": final_result.get('recommended_careers', []),
                    "primary_id": final_personality_id,
                    "secondary_id": secondary_personality_id,
                    "secondary_title": secondary_result.get('title'),
                    "secondary_description": secondary_result.get('description'),
                    "secondary_recommendation": secondary_result.get('recommendation'),
                    "in_relationships": final_result.get('in_relationships'),
                    "under_stress": final_result.get('under_stress'),
                    "facing_change": final_result.get('facing_change'),
                    "secondary_in_relationships": secondary_result.get('in_relationships'),
                    "secondary_under_stress": secondary_result.get('under_stress'),
                    "secondary_facing_change": secondary_result.get('facing_change'),
                    "fortune_keyword": final_result.get('fortune_keyword'),
                    "fortune_window": final_result.get('fortune_window'),
                    "lucky_color": final_result.get('lucky_color'),
                    "lucky_action": final_result.get('lucky_action'),
                    "lucky_phrase": final_result.get('lucky_phrase'),
                    "emotional_anchor": final_result.get('emotional_anchor'),
                    "tendency_breakdown": tendency_breakdown,
                    "image_url": final_result.get('image_url')
                }
            }
                
    def _calculate_soul_drink_result(self, request_answers: Dict[str, str], scale_data: Dict) -> Dict:
        """处理灵魂饮料测试的 S/N、T/F、J/P 三维组合计分。"""
        questions = {str(q.get('order')): q for q in scale_data.get('questions', [])}
        interpretations = scale_data.get('interpretations', {})
        dim_counts = {'S': 0, 'N': 0, 'T': 0, 'F': 0, 'J': 0, 'P': 0}

        for q_order, option_id in request_answers.items():
            question = questions.get(str(q_order))
            if not question:
                continue

            selected_option = next(
                (opt for opt in question.get('options', []) if str(opt.get('id')) == str(option_id)),
                None,
            )
            if not selected_option:
                continue

            score_map = selected_option.get('score', {})
            if not isinstance(score_map, dict):
                continue

            for dimension, value in score_map.items():
                if dimension in dim_counts:
                    try:
                        dim_counts[dimension] += int(value)
                    except (TypeError, ValueError):
                        continue

        result_type = ''
        result_type += 'S' if dim_counts['S'] > dim_counts['N'] else 'N'
        result_type += 'T' if dim_counts['T'] > dim_counts['F'] else 'F'
        result_type += 'J' if dim_counts['J'] > dim_counts['P'] else 'P'

        final_result = interpretations.get(result_type, {})
        dimension_pairs = {
            'SN': {'S': dim_counts['S'], 'N': dim_counts['N'], 'winner': result_type[0]},
            'TF': {'T': dim_counts['T'], 'F': dim_counts['F'], 'winner': result_type[1]},
            'JP': {'J': dim_counts['J'], 'P': dim_counts['P'], 'winner': result_type[2]},
        }
        result_card_base_url = (
            'https://assets.feelyourself.cn/miniprogram/assets/v1/'
            'pkgAssessment/images/drink-ti/result-cards'
        )
        result_card_map = {
            'STJ': f'{result_card_base_url}/stj-unsweetened-oolong-tea.jpg',
            'STP': f'{result_card_base_url}/stp-lime-electrolyte-water.jpg',
            'SFJ': f'{result_card_base_url}/sfj-hot-milk-tea.jpg',
            'SFP': f'{result_card_base_url}/sfp-peach-sparkling-water.jpg',
            'NTJ': f'{result_card_base_url}/ntj-cold-brew-black-coffee.jpg',
            'NTP': f'{result_card_base_url}/ntp-special-cocktail.jpg',
            'NFJ': f'{result_card_base_url}/nfj-honey-grapefruit-tea.jpg',
            'NFP': f'{result_card_base_url}/nfp-colorful-fruit-tea.jpg',
        }

        return {
            "raw_score": None,
            "final_score": None,
            "result_level": final_result.get('title', result_type),
            "result_interpretation": final_result.get('description', ''),
            "result_recommendation": '',
            "result_details": {
                "title": final_result.get('title', result_type),
                "type_code": result_type,
                "trait": final_result.get('trait', ''),
                "college": final_result.get('trait', ''),
                "college_motto": final_result.get('college_motto', ''),
                "career_teaser": final_result.get('career_teaser', ''),
                "profile_title": final_result.get('profile_title', ''),
                "in_relationships": final_result.get('in_relationships', ''),
                "under_stress": final_result.get('under_stress', ''),
                "facing_change": final_result.get('facing_change', ''),
                "dimension_scores": dim_counts,
                "dimension_pairs": dimension_pairs,
                "image_url": final_result.get('image_url', ''),
                "result_card_url": result_card_map.get(result_type, ''),
            }
        }

    def _calculate_mbti_dimensional_result(self, request_answers: Dict[str, str], scale_data: Dict) -> Dict:
        """【新增】专门处理 MBTI 维度计分的私有方法"""
        questions = {str(q['order']): q for q in scale_data.get('questions', [])}
        interpretations = scale_data.get('interpretations', {})
        print("使用专属函数了")
        # 1. 初始化维度计分板
        dim_counts = { 'I': 0, 'E': 0, 'S': 0, 'N': 0, 'T': 0, 'F': 0, 'J': 0, 'P': 0 }

        # 2. 遍历答案，解析复合ID并计分
        for q_order, option_id in request_answers.items():
            question = questions.get(q_order)
            if not question: continue
            
            option = next((opt for opt in question.get('options', []) if opt['id'] == option_id), None)
            if not option: continue
                
            target_id = option.get('target_personality_id')
            if target_id and target_id.startswith('mbti:'):
                try:
                    # 解析 "mbti:IE:I"
                    _, dimension, value = target_id.split(':')
                    if value in dim_counts:
                        dim_counts[value] += 1
                except ValueError:
                    # 如果格式不正确，则跳过
                    continue

        # 3. 计算最终人格类型
        result_type = ""
        result_type += 'I' if dim_counts['I'] >= dim_counts['E'] else 'E' # 等于时默认 I
        result_type += 'S' if dim_counts['S'] >= dim_counts['N'] else 'N' # 等于时默认 S
        result_type += 'T' if dim_counts['T'] >= dim_counts['F'] else 'F' # 等于时默认 T
        result_type += 'J' if dim_counts['J'] >= dim_counts['P'] else 'P' # 等于时默认 J
        
        # 4. 查找并返回结果
        final_result = interpretations.get(result_type, {})
        
        return {
            "raw_score": None,
            "final_score": None,
            "result_level": final_result.get('title'), # 复用 title 字段
            "result_interpretation": final_result.get('description'),
            "result_recommendation": final_result.get('recommendation'),
            "result_details": {
                "college": final_result.get('college'),                 # ✅ 添加 college
                "college_motto": final_result.get('college_motto'),     # ✅ 添加 college_motto
                "title": final_result.get('title'),
                "type_code": result_type,
                "dimension_scores": dim_counts,
                "image_url": final_result.get('image_url')
            }
        }
    

    def create_user_assessment(self, user_id: str, request_data: SubmitAnswersRequest) -> Optional[UserAssessment]:
        """核心方法：根据量表类型进行评分，并创建测评记录"""
        scale = self.get_scale_by_id(request_data.scale_id)
        if not scale:
            return None
            
        scale_data = json.loads(scale.json_data)
        
        result_data = {}
        if scale.assessment_type == 'scoring':
            result_data = self._calculate_scoring_result(request_data.answers, scale_data)
        elif scale.assessment_type == 'categorical':
            result_data = self._calculate_categorical_result(request_data.answers, scale_data)
        else:
            raise ValueError(f"Unsupported assessment type: {scale.assessment_type}")

        result_data = self._attach_ai_analysis(scale.short_name, request_data.answers, result_data)
        
        user_assessment = UserAssessment.create(
            user=user_id,
            scale=scale.id,
            answers=json.dumps(request_data.answers, ensure_ascii=False),
            raw_score=result_data.get('raw_score'),
            final_score=result_data.get('final_score'),
            result_level=result_data.get('result_level'),
            result_interpretation=result_data.get('result_interpretation'),
            result_recommendation=result_data.get('result_recommendation'),
            result_details=json.dumps(result_data.get('result_details'), ensure_ascii=False) if result_data.get('result_details') else None
        )
        return user_assessment

    def get_assessments_by_user(self, user_id: str) -> List[UserAssessment]:
        """获取一个用户的所有测评历史记录"""
        records = list(UserAssessment.select().where(UserAssessment.user == user_id).order_by(UserAssessment.completed_at.desc()))
        for record in records:
            self.ensure_scoring_result_for_record(record)
        return records

    def get_assessment_by_id(self, record_id: str) -> Optional[UserAssessment]:
        """根据记录ID获取单条测评结果"""
        record = UserAssessment.get_or_none(UserAssessment.id == record_id)
        self.ensure_scoring_result_for_record(record)
        return record

    def ensure_ai_analysis_for_record(self, record: UserAssessment) -> Optional[Dict[str, Any]]:
        """为历史心理健康记录补齐规则化分析，并返回分析对象。"""
        if not record or not record.scale:
            return None

        supports_analysis = record.scale.short_name == "SDS" or bool(
            self._get_mental_health_analysis_config(record.scale.short_name)
        )
        if not supports_analysis:
            return None

        try:
            answers = json.loads(record.answers) if record.answers else {}
        except json.JSONDecodeError:
            answers = {}

        try:
            result_details = json.loads(record.result_details) if record.result_details else {}
        except json.JSONDecodeError:
            result_details = {}

        if not isinstance(result_details, dict):
            result_details = {}

        existing_analysis = result_details.get("ai_analysis")
        if isinstance(existing_analysis, dict):
            return existing_analysis

        if record.scale.short_name == "SDS":
            ai_analysis = self._build_bdi_ai_analysis(
                request_answers=answers,
                result_level=record.result_level,
                final_score=record.final_score,
            )
        else:
            ai_analysis = self._build_configured_mental_health_analysis(
                scale_short_name=record.scale.short_name,
                request_answers=answers,
                result_level=record.result_level,
                final_score=record.final_score,
            )

        if not ai_analysis:
            return None

        result_details["ai_analysis"] = ai_analysis
        record.result_details = json.dumps(result_details, ensure_ascii=False)
        record.save()
        return ai_analysis

    def delete_user_assessment(self, user_id: str, record_id: str) -> bool:
        """删除一条属于特定用户的测评记录"""
        query = UserAssessment.delete().where(
            (UserAssessment.id == record_id) & (UserAssessment.user == user_id)
        )
        deleted_rows = query.execute()
        return deleted_rows > 0

# --- 实例化数据表访问对象 ---
assessment_tables = AssessmentTables(assessment_db)
