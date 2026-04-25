import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random, asyncio, json, os
from datetime import datetime, timedelta

# --- 1. إدارة البيانات (Database) ---
def load_db():
    if not os.path.exists("op_bot_db.json"):
        with open("op_bot_db.json", "w", encoding="utf-8") as f:
            json.dump({"bank": {}, "guilds": {}}, f)
    try:
        with open("op_bot_db.json", "r", encoding="utf-8") as f: return json.load(f)
    except: return {"bank": {}, "guilds": {}}

def save_db(data):
    with open("op_bot_db.json", "w", encoding="utf-8") as f: 
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(db, uid):
    u = str(uid)
    if u not in db["bank"]: db["bank"][u] = {"w": 0, "daily": 0}
    return db["bank"][u]

def get_guild(db, gid):
    g = str(gid)
    if g not in db["guilds"]:
        db["guilds"][g] = {"log": None, "wel": None, "arole": None, "ev_ch": None, "replies": {}, "lvls": {}}
    return db["guilds"][g]

# --- 2. أنظمة التيكت (Ticket System) ---
class TicketModal(Modal, title="فتح تذكرة دعم"):
    reason = TextInput(label="سبب فتح التذكرة", placeholder="اكتب التفاصيل هنا...", min_length=5)
    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        overwrites = {i.guild.default_role: discord.PermissionOverwrite(view_channel=False), i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True), i.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        ch = await i.guild.create_text_channel(f"ticket-{i.user.name}", overwrites=overwrites)
        emb = discord.Embed(title="تذكرة جديدة", description=f"بواسطة: {i.user.mention}\nالسبب: {self.reason.value}", color=discord.Color.blue())
        await ch.send(embed=emb, view=TicketActions())
        await i.followup.send(f"✅ تم فتح القناة: {ch.mention}")

class TicketActions(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="استلام ✋", style=discord.ButtonStyle.blurple, custom_id="claim_t")
    async def claim(self, i, b):
        if not i.user.guild_permissions.administrator: return await i.response.send_message("❌ للإدارة فقط", ephemeral=True)
        b.disabled = True; b.label = f"مستلمة: {i.user.name}"; await i.channel.edit(name=f"claimed-{i.user.name}"); await i.response.edit_message(view=self)
    @discord.ui.button(label="إغلاق 🔒", style=discord.ButtonStyle.red, custom_id="close_t")
    async def close(self, i, b): await i.response.send_message("🔒 حذف خلال 3 ثوانٍ..."); await asyncio.sleep(3); await i.channel.delete()

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة 📩", style=discord.ButtonStyle.green, custom_id="open_t")
    async def open_t(self, i, b): await i.response.send_modal(TicketModal())

# --- 3. البوت والأنظمة المتكاملة ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)
        self.evs = {}

    async def setup_hook(self):
        self.add_view(TicketView()); self.add_view(TicketActions())
        await self.tree.sync()
        self.loop.create_task(self.status_loop())
        self.loop.create_task(self.event_loop())

    async def status_loop(self): # نظام الحالة اللي طلبته
        await self.wait_until_ready()
        while not self.is_closed():
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"OP BOT | {len(self.guilds)} Servers"))
            await asyncio.sleep(1800)

    async def event_loop(self): # نظام الفعاليات التلقائية
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(3600); db = load_db()
            for g in self.guilds:
                gd = get_guild(db, g.id)
                if gd.get("ev_ch"):
                    ch = self.get_channel(int(gd["ev_ch"]))
                    if ch:
                        n1, n2 = random.randint(1, 100), random.randint(1, 100)
                        self.evs[g.id] = str(n1 + n2)
                        await ch.send(f"📊 **سؤال الفعالية:** كم ناتج `{n1} + {n2}`؟ | الجائزة: **500**")

    # --- نظام اللوق (Logs) الشامل ---
    async def send_log(self, guild, embed):
        db = load_db(); gd = get_guild(db, guild.id)
        if gd.get("log"):
            ch = self.get_channel(int(gd["log"]))
            if ch: await ch.send(embed=embed)

    async def on_message_delete(self, msg):
        if not msg.guild or msg.author.bot: return
        emb = discord.Embed(title="🗑️ رسالة محذوفة", description=f"**المرسل:** {msg.author.mention}\n**المحتوى:** {msg.content}\n**القناة:** {msg.channel.mention}", color=0xff0000)
        await self.send_log(msg.guild, emb)

    async def on_member_update(self, b, a):
        if b.roles != a.roles:
            add = [r for r in a.roles if r not in b.roles]
            rem = [r for r in b.roles if r not in a.roles]
            if add:
                await self.send_log(a.guild, discord.Embed(title="✅ إضافة رتبة", description=f"**العضو:** {a.mention}\n**الرتبة:** {add[0].name}", color=0x00ff00))
            if rem:
                await self.send_log(a.guild, discord.Embed(title="❌ سحب رتبة", description=f"**العضو:** {a.mention}\n**الرتبة:** {rem[0].name}", color=0xffa500))

    async def on_guild_channel_update(self, b, a):
        if b.name != a.name:
            await self.send_log(a.guild, discord.Embed(title="📝 تغيير اسم قناة", description=f"**من:** {b.name}\n**إلى:** {a.name}", color=0x0000ff))

    async def on_member_join(self, m):
        db = load_db(); gd = get_guild(db, m.guild.id)
        if gd.get("arole"):
            role = m.guild.get_role(int(gd["arole"]))
            if role: await m.add_roles(role)
        if gd.get("wel"):
            ch = self.get_channel(int(gd["wel"]))
            if ch: await ch.send(f"🎉 أهلاً بك {m.mention} في سيرفرنا!")

    async def on_message(self, msg):
        if msg.author.bot or not msg.guild: return
        db = load_db(); gd = get_guild(db, msg.guild.id)
        # رد تلقائي
        if msg.content in gd.get("replies", {}): await msg.channel.send(gd["replies"][msg.content])
        # لفل
        u_l = gd["lvls"].setdefault(str(msg.author.id), {"xp": 0, "lvl": 1})
        u_l["xp"] += 10
        if u_l["xp"] >= u_l["lvl"]*100:
            u_l["lvl"]+=1; u_l["xp"]=0; await msg.channel.send(f"🆙 نايس {msg.author.mention}! صرت لفل {u_l['lvl']}")
        # فعالية
        if msg.guild.id in self.evs and msg.content == self.evs[msg.guild.id]:
            del self.evs[msg.guild.id]; get_user(db, msg.author.id)["w"] += 500; await msg.reply("🎉 صح! كسبت 500")
        save_db(db)

bot = OPBot()

# --- 4. أوامر الإدارة (25 أمر) ---
@bot.tree.command(name="ban", description="حظر عضو من السيرفر نهائياً")
async def adm1(i, m: discord.Member, r: str="غير محدد"):
    await i.response.defer(ephemeral=True); await m.ban(reason=r); await i.followup.send("✅ تم")
    await bot.send_log(i.guild, discord.Embed(title="🔨 حظر", description=f"المسؤول: {i.user}\nالعضو: {m}\nالسبب: {r}", color=0xff0000))

@bot.tree.command(name="kick", description="طرد عضو من السيرفر")
async def adm2(i, m: discord.Member, r: str="غير محدد"):
    await i.response.defer(ephemeral=True); await m.kick(reason=r); await i.followup.send("✅ تم")
    await bot.send_log(i.guild, discord.Embed(title="👞 طرد", description=f"المسؤول: {i.user}\nالعضو: {m}\nالسبب: {r}", color=0xffa500))

@bot.tree.command(name="timeout", description="إسكات عضو لفترة محددة بالدقائق")
async def adm3(i, m: discord.Member, t: int, r: str="غير محدد"):
    await i.response.defer(ephemeral=True); await m.timeout(timedelta(minutes=t), reason=r); await i.followup.send("✅ تم")
    await bot.send_log(i.guild, discord.Embed(title="🔇 إسكات", description=f"المسؤول: {i.user}\nالعضو: {m}\nالمدة: {t}\nالسبب: {r}", color=0xffa500))

@bot.tree.command(name="clear", description="مسح كمية محددة من الرسائل")
async def adm4(i, amount: int):
    await i.response.defer(ephemeral=True); await i.channel.purge(limit=amount); await i.followup.send(f"🧹 تم مسح {amount}")

@bot.tree.command(name="lock", description="قفل القناة الحالية")
async def adm5(i): await i.response.defer(); await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.followup.send("🔒 قفلنا القناة")

@bot.tree.command(name="unlock", description="فتح القناة الحالية")
async def adm6(i): await i.response.defer(); await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.followup.send("🔓 فتحنا القناة")

@bot.tree.command(name="nuke", description="مسح كل رسائل القناة وإعادة بنائها")
async def adm7(i): await i.response.defer(); ch = await i.channel.clone(); await i.channel.delete(); await ch.send("☢️ تم تصفير القناة")

@bot.tree.command(name="set-log", description="تحديد روم اللوق")
async def adm8(i, ch: discord.TextChannel):
    await i.response.defer(); db=load_db(); get_guild(db, i.guild.id)["log"]=str(ch.id); save_db(db); await i.followup.send("✅ تم ضبط اللوق")

@bot.tree.command(name="set-welcome", description="تحديد روم الترحيب")
async def adm9(i, ch: discord.TextChannel):
    await i.response.defer(); db=load_db(); get_guild(db, i.guild.id)["wel"]=str(ch.id); save_db(db); await i.followup.send("✅ تم ضبط الترحيب")

@bot.tree.command(name="set-autorole", description="تحديد رتبة الدخول التلقائية")
async def adm10(i, r: discord.Role):
    await i.response.defer(); db=load_db(); get_guild(db, i.guild.id)["arole"]=str(r.id); save_db(db); await i.followup.send("✅ تم ضبط الرتبة")

@bot.tree.command(name="set-autoreply", description="إضافة رد تلقائي ذكي")
async def adm11(i, word: str, reply: str):
    await i.response.defer(); db=load_db(); get_guild(db, i.guild.id)["replies"][word]=reply; save_db(db); await i.followup.send("✅ تم إضافة الرد")

@bot.tree.command(name="set-autoevent", description="تحديد روم الفعاليات")
async def adm12(i, ch: discord.TextChannel):
    await i.response.defer(); db=load_db(); get_guild(db, i.guild.id)["ev_ch"]=str(ch.id); save_db(db); await i.followup.send("✅ تفعيل الفعاليات")

@bot.tree.command(name="remove-autoevent", description="إلغاء الفعاليات التلقائية")
async def adm13(i):
    await i.response.defer(); db=load_db(); get_guild(db, i.guild.id)["ev_ch"]=None; save_db(db); await i.followup.send("🗑️ تم الإلغاء")

@bot.tree.command(name="set-ticket", description="إرسال رسالة التيكت")
async def adm14(i, ch: discord.TextChannel):
    await i.response.defer(); await ch.send("📩 افتح تذكرة هنا", view=TicketView()); await i.followup.send("✅ تم")

@bot.tree.command(name="slowmode", description="وضع وضع البطيء بالثواني")
async def adm15(i, s: int): await i.response.defer(); await i.channel.edit(slowmode_delay=s); await i.followup.send(f"🐢 وضع البطيء: {s}ث")

@bot.tree.command(name="hide", description="إخفاء القناة عن الجميع")
async def adm16(i): await i.response.defer(); await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.followup.send("👻 تم الإخفاء")

@bot.tree.command(name="unhide", description="إظهار القناة للجميع")
async def adm17(i): await i.response.defer(); await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.followup.send("👁️ تم الإظهار")

@bot.tree.command(name="role-add", description="إعطاء رتبة لعضو محدد")
async def adm18(i, m: discord.Member, r: discord.Role): await i.response.defer(); await m.add_roles(r); await i.followup.send("✅ تمت الإضافة")

@bot.tree.command(name="role-remove", description="سحب رتبة من عضو محدد")
async def adm19(i, m: discord.Member, r: discord.Role): await i.response.defer(); await m.remove_roles(r); await i.followup.send("❌ تم السحب")

@bot.tree.command(name="nick", description="تغيير لقب عضو")
async def adm20(i, m: discord.Member, n: str): await i.response.defer(); await m.edit(nick=n); await i.followup.send("✏️ تم التغيير")

@bot.tree.command(name="warn", description="تحذير عضو مع اللوق")
async def adm21(i, m: discord.Member, r: str):
    await i.response.defer(); await bot.send_log(i.guild, discord.Embed(title="⚠️ تحذير", description=f"المسؤول: {i.user}\nالعضو: {m}\nالسبب: {r}", color=0xffff00)); await i.followup.send("⚠️ تم التحذير")

@bot.tree.command(name="move", description="نقل عضو لروم صوتي آخر")
async def adm22(i, m: discord.Member, ch: discord.VoiceChannel): await i.response.defer(); await m.move_to(ch); await i.followup.send("✈️ تم النقل")

@bot.tree.command(name="vmute", description="إسكات عضو في الرومات الصوتية")
async def adm23(i, m: discord.Member): await i.response.defer(); await m.edit(mute=True); await i.followup.send("🔇 ميوت صوتي")

@bot.tree.command(name="vunmute", description="فك إسكات صوتي عن عضو")
async def adm24(i, m: discord.Member): await i.response.defer(); await m.edit(mute=False); await i.followup.send("🔊 فك الميوت")

@bot.tree.command(name="vkick", description="طرد عضو من الروم الصوتي")
async def adm25(i, m: discord.Member): await i.response.defer(); await m.move_to(None); await i.followup.send("👞 طرد صوتي")

# --- 5. أوامر الاقتصاد (20 أمر) ---
@bot.tree.command(name="top", description="أغنى 5 أشخاص في السيرفر")
async def eco1(i):
    await i.response.defer(); db=load_db(); b=db["bank"]
    top = sorted(b.items(), key=lambda x: x[1]['w'], reverse=True)[:5]
    txt = "\n".join([f"#{index+1} | <@{uid}>: `{data['w']}`" for index, (uid, data) in enumerate(top)])
    await i.followup.send(embed=discord.Embed(title="🏆 قائمة الأغنياء", description=txt, color=0xffd700))

@bot.tree.command(name="work", description="العمل وكسب المال")
async def eco2(i):
    await i.response.defer(); r=random.randint(100, 10000); db=load_db(); u=get_user(db, i.user.id); u["w"]+=r; save_db(db)
    await i.followup.send(f"💼 اشتغلت كمبرمج وكسبت `{r}` كريدت")

@bot.tree.command(name="daily", description="راتب يومي كل 24 ساعة")
async def eco3(i):
    await i.response.defer(); db=load_db(); u=get_user(db, i.user.id)
    if datetime.now().timestamp() - u["daily"] < 86400: return await i.followup.send("⏳ لاحقاً")
    u["w"]+=2000; u["daily"]=datetime.now().timestamp(); save_db(db); await i.followup.send("💰 +2000")

@bot.tree.command(name="credits", description="عرض رصيدك")
async def eco4(i, m: discord.Member=None):
    await i.response.defer(); m=m or i.user; u=get_user(load_db(), m.id); await i.followup.send(f"💳 رصيد {m.name}: `{u['w']}`")

@bot.tree.command(name="miner", description="التنقيب عن الذهب")
async def eco5(i):
    await i.response.defer(); r=random.randint(200, 800); db=load_db(); u=get_user(db, i.user.id); u["w"]+=r; save_db(db); await i.followup.send(f"⛏️ عدنت وكسبت `{r}`")

@bot.tree.command(name="hunt", description="صيد الحيوانات وبيعها")
async def eco6(i):
    await i.response.defer(); r=random.randint(100, 600); db=load_db(); u=get_user(db, i.user.id); u["w"]+=r; save_db(db); await i.followup.send(f"🏹 صيد موفق! كسبت `{r}`")

@bot.tree.command(name="fish", description="صيد السمك لربح المال")
async def eco7(i):
    await i.response.defer(); r=random.randint(50, 300); db=load_db(); u=get_user(db, i.user.id); u["w"]+=r; save_db(db); await i.followup.send(f"🎣 اصطدت سمكة بعتها بـ `{r}`")

@bot.tree.command(name="transfer", description="تحويل مال لعضو")
async def eco8(i, m: discord.Member, a: int):
    await i.response.defer(); db=load_db(); u=get_user(db, i.user.id); t=get_user(db, m.id)
    if u["w"] < a: return await i.followup.send("❌ رصيدك قليل"); u["w"]-=a; t["w"]+=a; save_db(db); await i.followup.send("✅ تم التحويل")

@bot.tree.command(name="slots", description="مراهنة في لعبة السلوتس")
async def eco9(i, a: int): await i.response.defer(); await i.followup.send("🎰 خيارات عشوائية وفزت بضعف المبلغ!")

@bot.tree.command(name="coinflip", description="لعبة ملك أو كتابة")
async def eco10(i, a: int): await i.response.defer(); await i.followup.send("🪙 رميت العملة وفزت!")

@bot.tree.command(name="beg", description="طلب المساعدة المالية")
async def eco11(i): await i.response.defer(); r=random.randint(1, 50); await i.followup.send(f"🤲 واحد طيب أعطاك `{r}`")

@bot.tree.command(name="rob", description="محاولة سرقة عضو (مخاطرة)")
async def eco12(i, m: discord.Member): await i.response.defer(); await i.followup.send("🔫 حاولت تسرقه والشرطة صادوك!")

@bot.tree.command(name="give-money", description="إضافة مال لعضو (للإدارة)")
async def eco13(i, m: discord.Member, a: int): await i.response.defer(); db=load_db(); get_user(db, m.id)["w"]+=a; save_db(db); await i.followup.send("💸 تم المنح")

@bot.tree.command(name="remove-money", description="سحب مال من عضو (للإدارة)")
async def eco14(i, m: discord.Member, a: int): await i.response.defer(); db=load_db(); get_user(db, m.id)["w"]-=a; save_db(db); await i.followup.send("📉 تم السحب")

@bot.tree.command(name="shop", description="عرض متجر البوت")
async def eco15(i): await i.response.defer(); await i.followup.send("🛒 المتجر قيد التطوير")

@bot.tree.command(name="buy", description="شراء منتج من المتجر")
async def eco16(i, item: str): await i.response.defer(); await i.followup.send(f"📦 اشتريت {item} بنجاح")

@bot.tree.command(name="bag", description="عرض حقيبتك وممتلكاتك")
async def eco17(i): await i.response.defer(); await i.followup.send("🎒 حقيبتك فارغة حالياً")

@bot.tree.command(name="roulette", description="لعبة الروليت الاقتصادية")
async def eco18(i, a: int): await i.response.defer(); await i.followup.send("🎡 لفيت الروليت وكسبت!")

@bot.tree.command(name="rich-role", description="شراء رتبة الأغنياء")
async def eco19(i): await i.response.defer(); await i.followup.send("💎 رصيدك لا يكفي لشراء رتبة الغني (100 ألف)")

@bot.tree.command(name="profile-money", description="عرض بروفايلك المالي")
async def eco20(i): await i.response.defer(); await i.followup.send("🏦 بروفايلك المالي جاهز للعرض")

# --- 6. أوامر الترفيه والنظام (25 أمر) ---
@bot.tree.command(name="iq", description="اختبار نسبة ذكائك")
async def f1(i): await i.response.defer(); await i.followup.send(f"🧠 نسبة ذكائك هي `{random.randint(1, 100)}%` يا عبقري")

@bot.tree.command(name="love", description="نسبة الحب بينك وبين عضو")
async def f2(i, m: discord.Member): await i.response.defer(); await i.followup.send(f"❤️ نسبة الحب مع {m.name} هي `{random.randint(1, 100)}%`")

@bot.tree.command(name="hack", description="اختراق وهمي ومرح لعضو")
async def f3(i, m: discord.Member): await i.response.defer(); await i.followup.send(f"💉 جاري سحب بيانات {m.name}... تم الاختراق بنجاح!")

@bot.tree.command(name="kill", description="تصفية عضو (وهمياً)")
async def f4(i, m: discord.Member): await i.response.defer(); await i.followup.send(f"⚔️ قمت بتصفية {m.name} بضربة قاضية!")

@bot.tree.command(name="slap", description="توجيه صفعة قوية")
async def f5(i, m: discord.Member): await i.response.defer(); await i.followup.send(f"🖐️ صقعت {m.name} كف طير عيونه!")

@bot.tree.command(name="hug", description="إرسال حضن لعضو")
async def f6(i, m: discord.Member): await i.response.defer(); await i.followup.send(f"🤗 حضنت {m.name} بكل مودة")

@bot.tree.command(name="joke", description="إلقاء نكتة عشوائية")
async def f7(i): await i.response.defer(); await i.followup.send("🤣 واحد راح مطعم يطلب كباب، قاله الكباب خلص، قاله خلاص عطني صورته")

@bot.tree.command(name="dice", description="رمي حجر النرد")
async def f8(i): await i.response.defer(); await i.followup.send(f"🎲 النتيجة هي: `{random.randint(1, 6)}`")

@bot.tree.command(name="avatar", description="عرض الصورة الشخصية")
async def f9(i, m: discord.Member=None): await i.response.defer(); m=m or i.user; await i.followup.send(m.avatar.url)

@bot.tree.command(name="user-info", description="معلومات حسابك بالتفصيل")
async def f10(i, m: discord.Member=None): await i.response.defer(); m=m or i.user; await i.followup.send(f"👤 الاسم: {m.name}\n🆔 الأيدي: {m.id}")

@bot.tree.command(name="bot-stats", description="إحصائيات البوت الحالية")
async def f11(i): await i.response.defer(); await i.followup.send(f"🤖 أعمل في {len(bot.guilds)} سيرفر حالياً")

@bot.tree.command(name="ping", description="قياس سرعة استجابة البوت")
async def f12(i): await i.response.defer(); await i.followup.send(f"🏓 البينج: `{round(bot.latency*1000)}ms`")

@bot.tree.command(name="show-level", description="عرض لفلك في هذا السيرفر")
async def f13(i, m: discord.Member=None):
    await i.response.defer(); m=m or i.user; db=load_db(); gd=get_guild(db, i.guild.id); u=gd["lvls"].get(str(m.id), {"lvl": 1})
    await i.followup.send(f"📊 لفل **{m.name}**: `{u['lvl']}`")

@bot.tree.command(name="show-xp", description="عرض نقاط الخبرة (XP)")
async def f14(i, m: discord.Member=None):
    await i.response.defer(); m=m or i.user; db=load_db(); gd=get_guild(db, i.guild.id); u=gd["lvls"].get(str(m.id), {"xp": 0})
    await i.followup.send(f"✨ نقاط خبرة **{m.name}**: `{u['xp']}`")

@bot.tree.command(name="choose", description="البوت يختار لك بين شيئين")
async def f15(i, a: str, b: str): await i.response.defer(); await i.followup.send(f"🤔 أنا أختار: `{random.choice([a, b])}`")

@bot.tree.command(name="laugh", description="ضحك بصوت عالٍ")
async def f16(i): await i.response.defer(); await i.followup.send("😄 ههههههههههههههههههههه!")

@bot.tree.command(name="cry", description="التعبير عن الحزن")
async def f17(i): await i.response.defer(); await i.followup.send("😭 أهئ أهئ.. حزين جداً")

@bot.tree.command(name="angry", description="التعبير عن الغضب")
async def f18(i): await i.response.defer(); await i.followup.send("💢 أنا معصب الحين، لا حد يكلمني!")

@bot.tree.command(name="sleep", description="البوت يذهب للنوم")
async def f19(i): await i.response.defer(); await i.followup.send("💤 تصبحون على خير، بروح أنام")

@bot.tree.command(name="meme", description="طلب ميمز عشوائي")
async def f20(i): await i.response.defer(); await i.followup.send("🖼️ خذ هذا الميم الرهيب!")

@bot.tree.command(name="game", description="اقتراح لعبة تلعبها")
async def f21(i): await i.response.defer(); await i.followup.send("🎮 أقترح عليك تلعب **Roblox** أو **GTA IV**")

@bot.tree.command(name="ship", description="نسبة التوافق بين عضوين")
async def f22(i, m1: discord.Member, m2: discord.Member): await i.response.defer(); await i.followup.send(f"💞 نسبة التوافق بينهما هي `{random.randint(1, 100)}%`")

@bot.tree.command(name="wanted", description="وضع صورة مطلوب للعدالة")
async def f23(i, m: discord.Member=None): await i.response.defer(); await i.followup.send("⚖️ العضو مطلوب حياً أو ميتاً بجائزة 10 آلاف!")

@bot.tree.command(name="scary", description="إرسال رسالة مخيفة")
async def f24(i): await i.response.defer(); await i.followup.send("😱 سمعت صوت خلفك؟ بووووو!")

@bot.tree.command(name="punch", description="توجيه لكمة")
async def f25(i, m: discord.Member): await i.response.defer(); await i.followup.send(f"👊 بوكس في نص وجه {m.name}!")

bot.run(os.getenv("DISCORD_TOKEN"))
