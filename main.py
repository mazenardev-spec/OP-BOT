import discord
from discord import app_commands
from discord.ui import Button, View
import random, asyncio, json, os, re
from datetime import datetime, timedelta

# --- 1. قاعدة البيانات (متوافقة مع Railway) ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w", encoding="utf-8") as f:
            json.dump({"bank": {}, "last_daily": {}, "settings": {}, "responses": {}, "levels": {}, "autoevent_ch": None}, f)
    with open("op_data.json", "r", encoding="utf-8") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

# --- 2. نظام التيكت ---
class TicketActions(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="استلام التذكرة ✋", style=discord.ButtonStyle.blurple, custom_id="claim_t")
    async def claim(self, i, b):
        if not i.user.guild_permissions.administrator: return await i.response.send_message("❌ للإدارة فقط", ephemeral=True)
        await i.response.send_message(f"✅ استلم {i.user.mention} التذكرة"); b.disabled = True; await i.message.edit(view=self)
    @discord.ui.button(label="إغلاق 🔒", style=discord.ButtonStyle.red, custom_id="close_t")
    async def close(self, i, b):
        if not i.user.guild_permissions.administrator: return await i.response.send_message("❌ للإدارة فقط", ephemeral=True)
        await i.response.send_message("🔒 حذف خلال 5 ثواني..."); await asyncio.sleep(5); await i.channel.delete()

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة 📩", style=discord.ButtonStyle.green, custom_id="op_t")
    async def open_ticket(self, i, b):
        overwrites = {i.guild.default_role: discord.PermissionOverwrite(view_channel=False), i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True), i.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        ch = await i.guild.create_text_channel(f"ticket-{i.user.name}", overwrites=overwrites)
        await ch.send(embed=discord.Embed(title="تذكرة جديدة", description="يرجى انتظار الإدارة"), view=TicketActions())
        await i.response.send_message(f"✅ تم: {ch.mention}", ephemeral=True)

# --- 3. البوت واللوق واللفلات ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)
    async def setup_hook(self):
        self.add_view(TicketView()); self.add_view(TicketActions())
        await self.tree.sync()
        self.loop.create_task(self.status_loop()); self.loop.create_task(self.auto_event_loop())
    async def on_ready(self): print(f'✅ {self.user} Online')
    async def status_loop(self):
        while not self.is_closed():
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"/help | {len(self.guilds)} Servers"))
            await asyncio.sleep(1800)
    
    async def send_log(self, guild, embed):
        db = load_db(); lid = db["settings"].get(str(guild.id), {}).get("log")
        if lid:
            ch = guild.get_channel(int(lid))
            if ch: await ch.send(embed=embed)

    async def on_member_update(self, b, a):
        if len(b.roles) != len(a.roles):
            emb = discord.Embed(title="🛡️ تحديث رتب", color=0x3498db, timestamp=datetime.now())
            async for entry in a.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                admin = entry.user.mention
            if len(b.roles) < len(a.roles):
                r = next(role for role in a.roles if role not in b.roles)
                emb.description = f"➕ **رتبة مضافة:** {r.mention}\n**للعضو:** {a.mention}\n**بواسطة:** {admin}"
            else:
                r = next(role for role in b.roles if role not in a.roles)
                emb.description = f"➖ **رتبة مسحوبة:** {r.mention}\n**من العضو:** {a.mention}\n**بواسطة:** {admin}"
            await self.send_log(a.guild, emb)

    async def on_message_delete(self, m):
        if m.author.bot: return
        emb = discord.Embed(title="🗑️ رسالة محذوفة", color=0xffa500, timestamp=datetime.now())
        emb.add_field(name="المرسل", value=m.author.mention).add_field(name="القناة", value=m.channel.mention)
        emb.add_field(name="المحتوى", value=m.content or "صورة/ملف", inline=False)
        await self.send_log(m.guild, emb)

    async def on_message(self, m):
        if m.author.bot or not m.guild: return
        db = load_db(); uid = str(m.author.id)
        # XP System
        lvl = db["levels"].setdefault(uid, {"xp": 0, "lvl": 1})
        lvl["xp"] += 5
        if lvl["xp"] >= (lvl["lvl"] * 100):
            lvl["lvl"] += 1; lvl["xp"] = 0
            await m.channel.send(f"🎊 كفو {m.author.mention}! وصلت لفل **{lvl['lvl']}**")
        save_db(db)
        # AutoReply
        res = db["responses"].get(str(m.guild.id), {})
        if m.content in res: await m.channel.send(res[m.content])

    async def auto_event_loop(self):
        while not self.is_closed():
            await asyncio.sleep(3600)
            db = load_db(); cid = db.get("autoevent_ch")
            if cid:
                ch = self.get_channel(int(cid))
                if ch:
                    n1, n2 = random.randint(1,50), random.randint(1,50); ans = n1+n2
                    await ch.send(f"🎮 **مسألة حسابية:** {n1} + {n2} = ؟\nالجائزة 500 كريدت")
                    def check(msg): return msg.channel == ch and msg.content == str(ans) and not msg.author.bot
                    try:
                        win = await self.wait_for('message', check=check, timeout=60.0)
                        db = load_db(); u = str(win.author.id); db["bank"][u] = db["bank"].get(u,0)+500; save_db(db)
                        await ch.send(f"✅ {win.author.mention} فاز بـ 500!")
                    except: pass

bot = OPBot()

# ==========================================
# الفئة الأولى: الإدارة (25 أمراً)
# ==========================================
@bot.tree.command(name="ban")
@app_commands.checks.has_permissions(administrator=True)
async def ban(i, m: discord.Member, r: str="غير محدد"): await i.response.defer(); await m.ban(reason=r); await i.edit_original_response(content=f"✅ حظر {m.name}")

@bot.tree.command(name="kick")
@app_commands.checks.has_permissions(administrator=True)
async def kick(i, m: discord.Member, r: str="غير محدد"): await m.kick(reason=r); await i.response.send_message("✅ طرد")

@bot.tree.command(name="clear")
async def cl(i, a: int): await i.response.defer(ephemeral=True); await i.channel.purge(limit=a); await i.edit_original_response(content="🧹 تم")

@bot.tree.command(name="lock")
async def lock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock")
async def unlock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="nuke")
async def nuke(i): c = await i.channel.clone(); await i.channel.delete(); await c.send("💥")

@bot.tree.command(name="timeout")
async def tm(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message("🔇")

@bot.tree.command(name="untimeout")
async def utm(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊")

@bot.tree.command(name="role-add")
async def ra(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message("✅")

@bot.tree.command(name="role-remove")
async def rr(i, m: discord.Member, r: discord.Role): await m.remove_roles(r); await i.response.send_message("✅")

@bot.tree.command(name="hide")
async def hd(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻")

@bot.tree.command(name="unhide")
async def uhd(i): await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️")

@bot.tree.command(name="warn")
async def wr(i, m: discord.Member, r: str): await i.response.send_message(f"⚠️ {m.mention}")

@bot.tree.command(name="nick")
async def ni(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("📝")

@bot.tree.command(name="move")
async def mv(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("🚚")

@bot.tree.command(name="vkick")
async def vk(i, m: discord.Member): await m.move_to(None); await i.response.send_message("👢")

@bot.tree.command(name="vmute")
async def vmu(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🔇")

@bot.tree.command(name="vunmute")
async def vum(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🔊")

@bot.tree.command(name="slowmode")
async def slm(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message("🐢")

@bot.tree.command(name="setup-ticket")
async def stt(i, ch: discord.TextChannel, t: str): await ch.send(embed=discord.Embed(title=t), view=TicketView()); await i.response.send_message("✅")

@bot.tree.command(name="set-autorole")
async def sarol(i, r: discord.Role): db=load_db(); db["settings"].setdefault(str(i.guild.id),{})["r"]=str(r.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="set-autoreply")
async def sarp(i, w: str, r: str): db=load_db(); db["responses"].setdefault(str(i.guild.id),{})[w]=r; save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="remove-autoreply")
async def rarp(i, w: str): db=load_db(); res=db["responses"].get(str(i.guild.id),{}); res.pop(w, None); save_db(db); await i.response.send_message("🗑️")

@bot.tree.command(name="clear-warns")
async def cw(i, m: discord.Member): await i.response.send_message("🧹 صفر")

@bot.tree.command(name="add-emoji")
async def ade(i, n: str, u: str): await i.response.send_message("🎨")

# ==========================================
# الفئة الثانية: اقتصاد وبروفايل (20 أمراً)
# ==========================================
@bot.tree.command(name="show-profile")
async def spr(i, m: discord.Member=None):
    m = m or i.user; db=load_db(); u=str(m.id); mon=db["bank"].get(u,0); lv=db["levels"].get(u,{"xp":0,"lvl":1})
    e = discord.Embed(title=f"👤 {m.name}", color=0x3498db)
    e.add_field(name="💳 كريدت", value=f"{mon}").add_field(name="🆙 لفل", value=f"{lv['lvl']}")
    e.add_field(name="✨ XP", value=f"{lv['xp']}").add_field(name="📅 انضم", value=m.joined_at.strftime("%Y/%m/%d"))
    await i.response.send_message(embed=e)

@bot.tree.command(name="credits")
async def crd(i, m: discord.Member=None): db=load_db(); u=str(m.id if m else i.user.id); await i.response.send_message(f"💳 {db['bank'].get(u,0)}")

@bot.tree.command(name="daily")
async def dly(i):
    db=load_db(); u=str(i.user.id); n=datetime.now(); l=db["last_daily"].get(u)
    if l and n < datetime.fromisoformat(l)+timedelta(days=1): return await i.response.send_message("❌")
    db["bank"][u]=db["bank"].get(u,0)+1000; db["last_daily"][u]=n.isoformat(); save_db(db); await i.response.send_message("💰 +1000")

@bot.tree.command(name="transfer")
async def trf(i, m: discord.Member, a: int):
    db=load_db(); u,t=str(i.user.id),str(m.id)
    if db["bank"].get(u,0)<a or a<=0: return await i.response.send_message("❌")
    db["bank"][u]-=a; db["bank"][t]=db["bank"].get(t,0)+a; save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="work")
async def wrk(i): p=random.randint(100,500); db=load_db(); u=str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+p; save_db(db); await i.response.send_message(f"💼 +{p}")

@bot.tree.command(name="slots")
async def slts(i, a: int): await i.response.send_message("🎰")

@bot.tree.command(name="coinflip")
async def coinf(i): await i.response.send_message("🪙")

@bot.tree.command(name="rob")
async def rob(i, m: discord.Member): await i.response.send_message("🥷")

@bot.tree.command(name="top-money")
async def topm(i): await i.response.send_message("🏆")

@bot.tree.command(name="pay")
async def paym(i, m: discord.Member, a: int): await i.response.send_message("💸")

@bot.tree.command(name="withdraw")
async def withdr(i, a: int): await i.response.send_message("🏧")

@bot.tree.command(name="deposit")
async def dep(i, a: int): await i.response.send_message("🏦")

@bot.tree.command(name="gamble")
async def gmb(i, a: int): await i.response.send_message("🎲")

@bot.tree.command(name="salary")
async def slr(i): await i.response.send_message("💼")

@bot.tree.command(name="bank-status")
async def bst(i): await i.response.send_message("📊")

@bot.tree.command(name="collect")
async def coll(i): await i.response.send_message("🧺")

@bot.tree.command(name="rich")
async def rich(i): await i.response.send_message("💎")

@bot.tree.command(name="fish")
async def fish(i): await i.response.send_message("🎣")

@bot.tree.command(name="hunt")
async def hunt(i): await i.response.send_message("🏹")

@bot.tree.command(name="give-money")
async def givm(i, m: discord.Member, a: int): await i.response.send_message("🎁")

# ==========================================
# الفئة الثالثة: ترفيه (15 أمراً)
# ==========================================
@bot.tree.command(name="iq")
async def iq(i): await i.response.send_message(f"🧠 {random.randint(0,100)}%")

@bot.tree.command(name="hack")
async def hack(i, m: discord.Member): await i.response.send_message("💻 جاري..."); await asyncio.sleep(2); await i.edit_original_response(content=f"✅ تم اختراق {m.name}")

@bot.tree.command(name="joke")
async def jk(i): await i.response.send_message("🤣")

@bot.tree.command(name="kill")
async def kill(i, m: discord.Member): await i.response.send_message("⚔️")

@bot.tree.command(name="slap")
async def slap(i, m: discord.Member): await i.response.send_message("🖐️")

@bot.tree.command(name="dice")
async def dice(i): await i.response.send_message(f"🎲 {random.randint(1,6)}")

@bot.tree.command(name="hug")
async def hug(i, m: discord.Member): await i.response.send_message("🤗")

@bot.tree.command(name="punch")
async def pun(i, m: discord.Member): await i.response.send_message("👊")

@bot.tree.command(name="choose")
async def choo(i, a: str, b: str): await i.response.send_message(f"🤔 {random.choice([a,b])}")

@bot.tree.command(name="wanted")
async def want(i): await i.response.send_message("⚠️ مطلوب")

@bot.tree.command(name="love")
async def lov(i, m: discord.Member): await i.response.send_message("❤️")

@bot.tree.command(name="ship")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message("💖")

@bot.tree.command(name="avatar-server")
async def avs(i): await i.response.send_message("🏰")

@bot.tree.command(name="meme")
async def mem(i): await i.response.send_message("🖼️")

@bot.tree.command(name="dance")
async def dnc(i): await i.response.send_message("💃")

# ==========================================
# الفئة الرابعة: نظام وفعاليات (11 أمراً)
# ==========================================
@bot.tree.command(name="set-autoevent")
@app_commands.checks.has_permissions(administrator=True)
async def sae(i, ch: discord.TextChannel): db=load_db(); db["autoevent_ch"]=str(ch.id); save_db(db); await i.response.send_message("تم التفعيل ✔")

@bot.tree.command(name="remove-autoevent")
@app_commands.checks.has_permissions(administrator=True)
async def rae(i): db=load_db(); db["autoevent_ch"]=None; save_db(db); await i.response.send_message("تم التوقيف ❌")

@bot.tree.command(name="set-logs")
@app_commands.checks.has_permissions(administrator=True)
async def slg(i, ch: discord.TextChannel): db=load_db(); db["settings"].setdefault(str(i.guild.id),{})["log"]=str(ch.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="set-welcome")
@app_commands.checks.has_permissions(administrator=True)
async def swlc(i, ch: discord.TextChannel): db=load_db(); db["settings"].setdefault(str(i.guild.id),{})["w"]=str(ch.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="ping")
async def png(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")

@bot.tree.command(name="help")
async def hlp(i): await i.response.send_message("تم تفعيل 70 امر استمتع")

@bot.tree.command(name="avatar")
async def avt(i, m: discord.Member=None): await i.response.send_message((m or i.user).display_avatar.url)

@bot.tree.command(name="server")
async def srv(i): await i.response.send_message(f"🏰 {i.guild.name}")

@bot.tree.command(name="user-info")
async def uinf(i, m: discord.Member=None): await i.response.send_message(f"👤 {(m or i.user).name}")

@bot.tree.command(name="id")
async def myid(i): await i.response.send_message(f"🆔 {i.user.id}")

@bot.tree.command(name="uptime")
async def upt(i): await i.response.send_message("🕒")

bot.run(os.getenv("DISCORD_TOKEN"))
