import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = "bot_database.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        # جدول کاربران
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                join_date TEXT,
                is_blocked INTEGER DEFAULT 0
            )
        """)

        # جدول پلن‌ها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                price INTEGER NOT NULL,
                duration_days INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)

        # جدول سفارش‌ها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                receipt_file_id TEXT,
                sub_link TEXT,
                created_at TEXT,
                updated_at TEXT,
                admin_note TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (plan_id) REFERENCES plans (id)
            )
        """)

        # جدول لینک‌های ساب
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sub_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                link TEXT NOT NULL,
                is_used INTEGER DEFAULT 0,
                used_in_order_id INTEGER,
                created_at TEXT,
                FOREIGN KEY (plan_id) REFERENCES plans (id)
            )
        """)

        # جدول تنظیمات
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # مقادیر پیش‌فرض تنظیمات
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ("card_number", "6037-****-****-****")
        )
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ("card_name", "نام صاحب کارت")
        )
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ("welcome_text", "به ربات فروش فیلترشکن خوش آمدید 🌟")
        )

        await db.commit()


# ----------------- Users -----------------

async def add_user(user_id: int, username: str = None, full_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO users (user_id, username, full_name, join_date)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, username, full_name, datetime.now().isoformat())
        )
        await db.commit()


async def get_user(user_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ----------------- Settings -----------------

async def get_setting(key: str) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


# ----------------- Plans -----------------

async def add_plan(title: str, description: str, price: int, duration_days: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO plans (title, description, price, duration_days, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, description, price, duration_days, datetime.now().isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def get_active_plans() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM plans WHERE is_active = 1 ORDER BY price"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_all_plans() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM plans ORDER BY id") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_plan(plan_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_plan_price(plan_id: int, new_price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE plans SET price = ? WHERE id = ?",
            (new_price, plan_id)
        )
        await db.commit()


async def update_plan(plan_id: int, title: str = None, description: str = None,
                      price: int = None, duration_days: int = None, is_active: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        plan = await get_plan(plan_id)
        if not plan:
            return False

        title = title if title is not None else plan["title"]
        description = description if description is not None else plan["description"]
        price = price if price is not None else plan["price"]
        duration_days = duration_days if duration_days is not None else plan["duration_days"]
        is_active = is_active if is_active is not None else plan["is_active"]

        await db.execute(
            """
            UPDATE plans
            SET title = ?, description = ?, price = ?, duration_days = ?, is_active = ?
            WHERE id = ?
            """,
            (title, description, price, duration_days, is_active, plan_id)
        )
        await db.commit()
        return True


async def delete_plan(plan_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        await db.commit()


# ----------------- Sub Links -----------------

async def add_sub_link(plan_id: int, link: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO sub_links (plan_id, link, created_at)
            VALUES (?, ?, ?)
            """,
            (plan_id, link.strip(), datetime.now().isoformat())
        )
        await db.commit()


async def add_sub_links_bulk(plan_id: int, links: List[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        for link in links:
            link = link.strip()
            if link:
                await db.execute(
                    """
                    INSERT INTO sub_links (plan_id, link, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (plan_id, link, datetime.now().isoformat())
                )
        await db.commit()


async def get_available_sub_count(plan_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM sub_links WHERE plan_id = ? AND is_used = 0",
            (plan_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_available_sub_link(plan_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM sub_links
            WHERE plan_id = ? AND is_used = 0
            ORDER BY id ASC LIMIT 1
            """,
            (plan_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def mark_sub_link_used(link_id: int, order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE sub_links
            SET is_used = 1, used_in_order_id = ?
            WHERE id = ?
            """,
            (order_id, link_id)
        )
        await db.commit()


async def get_sub_links_stats(plan_id: int) -> Dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM sub_links WHERE plan_id = ?", (plan_id,)
        ) as cursor:
            total = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM sub_links WHERE plan_id = ? AND is_used = 0", (plan_id,)
        ) as cursor:
            available = (await cursor.fetchone())[0]

        return {"total": total, "available": available, "used": total - available}


# ----------------- Orders -----------------

async def create_order(user_id: int, plan_id: int, amount: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().isoformat()
        cursor = await db.execute(
            """
            INSERT INTO orders (user_id, plan_id, amount, status, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (user_id, plan_id, amount, now, now)
        )
        await db.commit()
        return cursor.lastrowid


async def get_order(order_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_order_status(order_id: int, status: str, sub_link: str = None, admin_note: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().isoformat()
        if sub_link:
            await db.execute(
                """
                UPDATE orders
                SET status = ?, sub_link = ?, updated_at = ?, admin_note = ?
                WHERE id = ?
                """,
                (status, sub_link, now, admin_note, order_id)
            )
        else:
            await db.execute(
                """
                UPDATE orders
                SET status = ?, updated_at = ?, admin_note = ?
                WHERE id = ?
                """,
                (status, now, admin_note, order_id)
            )
        await db.commit()


async def set_order_receipt(order_id: int, file_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE orders
            SET receipt_file_id = ?, status = 'waiting_approval', updated_at = ?
            WHERE id = ?
            """,
            (file_id, datetime.now().isoformat(), order_id)
        )
        await db.commit()


async def get_user_orders(user_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT o.*, p.title as plan_title
            FROM orders o
            JOIN plans p ON o.plan_id = p.id
            WHERE o.user_id = ?
            ORDER BY o.id DESC
            """,
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_pending_orders() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT o.*, p.title as plan_title, u.username, u.full_name
            FROM orders o
            JOIN plans p ON o.plan_id = p.id
            JOIN users u ON o.user_id = u.user_id
            WHERE o.status = 'waiting_approval'
            ORDER BY o.id ASC
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_orders_count_by_status(status: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE status = ?", (status,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
