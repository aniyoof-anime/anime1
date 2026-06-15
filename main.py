"""
Aniyoof Bot — aiogram 3.7 | asyncpg | Render.com ready
"""
from __future__ import annotations

import asyncio
import logging
import os
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
import asyncpg
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery, KeyboardButton, Message,
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────── CONFIG ────────────────────────────────────────

BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
_raw_admins      = os.getenv("ADMIN_IDS", "")
_raw_super       = os.getenv("SUPER_ADMIN_IDS", _raw_admins)
ADMIN_IDS       = [int(x) for x in _raw_admins.split(",") if x.strip().isdigit()]
SUPER_ADMIN_IDS = [int(x) for x in _raw_super.split(",")  if x.strip().isdigit()]
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@Aniyoof")
CHANNEL_ID       = os.getenv("CHANNEL_ID", "-100000000000")
BOT_USERNAME     = os.getenv("BOT_USERNAME", "aniyoof_bot")
DATABASE_URL     = os.getenv("DATABASE_URL", "")
ADVERTISER_UN    = os.getenv("ADVERTISER_USERNAME", "@Sarvarbek_offf")
ADMIN_USERNAMES  = [u.strip() for u in os.getenv("ADMIN_USERNAMES", "").split(",") if u.strip()]
PAYMENT_CARD     = os.getenv("PAYMENT_CARD", "8600 0000 0000 0000")
PORT             = int(os.getenv("PORT", "8080"))

GENRES = [
    "Aksyon", "Komediya", "Drama", "Romantika", "Fantastika",
    "Sehrli", "Jangovar san'at", "Maktab", "Isekai", "Triller",
    "Qo'rqinch", "Sport", "Sarguzasht", "Tarix", "Musiqiy",
    "Psixologik", "Supernatural",
]
YEARS       = [str(y) for y in range(2025, 1999, -1)]
AGE_RATINGS = ["10+","11+","12+","13+","14+","15+","16+","17+","18+","Belgilanmagan"]

INFO_FORMAT = (
    "Quyidagi formatda yuboring:\n\n"
    "Nomi: \nKod: \nJanr: \nYil: \n"
    "Fasllar: \nQismlar: \n"
    "Holati: Tugallangan yoki Davom etmoqda\n"
    "Yosh: 18+ yoki 16+ yoki 12+ yoki Belgilanmagan\n"
    "Tavsif: (ixtiyoriy)"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("aniyoof")

# ──────────────────────────── DB POOL ───────────────────────────────────────

pool: Optional[asyncpg.Pool] = None


async def init_db() -> None:
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL, ssl="require", statement_cache_size=0, min_size=2, max_size=10
    )
    async with pool.acquire() as c:
        await c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id               SERIAL PRIMARY KEY,
            telegram_id      BIGINT UNIQUE NOT NULL,
            username         TEXT,
            ism              TEXT,
            yosh             INTEGER,
            jins             TEXT,
            qiziqishlar      TEXT,
            raqam            TEXT,
            premium          BOOLEAN   DEFAULT FALSE,
            premium_tugash   TIMESTAMP,
            royxat_sanasi    TIMESTAMP DEFAULT NOW(),
            korgan_count     INTEGER   DEFAULT 0,
            is_blocked       BOOLEAN   DEFAULT FALSE
        );

        CREATE TABLE IF NOT EXISTS admins (
            id               SERIAL PRIMARY KEY,
            telegram_id      BIGINT UNIQUE NOT NULL,
            username         TEXT,
            qoshgan_admin    BIGINT,
            qoshilgan_sana   TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS animes (
            id               SERIAL PRIMARY KEY,
            nomi             TEXT NOT NULL,
            kodi             TEXT UNIQUE NOT NULL,
            janr             TEXT,
            yil              INTEGER,
            fasllar_soni     INTEGER   DEFAULT 1,
            qismlar_soni     INTEGER   DEFAULT 0,
            joylangan_qismlar INTEGER  DEFAULT 0,
            holati           TEXT      DEFAULT 'Davom etmoqda',
            yosh_chegarasi   TEXT      DEFAULT 'Belgilanmagan',
            media_file_id    TEXT,
            media_type       TEXT      DEFAULT 'photo',
            tavsif           TEXT      DEFAULT '',
            korish_soni      INTEGER   DEFAULT 0,
            reyting          REAL      DEFAULT 0,
            reyting_count    INTEGER   DEFAULT 0,
            created_at       TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS seasons (
            id          SERIAL PRIMARY KEY,
            anime_id    INTEGER REFERENCES animes(id) ON DELETE CASCADE,
            fasl_nomi   TEXT,
            fasl_raqami INTEGER
        );

        CREATE TABLE IF NOT EXISTS episodes (
            id            SERIAL PRIMARY KEY,
            season_id     INTEGER REFERENCES seasons(id) ON DELETE CASCADE,
            anime_id      INTEGER REFERENCES animes(id)  ON DELETE CASCADE,
            qism_raqami   INTEGER,
            video_file_id TEXT NOT NULL,
            nomi          TEXT
        );

        CREATE TABLE IF NOT EXISTS favorites (
            id         SERIAL PRIMARY KEY,
            user_id    BIGINT  NOT NULL,
            anime_id   INTEGER REFERENCES animes(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, anime_id)
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id       SERIAL PRIMARY KEY,
            user_id  BIGINT  NOT NULL,
            anime_id INTEGER REFERENCES animes(id) ON DELETE CASCADE,
            fasl     INTEGER DEFAULT 1,
            qism     INTEGER DEFAULT 1,
            UNIQUE(user_id, anime_id)
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id       SERIAL PRIMARY KEY,
            user_id  BIGINT  NOT NULL,
            anime_id INTEGER REFERENCES animes(id) ON DELETE CASCADE,
            baho     REAL    NOT NULL,
            UNIQUE(user_id, anime_id)
        );

        CREATE TABLE IF NOT EXISTS comments (
            id         SERIAL PRIMARY KEY,
            user_id    BIGINT  NOT NULL,
            anime_id   INTEGER REFERENCES animes(id) ON DELETE CASCADE,
            matn       TEXT    NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS premium_requests (
            id                 SERIAL PRIMARY KEY,
            user_id            BIGINT NOT NULL,
            tarif              TEXT   NOT NULL,
            screenshot_file_id TEXT,
            holati             TEXT   DEFAULT 'kutilmoqda',
            created_at         TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id       SERIAL PRIMARY KEY,
            user_id  BIGINT  NOT NULL,
            anime_id INTEGER REFERENCES animes(id) ON DELETE CASCADE,
            UNIQUE(user_id, anime_id)
        );
        """)

        # Safe migrations for older DBs
        for sql in [
            "ALTER TABLE animes ADD COLUMN IF NOT EXISTS joylangan_qismlar INTEGER DEFAULT 0",
            "ALTER TABLE animes ADD COLUMN IF NOT EXISTS yosh_chegarasi TEXT DEFAULT 'Belgilanmagan'",
        ]:
            try:
                await c.execute(sql)
            except Exception:
                pass

    log.info("✅ Database initialized")


# ──────────────────────────── DB: ADMINS ────────────────────────────────────

async def db_get_admins():
    async with pool.acquire() as c:
        return await c.fetch("SELECT * FROM admins ORDER BY qoshilgan_sana")


async def db_add_admin(tid: int, username: str, added_by: int) -> bool:
    async with pool.acquire() as c:
        try:
            await c.execute(
                "INSERT INTO admins(telegram_id,username,qoshgan_admin) "
                "VALUES($1,$2,$3) ON CONFLICT DO NOTHING",
                tid, username, added_by,
            )
            return True
        except Exception:
            return False


async def db_remove_admin(tid: int) -> None:
    async with pool.acquire() as c:
        await c.execute("DELETE FROM admins WHERE telegram_id=$1", tid)


async def load_db_admins() -> None:
    rows = await db_get_admins()
    for r in rows:
        if r["telegram_id"] not in ADMIN_IDS:
            ADMIN_IDS.append(r["telegram_id"])


# ──────────────────────────── DB: USERS ─────────────────────────────────────

async def db_get_user(tid: int):
    async with pool.acquire() as c:
        return await c.fetchrow("SELECT * FROM users WHERE telegram_id=$1", tid)


async def db_create_user(tid: int, username: Optional[str] = None) -> None:
    async with pool.acquire() as c:
        await c.execute(
            "INSERT INTO users(telegram_id,username) VALUES($1,$2) ON CONFLICT DO NOTHING",
            tid, username,
        )


async def db_update_user(tid: int, **kw) -> None:
    if not kw:
        return
    sets = ", ".join(f"{k}=${i+2}" for i, k in enumerate(kw))
    async with pool.acquire() as c:
        await c.execute(
            f"UPDATE users SET {sets} WHERE telegram_id=$1", tid, *kw.values()
        )


async def db_all_users():
    async with pool.acquire() as c:
        return await c.fetch("SELECT * FROM users WHERE is_blocked=FALSE")


async def db_premium_users():
    async with pool.acquire() as c:
        return await c.fetch("SELECT * FROM users WHERE premium=TRUE AND is_blocked=FALSE")


async def db_top_watchers(limit: int = 20):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT * FROM users ORDER BY korgan_count DESC LIMIT $1", limit
        )


async def db_user_rank(tid: int) -> int:
    async with pool.acquire() as c:
        row = await c.fetchrow(
            "SELECT rank FROM ("
            "  SELECT telegram_id, RANK() OVER (ORDER BY korgan_count DESC) as rank"
            "  FROM users"
            ") r WHERE telegram_id=$1",
            tid,
        )
        return row["rank"] if row else 0


async def db_stats() -> dict:
    async with pool.acquire() as c:
        return {
            "total_users":  await c.fetchval("SELECT COUNT(*) FROM users"),
            "premium_users": await c.fetchval("SELECT COUNT(*) FROM users WHERE premium=TRUE"),
            "total_animes": await c.fetchval("SELECT COUNT(*) FROM animes"),
            "total_views":  await c.fetchval("SELECT COALESCE(SUM(korish_soni),0) FROM animes"),
            "today_users":  await c.fetchval(
                "SELECT COUNT(*) FROM users WHERE royxat_sanasi::date=CURRENT_DATE"
            ),
            "erkak":   await c.fetchval("SELECT COUNT(*) FROM users WHERE jins='Erkak'"),
            "ayol":    await c.fetchval("SELECT COUNT(*) FROM users WHERE jins='Ayol'"),
            "yosh_avg": await c.fetchval(
                "SELECT ROUND(AVG(yosh)::numeric,1) FROM users WHERE yosh IS NOT NULL"
            ) or 0,
        }


# ──────────────────────────── DB: ANIME ─────────────────────────────────────

async def db_create_anime(
    nomi, kodi, janr, yil, fasllar_soni, qismlar_soni,
    holati, media_file_id, media_type, tavsif="", yosh_chegarasi="Belgilanmagan",
):
    async with pool.acquire() as c:
        return await c.fetchrow(
            "INSERT INTO animes"
            "(nomi,kodi,janr,yil,fasllar_soni,qismlar_soni,holati,"
            "media_file_id,media_type,tavsif,yosh_chegarasi)"
            "VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING *",
            nomi, kodi, janr, yil, fasllar_soni, qismlar_soni,
            holati, media_file_id, media_type, tavsif, yosh_chegarasi,
        )


async def db_get_anime(aid: int):
    async with pool.acquire() as c:
        return await c.fetchrow("SELECT * FROM animes WHERE id=$1", aid)


async def db_get_anime_by_code(kodi: str):
    async with pool.acquire() as c:
        return await c.fetchrow("SELECT * FROM animes WHERE kodi=$1", kodi)


async def db_search_anime_name(q: str):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT * FROM animes WHERE LOWER(nomi) LIKE LOWER($1) LIMIT 10", f"%{q}%"
        )


async def db_search_genre_year(janr: Optional[str], yil: Optional[str]):
    async with pool.acquire() as c:
        if janr and yil:
            return await c.fetch(
                "SELECT * FROM animes WHERE LOWER(janr) LIKE LOWER($1) AND yil=$2 LIMIT 10",
                f"%{janr}%", int(yil),
            )
        if janr:
            return await c.fetch(
                "SELECT * FROM animes WHERE LOWER(janr) LIKE LOWER($1) LIMIT 10", f"%{janr}%"
            )
        if yil:
            return await c.fetch("SELECT * FROM animes WHERE yil=$1", int(yil))
        return []


async def db_top_views(limit: int = 20):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT * FROM animes ORDER BY korish_soni DESC LIMIT $1", limit
        )


async def db_top_rating(limit: int = 20):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT * FROM animes WHERE reyting_count>0 ORDER BY reyting DESC LIMIT $1", limit
        )


async def db_random_anime():
    async with pool.acquire() as c:
        return await c.fetchrow("SELECT * FROM animes ORDER BY RANDOM() LIMIT 1")


async def db_all_animes():
    async with pool.acquire() as c:
        return await c.fetch("SELECT * FROM animes ORDER BY nomi")


async def db_delete_anime(aid: int) -> None:
    async with pool.acquire() as c:
        await c.execute("DELETE FROM animes WHERE id=$1", aid)


async def db_inc_views(aid: int) -> None:
    async with pool.acquire() as c:
        await c.execute("UPDATE animes SET korish_soni=korish_soni+1 WHERE id=$1", aid)


async def db_recommended(janr: str, limit: int = 5):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT * FROM animes WHERE LOWER(janr) LIKE LOWER($1)"
            " ORDER BY reyting DESC LIMIT $2",
            f"%{janr}%", limit,
        )


async def db_update_anime_field(aid: int, field: str, value) -> None:
    """Update a single column on animes table (safe whitelist enforced by caller)."""
    async with pool.acquire() as c:
        await c.execute(f"UPDATE animes SET {field}=$1 WHERE id=$2", value, aid)


# ──────────────────────────── DB: SEASONS / EPISODES ────────────────────────

async def db_create_season(anime_id: int, fasl_nomi: str, fasl_raqami: int):
    async with pool.acquire() as c:
        return await c.fetchrow(
            "INSERT INTO seasons(anime_id,fasl_nomi,fasl_raqami) VALUES($1,$2,$3) RETURNING *",
            anime_id, fasl_nomi, fasl_raqami,
        )


async def db_get_seasons(anime_id: int):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT * FROM seasons WHERE anime_id=$1 ORDER BY fasl_raqami", anime_id
        )


async def db_next_episode_number(season_id: int) -> int:
    async with pool.acquire() as c:
        existing = {
            r["qism_raqami"]
            for r in await c.fetch(
                "SELECT qism_raqami FROM episodes WHERE season_id=$1", season_id
            )
        }
        n = 1
        while n in existing:
            n += 1
        return n


async def db_create_episode(
    season_id: int, anime_id: int, qism_raqami: int, video_file_id: str, nomi: str = ""
):
    async with pool.acquire() as c:
        ep = await c.fetchrow(
            "INSERT INTO episodes(season_id,anime_id,qism_raqami,video_file_id,nomi)"
            " VALUES($1,$2,$3,$4,$5) RETURNING *",
            season_id, anime_id, qism_raqami, video_file_id, nomi,
        )
        await c.execute(
            "UPDATE animes SET joylangan_qismlar=joylangan_qismlar+1 WHERE id=$1", anime_id
        )
        return ep


# Per-season locks to serialise concurrent (forwarded) episode uploads so that
# the next episode number is computed and assigned atomically, preserving order.
_episode_locks: dict[int, asyncio.Lock] = {}


def _episode_lock(season_id: int) -> asyncio.Lock:
    lock = _episode_locks.get(season_id)
    if lock is None:
        lock = asyncio.Lock()
        _episode_locks[season_id] = lock
    return lock


async def db_append_episode(season_id: int, anime_id: int, video_file_id: str, nomi: str = ""):
    """Atomically compute the next qism_raqami and insert the episode.

    A per-season asyncio.Lock plus a single SQL statement that derives the
    next number from MAX(qism_raqami) guarantees correct sequential ordering
    even when many forwarded videos arrive almost simultaneously.
    """
    async with _episode_lock(season_id):
        async with pool.acquire() as c:
            async with c.transaction():
                ep = await c.fetchrow(
                    "INSERT INTO episodes(season_id,anime_id,qism_raqami,video_file_id,nomi) "
                    "VALUES($1,$2,"
                    "(SELECT COALESCE(MAX(qism_raqami),0)+1 FROM episodes WHERE season_id=$1),"
                    "$3,$4) RETURNING *",
                    season_id, anime_id, video_file_id, nomi,
                )
                await c.execute(
                    "UPDATE animes SET joylangan_qismlar=joylangan_qismlar+1 WHERE id=$1",
                    anime_id,
                )
            return ep


async def db_get_episodes(season_id: int):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT * FROM episodes WHERE season_id=$1 ORDER BY qism_raqami", season_id
        )


async def db_get_episode(eid: int):
    async with pool.acquire() as c:
        return await c.fetchrow("SELECT * FROM episodes WHERE id=$1", eid)


async def db_delete_episode(eid: int):
    async with pool.acquire() as c:
        ep = await c.fetchrow("SELECT * FROM episodes WHERE id=$1", eid)
        if ep:
            await c.execute("DELETE FROM episodes WHERE id=$1", eid)
            await c.execute(
                "UPDATE animes SET joylangan_qismlar=GREATEST(joylangan_qismlar-1,0) WHERE id=$1",
                ep["anime_id"],
            )
        return ep


# ──────────────────────────── DB: FAVORITES / WATCHLIST ─────────────────────

async def db_add_fav(uid: int, aid: int) -> bool:
    async with pool.acquire() as c:
        try:
            await c.execute("INSERT INTO favorites(user_id,anime_id) VALUES($1,$2)", uid, aid)
            return True
        except Exception:
            return False


async def db_remove_fav(uid: int, aid: int) -> None:
    async with pool.acquire() as c:
        await c.execute("DELETE FROM favorites WHERE user_id=$1 AND anime_id=$2", uid, aid)


async def db_get_favs(uid: int):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT a.* FROM animes a JOIN favorites f ON f.anime_id=a.id"
            " WHERE f.user_id=$1 ORDER BY f.created_at DESC",
            uid,
        )


async def db_is_fav(uid: int, aid: int) -> bool:
    async with pool.acquire() as c:
        return bool(
            await c.fetchrow("SELECT id FROM favorites WHERE user_id=$1 AND anime_id=$2", uid, aid)
        )


async def db_add_wl(uid: int, aid: int) -> bool:
    async with pool.acquire() as c:
        try:
            await c.execute("INSERT INTO watchlist(user_id,anime_id) VALUES($1,$2)", uid, aid)
            return True
        except Exception:
            return False


async def db_remove_wl(uid: int, aid: int) -> None:
    async with pool.acquire() as c:
        await c.execute("DELETE FROM watchlist WHERE user_id=$1 AND anime_id=$2", uid, aid)


async def db_get_wl(uid: int):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT a.* FROM animes a JOIN watchlist w ON w.anime_id=a.id WHERE w.user_id=$1", uid
        )


async def db_is_wl(uid: int, aid: int) -> bool:
    async with pool.acquire() as c:
        return bool(
            await c.fetchrow("SELECT id FROM watchlist WHERE user_id=$1 AND anime_id=$2", uid, aid)
        )


# ──────────────────────────── DB: RATINGS ───────────────────────────────────

async def db_add_rating(uid: int, aid: int, baho: float) -> None:
    async with pool.acquire() as c:
        await c.execute(
            "INSERT INTO ratings(user_id,anime_id,baho) VALUES($1,$2,$3)"
            " ON CONFLICT(user_id,anime_id) DO UPDATE SET baho=$3",
            uid, aid, baho,
        )
        r = await c.fetchrow(
            "SELECT AVG(baho) as avg, COUNT(*) as cnt FROM ratings WHERE anime_id=$1", aid
        )
        if r and r["avg"]:
            await c.execute(
                "UPDATE animes SET reyting=$1, reyting_count=$2 WHERE id=$3",
                round(float(r["avg"]), 1), r["cnt"], aid,
            )


async def db_get_user_rating(uid: int, aid: int):
    async with pool.acquire() as c:
        return await c.fetchrow(
            "SELECT * FROM ratings WHERE user_id=$1 AND anime_id=$2", uid, aid
        )


# ──────────────────────────── DB: COMMENTS ──────────────────────────────────

async def db_add_comment(uid: int, aid: int, matn: str) -> None:
    async with pool.acquire() as c:
        await c.execute(
            "INSERT INTO comments(user_id,anime_id,matn) VALUES($1,$2,$3)", uid, aid, matn
        )


async def db_get_comments(aid: int, limit: int = 10, offset: int = 0):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT c.*, u.ism, u.username FROM comments c"
            " JOIN users u ON u.telegram_id=c.user_id"
            " WHERE c.anime_id=$1 ORDER BY c.created_at DESC LIMIT $2 OFFSET $3",
            aid, limit, offset,
        )


async def db_count_comments(aid: int) -> int:
    async with pool.acquire() as c:
        return await c.fetchval("SELECT COUNT(*) FROM comments WHERE anime_id=$1", aid)


# ──────────────────────────── DB: PREMIUM REQUESTS ──────────────────────────

async def db_create_pr_req(uid: int, tarif: str, screenshot_id: str):
    async with pool.acquire() as c:
        return await c.fetchrow(
            "INSERT INTO premium_requests(user_id,tarif,screenshot_file_id)"
            " VALUES($1,$2,$3) RETURNING *",
            uid, tarif, screenshot_id,
        )


async def db_update_pr_req(rid: int, holati: str) -> None:
    async with pool.acquire() as c:
        await c.execute("UPDATE premium_requests SET holati=$1 WHERE id=$2", holati, rid)


async def db_get_pr_req(rid: int):
    async with pool.acquire() as c:
        return await c.fetchrow("SELECT * FROM premium_requests WHERE id=$1", rid)


# ──────────────────────────── DB: NOTIFICATIONS ─────────────────────────────

async def db_add_notif(uid: int, aid: int) -> bool:
    async with pool.acquire() as c:
        try:
            await c.execute(
                "INSERT INTO notifications(user_id,anime_id) VALUES($1,$2)", uid, aid
            )
            return True
        except Exception:
            return False


async def db_remove_notif(uid: int, aid: int) -> None:
    async with pool.acquire() as c:
        await c.execute(
            "DELETE FROM notifications WHERE user_id=$1 AND anime_id=$2", uid, aid
        )


async def db_notif_subs(aid: int):
    async with pool.acquire() as c:
        return await c.fetch(
            "SELECT u.telegram_id FROM users u"
            " JOIN notifications n ON n.user_id=u.telegram_id"
            " WHERE n.anime_id=$1 AND u.premium=TRUE AND u.is_blocked=FALSE",
            aid,
        )


async def db_is_notif(uid: int, aid: int) -> bool:
    async with pool.acquire() as c:
        return bool(
            await c.fetchrow(
                "SELECT id FROM notifications WHERE user_id=$1 AND anime_id=$2", uid, aid
            )
        )


# ──────────────────────────── HELPERS ───────────────────────────────────────

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


def is_super_admin(uid: int) -> bool:
    return uid in SUPER_ADMIN_IDS


async def is_premium(uid: int) -> bool:
    u = await db_get_user(uid)
    if not u or not u["premium"]:
        return False
    if u["premium_tugash"] and datetime.now() > u["premium_tugash"]:
        await db_update_user(uid, premium=False, premium_tugash=None)
        return False
    return True


async def check_sub(bot: Bot, uid: int) -> bool:
    try:
        m = await bot.get_chat_member(CHANNEL_ID, uid)
        return m.status not in ("left", "kicked", "banned")
    except Exception:
        return False


def tarif_days(tarif: str) -> int:
    return {"1oy": 30, "3oy": 90, "1yil": 365}.get(tarif, 30)


def tarif_label(tarif: str) -> str:
    return {
        "1oy": "1 oylik — 10,000 so'm",
        "3oy": "3 oylik — 27,000 so'm",
        "1yil": "1 yillik — 89,000 so'm",
    }.get(tarif, tarif)


def premium_end_date(tarif: str) -> datetime:
    return datetime.now() + timedelta(days=tarif_days(tarif))


def anime_card_text(a) -> str:
    status_icon = "✅" if a["holati"] == "Tugallangan" else "🔄"
    age         = a.get("yosh_chegarasi") or "Belgilanmagan"
    total       = a["qismlar_soni"] or 0
    uploaded    = a.get("joylangan_qismlar") or 0
    ep_text     = f"{total}/{uploaded} qism" if total > 0 else f"{uploaded} qism"
    return (
        f"🎬 <b>{a['nomi']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📁 Kod: <code>{a['kodi']}</code>\n"
        f"🎭 Janr: {a['janr']}\n"
        f"📅 Yil: {a['yil']}\n"
        f"🔞 Yosh: {age}\n"
        f"🗂 Fasllar: {a['fasllar_soni']}\n"
        f"📺 Qismlar: {ep_text}\n"
        f"{status_icon} Holati: {a['holati']}\n"
        f"⭐ Baho: {a['reyting']}/10 ({a['reyting_count']} ta)\n"
        f"👁 Ko'rishlar: {a['korish_soni']:,}\n"
        + (f"📝 {a['tavsif']}\n" if a['tavsif'] else "")
        + "\n<i>@Aniyoof</i>"
    )


def anime_edit_text(a) -> str:
    return (
        f"✏️ <b>{a['nomi']}</b>\n\n"
        f"📁 Kod: {a['kodi']}\n"
        f"🎭 Janr: {a['janr']}\n"
        f"📅 Yil: {a['yil']}\n"
        f"🔞 Yosh: {a.get('yosh_chegarasi') or '—'}\n"
        f"🗂 Fasllar: {a['fasllar_soni']}\n"
        f"📺 Qismlar: {a['qismlar_soni']}\n"
        f"🔄 Holat: {a['holati']}\n"
        f"📝 Tavsif: {a['tavsif'] or '—'}\n\n"
        "Qaysi maydonni o'zgartirmoqchisiz?"
    )


# ──────────────────────────── TRACE.MOE ─────────────────────────────────────

async def trace_moe_search(file_url: str) -> Optional[dict]:
    try:
        encoded = urllib.parse.quote(file_url, safe="")
        url     = f"https://api.trace.moe/search?url={encoded}&anilistInfo"
        async with aiohttp.ClientSession() as s:
            async with s.get(
                url,
                headers={"User-Agent": "AniyoofBot/1.0"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as r:
                if r.status != 200:
                    return None
                data = await r.json()
        if not data.get("result"):
            return None
        top        = data["result"][0]
        similarity = top.get("similarity", 0)
        if similarity < 0.60:
            return None
        anilist = top.get("anilistInfo", {})
        title   = (
            anilist.get("title", {}).get("romaji")
            or anilist.get("title", {}).get("english")
            or anilist.get("title", {}).get("native")
            or ""
        )
        return {
            "title":      title,
            "similarity": round(similarity * 100, 1),
            "episode":    top.get("episode"),
        }
    except asyncio.TimeoutError:
        log.warning("trace.moe timeout")
        return None
    except Exception as e:
        log.warning(f"trace.moe error: {e}")
        return None


# ──────────────────────────── KEYBOARDS ─────────────────────────────────────

def kb_main() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Anime izlash")],
            [KeyboardButton(text="💎 Premium olish"),  KeyboardButton(text="📢 Reklama berish")],
            [KeyboardButton(text="⭐ Reyting"),         KeyboardButton(text="❤️ Sevimlilar")],
            [KeyboardButton(text="👤 Profilim"),        KeyboardButton(text="📋 Watch list")],
            [KeyboardButton(text="📩 Murojat uchun")],
        ],
        resize_keyboard=True,
    )


def kb_admin() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Anime qo'shish")],
            [KeyboardButton(text="✏️ Anime tahrirlash"), KeyboardButton(text="✂️ Qism o'chirish")],
            [KeyboardButton(text="📝 Post yaratish")],
            [KeyboardButton(text="💎 Premium berish")],
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="📢 Xabar yuborish")],
            [KeyboardButton(text="👥 Admin boshqaruvi")],
            [KeyboardButton(text="👤 User paneliga o'tish")],
        ],
        resize_keyboard=True,
    )


def kb_cancel() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True
    )


def kb_skip() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ O'tkazib yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
    )


def kb_episode_upload() -> ReplyKeyboardMarkup:
    """Keyboard shown while the admin is uploading episodes one after another."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Tugatish")],
            [KeyboardButton(text="🏠 Bosh menyu")],
        ],
        resize_keyboard=True,
    )


def kb_phone() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Raqamni ulashish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ── Inline keyboards ──────────────────────────────────────────────────────────

def ik_back(cb: str = "back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data=cb)]]
    )


def ik_gender() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👦 Erkak", callback_data="gender_erkak"),
        InlineKeyboardButton(text="👧 Ayol",  callback_data="gender_ayol"),
    ]])


def ik_channel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"📢 {CHANNEL_USERNAME}",
            url="https://t.me/" + CHANNEL_USERNAME.lstrip("@"),
        )],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")],
    ])


def ik_search() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Nomi bilan",  callback_data="s_name"),
         InlineKeyboardButton(text="🔢 Kodi bilan",  callback_data="s_code")],
        [InlineKeyboardButton(text="🎭 Janr/Yil 💎", callback_data="s_janryil")],
        [InlineKeyboardButton(text="🖼 Rasm bilan 💎", callback_data="s_image"),
         InlineKeyboardButton(text="🎲 Tasodifiy",   callback_data="s_random")],
        [InlineKeyboardButton(text="🔥 Eng ko'p ko'rilgan 💎", callback_data="s_top")],
        [InlineKeyboardButton(text="🌟 Tavsiya",     callback_data="s_recommend")],
        [InlineKeyboardButton(text="🔙 Orqaga",      callback_data="back_main")],
    ])


def ik_janr_select(sel: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for j in GENRES:
        b.button(text=("✅ " if j in sel else "") + j, callback_data=f"seljanr_{j}")
    b.button(text="📅 Yil tanlash →", callback_data="goto_yil_sel")
    b.button(text="🔙 Orqaga",        callback_data="back_search")
    b.adjust(2)
    return b.as_markup()


def ik_yil_select(sel: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for y in YEARS:
        b.button(text=("✅ " if y in sel else "") + y, callback_data=f"selyil_{y}")
    b.button(text="🔍 Qidirish",      callback_data="do_janryil_search")
    b.button(text="🔙 Janrga qaytish", callback_data="goto_janr_sel")
    b.adjust(3)
    return b.as_markup()


def ik_anime_watch(aid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="▶️ Tomosha qilish", callback_data=f"watch_{aid}")
    ]])


def ik_anime_watch_channel(aid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="▶️ Tomosha qilish",
            url=f"https://t.me/{BOT_USERNAME}?start=anime_{aid}",
        )
    ]])


def ik_anime_extra(aid: int, is_fav: bool, is_wl: bool, is_notif: bool) -> InlineKeyboardMarkup:
    fav_label   = "💔 Sevimlilardan olish" if is_fav   else "❤️ Sevimlilarga"
    wl_label    = "📋 Watch listdan olish" if is_wl    else "📋 Watch list 💎"
    notif_label = "🔕 Bildirishnomani o'chirish" if is_notif else "🔔 Bildirishnoma 💎"
    notif_cb    = f"noff_{aid}" if is_notif else f"non_{aid}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=fav_label, callback_data=f"fav_{aid}"),
         InlineKeyboardButton(text=wl_label,  callback_data=f"wl_{aid}")],
        [InlineKeyboardButton(text="💬 Izohlar",     callback_data=f"cmt_{aid}_0"),
         InlineKeyboardButton(text="⭐ Baho berish", callback_data=f"rate_{aid}")],
        [InlineKeyboardButton(text=notif_label, callback_data=notif_cb)],
        [InlineKeyboardButton(text="🔙 Orqaga",       callback_data="back_search")],
    ])


def ik_anime_full(aid: int, is_fav: bool, is_wl: bool, is_notif: bool) -> InlineKeyboardMarkup:
    """Combined keyboard: Watch button + all extra buttons in a single message."""
    fav_label   = "💔 Sevimlilardan olish" if is_fav   else "❤️ Sevimlilarga"
    wl_label    = "📋 Watch listdan olish" if is_wl    else "📋 Watch list 💎"
    notif_label = "🔕 Bildirishnomani o'chirish" if is_notif else "🔔 Bildirishnoma 💎"
    notif_cb    = f"noff_{aid}" if is_notif else f"non_{aid}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Tomosha qilish", callback_data=f"watch_{aid}")],
        [InlineKeyboardButton(text=fav_label, callback_data=f"fav_{aid}"),
         InlineKeyboardButton(text=wl_label,  callback_data=f"wl_{aid}")],
        [InlineKeyboardButton(text="💬 Izohlar",     callback_data=f"cmt_{aid}_0"),
         InlineKeyboardButton(text="⭐ Baho berish", callback_data=f"rate_{aid}")],
        [InlineKeyboardButton(text=notif_label, callback_data=notif_cb)],
    ])


def ik_seasons(seasons, aid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in seasons:
        b.button(text=f"📂 {s['fasl_nomi']}", callback_data=f"ssn_{s['id']}_{aid}")
    b.button(text="🔙 Orqaga", callback_data=f"ac_{aid}")
    b.adjust(2)
    return b.as_markup()


def ik_episodes(eps, sid: int, aid: int, admin: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for e in eps:
        b.button(text=f"▶️ {e['qism_raqami']}-qism", callback_data=f"ep_{e['id']}")
    b.adjust(3)
    if eps:
        b.button(text="📦 Barchasini yuborish", callback_data=f"allep_{sid}")
    if admin:
        b.button(text="🗑 Qism o'chirish", callback_data=f"deleplist_{sid}_{aid}")
    b.button(text="🔙 Orqaga", callback_data=f"watch_{aid}")
    b.adjust(3)
    return b.as_markup()


def ik_episodes_delete(eps, sid: int, aid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for e in eps:
        b.button(
            text=f"🗑 {e['qism_raqami']}-qism",
            callback_data=f"delep_{e['id']}_{sid}_{aid}",
        )
    b.button(text="🔙 Orqaga", callback_data=f"ssn_{sid}_{aid}")
    b.adjust(2)
    return b.as_markup()


def ik_premium_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Bot orqali olish",   callback_data="pr_bot")],
        [InlineKeyboardButton(text="👤 Admin orqali olish", callback_data="pr_admin")],
        [InlineKeyboardButton(text="🔙 Orqaga",             callback_data="back_main")],
    ])


def ik_tarif() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 oy — 10,000 so'm",  callback_data="tarif_1oy")],
        [InlineKeyboardButton(text="3 oy — 27,000 so'm",  callback_data="tarif_3oy")],
        [InlineKeyboardButton(text="1 yil — 89,000 so'm", callback_data="tarif_1yil")],
        [InlineKeyboardButton(text="🔙 Orqaga",           callback_data="pr_menu")],
    ])


def ik_admin_pr(rid: int, uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"apr_{rid}_{uid}"),
        InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"rpr_{rid}_{uid}"),
    ]])


def ik_rating(aid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i in range(1, 11):
        star = "⭐" if i <= 5 else "🌟"
        b.button(text=f"{star} {i}", callback_data=f"rt_{aid}_{i}")
    b.button(text="🔙 Orqaga", callback_data=f"ac_{aid}")
    b.adjust(5)
    return b.as_markup()


def ik_comments(aid: int, offset: int, total: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if offset > 0:
        b.button(text="⬅️ Oldingi", callback_data=f"cmt_{aid}_{offset-10}")
    if offset + 10 < total:
        b.button(text="➡️ Keyingi", callback_data=f"cmt_{aid}_{offset+10}")
    b.button(text="✍️ Izoh yozish", callback_data=f"wcmt_{aid}")
    b.button(text="🔙 Orqaga",     callback_data=f"ac_{aid}")
    b.adjust(2)
    return b.as_markup()


def ik_reyting() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Eng ko'p ko'rganlar", callback_data="rtg_users")],
        [InlineKeyboardButton(text="🌟 Anime reytingi",      callback_data="rtg_anime")],
        [InlineKeyboardButton(text="🔙 Orqaga",              callback_data="back_main")],
    ])


def ik_profile() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Ismni o'zgartirish",         callback_data="ed_ism")],
        [InlineKeyboardButton(text="✏️ Yoshni o'zgartirish",        callback_data="ed_yosh")],
        [InlineKeyboardButton(text="✏️ Jinsni o'zgartirish",        callback_data="ed_jins")],
        [InlineKeyboardButton(text="✏️ Qiziqishlarni o'zgartirish", callback_data="ed_qiz")],
        [InlineKeyboardButton(text="🔙 Orqaga",                     callback_data="back_main")],
    ])


def ik_edit_gender() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👦 Erkak", callback_data="eg_erkak"),
        InlineKeyboardButton(text="👧 Ayol",  callback_data="eg_ayol"),
    ]])


def ik_premium_req() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Premium olish", callback_data="pr_menu")],
        [InlineKeyboardButton(text="🔙 Orqaga",        callback_data="back_search")],
    ])


def ik_admin_action(aid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 Qism qo'shish", callback_data=f"addep_{aid}")],
        [InlineKeyboardButton(text="📂 Fasl qo'shish", callback_data=f"addsn_{aid}")],
        [InlineKeyboardButton(text="🔙 Orqaga",        callback_data="adm_alist")],
    ])


def ik_admin_add() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi anime",       callback_data="adm_new")],
        [InlineKeyboardButton(text="📝 Davomini qo'shish", callback_data="adm_cont")],
        [InlineKeyboardButton(text="🔙 Orqaga",            callback_data="adm_back")],
    ])


def ik_seasons_ep(seasons, aid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in seasons:
        b.button(text=f"📂 {s['fasl_nomi']}", callback_data=f"sel_sn_{s['id']}_{aid}")
    b.button(text="🔙 Orqaga", callback_data=f"aa_{aid}")
    b.adjust(1)
    return b.as_markup()


def ik_admin_tarif() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 oy",  callback_data="gv_1oy")],
        [InlineKeyboardButton(text="3 oy",  callback_data="gv_3oy")],
        [InlineKeyboardButton(text="1 yil", callback_data="gv_1yil")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm_back")],
    ])


def ik_admins_contact() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for u in ADMIN_USERNAMES:
        u = u.strip()
        clean_u = u.lstrip("@")
        b.button(text=f"👤 {u}", url=f"https://t.me/{clean_u}")
    b.button(text="🔙 Orqaga", callback_data="pr_menu")
    b.adjust(1)
    return b.as_markup()


def ik_confirm_bc() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash",   callback_data="bc_yes"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bc_no"),
    ]])


def ik_bc_target() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Barcha userlar",      callback_data="bc_all")],
        [InlineKeyboardButton(text="💎 Faqat premiumlar",    callback_data="bc_premium")],
        [InlineKeyboardButton(text="👤 Faqat oddiy userlar", callback_data="bc_free")],
        [InlineKeyboardButton(text="🔙 Bekor qilish",        callback_data="adm_back")],
    ])


def ik_anime_edit_fields(aid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📛 Nomi",           callback_data=f"efield_nomi_{aid}"),
         InlineKeyboardButton(text="📁 Kodi",           callback_data=f"efield_kodi_{aid}")],
        [InlineKeyboardButton(text="🎭 Janri",          callback_data=f"efield_janr_{aid}"),
         InlineKeyboardButton(text="📅 Yili",           callback_data=f"efield_yil_{aid}")],
        [InlineKeyboardButton(text="🗂 Fasllar soni",   callback_data=f"efield_fasllar_{aid}"),
         InlineKeyboardButton(text="📺 Qismlar soni",   callback_data=f"efield_qismlar_{aid}")],
        [InlineKeyboardButton(text="🔄 Holati",         callback_data=f"efield_holati_{aid}"),
         InlineKeyboardButton(text="📝 Tavsif",         callback_data=f"efield_tavsif_{aid}")],
        [InlineKeyboardButton(text="🔞 Yosh chegarasi", callback_data=f"efield_yosh_{aid}")],
        [InlineKeyboardButton(text="🖼 Rasm/Video",     callback_data=f"efield_media_{aid}")],
        [InlineKeyboardButton(text="🗑 Animeni o'chirish", callback_data=f"delanime_{aid}")],
        [InlineKeyboardButton(text="🔙 Orqaga",         callback_data="adm_back")],
    ])


def ik_holati_select(aid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Davom etmoqda", callback_data=f"setholati_davom_{aid}"),
         InlineKeyboardButton(text="✅ Tugallangan",   callback_data=f"setholati_tugal_{aid}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"editanim_{aid}")],
    ])


def ik_yosh_select(aid: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for y in AGE_RATINGS:
        cb_val = y.replace("+", "plus")
        b.button(text=y, callback_data=f"setyosh_{cb_val}_{aid}")
    b.button(text="🔙 Orqaga", callback_data=f"editanim_{aid}")
    b.adjust(3)
    return b.as_markup()


def ik_confirm_del(aid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"confirmdel_{aid}"),
        InlineKeyboardButton(text="❌ Yo'q",       callback_data=f"editanim_{aid}"),
    ]])


def ik_admin_mgmt() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Admin qo'shish",   callback_data="adm_add")],
        [InlineKeyboardButton(text="📋 Adminlar ro'yxati", callback_data="adm_list_view")],
        [InlineKeyboardButton(text="🗑 Admin o'chirish",   callback_data="adm_remove")],
        [InlineKeyboardButton(text="🔙 Orqaga",            callback_data="adm_back")],
    ])


# ──────────────────────────── FSM STATES ────────────────────────────────────

class Reg(StatesGroup):
    ism = State(); yosh = State(); jins = State(); qiziqish = State(); raqam = State()

class Search(StatesGroup):
    name = State(); code = State(); image = State()

class PremiumPay(StatesGroup):
    screenshot = State()

class EditProfile(StatesGroup):
    ism = State(); yosh = State(); qiziqish = State()

class CommentW(StatesGroup):
    write = State()

class Contact(StatesGroup):
    msg = State()

class AddAnime(StatesGroup):
    info = State(); media = State()

class AddSeason(StatesGroup):
    name = State()

class AddEpisode(StatesGroup):
    sel_season = State(); video = State()

class AdminPremium(StatesGroup):
    find = State(); tarif = State()

class Broadcast(StatesGroup):
    msg = State(); target = State(); confirm = State()

class CreatePost(StatesGroup):
    media = State(); caption = State(); anime_sel = State()

class EditAnime(StatesGroup):
    value = State(); media = State()

class AdminMgmt(StatesGroup):
    add_id = State(); remove_id = State()

# ──────────────────────────── ROUTER ────────────────────────────────────────

router = Router()

# ── util ──────────────────────────────────────────────────────────────────────

async def send_anime_card(target: Message, anime, uid: int) -> None:
    fav   = await db_is_fav(uid, anime["id"])
    wl    = await db_is_wl(uid, anime["id"])
    notif = await db_is_notif(uid, anime["id"])
    txt   = anime_card_text(anime)
    kb    = ik_anime_full(anime["id"], fav, wl, notif)
    try:
        if anime["media_type"] == "video":
            await target.answer_video(
                anime["media_file_id"], caption=txt,
                reply_markup=kb, parse_mode="HTML",
            )
        else:
            await target.answer_photo(
                anime["media_file_id"], caption=txt,
                reply_markup=kb, parse_mode="HTML",
            )
    except Exception:
        await target.answer(txt, reply_markup=kb, parse_mode="HTML")


async def premium_gate(cb: CallbackQuery) -> bool:
    """Returns True if user has premium; otherwise shows paywall and returns False."""
    if await is_premium(cb.from_user.id):
        return True
    await cb.message.edit_text(
        "⚠️ Bu funksiya faqat 💎 <b>Premium</b> foydalanuvchilar uchun!",
        reply_markup=ik_premium_req(),
        parse_mode="HTML",
    )
    return False


# ──────────────────────────── /start ────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    uid   = msg.from_user.id
    uname = msg.from_user.username

    # Deep-link ?start=anime_<id>
    args         = (msg.text or "").split()
    anime_id_arg = None
    if len(args) > 1 and args[1].startswith("anime_"):
        try:
            anime_id_arg = int(args[1].split("_")[1])
        except ValueError:
            pass

    await db_create_user(uid, uname)

    if is_admin(uid):
        await msg.answer("👑 Xush kelibsiz, Admin!", reply_markup=kb_admin())
        if anime_id_arg:
            a = await db_get_anime(anime_id_arg)
            if a:
                await send_anime_card(msg, a, uid)
        return

    user = await db_get_user(uid)
    if not user or not user["ism"]:
        if anime_id_arg:
            await state.update_data(pending_anime=anime_id_arg)
        await state.set_state(Reg.ism)
        await msg.answer(
            "👋 Xush kelibsiz!\n\n📝 <b>Ismingizni kiriting:</b>",
            parse_mode="HTML", reply_markup=kb_cancel(),
        )
        return

    if not await check_sub(bot, uid):
        if anime_id_arg:
            await state.update_data(pending_anime=anime_id_arg)
        await msg.answer(
            f"📢 Kanalga obuna bo'ling!\n\n<b>{CHANNEL_USERNAME}</b>",
            reply_markup=ik_channel(), parse_mode="HTML",
        )
        return

    await msg.answer(
        f"🌸 Xush kelibsiz, <b>{user['ism']}</b>! 🎌",
        reply_markup=kb_main(), parse_mode="HTML",
    )
    if anime_id_arg:
        a = await db_get_anime(anime_id_arg)
        if a:
            await send_anime_card(msg, a, uid)


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(cb: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not await check_sub(bot, cb.from_user.id):
        await cb.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
        return
    user = await db_get_user(cb.from_user.id)
    d    = await state.get_data()
    pending = d.get("pending_anime")
    try:
        await cb.message.delete()
    except Exception:
        pass
    if not user or not user["ism"]:
        await state.set_state(Reg.ism)
        await cb.message.answer(
            "📝 <b>Ismingizni kiriting:</b>", parse_mode="HTML", reply_markup=kb_cancel()
        )
        return
    await state.clear()
    await cb.message.answer(
        f"✅ Xush kelibsiz, <b>{user['ism']}</b>! 🎌",
        reply_markup=kb_main(), parse_mode="HTML",
    )
    if pending:
        a = await db_get_anime(pending)
        if a:
            await send_anime_card(cb.message, a, cb.from_user.id)


@router.callback_query(F.data == "back_main")
async def cb_back_main(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await cb.message.delete()
    except Exception:
        pass
    await cb.message.answer("🏠 Bosh menyu", reply_markup=kb_main())


# ──────────────────────────── REGISTRATION ──────────────────────────────────

@router.message(Reg.ism)
async def reg_ism(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear()
        await msg.answer("❌", reply_markup=kb_main())
        return
    if not msg.text or len(msg.text.strip()) < 2:
        await msg.answer("❌ To'g'ri ism kiriting (kamida 2 harf).")
        return
    await state.update_data(ism=msg.text.strip())
    await state.set_state(Reg.yosh)
    await msg.answer("🎂 <b>Yoshingizni kiriting:</b>", parse_mode="HTML")


@router.message(Reg.yosh)
async def reg_yosh(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear()
        await msg.answer("❌", reply_markup=kb_main())
        return
    try:
        y = int(msg.text.strip())
        assert 5 <= y <= 100
    except (ValueError, AssertionError):
        await msg.answer("❌ To'g'ri yosh kiriting (5–100).")
        return
    await state.update_data(yosh=y)
    await state.set_state(Reg.jins)
    await msg.answer("⚧ <b>Jinsingizni tanlang:</b>", parse_mode="HTML", reply_markup=ik_gender())


@router.callback_query(F.data.in_({"gender_erkak", "gender_ayol"}), Reg.jins)
async def reg_jins(cb: CallbackQuery, state: FSMContext) -> None:
    jins = "Erkak" if cb.data == "gender_erkak" else "Ayol"
    await state.update_data(jins=jins)
    await state.set_state(Reg.qiziqish)
    await cb.message.edit_text(f"✅ Jins: <b>{jins}</b>", parse_mode="HTML")
    await cb.message.answer(
        "🎭 <b>Qiziqishlaringiz</b> (ixtiyoriy):",
        parse_mode="HTML", reply_markup=kb_skip(),
    )


@router.message(Reg.qiziqish)
async def reg_qiziqish(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear()
        await msg.answer("❌", reply_markup=kb_main())
        return
    q = "" if msg.text == "⏭ O'tkazib yuborish" else (msg.text or "").strip()
    await state.update_data(qiziqish=q)
    await state.set_state(Reg.raqam)
    await msg.answer(
        "📱 <b>Telefon raqamingizni ulashing:</b>", parse_mode="HTML", reply_markup=kb_phone()
    )


@router.message(Reg.raqam, F.contact)
async def reg_raqam(msg: Message, state: FSMContext, bot: Bot) -> None:
    uname = msg.from_user.username
    if not uname:
        await msg.answer(
            "⚠️ Username yo'q! Telegram sozlamalaridan username qo'ying, keyin /start bosing.",
            reply_markup=kb_cancel(),
        )
        await state.clear()
        return
    raqam = msg.contact.phone_number
    d     = await state.get_data()
    await db_update_user(
        msg.from_user.id,
        ism=d["ism"], yosh=d["yosh"], jins=d["jins"],
        qiziqishlar=d.get("qiziqish", ""),
        raqam=raqam, username=uname,
    )
    pending = d.get("pending_anime")
    await state.clear()

    if not await check_sub(bot, msg.from_user.id):
        await msg.answer(
            f"✅ Ro'yxatdan o'tdingiz!\n\n📢 Kanalga obuna bo'ling:\n<b>{CHANNEL_USERNAME}</b>",
            reply_markup=ik_channel(), parse_mode="HTML",
        )
        return
    await msg.answer(
        f"✅ Xush kelibsiz, <b>{d['ism']}</b>! 🎌",
        reply_markup=kb_main(), parse_mode="HTML",
    )
    if pending:
        a = await db_get_anime(pending)
        if a:
            await send_anime_card(msg, a, msg.from_user.id)


@router.message(Reg.raqam)
async def reg_raqam_wrong(msg: Message) -> None:
    if msg.text != "❌ Bekor qilish":
        await msg.answer("📱 Raqamni ulashish tugmasini bosing.", reply_markup=kb_phone())


# ──────────────────────────── MAIN MENU ─────────────────────────────────────

@router.message(F.text == "🔍 Anime izlash")
async def menu_search(msg: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    if not await check_sub(bot, msg.from_user.id):
        await msg.answer("📢 Avval kanalga obuna bo'ling!", reply_markup=ik_channel())
        return
    await msg.answer("🔍 <b>Anime izlash</b>", reply_markup=ik_search(), parse_mode="HTML")


@router.message(F.text == "💎 Premium olish")
async def menu_premium(msg: Message) -> None:
    await msg.answer(
        "💎 <b>Aniyoof Premium</b>\n\n"
        "✅ Janr/Yil bilan qidirish\n"
        "✅ Rasm orqali qidirish\n"
        "✅ Eng ko'p ko'rilgan\n"
        "✅ Watch list\n"
        "✅ Bildirishnomalar\n\nTanlang:",
        reply_markup=ik_premium_menu(), parse_mode="HTML",
    )


@router.message(F.text == "📢 Reklama berish")
async def menu_reklama(msg: Message) -> None:
    await msg.answer(f"📢 Reklama uchun: {ADVERTISER_UN}", reply_markup=kb_main())


@router.message(F.text == "⭐ Reyting")
async def menu_reyting(msg: Message) -> None:
    await msg.answer("⭐ <b>Reyting</b>", reply_markup=ik_reyting(), parse_mode="HTML")


@router.message(F.text == "❤️ Sevimlilar")
async def menu_favs(msg: Message) -> None:
    favs = await db_get_favs(msg.from_user.id)
    if not favs:
        await msg.answer("❤️ Sevimlilar bo'sh.", reply_markup=kb_main())
        return
    b = InlineKeyboardBuilder()
    for a in favs:
        b.button(text=f"🎬 {a['nomi']}", callback_data=f"ac_{a['id']}")
    b.button(text="🔙 Orqaga", callback_data="back_main")
    b.adjust(1)
    await msg.answer(
        f"❤️ <b>Sevimlilar ({len(favs)} ta):</b>",
        reply_markup=b.as_markup(), parse_mode="HTML",
    )


@router.message(F.text == "📋 Watch list")
async def menu_watchlist(msg: Message) -> None:
    if not await is_premium(msg.from_user.id):
        await msg.answer("⚠️ Faqat 💎 <b>Premium</b> uchun!", parse_mode="HTML", reply_markup=kb_main())
        return
    wl = await db_get_wl(msg.from_user.id)
    if not wl:
        await msg.answer("📋 Watch list bo'sh.", reply_markup=kb_main())
        return
    b = InlineKeyboardBuilder()
    for a in wl:
        b.button(text=f"🎬 {a['nomi']}", callback_data=f"ac_{a['id']}")
    b.button(text="🔙 Orqaga", callback_data="back_main")
    b.adjust(1)
    await msg.answer(
        f"📋 <b>Watch list ({len(wl)} ta):</b>",
        reply_markup=b.as_markup(), parse_mode="HTML",
    )


@router.message(F.text == "📩 Murojat uchun")
async def menu_contact(msg: Message, state: FSMContext) -> None:
    await state.set_state(Contact.msg)
    await msg.answer("📩 Murojatingizni yozing:", reply_markup=kb_cancel())


@router.message(Contact.msg)
async def contact_send(msg: Message, state: FSMContext, bot: Bot) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear()
        await msg.answer("❌", reply_markup=kb_main())
        return
    u    = await db_get_user(msg.from_user.id)
    name = u["ism"] if u else "?"
    un   = f"@{msg.from_user.username}" if msg.from_user.username else "yo'q"
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"📩 <b>Murojat</b>\n👤 {name} ({un})\n🆔 {msg.from_user.id}\n\n{msg.text}",
                parse_mode="HTML",
            )
        except Exception:
            pass
    await state.clear()
    await msg.answer("✅ Murojat yuborildi!", reply_markup=kb_main())


# ──────────────────────────── PROFILE ───────────────────────────────────────

@router.message(F.text == "👤 Profilim")
async def menu_profile(msg: Message) -> None:
    u = await db_get_user(msg.from_user.id)
    if not u:
        await msg.answer("❌")
        return
    rank = await db_user_rank(msg.from_user.id)
    pr   = "✅ Faol" if u["premium"] else "❌ Yo'q"
    pe   = (
        "\n⏰ Tugash: " + u['premium_tugash'].strftime("%d.%m.%Y")
        if u["premium"] and u["premium_tugash"]
        else ""
    )
    await msg.answer(
        f"👤 <b>Profilim</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📛 Ism: <b>{u['ism'] or '—'}</b>\n"
        f"🎂 Yosh: <b>{u['yosh'] or '—'}</b>\n"
        f"⚧ Jins: <b>{u['jins'] or '—'}</b>\n"
        f"🎭 Qiziqishlar: <b>{u['qiziqishlar'] or '—'}</b>\n"
        f"💎 Premium: {pr}{pe}\n"
        f"🏆 Ko'rish reytingi: <b>{rank}-o'rin</b>\n"
        f"👁 Ko'rgan: <b>{u['korgan_count'] or 0} ta</b>",
        reply_markup=ik_profile(), parse_mode="HTML",
    )


@router.callback_query(F.data == "ed_ism")
async def ed_ism_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(EditProfile.ism)
    await cb.message.answer("📝 Yangi ismingizni kiriting:", reply_markup=kb_cancel())


@router.message(EditProfile.ism)
async def ed_ism(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_main()); return
    await db_update_user(msg.from_user.id, ism=msg.text.strip())
    await state.clear()
    await msg.answer("✅ Ism yangilandi!", reply_markup=kb_main())


@router.callback_query(F.data == "ed_yosh")
async def ed_yosh_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(EditProfile.yosh)
    await cb.message.answer("🎂 Yangi yoshingizni kiriting:", reply_markup=kb_cancel())


@router.message(EditProfile.yosh)
async def ed_yosh(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_main()); return
    try:
        y = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Raqamda kiriting."); return
    await db_update_user(msg.from_user.id, yosh=y)
    await state.clear()
    await msg.answer("✅ Yosh yangilandi!", reply_markup=kb_main())


@router.callback_query(F.data == "ed_jins")
async def ed_jins_start(cb: CallbackQuery) -> None:
    await cb.message.answer("⚧ Yangi jinsni tanlang:", reply_markup=ik_edit_gender())


@router.callback_query(F.data.in_({"eg_erkak", "eg_ayol"}))
async def ed_jins(cb: CallbackQuery) -> None:
    j = "Erkak" if "erkak" in cb.data else "Ayol"
    await db_update_user(cb.from_user.id, jins=j)
    await cb.message.edit_text(f"✅ Jins yangilandi: <b>{j}</b>", parse_mode="HTML")
    await cb.message.answer("🏠 Bosh menyu", reply_markup=kb_main())


@router.callback_query(F.data == "ed_qiz")
async def ed_qiz_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(EditProfile.qiziqish)
    await cb.message.answer("🎭 Yangi qiziqishlarni kiriting:", reply_markup=kb_cancel())


@router.message(EditProfile.qiziqish)
async def ed_qiziqish(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_main()); return
    await db_update_user(msg.from_user.id, qiziqishlar=msg.text.strip())
    await state.clear()
    await msg.answer("✅ Qiziqishlar yangilandi!", reply_markup=kb_main())


# ──────────────────────────── RATING BOARD ──────────────────────────────────

@router.callback_query(F.data == "rtg_users")
async def cb_rtg_users(cb: CallbackQuery) -> None:
    top  = await db_top_watchers(20)
    uid  = cb.from_user.id
    rank = await db_user_rank(uid)
    t    = "🏆 <b>Eng ko'p ko'rganlar:</b>\n━━━━━━━━━━━━━━━━\n"
    for i, u in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        name  = u["ism"] or u["username"] or "?"
        me    = " 👈 Siz" if u["telegram_id"] == uid else ""
        t    += f"{medal} {name} — {u['korgan_count']} ta{me}\n"
    if rank > 20:
        t += f"\n📍 Sizning o'rningiz: <b>{rank}-o'rin</b>"
    await cb.message.edit_text(t, reply_markup=ik_back("back_main"), parse_mode="HTML")


@router.callback_query(F.data == "rtg_anime")
async def cb_rtg_anime(cb: CallbackQuery) -> None:
    top = await db_top_rating(20)
    t   = "🌟 <b>Top animelar (baho):</b>\n━━━━━━━━━━━━━━━━\n"
    for i, a in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        t    += f"{medal} {a['nomi']} — ⭐{a['reyting']}/10\n"
    if not top:
        t += "Hali baho berilmagan."
    await cb.message.edit_text(t, reply_markup=ik_back("back_main"), parse_mode="HTML")


# ──────────────────────────── SEARCH ────────────────────────────────────────

@router.callback_query(F.data == "back_search")
async def cb_back_search(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await cb.message.edit_text("🔍 <b>Anime izlash</b>", reply_markup=ik_search(), parse_mode="HTML")
    except Exception:
        await cb.message.answer("🔍 <b>Anime izlash</b>", reply_markup=ik_search(), parse_mode="HTML")


@router.callback_query(F.data == "s_name")
async def s_name_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Search.name)
    await cb.message.edit_text("📝 Anime nomini kiriting:", reply_markup=ik_back("back_search"))


@router.message(Search.name)
async def s_name(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("🏠", reply_markup=kb_main()); return
    res = await db_search_anime_name(msg.text.strip())
    await state.clear()
    if not res:
        b = InlineKeyboardBuilder()
        b.button(text="🔙 Orqaga", callback_data="back_search")
        await msg.answer("❌ Anime topilmadi.", reply_markup=b.as_markup())
        return
    if len(res) == 1:
        await send_anime_card(msg, res[0], msg.from_user.id)
        return
    b = InlineKeyboardBuilder()
    for a in res:
        b.button(text=f"🎬 {a['nomi']}", callback_data=f"ac_{a['id']}")
    b.button(text="🔙 Orqaga", callback_data="back_search")
    b.adjust(1)
    await msg.answer(f"🔍 <b>{len(res)} ta topildi:</b>", reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "s_code")
async def s_code_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Search.code)
    await cb.message.edit_text("🔢 Anime kodini kiriting:", reply_markup=ik_back("back_search"))


@router.message(Search.code)
async def s_code(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("🏠", reply_markup=kb_main()); return
    a = await db_get_anime_by_code(msg.text.strip())
    await state.clear()
    if not a:
        b = InlineKeyboardBuilder()
        b.button(text="🔙 Orqaga", callback_data="back_search")
        await msg.answer("❌ Bu kodda anime topilmadi.", reply_markup=b.as_markup())
        return
    await send_anime_card(msg, a, msg.from_user.id)


@router.callback_query(F.data == "s_image")
async def s_image_start(cb: CallbackQuery, state: FSMContext) -> None:
    if not await premium_gate(cb):
        return
    await state.set_state(Search.image)
    await cb.message.edit_text(
        "🖼 <b>Rasm orqali qidirish</b>\n\n"
        "Anime screenshotini yuboring.\n"
        "⚠️ Faqat anime kadr (screenshot) larida ishlaydi.\n"
        "📸 Sifatli va aniq rasm yuboring.",
        reply_markup=ik_back("back_search"), parse_mode="HTML",
    )


@router.message(Search.image, F.photo)
async def s_image(msg: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    wait = await msg.answer("🔍 Qidirilyapti... ⏳")
    try:
        file     = await bot.get_file(msg.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    except Exception:
        try:
            await wait.delete()
        except Exception:
            pass
        await msg.answer("❌ Rasm yuklanmadi.")
        return

    result = await trace_moe_search(file_url)
    try:
        await wait.delete()
    except Exception:
        pass

    if not result:
        b = InlineKeyboardBuilder()
        b.button(text="🔙 Orqaga", callback_data="back_search")
        await msg.answer(
            "❌ <b>Anime aniqlanmadi.</b>\n\n"
            "• Rasm sifati past bo'lishi mumkin\n"
            "• trace.moe bazasida yo'q\n\n"
            "Boshqa rasm yuboring.",
            reply_markup=b.as_markup(), parse_mode="HTML",
        )
        return

    title      = result["title"]
    similarity = result["similarity"]
    ep_info    = f" | {result['episode']}-qism" if result.get('episode') else ""

    res = await db_search_anime_name(title)
    if not res:
        first = title.split()[0] if title else ""
        if len(first) > 3:
            res = await db_search_anime_name(first)

    if not res:
        b = InlineKeyboardBuilder()
        b.button(text="🔙 Orqaga", callback_data="back_search")
        await msg.answer(
            f"🎬 <b>Aniqlandi:</b> {title} ({similarity}%{ep_info})\n\n"
            "❌ Lekin bazamizda bu anime hali yo'q.",
            reply_markup=b.as_markup(), parse_mode="HTML",
        )
        return

    if len(res) == 1:
        await msg.answer(f"✅ <b>Aniqlandi:</b> {title} ({similarity}%{ep_info})", parse_mode="HTML")
        await send_anime_card(msg, res[0], msg.from_user.id)
        return

    b = InlineKeyboardBuilder()
    for a in res:
        b.button(text=f"🎬 {a['nomi']}", callback_data=f"ac_{a['id']}")
    b.button(text="🔙 Orqaga", callback_data="back_search")
    b.adjust(1)
    await msg.answer(
        f"✅ <b>Aniqlandi:</b> {title} ({similarity}%{ep_info})\n🔍 {len(res)} ta natija:",
        reply_markup=b.as_markup(), parse_mode="HTML",
    )


@router.message(Search.image)
async def s_image_wrong(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("🏠", reply_markup=kb_main()); return
    await msg.answer("📸 Iltimos rasm (screenshot) yuboring!")


# ── Janr / Yil ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "s_janryil")
async def s_janryil(cb: CallbackQuery, state: FSMContext) -> None:
    if not await premium_gate(cb):
        return
    await state.update_data(sel_janrlar=[], sel_yillar=[])
    await cb.message.edit_text(
        "🎭 <b>Janrlarni tanlang:</b>", reply_markup=ik_janr_select([]), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("seljanr_"))
async def cb_seljanr(cb: CallbackQuery, state: FSMContext) -> None:
    janr = cb.data.replace("seljanr_", "")
    d    = await state.get_data()
    sel  = d.get("sel_janrlar", [])
    if janr in sel:
        sel.remove(janr)
    else:
        sel.append(janr)
    await state.update_data(sel_janrlar=sel)
    try:
        await cb.message.edit_reply_markup(reply_markup=ik_janr_select(sel))
    except Exception:
        pass
    await cb.answer(("✅ " if janr in sel else "❌ ") + janr)


@router.callback_query(F.data == "goto_yil_sel")
async def cb_goto_yil(cb: CallbackQuery, state: FSMContext) -> None:
    d = await state.get_data()
    await cb.message.edit_text(
        "📅 <b>Yillarni tanlang:</b>",
        reply_markup=ik_yil_select(d.get("sel_yillar", [])), parse_mode="HTML",
    )


@router.callback_query(F.data == "goto_janr_sel")
async def cb_goto_janr(cb: CallbackQuery, state: FSMContext) -> None:
    d = await state.get_data()
    await cb.message.edit_text(
        "🎭 <b>Janrlarni tanlang:</b>",
        reply_markup=ik_janr_select(d.get("sel_janrlar", [])), parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("selyil_"))
async def cb_selyil(cb: CallbackQuery, state: FSMContext) -> None:
    yil = cb.data.replace("selyil_", "")
    d   = await state.get_data()
    sel = d.get("sel_yillar", [])
    if yil in sel:
        sel.remove(yil)
    else:
        sel.append(yil)
    await state.update_data(sel_yillar=sel)
    try:
        await cb.message.edit_reply_markup(reply_markup=ik_yil_select(sel))
    except Exception:
        pass
    await cb.answer(("✅ " if yil in sel else "❌ ") + yil)


@router.callback_query(F.data == "do_janryil_search")
async def cb_do_janryil_search(cb: CallbackQuery, state: FSMContext) -> None:
    d           = await state.get_data()
    sel_janrlar = d.get("sel_janrlar", [])
    sel_yillar  = d.get("sel_yillar", [])
    await state.clear()
    if not sel_janrlar and not sel_yillar:
        await cb.answer("❗ Kamida 1 ta janr yoki yil tanlang!", show_alert=True)
        return
    results: list = []
    combos = [
        (j, y)
        for j in (sel_janrlar or [None])
        for y in (sel_yillar  or [None])
    ]
    for janr, yil in combos:
        for r in await db_search_genre_year(janr, yil):
            if not any(x["id"] == r["id"] for x in results):
                results.append(r)
    if not results:
        await cb.message.edit_text("❌ Hech narsa topilmadi.", reply_markup=ik_back("back_search"))
        return
    if len(results) == 1:
        try:
            await cb.message.delete()
        except Exception:
            pass
        await send_anime_card(cb.message, results[0], cb.from_user.id)
        return
    b = InlineKeyboardBuilder()
    for a in results[:20]:
        b.button(text=f"🎬 {a['nomi']}", callback_data=f"ac_{a['id']}")
    b.button(text="🔙 Orqaga", callback_data="back_search")
    b.adjust(1)
    janr_txt = ", ".join(sel_janrlar) or "—"
    yil_txt  = ", ".join(sel_yillar)  or "—"
    await cb.message.edit_text(
        f"🔍 <b>{len(results)} ta topildi</b>\n"
        f"🎭 {janr_txt}\n"
        f"📅 {yil_txt}",
        reply_markup=b.as_markup(), parse_mode="HTML",
    )


@router.callback_query(F.data == "s_random")
async def s_random(cb: CallbackQuery) -> None:
    a = await db_random_anime()
    if not a:
        await cb.answer("❌ Hali anime yo'q!", show_alert=True)
        return
    try:
        await cb.message.delete()
    except Exception:
        pass
    await send_anime_card(cb.message, a, cb.from_user.id)


@router.callback_query(F.data == "s_top")
async def s_top(cb: CallbackQuery) -> None:
    if not await premium_gate(cb):
        return
    top = await db_top_views(10)
    b   = InlineKeyboardBuilder()
    for i, a in enumerate(top, 1):
        b.button(
            text=f"{i}. 🎬 {a['nomi']} 👁{a['korish_soni']}",
            callback_data=f"ac_{a['id']}",
        )
    b.button(text="🔙 Orqaga", callback_data="back_search")
    b.adjust(1)
    await cb.message.edit_text(
        "🔥 <b>Eng ko'p ko'rilgan:</b>", reply_markup=b.as_markup(), parse_mode="HTML"
    )


@router.callback_query(F.data == "s_recommend")
async def s_recommend(cb: CallbackQuery) -> None:
    u    = await db_get_user(cb.from_user.id)
    janr = (u["qiziqishlar"] or "Aksyon") if u else "Aksyon"
    res  = await db_recommended(janr, 5) or await db_top_rating(5)
    b    = InlineKeyboardBuilder()
    for a in res:
        b.button(text=f"🎬 {a['nomi']}", callback_data=f"ac_{a['id']}")
    b.button(text="🔙 Orqaga", callback_data="back_search")
    b.adjust(1)
    await cb.message.edit_text(
        f"🌟 <b>Tavsiyalar ({janr}):</b>", reply_markup=b.as_markup(), parse_mode="HTML"
    )


# ──────────────────────────── ANIME CARD & WATCH ────────────────────────────

@router.callback_query(F.data.startswith("ac_"))
async def cb_anime_card(cb: CallbackQuery) -> None:
    aid = int(cb.data.split("_")[1])
    a   = await db_get_anime(aid)
    if not a:
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    try:
        await cb.message.delete()
    except Exception:
        pass
    await send_anime_card(cb.message, a, cb.from_user.id)


@router.callback_query(F.data.startswith("watch_"))
async def cb_watch(cb: CallbackQuery) -> None:
    aid     = int(cb.data.split("_")[1])
    seasons = await db_get_seasons(aid)
    if not seasons:
        await cb.answer("❌ Hali fasl qo'shilmagan!", show_alert=True)
        return
    await db_inc_views(aid)
    u = await db_get_user(cb.from_user.id)
    await db_update_user(cb.from_user.id, korgan_count=(u["korgan_count"] or 0) + 1)
    try:
        await cb.message.edit_reply_markup(reply_markup=ik_seasons(seasons, aid))
    except Exception:
        await cb.message.answer("📂 Faslni tanlang:", reply_markup=ik_seasons(seasons, aid))


@router.callback_query(F.data.startswith("ssn_"))
async def cb_season(cb: CallbackQuery) -> None:
    parts       = cb.data.split("_")
    sid, aid    = int(parts[1]), int(parts[2])
    eps         = await db_get_episodes(sid)
    if not eps:
        await cb.answer("❌ Bu faslda qism yo'q!", show_alert=True)
        return
    admin = is_admin(cb.from_user.id)
    try:
        await cb.message.edit_reply_markup(reply_markup=ik_episodes(eps, sid, aid, admin))
    except Exception:
        await cb.message.answer("📺 Qismni tanlang:", reply_markup=ik_episodes(eps, sid, aid, admin))


@router.callback_query(F.data.startswith("ep_"))
async def cb_episode(cb: CallbackQuery, bot: Bot) -> None:
    eid = int(cb.data.split("_")[1])
    ep  = await db_get_episode(eid)
    if not ep:
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    await cb.answer()
    await bot.send_video(
        cb.from_user.id, video=ep["video_file_id"],
        caption=f"▶️ {ep['qism_raqami']}-qism\n\n@Aniyoof",
    )


@router.callback_query(F.data.startswith("allep_"))
async def cb_all_episodes(cb: CallbackQuery, bot: Bot) -> None:
    sid = int(cb.data.split("_")[1])
    eps = await db_get_episodes(sid)
    if not eps:
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    await cb.answer(f"📦 {len(eps)} ta qism yuborilmoqda...", show_alert=True)
    for ep in eps:
        try:
            await bot.send_video(
                cb.from_user.id, video=ep["video_file_id"],
                caption=f"▶️ {ep['qism_raqami']}-qism | @Aniyoof",
            )
            await asyncio.sleep(0.3)
        except Exception:
            pass


# ──────────────────────────── FAVORITES / WATCHLIST ─────────────────────────

@router.callback_query(F.data.startswith("fav_"))
async def cb_fav(cb: CallbackQuery) -> None:
    aid = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    if await db_is_fav(uid, aid):
        await db_remove_fav(uid, aid)
        await cb.answer("💔 Sevimlilardan olib tashlandi!")
        new_fav = False
    else:
        await db_add_fav(uid, aid)
        await cb.answer("❤️ Sevimlilarga qo'shildi!")
        new_fav = True
    wl    = await db_is_wl(uid, aid)
    notif = await db_is_notif(uid, aid)
    try:
        await cb.message.edit_reply_markup(reply_markup=ik_anime_full(aid, new_fav, wl, notif))
    except Exception:
        pass


@router.callback_query(F.data.startswith("wl_"))
async def cb_wl(cb: CallbackQuery) -> None:
    aid = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    if not await is_premium(uid):
        await cb.answer("💎 Faqat Premium uchun!", show_alert=True)
        return
    if await db_is_wl(uid, aid):
        await db_remove_wl(uid, aid)
        await cb.answer("📋 Watch listdan olib tashlandi!")
        new_wl = False
    else:
        await db_add_wl(uid, aid)
        await cb.answer("📋 Watch listga qo'shildi!")
        new_wl = True
    fav   = await db_is_fav(uid, aid)
    notif = await db_is_notif(uid, aid)
    try:
        await cb.message.edit_reply_markup(reply_markup=ik_anime_full(aid, fav, new_wl, notif))
    except Exception:
        pass


# ──────────────────────────── RATING & COMMENTS ─────────────────────────────

@router.callback_query(F.data.startswith("rate_"))
async def cb_rate_start(cb: CallbackQuery) -> None:
    aid = int(cb.data.split("_")[1])
    ex  = await db_get_user_rating(cb.from_user.id, aid)
    extra = f"\n\nSizning bahoyingiz: ⭐{ex['baho']}" if ex else ""
    await cb.message.answer(
        f"⭐ <b>Baholash</b>{extra}\n\nBaho bering (1–10):",
        reply_markup=ik_rating(aid), parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("rt_"))
async def cb_rate_save(cb: CallbackQuery) -> None:
    _, aid, baho = cb.data.split("_")
    await db_add_rating(cb.from_user.id, int(aid), float(baho))
    await cb.answer(f"✅ Bahoyingiz {baho}/10 saqlandi!", show_alert=True)
    try:
        await cb.message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("non_"))
async def cb_notif_on(cb: CallbackQuery) -> None:
    aid = int(cb.data.split("_")[1])
    if not await is_premium(cb.from_user.id):
        await cb.answer("💎 Faqat Premium uchun!", show_alert=True)
        return
    await db_add_notif(cb.from_user.id, aid)
    await cb.answer("🔔 Bildirishnoma yoqildi!")
    fav = await db_is_fav(cb.from_user.id, aid)
    wl  = await db_is_wl(cb.from_user.id, aid)
    try:
        await cb.message.edit_reply_markup(reply_markup=ik_anime_full(aid, fav, wl, True))
    except Exception:
        pass


@router.callback_query(F.data.startswith("noff_"))
async def cb_notif_off(cb: CallbackQuery) -> None:
    aid = int(cb.data.split("_")[1])
    await db_remove_notif(cb.from_user.id, aid)
    await cb.answer("🔕 Bildirishnoma o'chirildi!")
    fav = await db_is_fav(cb.from_user.id, aid)
    wl  = await db_is_wl(cb.from_user.id, aid)
    try:
        await cb.message.edit_reply_markup(reply_markup=ik_anime_full(aid, fav, wl, False))
    except Exception:
        pass


@router.callback_query(F.data.startswith("cmt_"))
async def cb_comments(cb: CallbackQuery) -> None:
    _, aid, offset = cb.data.split("_")
    aid, offset    = int(aid), int(offset)
    cmts  = await db_get_comments(aid, 10, offset)
    total = await db_count_comments(aid)
    a     = await db_get_anime(aid)
    t     = f"💬 <b>{a['nomi']} — Izohlar</b>\n━━━━━━━━━━━━━━━━\n"
    if not cmts:
        t += "\nHali izoh yo'q. Birinchi bo'ling! 👇"
    else:
        for c in cmts:
            name = c["ism"] or c["username"] or "?"
            date = c["created_at"].strftime("%d.%m") if c["created_at"] else ""
            t   += f"👤 <b>{name}</b> <i>{date}</i>\n{c['matn']}\n\n"
    await cb.message.answer(t, reply_markup=ik_comments(aid, offset, total), parse_mode="HTML")


@router.callback_query(F.data.startswith("wcmt_"))
async def cb_write_comment(cb: CallbackQuery, state: FSMContext) -> None:
    aid = int(cb.data.split("_")[1])
    await state.update_data(cmt_aid=aid)
    await state.set_state(CommentW.write)
    await cb.message.answer("✍️ Izohingizni yozing:", reply_markup=kb_cancel())


@router.message(CommentW.write)
async def save_comment(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_main()); return
    d = await state.get_data()
    await db_add_comment(msg.from_user.id, d["cmt_aid"], msg.text.strip())
    await state.clear()
    await msg.answer("✅ Izoh qo'shildi!", reply_markup=kb_main())


# ──────────────────────────── PREMIUM ───────────────────────────────────────

PREMIUM_TXT = (
    "💎 <b>Aniyoof Premium</b>\n\n"
    "✅ Janr/Yil bilan qidirish\n"
    "✅ Rasm orqali qidirish\n"
    "✅ Eng ko'p ko'rilgan\n"
    "✅ Watch list\n"
    "✅ Bildirishnomalar\n\nTanlang:"
)


@router.callback_query(F.data == "pr_menu")
async def cb_pr_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await cb.message.edit_text(PREMIUM_TXT, reply_markup=ik_premium_menu(), parse_mode="HTML")
    except Exception:
        await cb.message.answer(PREMIUM_TXT, reply_markup=ik_premium_menu(), parse_mode="HTML")


@router.callback_query(F.data == "pr_bot")
async def cb_pr_bot(cb: CallbackQuery) -> None:
    await cb.message.edit_text("💰 <b>Tarifni tanlang:</b>", reply_markup=ik_tarif(), parse_mode="HTML")


@router.callback_query(F.data == "pr_admin")
async def cb_pr_admin(cb: CallbackQuery) -> None:
    await cb.message.edit_text(
        "👤 <b>Admin orqali olish:</b>", reply_markup=ik_admins_contact(), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("tarif_"))
async def cb_tarif(cb: CallbackQuery, state: FSMContext) -> None:
    tarif = cb.data.split("_")[1]
    await state.update_data(tarif=tarif)
    await state.set_state(PremiumPay.screenshot)
    await cb.message.edit_text(
        f"💳 <b>To'lov:</b>\n\n"
        f"💳 Karta: <code>{PAYMENT_CARD}</code>\n"
        f"💰 Miqdor: <b>{tarif_label(tarif)}</b>\n\n"
        "Chek screenshot yuboring 👇",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="pr_menu")
        ]]),
        parse_mode="HTML",
    )


@router.message(PremiumPay.screenshot, F.photo)
async def pr_screenshot(msg: Message, state: FSMContext, bot: Bot) -> None:
    d     = await state.get_data()
    tarif = d.get("tarif", "1oy")
    sid   = msg.photo[-1].file_id
    uid   = msg.from_user.id
    req   = await db_create_pr_req(uid, tarif, sid)
    u     = await db_get_user(uid)
    name  = u["ism"] if u else "?"
    un    = f"@{msg.from_user.username}" if msg.from_user.username else "yo'q"
    await state.clear()
    await msg.answer(
        "✅ <b>Ariza qabul qilindi!</b>\n⏰ 1–24 soat ichida tekshiriladi.",
        reply_markup=kb_main(), parse_mode="HTML",
    )
    for adm_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                adm_id, photo=sid,
                caption=(
                    f"💳 <b>Premium ariza!</b>\n"
                    f"👤 {name}\n🆔 {un}\n📱 ID: {uid}\n"
                    f"📦 {tarif_label(tarif)}\n🔑 Req ID: {req['id']}"
                ),
                reply_markup=ik_admin_pr(req["id"], uid),
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.message(PremiumPay.screenshot)
async def pr_screenshot_wrong(msg: Message, state: FSMContext) -> None:
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_main()); return
    await msg.answer("📸 Screenshot rasm yuboring.")


@router.callback_query(F.data.startswith("apr_"))
async def cb_approve_pr(cb: CallbackQuery, bot: Bot) -> None:
    _, rid, uid = cb.data.split("_")
    rid, uid    = int(rid), int(uid)
    req         = await db_get_pr_req(rid)
    if not req:
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    pe = premium_end_date(req["tarif"])
    await db_update_user(uid, premium=True, premium_tugash=pe)
    await db_update_pr_req(rid, "tasdiqlandi")
    try:
        await cb.message.edit_caption(cb.message.caption + "\n\n✅ TASDIQLANDI", parse_mode="HTML")
    except Exception:
        pass
    try:
        await bot.send_message(
            uid,
            f"🎉 <b>Premium faollashtirildi!</b>\n"
            f"📦 {tarif_label(req['tarif'])}\n"
            "⏰ " + pe.strftime("%d.%m.%Y") + " gacha\n💎 Rohatlaning!",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await cb.answer("✅ Premium berildi!")


@router.callback_query(F.data.startswith("rpr_"))
async def cb_reject_pr(cb: CallbackQuery, bot: Bot) -> None:
    _, rid, uid = cb.data.split("_")
    rid, uid    = int(rid), int(uid)
    await db_update_pr_req(rid, "rad etildi")
    try:
        await cb.message.edit_caption(cb.message.caption + "\n\n❌ RAD ETILDI", parse_mode="HTML")
    except Exception:
        pass
    try:
        await bot.send_message(uid, "❌ <b>Premium arizangiz rad etildi.</b>", parse_mode="HTML")
    except Exception:
        pass
    await cb.answer("❌ Rad etildi!")


# ──────────────────────────── ADMIN PANEL ───────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    await state.clear()
    await msg.answer("👑 Admin paneli:", reply_markup=kb_admin())


@router.message(F.text == "👤 User paneliga o'tish")
async def switch_to_user(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    await state.clear()
    await msg.answer("👤 User paneliga o'tdingiz!", reply_markup=kb_main())


@router.callback_query(F.data == "adm_back")
async def cb_adm_back(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await cb.message.delete()
    except Exception:
        pass
    await cb.message.answer("👑 Admin paneli:", reply_markup=kb_admin())


# ── Admin Statistics ──────────────────────────────────────────────────────────

@router.message(F.text == "📊 Statistika")
async def adm_stats(msg: Message) -> None:
    if not is_admin(msg.from_user.id):
        return
    s = await db_stats()
    await msg.answer(
        f"📊 <b>Statistika</b>\n━━━━━━━━━━━━━━━━\n"
        f"👥 Jami foydalanuvchi: <b>{s['total_users']}</b>\n"
        f"💎 Premium: <b>{s['premium_users']}</b>\n"
        f"🎬 Jami anime: <b>{s['total_animes']}</b>\n"
        f"👁 Jami ko'rishlar: <b>{s['total_views']:,}</b>\n"
        f"📅 Bugun qo'shildi: <b>{s['today_users']}</b>\n"
        f"👦 Erkak: <b>{s['erkak']}</b> | 👧 Ayol: <b>{s['ayol']}</b>\n"
        f"🎂 O'rtacha yosh: <b>{s['yosh_avg']}</b>",
        parse_mode="HTML", reply_markup=kb_admin(),
    )


# ── Broadcast ─────────────────────────────────────────────────────────────────

@router.message(F.text == "📢 Xabar yuborish")
async def adm_broadcast_start(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    await state.set_state(Broadcast.msg)
    await msg.answer("📢 Yubormoqchi bo'lgan xabarni yozing:", reply_markup=kb_cancel())


@router.message(Broadcast.msg)
async def adm_broadcast_msg(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_admin()); return
    await state.update_data(bc_msg_id=msg.message_id, bc_chat_id=msg.chat.id)
    await state.set_state(Broadcast.target)
    await msg.answer("🎯 Kimga yuborilsin?", reply_markup=ik_bc_target())


@router.callback_query(F.data.in_({"bc_all", "bc_premium", "bc_free"}), Broadcast.target)
async def adm_broadcast_target(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(bc_target=cb.data)
    await state.set_state(Broadcast.confirm)
    labels = {"bc_all": "Barcha", "bc_premium": "Premiumlar", "bc_free": "Oddiy userlar"}
    await cb.message.edit_text(
        f"📢 <b>Xabar</b> → {labels[cb.data]}\n\nTasdiqlaysizmi?",
        reply_markup=ik_confirm_bc(), parse_mode="HTML",
    )


@router.callback_query(F.data == "bc_no", Broadcast.confirm)
async def adm_broadcast_no(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text("❌ Bekor qilindi.")
    await cb.message.answer("👑 Admin paneli:", reply_markup=kb_admin())


@router.callback_query(F.data == "bc_yes", Broadcast.confirm)
async def adm_broadcast_yes(cb: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    d      = await state.get_data()
    target = d.get("bc_target", "bc_all")
    await state.clear()

    if target == "bc_premium":
        users = await db_premium_users()
    elif target == "bc_free":
        async with pool.acquire() as c:
            users = await c.fetch("SELECT * FROM users WHERE premium=FALSE AND is_blocked=FALSE")
    else:
        users = await db_all_users()

    sent = failed = 0
    status_msg = await cb.message.edit_text(f"📢 Yuborilmoqda... 0/{len(users)}")
    for i, u in enumerate(users, 1):
        try:
            await bot.copy_message(u["telegram_id"], d["bc_chat_id"], d["bc_msg_id"])
            sent += 1
        except Exception:
            failed += 1
        if i % 20 == 0:
            try:
                await status_msg.edit_text(f"📢 Yuborilmoqda... {i}/{len(users)}")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    try:
        await status_msg.edit_text(
            f"✅ Yuborildi: {sent}\n❌ Xato: {failed}"
        )
    except Exception:
        pass


# ── Admin Management ──────────────────────────────────────────────────────────

@router.message(F.text == "👥 Admin boshqaruvi")
async def adm_mgmt_menu(msg: Message, state: FSMContext) -> None:
    if not is_super_admin(msg.from_user.id):
        await msg.answer("⛔ Faqat asosiy adminlar uchun!", reply_markup=kb_admin())
        return
    await state.clear()
    await msg.answer("👥 <b>Admin boshqaruvi</b>", reply_markup=ik_admin_mgmt(), parse_mode="HTML")


@router.callback_query(F.data == "adm_add")
async def adm_add_start(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_super_admin(cb.from_user.id):
        await cb.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(AdminMgmt.add_id)
    await cb.message.edit_text(
        "➕ <b>Yangi admin qo'shish</b>\n\n"
        "Foydalanuvchining Telegram ID sini yuboring.\n"
        "(masalan: 123456789)\n\n"
        "ID bilish uchun: @userinfobot",
        parse_mode="HTML", reply_markup=ik_back("adm_back"),
    )


@router.message(AdminMgmt.add_id)
async def adm_add_process(msg: Message, state: FSMContext, bot: Bot) -> None:
    if not is_super_admin(msg.from_user.id):
        return
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_admin()); return
    try:
        new_id = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Faqat raqam kiriting!")
        return
    if new_id in ADMIN_IDS:
        await state.clear()
        await msg.answer("⚠️ Bu foydalanuvchi allaqachon admin!", reply_markup=kb_admin())
        return
    try:
        chat  = await bot.get_chat(new_id)
        uname = chat.username or ""
    except Exception:
        uname = ""
    await db_add_admin(new_id, uname, msg.from_user.id)
    ADMIN_IDS.append(new_id)
    await state.clear()
    display = f"@{uname}" if uname else f"ID: {new_id}"
    await msg.answer(f"✅ <b>Admin qo'shildi:</b> {display}", parse_mode="HTML", reply_markup=kb_admin())
    try:
        await bot.send_message(
            new_id,
            "🎉 <b>Siz admin qildingiz!</b>\n/admin buyrug'ini bosing.",
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data == "adm_list_view")
async def adm_list_view(cb: CallbackQuery) -> None:
    if not is_super_admin(cb.from_user.id):
        await cb.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    rows = await db_get_admins()
    t    = "👥 <b>Adminlar ro'yxati</b>\n━━━━━━━━━━━━━━━━\n\n"
    t   += "👑 <b>Asosiy adminlar:</b>\n"
    for sid in SUPER_ADMIN_IDS:
        t += f"• ID: <code>{sid}</code>\n"
    t += "\n➕ <b>Qo'shilgan adminlar:</b>\n"
    if rows:
        for a in rows:
            un   = f"@{a['username']}" if a['username'] else f"ID: {a['telegram_id']}"
            date = a["qoshilgan_sana"].strftime("%d.%m.%Y") if a["qoshilgan_sana"] else "—"
            t   += f"• {un} | {date}\n"
    else:
        t += "Hali qo'shilgan admin yo'q.\n"
    b = InlineKeyboardBuilder()
    b.button(text="🔙 Orqaga", callback_data="adm_back")
    try:
        await cb.message.edit_text(t, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        await cb.message.answer(t, reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "adm_remove")
async def adm_remove_start(cb: CallbackQuery) -> None:
    if not is_super_admin(cb.from_user.id):
        await cb.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    rows = await db_get_admins()
    if not rows:
        await cb.answer("❌ O'chirilishi mumkin admin yo'q!", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    for a in rows:
        un = f"@{a['username']}" if a['username'] else f"ID:{a['telegram_id']}"
        b.button(text=f"🗑 {un}", callback_data=f"rmadm_{a['telegram_id']}")
    b.button(text="🔙 Orqaga", callback_data="adm_back")
    b.adjust(1)
    try:
        await cb.message.edit_text(
            "🗑 <b>Qaysi adminni o'chirmoqchisiz?</b>",
            reply_markup=b.as_markup(), parse_mode="HTML",
        )
    except Exception:
        await cb.message.answer(
            "🗑 <b>Qaysi adminni o'chirmoqchisiz?</b>",
            reply_markup=b.as_markup(), parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("rmadm_"))
async def adm_remove_confirm(cb: CallbackQuery, bot: Bot) -> None:
    if not is_super_admin(cb.from_user.id):
        await cb.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    target_id = int(cb.data.split("_")[1])
    if target_id in SUPER_ADMIN_IDS:
        await cb.answer("⛔ Asosiy adminni o'chirib bo'lmaydi!", show_alert=True)
        return
    await db_remove_admin(target_id)
    if target_id in ADMIN_IDS:
        ADMIN_IDS.remove(target_id)
    await cb.answer("✅ Admin o'chirildi!", show_alert=True)
    try:
        await bot.send_message(target_id, "ℹ️ <b>Adminlikdan olib tashlandingiz.</b>", parse_mode="HTML")
    except Exception:
        pass
    rows = await db_get_admins()
    if not rows:
        try:
            await cb.message.edit_text("✅ Barcha qo'shilgan adminlar o'chirildi.", reply_markup=ik_back("adm_back"))
        except Exception:
            pass
        return
    b = InlineKeyboardBuilder()
    for a in rows:
        un = f"@{a['username']}" if a['username'] else f"ID:{a['telegram_id']}"
        b.button(text=f"🗑 {un}", callback_data=f"rmadm_{a['telegram_id']}")
    b.button(text="🔙 Orqaga", callback_data="adm_back")
    b.adjust(1)
    try:
        await cb.message.edit_reply_markup(reply_markup=b.as_markup())
    except Exception:
        pass


# ── Add Anime ─────────────────────────────────────────────────────────────────

@router.message(F.text == "➕ Anime qo'shish")
async def adm_add_anime(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    await state.clear()
    await msg.answer("➕ <b>Anime qo'shish</b>", reply_markup=ik_admin_add(), parse_mode="HTML")


@router.callback_query(F.data == "adm_cont")
async def adm_continue_anime(cb: CallbackQuery, state: FSMContext) -> None:
    """'📝 Davomini qo'shish' — pick an existing anime to add seasons/episodes to."""
    if not is_admin(cb.from_user.id):
        return
    await state.clear()
    animes = await db_all_animes()
    if not animes:
        await cb.answer("❌ Hali anime yo'q!", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    for a in animes:
        b.button(text=f"🎬 {a['kodi']} — {a['nomi']}", callback_data=f"aa_{a['id']}")
    b.button(text="🔙 Orqaga", callback_data="adm_back")
    b.adjust(1)
    try:
        await cb.message.edit_text(
            "📝 <b>Qaysi animega davom qo'shasiz?</b>",
            reply_markup=b.as_markup(), parse_mode="HTML",
        )
    except Exception:
        await cb.message.answer(
            "📝 <b>Qaysi animega davom qo'shasiz?</b>",
            reply_markup=b.as_markup(), parse_mode="HTML",
        )


@router.callback_query(F.data == "adm_new")
async def adm_new_anime_start(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        return
    await state.set_state(AddAnime.info)
    await cb.message.edit_text(
        f"📝 <b>Yangi anime:</b>\n\n{INFO_FORMAT}", parse_mode="HTML", reply_markup=ik_back("adm_back")
    )


@router.message(AddAnime.info)
async def adm_anime_info(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    if msg.text in ("❌ Bekor qilish", "/admin"):
        await state.clear(); await msg.answer("❌", reply_markup=kb_admin()); return
    try:
        d: dict = {}
        for line in (msg.text or "").strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                d[k.strip().lower()] = v.strip()
        nomi    = d["nomi"]
        kodi    = d["kod"]
        janr    = d["janr"]
        yil     = int(d["yil"])
        fasllar = int(d.get("fasllar", 1))
        qismlar = int(d.get("qismlar", 0))
        holati  = d.get("holati", "Davom etmoqda")
        tavsif  = d.get("tavsif", "")
        yosh    = d.get("yosh", "Belgilanmagan")
        if await db_get_anime_by_code(kodi):
            await msg.answer(f"❌ <b>{kodi}</b> kodi allaqachon mavjud!", parse_mode="HTML")
            return
        await state.update_data(
            nomi=nomi, kodi=kodi, janr=janr, yil=yil,
            fasllar=fasllar, qismlar=qismlar,
            holati=holati, tavsif=tavsif, yosh=yosh,
        )
        await state.set_state(AddAnime.media)
        await msg.answer("🖼 <b>Rasm yoki video yuboring:</b>", parse_mode="HTML", reply_markup=ik_back("adm_back"))
    except (KeyError, ValueError):
        await msg.answer(f"❌ Xato format!\n\n{INFO_FORMAT}")


@router.message(AddAnime.media, F.photo | F.video)
async def adm_anime_media(msg: Message, state: FSMContext, bot: Bot) -> None:
    if not is_admin(msg.from_user.id):
        return
    d   = await state.get_data()
    fid = msg.photo[-1].file_id if msg.photo else msg.video.file_id
    mt  = "photo" if msg.photo else "video"
    a   = await db_create_anime(
        d["nomi"], d["kodi"], d["janr"], d["yil"],
        d["fasllar"], d["qismlar"], d["holati"],
        fid, mt, d.get("tavsif", ""), d.get("yosh", "Belgilanmagan"),
    )
    await state.clear()
    anime_id_val = a["id"]
    await msg.answer(f"✅ <b>{d['nomi']}</b> qo'shildi!", reply_markup=ik_admin_action(anime_id_val), parse_mode="HTML")

    # Channel post
    status_icon = "✅" if d["holati"] == "Tugallangan" else "🔄"
    ch_txt = (
        f"🎌 <b>Yangi anime!</b>\n\n🎬 <b>{d['nomi']}</b>\n"
        f"📁 Kod: <code>{d['kodi']}</code>\n"
        f"🎭 {d['janr']}\n📅 {d['yil']}\n"
        f"🗂 {d['fasllar']} fasl | 📺 {d['qismlar']} qism\n"
        f"{status_icon} {d['holati']}\n\n@Aniyoof"
    )
    try:
        if mt == "video":
            await bot.send_video(CHANNEL_ID, video=fid, caption=ch_txt,
                                 reply_markup=ik_anime_watch_channel(a["id"]), parse_mode="HTML")
        else:
            await bot.send_photo(CHANNEL_ID, photo=fid, caption=ch_txt,
                                 reply_markup=ik_anime_watch_channel(a["id"]), parse_mode="HTML")
    except Exception as ex:
        await msg.answer(f"⚠️ Kanalga post xato: {ex}")

    # Notify premium users
    premium = await db_premium_users()
    count   = 0
    for u in premium:
        try:
            await bot.send_message(
                u["telegram_id"],
                f"🔔 <b>Yangi anime!</b>\n\n🎬 <b>{d['nomi']}</b>\n"
                f"🎭 {d['janr']} | 📅 {d['yil']}\n\nBotda ko'ring!",
                parse_mode="HTML",
            )
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    if count:
        await msg.answer(f"📢 {count} ta premium foydalanuvchiga xabar yuborildi!")


@router.message(AddAnime.media)
async def adm_anime_media_wrong(msg: Message) -> None:
    if msg.text not in ("❌ Bekor qilish", "/admin"):
        await msg.answer("🖼 Rasm yoki video yuboring!")


# ── Add Season ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("addsn_"))
async def adm_add_season_start(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        return
    aid = int(cb.data.split("_")[1])
    await state.update_data(sn_anime_id=aid)
    await state.set_state(AddSeason.name)
    await cb.message.answer(
        "📂 Fasl nomini kiriting:\n(masalan: 1-Fasl yoki Season 1)",
        reply_markup=kb_cancel(),
    )


@router.message(AddSeason.name)
async def adm_add_season(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_admin()); return
    d         = await state.get_data()
    aid       = d["sn_anime_id"]
    seasons   = await db_get_seasons(aid)
    fasl_raqami = len(seasons) + 1
    season    = await db_create_season(aid, msg.text.strip(), fasl_raqami)
    await state.clear()
    await msg.answer(
        f"✅ <b>{season['fasl_nomi']}</b> yaratildi!",
        reply_markup=ik_admin_action(aid), parse_mode="HTML",
    )


# ── Add Episode ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("addep_"))
async def adm_add_ep_start(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        return
    aid     = int(cb.data.split("_")[1])
    seasons = await db_get_seasons(aid)
    if not seasons:
        await cb.answer("❌ Avval fasl qo'shing!", show_alert=True)
        return
    await state.update_data(ep_anime_id=aid)
    if len(seasons) == 1:
        await state.update_data(ep_season_id=seasons[0]["id"])
        await state.set_state(AddEpisode.video)
        await cb.message.answer(
            f"📥 <b>{seasons[0]['fasl_nomi']}</b> uchun videolarni yuboring.\n\n"
            "Bir nechta qismni ketma-ket (yoki forward qilib) yuborishingiz mumkin — "
            "ular yuborilgan tartibda 1-qism, 2-qism... bo'lib qo'shiladi.\n\n"
            "Tugatgach ✅ Tugatish tugmasini bosing.",
            reply_markup=kb_episode_upload(), parse_mode="HTML",
        )
    else:
        await state.set_state(AddEpisode.sel_season)
        await cb.message.answer("📂 Faslni tanlang:", reply_markup=ik_seasons_ep(seasons, aid))


@router.callback_query(F.data.startswith("sel_sn_"), AddEpisode.sel_season)
async def adm_sel_season(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split("_")
    sid   = int(parts[2])
    await state.update_data(ep_season_id=sid)
    await state.set_state(AddEpisode.video)
    await cb.message.answer(
        "📥 Videolarni ketma-ket (yoki forward qilib) yuboring.\n\n"
        "Ular yuborilgan tartibda qism bo'lib qo'shiladi.\n"
        "Tugatgach ✅ Tugatish tugmasini bosing.",
        reply_markup=kb_episode_upload(),
    )


@router.message(AddEpisode.video, F.video)
async def adm_add_episode(msg: Message, state: FSMContext, bot: Bot) -> None:
    if not is_admin(msg.from_user.id):
        return
    d   = await state.get_data()
    sid = d["ep_season_id"]
    aid = d["ep_anime_id"]
    # Atomic, lock-protected insert keeps forwarded videos in order and does NOT
    # clear the FSM state, so the admin can keep sending episodes one after another.
    ep    = await db_append_episode(sid, aid, msg.video.file_id)
    anime = await db_get_anime(aid)
    await msg.answer(
        f"✅ {ep['qism_raqami']}-qism qo'shildi! (Jami: {anime['joylangan_qismlar']})",
        reply_markup=kb_episode_upload(),
    )
    # Notify subscribers
    subs = await db_notif_subs(aid)
    for sub in subs:
        try:
            await bot.send_message(
                sub["telegram_id"],
                f"🔔 <b>{anime['nomi']}</b> — {ep['qism_raqami']}-qism chiqdi!",
                parse_mode="HTML",
            )
            await asyncio.sleep(0.05)
        except Exception:
            pass


@router.message(AddEpisode.video)
async def adm_add_episode_other(msg: Message, state: FSMContext) -> None:
    txt = msg.text or ""
    if txt == "✅ Tugatish":
        d   = await state.get_data()
        aid = d.get("ep_anime_id")
        await state.clear()
        if aid:
            anime = await db_get_anime(aid)
            jami  = anime["joylangan_qismlar"] if anime else 0
            await msg.answer(
                f"✅ Qism qo'shish tugatildi! (Jami joylangan: {jami})",
                reply_markup=kb_admin(),
            )
            await msg.answer("⚙️ Anime boshqaruvi:", reply_markup=ik_admin_action(aid))
        else:
            await msg.answer("✅ Tugatildi!", reply_markup=kb_admin())
        return
    if txt in ("🏠 Bosh menyu", "❌ Bekor qilish"):
        await state.clear()
        await msg.answer("🏠 Bosh menyu", reply_markup=kb_admin())
        return
    await msg.answer(
        "🎬 Video fayl yuboring yoki ✅ Tugatish tugmasini bosing!",
        reply_markup=kb_episode_upload(),
    )


# ── Edit Anime ────────────────────────────────────────────────────────────────

@router.message(F.text == "✏️ Anime tahrirlash")
async def adm_edit_list(msg: Message) -> None:
    if not is_admin(msg.from_user.id):
        return
    animes = await db_all_animes()
    if not animes:
        await msg.answer("❌ Hali anime yo'q!", reply_markup=kb_admin())
        return
    b = InlineKeyboardBuilder()
    for a in animes:
        b.button(text=f"🎬 {a['kodi']} — {a['nomi']}", callback_data=f"editanim_{a['id']}")
    b.button(text="🔙 Orqaga", callback_data="adm_back")
    b.adjust(1)
    await msg.answer("✏️ <b>Qaysi animeni tahrirlaysiz?</b>", reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("editanim_"))
async def cb_editanim(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    aid = int(cb.data.split("_")[1])
    a   = await db_get_anime(aid)
    if not a:
        await cb.answer("❌", show_alert=True)
        return
    try:
        await cb.message.edit_text(
            anime_edit_text(a), reply_markup=ik_anime_edit_fields(aid), parse_mode="HTML"
        )
    except Exception:
        await cb.message.answer(
            anime_edit_text(a), reply_markup=ik_anime_edit_fields(aid), parse_mode="HTML"
        )


# Whitelisted editable fields
_ANIME_FIELD_MAP = {
    "nomi":    "nomi",
    "kodi":    "kodi",
    "janr":    "janr",
    "yil":     "yil",
    "fasllar": "fasllar_soni",
    "qismlar": "qismlar_soni",
    "tavsif":  "tavsif",
}
_ANIME_FIELD_LABELS = {
    "nomi":    "📛 Nomi",
    "kodi":    "📁 Kodi",
    "janr":    "🎭 Janri",
    "yil":     "📅 Yili",
    "fasllar": "🗂 Fasllar soni",
    "qismlar": "📺 Qismlar soni",
    "tavsif":  "📝 Tavsif",
}


@router.callback_query(F.data.startswith("efield_"))
async def cb_efield(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        return
    parts = cb.data.split("_")
    field = parts[1]
    aid   = int(parts[2])
    await state.update_data(edit_aid=aid, edit_field=field)

    if field == "holati":
        await cb.message.edit_text("🔄 Holatni tanlang:", reply_markup=ik_holati_select(aid))
        return
    if field == "yosh":
        await cb.message.edit_text("🔞 Yosh chegarasini tanlang:", reply_markup=ik_yosh_select(aid))
        return
    if field == "media":
        await state.set_state(EditAnime.media)
        await cb.message.edit_text("🖼 Yangi rasm yoki video yuboring:", reply_markup=ik_back(f"editanim_{aid}"))
        return

    label = _ANIME_FIELD_LABELS.get(field, field)
    await state.set_state(EditAnime.value)
    await cb.message.edit_text(
        f"✏️ <b>{label}</b> uchun yangi qiymat yozing:",
        reply_markup=ik_back(f"editanim_{aid}"), parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("setholati_"))
async def cb_setholati(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    parts  = cb.data.split("_")
    aid    = int(parts[2])
    holati = "Davom etmoqda" if parts[1] == "davom" else "Tugallangan"
    await db_update_anime_field(aid, "holati", holati)
    await cb.answer(f"✅ Holat: {holati}")
    a = await db_get_anime(aid)
    try:
        await cb.message.edit_text(anime_edit_text(a), reply_markup=ik_anime_edit_fields(aid), parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("setyosh_"))
async def cb_setyosh(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    parts    = cb.data.split("_")
    aid      = int(parts[2])
    yosh_val = parts[1].replace("plus", "+")
    await db_update_anime_field(aid, "yosh_chegarasi", yosh_val)
    await cb.answer(f"✅ Yosh: {yosh_val}")
    a = await db_get_anime(aid)
    try:
        await cb.message.edit_text(anime_edit_text(a), reply_markup=ik_anime_edit_fields(aid), parse_mode="HTML")
    except Exception:
        pass


@router.message(EditAnime.value)
async def edit_anime_value(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_admin()); return
    d     = await state.get_data()
    aid   = d["edit_aid"]
    field = d["edit_field"]
    db_col = _ANIME_FIELD_MAP.get(field)
    if not db_col:
        await state.clear(); await msg.answer("❌ Xato!", reply_markup=kb_admin()); return
    val = msg.text.strip()
    try:
        if field in ("yil", "fasllar", "qismlar"):
            val = int(val)
        await db_update_anime_field(aid, db_col, val)
        await state.clear()
        a = await db_get_anime(aid)
        await msg.answer(
            "✅ <b>Yangilandi!</b>\n\n" + anime_edit_text(a),
            reply_markup=ik_anime_edit_fields(aid), parse_mode="HTML",
        )
    except ValueError:
        await msg.answer("❌ Raqam kerak bo'lsa raqam kiriting!")


@router.message(EditAnime.media, F.photo | F.video)
async def edit_anime_media(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    d   = await state.get_data()
    aid = d["edit_aid"]
    fid = msg.photo[-1].file_id if msg.photo else msg.video.file_id
    mt  = "photo" if msg.photo else "video"
    async with pool.acquire() as c:
        await c.execute(
            "UPDATE animes SET media_file_id=$1, media_type=$2 WHERE id=$3", fid, mt, aid
        )
    await state.clear()
    a = await db_get_anime(aid)
    await msg.answer(
        f"✅ <b>{a['nomi']}</b> media yangilandi!",
        reply_markup=ik_anime_edit_fields(aid), parse_mode="HTML",
    )


@router.message(EditAnime.media)
async def edit_anime_media_wrong(msg: Message) -> None:
    if msg.text != "❌ Bekor qilish":
        await msg.answer("🖼 Rasm yoki video yuboring!")


@router.callback_query(F.data.startswith("delanime_"))
async def cb_delanime(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    aid = int(cb.data.split("_")[1])
    a   = await db_get_anime(aid)
    if not a:
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    try:
        await cb.message.edit_text(
            f"⚠️ <b>{a['nomi']}</b> animesini o'chirishni tasdiqlaysizmi?\n\n"
            "Barcha fasl, qism va ma'lumotlar o'chib ketadi!",
            reply_markup=ik_confirm_del(aid), parse_mode="HTML",
        )
    except Exception:
        await cb.message.answer(
            f"⚠️ <b>{a['nomi']}</b> — o'chirishni tasdiqlaysizmi?",
            reply_markup=ik_confirm_del(aid), parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("confirmdel_"))
async def cb_confirmdel(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    aid  = int(cb.data.split("_")[1])
    a    = await db_get_anime(aid)
    nomi = a["nomi"] if a else "?"
    await db_delete_anime(aid)
    await cb.answer(f"✅ {nomi} o'chirildi!", show_alert=True)
    try:
        await cb.message.delete()
    except Exception:
        pass
    await cb.message.answer("✅ Anime o'chirildi!", reply_markup=kb_admin())


# ── Delete Episode ────────────────────────────────────────────────────────────

@router.message(F.text == "✂️ Qism o'chirish")
async def adm_del_ep_start(msg: Message) -> None:
    if not is_admin(msg.from_user.id):
        return
    animes = await db_all_animes()
    if not animes:
        await msg.answer("❌ Hali anime yo'q!", reply_markup=kb_admin())
        return
    b = InlineKeyboardBuilder()
    for a in animes:
        b.button(text=f"🎬 {a['kodi']} — {a['nomi']}", callback_data=f"epdelanim_{a['id']}")
    b.button(text="🔙 Orqaga", callback_data="adm_back")
    b.adjust(1)
    await msg.answer(
        "✂️ <b>Qaysi animening qismini o'chirmoqchisiz?</b>",
        reply_markup=b.as_markup(), parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("epdelanim_"))
async def cb_epdelanim(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    aid = int(cb.data.split("_")[1])
    sns = await db_get_seasons(aid)
    if not sns:
        await cb.answer("❌ Bu animeda fasl yo'q!", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    for s in sns:
        b.button(text=f"📂 {s['fasl_nomi']}", callback_data=f"epdelssn_{s['id']}_{aid}")
    b.button(text="🔙 Orqaga", callback_data="adm_back")
    b.adjust(1)
    try:
        await cb.message.edit_text("📂 <b>Faslni tanlang:</b>", reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        await cb.message.answer("📂 <b>Faslni tanlang:</b>", reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("epdelssn_"))
async def cb_epdelssn(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    parts    = cb.data.split("_")
    sid, aid = int(parts[1]), int(parts[2])
    eps      = await db_get_episodes(sid)
    if not eps:
        await cb.answer("❌ Bu faslda qism yo'q!", show_alert=True)
        return
    try:
        await cb.message.edit_text(
            "✂️ <b>Qismni tanlang:</b>",
            reply_markup=ik_episodes_delete(eps, sid, aid), parse_mode="HTML",
        )
    except Exception:
        await cb.message.answer(
            "✂️ <b>Qismni tanlang:</b>",
            reply_markup=ik_episodes_delete(eps, sid, aid), parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("deleplist_"))
async def cb_delep_list(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    _, sid, aid = cb.data.split("_")
    sid, aid    = int(sid), int(aid)
    eps         = await db_get_episodes(sid)
    if not eps:
        await cb.answer("❌ Qism yo'q!", show_alert=True)
        return
    try:
        await cb.message.edit_reply_markup(reply_markup=ik_episodes_delete(eps, sid, aid))
    except Exception:
        await cb.message.answer("🗑 Qismni tanlang:", reply_markup=ik_episodes_delete(eps, sid, aid))


@router.callback_query(F.data.startswith("delep_"))
async def cb_delep(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    parts       = cb.data.split("_")
    eid, sid, aid = int(parts[1]), int(parts[2]), int(parts[3])
    ep          = await db_delete_episode(eid)
    if not ep:
        await cb.answer("❌ Topilmadi!", show_alert=True)
        return
    await cb.answer(f"✅ {ep['qism_raqami']}-qism o'chirildi!", show_alert=True)
    eps = await db_get_episodes(sid)
    if eps:
        try:
            await cb.message.edit_reply_markup(reply_markup=ik_episodes_delete(eps, sid, aid))
        except Exception:
            pass
    else:
        await cb.message.answer("✅ Barcha qismlar o'chirildi.", reply_markup=ik_admin_action(aid))


# ── Admin list shortcut ───────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_alist")
async def cb_adm_alist(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    animes = await db_all_animes()
    if not animes:
        await cb.message.answer("❌ Hali anime yo'q!", reply_markup=kb_admin())
        return
    b = InlineKeyboardBuilder()
    for a in animes:
        b.button(text=f"🎬 {a['kodi']} — {a['nomi']}", callback_data=f"aa_{a['id']}")
    b.button(text="🔙 Orqaga", callback_data="adm_back")
    b.adjust(1)
    try:
        await cb.message.edit_text("🎬 <b>Anime tanlang:</b>", reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception:
        await cb.message.answer("🎬 <b>Anime tanlang:</b>", reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("aa_"))
async def cb_aa(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        return
    aid = int(cb.data.split("_")[1])
    try:
        await cb.message.edit_text(
            f"⚙️ Anime ID: {aid}", reply_markup=ik_admin_action(aid)
        )
    except Exception:
        await cb.message.answer(f"⚙️ Anime ID: {aid}", reply_markup=ik_admin_action(aid))


# ── Admin Premium ──────────────────────────────────────────────────────────────

@router.message(F.text == "💎 Premium berish")
async def adm_give_premium_start(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    await state.set_state(AdminPremium.find)
    await msg.answer(
        "👤 Foydalanuvchi username yoki ID kiriting:", reply_markup=kb_cancel()
    )


@router.message(AdminPremium.find)
async def adm_give_premium_find(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_admin()); return
    txt  = msg.text.strip()
    user = None
    if txt.lstrip("@").isdigit():
        user = await db_get_user(int(txt.lstrip("@")))
    else:
        async with pool.acquire() as c:
            user = await c.fetchrow(
                "SELECT * FROM users WHERE username=$1", txt.lstrip("@")
            )
    if not user:
        await msg.answer("❌ Foydalanuvchi topilmadi.")
        return
    await state.update_data(gv_uid=user["telegram_id"], gv_name=user["ism"] or "?")
    await state.set_state(AdminPremium.tarif)
    await msg.answer(
        f"👤 <b>{user['ism']}</b> — tarifni tanlang:",
        reply_markup=ik_admin_tarif(), parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("gv_"), AdminPremium.tarif)
async def adm_give_premium_tarif(cb: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    tarif = cb.data.split("_")[1]
    d     = await state.get_data()
    uid   = d["gv_uid"]
    pe    = premium_end_date(tarif)
    await db_update_user(uid, premium=True, premium_tugash=pe)
    await state.clear()
    await cb.message.edit_text(
        f"✅ <b>{d['gv_name']}</b> ga {tarif_label(tarif)} premium berildi!\n"
        f"⏰ {pe.strftime('%d.%m.%Y')} gacha",
        parse_mode="HTML",
    )
    await cb.message.answer("👑 Admin paneli:", reply_markup=kb_admin())
    try:
        await bot.send_message(
            uid,
            f"🎉 <b>Premium faollashtirildi!</b>\n📦 {tarif_label(tarif)}\n"
            f"⏰ {pe.strftime('%d.%m.%Y')} gacha",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ── Create Post ───────────────────────────────────────────────────────────────

@router.message(F.text == "📝 Post yaratish")
async def adm_post_start(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    await state.set_state(CreatePost.media)
    await msg.answer("🖼 Post uchun rasm yoki video yuboring:", reply_markup=kb_cancel())


@router.message(CreatePost.media, F.photo | F.video)
async def adm_post_media(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    fid = msg.photo[-1].file_id if msg.photo else msg.video.file_id
    mt  = "photo" if msg.photo else "video"
    await state.update_data(post_fid=fid, post_mt=mt)
    await state.set_state(CreatePost.caption)
    await msg.answer("📝 Post matnini kiriting:", reply_markup=kb_cancel())


@router.message(CreatePost.caption)
async def adm_post_caption(msg: Message, state: FSMContext) -> None:
    if not is_admin(msg.from_user.id):
        return
    if msg.text == "❌ Bekor qilish":
        await state.clear(); await msg.answer("❌", reply_markup=kb_admin()); return
    await state.update_data(post_caption=msg.text)
    await state.set_state(CreatePost.anime_sel)
    animes = await db_all_animes()
    b      = InlineKeyboardBuilder()
    for a in animes:
        b.button(text=f"🎬 {a['kodi']} — {a['nomi']}", callback_data=f"posta_{a['id']}")
    b.button(text="🚀 Animesiz yuborish", callback_data="posta_none")
    b.adjust(1)
    await msg.answer("🎬 Qaysi animega link qo'shamiz?", reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("posta_"), CreatePost.anime_sel)
async def adm_post_send(cb: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not is_admin(cb.from_user.id):
        return
    d       = await state.get_data()
    fid     = d["post_fid"]
    mt      = d["post_mt"]
    caption = d["post_caption"]
    aid_str = cb.data.split("_")[1]
    kb      = None
    if aid_str != "none":
        aid = int(aid_str)
        kb  = ik_anime_watch_channel(aid)
    await state.clear()
    try:
        if mt == "video":
            await bot.send_video(CHANNEL_ID, video=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
        else:
            await bot.send_photo(CHANNEL_ID, photo=fid, caption=caption, reply_markup=kb, parse_mode="HTML")
        await cb.message.answer("✅ Post yuborildi!", reply_markup=kb_admin())
    except Exception as ex:
        await cb.message.answer(f"❌ Xato: {ex}", reply_markup=kb_admin())


# ──────────────────────────── AIOHTTP KEEP-ALIVE ────────────────────────────

async def health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def start_web_server() -> None:
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"✅ Web server started on port {PORT}")


# ──────────────────────────── MAIN ──────────────────────────────────────────

async def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in environment!")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in environment!")

    await init_db()
    await load_db_admins()

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await start_web_server()

    log.info("🚀 Bot ishga tushdi!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        if pool:
            await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
