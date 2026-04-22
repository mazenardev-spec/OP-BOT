import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random, asyncio, json, os, time, requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, url_for
from threading import Thread
from requests_oauthlib import OAuth2Session

# إعدادات البيئة
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app = Flask(__name__)
app.secret_key = os.urandom(24)

CLIENT_ID = os.getenv('CLIENT_ID', '1495807245856804976')
CLIENT_SECRET = os.getenv('CLIENT_SECRET', 'PKoJ6RyZGnM-YKuM-3el-z193iWS-H7T')
REDIRECT_URI = 'https://op-bot-production.up.railway.app/callback'
AUTH_BASE_URL = 'https://discord.com/api/oauth2/authorize'
TOKEN_URL = 'https://discord.com/api/oauth2/token'

# --- إدارة قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f:
            json.dump({"bank": {}, "warns": {}, "auto_role": {}, "responses": {}, "settings": {}, "daily_cooldown": {}, "levels": {}, "security": {}}, f)
    with open("op_data.json", "r") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: json.dump(data, f, indent=4)

# --- مسارات الـ Flask ---
@app.route('/')
def home(): return render_template('index.html', user=session.get('user'))

@app.route('/login')
def login():
    discord_sess = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=['identify', 'guilds'])
    auth_url, state = discord_sess.authorization_url(AUTH_BASE_URL)
    session['oauth2_state'] = state
    return redirect(auth_url)

@app.route('/callback')
def callback():
    try:
        discord_sess = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=session.get('oauth2_state'))
        token = discord_sess.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=request.url)
        session['token'] = token
        session['user'] = discord_sess.get('https://discord.com/api/users/@me').json()
        return redirect(url_for('dashboard'))
    except: return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    headers = {'Authorization': f"Bearer {session['token']['access_token']}"}
    user_guilds = requests.get('https://discord.com/api/users/@me/guilds', headers=headers).json()
    if not isinstance(user_guilds, list): return "خطأ، سجل دخول مجدداً."
    admin_guilds = [g for g in user_guilds if (int(g['permissions']) & 0x8) == 0x8]
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
    db = load_db()
    db["auto_role"][str(guild_id)] = request.form.get('autorole')
    db["settings"][f"{guild_id}_logs"] = request.form.get('logs')
    db["settings"][f"{guild_id}_welcome_msg"] = request.form.get('welcome_msg')
    db["settings"][f"{guild_id}_welcome_channel"] = request.form.get('welcome_channel')
    db["security"][str(guild_id)] = request.form.get('security') == 'on'
    save_db(db)
    return redirect(url_for('manage_guild', guild_id=guild_id))

# --- تذاكر الدعم ---
class TicketReasonModal(Modal, title="فتح تذكرة"):
    reason = TextInput(label="السبب", placeholder="اكتب السبب هنا...", min_length=5)
    async def on_submit(self, interaction: discord.Interaction):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)
        await channel.send(f"تذكرة جديدة من {interaction.user.mention}\nالسبب: {self.reason.value}", view=TicketActions())
        await interaction.response.send_message(f"✅ تم فتح التذكرة: {channel.mention}", ephemeral=True)

class TicketActions(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="قفل", style=discord.ButtonStyle.danger, custom_id="close_t")
    async def close(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.delete()

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة", style=discord.ButtonStyle.primary, custom_id="open_t")
    async def open_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketReasonModal())

# --- كلاس البوت ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)
    async def setup_hook(self):
        self.add_view(TicketView()); self.add_view(TicketActions())
        await self.tree.sync()
    async def on_ready(self):
        print(f'Logged in as {self.user}!')
        self.loop.create_task(self.status_task())
    async def status_task(self):
        while True:
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"/help | {len(self.guilds)} Servers"))
            await asyncio.sleep(300)
    async def on_message(self, message):
        if message.author.bot: return
        db = load_db()
        # الردود التلقائية
        res = db["responses"].get(str(message.guild.id), {})
        if message.content in res: await message.channel.send(res[message.content])
        # الحماية
        if db["security"].get(str(message.guild.id)) and ("http" in message.content or len(message.content) > 500):
            await message.delete(); await message.channel.send(f"⚠️ {message.author.mention} ممنوع الروابط/السبام", delete_after=5)

bot = OPBot()

# --- قائمة الـ 64 أمر كاملة ---

# [إعدادات - SET]
@bot.tree.command(name="set-logs")
async def sl(i, ch: discord.TextChannel):
    db=load_db(); db["settings"][f"{i.guild.id}_logs"]=ch.id; save_db(db); await i.response.send_message("✅")
@bot.tree.command(name="set-autorole")
async def sar(i, r: discord.Role):
    db=load_db(); db["auto_role"][str(i.guild.id)]=r.id; save_db(db); await i.response.send_message("✅")
@bot.tree.command(name="set-welcome")
async def swc(i, ch: discord.TextChannel, msg: str):
    db=load_db(); db["settings"][f"{i.guild.id}_welcome_channel"]=ch.id; db["settings"][f"{i.guild.id}_welcome_msg"]=msg; save_db(db); await i.response.send_message("✅")
@bot.tree.command(name="set-ticket")
async def st(i, ch: discord.TextChannel):
    await ch.send("تذاكر الدعم", view=TicketView()); await i.response.send_message("✅")

# [إدارة - ADMIN]
@bot.tree.command(name="ban")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i, m: discord.Member, r: str="غير محدد"): await m.ban(reason=r); await i.response.send_message(f"✅ تم حظر {m}")
@bot.tree.command(name="kick")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i, m: discord.Member, r: str="غير محدد"): await m.kick(reason=r); await i.response.send_message(f"✅ تم طرد {m}")
@bot.tree.command(name="clear")
async def clear(i, a: int): await i.channel.purge(limit=a); await i.response.send_message("🧹", ephemeral=True)
@bot.tree.command(name="lock")
async def lock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")
@bot.tree.command(name="unlock")
async def unlock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")
@bot.tree.command(name="mute")
async def mute(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message("🔇")
@bot.tree.command(name="unmute")
async def unmute(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊")
@bot.tree.command(name="warn")
async def warn(i, m: discord.Member, r: str):
    db=load_db(); u=str(m.id); db["warns"][u]=db["warns"].get(u,0)+1; save_db(db); await i.response.send_message(f"⚠️ تحذير لـ {m.mention}")
@bot.tree.command(name="slowmode")
async def slow(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"🐢 {s}s")
@bot.tree.command(name="nick")
async def nick(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("✅")
@bot.tree.command(name="move")
async def move(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("✅")
@bot.tree.command(name="vmute")
async def vmute(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🎙️🔇")
@bot.tree.command(name="vunmute")
async def vunmute(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🎙️🔊")

# [اقتصاد - ECO]
@bot.tree.command(name="daily")
async def daily(i):
    db=load_db(); u=str(i.user.id); now=time.time()
    if now - db["daily_cooldown"].get(u,0) < 86400: return await i.response.send_message("❌ انتظر 24 ساعة")
    db["bank"][u]=db["bank"].get(u,0)+1000; db["daily_cooldown"][u]=now; save_db(db); await i.response.send_message("💰 +1000")
@bot.tree.command(name="credits")
async def cr(i, m: discord.Member=None): m=m or i.user; await i.response.send_message(f"💳 رصيد {m.name}: {load_db()['bank'].get(str(m.id),0)}")
@bot.tree.command(name="work")
async def work(i):
    r=random.randint(50,300); db=load_db(); u=str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+r; save_db(db); await i.response.send_message(f"👷 ربحت {r}")
@bot.tree.command(name="transfer")
async def trans(i, m: discord.Member, a: int):
    db=load_db(); s=str(i.user.id); r=str(m.id)
    if db["bank"].get(s,0)<a: return await i.response.send_message("❌ رصيدك لا يكفي")
    db["bank"][s]-=a; db["bank"][r]=db["bank"].get(r,0)+a; save_db(db); await i.response.send_message("✅ تم التحويل")
@bot.tree.command(name="top-bank")
async def topb(i):
    top=sorted(load_db()["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    await i.response.send_message("🏆 توب بنك:\n" + "\n".join([f"<@{u}>: {a}" for u,a in top]))
@bot.tree.command(name="give-money")
async def gm(i, m: discord.Member, a: int):
    if not i.user.guild_permissions.administrator: return
    db=load_db(); u=str(m.id); db["bank"][u]=db["bank"].get(u,0)+a; save_db(db); await i.response.send_message("🎁 تم المنح")
@bot.tree.command(name="rob")
async def rob(i, m: discord.Member): await i.response.send_message(random.choice(["نجحت وسرقت 500", "فشلت وانمسكت!"]))
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
@bot.tree.command(name="reset-money")
async def rmoney(i, m: discord.Member):
    if not i.user.guild_permissions.administrator: return
    db=load_db(); db["bank"][str(m.id)]=0; save_db(db); await i.response.send_message("🧹 تم التصفير")

# [ترفيه - FUN]
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

# [عام - GEN]
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
async def inv(i): await i.response.send_message("🔗 رابط دعوة البوت")
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
async def rul(i): await i.response.send_message("📜 قوانين السيرفر")
@bot.tree.command(name="bot-info")
async def bti(i): await i.response.send_message("OP BOT v5.0")
@bot.tree.command(name="members")
async def mem(i): await i.response.send_message(f"👥 عدد الأعضاء: {i.guild.member_count}")
@bot.tree.command(name="top-levels")
async def tl(i): await i.response.send_message("🏅 توب ليفل قيد التطوير")
@bot.tree.command(name="remove-security")
async def rs(i): 
    db=load_db(); db["security"][str(i.guild.id)]=False; save_db(db); await i.response.send_message("🔓 تم إيقاف الحماية")
@bot.tree.command(name="add-security")
async def ads(i): 
    db=load_db(); db["security"][str(i.guild.id)]=True; save_db(db); await i.response.send_message("🛡️ تم تفعيل الحماية")

# تشغيل
if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.run(os.getenv("DISCORD_TOKEN"))
