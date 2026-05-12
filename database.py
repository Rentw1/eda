import aiosqlite
from datetime import date

DB_PATH = "calories.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                name TEXT NOT NULL,
                grams REAL NOT NULL,
                kcal REAL NOT NULL,
                protein REAL NOT NULL,
                fat REAL NOT NULL,
                carbs REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                user_id INTEGER PRIMARY KEY,
                kcal_goal INTEGER DEFAULT 2000
            )
        """)
        await db.commit()

async def add_meal(user_id: int, name: str, grams: float, kcal: float, protein: float, fat: float, carbs: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO meals (user_id, date, name, grams, kcal, protein, fat, carbs) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, date.today().isoformat(), name, grams, kcal, protein, fat, carbs)
        )
        await db.commit()

async def get_today(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM meals WHERE user_id=? AND date=? ORDER BY created_at",
            (user_id, date.today().isoformat())
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]

async def get_week(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT date, SUM(kcal) as kcal, SUM(protein) as protein,
               SUM(fat) as fat, SUM(carbs) as carbs
               FROM meals WHERE user_id=? AND date >= date('now','-6 days')
               GROUP BY date ORDER BY date""",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]

async def delete_last_meal(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM meals WHERE user_id=? AND date=? ORDER BY created_at DESC LIMIT 1",
            (user_id, date.today().isoformat())
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return False
        await db.execute("DELETE FROM meals WHERE id=?", (row[0],))
        await db.commit()
    return True

async def set_goal(user_id: int, kcal_goal: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO goals (user_id, kcal_goal) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET kcal_goal=?",
            (user_id, kcal_goal, kcal_goal)
        )
        await db.commit()

async def get_goal(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT kcal_goal FROM goals WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else 2000
