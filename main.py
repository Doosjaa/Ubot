import os
import sys
import asyncio
import random
import string
import time
import sqlite3
from datetime import datetime, timezone

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, AuthKeyDuplicatedError
from telethon.sessions import StringSession
from telethon import functions

try:
    import psutil
    PSUTIL_AVAILABLE = True
except:
    PSUTIL_AVAILABLE = False

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
STRING_SESSION = os.getenv("STRING_SESSION", "")

BOT_NAME = "𝕺𝖔𝖔𝕭𝖔𝖙"
START_TIME = time.time()

client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    auto_reconnect=True,
    connection_retries=999999,
    retry_delay=5,
    request_retries=10,
    sequential_updates=True
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bot.db")

db = sqlite3.connect(DB_PATH)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS blacklist (
    chat_id INTEGER PRIMARY KEY
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS auto_reply (
    chat_id INTEGER PRIMARY KEY
)
""")


db.commit()

def load_blacklist():
    cursor.execute(
        "SELECT chat_id FROM blacklist"
    )
    return set(x[0] for x in cursor.fetchall())

blacklist = set()
auto_reply_groups = set()

def add_blacklist(chat_id):
    global blacklist

    cursor.execute(
        "INSERT OR IGNORE INTO blacklist VALUES (?)",
        (chat_id,)
    )

    db.commit()

    blacklist = load_blacklist()

def remove_blacklist(chat_id):
    global blacklist

    cursor.execute(
        "DELETE FROM blacklist WHERE chat_id=?",
        (chat_id,)
    )

    db.commit()

    blacklist = load_blacklist()

is_gcast_running = False
PROCESSED = set()

last_broadcast_errors = {
    "task_id": "None",
    "errors": []
}

OWNER_NAME = "Unknown"

def box(title, body):
    return f"""
<blockquote>
<b>{title}</b>

{body}
</blockquote>
"""

def gcast_progress_box(task_id, progress, ok, fa, sk, current, total):

    p_int = int(progress)

    bar = "█" * (p_int // 10) + "░" * (10 - (p_int // 10))

    return box(
        "📡 GCAST",
        f"""➠ progress : {p_int}%
➠ success : {ok}
➠ failed : {fa}
➠ skip : {sk}
➠ total : {current}/{total}

{bar}

➠ task_id : {task_id}
➠ owner : {OWNER_NAME}"""
    )

def gcast_success_box(task_id, ok, fa, total):

    return box(
        "✅ DONE",
        f"""➠ success : {ok}
➠ failed : {fa}
➠ total : {total}

➠ task_id : {task_id}
➠ owner : {OWNER_NAME}"""
    )

def uptime():

    s = int(time.time() - START_TIME)

    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)

    return f"{d}d {h}h {m}m {s}s"

def ram():

    if not PSUTIL_AVAILABLE:
        return "N/A"

    p = psutil.Process(os.getpid())

    return f"{p.memory_info().rss / 1024 / 1024:.2f} MB"

def gen(n=8):

    return ''.join(
        random.choice(
            string.ascii_letters + string.digits
        ) for _ in range(n)
    )

async def auto_delete(m, d=10800):

    await asyncio.sleep(d)

    try:
        await m.delete()
    except:
        pass

def old(e):

    return (
        datetime.now(timezone.utc) - e.message.date
    ).total_seconds() > 15

def safe_start():

    if not STRING_SESSION.strip():
        print("❌ STRING_SESSION kosong")
        sys.exit(1)

    try:
        client.start()

    except EOFError:
        print("❌ EOF Error - Session tidak valid")
        sys.exit(1)

    except AuthKeyDuplicatedError:
        print("❌ Session duplicate terdeteksi")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Gagal start bot: {e}")
        sys.exit(1)

@client.on(events.NewMessage(
    pattern=r'^\.menu$',
    outgoing=True
))
async def menu(e):

    text = f"""
╭──〔 {BOT_NAME} 〕──╮

➠ owner : {OWNER_NAME}
➠ ram : {ram()}
➠ uptime : {uptime()}

├──────────────
➠ .menu
➠ .ping
➠ .alive
➠ .stats
➠ .id
➠ .info
➠ .restart

├──────────────
➠ .gcast
➠ .ucast
➠ .cancel
➠ .bc-error

├──────────────
➠ .addbl
➠ .delbl
➠ .listbl

├──────────────
➠ .repwok
➠ .repoff
➠ .spm
➠ .spmoff
➠ .blck
➠ .unblck
➠ .q

╰────────────────
"""

    m = await e.reply(
        box("📋 MENU BOT", text),
        parse_mode='html'
    )

    asyncio.create_task(auto_delete(m))

@client.on(events.NewMessage(
    pattern=r'^\.ping$',
    outgoing=True
))
async def ping(e):

    s = time.time()

    m = await e.reply(
        box(
            "⚡ PING",
            "➠ checking..."
        ),
        parse_mode='html'
    )

    p = round((time.time() - s) * 1000)

    await m.edit(
        box(
            "⚡ PING",
            f"""➠ ping : {p} ms
➠ ram : {ram()}
➠ uptime : {uptime()}
➠ owner : {OWNER_NAME}"""
        ),
        parse_mode='html'
    )

    asyncio.create_task(auto_delete(m))

@client.on(events.NewMessage(
    pattern=r'^\.addbl$',
    outgoing=True
))
async def addbl(e):

    add_blacklist(e.chat_id)

    m = await e.reply(
        box(
            "🗂 BLACKLIST",
            f"""➠ status : added
➠ chat_id : {e.chat_id}
➠ total : {len(blacklist)}
➠ owner : {OWNER_NAME}"""
        ),
        parse_mode='html'
    )

    asyncio.create_task(auto_delete(m))

@client.on(events.NewMessage(
    pattern=r'^\.delbl$',
    outgoing=True
))
async def delbl(e):

    remove_blacklist(e.chat_id)

    m = await e.reply(
        box(
            "🗂 BLACKLIST",
            f"""➠ status : removed
➠ chat_id : {e.chat_id}
➠ total : {len(blacklist)}
➠ owner : {OWNER_NAME}"""
        ),
        parse_mode='html'
    )

    asyncio.create_task(auto_delete(m))

@client.on(events.NewMessage(
    pattern=r'^\.listbl$',
    outgoing=True
))
async def listbl(e):

    bl = load_blacklist()

    t = "\n".join(
        f"➠ {i}" for i in bl
    ) or "➠ empty"

    m = await e.reply(
        box(
            "🗂 BLACKLIST LIST",
            f"""{t}

➠ total : {len(bl)}
➠ owner : {OWNER_NAME}"""
        ),
        parse_mode='html'
    )

    asyncio.create_task(auto_delete(m))

@client.on(events.NewMessage(
    pattern=r'^\.q$',
    outgoing=True
))
async def quote(e):

    if not e.is_reply:

        m = await e.reply(
            box(
                "❌ QUOTLY",
                f"""➠ reply pesan target
➠ owner : {OWNER_NAME}"""
            ),
            parse_mode="html"
        )

        asyncio.create_task(auto_delete(m))
        return

    try:

        reply = await e.get_reply_message()

        status = await e.reply(
            box(
                "⏳ QUOTLY",
                "➠ membuat stiker..."
            ),
            parse_mode="html"
        )

        bot = "@QuotLyBot"

        before = await client.get_messages(
            bot,
            limit=1
        )

        last_id = before[0].id if before else 0

        await client.forward_messages(
            bot,
            reply
        )

        sticker = None

        for _ in range(30):

            await asyncio.sleep(1)

            msgs = await client.get_messages(
                bot,
                limit=5
            )

            for msg in msgs:

                if msg.id <= last_id:
                    continue

                if msg.sticker or msg.document:
                    sticker = msg
                    break

            if sticker:
                break

        if not sticker:
            raise Exception(
                "QuotLyBot tidak merespon"
            )

        await client.send_file(
            e.chat_id,
            sticker.media,
            reply_to=e.reply_to_msg_id
        )

        await status.delete()

    except Exception as ex:

        await status.edit(
            box(
                "❌ QUOTLY ERROR",
                f"""➠ {str(ex)}
➠ owner : {OWNER_NAME}"""
            ),
            parse_mode="html"
        )

        asyncio.create_task(
            auto_delete(status)
        )



@client.on(events.NewMessage(
    pattern=r'^\.alive$',
    outgoing=True
))
async def alive(e):
    await e.reply(
        box(
            "🟢 ALIVE",
            f"""➠ owner : {OWNER_NAME}
➠ uptime : {uptime()}
➠ ram : {ram()}"""
        ),
        parse_mode='html'
    )

@client.on(events.NewMessage(
    pattern=r'^\.stats$',
    outgoing=True
))
async def stats(e):
    groups = 0
    async for d in client.iter_dialogs():
        if d.is_group:
            groups += 1
    await e.reply(
        box(
            "📊 STATS",
            f"""➠ groups : {groups}
➠ blacklist : {len(blacklist)}
➠ ram : {ram()}
➠ uptime : {uptime()}"""
        ),
        parse_mode='html'
    )

@client.on(events.NewMessage(
    pattern=r'^\.id$',
    outgoing=True
))
async def idcmd(e):
    await e.reply(
        box(
            "🆔 ID",
            f"""➠ chat_id : {e.chat_id}
➠ user_id : {(await e.get_sender()).id}"""
        ),
        parse_mode='html'
    )

@client.on(events.NewMessage(
    pattern=r'^\.info$',
    outgoing=True
))
async def info(e):
    chat = await e.get_chat()
    await e.reply(
        box(
            "ℹ️ INFO",
            f"""➠ title : {getattr(chat, 'title', 'Private Chat')}
➠ chat_id : {e.chat_id}"""
        ),
        parse_mode='html'
    )

@client.on(events.NewMessage(
    pattern=r'^\.restart$',
    outgoing=True
))
async def restart(e):
    await e.reply(
        box("♻️ RESTART", "➠ restarting bot..."),
        parse_mode='html'
    )
    os.execv(sys.executable, [sys.executable] + sys.argv)

@client.on(events.NewMessage(
    pattern=r'^\.cancel$',
    outgoing=True
))
async def cancel(e):

    global is_gcast_running

    is_gcast_running = False

    m = await e.reply(
        box(
            "⛔ STOP",
            f"""➠ broadcast stopped
➠ owner : {OWNER_NAME}"""
        ),
        parse_mode='html'
    )

    asyncio.create_task(auto_delete(m))

@client.on(events.NewMessage(
    pattern=r'^\.bc-error$',
    outgoing=True
))
async def bc_error(e):

    er = last_broadcast_errors["errors"]

    if not er:

        m = await e.reply(
            box(
                "❌ ERROR",
                f"""➠ no errors
➠ owner : {OWNER_NAME}"""
            ),
            parse_mode='html'
        )

        asyncio.create_task(auto_delete(m))
        return

    t = ""

    for i in er[:20]:

        t += f"""➠ {i['chat_title']}
➠ {i['chat_id']}
➠ {i['reason']}

"""

    m = await e.reply(
        box(
            "❌ ERROR LIST",
            f"""{t}
➠ owner : {OWNER_NAME}"""
        ),
        parse_mode='html'
    )

    asyncio.create_task(auto_delete(m))

@client.on(events.NewMessage(
    pattern=r'^\.ucast$',
    outgoing=True
))
async def ucast(e):

    if not e.is_reply:

        m = await e.reply(
            box(
                "❌ UCAST",
                "➠ reply pesan target"
            ),
            parse_mode='html'
        )

        asyncio.create_task(auto_delete(m))
        return

    reply = await e.get_reply_message()

    me = await client.get_me()

    profile = f"""
<blockquote>
👤 PROFILE USER

➠ nama : {OWNER_NAME}
➠ id : {me.id}
➠ username : @{me.username if me.username else '-'}
</blockquote>
"""

    await client.send_message(
        e.chat_id,
        profile,
        parse_mode='html'
    )

    await client.forward_messages(
        e.chat_id,
        reply
    )

@client.on(events.NewMessage(
    pattern=r'^\.gcast$',
    outgoing=True
))
async def gcast(e):

    global is_gcast_running
    global PROCESSED

    if old(e) or is_gcast_running:
        return

    k = f"{e.chat_id}:{e.id}"

    if k in PROCESSED:
        return

    PROCESSED.add(k)

    if not e.is_reply:

        m = await e.reply(
            box(
                "❌ GCAST",
                f"""➠ reply target message
➠ owner : {OWNER_NAME}"""
            ),
            parse_mode='html'
        )

        asyncio.create_task(auto_delete(m))
        return

    is_gcast_running = True

    r = await e.get_reply_message()

    tid = gen()

    last_broadcast_errors["task_id"] = tid
    last_broadcast_errors["errors"] = []

    groups = []

    async for d in client.iter_dialogs():

        if not d.is_group:
            continue

        if d.id in blacklist:
            continue

        groups.append(d)

    total = len(groups)

    s = await e.reply(
        gcast_progress_box(
            tid,
            0,
            0,
            0,
            0,
            0,
            total
        ),
        parse_mode='html'
    )

    ok = 0
    fa = 0
    sk = 0
    pr = 0

    lt = time.time()

    try:

        for g in groups:

            if not is_gcast_running:
                break

            pr += 1

            try:

                await client.send_message(
                    g.id,
                    r.message,
                    file=r.media
                )

                ok += 1

                await asyncio.sleep(
                    random.uniform(6, 12)
                )

            except FloodWaitError as ex:

                fa += 1

                last_broadcast_errors["errors"].append({
                    "chat_title": g.name,
                    "chat_id": g.id,
                    "reason": f"FloodWait {ex.seconds}s"
                })

                await asyncio.sleep(ex.seconds)

            except Exception as ex:

                fa += 1

                last_broadcast_errors["errors"].append({
                    "chat_title": g.name,
                    "chat_id": g.id,
                    "reason": str(ex)
                })

            if time.time() - lt > 10:

                p = int(
                    (pr / total) * 100
                ) if total else 100

                await s.edit(
                    gcast_progress_box(
                        tid,
                        p,
                        ok,
                        fa,
                        sk,
                        pr,
                        total
                    ),
                    parse_mode='html'
                )

                lt = time.time()

    finally:
        is_gcast_running = False

    result_text = gcast_success_box(
        tid,
        ok,
        fa,
        total
    )

    await s.edit(
        result_text,
        parse_mode='html'
    )

    try:

        log_text = f"""
<blockquote>
📡 GCAST LOG

➠ task_id : {tid}
➠ success : {ok}
➠ failed : {fa}
➠ total : {total}
➠ owner : {OWNER_NAME}
➠ uptime : {uptime()}
</blockquote>
"""

        await client.send_message(
            "me",
            log_text,
            parse_mode='html'
        )

    except:
        pass



def load_autoreply():
    cursor.execute("SELECT chat_id FROM auto_reply")
    return set(x[0] for x in cursor.fetchall())

auto_reply_groups = set()

def add_autoreply(chat_id):
    global auto_reply_groups
    cursor.execute("INSERT OR IGNORE INTO auto_reply VALUES (?)", (chat_id,))
    db.commit()
    auto_reply_groups = load_autoreply()

def remove_autoreply(chat_id):
    global auto_reply_groups
    cursor.execute("DELETE FROM auto_reply WHERE chat_id=?", (chat_id,))
    db.commit()
    auto_reply_groups = load_autoreply()

AUTO_REPLY_TEXTS = [
    "wsup man","yo bro","mantap","boleh juga","valid","sabi",
    "iya juga","nah itu dia","asik","lanjut","setuju sih",
    "ngerti","siap","oke","masuk akal","noted",
    "wkwk bisa jadi","ga salah","menarik","cukup valid"
]

@client.on(events.NewMessage(pattern=r'^\.repwok$', outgoing=True))
async def autoreply_on(e):
    add_autoreply(e.chat_id)
    await e.reply(box("🤖 AUTO REPLY","➠ status : enabled"), parse_mode='html')

@client.on(events.NewMessage(pattern=r'^\.repoff$', outgoing=True))
async def autoreply_off(e):
    remove_autoreply(e.chat_id)
    await e.reply(box("🤖 AUTO REPLY","➠ status : disabled"), parse_mode='html')

@client.on(events.NewMessage(incoming=True))
async def auto_reply_handler(e):
    if e.chat_id not in auto_reply_groups:
        return
    if not e.is_group:
        return
    me = await client.get_me()
    if e.sender_id == me.id:
        return
    await asyncio.sleep(random.randint(2,5))
    await e.reply(random.choice(AUTO_REPLY_TEXTS))



@client.on(events.NewMessage(
    pattern=r'^\.blck$',
    outgoing=True
))
async def blck(e):

    if not e.is_reply:
        await e.reply(
            box("❌ BLOCK", "➠ reply target user"),
            parse_mode='html'
        )
        return

    reply = await e.get_reply_message()
    await client(functions.contacts.BlockRequest(reply.sender_id))

    await e.reply(
        box("🚫 BLOCK", f"➠ blocked : {reply.sender_id}"),
        parse_mode='html'
    )

@client.on(events.NewMessage(
    pattern=r'^\.unblck$',
    outgoing=True
))
async def unblck(e):

    if not e.is_reply:
        await e.reply(
            box("❌ UNBLOCK", "➠ reply target user"),
            parse_mode='html'
        )
        return

    reply = await e.get_reply_message()
    await client(functions.contacts.UnblockRequest(reply.sender_id))

    await e.reply(
        box("✅ UNBLOCK", f"➠ unblocked : {reply.sender_id}"),
        parse_mode='html'
    )


active_spm = {}

@client.on(events.NewMessage(
    pattern=r'^\.spm (.+)\s+\((\d+)\)$',
    outgoing=True
))
async def spm_start(e):

    text = e.pattern_match.group(1).strip()
    interval = int(e.pattern_match.group(2))

    chat_id = e.chat_id

    if chat_id in active_spm:
        active_spm[chat_id].cancel()

    async def spm_loop():
        while True:
            await asyncio.sleep(interval)
            await client.send_message(chat_id, text)

    task = asyncio.create_task(spm_loop())
    active_spm[chat_id] = task

    await e.reply(
        box(
            "📨 AUTO TEXT",
            f"""➠ status : enabled
➠ interval : {interval} detik
➠ text : {text}"""
        ),
        parse_mode='html'
    )

@client.on(events.NewMessage(
    pattern=r'^\.spmoff$',
    outgoing=True
))
async def spm_stop(e):

    chat_id = e.chat_id

    if chat_id not in active_spm:

        await e.reply(
            box(
                "📨 AUTO TEXT",
                "➠ tidak ada task aktif"
            ),
            parse_mode='html'
        )
        return

    active_spm[chat_id].cancel()
    del active_spm[chat_id]

    await e.reply(
        box(
            "📨 AUTO TEXT",
            "➠ status : disabled"
        ),
        parse_mode='html'
    )


print(BOT_NAME)

safe_start()

blacklist = load_blacklist()
auto_reply_groups = load_autoreply()

me = client.loop.run_until_complete(
    client.get_me()
)

OWNER_NAME = (
    f"{me.first_name or ''} "
    f"{me.last_name or ''}"
).strip() or "User"

print(f"✅ Login sebagai {OWNER_NAME}")

client.run_until_disconnected()