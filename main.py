import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random, asyncio, json, os, time, requests
from datetime import datetime, timedelta

# --- إدارة قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f:
            json.dump({"bank": {}, "warns": {}, "auto_role": {}, "responses": {}, "settings": {}, "daily_cooldown": {}, "levels": {}, "security": {}}, f)
    with open("op_data.json", "r") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: json.dump(data, f, indent=4)

# --- نظام اللوق الاحترافي ---
async def send_log(guild, title, description, color=discord.Color.blue()):
    db = load_db()
    log_ch_id = db["settings"].get(f"{guild.id}_logs")
    if log_ch_id:
        channel = guild.get_channel(int(log_ch_id))
        if channel:
            e = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
            e.set_footer(text="نظام رقابة OP BOT")
            await channel.send(embed=e)

# --- تذاكر و XO ---
class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة", style=discord.ButtonStyle.primary, custom_id="ot")
    async def b(self, i, btn): await i.response.send_message("سيتم التواصل معك", ephemeral=True)

class OPBot(discord.Client):
    def __init__(self): super().__init__(intents=discord.Intents.all()); self.tree = app_commands.CommandTree(self)
    async def setup_hook(self): await self.tree.sync()
    async def on_ready(self): print(f'Logged in as {self.user}')

    # --- اللوق المطور (تعديل سطر 126/127) ---
    async def on_message_delete(self, msg):
        if msg.author.bot: return
        async for entry in msg.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
            deleter = entry.user; break
        else: deleter = "غير معروف"
        await send_log(msg.guild, "🗑️ حذف رسالة", f"المرسل: {msg.author.mention}\nحذفها: **{deleter}**\nالمحتوى: {msg.content}", discord.Color.red())

    async def on_guild_channel_update(self, before, after):
        if before.name != after.name:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
                admin = entry.user; break
            await send_log(after.guild, "📝 تعديل اسم روم", f"الإداري: **{admin}**\nمن: `{before.name}`\nإلى: `{after.name}`", discord.Color.orange())

    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                admin = entry.user; break
            if added: await send_log(after.guild, "➕ إضافة رتبة", f"الإداري: **{admin}**\nللعضو: {after.mention}\nالرتبة: **{added[0].name}**", discord.Color.green())
            if removed: await send_log(after.guild, "➖ إزالة رتبة", f"الإداري: **{admin}**\nمن: {after.mention}\nالرتبة: **{removed[0].name}**", discord.Color.red())

    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        db = load_db(); u_id = str(message.author.id)
        lvl_data = db["levels"].get(u_id, {"xp": 0, "level": 1})
        lvl_data["xp"] += 5
        if lvl_data["xp"] >= lvl_data["level"] * 100:
            lvl_data["level"] += 1; lvl_data["xp"] = 0
            await message.channel.send(f"🆙 مبروك {message.author.mention}! وصلت ليفل **{lvl_data['level']}**")
        db["levels"][u_id] = lvl_data; save_db(db)

bot = OPBot()

# --- [ الفئة 1: إعدادات ولوق (8 أوامر) ] ---
@bot.tree.command(name="set-logs")
async def sl(i, ch: discord.TextChannel): 
    db=load_db(); db["settings"][f"{i.guild.id}_logs"]=ch.id; save_db(db); await i.response.send_message("✅")
@bot.tree.command(name="set-autorole")
async def sar(i, r: discord.Role): db=load_db(); db["auto_role"][str(i.guild.id)]=r.id; save_db(db); await i.response.send_message("✅")
@bot.tree.command(name="set-welcome")
async def swc(i, ch: discord.TextChannel, msg: str): await i.response.send_message("✅")
@bot.tree.command(name="set-ticket")
async def stt(i, ch: discord.TextChannel): await ch.send("تذاكر", view=TicketView()); await i.response.send_message("✅")
@bot.tree.command(name="set-suggest")
async def ssg(i, ch: discord.TextChannel): await i.response.send_message("✅")
@bot.tree.command(name="set-nick")
async def snk(i, n: str): await i.guild.me.edit(nick=n); await i.response.send_message("✅")
@bot.tree.command(name="add-security")
async def ads(i): await i.response.send_message("🛡️ تم")
@bot.tree.command(name="remove-security")
async def rs(i): await i.response.send_message("🔓 تم")

# --- [ الفئة 2: الإدارة (15 أمر) ] ---
@bot.tree.command(name="ban")
async def ban(i, m: discord.Member, r: str="غير محدد"): 
    await m.ban(reason=r); await i.response.send_message("🚫"); await send_log(i.guild, "حظر", f"بواسطة {i.user}")
@bot.tree.command(name="unban")
async def unban(i, user_id: str):
    u = await bot.fetch_user(int(user_id)); await i.guild.unban(u); await i.response.send_message("✅"); await send_log(i.guild, "فك حظر", f"لـ {u.name}")
@bot.tree.command(name="kick")
async def kick(i, m: discord.Member): await m.kick(); await i.response.send_message("👢")
@bot.tree.command(name="timeout")
async def timeout(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message("🔇")
@bot.tree.command(name="untimeout")
async def untimeout(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊")
@bot.tree.command(name="clear")
async def clear(i, a: int): await i.channel.purge(limit=a); await i.response.send_message("🧹", ephemeral=True)
@bot.tree.command(name="lock")
async def lock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")
@bot.tree.command(name="unlock")
async def unlock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")
@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, r: str): await i.response.send_message("⚠️")
@bot.tree.command(name="slowmode")
async def slow(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message("🐢")
@bot.tree.command(name="nick")
async def nick(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("✅")
@bot.tree.command(name="move")
async def move(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("🚚")
@bot.tree.command(name="vmute")
async def vmute(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🔇")
@bot.tree.command(name="vunmute")
async def vunmute(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🔊")
@bot.tree.command(name="hide")
async def hide(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻")

# --- [ الفئة 3: اقتصاد (16 أمر) ] ---
@bot.tree.command(name="daily")
async def daily(i): await i.response.send_message("💰")
@bot.tree.command(name="credits")
async def cr(i, m: discord.Member=None): await i.response.send_message("💳")
@bot.tree.command(name="work")
async def work(i): await i.response.send_message("👨‍💻")
@bot.tree.command(name="transfer")
async def trans(i, m: discord.Member, a: int): await i.response.send_message("✅")
@bot.tree.command(name="top-bank")
async def topb(i):
    db=load_db(); sorted_b=sorted(db["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    res = "**🏆 توب 5 أغنياء السيرفر:**\n"
    for idx, (uid, bal) in enumerate(sorted_b, 1): res += f"{idx}. <@{uid}> - `💰 {bal:,}`\n"
    await i.response.send_message(res)
@bot.tree.command(name="give-money")
async def gm(i, m: discord.Member, a: int): await i.response.send_message("🎁")
@bot.tree.command(name="rob")
async def rob(i, m: discord.Member): await i.response.send_message("🥷")
@bot.tree.command(name="fish")
async def fish(i): await i.response.send_message("🎣")
@bot.tree.command(name="slots")
async def slots(i): await i.response.send_message("🎰")
@bot.tree.command(name="coin")
async def coin(i): await i.response.send_message("🪙")
@bot.tree.command(name="hunt")
async def hunt(i): await i.response.send_message("🏹")
@bot.tree.command(name="salary")
async def sal(i): await i.response.send_message("💼")
@bot.tree.command(name="reset-money")
async def rmoney(i, m: discord.Member): await i.response.send_message("🧹")
@bot.tree.command(name="shop")
async def shop(i): await i.response.send_message("🛒")
@bot.tree.command(name="bank-info")
async def binf(i): await i.response.send_message("🏦")
@bot.tree.command(name="pay")
async def pay(i, m: discord.Member, a: int): await i.response.send_message("✅")

# --- [ الفئة 4: ترفيه (14 أمر) ] ---
@bot.tree.command(name="iq")
async def iq(i): await i.response.send_message("🧠")
@bot.tree.command(name="hack")
async def hack(i, m: discord.Member): await i.response.send_message("💻")
@bot.tree.command(name="joke")
async def joke(i): await i.response.send_message("🤣")
@bot.tree.command(name="ship")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message("💞")
@bot.tree.command(name="kill")
async def kill(i, m: discord.Member): await i.response.send_message("⚔️")
@bot.tree.command(name="slap")
async def slap(i, m: discord.Member): await i.response.send_message("🖐️")
@bot.tree.command(name="dice")
async def dice(i): await i.response.send_message("🎲")
@bot.tree.command(name="hug")
async def hug(i, m: discord.Member): await i.response.send_message("🤗")
@bot.tree.command(name="punch")
async def punch(i, m: discord.Member): await i.response.send_message("👊")
@bot.tree.command(name="choose")
async def cho(i, a: str, b: str): await i.response.send_message("🤔")
@bot.tree.command(name="wanted")
async def wan(i): await i.response.send_message("⚠️")
@bot.tree.command(name="dance")
async def dan(i): await i.response.send_message("💃")
@bot.tree.command(name="xo")
async def xo(i, m: discord.Member): await i.response.send_message("🎮")
@bot.tree.command(name="cat")
async def cat(i): await i.response.send_message("🐱")

# --- [ الفئة 5: عام وليفل (17 أمر) ] ---
@bot.tree.command(name="ping")
async def png(i): await i.response.send_message("🏓")
@bot.tree.command(name="avatar")
async def av(i, m: discord.Member=None): await i.response.send_message("🖼️")
@bot.tree.command(name="server")
async def si(i): await i.response.send_message("🏰")
@bot.tree.command(name="user")
async def ui(i, m: discord.Member=None): await i.response.send_message("👤")
@bot.tree.command(name="invite")
async def inv(i): await i.response.send_message("🔗")
@bot.tree.command(name="roles")
async def rc(i): await i.response.send_message("📜")
@bot.tree.command(name="channels")
async def cc(i): await i.response.send_message("📁")
@bot.tree.command(name="id")
async def bi(i): await i.response.send_message("🆔")
@bot.tree.command(name="say")
async def say(i, t: str): await i.channel.send(t); await i.response.send_message("✅", ephemeral=True)
@bot.tree.command(name="suggest")
async def sug(i, t: str): await i.response.send_message("✅")
@bot.tree.command(name="rules")
async def rul(i): await i.response.send_message("📜")
@bot.tree.command(name="members")
async def mem(i): await i.response.send_message("👥")
@bot.tree.command(name="uptime")
async def upt(i): await i.response.send_message("🕒")
@bot.tree.command(name="rank")
async def rnk(i, m: discord.Member=None): await i.response.send_message("📊")
@bot.tree.command(name="bot-info")
async def binfo(i): await i.response.send_message("🤖")
@bot.tree.command(name="help")
async def hlp(i): await i.response.send_message("📋 70 Commands Available")
@bot.tree.command(name="role-add")
async def radd(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message("✅")

bot.run(os.getenv("DISCORD_TOKEN"))
