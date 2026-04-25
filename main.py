import discord
from discord import app_commands
from discord.ui import Button, View
import random, asyncio, json, os, re
from datetime import datetime, timedelta

# --- 1. قاعدة البيانات (اقتصاد عالمي + نظام سيرفرات للفل والإدارة) ---
def load_db():
    if not os.path.exists("op_bot_db.json"):
        with open("op_bot_db.json", "w", encoding="utf-8") as f:
            json.dump({"global_bank": {}, "guilds": {}}, f)
    with open("op_bot_db.json", "r", encoding="utf-8") as f: return json.load(f)

def save_db(data):
    with open("op_bot_db.json", "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

# لجلب الكريدت العالمي
def get_global_user(db, uid):
    u = str(uid)
    if u not in db["global_bank"]: db["global_bank"][u] = {"w": 0}
    return db["global_bank"][u]

# لجلب إعدادات السيرفر (بما فيها اللفل الخاص بالسيرفر)
def get_guild_data(db, gid):
    g = str(gid)
    if g not in db["guilds"]:
        db["guilds"][g] = {
            "wel_ch": None, "role_id": None, "event_ch": None, 
            "anti_link": False, "replies": {}, "levels": {} # اللفل صار داخل السيرفر هنا
        }
    return db["guilds"][g]

def get_user_guild_stats(g_data, uid):
    u = str(uid)
    if u not in g_data["levels"]: g_data["levels"][u] = {"xp": 0, "lvl": 1}
    return g_data["levels"][u]

# --- 2. نظام التيكت ---
class TicketActions(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.claimed_by = None 

    @discord.ui.button(label="استلام التذكرة ✋", style=discord.ButtonStyle.blurple, custom_id="claim_t")
    async def claim(self, i: discord.Interaction, b: discord.ui.Button):
        if not i.user.guild_permissions.administrator: return await i.response.send_message("❌ للإدارة فقط!", ephemeral=True)
        self.claimed_by = i.user.id
        b.disabled = True; b.label = f"مستلمة بواسطة {i.user.name}"
        await i.channel.edit(name=f"claimed-{i.user.name}")
        await i.response.edit_message(view=self)

    @discord.ui.button(label="إغلاق 🔒", style=discord.ButtonStyle.red, custom_id="close_t")
    async def close(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_message("🔒 حذف خلال 5 ثوانٍ..."); await asyncio.sleep(5); await i.channel.delete()

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة دعم 📩", style=discord.ButtonStyle.green, custom_id="open_t")
    async def open_t(self, i: discord.Interaction, b: discord.ui.Button):
        overwrites = {i.guild.default_role: discord.PermissionOverwrite(view_channel=False), i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True), i.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        ch = await i.guild.create_text_channel(f"ticket-{i.user.name}", overwrites=overwrites)
        await ch.send(f"أهلاً {i.user.mention}، يرجى انتظار المستلم.", view=TicketActions())
        await i.response.send_message(f"✅ تم فتح تذكرتك: {ch.mention}", ephemeral=True)

# --- 3. البوت الأساسي ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)
        self.current_events = {}

    async def setup_hook(self):
        self.add_view(TicketView()); self.add_view(TicketActions())
        await self.tree.sync()
        self.loop.create_task(self.status_loop())
        self.loop.create_task(self.auto_event_loop())

    async def status_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"OP BOT | Servers: {len(self.guilds)}"))
            await asyncio.sleep(1800)

    async def auto_event_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(3600)
            db = load_db()
            for guild in self.guilds:
                g_data = get_guild_data(db, guild.id)
                if g_data["event_ch"]:
                    ch = self.get_channel(int(g_data["event_ch"]))
                    if ch:
                        n1, n2 = random.randint(1, 50), random.randint(1, 50)
                        self.current_events[guild.id] = str(n1 + n2)
                        await ch.send(f"@everyone 💡 **سؤال الفعالية:** `{n1} + {n2} = ?` | الجائزة: **1000**")

    async def on_member_join(self, member):
        db = load_db()
        g_data = get_guild_data(db, member.guild.id)
        if g_data["role_id"]:
            role = member.guild.get_role(int(g_data["role_id"]))
            if role: await member.add_roles(role)
        if g_data["wel_ch"]:
            ch = self.get_channel(int(g_data["wel_ch"]))
            if ch and ch.guild.id == member.guild.id:
                emb = discord.Embed(title="🎉 عضو جديد!", description=f"أهلاً {member.mention} في {member.guild.name}", color=0x3498db)
                await ch.send(embed=emb)

    async def on_message(self, msg):
        if msg.author.bot or not msg.guild: return
        db = load_db()
        
        # بيانات السيرفر (للفل والإدارة)
        g_data = get_guild_data(db, msg.guild.id)
        lvls = get_user_guild_stats(g_data, msg.author.id)
        
        # الكريدت (عالمي)
        user_bank = get_global_user(db, msg.author.id)

        # فعاليات
        if msg.guild.id in self.current_events and msg.channel.id == int(g_data.get("event_ch", 0)):
            if msg.content == self.current_events[msg.guild.id]:
                del self.current_events[msg.guild.id]
                user_bank["w"] += 1000; save_db(db)
                await msg.reply(f"✅ مبروك {msg.author.mention}! فزت بـ 1000 كريدت عالمي.")

        # نظام لفل (خاص بالسيرفر)
        lvls["xp"] += random.randint(5, 15)
        needed = lvls["lvl"] * 100
        if lvls["xp"] >= needed:
            lvls["lvl"] += 1; lvls["xp"] = 0
            await msg.channel.send(f"🎊 مبروك {msg.author.mention}! ارتفع لفلك في هذا السيرفر لـ **{lvls['lvl']}**")
        save_db(db)

bot = OPBot()

# --- 4. فئة الإدارة (25 أمر) ---
@bot.tree.command(name="show-level", description="اظهار مستواك")
async def show_level(i, m: discord.Member = None):
    m = m or i.user; db = load_db(); _, l = get_acc(db, m.id)
    await i.response.send_message(f"📊 لفل **{m.name}** الحالي هو: `{l['lvl']}`")

@bot.tree.command(name="show-xp", description="يوريك نقاط الخبرة (XP) حقك")
async def show_xp(i, m: discord.Member = None):
    m = m or i.user; db = load_db(); _, l = get_acc(db, m.id)
    needed = l['lvl'] * 100
    await i.response.send_message(f"✨ نقاط خبرة **{m.name}**: `{l['xp']}/{needed}` XP")


@bot.tree.command(name="ban", description="حظر عضو + إرسال خاص")
async def adm1(i, m: discord.Member, r: str="غير محدد"):
    try: await m.send(f"⚠️ تم حظرك من **{i.guild.name}** | السبب: {r}")
    except: pass
    await m.ban(reason=r); await i.response.send_message(f"✅ تم حظر {m.name}")

@bot.tree.command(name="kick", description="طرد عضو + إرسال خاص")
async def adm2(i, m: discord.Member, r: str="غير محدد"):
    try: await m.send(f"⚠️ تم طردك من **{i.guild.name}** | السبب: {r}")
    except: pass
    await m.kick(reason=r); await i.response.send_message(f"✅ تم طرد {m.name}")

@bot.tree.command(name="timeout", description="إسكات عضو + إرسال خاص")
async def adm3(i, m: discord.Member, t: int, r: str="غير محدد"):
    await m.timeout(timedelta(minutes=t), reason=r)
    try: await m.send(f"🔇 تم إسكاتك في **{i.guild.name}** لـ {t} دقيقة | السبب: {r}")
    except: pass
    await i.response.send_message(f"✅ تم إسكات {m.name}")

@bot.tree.command(name="warn", description="تحذير عضو في الخاص")
async def adm4(i, m: discord.Member, r: str):
    try: await m.send(f"⚠️ تحذير جديد في **{i.guild.name}** | السبب: {r}")
    except: pass
    await i.response.send_message(f"✅ تم تحذير {m.name}")

@bot.tree.command(name="clear", description="مسح الرسائل")
async def adm5(i, a: int): await i.channel.purge(limit=a); await i.response.send_message(f"🧹 تم مسح {a} رسالة", ephemeral=True)

@bot.tree.command(name="lock", description="قفل الشات")
async def adm6(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 تم قفل الشات")

@bot.tree.command(name="unlock", description="فتح الشات")
async def adm7(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 تم فتح الشات")

@bot.tree.command(name="nuke", description="تطهير الروم")
async def adm8(i): cl = await i.channel.clone(); await i.channel.delete(); await cl.send("✅ تم التطهير")

@bot.tree.command(name="hide", description="إخفاء الروم")
async def adm9(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻 مخفي")

@bot.tree.command(name="unhide", description="إظهار الروم")
async def adm10(i): await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️ ظاهر")

@bot.tree.command(name="anti-link", description="تفعيل مانع الروابط")
async def adm11(i): db=load_db(); db["anti_link"]=True; save_db(db); await i.response.send_message("🔗 تم التفعيل")

@bot.tree.command(name="remove-antilink", description="تعطيل مانع الروابط")
async def adm12(i): db=load_db(); db["anti_link"]=False; save_db(db); await i.response.send_message("🔓 تم التعطيل")

@bot.tree.command(name="set-ticket", description="تركيب نظام التيكت مع عنوان مخصص")
async def sticket(i, ch: discord.TextChannel, title: str):
    emb = discord.Embed(title=title, description="اضغط على الزر أدناه لفتح تذكرة تواصل مع الإدارة.", color=discord.Color.blue())
    await ch.send(embed=emb, view=TicketView())
    await i.response.send_message(f"✅ تم تركيب التيكت في {ch.mention} بعنوان: **{title}**")
    
@bot.tree.command(name="set-welcome", description="تحديد روم الترحيب")
async def swel(i, ch: discord.TextChannel):
    db = load_db(); g_data = get_guild_data(db, i.guild.id)
    g_data["wel_ch"] = str(ch.id); save_db(db)
    await i.response.send_message(f"✅ تم تحديد {ch.mention} للترحيب هنا.")
    
@bot.tree.command(name="set-autorole", description="رتبة تلقائية")
async def adm14(i, r: discord.Role): db=load_db(); db["role_id"]=str(r.id); save_db(db); await i.response.send_message("✅ تم")

@bot.tree.command(name="set-autoreply", description="إضافة رد")
async def adm15(i, word: str, reply: str): 
    db=load_db(); g_data=get_guild_data(db, i.guild.id)
    g_data["replies"][word]=reply; save_db(db)
    await i.response.send_message("📝 تم إضافة الرد التلقائي")

@bot.tree.command(name="del-autoreply", description="حذف رد")
async def adm16(i, word: str): 
    db=load_db(); g_data=get_guild_data(db, i.guild.id)
    g_data["replies"].pop(word, None); save_db(db)
    await i.response.send_message("🗑️ تم حذف الرد")

@bot.tree.command(name="set-autoevent", description="تحديد روم فاعليات")
async def sevent(i, ch: discord.TextChannel):
    db=load_db(); g_data=get_guild_data(db, i.guild.id)
    g_data["event_ch"]=str(ch.id); save_db(db)
    await i.response.send_message(f"✅ تم التفعيل في {ch.mention} وسيبدأ أول سؤال الآن.")
    await bot.send_event_math(i.guild.id, ch) 
    
@bot.tree.command(name="slowmode", description="وضع البطء")
async def adm17(i, s: int): 
    await i.channel.edit(slowmode_delay=s)
    await i.response.send_message(f"🐢 تم وضع البطء: {s} ثانية")
@bot.tree.command(name="nick", description="تغيير لقب")
async def adm18(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("✏️ تم")

@bot.tree.command(name="role-add", description="إعطاء رتبة")
async def adm19(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message("✅ تم")

@bot.tree.command(name="role-remove", description="سحب رتبة")
async def adm20(i, m: discord.Member, r: discord.Role): await m.remove_roles(r); await i.response.send_message("❌ تم")

@bot.tree.command(name="vmute", description="كتم صوتي")
async def adm22(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🔇 تم")

@bot.tree.command(name="vunmute", description="فك كتم")
async def adm23(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🔊 تم")

@bot.tree.command(name="set-name", description="اسم السيرفر")
async def adm25(i, n: str): await i.guild.edit(name=n); await i.response.send_message("🏰 تم")

# --- 5. أوامر الاقتصاد (20 أمراً) ---
@bot.tree.command(name="credits", description="اظهار الرصيد")
async def credits(i, m: discord.Member=None):
    m = m or i.user; db = load_db(); u = get_global_user(db, m.id)
    await i.response.send_message(f"💳 رصيد {m.name} العالمي: `{u['w']}`")

@bot.tree.command(name="transfer", description="تحويل كريدت مع إيصال")
async def eco2(i, m: discord.Member, a: int):
    db=load_db(); u, _ = get_acc(db, i.user.id); t, _ = get_acc(db, m.id)
    if u["w"] < a or a <= 0: return await i.response.send_message("❌ رصيدك لا يكفي")
    u["w"]-=a; t["w"]+=a; save_db(db)
    try: await m.send(f"🏪 استلمت `{a}` من {i.user.name} في {i.guild.name}")
    except: pass
    await i.response.send_message(f"✅ تم تحويل {a} لـ {m.name}")

@bot.tree.command(name="daily", description="راتب يومي")
async def eco3(i): db=load_db(); u, _ = get_acc(db, i.user.id); u["w"]+=1000; save_db(db); await i.response.send_message("💰 +1000")

@bot.tree.command(name="work", description="العمل لكسب المال")
async def eco4(i): r=random.randint(100,600); db=load_db(); u,_=get_acc(db, i.user.id); u["w"]+=r; save_db(db); await i.response.send_message(f"💼 عملت وحصلت على {r}")

@bot.tree.command(name="top", description="أغنى 10 بالسيرفر")
async def eco5(i):
    db=load_db(); s=sorted(db["bank"].items(), key=lambda x:x[1]['w'], reverse=True)[:10]
    t="\n".join([f"#{idx+1} | <@{u}>: `{d['w']}`" for idx,(u,d) in enumerate(s)])
    await i.response.send_message(embed=discord.Embed(title="🏆 قائمة الأغنياء", description=t))

@bot.tree.command(name="fish", description="صيد سمك")
async def eco6(i): r=random.randint(50,200); db=load_db(); u,_=get_acc(db, i.user.id); u["w"]+=r; save_db(db); await i.response.send_message(f"🎣 اصطدت بـ {r}")

@bot.tree.command(name="hunt", description="صيد حيوانات")
async def eco7(i): r=random.randint(100,300); db=load_db(); u,_=get_acc(db, i.user.id); u["w"]+=r; save_db(db); await i.response.send_message(f"🏹 قنصت بـ {r}")

@bot.tree.command(name="slots", description="آلة الحظ")
async def eco8(i, a: int):
    db=load_db(); u,_=get_acc(db, i.user.id)
    if u["w"] < a: return await i.response.send_message("❌")
    if random.random() > 0.7: u["w"]+=a*2; await i.response.send_message("🎰 فزت!")
    else: u["w"]-=a; await i.response.send_message("🎰 خسرت")
    save_db(db)

@bot.tree.command(name="roulette", description="روليت")
async def eco9(i, a: int):
    db=load_db(); u,_=get_acc(db, i.user.id)
    if u["w"] < a: return await i.response.send_message("❌")
    if random.choice([True, False]): u["w"]+=a; await i.response.send_message("🎉 فوز")
    else: u["w"]-=a; await i.response.send_message("💀 خسارة")
    save_db(db)

@bot.tree.command(name="coinflip", description="عملة")
async def eco10(i, a: int): 
    db=load_db(); u,_=get_acc(db, i.user.id)
    if u["w"] < a: return await i.response.send_message("❌")
    u["w"] += a if random.random() > 0.5 else -a; save_db(db); await i.response.send_message("🪙")

@bot.tree.command(name="rob", description="سرقة")
async def eco11(i, m: discord.Member): await i.response.send_message(f"👮 مسكتك الشرطة وانت تحاول تسرق {m.name}")

@bot.tree.command(name="beg", description="شحاتة")
async def eco14(i): r=random.randint(1,50); db=load_db(); u,_=get_acc(db, i.user.id); u["w"]+=r; save_db(db); await i.response.send_message(f"🤲 أعطاك فاعل خير {r}")

@bot.tree.command(name="miner", description="تعدين")
async def eco15(i): r=random.randint(200,500); db=load_db(); u,_=get_acc(db, i.user.id); u["w"]+=r; save_db(db); await i.response.send_message(f"⛏️ عدنت بـ {r}")

@bot.tree.command(name="farm", description="مزرعة")
async def eco16(i): await i.response.send_message("🚜 حصدت محصولك!")

@bot.tree.command(name="rich-role", description="رتبة الأغنياء")
async def eco19(i): await i.response.send_message("💎 قريباً...")

# --- 6. أوامر الترفيه (15 أمراً) ---
@bot.tree.command(name="iq", description="نسبة ذكاء")
async def f1(i): await i.response.send_message(f"🧠 نسبة ذكائك: {random.randint(40,160)}%")

@bot.tree.command(name="love", description="نسبة حب")
async def f2(i, m: discord.Member): await i.response.send_message(f"❤️ نسبة الحب بينك وبين {m.name}: {random.randint(0,100)}%")

@bot.tree.command(name="hack", description="اختراق")
async def f3(i, m: discord.Member): await i.response.send_message(f"💉 جاري سحب بيانات {m.name}... تم الاختراق بنجاح! 💀")

@bot.tree.command(name="slap", description="صفعة")
async def f4(i, m: discord.Member): await i.response.send_message(f"🖐️ {i.user.name} صفع {m.mention}!")

@bot.tree.command(name="kill", description="قتل")
async def f5(i, m: discord.Member): await i.response.send_message(f"⚔️ {i.user.name} قتل {m.mention}!")

@bot.tree.command(name="joke", description="نكتة")
async def f6(i): await i.response.send_message("🤣 واحد خبل راح للمستشفى...")

@bot.tree.command(name="dice", description="نرد")
async def f7(i): await i.response.send_message(f"🎲 النرد طلع: {random.randint(1,6)}")

@bot.tree.command(name="hug", description="حضن")
async def f8(i, m: discord.Member): await i.response.send_message(f"🤗 حضنت {m.mention}")

@bot.tree.command(name="punch", description="لكمة")
async def f9(i, m: discord.Member): await i.response.send_message(f"👊 لكمت {m.mention}")

@bot.tree.command(name="choose", description="اختيار")
async def f10(i, a: str, b: str): await i.response.send_message(f"🤔 اخترت لك: {random.choice([a,b])}")

@bot.tree.command(name="dance", description="رقصة")
async def f11(i): await i.response.send_message("💃🕺")

@bot.tree.command(name="wanted", description="مطلوب للعدالة")
async def f12(i, m: discord.Member=None): m=m or i.user; await i.response.send_message(f"⚠️ {m.name} مطلوب للعدالة وجائزته مليون!")

@bot.tree.command(name="ship", description="تطقيم")
async def f13(i, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 {m1.name} + {m2.name} = ❤️")

@bot.tree.command(name="meme", description="ميم")
async def f14(i): await i.response.send_message("🖼️ ميم مضحك!")

@bot.tree.command(name="game", description="لعبة عشوائية")
async def f15(i): await i.response.send_message("🎮 العب روبلوكس!")

# --- 7. فئة النظام واللفل ---
@bot.tree.command(name="rank", description="مستواك")
async def rank(i, m: discord.Member=None):
    m=m or i.user; db=load_db(); _, l = get_acc(db, m.id)
    await i.response.send_message(f"📊 **{m.name}** | اللفل: `{l['lvl']}` | XP: `{l['xp']}/{l['lvl']*100}`")

@bot.tree.command(name="ping", description="سرعة البوت")
async def ping(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")

# --- 8. أمر المساعدة ---
@bot.tree.command(name="help", description="عرض جميع فئات الأوامر")
async def help(i):
    emb = discord.Embed(title="📜 قائمة أوامر OP BOT", color=discord.Color.green())
    emb.add_field(name="🛡️ الإدارة", value="`ban`, `kick`, `timeout`, `clear`, `set-welcome`, `set-ticket`, `set-autoevent`, `set-autorole`", inline=False)
    emb.add_field(name="💰 الاقتصاد", value="`credits`, `transfer`, `daily`, `work`, `top`, `fish`, `hunt`, `slots`, `roulette`, `beg`", inline=False)
    emb.add_field(name="🎉 الترفيه", value="`iq`, `love`, `hack`, `slap`, `kill`, `joke`, `dice`, `choose`, `dance`", inline=False)
    emb.add_field(name="⚙️ النظام واللفل", value="`show-level`, `show-xp`, `rank`, `ping`, `avatar`, `id`, `stats`", inline=False)
    await i.response.send_message(embed=emb)
    
bot.run(os.getenv("DISCORD_TOKEN"))
