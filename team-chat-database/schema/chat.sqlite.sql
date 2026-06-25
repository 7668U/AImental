PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS team_chat_roles (
  author_role TEXT PRIMARY KEY,
  author_name TEXT NOT NULL,
  home_folder TEXT NOT NULL
);

INSERT OR IGNORE INTO team_chat_roles (author_role, author_name, home_folder) VALUES
  ('product_manager', '产品经理', 'product-design-iterations'),
  ('frontend_designer', '前端设计师', 'frontend-design-iterations'),
  ('backend_engineer', '后端工程师', 'backend-work-iterations');

CREATE TABLE IF NOT EXISTS team_chat_messages (
  id TEXT PRIMARY KEY,
  room_id TEXT NOT NULL DEFAULT 'core-team',
  created_at TEXT NOT NULL,
  author_role TEXT NOT NULL CHECK (author_role IN ('system', 'product_manager', 'frontend_designer', 'backend_engineer')),
  author_name TEXT NOT NULL,
  reply_to_id TEXT NULL REFERENCES team_chat_messages(id) ON DELETE SET NULL,
  topic TEXT NOT NULL DEFAULT 'general',
  message_type TEXT NOT NULL DEFAULT 'message' CHECK (message_type IN ('system', 'message', 'question', 'answer', 'decision', 'task', 'note', 'handoff', 'review')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'blocked', 'resolved', 'archived')),
  body TEXT NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '[]',
  mentions_json TEXT NOT NULL DEFAULT '[]',
  links_json TEXT NOT NULL DEFAULT '[]',
  attachments_json TEXT NOT NULL DEFAULT '[]',
  related_files_json TEXT NOT NULL DEFAULT '[]',
  decisions_json TEXT NOT NULL DEFAULT '[]',
  tasks_json TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_team_chat_messages_created_at
  ON team_chat_messages (created_at);

CREATE INDEX IF NOT EXISTS idx_team_chat_messages_reply_to
  ON team_chat_messages (reply_to_id);

CREATE INDEX IF NOT EXISTS idx_team_chat_messages_topic
  ON team_chat_messages (topic);

CREATE INDEX IF NOT EXISTS idx_team_chat_messages_author_role
  ON team_chat_messages (author_role);

