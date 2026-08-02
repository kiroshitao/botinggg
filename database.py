import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER DEFAULT NULL,
                level INTEGER DEFAULT 0,
                FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mentors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                photo_file_id TEXT DEFAULT NULL,
                description TEXT DEFAULT '',
                experience TEXT DEFAULT '',
                specialization TEXT DEFAULT '',
                price TEXT DEFAULT '',
                tg_username TEXT DEFAULT '',
                tg_user_id INTEGER DEFAULT NULL,
                is_active INTEGER DEFAULT 1,
                category_id INTEGER DEFAULT NULL,
                topic_id INTEGER DEFAULT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_tg_id INTEGER NOT NULL,
                student_username TEXT DEFAULT '',
                student_name TEXT DEFAULT '',
                mentor_id INTEGER NOT NULL,
                direction TEXT DEFAULT '',
                specialization TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'Новая заявка',
                status_updated_at TEXT DEFAULT NULL,
                contacted INTEGER DEFAULT 0,
                deal_closed INTEGER DEFAULT 0,
                commission_paid INTEGER DEFAULT 0,
                commission_amount REAL DEFAULT 0.0,
                admin_message_id INTEGER DEFAULT NULL,
                FOREIGN KEY (mentor_id) REFERENCES mentors(id) ON DELETE CASCADE
            )
        """)
        await db.commit()


# ─── Categories ───────────────────────────────────────────────────────────────

async def get_root_categories():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM categories WHERE parent_id IS NULL ORDER BY name"
        ) as cursor:
            return await cursor.fetchall()


async def get_subcategories(parent_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM categories WHERE parent_id = ? ORDER BY name",
            (parent_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_category(category_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ) as cursor:
            return await cursor.fetchone()


async def add_category(name: str, parent_id: int | None = None) -> int:
    level = 0
    if parent_id is not None:
        parent = await get_category(parent_id)
        if parent:
            level = parent["level"] + 1
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO categories (name, parent_id, level) VALUES (?, ?, ?)",
            (name, parent_id, level)
        )
        await db.commit()
        return cursor.lastrowid


async def update_category(category_id: int, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE categories SET name = ? WHERE id = ?", (name, category_id)
        )
        await db.commit()


async def delete_category(category_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await db.commit()


async def has_subcategories(category_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM categories WHERE parent_id = ?", (category_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] > 0


async def get_mentors_in_category(category_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM mentors WHERE category_id = ? ORDER BY name",
            (category_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_category_path(category_id: int) -> list[str]:
    """Returns list of category names from root to given category."""
    path = []
    current_id = category_id
    while current_id:
        cat = await get_category(current_id)
        if not cat:
            break
        path.insert(0, cat["name"])
        current_id = cat["parent_id"]
    return path


# ─── Mentors ──────────────────────────────────────────────────────────────────

async def get_mentor(mentor_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM mentors WHERE id = ?", (mentor_id,)
        ) as cursor:
            return await cursor.fetchone()


async def get_all_mentors():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM mentors ORDER BY name") as cursor:
            return await cursor.fetchall()


async def add_mentor(
    name: str,
    photo_file_id: str | None,
    description: str,
    experience: str,
    specialization: str,
    price: str,
    tg_username: str,
    tg_user_id: int | None,
    category_id: int | None,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO mentors
               (name, photo_file_id, description, experience, specialization,
                price, tg_username, tg_user_id, category_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, photo_file_id, description, experience, specialization,
             price, tg_username, tg_user_id, category_id)
        )
        await db.commit()
        return cursor.lastrowid


async def update_mentor_field(mentor_id: int, field: str, value):
    allowed = {
        "name", "photo_file_id", "description", "experience",
        "specialization", "price", "tg_username", "tg_user_id",
        "is_active", "category_id", "topic_id"
    }
    if field not in allowed:
        raise ValueError(f"Field '{field}' is not allowed")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE mentors SET {field} = ? WHERE id = ?", (value, mentor_id)
        )
        await db.commit()


async def delete_mentor(mentor_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM mentors WHERE id = ?", (mentor_id,))
        await db.commit()


async def toggle_mentor_active(mentor_id: int) -> bool:
    mentor = await get_mentor(mentor_id)
    if not mentor:
        return False
    new_status = 0 if mentor["is_active"] else 1
    await update_mentor_field(mentor_id, "is_active", new_status)
    return bool(new_status)


# ─── Applications ─────────────────────────────────────────────────────────────

async def create_application(
    student_tg_id: int,
    student_username: str,
    student_name: str,
    mentor_id: int,
    direction: str,
    specialization: str,
    created_at: str,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO applications
               (student_tg_id, student_username, student_name, mentor_id,
                direction, specialization, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Новая заявка')""",
            (student_tg_id, student_username, student_name, mentor_id,
             direction, specialization, created_at)
        )
        await db.commit()
        return cursor.lastrowid


async def get_application(app_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ) as cursor:
            return await cursor.fetchone()


async def update_application_status(app_id: int, status: str, updated_at: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE applications SET status = ?, status_updated_at = ? WHERE id = ?",
            (status, updated_at, app_id)
        )
        await db.commit()


async def update_application_admin_message(app_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE applications SET admin_message_id = ? WHERE id = ?",
            (message_id, app_id)
        )
        await db.commit()


async def update_application_field(app_id: int, field: str, value):
    allowed = {"contacted", "deal_closed", "commission_paid", "commission_amount"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' is not allowed")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE applications SET {field} = ? WHERE id = ?", (value, app_id)
        )
        await db.commit()


async def get_applications_by_mentor(mentor_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM applications WHERE mentor_id = ? ORDER BY created_at DESC",
            (mentor_id,)
        ) as cursor:
            return await cursor.fetchall()


async def get_all_applications():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM applications ORDER BY created_at DESC"
        ) as cursor:
            return await cursor.fetchall()


# ─── Statistics ───────────────────────────────────────────────────────────────

async def get_statistics() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async def scalar(query, params=()):
            async with db.execute(query, params) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

        total = await scalar("SELECT COUNT(*) FROM applications")
        confirmed = await scalar(
            "SELECT COUNT(*) FROM applications WHERE status = 'Подтверждена'"
        )
        rejected = await scalar(
            "SELECT COUNT(*) FROM applications WHERE status = 'Отклонена'"
        )
        active_mentors = await scalar(
            "SELECT COUNT(*) FROM mentors WHERE is_active = 1"
        )
        contacted = await scalar(
            "SELECT COUNT(*) FROM applications WHERE contacted = 1"
        )
        deals_closed = await scalar(
            "SELECT COUNT(*) FROM applications WHERE deal_closed = 1"
        )
        commission = await scalar(
            "SELECT COALESCE(SUM(commission_amount), 0) FROM applications WHERE commission_paid = 1"
        )

        conversion = round(confirmed / total * 100, 1) if total > 0 else 0.0

        # Per mentor stats
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT m.name, COUNT(a.id) as cnt
            FROM mentors m
            LEFT JOIN applications a ON a.mentor_id = m.id
            GROUP BY m.id
            ORDER BY cnt DESC
        """) as cur:
            per_mentor = await cur.fetchall()

        return {
            "total": total,
            "confirmed": confirmed,
            "rejected": rejected,
            "active_mentors": active_mentors,
            "contacted": contacted,
            "deals_closed": deals_closed,
            "commission": commission,
            "conversion": conversion,
            "per_mentor": per_mentor,
        }
