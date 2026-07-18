import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=False)

import generate_community_response as community_response


class FakeCompletions:
    def __init__(self, contents):
        self.contents = list(contents)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.contents.pop(0)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                )
            ]
        )


class FakeClient:
    def __init__(self, contents):
        self.completions = FakeCompletions(contents)
        self.chat = SimpleNamespace(completions=self.completions)


def valid_response(message="结构已经修复"):
    return json.dumps(
        {
            "messages": [message],
            "control": {
                "next_state": "CONTINUE_CHAT",
                "next_delay_minutes": 0,
            },
        },
        ensure_ascii=False,
    )


class CommunityResponseRetryTestCase(unittest.TestCase):
    def generate_with(self, contents, conversation_history=None, character_name="测试角色"):
        fake_client = FakeClient(contents)
        with (
            patch.object(community_response, "IS_MOCK_API", False),
            patch.object(community_response, "_no_retry_client", return_value=fake_client),
        ):
            result = community_response.generate_ai_response(
                character_profile={
                    "identity_core": {"name": character_name},
                    "personality_traits": {},
                },
                current_ai_status={
                    "status_title": "在线",
                    "status_description": "正在安静地待着。",
                    "focus_level": "LOW",
                },
                conversation_history=conversation_history or [
                    {"role": "user", "content": "之前聊过什么"},
                    {"role": "ai", "content": "聊过一点日常"},
                    {"role": "user", "content": "那继续吧"},
                ],
                full_day_schedule=[],
                memory_context={},
            )
        return result, fake_client.completions.calls

    def test_empty_object_triggers_schema_correction_retry(self):
        result, calls = self.generate_with(["{}", valid_response()])

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["temperature"], 0.65)
        self.assertEqual(calls[1]["temperature"], 0.2)
        self.assertIn("不要返回空对象", calls[1]["messages"][-1]["content"])

    def test_malformed_json_triggers_schema_correction_retry(self):
        result, calls = self.generate_with(["not-json", valid_response()])

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)

    def test_second_invalid_response_returns_none_after_one_retry(self):
        result, calls = self.generate_with(["{}", "{}"])

        self.assertIsNone(result)
        self.assertEqual(len(calls), 2)

    def test_valid_initial_response_does_not_retry(self):
        result, calls = self.generate_with([valid_response("第一次就成功")])

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 1)

    def test_conversation_state_detects_intro_name_question_and_user_name(self):
        state = community_response._build_conversation_state(
            [
                {"role": "ai", "content": "嗨，我是凌曜，平时做街拍摄影。"},
                {"role": "user", "content": "你好"},
                {"role": "ai", "content": "怎么称呼你？"},
                {"role": "user", "content": "你好 我是杨超"},
            ],
            "凌曜",
        )

        self.assertTrue(state["character_already_introduced"])
        self.assertTrue(state["name_question_already_asked"])
        self.assertTrue(state["user_name_already_provided"])
        self.assertEqual(state["user_name_candidate"], "杨超")

    def test_name_extraction_ignores_common_status_and_job_phrases(self):
        self.assertEqual(community_response._extract_name_from_user_text("我是程序员"), "")
        self.assertEqual(community_response._extract_name_from_user_text("我是一个学生"), "")
        self.assertEqual(community_response._extract_name_from_user_text("I am tired"), "")

    def test_direct_user_name_address_detection(self):
        self.assertTrue(
            community_response._uses_user_name_as_direct_address(
                ["杨超，你也太厉害了吧！"],
                "杨超",
            )
        )
        self.assertTrue(
            community_response._uses_user_name_as_direct_address(
                ["哇塞！杨超你也太厉害了吧！"],
                "杨超",
            )
        )
        self.assertFalse(
            community_response._uses_user_name_as_direct_address(
                ["哇塞！你也太厉害了吧！"],
                "杨超",
            )
        )

    def test_reply_style_allows_natural_one_to_three_message_rhythm(self):
        boundary = {
            "affinity_score_for_boundary_only": 0,
            "treat_as_new_acquaintance": True,
            "conversation_state": {},
        }
        short_policy = community_response._build_reply_style_policy(
            [{"role": "user", "content": "刚吃完饭"}],
            boundary,
        )
        medium_policy = community_response._build_reply_style_policy(
            [{"role": "user", "content": "今天路上看到一家很有意思的小书店，里面摆了好多旧书"}],
            boundary,
        )
        rich_policy = community_response._build_reply_style_policy(
            [{
                "role": "user",
                "content": "今天发生了好多事，我先是被老师批评，后来又和朋友闹了点矛盾，现在心里特别难受。我是不是哪里做错了？接下来该怎么办？",
            }],
            boundary,
        )

        self.assertEqual(short_policy["target_message_count"], 1)
        self.assertEqual(short_policy["max_message_count"], 2)
        self.assertEqual(medium_policy["target_message_count"], 2)
        self.assertEqual(medium_policy["max_message_count"], 2)
        self.assertEqual(rich_policy["target_message_count"], 2)
        self.assertEqual(rich_policy["max_message_count"], 3)

    def test_conversation_state_blocks_recent_repeated_opening_tic(self):
        state = community_response._build_conversation_state(
            [
                {"role": "ai", "content": "嗯，你好呀，我是刘书沁。"},
                {"role": "user", "content": "你好"},
                {"role": "ai", "content": "嗯…今天想聊什么？"},
                {"role": "user", "content": "随便聊聊"},
            ],
            "刘书沁",
        )

        self.assertEqual(state["recent_ai_opening_tics"], ["嗯", "嗯"])
        self.assertEqual(state["avoid_opening_tics_next_reply"], ["嗯"])

    def test_repeated_opening_tic_triggers_semantic_retry(self):
        history = [
            {"role": "ai", "content": "嗯，你好呀，我是刘书沁。"},
            {"role": "user", "content": "你好"},
            {"role": "ai", "content": "嗯…今天想聊什么？"},
            {"role": "user", "content": "你怎么总是嗯开头"},
        ]
        result, calls = self.generate_with(
            [
                valid_response("嗯…被你发现了，我有时会先想一下。"),
                valid_response("被你发现了。我有时说话前会先在脑子里过一遍。"),
            ],
            conversation_history=history,
            character_name="刘书沁",
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)
        self.assertFalse(result.messages[0].startswith("嗯"))
        self.assertIn("avoid_opening_tics_next_reply", calls[1]["messages"][-1]["content"])

    def test_repeated_opening_tic_is_stripped_if_retry_still_repeats_it(self):
        history = [
            {"role": "ai", "content": "嗯，你好呀，我是刘书沁。"},
            {"role": "user", "content": "你好"},
            {"role": "ai", "content": "嗯…今天想聊什么？"},
            {"role": "user", "content": "换个开头试试"},
        ]
        result, calls = self.generate_with(
            [
                valid_response("嗯…好，那我换一个开头。"),
                valid_response("嗯…这次我会注意。"),
            ],
            conversation_history=history,
            character_name="刘书沁",
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result.messages[0], "这次我会注意。")

    def test_repeated_name_question_triggers_semantic_retry(self):
        history = [
            {"role": "ai", "content": "嗨，我是凌曜，平时做街拍摄影。"},
            {"role": "user", "content": "你好"},
            {"role": "ai", "content": "嘿，你好啊！怎么称呼你？"},
            {"role": "user", "content": "你好 我是杨超"},
        ]
        result, calls = self.generate_with(
            [
                valid_response("杨超，好名字！我该怎么称呼你？"),
                valid_response("杨超，记住了。你平时也喜欢拍照吗？"),
            ],
            conversation_history=history,
            character_name="凌曜",
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("怎么称呼", result.messages[0])
        self.assertIn("用户已经提供姓名", calls[1]["messages"][-1]["content"])

    def test_repeated_name_question_uses_local_fallback_if_retry_still_bad(self):
        history = [
            {"role": "ai", "content": "嗨，我是凌曜，平时做街拍摄影。"},
            {"role": "user", "content": "你好"},
            {"role": "ai", "content": "怎么称呼你？"},
            {"role": "user", "content": "你好 我是杨超"},
        ]
        result, calls = self.generate_with(
            [
                valid_response("杨超，好名字！我该怎么称呼你？"),
                valid_response("那我还是该怎么称呼你？"),
            ],
            conversation_history=history,
            character_name="凌曜",
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("杨超", result.messages[0])
        self.assertNotIn("称呼", result.messages[0])

    def test_direct_user_name_address_triggers_semantic_retry(self):
        history = [
            {"role": "ai", "content": "哈喽！我是夏阳。"},
            {"role": "user", "content": "你好 夏阳"},
            {"role": "ai", "content": "你呢，怎么称呼？"},
            {"role": "user", "content": "我是杨超"},
            {"role": "ai", "content": "这名字挺好记的！"},
            {"role": "user", "content": "我在高能所读博士呢，你呢"},
        ]
        result, calls = self.generate_with(
            [
                valid_response("哇塞！杨超你也太厉害了吧！我还在读本科呢。"),
                valid_response("哇塞！你也太厉害了吧！我还在读本科呢。"),
            ],
            conversation_history=history,
            character_name="夏阳",
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("杨超", result.messages[0])
        self.assertIn("一对一聊天直接说“你”", calls[1]["messages"][-1]["content"])

    def test_direct_user_name_address_is_stripped_if_retry_still_repeats_it(self):
        history = [
            {"role": "ai", "content": "哈喽！我是夏阳。"},
            {"role": "user", "content": "我是杨超"},
            {"role": "ai", "content": "记住啦。"},
            {"role": "user", "content": "我在高能所读博士呢"},
        ]
        result, calls = self.generate_with(
            [
                valid_response("杨超，你真的很厉害！"),
                valid_response("哇塞！杨超你真的很厉害！"),
            ],
            conversation_history=history,
            character_name="夏阳",
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result.messages[0], "哇塞！你真的很厉害！")

    def test_user_name_is_allowed_when_user_explicitly_asks_for_it(self):
        history = [
            {"role": "ai", "content": "哈喽！我是夏阳。"},
            {"role": "user", "content": "我是杨超"},
            {"role": "ai", "content": "记住啦。"},
            {"role": "user", "content": "你还记得我叫什么吗"},
        ]
        result, calls = self.generate_with(
            [valid_response("杨超，我当然记得。")],
            conversation_history=history,
            character_name="夏阳",
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 1)
        self.assertIn("杨超", result.messages[0])

    def test_repeated_character_introduction_triggers_semantic_retry(self):
        history = [
            {"role": "ai", "content": "嗨，我是凌曜，平时做街拍摄影。"},
            {"role": "user", "content": "你好"},
            {"role": "ai", "content": "今天想聊点什么？"},
            {"role": "user", "content": "随便聊聊"},
        ]
        result, calls = self.generate_with(
            [
                valid_response("我是凌曜，平时做街拍摄影。你呢？"),
                valid_response("好啊，那就随便聊聊。你最近有拍到喜欢的照片吗？"),
            ],
            conversation_history=history,
            character_name="凌曜",
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("我是凌曜", result.messages[0])


if __name__ == "__main__":
    unittest.main()
