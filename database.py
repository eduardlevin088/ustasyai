import aiosqlite
import logging
import uuid
from config import DB_PATH


logger = logging.getLogger(__name__)

db: aiosqlite.Connection = None


async def init_db():
    global db
    try:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        
        await create_tables()
        logger.info(f"Database initialized: {DB_PATH}")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def create_tables():
    if db is None:
        raise RuntimeError("Database not initialized")
    
    # Users
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            last_response_id TEXT,
            role TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.commit()
    logger.info("Database tables created successfully")


async def close_db():
    global db
    if db:
        await db.close()
        db = None
        logger.info("Database connection closed")


async def create_user(user_id: int, username: str = None) -> None:
    if db is None:
        raise RuntimeError("Database not initialized")
    
    await db.execute("""
        DELETE FROM users WHERE user_id = ?
    """, (user_id,))

    await db.execute("""
        INSERT INTO users (user_id, username)
        VALUES (?, ?)
    """, (user_id, username))
    await db.commit()


async def get_user_last_response_id(user_id: int) -> str | None:
    if db is None:
        raise RuntimeError("Database not initialized")
    
    async with db.execute(
        "SELECT last_response_id FROM users WHERE user_id = ?",
        (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row and row[0] else None


async def set_user_last_response_id(user_id: int, last_response_id: str):
    if db is None:
        raise RuntimeError("Database not initialized")
    
    await db.execute("""
        UPDATE users SET last_response_id = ?
        WHERE user_id = ?
    """, (last_response_id, user_id))
    await db.commit()


async def get_users() -> list[tuple]:
    if db is None:
        raise RuntimeError("Database not initialized")
    
    async with db.execute("""
        SELECT username, user_id
        FROM users
    """) as cursor:
        rows = await cursor.fetchall()
        users = [ (row["username"], row["user_id"], row["role"]) for row in rows]
        return users


async def set_user_role(user_id: int, role: str):
    if db is None:
        raise RuntimeError("Database not initialized")
    
    await db.execute("""
        UPDATE users SET role = ?
        WHERE user_id = ?
    """, (role.upper(), user_id))
    await db.commit()


async def get_user_role(user_id: int) -> str | None:
    if db is None:
        raise RuntimeError("Database not initialized")
    
    async with db.execute("""
        SELECT role FROM users WHERE user_id = ?
    """, (user_id,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row and row[0] else None
