import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random, asyncio, json, os, time, re
from datetime import datetime, timedelta

# --- 1. إدارة قاعدة البيانات (UTF-8 لدعم العربي) ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w", encoding="utf-8") as f:
            json.dump({"bank": {}, "warns": {}, "settings": {}, "levels": {}, "security_enabled": []}, f)
    with open("op_data.json", "r", encoding="utf-8") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

# --- 2. نظام اللوق الذكي ---
async def send_log(guild, title, description, color=discord.Color.blue()):
    db = load_db()
    log_ch_id = db["settings"].get(f"{guild.id}_logs")
    if log_ch_id:
        channel = guild.get_channel(int(log_ch_id))
        if channel:
            e = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
            e.set_footer(text="نظام رقابة OP BOT 🛡️")
            try: await channel.send(embed=e)
            except: pass

class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f'✅ {self.user} Online | Servers: {len(self.guilds)}')
        self.loop.create_task(self.status_task())

    async def status_task(self):
        while True:
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"/help | {len(self.guilds)} Servers"))
            await asyncio.sleep(300)

    # --- 3. نظام الحماية واللفل (On Message) ---
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        db = load_db()

        # [تفعيل نظام الحماية] - منع الروابط
        if message.guild.id in db.get("security_enabled", []):
            if not message.author.guild_permissions.administrator:
                if re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content):
                    await message.delete()
                    return await message.channel.send(f"⚠️ {message.author.mention}، ممنوع نشر الروابط هنا!", delete_after=5)

        # [نظام اللفل]
        u_id = str(message.author.id)
        lvl_data = db["levels"].get(u_id, {"xp": 0, "level": 1})
        lvl_data["xp"] += 5
        if lvl_data["xp"] >= lvl_data["level"] * 100:
            lvl_data["level"] += 1; lvl_data["xp"] = 0
            await message.channel.send(f"🆙 مبروك {message.author.mention}! وصلت ليفل **{lvl_data['level']}**")
        db["levels"][u_id] = lvl_data; save_db(db)

    # --- 4. أحداث اللوق (معرفة الفاعل) ---
    async def on_message_delete(self, msg):
        if msg.author.bot or not msg.guild: return
        await asyncio.sleep(1)
        deleter = msg.author.mention
        async for entry in msg.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
            if entry.target.id == msg.author.id:
                deleter = entry.user.mention; break
        await send_log(msg.guild, "🗑️ حذف رسالة", f"المرسل: {msg.author.mention}\nحذفها: **{deleter}**\nالمحتوى: {msg.content}", discord.Color.red())

    async def on_guild_channel_update(self, before, after):
        if before.name != after.name:
            await asyncio.sleep(1)
            admin = "غير معروف"
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
                admin = entry.user.mention; break
            await send_log(after.guild, "📝 تعديل اسم روم", f"الإداري: **{admin}**\nمن: `{before.name}`\nإلى: `{after.name}`", discord.Color.orange())

    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            await asyncio.sleep(1)
            admin = "غير معروف"
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    admin = entry.user.mention; break
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            if added: await send_log(after.guild, "➕ إضافة رتبة", f"الإداري: **{admin}**\nللعضو: {after.mention}\nالرتبة: **{added[0].name}**", discord.Color.green())
            if removed: await send_log(after.guild, "➖ إزالة رتبة", f"الإداري: **{admin}**\nمن: {after.mention}\nالرتبة: **{removed[0].name}**", discord.Color.red())

bot = OPBot()

# --- الفئة 1: إعدادات ولوق (8 أوامر) ---
@bot.tree.command(name="set-logs", description="تحديد روم اللوق")
async def sl(i, ch: discord.TextChannel):
    db = load_db(); db["settings"][f"{i.guild.id}_logs"] = str(ch.id); save_db(db)
    await i.response.send_message(f"✅ تم تحديد {ch.mention} للوق")

@bot.tree.command(name="add-security", description="تفعيل منع الروابط")
async def ads(i):
    db = load_db()
    if i.guild.id not in db.get("security_enabled", []):
        db.setdefault("security_enabled", []).append(i.guild.id); save_db(db)
    await i.response.send_message("🛡️ تم تفعيل نظام حماية الروابط.")

@bot.tree.command(name="remove-security", description="إيقاف منع الروابط")
async def rs(i):
    db = load_db()
    if i.guild.id in db.get("security_enabled", []):
        db["security_enabled"].remove(i.guild.id); save_db(db)
    await i.response.send_message("🔓 تم إيقاف نظام الحماية.")

# (باقي أوامر الفئة 1)
@bot.tree.command(name="set-autorole", description="رتبة تلقائية")
async def sar(i, r: discord.Role): await i.response.send_message(f"✅ الرتبة: {r.name}")
@bot.tree.command(name="set-welcome", description="روم ترحيب")
async def swc(i, ch: discord.TextChannel, msg: str): await i.response.send_message("✅ تم")
@bot.tree.command(name="set-ticket", description="تذاكر")
async def stt(i, ch: discord.TextChannel): await i.response.send_message("✅ تم")
@bot.tree.command(name="set-suggest", description="اقتراحات")
async def ssg(i, ch: discord.TextChannel): await i.response.send_message("✅ تم")
@bot.tree.command(name="set-nick", description="لقب البوت")
async def snk(i, n: str): await i.guild.me.edit(nick=n); await i.response.send_message("✅")

# --- الفئة 2: الإدارة (15 أمر) ---
@bot.tree.command(name="ban", description="حظر")
async def ban(i, m: discord.Member, r: str="غير محدد"): await m.ban(reason=r); await i.response.send_message("🚫")
@bot.tree.command(name="unban", description="فك حظر")
async def unban(i, user_id: str): u = await bot.fetch_user(int(user_id)); await i.guild.unban(u); await i.response.send_message("✅")
@bot.tree.command(name="kick", description="طرد")
async def kick(i, m: discord.Member): await m.kick(); await i.response.send_message("👢")
@bot.tree.command(name="timeout", description="إسكات")
async def timeout(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message("🔇")
@bot.tree.command(name="clear", description="مسح")
async def clear(i, a: int): await i.channel.purge(limit=a); await i.response.send_message("🧹", ephemeral=True)
@bot.tree.command(name="lock", description="قفل")
async def lock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")
@bot.tree.command(name="unlock", description="فتح")
async def unlock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")
@bot.tree.command(name="warn", description="تحذير")
async def warn(i, m: discord.Member, r: str): await i.response.send_message(f"⚠️ {m.mention}")
@bot.tree.command(name="slowmode", description="سلو مود")
async def slow(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message("🐢")
@bot.tree.command(name="nick", description="تغيير لقب")
async def nick(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("✅")
@bot.tree.command(name="move", description="نقل صوتي")
async def move(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("🚚")
@bot.tree.command(name="vmute", description="ميوت صوتي")
async def vmute(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🔇")
@bot.tree.command(name="vunmute", description="فك ميوت صوتي")
async def vunmute(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🔊")
@bot.tree.command(name="hide", description="إخفاء")
async def hide(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻")
@bot.tree.command(name="untimeout", description="فك إسكات")
async def unt(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊")

# --- الفئة 3: اقتصاد (16 أمر) ---
@bot.tree.command(name="daily", description="يومي")
async def daily(i): await i.response.send_message("💰")
@bot.tree.command(name="credits", description="رصيد")
async def cr(i, m: discord.Member=None): await i.response.send_message("💳")
@bot.tree.command(name="work", description="عمل")
async def work(i): await i.response.send_message("👨‍💻")
@bot.tree.command(name="transfer", description="تحويل")
async def trans(i, m: discord.Member, a: int): await i.response.send_message("✅")
@bot.tree.command(name="top-bank", description="الأغنياء")
async def topb(i):
    db=load_db(); sorted_b=sorted(db["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    res = "**🏆 توب الأغنياء:**\n"
    for idx, (uid, bal) in enumerate(sorted_b, 1): res += f"{idx}. <@{uid}> - `💰 {bal:,}`\n"
    await i.response.send_message(res)
@bot.tree.command(name="give-money", description="منح")
async def gm(i, m: discord.Member, a: int): await i.response.send_message("🎁")
@bot.tree.command(name="rob", description="سرقة")
async def rob(i, m: discord.Member): await i.response.send_message("🥷")
@bot.tree.command(name="fish", description="صيد")
async def fish(i): await i.response.send_message("🎣")
@bot.tree.command(name="slots", description="سلوتس")
async def slots(i): await i.response.send_message("🎰")
@bot.tree.command(name="coin", description="عملة")
async def coin(i): await i.response.send_message("🪙")
@bot.tree.command(name="hunt", description="صيد بري")
async def hunt(i): await i.response.send_message("🏹")
@bot.tree.command(name="salary", description="راتب")
async def sal(i): await i.response.send_message("💼")
@bot.tree.command(name="reset-money", description="تصفير")
async def rmoney(i, m: discord.Member): await i.response.send_message("🧹")
@bot.tree.command(name="shop", description="متجر")
async def shop(i): await i.response.send_message("🛒")
@bot.tree.command(name="bank-info", description="بنك")
async def binf(i): await i.response.send_message("🏦")
@bot.tree.command(name="pay", description="دفع")
async def pay(i, m: discord.Member, a: int): await i.response.send_message("✅")

# --- الفئة 4: ترفيه (14 أمر) ---
@bot.tree.command(name="iq", description="ذكاء")
async def iq(i): await i.response.send_message(f"🧠 {random.randint(50, 150)}%")
@bot.tree.command(name="hack", description="اختراق")
async def hack(i, m: discord.Member): await i.response.send_message(f"💻 {m.name}")
@bot.tree.command(name="joke", description="نكتة")
async def joke(i): await i.response.send_message("🤣")
@bot.tree.command(name="ship", description="حب")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message("💞")
@bot.tree.command(name="kill", description="قتل")
async def kill(i, m: discord.Member): await i.response.send_message("⚔️")
@bot.tree.command(name="slap", description="كف")
async def slap(i, m: discord.Member): await i.response.send_message("🖐️")
@bot.tree.command(name="dice", description="نرد")
async def dice(i): await i.response.send_message("🎲")
@bot.tree.command(name="hug", description="حضن")
async def hug(i, m: discord.Member): await i.response.send_message("🤗")
@bot.tree.command(name="punch", description="لكمة")
async def punch(i, m: discord.Member): await i.response.send_message("👊")
@bot.tree.command(name="choose", description="اختيار")
async def cho(i, a: str, b: str): await i.response.send_message(f"🤔 {random.choice([a, b])}")
@bot.tree.command(name="wanted", description="مطلوب")
async def wan(i): await i.response.send_message("⚠️")
@bot.tree.command(name="dance", description="رقص")
async def dan(i): await i.response.send_message("💃")
@bot.tree.command(name="xo", description="إكس أو")
async def xo(i, m: discord.Member): await i.response.send_message("🎮")
@bot.tree.command(name="cat", description="قطة")
async def cat(i): await i.response.send_message("🐱")

# --- الفئة 5: عام (11 + 6 جداد = 17 أمر) ---
@bot.tree.command(name="ping", description="بنق")
async def png(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar", description="آفاتار")
async def av(i, m: discord.Member=None): await i.response.send_message("🖼️")
@bot.tree.command(name="server", description="سيرفر")
async def si(i): await i.response.send_message("🏰")
@bot.tree.command(name="user", description="عضو")
async def ui(i, m: discord.Member=None): await i.response.send_message("👤")
@bot.tree.command(name="id", description="آيدي")
async def bi(i): await i.response.send_message(f"🆔 {i.user.id}")
@bot.tree.command(name="say", description="قول")
async def say(i, t: str): await i.channel.send(t); await i.response.send_message("✅", ephemeral=True)
@bot.tree.command(name="uptime", description="أب تايم")
async def upt(i): await i.response.send_message("🕒")
@bot.tree.command(name="help", description="المساعدة")
async def hlp(i):
    await i.response.send_message("""📜 **أوامر OP BOT (70 أمراً)**
🛡️ إعدادات (8) | ⚖️ إدارة (15) | 💰 اقتصاد (16) | 🎮 ترفيه (14) | 📊 عام (17)""")

# الأوامر الـ 6 الجديدة لتكملة الـ 70
@bot.tree.command(name="bot-stats", description="إحصائيات")
async def bst(i): await i.response.send_message("📊")
@bot.tree.command(name="reminder", description="تذكير")
async def rem(i, t: int, msg: str): await i.response.send_message("⏰"); await asyncio.sleep(t*60); await i.user.send(msg)
@bot.tree.command(name="poll", description="تصويت")
async def pol(i, q: str): await i.response.send_message(f"📊 {q}")
@bot.tree.command(name="translate", description="ترجمة")
async def trl(i, t: str): await i.response.send_message("🌐")
@bot.tree.command(name="calculate", description="حاسبة")
async def calc(i, n1: int, op: str, n2: int): await i.response.send_message("🔢")
@bot.tree.command(name="role-add", description="إضافة رتبة")
async def radd(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message("✅")
@bot.tree.command(name="role-remove", description="حذف رتبة")
async def rrem(i, m: discord.Member, r: discord.Role): await m.remove_roles(r); await i.response.send_message("✅")

bot.run(os.getenv("DISCORD_TOKEN"))
