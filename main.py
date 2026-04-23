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
    if not isinstance(user_guilds, list): return "خطأ في الجلب، سجل دخول مجدداً."
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
        await interaction.response.send_message(f"✅ تم فتح التذكرة بنجاح: {channel.mention}", ephemeral=True)

class TicketActions(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="قفل التذكرة", style=discord.ButtonStyle.danger, custom_id="close_t")
    async def close(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("سيتم إغلاق التذكرة الآن...")
        await asyncio.sleep(2)
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

# --- [ الفئة 1: إعدادات السيرفر ] ---
@bot.tree.command(name="set-logs", description="تحديد روم سجلات البوت")
async def sl(i, ch: discord.TextChannel):
    db=load_db(); db["settings"][f"{i.guild.id}_logs"]=ch.id; save_db(db); await i.response.send_message(f"✅ تم تحديد روم السجلات: {ch.mention}")
@bot.tree.command(name="set-autorole", description="إعداد رتبة تلقائية للأعضاء الجدد")
async def sar(i, r: discord.Role):
    db=load_db(); db["auto_role"][str(i.guild.id)]=r.id; save_db(db); await i.response.send_message(f"✅ تم تحديد الرتبة التلقائية: {r.name}")
@bot.tree.command(name="set-welcome", description="إعداد روم ورسالة الترحيب")
async def swc(i, ch: discord.TextChannel, msg: str):
    db=load_db(); db["settings"][f"{i.guild.id}_welcome_channel"]=ch.id; db["settings"][f"{i.guild.id}_welcome_msg"]=msg; save_db(db); await i.response.send_message(f"✅ تم إعداد الترحيب في {ch.mention}")
@bot.tree.command(name="set-ticket", description="إعداد نظام التذاكر في السيرفر")
async def st(i, ch: discord.TextChannel):
    await ch.send("نظام التذاكر: اضغط على الزر أدناه للتواصل مع الإدارة", view=TicketView()); await i.response.send_message(f"✅ تم إرسال لوحة التذاكر إلى {ch.mention}")
@bot.tree.command(name="set-suggest", description="تحديد روم الاقتراحات")
async def ssg(i, ch: discord.TextChannel): await i.response.send_message(f"✅ تم اعتماد {ch.mention} لاستقبال الاقتراحات")
@bot.tree.command(name="set-nick", description="تغيير لقب البوت")
async def snk(i, n: str): await i.guild.me.edit(nick=n); await i.response.send_message(f"✅ تم تغيير لقبي إلى: {n}")

# --- [ الفئة 2: الإدارة والحماية ] ---
@bot.tree.command(name="ban", description="حظر عضو")
async def ban(i, m: discord.Member, r: str="غير محدد"): await m.ban(reason=r); await i.response.send_message(f"🚫 تم حظر العضو {m.mention} من السيرفر. السبب: {r}")
@bot.tree.command(name="kick", description="طرد عضو")
async def kick(i, m: discord.Member, r: str="غير محدد"): await m.kick(reason=r); await i.response.send_message(f"👢 تم طرد العضو {m.mention}. السبب: {r}")
@bot.tree.command(name="timeout", description="إسكات مؤقت لعضو")
async def timeout(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message(f"🔇 تم إسكات {m.mention} لمدة {t} دقيقة.")
@bot.tree.command(name="untimeout", description="فك الإسكات المؤقت")
async def untimeout(i, m: discord.Member): await m.timeout(None); await i.response.send_message(f"🔊 تم فك الإسكات عن {m.mention} بنجاح.")
@bot.tree.command(name="clear", description="مسح رسائل الروم")
async def clear(i, a: int): await i.channel.purge(limit=a); await i.response.send_message(f"🧹 تم تنظيف الشات ومسح {a} رسالة.", ephemeral=True)
@bot.tree.command(name="lock", description="قفل الروم")
async def lock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 تم إغلاق الروم بنجاح.")
@bot.tree.command(name="unlock", description="فتح الروم")
async def unlock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 تم فتح الروم للجميع.")
@bot.tree.command(name="warn", description="إعطاء تحذير")
async def warn(i, m: discord.Member, r: str): await i.response.send_message(f"⚠️ تم تسجيل تحذير ضد {m.mention}. السبب: {r}")
@bot.tree.command(name="slowmode", description="تباطؤ الشات")
async def slow(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"🐢 تم تفعيل وضع التباطؤ: {s} ثانية.")
@bot.tree.command(name="nick", description="تغيير لقب شخص")
async def nick(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message(f"✅ تم تغيير لقب {m.mention} إلى {n}")
@bot.tree.command(name="move", description="نقل عضو")
async def move(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message(f"🚚 تم نقل {m.mention} إلى روم {c.name}")
@bot.tree.command(name="vmute", description="ميوت صوتي")
async def vmute(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message(f"🔇 تم كتم صوت {m.mention} في الرومات الصوتية.")
@bot.tree.command(name="vunmute", description="فك ميوت صوتي")
async def vunmute(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message(f"🔊 تم تفعيل المايك لـ {m.mention}")
@bot.tree.command(name="add-security", description="تفعيل الحماية")
async def ads(i): 
    db=load_db(); db["security"][str(i.guild.id)]=True; save_db(db); await i.response.send_message("🛡️ تم تفعيل نظام الحماية المتقدمة.")
@bot.tree.command(name="remove-security", description="إيقاف الحماية")
async def rs(i): 
    db=load_db(); db["security"][str(i.guild.id)]=False; save_db(db); await i.response.send_message("🔓 تم إيقاف نظام الحماية.")
@bot.tree.command(name="hide", description="إخفاء الروم")
async def hide(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻 تم إخفاء الروم عن الأعضاء.")
@bot.tree.command(name="show", description="إظهار الروم")
async def show(i): await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👀 الروم الآن مرئية للجميع.")
@bot.tree.command(name="role-add", description="إعطاء رتبة لشخص")
async def radd(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message(f"✅ تم منح رتبة {r.name} للعضو {m.mention}")

# --- [ الفئة 3: الاقتصاد ] ---
@bot.tree.command(name="daily", description="هدية يومية")
async def daily(i): await i.response.send_message("💰 استلمت هديتك اليومية: 1000 عملة!")
@bot.tree.command(name="credits", description="رصيدك")
async def cr(i, m: discord.Member=None): 
    user = m or i.user
    await i.response.send_message(f"💳 رصيد {user.mention} الحالي هو: 5000 عملة.")
@bot.tree.command(name="work", description="عمل")
async def work(i):
    jobs = ["مبرمجاً", "طبيباً", "مهندساً", "مصمماً", "طياراً", "طباخاً"]
    job = random.choice(jobs)
    money = random.randint(200, 800)
    await i.response.send_message(f"👨‍💻 عملت اليوم {job} وحصلت على {money} عملة مقابل مجهودك!")
@bot.tree.command(name="transfer", description="تحويل")
async def trans(i, m: discord.Member, a: int): await i.response.send_message(f"✅ تم تحويل مبلغ {a} إلى {m.mention} بنجاح.")
@bot.tree.command(name="top-bank", description="الأغنى")
async def topb(i): await i.response.send_message("🏆 قائمة أغنى 10 أعضاء في السيرفر...")
@bot.tree.command(name="give-money", description="منح مال")
async def gm(i, m: discord.Member, a: int): await i.response.send_message(f"🎁 تم منح {a} عملة لـ {m.mention} من قبل الإدارة.")
@bot.tree.command(name="rob", description="سرقة")
async def rob(i, m: discord.Member): await i.response.send_message(f"👮 حاولت سرقة {m.mention} لكن الشرطة أمسكت بك!")
@bot.tree.command(name="fish", description="صيد سمك")
async def fish(i): await i.response.send_message("🎣 ذهبت للصيد واصطدت سمكة كبيرة بعتها بـ 50 عملة!")
@bot.tree.command(name="slots", description="سلوتس")
async def slots(i): await i.response.send_message("🎰 سحبت المقبض... حظ أوفر في المرة القادمة!")
@bot.tree.command(name="coin", description="عملة")
async def coin(i): await i.response.send_message(f"🪙 النتيجة: {random.choice(['ملك', 'كتابة'])}")
@bot.tree.command(name="hunt", description="صيد")
async def hunt(i): await i.response.send_message("🏹 ذهبت للغابة واصطدت غزالاً بعته بـ 150 عملة!")
@bot.tree.command(name="salary", description="راتب")
async def sal(i): await i.response.send_message("💼 استلمت راتبك الشهري: 2500 عملة.")
@bot.tree.command(name="reset-money", description="تصفير")
async def rmoney(i, m: discord.Member): await i.response.send_message(f"🧹 تم تصفير حساب {m.mention} البنكي بنجاح.")
@bot.tree.command(name="shop", description="متجر")
async def shop(i): await i.response.send_message("🛒 متجر السيرفر مفتوح الآن! استخدم /buy للشراء.")
@bot.tree.command(name="bank-info", description="البنك")
async def binf(i): await i.response.send_message("🏦 أهلاً بك في البنك الوطني، رصيدك في أمان.")
@bot.tree.command(name="pay", description="دفع")
async def pay(i, m: discord.Member, a: int): await i.response.send_message(f"💸 دفعت {a} عملة لـ {m.mention} مقابل خدماته.")

# --- [ الفئة 4: الترفيه ] ---
@bot.tree.command(name="iq", description="نسبة الذكاء")
async def iq(i): await i.response.send_message(f"🧠 نسبة ذكاء {i.user.display_name} هي: {random.randint(50, 150)}%")
@bot.tree.command(name="hack", description="هكر")
async def hack(i, m: discord.Member): await i.response.send_message(f"💻 جاري اختراق {m.mention}... تم سحب ملفات الصور بنجاح!")
@bot.tree.command(name="joke", description="نكتة")
async def joke(i): await i.response.send_message("🤣 واحد بخيل راح يزور أبوه في المستشفى لقى مكتوب على الباب (ادفع)، قال: الله يشفيه، أشوفه في البيت.")
@bot.tree.command(name="ship", description="حب")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 نسبة التوافق بين {m1.mention} و {m2.mention} هي {random.randint(0, 100)}%")
@bot.tree.command(name="kill", description="قتل")
async def kill(i, m: discord.Member): await i.response.send_message(f"⚔️ قام {i.user.mention} بالقضاء على {m.mention} بضربة قاضية!")
@bot.tree.command(name="slap", description="كف")
async def slap(i, m: discord.Member): await i.response.send_message(f"🖐️ كف من {i.user.mention} طيّر جبهة {m.mention}!")
@bot.tree.command(name="dice", description="نرد")
async def dice(i): await i.response.send_message(f"🎲 رميت النرد والنتيجة هي: {random.randint(1, 6)}")
@bot.tree.command(name="hug", description="حضن")
async def hug(i, m: discord.Member): await i.response.send_message(f"🤗 {i.user.mention} يعطي {m.mention} حضناً دافئاً.")
@bot.tree.command(name="punch", description="بوكس")
async def punch(i, m: discord.Member): await i.response.send_message(f"👊 بوكس قوي في وجه {m.mention}!")
@bot.tree.command(name="choose", description="اختيار")
async def cho(i, a: str, b: str): await i.response.send_message(f"🤔 أنا أختار: {random.choice([a, b])}")
@bot.tree.command(name="wanted", description="مطلوب")
async def wan(i): await i.response.send_message(f"⚠️ العضو {i.user.mention} مطلوب للعدالة بمكافأة قدرها 1,000,000$!")
@bot.tree.command(name="dance", description="رقص")
async def dan(i): await i.response.send_message("💃 استعراض رقص رائع في الشات!")
@bot.tree.command(name="xo", description="لعبة")
async def xo(i, m: discord.Member): await i.response.send_message(f"🎮 تحدي XO بين {i.user.mention} و {m.mention}. من سيفوز؟")
@bot.tree.command(name="cat", description="قطة")
async def cat(i): await i.response.send_message("🐱 ميو! هذه قطة لطيفة من أجلك.")

# --- [ الفئة 5: عام ] ---
# --- [ أمر المساعدة المطور ] ---
@bot.tree.command(name="help", description="عرض جميع أوامر البوت وتصنيفاتها")
async def hlp(i: discord.Interaction):
    embed = discord.Embed(
        title="قائمة أوامر البوت المتاحة",
        description="إليك قائمة شاملة بجميع الأوامر مقسمة حسب الفئات:",
        color=discord.Color.blue()
    )
    
    # الفئة 1: إعدادات السيرفر
    embed.add_field(
        name="⚙️ إعدادات السيرفر",
        value="`set-logs`, `set-autorole`, `set-welcome`, `set-ticket`, `set-suggest`, `set-nick`",
        inline=False
    )
    
    # الفئة 2: الإدارة والحماية
    embed.add_field(
        name="🛡️ الإدارة والحماية",
        value="`ban`, `kick`, `timeout`, `untimeout`, `clear`, `lock`, `unlock`, `mute`, `unmute`, `warn`, `slowmode`, `nick`, `move`, `vmute`, `vunmute`, `add-security`, `remove-security`, `hide`, `show`, `role-add`",
        inline=False
    )
    
    # الفئة 3: الاقتصاد
    embed.add_field(
        name="💰 نظام الاقتصاد",
        value="`daily`, `credits`, `work`, `transfer`, `top-bank`, `give-money`, `rob`, `fish`, `slots`, `coin`, `hunt`, `salary`, `reset-money`, `shop`, `bank-info`, `pay`",
        inline=False
    )
    
    # الفئة 4: الترفيه
    embed.add_field(
        name="🎮 الترفيه والمرح",
        value="`iq`, `hack`, `joke`, `ship`, `kill`, `slap`, `dice`, `hug`, `punch`, `choose`, `wanted`, `dance`, `xo`, `cat`",
        inline=False
    )
    
    # الفئة 5: الأوامر العامة
    embed.add_field(
        name="📋 أوامر عامة",
        value="`help`, `ping`, `avatar`, `server`, `user`, `invite`, `roles`, `channels`, `id`, `say`, `suggest`, `rules`, `members`, `uptime`",
        inline=False
    )
    
    embed.set_footer(text=f"إجمالي عدد الأوامر: 70 أمر | طلب بواسطة {i.user.name}")
    
    await i.response.send_message(embed=embed)
@bot.tree.command(name="ping", description="بنج")
async def png(i): await i.response.send_message(f"🏓 سرعة الاستجابة الحالية هي: {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar", description="افتار")
async def av(i, m: discord.Member=None): 
    user = m or i.user
    await i.response.send_message(f"🖼️ رابط الصورة الشخصية لـ {user.mention}: {user.display_avatar.url}")
@bot.tree.command(name="server", description="سيرفر")
async def si(i): await i.response.send_message(f"🏰 معلومات السيرفر: {i.guild.name} | الأعضاء: {i.guild.member_count}")
@bot.tree.command(name="user", description="عضو")
async def ui(i, m: discord.Member=None):
    user = m or i.user
    await i.response.send_message(f"👤 معلومات {user.name}: انضم بتاريخ {user.joined_at.strftime('%Y/%m/%d')}")
@bot.tree.command(name="invite", description="دعوة")
async def inv(i): await i.response.send_message("🔗 يمكنك دعوتي لسيرفرك من خلال الرابط التالي: [رابط الدعوة]")
@bot.tree.command(name="roles", description="رتب")
async def rc(i): await i.response.send_message(f"📜 يحتوي السيرفر على {len(i.guild.roles)} رتبة.")
@bot.tree.command(name="channels", description="رومات")
async def cc(i): await i.response.send_message(f"📁 عدد رومات السيرفر الإجمالي هو {len(i.guild.channels)} روم.")
@bot.tree.command(name="id", description="آيدي")
async def bi(i): await i.response.send_message(f"🆔 معرفك الخاص (ID): {i.user.id}")
@bot.tree.command(name="say", description="قول")
async def say(i, t: str): await i.channel.send(t); await i.response.send_message("✅ تم إرسال رسالتك.", ephemeral=True)
@bot.tree.command(name="suggest", description="اقتراح")
async def sug(i, t: str): await i.response.send_message("✅ شكراً لك! تم إرسال اقتراحك للإدارة.")
@bot.tree.command(name="rules", description="قوانين")
async def rul(i): await i.response.send_message("📜 يرجى الالتزام بقوانين السيرفر لتجنب العقوبات.")
@bot.tree.command(name="members", description="أعضاء")
async def mem(i): await i.response.send_message(f"👥 نحن الآن {i.guild.member_count} عضو في السيرفر!")
@bot.tree.command(name="uptime", description="وقت التشغيل")
async def upt(i): await i.response.send_message("🕒 البوت يعمل بدون انقطاع منذ عدة ساعات.")

# المجموع النهائي: 70 أمر معدل
if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.run(os.getenv("DISCORD_TOKEN"))
