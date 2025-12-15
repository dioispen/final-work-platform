# models/issue_repository.py
from typing import List, Optional
from psycopg2.extras import RealDictCursor
from db import get_db

class IssueRepository:
    
    # --- 議題 (Issue) 相關 ---

    @staticmethod
    def create_issue(project_id: int, creator_id: int, title: str) -> int:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO issues (project_id, creator_id, title, status, created_at)
                VALUES (%s, %s, %s, 'open', NOW())
                RETURNING id
            """, (project_id, creator_id, title))
            issue_id = cur.fetchone()[0]
            conn.commit()
            return issue_id

    @staticmethod
    def get_by_project(project_id: int) -> List[dict]:
        """取得某專案下的所有議題"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM issues WHERE project_id = %s ORDER BY created_at DESC
            """, (project_id,))
            return cur.fetchall()

    @staticmethod
    def get_by_id(issue_id: int) -> Optional[dict]:
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM issues WHERE id = %s", (issue_id,))
            return cur.fetchone()

    @staticmethod
    def close_issue(issue_id: int):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE issues SET status = 'resolved' WHERE id = %s", (issue_id,))
            conn.commit()

    # --- 留言 (Comment) 相關 ---

    @staticmethod
    def add_comment(issue_id: int, user_id: int, message: str):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO issue_comments (issue_id, user_id, message, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (issue_id, user_id, message))
            conn.commit()

    @staticmethod
    def get_comments(issue_id: int) -> List[dict]:
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT c.*, u.username, u.role
                FROM issue_comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.issue_id = %s
                ORDER BY c.created_at ASC
            """, (issue_id,))
            return cur.fetchall()