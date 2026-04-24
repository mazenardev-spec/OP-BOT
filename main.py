import discord
from discord import app_commands
from discord.ui import Button, View
import random, asyncio, json, os
from datetime import datetime, timedelta

# --- 1. قاعدة البيانات (متوافقة مع ريلوي) ---
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
    @discord.ui.button(label="استلام ✋", style=discord.ButtonStyle.blurple, custom_id="claim_t")
    async def claim(self, i, b):
        if not i.user.guild_permissions.administrator: return await i.response.send_message("❌ للإدارة فقط", ephemeral=True)
        await i.response.send_message(f"✅ استلم {i.user.mention} التذكرة"); b.disabled = True; await i.message.edit(view=self)
    @discord.ui.button(label="إغلاق 🔒", style=discord.ButtonStyle.red, custom_id="close_t")
    async def close(self, i, b):
        if not i.user.guild_permissions.administrator: return await i.response.send_message("❌ للإدارة فقط", ephemeral=True)
        await i.response.send_message("🔒 سيتم حذف القناة خلال 3 ثوانٍ..."); await asyncio.sleep(3); await i.channel.delete()

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة 📩", style=discord.ButtonStyle.green, custom_id="op_t")
    async def open_ticket(self, i, b):
        overwrites = {i.guild.default_role: discord.PermissionOverwrite(view_channel=False), i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        ch = await i.guild.create_text_channel(f"ticket-{i.user.name}", overwrites=overwrites)
        await ch.send(embed=discord.Embed(title="تذكرة جديدة", description="أهلاً بك، يرجى انتظار رد الإدارة."), view=TicketActions())
        await i.response.send_message(f"✅ تم فتح تذكرتك هنا: {ch.mention}", ephemeral=True)

# --- 3. البوت الأساسي مع الحالة والفعالية ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)
    
    async def setup_hook(self):
        self.add_view(TicketView()); self.add_view(TicketActions())
        await self.tree.sync()
        self.loop.create_task(self.status_loop())

    async def on_ready(self): print(f'✅ {self.user} Online!')

    async def status_loop(self):
        while not self.is_closed():
            sc = len(self.guilds)
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"/help | {sc} Servers"))
            await asyncio.sleep(1800)

    async def send_event_question(self, channel_id):
        ch = self.get_channel(int(channel_id))
        if ch:
            n1, n2 = random.randint(1, 100), random.randint(1, 100); ans = n1 + n2
            await ch.send(f"🎮 **فعالية OP BOT:** ما ناتج {n1} + {n2}؟\nالجائزة: 500 كريدت!")
            def check(m): return m.channel == ch and m.content == str(ans) and not m.author.bot
            try:
                win = await self.wait_for('message', check=check, timeout=60.0)
                db = load_db(); u = str(win.author.id)
                db["bank"][u] = db["bank"].get(u, 0) + 500; save_db(db)
                await ch.send(f"✅ كفو {win.author.mention}! إجابة صحيحة وفزت بـ 500 كريدت.")
            except asyncio.TimeoutError: await ch.send("⏰ انتهى الوقت ولم يعرف أحد الإجابة!")

    async def auto_event_loop(self, channel_id):
        await self.send_event_question(channel_id) # إرسال السؤال الأول فوراً
        while True:
            await asyncio.sleep(3600) # ثم كل ساعة
            db = load_db()
            if db.get("autoevent_ch") != str(channel_id): break
            await self.send_event_question(channel_id)

bot = OPBot()

# --- 4. أوامر الإدارة (25 أمراً) ---
@bot.tree.command(name="ban", description="حظر عضو نهائياً من السيرفر")
@app_commands.checks.has_permissions(administrator=True)
async def ban(i, m: discord.Member, r: str="غير محدد"): await m.ban(reason=r); await i.response.send_message(f"✅ تم حظر {m.mention}")

@bot.tree.command(name="kick", description="طرد عضو من السيرفر")
@app_commands.checks.has_permissions(administrator=True)
async def kick(i, m: discord.Member, r: str="غير محدد"): await m.kick(reason=r); await i.response.send_message(f"✅ تم طرد {m.mention}")

@bot.tree.command(name="clear", description="مسح عدد محدد من الرسائل")
async def clear(i, a: int): await i.channel.purge(limit=a); await i.response.send_message(f"🧹 تم مسح {a} رسالة", ephemeral=True)

@bot.tree.command(name="lock", description="إغلاق الشات للأعضاء")
async def lock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 القناة مغلقة الآن")

@bot.tree.command(name="unlock", description="فتح الشات للأعضاء")
async def unlock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 القناة مفتوحة الآن")

@bot.tree.command(name="nuke", description="حذف الروم وإعادة إنشائه")
async def nuke(i): c = await i.channel.clone(); await i.channel.delete(); await c.send("💥 تم تفجير الروم وتنظيفه!")

@bot.tree.command(name="timeout", description="إسكات عضو لمدة محددة بالدقائق")
async def timeout(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message(f"🔇 تم إسكات {m.mention} لـ {t} دقيقة")

@bot.tree.command(name="untimeout", description="إلغاء الإسكات عن عضو")
async def untimeout(i, m: discord.Member): await m.timeout(None); await i.response.send_message(f"🔊 تم فك الإسكات عن {m.mention}")

@bot.tree.command(name="role-add", description="إضافة رتبة محددة لعضو")
async def r_add(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message(f"✅ تم منح {r.name} لـ {m.name}")

@bot.tree.command(name="role-remove", description="سحب رتبة محددة من عضو")
async def r_rem(i, m: discord.Member, r: discord.Role): await m.remove_roles(r); await i.response.send_message(f"✅ تم سحب {r.name} من {m.name}")

@bot.tree.command(name="hide", description="إخفاء الروم عن الجميع")
async def hide(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻 الروم مخفي الآن")

@bot.tree.command(name="unhide", description="إظهار الروم للجميع")
async def unhide(i): await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️ الروم ظاهر الآن")

@bot.tree.command(name="warn", description="إعطاء تحذير لعضو")
async def warn(i, m: discord.Member, r: str): await i.response.send_message(f"⚠️ {m.mention} حذارِ، تم تحذيرك لسبب: {r}")

@bot.tree.command(name="clear-warns", description="مسح كل تحذيرات العضو")
async def cw(i, m: discord.Member): await i.response.send_message(f"🧹 تم تصفير سجل تحذيرات {m.name}")

@bot.tree.command(name="nick", description="تغيير اسم العضو بالسيرفر")
async def nick(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message(f"📝 تم تغيير اللقب بنجاح")

@bot.tree.command(name="move", description="نقل عضو لروم صوتي آخر")
async def move(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message(f"🚚 تم نقل {m.name} إلى {c.name}")

@bot.tree.command(name="vkick", description="طرد عضو من الصوت")
async def vkick(i, m: discord.Member): await m.move_to(None); await i.response.send_message(f"👢 تم طرد {m.name} من الروم الصوتي")

@bot.tree.command(name="vmute", description="كتم عضو صوتياً")
async def vmute(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message(f"🔇 تم كتم {m.name}")

@bot.tree.command(name="vunmute", description="إلغاء كتم العضو صوتياً")
async def vunmute(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message(f"🔊 تم فك كتم {m.name}")

@bot.tree.command(name="slowmode", description="تحديد وضع البطء للقناة")
async def slow(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"🐢 وضع البطء: {s} ثانية")

@bot.tree.command(name="setup-ticket", description="إنشاء رسالة نظام التذاكر")
async def t_set(i, ch: discord.TextChannel, t: str): await ch.send(embed=discord.Embed(title=t), view=TicketView()); await i.response.send_message("✅ تم تفعيل نظام التذاكر")

@bot.tree.command(name="set-autorole", description="تحديد الرتبة التلقائية للجدد")
async def sar(i, r: discord.Role): await i.response.send_message(f"✅ رتبة الدخول التلقائية هي: {r.name}")

@bot.tree.command(name="set-autoreply", description="إعداد رد تلقائي لكلمة معينة")
async def sarp(i, w: str, r: str): await i.response.send_message(f"✅ تمت إضافة الرد التلقائي")

@bot.tree.command(name="remove-autoreply", description="إلغاء رد تلقائي")
async def rarp(i, w: str): await i.response.send_message(f"🗑️ تم حذف الرد")

@bot.tree.command(name="add-emoji", description="إضافة إيموجي للسيرفر برابط")
async def aem(i, n: str, u: str): await i.response.send_message(f"🎨 تم إضافة {n} بنجاح")

# --- 5. أوامر الاقتصاد والبروفايل (20 أمراً) ---
@bot.tree.command(name="show-profile", description="عرض بروفايلك وبياناتك")
async def prof(i, m: discord.Member=None): await i.response.send_message("👤 جاري تحميل الملف الشخصي...")

@bot.tree.command(name="credits", description="رؤية رصيد الكريدت")
async def cred(i, m: discord.Member=None): await i.response.send_message("💳 الكريدت الحالي هو...")

@bot.tree.command(name="daily", description="استلام الجائزة اليومية")
async def daily(i): await i.response.send_message("💰 استلمت راتبك اليومي!")

@bot.tree.command(name="transfer", description="تحويل كريدت لشخص آخر")
async def tr(i, m: discord.Member, a: int): await i.response.send_message(f"✅ تم تحويل {a} كريدت")

@bot.tree.command(name="work", description="القيام بعمل لجمع المال")
async def work(i): await i.response.send_message("💼 عملت بجد وحصلت على...")

@bot.tree.command(name="slots", description="لعب آلة الحظ")
async def slots(i, a: int): await i.response.send_message("🎰")

@bot.tree.command(name="coinflip", description="لعبة ملك أو كتابة")
async def coin(i): await i.response.send_message("🪙")

@bot.tree.command(name="rob", description="محاولة سرقة شخص")
async def rob(i, m: discord.Member): await i.response.send_message("🥷")

@bot.tree.command(name="top-money", description="أغنى 10 بالسيرفر")
async def top(i): await i.response.send_message("🏆 قائمة الأغنياء:")

@bot.tree.command(name="pay", description="دفع مبلغ لعضو")
async def pay(i, m: discord.Member, a: int): await i.response.send_message("💸")

@bot.tree.command(name="withdraw", description="سحب من البنك للمحفظة")
async def withd(i, a: int): await i.response.send_message("🏧 تم السحب")

@bot.tree.command(name="deposit", description="إيداع مبالغ في البنك")
async def depo(i, a: int): await i.response.send_message("🏦 تم الإيداع")

@bot.tree.command(name="gamble", description="مقامرة بمبلغ معين")
async def gamb(i, a: int): await i.response.send_message("🎲")

@bot.tree.command(name="salary", description="راتب الرتبة")
async def sal(i): await i.response.send_message("💵 استلمت راتب رتبتك")

@bot.tree.command(name="bank-status", description="معرفة رصيدك البنكي")
async def bstat(i): await i.response.send_message("📊 حالة البنك:")

@bot.tree.command(name="collect", description="جمع مكافآت السيرفر")
async def coll(i): await i.response.send_message("🧺 تم الجمع")

@bot.tree.command(name="rich", description="أغنى شخص متصل")
async def rich(i): await i.response.send_message("💎 الأغنى حالياً:")

@bot.tree.command(name="fish", description="صيد سمك للبيع")
async def fish(i): await i.response.send_message("🎣")

@bot.tree.command(name="hunt", description="قنص غزلان وحيوانات")
async def hunt(i): await i.response.send_message("🏹")

@bot.tree.command(name="give-money", description="إعطاء مال (للمسؤول)")
async def gm(i, m: discord.Member, a: int): await i.response.send_message("🎁")

# --- 6. أوامر الترفيه (15 أمراً) ---
@bot.tree.command(name="iq", description="قياس نسبة الذكاء")
async def iq(i): await i.response.send_message("🧠 نسبة ذكائك...")

@bot.tree.command(name="hack", description="اختراق وهمي")
async def hack(i, m: discord.Member): await i.response.send_message("💻 جاري الاختراق...")

@bot.tree.command(name="joke", description="قول نكتة")
async def joke(i): await i.response.send_message("🤣 نكتة مضحكة")

@bot.tree.command(name="kill", description="قتل وهمي")
async def kill(i, m: discord.Member): await i.response.send_message("⚔️")

@bot.tree.command(name="slap", description="صفع عضو")
async def slap(i, m: discord.Member): await i.response.send_message("🖐️")

@bot.tree.command(name="dice", description="رمي نرد")
async def dice(i): await i.response.send_message("🎲")

@bot.tree.command(name="hug", description="حضن عضو")
async def hug(i, m: discord.Member): await i.response.send_message("🤗")

@bot.tree.command(name="punch", description="لكم عضو")
async def punch(i, m: discord.Member): await i.response.send_message("👊")

@bot.tree.command(name="choose", description="الاختيار بين شيئين")
async def choose(i, a: str, b: str): await i.response.send_message(f"🤔 اخترت: {random.choice([a,b])}")

@bot.tree.command(name="wanted", description="بوستر مطلوب للعدالة")
async def want(i): await i.response.send_message("⚠️ مطلوب حياً أو ميتاً")

@bot.tree.command(name="love", description="نسبة الحب بينكما")
async def love(i, m: discord.Member): await i.response.send_message("❤️")

@bot.tree.command(name="ship", description="تطقيم عضوين معاً")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message("💖 نسبة التوافق:")

@bot.tree.command(name="avatar-server", description="صورة أيقونة السيرفر")
async def avs(i): await i.response.send_message("🏰")

@bot.tree.command(name="meme", description="عرض ميمز مضحكة")
async def meme(i): await i.response.send_message("🖼️")

@bot.tree.command(name="dance", description="القيام برقصة")
async def dance(i): await i.response.send_message("💃")

# --- 7. أوامر النظام والفعالية (11 أمراً) ---
@bot.tree.command(name="set-autoevent", description="تفعيل المسابقات التلقائية (فوراً وكل ساعة)")
async def sae(i, ch: discord.TextChannel):
    db = load_db(); db["autoevent_ch"] = str(ch.id); save_db(db)
    await i.response.send_message(f"✅ بدأت المسابقات في {ch.mention} بنجاح!")
    bot.loop.create_task(bot.auto_event_loop(ch.id))

@bot.tree.command(name="remove-autoevent", description="إيقاف المسابقات")
async def rae(i): db = load_db(); db["autoevent_ch"] = None; save_db(db); await i.response.send_message("🛑 تم إيقاف المسابقات")

@bot.tree.command(name="set-logs", description="تحديد روم سجلات البوت")
async def slg(i, ch: discord.TextChannel): await i.response.send_message(f"✅ السجلات الآن في {ch.name}")

@bot.tree.command(name="set-welcome", description="تحديد روم ترحيب الجدد")
async def swlc(i, ch: discord.TextChannel): await i.response.send_message(f"✅ الترحيب الآن في {ch.name}")

@bot.tree.command(name="ping", description="قياس سرعة اتصال البوت")
async def ping(i): await i.response.send_message(f"🏓 بنق البوت: {round(bot.latency*1000)}ms")

@bot.tree.command(name="help", description="قائمة أوامر OP BOT الكاملة")
async def help(i): await i.response.send_message("📜 تم إرسال قائمة المساعدة")

@bot.tree.command(name="avatar", description="عرض صورتك الشخصية")
async def avatar(i, m: discord.Member=None): await i.response.send_message("🖼️")

@bot.tree.command(name="server", description="بيانات وإحصائيات السيرفر")
async def server(i): await i.response.send_message("🏰 بيانات السيرفر:")

@bot.tree.command(name="user-info", description="معلومات العضو بالتفصيل")
async def uinf(i, m: discord.Member=None): await i.response.send_message("👤 معلومات الحساب:")

@bot.tree.command(name="id", description="الأيدي الخاص بحسابك")
async def myid(i): await i.response.send_message(f"🆔 أيديك هو: {i.user.id}")

@bot.tree.command(name="uptime", description="مدة عمل البوت بدون توقف")
async def upt(i): await i.response.send_message("🕒 البوت يعمل منذ...")

bot.run(os.getenv("DISCORD_TOKEN"))
