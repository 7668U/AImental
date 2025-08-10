# db.py
import peewee as pw

# This file's ONLY job is to create and export the database connection objects.
# It does not need to know about any specific models.

# --- Database Instances ---
user_db = pw.SqliteDatabase('db/user_account.db')
chat_db = pw.SqliteDatabase('db/chat_history.db')
assessment_db = pw.SqliteDatabase('db/psychological_assessment.db')
status_db = pw.SqliteDatabase('db/daily_status.db')
feedback_db = pw.SqliteDatabase('db/feedback.db')
promotion_db = pw.SqliteDatabase('db/promotion.db')

cabinet_db = pw.SqliteDatabase('db/cabinet.db')

# A list of all database connections for easy management in main.py
all_dbs = [user_db, chat_db, assessment_db, status_db, feedback_db, promotion_db, cabinet_db]