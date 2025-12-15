from typing import List, Optional
from psycopg2.extras import RealDictCursor
from db import get_db

class ProjectRepository:
    """專案資料存取層"""
    
    @staticmethod
    def get_by_client_id(client_id: int) -> List[dict]:
        """取得委託人的所有專案"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT p.*, u.username as contractor_name
                FROM projects p
                LEFT JOIN users u ON p.contractor_id = u.id
                WHERE p.client_id = %s
                ORDER BY p.updated_at DESC
            """, (client_id,))
            return cur.fetchall()
    
    @staticmethod
    def get_by_id(project_id: int) -> Optional[dict]:
        """根據 ID 取得專案"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT p.*, 
                       uc.username as client_name,
                       uo.username as contractor_name
                FROM projects p
                JOIN users uc ON p.client_id = uc.id
                LEFT JOIN users uo ON p.contractor_id = uo.id
                WHERE p.id = %s
            """, (project_id,))
            return cur.fetchone()
    
    @staticmethod
    def get_available_projects() -> List[dict]:
        """取得所有可接案的專案"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT p.*, u.username as client_name
                FROM projects p
                JOIN users u ON p.client_id = u.id
                WHERE p.status = 'open'
                ORDER BY p.updated_at DESC
            """)
            return cur.fetchall()
    
    @staticmethod
    def create(title: str, description: str, budget: int, client_id: int, deadline: Optional[str] = None) -> int:
        """建立新專案"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO projects (title, description, budget, client_id, status, updated_at, deadline)
                VALUES (%s, %s, %s, %s, 'open', NOW(), %s)
                RETURNING id
            """, (title, description, budget, client_id, deadline))
            project_id = cur.fetchone()[0]
            conn.commit()
            return project_id

    @staticmethod
    def update(project_id: int, title: str, description: str, budget: int, client_id: int, deadline: Optional[str] = None) -> bool:
        """更新專案"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE projects
                SET title = %s, description = %s, budget = %s, updated_at = NOW(), deadline = %s
                WHERE id = %s AND client_id = %s
            """, (title, description, budget, deadline, project_id, client_id))
            changed = cur.rowcount > 0
            conn.commit()
            return changed

    @staticmethod
    def assign_contractor(project_id: int, contractor_id: int) -> bool:
        """指派接案人"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE projects
                SET contractor_id = %s, status = 'assigned', updated_at = NOW()
                WHERE id = %s
            """, (contractor_id, project_id))
            changed = cur.rowcount > 0
            conn.commit()
            return changed

    @staticmethod
    def complete(project_id: int, client_id: int) -> bool:
        """完成專案"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE projects
                SET status = 'completed', updated_at = NOW()
                WHERE id = %s AND client_id = %s
            """, (project_id, client_id))
            changed = cur.rowcount > 0
            conn.commit()
            return changed

    @staticmethod
    def reject(project_id: int, client_id: int) -> bool:
        """退件"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE projects
                SET status = 'rejected', updated_at = NOW()
                WHERE id = %s AND client_id = %s
            """, (project_id, client_id))
            changed = cur.rowcount > 0
            conn.commit()
            return changed

    @staticmethod
    def get_contractor_projects(contractor_id: int) -> List[dict]:
        """取得接案人的所有專案"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT p.*, u.username as client_name
                FROM projects p
                JOIN users u ON p.client_id = u.id
                WHERE p.contractor_id = %s
                ORDER BY p.updated_at DESC
            """, (contractor_id,))
            return cur.fetchall()

    @staticmethod
    def get_project_with_client(project_id: int) -> Optional[dict]:
        """取得專案和委託人資訊"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT p.*, u.username as client_name
                FROM projects p
                JOIN users u ON p.client_id = u.id
                WHERE p.id = %s
            """, (project_id,))
            return cur.fetchone()

    @staticmethod
    def get_project_by_contractor(project_id: int, contractor_id: int) -> Optional[dict]:
        """取得接案人的特定專案"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM projects
                WHERE id = %s AND contractor_id = %s
            """, (project_id, contractor_id))
            return cur.fetchone()