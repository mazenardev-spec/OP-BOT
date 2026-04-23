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

# --- نظام XO التفاعلي ---
class XOButton(discord.ui.Button['XOView']):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x, self.y = x, y
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.current_player: return await interaction.response.send_message("ليس دورك!", ephemeral=True)
        char = 'X' if view.current_player == view.player1 else 'O'
        self.label, self.style, self.disabled = char, (discord.ButtonStyle.danger if char == 'X' else discord.ButtonStyle.success), True
        view.board[self.y][self.x] = 1 if char == 'X' else 2
        if view.check_winner():
            db = load_db(); db["bank"][str(view.current_player.id)] = db["bank"].get(str(view.current_player.id), 0) + 100; save_db(db)
            for c in view.children: c.disabled = True
            await interaction.response.edit_message(content=f"🎉 {view.current_player.mention} فاز وحصل على 100 عملة!", view=view)
        elif view.is_full(): await interaction.response.edit_message(content="🤝 تعادل!", view=view)
        else:
            view.current_player = view.player2 if view.current_player == view.player1 else view.player1
            await interaction.response.edit_message(content=f"دور: {view.current_player.mention}", view=view)

class XOView(View):
    def __init__(self, p1, p2):
        super().__init__(); self.player1, self.player2, self.current_player = p1, p2, p1
        self.board = [[0,0,0],[0,0,0],[0,0,0]]
        for y in range(3):
            for x in range(3): self.add_item(XOButton(x, y))
    def check_winner(self):
        for i in range(3):
            if self.board[i][0]==self.board[i][1]==self.board[i][2]!=0 or self.board[0][i]==self.board[1][i]==self.board[2][i]!=0: return True
        return self.board[0][0]==self.board[1][1]==self.board[2][2]!=0 or self.board[0][2]==self.board[1][1]==self.board[2][0]!=0
    def is_full(self): return all(all(row) for row in self.board)

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
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        db = load_db()
        if db["security"].get(str(message.guild.id), False):
            if any(x in message.content for x in ["http", "discord.gg"]) or message.attachments:
                await message.delete()
                try: await message.author.send(f"⚠️ ممنوع الروابط والصور في {message.guild.name}!")
                except: pass

bot = OPBot()

# --- [ الفئة 1: إعدادات السيرفر والحماية ] ---
@bot.tree.command(name="set-logs", description="تحديد روم السجلات")
async def sl(i, ch: discord.TextChannel):
    db=load_db(); db["settings"][f"{i.guild.id}_logs"]=ch.id; save_db(db); await i.response.send_message(f"✅ تم تحديد السجلات: {ch.mention}")
@bot.tree.command(name="set-autorole", description="الرتبة التلقائية")
async def sar(i, r: discord.Role):
    db=load_db(); db["auto_role"][str(i.guild.id)]=r.id; save_db(db); await i.response.send_message(f"✅ تم تحديد الرتبة: {r.name}")
@bot.tree.command(name="set-welcome", description="الترحيب")
async def swc(i, ch: discord.TextChannel, msg: str):
    db=load_db(); db["settings"][f"{i.guild.id}_welcome_channel"]=ch.id; db["settings"][f"{i.guild.id}_welcome_msg"]=msg; save_db(db); await i.response.send_message(f"✅ تم الإعداد في {ch.mention}")
@bot.tree.command(name="set-ticket", description="نظام التذاكر")
async def st(i, ch: discord.TextChannel):
    await ch.send("تواصل مع الإدارة عبر التذاكر", view=TicketView()); await i.response.send_message(f"✅ تم الإرسال إلى {ch.mention}")
@bot.tree.command(name="set-suggest", description="الاقتراحات")
async def ssg(i, ch: discord.TextChannel): await i.response.send_message(f"✅ تم اعتماد {ch.mention}")
@bot.tree.command(name="set-nick", description="لقب البوت")
async def snk(i, n: str): await i.guild.me.edit(nick=n); await i.response.send_message(f"✅ تم التغيير إلى: {n}")
@bot.tree.command(name="add-security", description="تفعيل منع الروابط والصور")
async def ads(i):
    db=load_db(); db["security"][str(i.guild.id)]=True; save_db(db); await i.response.send_message("🛡️ تم تفعيل الحماية.")
@bot.tree.command(name="remove-security", description="إيقاف الحماية")
async def rs(i):
    db=load_db(); db["security"][str(i.guild.id)]=False; save_db(db); await i.response.send_message("🔓 تم إيقاف الحماية.")

# --- [ الفئة 2: الإدارة ] ---
@bot.tree.command(name="ban", description="حظر")
async def ban(i, m: discord.Member, r: str="غير محدد"): await m.ban(reason=r); await i.response.send_message(f"🚫 حظر {m.mention}")
@bot.tree.command(name="kick", description="طرد")
async def kick(i, m: discord.Member, r: str="غير محدد"): await m.kick(reason=r); await i.response.send_message(f"👢 طرد {m.mention}")
@bot.tree.command(name="timeout", description="إسكات")
async def timeout(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message(f"🔇 إسكات {m.mention}")
@bot.tree.command(name="untimeout", description="فك إسكات")
async def untimeout(i, m: discord.Member): await m.timeout(None); await i.response.send_message(f"🔊 فك إسكات {m.mention}")
@bot.tree.command(name="clear", description="مسح")
async def clear(i, a: int): await i.channel.purge(limit=a); await i.response.send_message(f"🧹 مسح {a}", ephemeral=True)
@bot.tree.command(name="lock", description="قفل")
async def lock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 قفل")
@bot.tree.command(name="unlock", description="فتح")
async def unlock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 فتح")
@bot.tree.command(name="warn", description="تحذير")
async def warn(i, m: discord.Member, r: str): await i.response.send_message(f"⚠️ تحذير {m.mention}")
@bot.tree.command(name="slowmode", description="تبطئ")
async def slow(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"🐢 تبطئ {s}")
@bot.tree.command(name="nick", description="لقب")
async def nick(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message(f"✅ لقب {m.mention}")
@bot.tree.command(name="move", description="نقل")
async def move(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message(f"🚚 نقل {m.mention}")
@bot.tree.command(name="vmute", description="ميوت")
async def vmute(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message(f"🔇 ميوت {m.mention}")
@bot.tree.command(name="vunmute", description="فك ميوت")
async def vunmute(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message(f"🔊 فك ميوت {m.mention}")
@bot.tree.command(name="hide", description="إخفاء")
async def hide(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻 إخفاء")
@bot.tree.command(name="show", description="إظهار")
async def show(i): await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👀 إظهار")
@bot.tree.command(name="role-add", description="إضافة رتبة")
async def radd(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message(f"✅ رتبة {r.name}")

# --- [ الفئة 3: الاقتصاد ] ---
@bot.tree.command(name="daily", description="يومي")
async def daily(i):
    db=load_db(); u=str(i.user.id); now=time.time()
    if now-db["daily_cooldown"].get(u,0)<86400: return await i.response.send_message("⏳ غداً")
    db["bank"][u]=db["bank"].get(u,0)+1000; db["daily_cooldown"][u]=now; save_db(db); await i.response.send_message("💰 +1000")
@bot.tree.command(name="credits", description="رصيد")
async def cr(i, m: discord.Member=None):
    db=load_db(); u=m or i.user; b=db["bank"].get(str(u.id),0); await i.response.send_message(f"💳 {u.mention}: {b:,}")
@bot.tree.command(name="work", description="عمل")
async def work(i):
    db=load_db(); m=random.randint(200,800); db["bank"][str(i.user.id)]=db["bank"].get(str(i.user.id),0)+m; save_db(db); await i.response.send_message(f"👨‍💻 +{m}")
@bot.tree.command(name="transfer", description="تحويل")
async def trans(i, m: discord.Member, a: int):
    db=load_db(); s=str(i.user.id)
    if db["bank"].get(s,0)<a or a<=0: return await i.response.send_message("❌")
    db["bank"][s]-=a; db["bank"][str(m.id)]=db["bank"].get(str(m.id),0)+a; save_db(db); await i.response.send_message(f"✅ تحويل {a}")
@bot.tree.command(name="top-bank", description="توب")
async def topb(i):
    db=load_db(); sorted_b=sorted(db["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    await i.response.send_message(f"🏆 توب 5: {sorted_b}")
@bot.tree.command(name="give-money", description="منح")
async def gm(i, m: discord.Member, a: int):
    db=load_db(); db["bank"][str(m.id)]=db["bank"].get(str(m.id),0)+a; save_db(db); await i.response.send_message(f"🎁 +{a}")
@bot.tree.command(name="rob", description="سرقة")
async def rob(i, m: discord.Member):
    db=load_db(); s=str(i.user.id); t=str(m.id)
    if random.random()<0.3:
        st=random.randint(100,500); db["bank"][s]+=st; db["bank"][t]-=st; await i.response.send_message(f"🥷 سرقت {st}")
    else: await i.response.send_message("👮 أمسكت بك الشرطة!"); db["bank"][s]-=200
    save_db(db)
@bot.tree.command(name="fish", description="صيد")
async def fish(i):
    db=load_db(); r=random.randint(50,150); db["bank"][str(i.user.id)]+=r; save_db(db); await i.response.send_message(f"🎣 {r}")
@bot.tree.command(name="slots", description="سلوتس")
async def slots(i):
    db=load_db(); u=str(i.user.id)
    if db["bank"].get(u,0)<100: return await i.response.send_message("❌")
    db["bank"][u]-=100; win=(random.random()<0.2)
    if win: db["bank"][u]+=1000; await i.response.send_message("🎰 فزت!")
    else: await i.response.send_message("🎰 خسرت")
    save_db(db)
@bot.tree.command(name="coin", description="عملة")
async def coin(i): await i.response.send_message(f"🪙 {random.choice(['ملك', 'كتابة'])}")
@bot.tree.command(name="hunt", description="صيد")
async def hunt(i):
    db=load_db(); r=random.randint(100,300); db["bank"][str(i.user.id)]+=r; save_db(db); await i.response.send_message(f"🏹 {r}")
@bot.tree.command(name="salary", description="راتب")
async def sal(i):
    db=load_db(); db["bank"][str(i.user.id)]+=500; save_db(db); await i.response.send_message("💼 +500")
@bot.tree.command(name="reset-money", description="تصفير")
async def rmoney(i, m: discord.Member):
    db=load_db(); db["bank"][str(m.id)]=0; save_db(db); await i.response.send_message("🧹 0")
@bot.tree.command(name="shop", description="متجر")
async def shop(i): await i.response.send_message("🛒 قريباً")
@bot.tree.command(name="bank-info", description="بنك")
async def binf(i): await i.response.send_message("🏦 بنك OP")
@bot.tree.command(name="pay", description="دفع")
async def pay(i, m: discord.Member, a: int): await trans.callback(i, m, a)

# --- [ الفئة 4: الترفيه ] ---
@bot.tree.command(name="iq", description="ذكاء")
async def iq(i): await i.response.send_message(f"🧠 {random.randint(50, 150)}%")
@bot.tree.command(name="hack", description="هكر")
async def hack(i, m: discord.Member): await i.response.send_message(f"💻 اختراق {m.mention}")
@bot.tree.command(name="joke", description="نكتة")
async def joke(i): await i.response.send_message("🤣 نكتة")
@bot.tree.command(name="ship", description="حب")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 {random.randint(0, 100)}%")
@bot.tree.command(name="kill", description="قتل")
async def kill(i, m: discord.Member): await i.response.send_message(f"⚔️ قتل {m.mention}")
@bot.tree.command(name="slap", description="كف")
async def slap(i, m: discord.Member): await i.response.send_message(f"🖐️ كف لـ {m.mention}")
@bot.tree.command(name="dice", description="نرد")
async def dice(i): await i.response.send_message(f"🎲 {random.randint(1, 6)}")
@bot.tree.command(name="hug", description="حضن")
async def hug(i, m: discord.Member): await i.response.send_message(f"🤗 حضن لـ {m.mention}")
@bot.tree.command(name="punch", description="بوكس")
async def punch(i, m: discord.Member): await i.response.send_message(f"👊 بوكس لـ {m.mention}")
@bot.tree.command(name="choose", description="اختيار")
async def cho(i, a: str, b: str): await i.response.send_message(f"🤔 {random.choice([a, b])}")
@bot.tree.command(name="wanted", description="مطلوب")
async def wan(i): await i.response.send_message(f"⚠️ مطلوب {i.user.mention}")
@bot.tree.command(name="dance", description="رقص")
async def dan(i): await i.response.send_message("💃")
@bot.tree.command(name="xo", description="لعبة XO")
async def xo(i, m: discord.Member):
    if m.id == i.user.id: return await i.response.send_message("❌")
    await i.response.send_message(f"🎮 XO: {i.user.mention} vs {m.mention}", view=XOView(i.user, m))
@bot.tree.command(name="cat", description="قطة")
async def cat(i): await i.response.send_message("🐱")

# --- [ الفئة 5: عام ] ---
@bot.tree.command(name="help", description="المساعدة")
async def hlp(i):
    embed = discord.Embed(title="قائمة الأوامر", color=discord.Color.blue())
    embed.add_field(name="⚙️ الإعدادات والحماية", value="`set-logs`, `set-autorole`, `set-welcome`, `set-ticket`, `set-suggest`, `set-nick`, `add-security`, `remove-security`")
    embed.add_field(name="🛡️ الإدارة", value="`ban`, `kick`, `timeout`, `clear`, `lock`, `unlock`, `warn`, `slowmode`, `nick`, `move`, `vmute`, `hide`, `show`, `role-add`")
    embed.add_field(name="💰 الاقتصاد", value="`daily`, `credits`, `work`, `transfer`, `top-bank`, `give-money`, `rob`, `fish`, `slots`, `coin`, `hunt`, `salary`, `reset-money`, `shop`, `bank-info`, `pay`")
    embed.add_field(name="🎮 الترفيه", value="`iq`, `hack`, `joke`, `ship`, `kill`, `slap`, `dice`, `hug`, `punch`, `choose`, `wanted`, `dance`, `xo`, `cat`")
    embed.add_field(name="📋 عام", value="`ping`, `avatar`, `server`, `user`, `invite`, `roles`, `channels`, `id`, `say`, `suggest`, `rules`, `members`, `uptime`")
    await i.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="بنج")
async def png(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar", description="افتار")
async def av(i, m: discord.Member=None): u=m or i.user; await i.response.send_message(u.display_avatar.url)
@bot.tree.command(name="server", description="سيرفر")
async def si(i): await i.response.send_message(f"🏰 {i.guild.name} | {i.guild.member_count}")
@bot.tree.command(name="user", description="عضو")
async def ui(i, m: discord.Member=None): u=m or i.user; await i.response.send_message(f"👤 {u.name}")
@bot.tree.command(name="invite", description="دعوة")
async def inv(i): await i.response.send_message("🔗 [رابط]")
@bot.tree.command(name="roles", description="رتب")
async def rc(i): await i.response.send_message(f"📜 {len(i.guild.roles)}")
@bot.tree.command(name="channels", description="رومات")
async def cc(i): await i.response.send_message(f"📁 {len(i.guild.channels)}")
@bot.tree.command(name="id", description="آيدي")
async def bi(i): await i.response.send_message(f"🆔 {i.user.id}")
@bot.tree.command(name="say", description="قول")
async def say(i, t: str): await i.channel.send(t); await i.response.send_message("✅", ephemeral=True)
@bot.tree.command(name="suggest", description="اقتراح")
async def sug(i, t: str): await i.response.send_message("✅")
@bot.tree.command(name="rules", description="قوانين")
async def rul(i): await i.response.send_message("📜 القوانين")
@bot.tree.command(name="members", description="أعضاء")
async def mem(i): await i.response.send_message(f"👥 {i.guild.member_count}")
@bot.tree.command(name="uptime", description="وقت التشغيل")
async def upt(i): await i.response.send_message("🕒 متصل")

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.run(os.getenv("DISCORD_TOKEN"))
