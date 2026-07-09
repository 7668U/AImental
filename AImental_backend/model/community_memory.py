import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import pytz
from peewee import (
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
)

from db import chat_db
from generate_community_memory import (
    build_default_profile_card,
    generate_history_summary_card,
    generate_user_profile_memory_card,
    merge_history_summary_cards,
)
from logger_config import logger
from .ai_character import AICharacter
from .chat_community import community_chat_table


BEIJING_TZ = pytz.timezone("Asia/Shanghai")
PROFILE_UPDATE_INTERVAL = 30
SUMMARY_BLOCK_SIZE = 100
MAX_SUMMARY_CARDS = 5


class CharacterUserMemory(Model):
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user_id = CharField(index=True)
    character = ForeignKeyField(AICharacter, field="id", backref="user_memories", on_delete="CASCADE")
    profile_card_json = TextField(default=lambda: json.dumps(build_default_profile_card(), ensure_ascii=False))
    last_profile_update_message_count = IntegerField(default=0)
    last_summary_message_count = IntegerField(default=0)
    created_at = DateTimeField(default=lambda: datetime.now(BEIJING_TZ))
    updated_at = DateTimeField(default=lambda: datetime.now(BEIJING_TZ))

    class Meta:
        database = chat_db
        table_name = "community_user_memory"
        indexes = ((("user_id", "character"), True),)


class CommunityHistorySummary(Model):
    id = CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    user_id = CharField(index=True)
    character = ForeignKeyField(AICharacter, field="id", backref="history_summaries", on_delete="CASCADE")
    start_message_index = IntegerField()
    end_message_index = IntegerField()
    level = IntegerField(default=1)
    summary_card_json = TextField()
    created_at = DateTimeField(default=lambda: datetime.now(BEIJING_TZ))
    updated_at = DateTimeField(default=lambda: datetime.now(BEIJING_TZ))

    class Meta:
        database = chat_db
        table_name = "community_history_summaries"
        indexes = ((("user_id", "character", "start_message_index"), False),)


class CommunityMemoryTable:
    def __init__(self, db_connection):
        self.db = db_connection
        self.db.create_tables([CharacterUserMemory, CommunityHistorySummary])

    def get_or_create_memory(self, user_id: str, character_id: str) -> CharacterUserMemory:
        memory, _ = CharacterUserMemory.get_or_create(
            user_id=user_id,
            character=character_id,
            defaults={"profile_card_json": json.dumps(build_default_profile_card(), ensure_ascii=False)},
        )
        return memory

    def _load_json(self, raw: str, fallback: Any) -> Any:
        try:
            return json.loads(raw) if raw else fallback
        except json.JSONDecodeError:
            return fallback

    def get_profile_card(self, user_id: str, character_id: str) -> Dict[str, Any]:
        memory = self.get_or_create_memory(user_id, character_id)
        return self._load_json(memory.profile_card_json, build_default_profile_card())

    def get_summary_cards(self, user_id: str, character_id: str) -> List[Dict[str, Any]]:
        summaries = (
            CommunityHistorySummary.select()
            .where(
                (CommunityHistorySummary.user_id == user_id)
                & (CommunityHistorySummary.character == character_id)
            )
            .order_by(CommunityHistorySummary.start_message_index.asc(), CommunityHistorySummary.created_at.asc())
        )
        cards = []
        for summary in summaries:
            card = self._load_json(summary.summary_card_json, {})
            if card:
                card["_range"] = [summary.start_message_index + 1, summary.end_message_index]
                card["_level"] = summary.level
                cards.append(card)
        return cards

    def get_prompt_context(self, user_id: str, character_id: str) -> Dict[str, Any]:
        return {
            "user_profile_memory": self.get_profile_card(user_id, character_id),
            "history_summaries": self.get_summary_cards(user_id, character_id),
        }

    def queue_memory_update_if_needed(self, user_id: str, character_id: str, ai_task_table) -> bool:
        history = community_chat_table.get_conversation_history(user_id, character_id, limit=100000)
        message_count = len(history or [])
        memory = self.get_or_create_memory(user_id, character_id)

        needs_profile = message_count - memory.last_profile_update_message_count >= PROFILE_UPDATE_INTERVAL
        needs_summary = message_count - memory.last_summary_message_count >= SUMMARY_BLOCK_SIZE
        if not (needs_profile or needs_summary):
            return False

        task = ai_task_table.create_task_if_needed(
            user_id=user_id,
            character_id=character_id,
            task_type="memory_update",
            execute_at=datetime.now(BEIJING_TZ) + timedelta(seconds=2),
        )
        return task is not None

    def _save_profile_card(self, memory: CharacterUserMemory, card: Dict[str, Any], message_count: int):
        memory.profile_card_json = json.dumps(card, ensure_ascii=False)
        memory.last_profile_update_message_count = message_count
        memory.updated_at = datetime.now(BEIJING_TZ)
        memory.save()

    def _create_summary_card(
        self,
        user_id: str,
        character_id: str,
        start_index: int,
        end_index: int,
        card: Dict[str, Any],
        level: int = 1,
    ) -> CommunityHistorySummary:
        return CommunityHistorySummary.create(
            user_id=user_id,
            character=character_id,
            start_message_index=start_index,
            end_message_index=end_index,
            level=level,
            summary_card_json=json.dumps(card, ensure_ascii=False),
        )

    def _summary_rows(self, user_id: str, character_id: str) -> List[CommunityHistorySummary]:
        return list(
            CommunityHistorySummary.select()
            .where(
                (CommunityHistorySummary.user_id == user_id)
                & (CommunityHistorySummary.character == character_id)
            )
            .order_by(CommunityHistorySummary.start_message_index.asc(), CommunityHistorySummary.created_at.asc())
        )

    def _compress_oldest_summaries_if_needed(self, user_id: str, character_id: str, character_profile: Dict[str, Any]):
        rows = self._summary_rows(user_id, character_id)
        while len(rows) > MAX_SUMMARY_CARDS:
            first, second = rows[0], rows[1]
            first_card = self._load_json(first.summary_card_json, {})
            second_card = self._load_json(second.summary_card_json, {})
            merged_card = merge_history_summary_cards(
                character_profile=character_profile,
                first_summary=first_card,
                second_summary=second_card,
            )
            merged_start = min(first.start_message_index, second.start_message_index)
            merged_end = max(first.end_message_index, second.end_message_index)
            merged_level = max(first.level, second.level) + 1

            first.delete_instance()
            second.delete_instance()
            self._create_summary_card(
                user_id=user_id,
                character_id=character_id,
                start_index=merged_start,
                end_index=merged_end,
                card=merged_card,
                level=merged_level,
            )
            rows = self._summary_rows(user_id, character_id)

    def update_memory_for_conversation(
        self,
        *,
        user_id: str,
        character_id: str,
        character_profile: Dict[str, Any],
    ) -> Tuple[bool, bool]:
        memory = self.get_or_create_memory(user_id, character_id)
        all_messages = community_chat_table.get_conversation_history(user_id, character_id, limit=100000) or []
        message_count = len(all_messages)
        profile_updated = False
        summaries_updated = False

        if message_count - memory.last_summary_message_count >= SUMMARY_BLOCK_SIZE:
            while message_count - memory.last_summary_message_count >= SUMMARY_BLOCK_SIZE:
                start_index = memory.last_summary_message_count
                end_index = start_index + SUMMARY_BLOCK_SIZE
                block = all_messages[start_index:end_index]
                if not block:
                    break

                card = generate_history_summary_card(
                    character_profile=character_profile,
                    messages=block,
                    start_index=start_index,
                    end_index=end_index,
                )
                self._create_summary_card(user_id, character_id, start_index, end_index, card, level=1)
                memory.last_summary_message_count = end_index
                memory.updated_at = datetime.now(BEIJING_TZ)
                memory.save()
                summaries_updated = True

            self._compress_oldest_summaries_if_needed(user_id, character_id, character_profile)

        if message_count - memory.last_profile_update_message_count >= PROFILE_UPDATE_INTERVAL:
            existing_profile = self._load_json(memory.profile_card_json, build_default_profile_card())
            recent_messages = all_messages[-50:]
            summaries = self.get_summary_cards(user_id, character_id)
            new_profile = generate_user_profile_memory_card(
                character_profile=character_profile,
                existing_profile_card=existing_profile,
                recent_messages=recent_messages,
                history_summaries=summaries,
                total_message_count=message_count,
            )
            self._save_profile_card(memory, new_profile, message_count)
            profile_updated = True

        logger.info(
            "Memory update for user=%s character=%s: profile=%s summaries=%s message_count=%s",
            user_id,
            character_id,
            profile_updated,
            summaries_updated,
            message_count,
        )
        return profile_updated, summaries_updated


community_memory_table = CommunityMemoryTable(chat_db)
