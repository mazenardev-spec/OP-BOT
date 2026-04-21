import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random, asyncio, json, os, time
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# --- 1. نظام الـ Keep Alive ---
app = Flask('')
@app.route('/')
def home(): return "OP BOT IS ONLINE"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f:
            json.dump({"bank": {}, "warns": {}, "auto_role": {}, "responses": {}, "settings": {}, "daily_cooldown": {}, "levels": {}, "security": {}}, f)
    with open("op_data.json", "r") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: json.dump(data, f, indent=4)

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

# --- 4. فئة البوت والأحداث (اللوج المطور) ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActions())
        await self.tree.sync()

    async def send_log(self, guild, embed):
        db = load_db()
        log_id = db["settings"].get(f"{guild.id}_logs")
        if log_id:
            ch = guild.get_channel(log_id)
            if ch: await ch.send(embed=embed)

    # أحداث اللوج
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

bot = OPBot()

# ==========================================
# الفئة 1: الإدارة (15 أمر - تشمل التيكت)
# ==========================================
@bot.tree.command(name="set-ticket", description="إرسال رسالة فتح التذاكر في قناة محددة")
@app_commands.checks.has_permissions(administrator=True)
async def setticket(i, channel: discord.TextChannel):
    embed = discord.Embed(title="نظام التذاكر", description="اضغط على الزر أدناه للتحدث مع الإدارة", color=discord.Color.blue())
    await channel.send(embed=embed, view=TicketView())
    await i.response.send_message(f"✅ تم إرسال نظام التذاكر في {channel.mention}")

@bot.tree.command(name="ban", description="حظر عضو من السيرفر")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i, member: discord.Member, reason: str="غير محدد"):
    await member.ban(reason=reason); await i.response.send_message(f"✅ تم حظر {member.name}")

@bot.tree.command(name="kick", description="طرد عضو من السيرفر")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i, member: discord.Member, reason: str="غير محدد"):
    await member.kick(reason=reason); await i.response.send_message(f"✅ تم طرد {member.name}")

@bot.tree.command(name="clear", description="مسح الرسائل من القناة")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i, amount: int):
    await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 تم مسح {amount} رسالة", ephemeral=True)

@bot.tree.command(name="lock", description="قفل القناة")
async def lock(i):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 تم قفل القناة")

@bot.tree.command(name="unlock", description="فتح القناة")
async def unlock(i):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 تم فتح القناة")

@bot.tree.command(name="mute", description="إسكات عضو لفترة محددة")
async def mute(i, member: discord.Member, minutes: int):
    await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🔇 تم إسكات {member.name}")

@bot.tree.command(name="unmute", description="إزالة الإسكات عن عضو")
async def unmute(i, member: discord.Member):
    await member.timeout(None); await i.response.send_message(f"🔊 تم فك إسكات {member.name}")

@bot.tree.command(name="warn", description="إعطاء تحذير لعضو")
async def warn(i, member: discord.Member, reason: str):
    db=load_db(); mid=str(member.id); db["warns"][mid]=db["warns"].get(mid,0)+1; save_db(db)
    await i.response.send_message(f"⚠️ تحذير لـ {member.mention} | السبب: {reason}")

@bot.tree.command(name="set-logs", description="تحديد قناة اللوج الشامل")
async def setlogs(i, channel: discord.TextChannel):
    db=load_db(); db["settings"][f"{i.guild.id}_logs"]=channel.id; save_db(db)
    await i.response.send_message(f"✅ تم ضبط اللوج في {channel.mention}")

@bot.tree.command(name="set-welcome", description="تحديد قناة الترحيب")
async def setw(i, channel: discord.TextChannel):
    db=load_db(); db["settings"][f"{i.guild.id}_welcome"]=channel.id; save_db(db)
    await i.response.send_message(f"✅ تم تحديد {channel.mention} للترحيب")

@bot.tree.command(name="slowmode", description="تفعيل الوضع البطيء")
async def slow(i, seconds: int):
    await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"🐢 الوضع البطيء: {seconds} ثانية")

@bot.tree.command(name="nick", description="تغيير لقب عضو")
async def nick(i, member: discord.Member, name: str):
    await member.edit(nick=name); await i.response.send_message(f"✅ تم تغيير لقب {member.name}")

@bot.tree.command(name="security", description="تفعيل/تعطيل حماية الروابط")
async def sec(i, status: bool):
    db=load_db(); db["security"][str(i.guild.id)]=status; save_db(db)
    await i.response.send_message(f"🛡️ الحماية: {'مشغلة' if status else 'مغلقة'}")

@bot.tree.command(name="unban", description="فك الحظر عن عضو بالآيدي")
async def unban(i, user_id: str):
    user = await bot.fetch_user(int(user_id)); await i.guild.unban(user)
    await i.response.send_message(f"✅ تم فك حظر {user.name}")

# ==========================================
# الفئة 2: الاقتصاد (15 أمر)
# ==========================================
@bot.tree.command(name="daily", description="استلام الراتب اليومي")
async def daily(i):
    db=load_db(); u=str(i.user.id); now=time.time()
    if now - db["daily_cooldown"].get(u,0) < 86400: return await i.response.send_message("❌ عد غداً", ephemeral=True)
    db["bank"][u]=db["bank"].get(u,0)+1000; db["daily_cooldown"][u]=now; save_db(db); await i.response.send_message("💰 تم استلام 1000")

@bot.tree.command(name="credits", description="معرفة رصيدك")
async def cr(i, member: discord.Member=None):
    m=member or i.user; await i.response.send_message(f"💳 رصيد {m.name}: {load_db()['bank'].get(str(m.id),0)}")

@bot.tree.command(name="work", description="العمل لجمع المال")
async def work(i):
    r=random.randint(50,300); db=load_db(); u=str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+r; save_db(db)
    await i.response.send_message(f"👷 عملت وربحت {r}")

@bot.tree.command(name="transfer", description="تحويل مال لعضو")
async def trans(i, member: discord.Member, amount: int):
    db=load_db(); s=str(i.user.id); r=str(member.id)
    if db["bank"].get(s,0)<amount: return await i.response.send_message("❌ رصيدك ناقص")
    db["bank"][s]-=amount; db["bank"][r]=db["bank"].get(r,0)+amount; save_db(db); await i.response.send_message(f"✅ تم تحويل {amount}")

@bot.tree.command(name="top-bank", description="أغنى 5 في السيرفر")
async def topb(i):
    top=sorted(load_db()["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    await i.response.send_message("\n".join([f"<@{u}>: {a}" for u,a in top]))

@bot.tree.command(name="give-money", description="منح مال لعضو (إدارة)")
async def gm(i, member: discord.Member, amount: int):
    db=load_db(); u=str(member.id); db["bank"][u]=db["bank"].get(u,0)+amount; save_db(db); await i.response.send_message("🎁 تمت الهدية")

@bot.tree.command(name="rob", description="محاولة سرقة عضو")
async def rob(i, member: discord.Member): await i.response.send_message(random.choice(["نجحت في السرقة!", "انمسكت ودخلت السجن!"]))

@bot.tree.command(name="fish", description="صيد السمك")
async def fish(i): await i.response.send_message(f"🎣 اصطدت سمكة بقيمة {random.randint(10,100)}")

@bot.tree.command(name="slots", description="لعبة السلوتس")
async def slots(i): await i.response.send_message("🎰 | 🍒 | 🍒 | 🍒 - فزت!")

@bot.tree.command(name="coin", description="ملك أو كتابة")
async def coin(i): await i.response.send_message(f"🪙 النتيجة: {random.choice(['ملك', 'كتابة'])}")

@bot.tree.command(name="hunt", description="صيد الحيوانات")
async def hunt(i): await i.response.send_message("🏹 صيد موفق")

@bot.tree.command(name="salary", description="راتب إضافي")
async def sal(i): await i.response.send_message("💼 +200")

@bot.tree.command(name="shop", description="المتجر")
async def shop(i): await i.response.send_message("🛒 المتجر قريباً")

@bot.tree.command(name="bank-info", description="حالة البنك")
async def binf(i): await i.response.send_message("🏦 بنك OP يعمل بكفاءة")

@bot.tree.command(name="reset-money", description="تصفير محفظة عضو")
async def rmoney(i, member: discord.Member):
    db=load_db(); db["bank"][str(member.id)]=0; save_db(db); await i.response.send_message("🧹 تم تصفير المحفظة")

# ==========================================
# الفئة 3: الترفيه (15 أمر)
# ==========================================
@bot.tree.command(name="iq", description="قياس الذكاء")
async def iq(i): await i.response.send_message(f"🧠 نسبة ذكائك: {random.randint(1,200)}%")
@bot.tree.command(name="hack", description="اختراق وهمي")
async def hack(i, member: discord.Member): await i.response.send_message(f"💻 جاري اختراق {member.name}...")
@bot.tree.command(name="joke", description="نكتة مضحكة")
async def joke(i): await i.response.send_message("مرة واحد...")
@bot.tree.command(name="ship", description="نسبة الحب بين اثنين")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 نسبة التوافق: {random.randint(1,100)}%")
@bot.tree.command(name="kill", description="قتل عضو وهمياً")
async def kill(i, m: discord.Member): await i.response.send_message(f"⚔️ تم تصفية {m.name}")
@bot.tree.command(name="slap", description="إعطاء كف")
async def slap(i, m: discord.Member): await i.response.send_message(f"🖐️ كف خماسي لـ {m.name}")
@bot.tree.command(name="dice", description="رمي الزار")
async def dice(i): await i.response.send_message(f"🎲 النتيجة: {random.randint(1,6)}")
@bot.tree.command(name="hug", description="حضن عضو")
async def hug(i, m: discord.Member): await i.response.send_message(f"🤗 حضن لـ {m.name}")
@bot.tree.command(name="punch", description="لكمة عضو")
async def punch(i, m: discord.Member): await i.response.send_message(f"👊 لكمة لـ {m.name}")
@bot.tree.command(name="choose", description="البوت يختار لك")
async def cho(i, a: str, b: str): await i.response.send_message(f"🤔 أختار: {random.choice([a,b])}")
@bot.tree.command(name="love", description="نسبة حبك للبوت")
async def love(i): await i.response.send_message(f"❤️ أحبك بنسبة {random.randint(1,100)}%")
@bot.tree.command(name="hot", description="قياس الجمال")
async def hot(i): await i.response.send_message(f"🔥 نسبة جمالك: {random.randint(1,100)}%")
@bot.tree.command(name="wanted", description="أنت مطلوب!")
async def wan(i): await i.response.send_message("⚠️ مطلوب للعدالة فوراً!")
@bot.tree.command(name="dance", description="رقص!")
async def dan(i): await i.response.send_message("💃🕺")
@bot.tree.command(name="xo", description="تحدي XO")
async def xo(i, member: discord.Member): await i.response.send_message(f"🎮 تحدي XO مع {member.mention}")

# ==========================================
# الفئة 4: عام (15 أمر)
# ==========================================
@bot.tree.command(name="help", description="قائمة أوامر البوت")
async def hlp(i): await i.response.send_message("🛡️ إدارة | 💰 اقتصاد | 🎮 ترفيه | 📁 عام")
@bot.tree.command(name="ping", description="سرعة استجابة البوت")
async def png(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar", description="صورة بروفايل")
async def av(i, member: discord.Member=None): m=member or i.user; await i.response.send_message(m.display_avatar.url)
@bot.tree.command(name="server-info", description="معلومات السيرفر")
async def si(i): await i.response.send_message(f"🏰 {i.guild.name} | الأعضاء: {i.guild.member_count}")
@bot.tree.command(name="user-info", description="معلوماتك الشخصية")
async def ui(i, member: discord.Member=None): m=member or i.user; await i.response.send_message(f"👤 {m.name} | آيدي: {m.id}")
@bot.tree.command(name="uptime", description="مدة عمل البوت")
async def upt(i): await i.response.send_message("🕒 يعمل منذ ساعات طويلة")
@bot.tree.command(name="invite", description="دعوة البوت لسيرفرك")
async def inv(i): await i.response.send_message("🔗 رابط الدعوة متوفر في الخاص")
@bot.tree.command(name="roles-count", description="عدد الرتب بالسيرفر")
async def rc(i): await i.response.send_message(f"📜 عدد الرتب: {len(i.guild.roles)}")
@bot.tree.command(name="channels-count", description="عدد القنوات")
async def cc(i): await i.response.send_message(f"📁 عدد القنوات: {len(i.guild.channels)}")
@bot.tree.command(name="bot-id", description="آيدي البوت")
async def bi(i): await i.response.send_message(bot.user.id)
@bot.tree.command(name="say", description="تكرار كلامك")
async def say(i, text: str): await i.channel.send(text); await i.response.send_message("تم", ephemeral=True)
@bot.tree.command(name="suggest", description="إرسال اقتراح")
async def sug(i, text: str): await i.response.send_message("✅ تم استلام اقتراحك")
@bot.tree.command(name="bot-support", description="سيرفر دعم البوت")
async def rul(i): await i.response.send_message("https://discord.gg/vvmaAbasEN")
@bot.tree.command(name="bot-creator", description="صانع البوت")
async def bti(i): await i.response.send_message("صانعي هو @mazenardev")
@bot.tree.command(name="members", description="عدد الأعضاء")
async def mem(i): await i.response.send_message(f"👥 {i.guild.member_count}")

# --- التشغيل ---
if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
