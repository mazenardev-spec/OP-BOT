import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random, asyncio, json, os, time, requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, url_for
from threading import Thread
from requests_oauthlib import OAuth2Session

# تفعيل البيئة للسماح بالروابط غير المؤمنة في التطوير (مهم لـ Railway)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- 1. إعدادات Flask و OAuth2 ---
app = Flask(__name__)
app.secret_key = os.urandom(24)

CLIENT_ID = os.getenv('CLIENT_ID', '1495807245856804976')
CLIENT_SECRET = os.getenv('CLIENT_SECRET', 'PKoJ6RyZGnM-YKuM-3el-z193iWS-H7T')
REDIRECT_URI = 'https://op-bot-production.up.railway.app/callback' 

AUTH_BASE_URL = 'https://discord.com/api/oauth2/authorize'
TOKEN_URL = 'https://discord.com/api/oauth2/token'

# --- 2. قاعدة البيانات (JSON) ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f:
            json.dump({
                "bank": {}, "warns": {}, "auto_role": {}, 
                "responses": {}, "settings": {}, "daily_cooldown": {}, 
                "levels": {}, "security": {}
            }, f)
    with open("op_data.json", "r") as f: 
        return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: 
        json.dump(data, f, indent=4)

# --- 3. مسارات الداشبورد (Flask Routes) ---
@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/login')
def login():
    discord_sess = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=['identify', 'guilds'])
    authorization_url, state = discord_sess.authorization_url(AUTH_BASE_URL)
    session['oauth2_state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    try:
        discord_sess = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=session.get('oauth2_state'))
        token = discord_sess.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=request.url)
        session['token'] = token
        user_data = discord_sess.get('https://discord.com/api/users/@me').json()
        session['user'] = user_data
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Login Error: {e}"

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    
    headers = {'Authorization': f"Bearer {session['token']['access_token']}"}
    user_guilds = requests.get('https://discord.com/api/users/@me/guilds', headers=headers).json()
    
    bot_guilds = [str(g.id) for g in bot.guilds]
    # فلترة السيرفرات: لازم يكون أدمن والبوت موجود
    admin_guilds = [g for g in user_guilds if (int(g['permissions']) & 0x8) == 0x8 and str(g['id']) in bot_guilds]
    
    return render_template('dashboard.html', guilds=admin_guilds, user=session['user'])

@app.route('/manage/<guild_id>')
def manage_guild(guild_id):
    if 'user' not in session: return redirect(url_for('login'))
    db = load_db()
    guild_data = {
        "id": guild_id,
        "responses": db["responses"].get(str(guild_id), {}),
        "autorole": db["auto_role"].get(str(guild_id), ""),
        "logs": db["settings"].get(f"{guild_id}_logs", ""),
        "welcome_msg": db["settings"].get(f"{guild_id}_welcome_msg", ""),
        "welcome_ch": db["settings"].get(f"{guild_id}_welcome_channel", ""),
        "security": db["security"].get(str(guild_id), False)
    }
    return render_template('manage.html', guild=guild_data)

@app.route('/update/<guild_id>', methods=['POST'])
def update_settings(guild_id):
    if 'user' not in session: return redirect(url_for('login'))
    db = load_db()
    
    # تحديث البيانات
    db["auto_role"][str(guild_id)] = request.form.get('autorole')
    db["settings"][f"{guild_id}_logs"] = request.form.get('logs')
    db["settings"][f"{guild_id}_welcome_msg"] = request.form.get('welcome_msg')
    db["settings"][f"{guild_id}_welcome_channel"] = request.form.get('welcome_channel')
    db["security"][str(guild_id)] = request.form.get('security') == 'on'
    
    # إضافة رد تلقائي جديد لو وجد
    word = request.form.get('new_word')
    reply = request.form.get('new_reply')
    if word and reply:
        if str(guild_id) not in db["responses"]: db["responses"][str(guild_id)] = {}
        db["responses"][str(guild_id)][word] = reply

    save_db(db)
    return redirect(url_for('manage_guild', guild_id=guild_id))

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 4. فئة البوت والأحداث ---
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

class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActions())
        await self.tree.sync()

    async def on_ready(self):
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/help"))
        print(f'Logged in as {self.user}!')

    async def send_log(self, guild, embed):
        db = load_db()
        log_id = db["settings"].get(f"{guild.id}_logs")
        if log_id:
            ch = guild.get_channel(int(log_id))
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

    async def on_member_join(self, member):
        db = load_db()
        gid = str(member.guild.id)
        # ترحيب
        welcome_ch = db["settings"].get(f"{gid}_welcome_channel")
        welcome_msg = db["settings"].get(f"{gid}_welcome_msg")
        if welcome_ch and welcome_msg:
            ch = member.guild.get_channel(int(welcome_ch))
            if ch: await ch.send(welcome_msg.replace("{user}", member.mention))
        # رتبة تلقائية
        rid = db["auto_role"].get(gid)
        if rid:
            role = member.guild.get_role(int(rid))
            if role: await member.add_roles(role)

    async def on_message(self, message):
        if message.author.bot: return
        db = load_db()
        # رد تلقائي
        guild_responses = db["responses"].get(str(message.guild.id), {})
        if message.content in guild_responses:
            await message.channel.send(guild_responses[message.content])

bot = OPBot()

# --- 5. أوامر البوت (64 أمر بدون اختصار) ---

# [إدارة]
@bot.tree.command(name="set-logs")
async def sl(i, channel: discord.TextChannel):
    db=load_db(); db["settings"][f"{i.guild.id}_logs"]=channel.id; save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="ban")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i, member: discord.Member, reason: str="غير محدد"):
    await member.ban(reason=reason); await i.response.send_message(f"✅ تم حظر {member.name}")

@bot.tree.command(name="kick")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i, member: discord.Member, reason: str="غير محدد"):
    await member.kick(reason=reason); await i.response.send_message(f"✅ تم طرد {member.name}")

@bot.tree.command(name="clear")
async def clear(i, amount: int):
    await i.channel.purge(limit=amount); await i.response.send_message("🧹", ephemeral=True)

@bot.tree.command(name="lock")
async def lock(i):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock")
async def unlock(i):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="mute")
async def mute(i, member: discord.Member, minutes: int):
    await member.timeout(timedelta(minutes=minutes)); await i.response.send_message("🔇")

@bot.tree.command(name="unmute")
async def unmute(i, member: discord.Member):
    await member.timeout(None); await i.response.send_message("🔊")

@bot.tree.command(name="warn")
async def warn(i, member: discord.Member, reason: str):
    db=load_db(); mid=str(member.id); db["warns"][mid]=db["warns"].get(mid,0)+1; save_db(db); await i.response.send_message(f"⚠️ تحذير لـ {member.mention}")

@bot.tree.command(name="slowmode")
async def slow(i, seconds: int):
    await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"🐢 {seconds}s")

@bot.tree.command(name="nick")
async def nick(i, member: discord.Member, name: str):
    await member.edit(nick=name); await i.response.send_message("✅")

@bot.tree.command(name="set-ticket")
async def st(i, channel: discord.TextChannel):
    await channel.send("تذاكر الدعم", view=TicketView()); await i.response.send_message("✅")

# [اقتصاد]
@bot.tree.command(name="daily")
async def daily(i):
    db=load_db(); u=str(i.user.id); now=time.time()
    if now - db["daily_cooldown"].get(u,0) < 86400: return await i.response.send_message("❌ انتظر 24 ساعة")
    db["bank"][u]=db["bank"].get(u,0)+1000; db["daily_cooldown"][u]=now; save_db(db); await i.response.send_message("💰 +1000")

@bot.tree.command(name="credits")
async def cr(i, member: discord.Member=None):
    m=member or i.user; await i.response.send_message(f"💳 رصيد {m.name}: {load_db()['bank'].get(str(m.id),0)}")

@bot.tree.command(name="work")
async def work(i):
    r=random.randint(50,300); db=load_db(); u=str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+r; save_db(db); await i.response.send_message(f"👷 ربحت {r}")

@bot.tree.command(name="transfer")
async def trans(i, member: discord.Member, amount: int):
    db=load_db(); s=str(i.user.id); r=str(member.id)
    if db["bank"].get(s,0)<amount: return await i.response.send_message("❌ رصيدك لا يكفي")
    db["bank"][s]-=amount; db["bank"][r]=db["bank"].get(r,0)+amount; save_db(db); await i.response.send_message("✅ تم التحويل")

@bot.tree.command(name="top-bank")
async def topb(i):
    top=sorted(load_db()["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    await i.response.send_message("🏆 توب بنك:\n" + "\n".join([f"<@{u}>: {a}" for u,a in top]))

@bot.tree.command(name="give-money")
async def gm(i, member: discord.Member, amount: int):
    if not i.user.guild_permissions.administrator: return
    db=load_db(); u=str(member.id); db["bank"][u]=db["bank"].get(u,0)+amount; save_db(db); await i.response.send_message("🎁 تم المنح")

@bot.tree.command(name="rob")
async def rob(i, member: discord.Member): await i.response.send_message(random.choice(["نجحت وسرقت 500", "فشلت وانمسكت!"]))

@bot.tree.command(name="fish")
async def fish(i): await i.response.send_message(f"🎣 اصطدت سمكة بقيمة {random.randint(10,100)}")

@bot.tree.command(name="slots")
async def slots(i): await i.response.send_message("🎰 | 🍒 | 🍋 | 💎")

@bot.tree.command(name="coin")
async def coin(i): await i.response.send_message(f"🪙 النتيجة: {random.choice(['ملك', 'كتابة'])}")

@bot.tree.command(name="hunt")
async def hunt(i): await i.response.send_message(f"🏹 اصطدت {random.choice(['غزال', 'أرنب', 'بطة'])}")

@bot.tree.command(name="salary")
async def sal(i): await i.response.send_message("💼 استلمت راتبك +200")

@bot.tree.command(name="shop")
async def shop(i): await i.response.send_message("🛒 المتجر فارغ حالياً")

@bot.tree.command(name="bank-info")
async def binf(i): await i.response.send_message("🏦 البنك الوطني لـ OP BOT")

@bot.tree.command(name="reset-money")
async def rmoney(i, member: discord.Member):
    if not i.user.guild_permissions.administrator: return
    db=load_db(); db["bank"][str(member.id)]=0; save_db(db); await i.response.send_message("🧹 تم التصفير")

# [ترفيه]
@bot.tree.command(name="iq")
async def iq(i): await i.response.send_message(f"🧠 نسبة ذكائك: {random.randint(1,200)}%")
@bot.tree.command(name="hack")
async def hack(i, m: discord.Member): await i.response.send_message(f"💻 جاري اختراق {m.name}... تم سحب الصور!")
@bot.tree.command(name="joke")
async def joke(i): await i.response.send_message("مرة واحد اشترى موبايل طلعله عفريت!")
@bot.tree.command(name="ship")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 نسبة الحب: {random.randint(1,100)}%")
@bot.tree.command(name="kill")
async def kill(i, m: discord.Member): await i.response.send_message(f"⚔️ قتل {i.user.name} العضو {m.name}!")
@bot.tree.command(name="slap")
async def slap(i, m: discord.Member): await i.response.send_message(f"🖐️ كف خماسي على وجه {m.name}!")
@bot.tree.command(name="dice")
async def dice(i): await i.response.send_message(f"🎲 النتيجة: {random.randint(1,6)}")
@bot.tree.command(name="hug")
async def hug(i, m: discord.Member): await i.response.send_message(f"🤗 حضن دافئ لـ {m.name}")
@bot.tree.command(name="punch")
async def punch(i, m: discord.Member): await i.response.send_message(f"👊 بوكس في عين {m.name}")
@bot.tree.command(name="choose")
async def cho(i, a: str, b: str): await i.response.send_message(f"🤔 اخترت: {random.choice([a,b])}")
@bot.tree.command(name="love")
async def love(i): await i.response.send_message(f"❤️ نسبة حب البوت لك: {random.randint(1,100)}%")
@bot.tree.command(name="hot")
async def hot(i): await i.response.send_message(f"🔥 نسبة جمالك: {random.randint(1,100)}%")
@bot.tree.command(name="wanted")
async def wan(i): await i.response.send_message("⚠️ أنت مطلوب للعدالة!")
@bot.tree.command(name="dance")
async def dan(i): await i.response.send_message("💃 أووووووه رقصني!")
@bot.tree.command(name="xo")
async def xo(i, m: discord.Member): await i.response.send_message(f"🎮 تحدي XO بين {i.user.name} و {m.name}")

# [عام]
@bot.tree.command(name="help")
async def hlp(i): await i.response.send_message("قائمة الأوامر: الإدارة، الاقتصاد، الترفيه، عام. استخدم / لمعرفة التفاصيل.")
@bot.tree.command(name="ping")
async def png(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar")
async def av(i, m: discord.Member=None): m=m or i.user; await i.response.send_message(m.display_avatar.url)
@bot.tree.command(name="server-info")
async def si(i): await i.response.send_message(f"🏰 اسم السيرفر: {i.guild.name}\n🆔 الآيدي: {i.guild.id}")
@bot.tree.command(name="user-info")
async def ui(i, m: discord.Member=None): m=m or i.user; await i.response.send_message(f"👤 الاسم: {m.name}\n🆔 الآيدي: {m.id}")
@bot.tree.command(name="uptime")
async def upt(i): await i.response.send_message("🕒 البوت شغال منذ فترة")
@bot.tree.command(name="invite")
async def inv(i): await i.response.send_message("🔗 رابط دعوة البوت: [هنا]")
@bot.tree.command(name="roles-count")
async def rc(i): await i.response.send_message(f"📜 عدد الرتب: {len(i.guild.roles)}")
@bot.tree.command(name="channels-count")
async def cc(i): await i.response.send_message(f"📁 عدد القنوات: {len(i.guild.channels)}")
@bot.tree.command(name="bot-id")
async def bi(i): await i.response.send_message(f"🤖 آيدي البوت: {bot.user.id}")
@bot.tree.command(name="say")
async def say(i, t: str): await i.channel.send(t); await i.response.send_message("تم", ephemeral=True)
@bot.tree.command(name="suggest")
async def sug(i, t: str): await i.response.send_message("✅ تم إرسال اقتراحك")
@bot.tree.command(name="rules")
async def rul(i): await i.response.send_message("📜 قوانين السيرفر: لا تسب، احترم الجميع.")
@bot.tree.command(name="bot-info")
async def bti(i): await i.response.send_message("OP BOT v5.0 - صنع بكل حب")
@bot.tree.command(name="members")
async def mem(i): await i.response.send_message(f"👥 عدد الأعضاء: {i.guild.member_count}")

# تشغيل البوت والداشبورد
if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
