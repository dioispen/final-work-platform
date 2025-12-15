from db import get_db


class ReviewRepository:

    # =========================
    # 是否已評價（防止重複）
    # =========================
    @staticmethod
    def has_reviewed(project_id, reviewer_id):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 1
                FROM reviews
                WHERE project_id = %s
                  AND reviewer_id = %s
            """, (project_id, reviewer_id))
            return cur.fetchone() is not None

    # =========================
    # 建立評價（⭐ 支援 keyword argument）
    # =========================
    @staticmethod
    def create(
        *,
        project_id,
        reviewer_id,
        reviewee_id,   # ← routes 用這個名字
        score_1,
        score_2,
        score_3,
        comment
    ):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO reviews (
                    project_id,
                    reviewer_id,
                    target_id,
                    dim1,
                    dim2,
                    dim3,
                    comment
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                project_id,
                reviewer_id,
                reviewee_id,  # → 寫進 target_id
                score_1,      # → dim1
                score_2,      # → dim2
                score_3,      # → dim3
                comment
            ))

    # =========================
    # 平均評分 + 歷史評論（需求 1、2）
    # =========================
    @staticmethod
    def get_average_and_comments(target_id):
        with get_db() as conn:
            cur = conn.cursor()

            # 平均分數
            cur.execute("""
                SELECT
                    AVG(dim1),
                    AVG(dim2),
                    AVG(dim3)
                FROM reviews
                WHERE target_id = %s
            """, (target_id,))
            avg = cur.fetchone()

            # 歷史評論
            cur.execute("""
                SELECT comment, created_at
                FROM reviews
                WHERE target_id = %s
                  AND comment IS NOT NULL
                ORDER BY created_at DESC
            """, (target_id,))
            comments = cur.fetchall()

        return {
            "avg": avg,
            "comments": comments
        }
