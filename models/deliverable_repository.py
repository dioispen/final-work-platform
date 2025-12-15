from typing import Optional, List
from psycopg2.extras import RealDictCursor
from db import get_db

class DeliverableRepository:
    """結案檔案資料存取層"""
    
    @staticmethod
    def get_all_by_project_id(project_id: int) -> List[dict]:
        """取得專案所有結案檔案（歷史版本）"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM deliverables WHERE project_id = %s ORDER BY uploaded_at DESC", (project_id,))
            return cur.fetchall()
    
    @staticmethod
    def get_latest_by_project_id(project_id: int) -> Optional[dict]:
        """取得專案最新一筆結案檔案"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM deliverables WHERE project_id = %s ORDER BY uploaded_at DESC LIMIT 1", (project_id,))
            return cur.fetchone()
    
    @staticmethod
    def create(project_id: int, file_name: str, file_path: str, message: str) -> int:
        """建立結案檔案（新增一個版本，保留歷史）"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO deliverables (project_id, file_name, file_path, message, uploaded_at)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING id
            """, (project_id, file_name, file_path, message))
            deliverable_id = cur.fetchone()[0]
            conn.commit()
            return deliverable_id
        
    @staticmethod
    def delete_by_project_id(project_id: int) -> bool:
        """刪除專案的結案檔案（保留：僅供管理用途）"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM deliverables WHERE project_id = %s", (project_id,))
            changed = cur.rowcount > 0
            conn.commit()
            return changed