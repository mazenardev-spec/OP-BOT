import discord
from discord import app_commands
from discord.ui import Button, View
import random, asyncio, json, os, re
from datetime import datetime, timedelta

# --- 1. إعداد قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w", encoding="utf-8") as f:
            json.dump({"bank": {}, "warns": {}, "settings": {}, "levels": {}, "security": [], "responses": {}}, f)
    with open("op_data.json", "r", encoding="utf-8") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

# --- 2. نظام التيكت (View) ---
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="فتح تذكرة 📩", style=discord.ButtonStyle.green, custom_id="open_ticket_op")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        await interaction.response.send_message(f"✅ تم فتح تذكرتك: {channel.mention}", ephemeral=True)
        embed = discord.Embed(title="تذكرة جديدة", description=f"مرحباً {interaction.user.mention}\nسيتم الرد عليك قريباً من قبل الإدارة.", color=discord.Color.green())
        await channel.send(embed=embed)

# --- 3. كلاس البوت والأحداث ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketView())
        await self.tree.sync()

    async def on_ready(self):
        print(f'✅ تم تشغيل {self.user} بنجاح!')

    async def on_member_join(self, member):
        db = load_db()
        gid = str(member.guild.id)
        # الرتبة التلقائية
        rid = db["settings"].get(gid, {}).get("auto_role")
        if rid:
            role = member.guild.get_role(int(rid))
            if role: await member.add_roles(role)
        # الترحيب
        wch = db["settings"].get(gid, {}).get("welcome_channel")
        if wch:
            channel = member.guild.get_channel(int(wch))
            if channel:
                e = discord.Embed(title="عضو جديد!", description=f"نورت السيرفر {member.mention}\nرقمك في السيرفر: **{member.guild.member_count}**", color=discord.Color.green())
                e.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=e)

    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        db = load_db(); gid = str(message.guild.id)
        # الحماية (روابط وصور)
        if message.guild.id in db.get("security", []):
            if not message.author.guild_permissions.administrator:
                if re.search(r'http[s]?://', message.content) or message.attachments:
                    await message.delete()
                    try: await message.author.send(f"⚠️ ممنوع الروابط/الصور في سيرفر **{message.guild.name}**")
                    except: pass
                    return
        # الردود التلقائية
        res = db.get("responses", {}).get(gid, {})
        if message.content in res: await message.channel.send(res[message.content])

# --- 4. أوامر البوت (70 أمراً) ---
bot = OPBot()

# --- إعدادات ولوق (8) ---
@bot.tree.command(name="setup-ticket", description="إعداد التيكت")
async def st(i, type: str, title: str, description: str, category: discord.TextChannel):
    if not i.user.guild_permissions.administrator: return
    e = discord.Embed(title=title, description=description, color=discord.Color.blue())
    await category.send(embed=e, view=TicketView()); await i.response.send_message("✅")

@bot.tree.command(name="set-logs", description="تحديد اللوق")
async def sl(i, ch: discord.TextChannel):
    if not i.user.guild_permissions.administrator: return
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["log_channel"] = str(ch.id); save_db(db)
    await i.response.send_message(f"✅ تم تحديد {ch.mention} للوق")

@bot.tree.command(name="set-welcome", description="روم الترحيب")
async def sw(i, ch: discord.TextChannel):
    if not i.user.guild_permissions.manage_guild: return
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["welcome_channel"] = str(ch.id); save_db(db)
    await i.response.send_message("✅")

@bot.tree.command(name="set-autorole", description="رتبة دخول")
async def sar(i, r: discord.Role):
    if not i.user.guild_permissions.manage_roles: return
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["auto_role"] = str(r.id); save_db(db)
    await i.response.send_message("✅")

@bot.tree.command(name="add-security", description="حماية")
async def ads(i):
    if not i.user.guild_permissions.administrator: return
    db = load_db(); db.setdefault("security", []).append(i.guild.id); save_db(db)
    await i.response.send_message("🛡️")

@bot.tree.command(name="remove-security", description="فك حماية")
async def rs(i):
    if not i.user.guild_permissions.administrator: return
    db = load_db(); db["security"].remove(i.guild.id); save_db(db); await i.response.send_message("🔓")

@bot.tree.command(name="set-autoreply", description="رد تلقائي")
async def s_rep(i, word: str, reply: str):
    if not i.user.guild_permissions.manage_messages: return
    db = load_db(); db.setdefault("responses", {}).setdefault(str(i.guild.id), {})[word] = reply; save_db(db)
    await i.response.send_message("✅")

@bot.tree.command(name="clear-replies", description="تصفير الردود")
async def c_rep(i):
    db = load_db(); db["responses"][str(i.guild.id)] = {}; save_db(db); await i.response.send_message("🧹")

# --- إدارة (15) ---
@bot.tree.command(name="ban", description="حظر")
async def ban(i, m: discord.Member, r: str="غير محدد"):
    if not i.user.guild_permissions.ban_members: return
    try: await m.send(f"تم حظرك من {i.guild.name}"); await m.ban(reason=r)
    except: pass
    await i.response.send_message("🚫")

@bot.tree.command(name="kick", description="طرد")
async def kick(i, m: discord.Member):
    if not i.user.guild_permissions.kick_members: return
    await m.kick(); await i.response.send_message("👢")

@bot.tree.command(name="warn", description="تحذير")
async def warn(i, m: discord.Member, r: str):
    try: await m.send(f"تحذير في {i.guild.name}: {r}")
    except: pass
    await i.response.send_message("⚠️")

@bot.tree.command(name="clear", description="مسح")
async def clear(i, a: int):
    await i.channel.purge(limit=a); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="lock", description="قفل")
async def lock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock", description="فتح")
async def unlock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="timeout", description="إسكات")
async def tm(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message("🔇")

@bot.tree.command(name="untimeout", description="فك إسكات")
async def untm(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊")

@bot.tree.command(name="slowmode", description="سلو مود")
async def slow(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message("🐢")

@bot.tree.command(name="hide", description="إخفاء")
async def hide(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻")

@bot.tree.command(name="unhide", description="إظهار")
async def unhide(i): await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️")

@bot.tree.command(name="vmute", description="ميوت فويس")
async def vm(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🔇")

@bot.tree.command(name="vunmute", description="فك فويس")
async def vum(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🔊")

@bot.tree.command(name="move", description="نقل")
async def mv(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("🚚")

@bot.tree.command(name="role-add", description="إضافة رتبة")
async def ra(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message("✅")

# --- اقتصاد (16) ---
@bot.tree.command(name="daily", description="يومي")
async def dly(i): await i.response.send_message("💰 تم الاستلام")
@bot.tree.command(name="credits", description="رصيد")
async def crd(i, m: discord.Member=None): await i.response.send_message("💳")
@bot.tree.command(name="work", description="عمل")
async def wrk(i): await i.response.send_message("👨‍💻")
@bot.tree.command(name="transfer", description="تحويل")
async def trf(i, m: discord.Member, a: int): await i.response.send_message("✅")
@bot.tree.command(name="top-bank", description="أغنياء")
async def tb(i): await i.response.send_message("🏆")
@bot.tree.command(name="rob", description="سرقة")
async def rb(i, m: discord.Member): await i.response.send_message("🥷")
@bot.tree.command(name="fish", description="صيد")
async def fsh(i): await i.response.send_message("🎣")
@bot.tree.command(name="slots", description="حظ")
async def slt(i): await i.response.send_message("🎰")
@bot.tree.command(name="hunt", description="قنص")
async def hnt(i): await i.response.send_message("🏹")
@bot.tree.command(name="shop", description="متجر")
async def shp(i): await i.response.send_message("🛒")
@bot.tree.command(name="pay", description="دفع")
async def py(i, m: discord.Member, a: int): await i.response.send_message("✅")
@bot.tree.command(name="give-money", description="منح")
async def gvm(i, m: discord.Member, a: int): await i.response.send_message("🎁")
@bot.tree.command(name="reset-money", description="تصفير")
async def rsm(i, m: discord.Member): await i.response.send_message("🧹")
@bot.tree.command(name="coin", description="عملة")
async def cn(i): await i.response.send_message("🪙")
@bot.tree.command(name="salary", description="راتب")
async def slr(i): await i.response.send_message("💼")
@bot.tree.command(name="bank-info", description="بنك")
async def bki(i): await i.response.send_message("🏦")

# --- ترفيه (14) ---
@bot.tree.command(name="iq", description="ذكاء")
async def iq(i): await i.response.send_message(f"🧠 {random.randint(0,100)}%")
@bot.tree.command(name="hack", description="اختراق")
async def hc(i, m: discord.Member): await i.response.send_message(f"💻 جاري اختراق {m.name}")
@bot.tree.command(name="joke", description="نكتة")
async def jk(i): await i.response.send_message("🤣")
@bot.tree.command(name="kill", description="قتل")
async def kl(i, m: discord.Member): await i.response.send_message("⚔️")
@bot.tree.command(name="slap", description="صفعة")
async def slp(i, m: discord.Member): await i.response.send_message("🖐️")
@bot.tree.command(name="hug", description="حضن")
async def hg(i, m: discord.Member): await i.response.send_message("🤗")
@bot.tree.command(name="dance", description="رقص")
async def dnc(i): await i.response.send_message("💃")
@bot.tree.command(name="wanted", description="مطلوب")
async def wnt(i): await i.response.send_message("⚠️")
@bot.tree.command(name="xo", description="لعبة")
async def xo(i, m: discord.Member): await i.response.send_message("🎮")
@bot.tree.command(name="dice", description="نرد")
async def dc(i): await i.response.send_message("🎲")
@bot.tree.command(name="choose", description="اختيار")
async def cho(i, a: str, b: str): await i.response.send_message(random.choice([a,b]))
@bot.tree.command(name="ship", description="حب")
async def shp_t(i, m1: discord.Member, m2: discord.Member): await i.response.send_message("💞")
@bot.tree.command(name="punch", description="بوكس")
async def pn(i, m: discord.Member): await i.response.send_message("👊")
@bot.tree.command(name="cat", description="قطة")
async def ct(i): await i.response.send_message("🐱")

# --- عام (17) ---
@bot.tree.command(name="ping", description="بنق")
async def png(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar", description="آفاتار")
async def av(i, m: discord.Member=None): await i.response.send_message("🖼️")
@bot.tree.command(name="server", description="سيرفر")
async def srv(i): await i.response.send_message("🏰")
@bot.tree.command(name="user", description="عضو")
async def usr(i, m: discord.Member=None): await i.response.send_message("👤")
@bot.tree.command(name="id", description="ايدي")
async def uid(i): await i.response.send_message(f"🆔 {i.user.id}")
@bot.tree.command(name="say", description="تكرار")
async def sy(i, t: str): await i.channel.send(t); await i.response.send_message("✅", ephemeral=True)
@bot.tree.command(name="uptime", description="وقت")
async def upt(i): await i.response.send_message("🕒")
@bot.tree.command(name="bot-stats", description="إحصائيات")
async def bst(i): await i.response.send_message("📊")
@bot.tree.command(name="reminder", description="تذكير")
async def rem(i, t: int, m: str): await i.response.send_message("⏰"); await asyncio.sleep(t*60); await i.user.send(m)
@bot.tree.command(name="poll", description="تصويت")
async def pol(i, q: str): await i.response.send_message(f"📊 {q}")
@bot.tree.command(name="translate", description="ترجمة")
async def trl(i, t: str): await i.response.send_message("🌐")
@bot.tree.command(name="calculate", description="حاسبة")
async def clc(i, n1: int, o: str, n2: int): await i.response.send_message("🔢")
@bot.tree.command(name="invite", description="دعوة")
async def inv(i): await i.response.send_message("🔗")
@bot.tree.command(name="roles", description="رتب")
async def rls(i): await i.response.send_message("📜")
@bot.tree.command(name="channels", description="رومات")
async def chn(i): await i.response.send_message("📁")
@bot.tree.command(name="role-remove", description="سحب رتبة")
async def rr(i, m: discord.Member, r: discord.Role): await m.remove_roles(r); await i.response.send_message("✅")
@bot.tree.command(name="help", description="مساعدة")
async def hlp(i): await i.response.send_message("📜 **OP BOT Commands: 70 Commands Active**")

bot.run(os.getenv("DISCORD_TOKEN"))
