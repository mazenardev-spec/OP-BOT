import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random, asyncio, json, os, time
from datetime import datetime, timedelta
from flask import Flask, render_template
from threading import Thread

# --- 1. نظام الداشبورد و الـ Keep Alive ---
app = Flask(__name__)

@app.route('/')
def home():
    try:
        db = load_db()
        # حساب إحصائيات سريعة للعرض في الداشبورد
        bank_data = db.get("bank", {})
        total_users = len(bank_data)
        total_money = sum(bank_data.values()) if bank_data else 0
        server_count = len(bot.guilds)
        
        return render_template('index.html', 
                               servers=server_count, 
                               users=total_users, 
                               economy=total_money)
    except Exception as e:
        return f"Dashboard is online, but error loading stats: {e}"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f:
            json.dump({"bank": {}, "warns": {}, "auto_role": {}, "responses": {}, "settings": {}, "daily_cooldown": {}, "levels": {}, "security": {}}, f)
    with open("op_data.json", "r") as f: 
        return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: 
        json.dump(data, f, indent=4)

# --- 3. أنظمة التفاعل (تيكت) ---
class TicketReasonModal(Modal, title="فتح تذكرة جديدة"):
    reason = TextInput(label="سبب التذكرة؟", placeholder="اكتب السبب هنا...", min_length=5)
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)
        await channel.send(f"مرحباً {interaction.user.mention}، سيتم الرد عليك قريباً.\nالسبب: {self.reason.value}", view=TicketActions())
        await interaction.response.send_message(f"✅ تم فتح تذكرتك: {channel.mention}", ephemeral=True)

class TicketActions(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="قفل التذكرة", style=discord.ButtonStyle.danger, custom_id="close_t")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة", style=discord.ButtonStyle.primary, custom_id="open_t")
    async def open_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketReasonModal())

# --- 4. فئة البوت والأحداث ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActions())
        await self.tree.sync()

    async def on_ready(self):
        activity = discord.Activity(type=discord.ActivityType.watching, name=f"/help | {len(self.guilds)} Servers")
        await self.change_presence(status=discord.Status.online, activity=activity)
        print(f'Logged in as {self.user}!')

    async def send_log(self, guild, embed):
        db = load_db()
        log_id = db["settings"].get(f"{guild.id}_logs")
        if log_id:
            ch = guild.get_channel(log_id)
            if ch: await ch.send(embed=embed)

    async def on_message_delete(self, m):
        if m.author.bot: return
        emb = discord.Embed(title="🗑️ حذف رسالة", color=0xff0000, timestamp=datetime.now())
        emb.add_field(name="المرسل:", value=m.author.mention).add_field(name="القناة:", value=m.channel.mention)
        emb.add_field(name="المحتوى:", value=m.content or "ملف/صورة", inline=False)
        await self.send_log(m.guild, emb)

    async def on_message_edit(self, b, a):
        if b.author.bot or b.content == a.content: return
        emb = discord.Embed(title="📝 تعديل رسالة", color=0xffa500, timestamp=datetime.now())
        emb.add_field(name="المرسل:", value=b.author.mention)
        emb.add_field(name="قبل:", value=b.content).add_field(name="بعد:", value=a.content)
        await self.send_log(b.guild, emb)

    async def on_member_update(self, b, a):
        if b.roles != a.roles:
            added = [r.mention for r in a.roles if r not in b.roles]
            removed = [r.mention for r in b.roles if r not in a.roles]
            emb = discord.Embed(title="🛡️ تحديث رتب العضو", color=0x3498db, timestamp=datetime.now())
            emb.set_author(name=a.name, icon_url=a.display_avatar.url)
            if added: emb.add_field(name="✅ رتب مضافة:", value=", ".join(added))
            if removed: emb.add_field(name="❌ رتب مسحوبة:", value=", ".join(removed))
            await self.send_log(a.guild, emb)

    async def on_guild_role_create(self, role):
        emb = discord.Embed(title="🆕 إنشاء رتبة جديدة", color=0x2ecc71, timestamp=datetime.now())
        emb.add_field(name="الاسم:", value=role.name).add_field(name="الآيدي:", value=role.id)
        await self.send_log(role.guild, emb)

    async def on_guild_role_delete(self, role):
        emb = discord.Embed(title="🔥 حذف رتبة", color=0xe74c3c, timestamp=datetime.now())
        emb.add_field(name="الاسم كان:", value=role.name)
        await self.send_log(role.guild, emb)

    async def on_message(self, message):
        if message.author.bot: return
        db = load_db()
        guild_responses = db["responses"].get(str(message.guild.id), {})
        if message.content in guild_responses:
            await message.channel.send(guild_responses[message.content])

    async def on_member_join(self, member):
        db = load_db()
        role_id = db["auto_role"].get(str(member.guild.id))
        if role_id:
            role = member.guild.get_role(int(role_id))
            if role:
                try: await member.add_roles(role)
                except: pass

bot = OPBot()

# --- الفئة 1: الإدارة ---
@bot.tree.command(name="set-autoreply", description="إضافة رد تلقائي")
@app_commands.checks.has_permissions(administrator=True)
async def setautoreply(i, word: str, reply: str):
    db = load_db(); gid = str(i.guild.id)
    if gid not in db["responses"]: db["responses"][gid] = {}
    db["responses"][gid][word] = reply; save_db(db)
    await i.response.send_message(f"✅ تم ضبط الرد")

@bot.tree.command(name="set-autorole", description="تحديد رتبة تلقائية")
async def setautorole(i, role: discord.Role):
    db = load_db(); db["auto_role"][str(i.guild.id)] = role.id; save_db(db)
    await i.response.send_message(f"✅ الرتبة: {role.mention}")

@bot.tree.command(name="set-ticket", description="إرسال نظام التذاكر")
async def setticket(i, channel: discord.TextChannel):
    embed = discord.Embed(title="الدعم الفني", description="اضغط لفتح تذكرة", color=0x3498db)
    await channel.send(embed=embed, view=TicketView()); await i.response.send_message("✅")

@bot.tree.command(name="set-logs", description="تحديد روم اللوج")
async def setlogs(i, channel: discord.TextChannel):
    db=load_db(); db["settings"][f"{i.guild.id}_logs"]=channel.id; save_db(db)
    await i.response.send_message("✅ تم")

@bot.tree.command(name="ban", description="حظر عضو")
async def ban(i, member: discord.Member, reason: str="غير محدد"):
    await member.ban(reason=reason); await i.response.send_message("✅")

@bot.tree.command(name="kick", description="طرد عضو")
async def kick(i, member: discord.Member, reason: str="غير محدد"):
    await member.kick(reason=reason); await i.response.send_message("✅")

@bot.tree.command(name="clear", description="مسح رسائل")
async def clear(i, amount: int):
    await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="lock", description="قفل")
async def lock(i):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock", description="فتح")
async def unlock(i):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="mute", description="إسكات")
async def mute(i, member: discord.Member, minutes: int):
    await member.timeout(timedelta(minutes=minutes)); await i.response.send_message("🔇")

@bot.tree.command(name="unmute", description="فك إسكات")
async def unmute(i, member: discord.Member):
    await member.timeout(None); await i.response.send_message("🔊")

@bot.tree.command(name="warn", description="تحذير")
async def warn(i, member: discord.Member, reason: str):
    db=load_db(); mid=str(member.id); db["warns"][mid]=db["warns"].get(mid,0)+1; save_db(db)
    await i.response.send_message("⚠️")

@bot.tree.command(name="slowmode", description="وضع بطيء")
async def slow(i, seconds: int):
    await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"🐢 {seconds}s")

@bot.tree.command(name="nick", description="لقب")
async def nick(i, member: discord.Member, name: str):
    await member.edit(nick=name); await i.response.send_message("✅")

@bot.tree.command(name="security", description="حماية")
async def sec(i, status: bool):
    db=load_db(); db["security"][str(i.guild.id)]=status; save_db(db)
    await i.response.send_message(f"🛡️ {status}")

# --- الفئة 2: الاقتصاد ---
@bot.tree.command(name="daily", description="يومي")
async def daily(i):
    db=load_db(); u=str(i.user.id); now=time.time()
    if now - db["daily_cooldown"].get(u,0) < 86400: return await i.response.send_message("❌ بكره")
    db["bank"][u]=db["bank"].get(u,0)+1000; db["daily_cooldown"][u]=now; save_db(db); await i.response.send_message("💰 +1000")

@bot.tree.command(name="credits", description="رصيد")
async def cr(i, member: discord.Member=None):
    m=member or i.user; await i.response.send_message(f"💳 {load_db()['bank'].get(str(m.id),0)}")

@bot.tree.command(name="work", description="عمل")
async def work(i):
    r=random.randint(50,300); db=load_db(); u=str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+r; save_db(db); await i.response.send_message(f"👷 {r}")

@bot.tree.command(name="transfer", description="تحويل")
async def trans(i, member: discord.Member, amount: int):
    db=load_db(); s=str(i.user.id); r=str(member.id)
    if db["bank"].get(s,0)<amount: return await i.response.send_message("❌");
    db["bank"][s]-=amount; db["bank"][r]=db["bank"].get(r,0)+amount; save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="top-bank", description="توب")
async def topb(i):
    top=sorted(load_db()["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    await i.response.send_message("\n".join([f"<@{u}>: {a}" for u,a in top]))

@bot.tree.command(name="give-money", description="منح")
async def gm(i, member: discord.Member, amount: int):
    db=load_db(); u=str(member.id); db["bank"][u]=db["bank"].get(u,0)+amount; save_db(db); await i.response.send_message("🎁")

@bot.tree.command(name="rob", description="سرقة")
async def rob(i, member: discord.Member): await i.response.send_message(random.choice(["نجحت", "فشلت"]))

@bot.tree.command(name="fish", description="صيد")
async def fish(i): await i.response.send_message(f"🎣 {random.randint(10,100)}")

@bot.tree.command(name="slots", description="سلوتس")
async def slots(i): await i.response.send_message("🎰")

@bot.tree.command(name="coin", description="عملة")
async def coin(i): await i.response.send_message(f"🪙 {random.choice(['ملك', 'كتابة'])}")

@bot.tree.command(name="hunt", description="صيد حيوان")
async def hunt(i): await i.response.send_message("🏹")

@bot.tree.command(name="salary", description="راتب")
async def sal(i): await i.response.send_message("💼 +200")

@bot.tree.command(name="shop", description="متجر")
async def shop(i): await i.response.send_message("🛒")

@bot.tree.command(name="bank-info", description="بنك")
async def binf(i): await i.response.send_message("🏦")

@bot.tree.command(name="reset-money", description="تصفير")
async def rmoney(i, member: discord.Member):
    db=load_db(); db["bank"][str(member.id)]=0; save_db(db); await i.response.send_message("🧹")

# --- الفئة 3: ترفيه ---
@bot.tree.command(name="iq", description="ذكاء")
async def iq(i): await i.response.send_message(f"🧠 {random.randint(1,200)}%")
@bot.tree.command(name="hack", description="اختراق")
async def hack(i, m: discord.Member): await i.response.send_message(f"💻 {m.name}")
@bot.tree.command(name="joke", description="نكتة")
async def joke(i): await i.response.send_message("مرة واحد...")
@bot.tree.command(name="ship", description="حب")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 {random.randint(1,100)}%")
@bot.tree.command(name="kill", description="قتل")
async def kill(i, m: discord.Member): await i.response.send_message(f"⚔️ {m.name}")
@bot.tree.command(name="slap", description="كف")
async def slap(i, m: discord.Member): await i.response.send_message(f"🖐️ {m.name}")
@bot.tree.command(name="dice", description="زار")
async def dice(i): await i.response.send_message(f"🎲 {random.randint(1,6)}")
@bot.tree.command(name="hug", description="حضن")
async def hug(i, m: discord.Member): await i.response.send_message(f"🤗")
@bot.tree.command(name="punch", description="لكمة")
async def punch(i, m: discord.Member): await i.response.send_message(f"👊")
@bot.tree.command(name="choose", description="اختيار")
async def cho(i, a: str, b: str): await i.response.send_message(f"🤔 {random.choice([a,b])}")
@bot.tree.command(name="love", description="حب البوت")
async def love(i): await i.response.send_message(f"❤️ {random.randint(1,100)}%")
@bot.tree.command(name="hot", description="جمال")
async def hot(i): await i.response.send_message(f"🔥 {random.randint(1,100)}%")
@bot.tree.command(name="wanted", description="مطلوب")
async def wan(i): await i.response.send_message("⚠️")
@bot.tree.command(name="dance", description="رقص")
async def dan(i): await i.response.send_message("💃")
@bot.tree.command(name="xo", description="تحدي")
async def xo(i, m: discord.Member): await i.response.send_message(f"🎮 {m.mention}")

# --- الفئة 4: عام ---
@bot.tree.command(name="help", description="أوامر")
async def hlp(i): await i.response.send_message("🛡️ | 💰 | 🎮 | 📁")
@bot.tree.command(name="ping", description="بنج")
async def png(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar", description="أفاتار")
async def av(i, m: discord.Member=None): m=m or i.user; await i.response.send_message(m.display_avatar.url)
@bot.tree.command(name="server-info", description="سيرفر")
async def si(i): await i.response.send_message(f"🏰 {i.guild.name}")
@bot.tree.command(name="user-info", description="معلوماتك")
async def ui(i, m: discord.Member=None): m=m or i.user; await i.response.send_message(f"👤 {m.name}")
@bot.tree.command(name="uptime", description="أونلاين")
async def upt(i): await i.response.send_message("🕒 Online")
@bot.tree.command(name="invite", description="رابط")
async def inv(i): await i.response.send_message("🔗")
@bot.tree.command(name="roles-count", description="رتب")
async def rc(i): await i.response.send_message(f"📜 {len(i.guild.roles)}")
@bot.tree.command(name="channels-count", description="قنوات")
async def cc(i): await i.response.send_message(f"📁 {len(i.guild.channels)}")
@bot.tree.command(name="bot-id", description="آيدي")
async def bi(i): await i.response.send_message(bot.user.id)
@bot.tree.command(name="say", description="تكرار")
async def say(i, t: str): await i.channel.send(t); await i.response.send_message("تم", ephemeral=True)
@bot.tree.command(name="suggest", description="اقتراح")
async def sug(i, t: str): await i.response.send_message("✅")
@bot.tree.command(name="rules", description="قوانين")
async def rul(i): await i.response.send_message("📜 القوانين")
@bot.tree.command(name="bot-info", description="عن البوت")
async def bti(i): await i.response.send_message("OP BOT v5.0")
@bot.tree.command(name="members", description="أعضاء")
async def mem(i): await i.response.send_message(f"👥 {i.guild.member_count}")

# --- التشغيل النهائي ---
if __name__ == "__main__":
    keep_alive() # تشغيل الداشبورد أونلاين
    bot.run(os.getenv("DISCORD_TOKEN"))
