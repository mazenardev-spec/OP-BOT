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

# --- مسارات الـ Flask (الداشبورد) ---
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

# --- كلاس البوت الرئيسي ---
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

bot = OPBot()

# --- [ الفئة 1: إعدادات متقدمة (4 أوامر) ] ---
@bot.tree.command(name="set-logs", description="تحديد روم اللوجات")
async def sl(i, ch: discord.TextChannel):
    db=load_db(); db["settings"][f"{i.guild.id}_logs"]=ch.id; save_db(db); await i.response.send_message("✅")
@bot.tree.command(name="set-autorole", description="تحديد رتبة دخول تلقائية")
async def sar(i, r: discord.Role):
    db=load_db(); db["auto_role"][str(i.guild.id)]=r.id; save_db(db); await i.response.send_message("✅")
@bot.tree.command(name="set-welcome", description="إعداد روم ورسالة الترحيب")
async def swc(i, ch: discord.TextChannel, msg: str):
    db=load_db(); db["settings"][f"{i.guild.id}_welcome_channel"]=ch.id; db["settings"][f"{i.guild.id}_welcome_msg"]=msg; save_db(db); await i.response.send_message("✅")
@bot.tree.command(name="set-ticket", description="تجهيز نظام التذاكر في روم معين")
async def st(i, ch: discord.TextChannel):
    await ch.send("تذاكر الدعم", view=TicketView()); await i.response.send_message("✅")

# --- [ الفئة 2: الإدارة والحماية (18 أمر) ] ---
@bot.tree.command(name="ban", description="حظر عضو من السيرفر")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i, m: discord.Member, r: str="غير محدد"): await m.ban(reason=r); await i.response.send_message(f"✅ تم حظر {m}")
@bot.tree.command(name="kick", description="طرد عضو من السيرفر")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i, m: discord.Member, r: str="غير محدد"): await m.kick(reason=r); await i.response.send_message(f"✅ تم طرد {m}")
@bot.tree.command(name="timeout", description="إعطاء تايم أوت (اسكات مؤقت)")
async def timeout(i, m: discord.Member, t: int, r: str="غير محدد"):
    await m.timeout(timedelta(minutes=t), reason=r); await i.response.send_message(f"🔇 تم إعطاء تايم أوت لـ {m.name} لمدة {t} دقيقة")
@bot.tree.command(name="untimeout", description="إزالة التايم أوت")
async def untimeout(i, m: discord.Member): await m.timeout(None); await i.response.send_message(f"🔊 تم فك التايم أوت عن {m.name}")
@bot.tree.command(name="clear", description="مسح عدد معين من الرسائل")
async def clear(i, a: int): await i.channel.purge(limit=a); await i.response.send_message(f"🧹 تم مسح {a} رسالة", ephemeral=True)
@bot.tree.command(name="lock", description="قفل الروم الحالي")
async def lock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")
@bot.tree.command(name="unlock", description="فتح الروم المقفل")
async def unlock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")
@bot.tree.command(name="mute", description="إسكات عضو (تايم أوت سريع)")
async def mute(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message("🔇")
@bot.tree.command(name="unmute", description="فك الإسكات")
async def unmute(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊")
@bot.tree.command(name="warn", description="إرسال تحذير للعضو")
async def warn(i, m: discord.Member, r: str):
    db=load_db(); u=str(m.id); db["warns"][u]=db["warns"].get(u,0)+1; save_db(db); await i.response.send_message(f"⚠️ تحذير لـ {m.mention} | السبب: {r}")
@bot.tree.command(name="slowmode", description="تفعيل وضع التباطؤ للروم")
async def slow(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"🐢 وضع التباطؤ: {s} ثانية")
@bot.tree.command(name="nick", description="تغيير لقب عضو")
async def nick(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("✅ تم تغيير اللقب")
@bot.tree.command(name="move", description="نقل عضو لروم صوتي آخر")
async def move(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("✅")
@bot.tree.command(name="vmute", description="إسكات عضو في الروم الصوتي")
async def vmute(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🎙️🔇")
@bot.tree.command(name="vunmute", description="فك إسكات الروم الصوتي")
async def vunmute(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🎙️🔊")
@bot.tree.command(name="add-security", description="تفعيل نظام حماية الروابط")
async def ads(i): 
    db=load_db(); db["security"][str(i.guild.id)]=True; save_db(db); await i.response.send_message("🛡️ الحماية مفعلة")
@bot.tree.command(name="remove-security", description="إيقاف نظام حماية الروابط")
async def rs(i): 
    db=load_db(); db["security"][str(i.guild.id)]=False; save_db(db); await i.response.send_message("🔓 الحماية معطلة")
@bot.tree.command(name="hide", description="إخفاء الروم")
async def hide(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻")

# --- [ الفئة 3: نظام الاقتصاد (15 أمر) ] ---
@bot.tree.command(name="daily", description="استلام الجائزة اليومية")
async def daily(i):
    db=load_db(); u=str(i.user.id); now=time.time()
    if now - db["daily_cooldown"].get(u,0) < 86400: return await i.response.send_message("❌ انتظر 24 ساعة")
    db["bank"][u]=db["bank"].get(u,0)+1000; db["daily_cooldown"][u]=now; save_db(db); await i.response.send_message("💰 +1000")
@bot.tree.command(name="credits", description="رؤية رصيدك الحالي")
async def cr(i, m: discord.Member=None): m=m or i.user; await i.response.send_message(f"💳 رصيد {m.name}: {load_db()['bank'].get(str(m.id),0)}")
@bot.tree.command(name="work", description="العمل لجمع المال")
async def work(i):
    r=random.randint(50,300); db=load_db(); u=str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+r; save_db(db); await i.response.send_message(f"👷 ربحت {r}")
@bot.tree.command(name="transfer", description="تحويل مبلغ لشخص آخر")
async def trans(i, m: discord.Member, a: int):
    db=load_db(); s=str(i.user.id); r=str(m.id)
    if db["bank"].get(s,0)<a: return await i.response.send_message("❌ رصيدك لا يكفي")
    db["bank"][s]-=a; db["bank"][r]=db["bank"].get(r,0)+a; save_db(db); await i.response.send_message("✅ تم التحويل")
@bot.tree.command(name="top-bank", description="قائمة أغنى 5 أشخاص")
async def topb(i):
    top=sorted(load_db()["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    await i.response.send_message("🏆 الأغنى:\n" + "\n".join([f"<@{u}>: {a}" for u,a in top]))
@bot.tree.command(name="give-money", description="منح مال لعضو (أدمن فقط)")
async def gm(i, m: discord.Member, a: int):
    if not i.user.guild_permissions.administrator: return
    db=load_db(); u=str(m.id); db["bank"][u]=db["bank"].get(u,0)+a; save_db(db); await i.response.send_message("🎁 تم")
@bot.tree.command(name="rob", description="محاولة سرقة شخص")
async def rob(i, m: discord.Member): await i.response.send_message(random.choice(["💰 سرقت 500!", "👮 صادوك الشرطة!"]))
@bot.tree.command(name="fish", description="الصيد لبيع السمك")
async def fish(i): await i.response.send_message(f"🎣 اصطدت سمكة بقيمة {random.randint(10,100)}")
@bot.tree.command(name="slots", description="لعبة السلوتس")
async def slots(i): await i.response.send_message("🎰 | 🍒 | 💎 | 🍒")
@bot.tree.command(name="coin", description="لعبة العملة (ملك/كتابة)")
async def coin(i): await i.response.send_message(f"🪙 {random.choice(['ملك', 'كتابة'])}")
@bot.tree.command(name="hunt", description="الخروج للصيد")
async def hunt(i): await i.response.send_message(f"🏹 اصطدت {random.choice(['غزال', 'بطة'])}")
@bot.tree.command(name="salary", description="استلام الراتب")
async def sal(i): await i.response.send_message("💼 +200")
@bot.tree.command(name="reset-money", description="تصفير رصيد شخص")
async def rmoney(i, m: discord.Member):
    if not i.user.guild_permissions.administrator: return
    db=load_db(); db["bank"][str(m.id)]=0; save_db(db); await i.response.send_message("🧹 صفر")
@bot.tree.command(name="shop", description="فتح المتجر")
async def shop(i): await i.response.send_message("🛒 قريباً")
@bot.tree.command(name="bank-info", description="معلومات البنك")
async def binf(i): await i.response.send_message("🏦 بنك OP BOT")

# --- [ الفئة 4: الترفيه (13 أمر) ] ---
@bot.tree.command(name="iq", description="فحص نسبة الذكاء")
async def iq(i): await i.response.send_message(f"🧠 نسبة ذكائك: {random.randint(1,200)}%")
@bot.tree.command(name="hack", description="اختراق وهمي لعضو")
async def hack(i, m: discord.Member): await i.response.send_message(f"💻 اختراق {m.name}...")
@bot.tree.command(name="joke", description="قول نكتة")
async def joke(i): await i.response.send_message("مرة واحد..")
@bot.tree.command(name="ship", description="نسبة الحب بين شخصين")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 {random.randint(1,100)}%")
@bot.tree.command(name="kill", description="قتل عضو وهمي")
async def kill(i, m: discord.Member): await i.response.send_message(f"⚔️ مات {m}")
@bot.tree.command(name="slap", description="ضرب عضو كف")
async def slap(i, m: discord.Member): await i.response.send_message(f"🖐️ كف لـ {m}")
@bot.tree.command(name="dice", description="رمي الزهر")
async def dice(i): await i.response.send_message(f"🎲 {random.randint(1,6)}")
@bot.tree.command(name="hug", description="حضن عضو")
async def hug(i, m: discord.Member): await i.response.send_message(f"🤗 {m}")
@bot.tree.command(name="punch", description="ضرب عضو بوكس")
async def punch(i, m: discord.Member): await i.response.send_message(f"👊 {m}")
@bot.tree.command(name="choose", description="البوت يختار بين شيئين")
async def cho(i, a: str, b: str): await i.response.send_message(f"🤔 اخترت: {random.choice([a,b])}")
@bot.tree.command(name="wanted", description="صورة مطلوب للعدالة")
async def wan(i): await i.response.send_message("⚠️ مطلوب!")
@bot.tree.command(name="dance", description="الرقص")
async def dan(i): await i.response.send_message("💃")
@bot.tree.command(name="xo", description="لعب XO")
async def xo(i, m: discord.Member): await i.response.send_message(f"🎮 {i.user.name} ضد {m.name}")

# --- [ الفئة 5: أوامر عامة (14 أمر) ] ---
@bot.tree.command(name="help", description="عرض كل الأوامر")
async def hlp(i): await i.response.send_message("استخدم / لرؤية كل الأوامر والوصف")
@bot.tree.command(name="ping", description="فحص سرعة اتصال البوت")
async def png(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar", description="عرض افتار عضو")
async def av(i, m: discord.Member=None): m=m or i.user; await i.response.send_message(m.display_avatar.url)
@bot.tree.command(name="server-info", description="معلومات السيرفر")
async def si(i): await i.response.send_message(f"🏰 {i.guild.name} | {i.guild.id}")
@bot.tree.command(name="user-info", description="معلومات العضو")
async def ui(i, m: discord.Member=None): m=m or i.user; await i.response.send_message(f"👤 {m.name} | {m.id}")
@bot.tree.command(name="invite", description="رابط دعوة البوت")
async def inv(i): await i.response.send_message("🔗 قريباً")
@bot.tree.command(name="roles", description="عرض عدد الرتب")
async def rc(i): await i.response.send_message(f"📜 {len(i.guild.roles)}")
@bot.tree.command(name="channels", description="عرض عدد القنوات")
async def cc(i): await i.response.send_message(f"📁 {len(i.guild.channels)}")
@bot.tree.command(name="bot-id", description="آيدي البوت")
async def bi(i): await i.response.send_message(f"🤖 {bot.user.id}")
@bot.tree.command(name="say", description="البوت يقول كلامك")
async def say(i, t: str): await i.channel.send(t); await i.response.send_message("تم", ephemeral=True)
@bot.tree.command(name="suggest", description="إرسال اقتراح")
async def sug(i, t: str): await i.response.send_message("✅ تم")
@bot.tree.command(name="rules", description="قوانين السيرفر")
async def rul(i): await i.response.send_message("📜 القوانين")
@bot.tree.command(name="members", description="عدد الأعضاء")
async def mem(i): await i.response.send_message(f"👥 {i.guild.member_count}")
@bot.tree.command(name="top-levels", description="توب ليفل")
async def tl(i): await i.response.send_message("🏅")

# تشغيل
if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.run(os.getenv("DISCORD_TOKEN"))
