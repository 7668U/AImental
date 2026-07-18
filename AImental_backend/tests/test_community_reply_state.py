import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv
from fastapi import HTTPException


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=False)

from router import ai_community


class CommunityReplyStateTestCase(unittest.TestCase):
    def setUp(self):
        ai_community.active_reply_sessions.clear()

    def tearDown(self):
        ai_community.active_reply_sessions.clear()

    def test_reply_progress_is_scoped_to_user_and_character(self):
        active_key = ai_community._reply_lock_key("user-1", "character-1")
        ai_community.active_reply_sessions.add(active_key)

        self.assertTrue(ai_community._reply_in_progress("user-1", "character-1"))
        self.assertFalse(ai_community._reply_in_progress("user-2", "character-1"))
        self.assertFalse(ai_community._reply_in_progress("user-1", "character-2"))

    def test_reply_status_endpoint_reports_current_session_state(self):
        with patch.object(
            ai_community.ai_character_table,
            "get_character_by_id",
            return_value=object(),
        ):
            inactive = ai_community.get_chat_reply_status("character-1", "user-1")
            self.assertFalse(inactive.reply_in_progress)

            ai_community.active_reply_sessions.add(
                ai_community._reply_lock_key("user-1", "character-1")
            )
            active = ai_community.get_chat_reply_status("character-1", "user-1")
            self.assertTrue(active.reply_in_progress)

    def test_reply_status_endpoint_rejects_unknown_character(self):
        with patch.object(
            ai_community.ai_character_table,
            "get_character_by_id",
            return_value=None,
        ):
            with self.assertRaises(HTTPException) as context:
                ai_community.get_chat_reply_status("missing", "user-1")

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
