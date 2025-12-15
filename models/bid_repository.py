from typing import List, Optional
from psycopg2.extras import RealDictCursor
from db import get_db

class BidRepository:
    """投標資料存取層"""
    
    @staticmethod
    def get_by_project_id(project_id: int) -> List[dict]:
        """取得專案的所有投標"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT b.*, u.username as contractor_name, p.client_id
                FROM bids b
                JOIN users u ON b.contractor_id = u.id
                JOIN projects p ON b.project_id = p.id
                WHERE b.project_id = %s
                ORDER BY b.updated_at ASC
            """, (project_id,))
            return cur.fetchall()
    
    @staticmethod
    def get_by_id(bid_id: int) -> Optional[dict]:
        """根據 ID 取得投標"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT b.*, p.client_id
                FROM bids b
                JOIN projects p ON b.project_id = p.id
                WHERE b.id = %s
            """, (bid_id,))
            return cur.fetchone()
    
    @staticmethod
    def create(project_id: int, contractor_id: int, price: int, message: str, file_name: str = None, file_path: str = None) -> int:
        """建立投標（含提案檔案）"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO bids (project_id, contractor_id, price, message, status, updated_at, file_name, file_path, uploaded_at)
                VALUES (%s, %s, %s, %s, 'pending', NOW(), %s, %s, NOW())
                RETURNING id
            """, (project_id, contractor_id, price, message, file_name, file_path))
            bid_id = cur.fetchone()[0]
            conn.commit()
            return bid_id
    
    @staticmethod
    def accept(bid_id: int) -> bool:
        """接受投標"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE bids
                SET status = 'accepted'
                WHERE id = %s
            """, (bid_id,))
            changed = cur.rowcount > 0
            conn.commit()
            return changed
    
    @staticmethod
    def reject_others(project_id: int, accepted_bid_id: int) -> bool:
        """拒絕其他投標"""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE bids
                SET status = 'rejected', updated_at = NOW()
                WHERE project_id = %s AND id != %s
            """, (project_id, accepted_bid_id))
            changed = cur.rowcount > 0
            conn.commit()
            return changed
    
    @staticmethod
    def get_contractor_bid(project_id: int, contractor_id: int) -> Optional[dict]:
        """取得接案人對某專案的投標"""
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM bids
                WHERE project_id = %s AND contractor_id = %s
            """, (project_id, contractor_id))
            return cur.fetchone()