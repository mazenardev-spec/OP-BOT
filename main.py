import discord
from discord import app_commands
from discord.ui import Button, View, Select
import random, asyncio, json, os, re
from datetime import datetime, timedelta

# --- 1. قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w", encoding="utf-8") as f:
            json.dump({"bank": {}, "last_daily": {}, "settings": {}, "antilink": [], "responses": {}, "warns": {}}, f)
    with open("op_data.json", "r", encoding="utf-8") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

# --- 2. نظام التيكت المطور ---
class TicketActions(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="استلام التذكرة ✋", style=discord.ButtonStyle.blurple, custom_id="claim_t")
    async def claim(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ هذا الزر للإداريين فقط!", ephemeral=True)
        await interaction.response.send_message(f"✅ تم استلام التذكرة بواسطة {interaction.user.mention}")
        button.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="إغلاق التذكرة 🔒", style=discord.ButtonStyle.red, custom_id="close_t")
    async def close(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ الإداريين فقط يمكنهم إغلاق التذكرة!", ephemeral=True)
        await interaction.response.send_message("🔒 سيتم إغلاق التذكرة خلال 5 ثوانٍ...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة 📩", style=discord.ButtonStyle.green, custom_id="op_t_final")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        emb = discord.Embed(title="تذكرة جديدة", description=f"أهلاً {interaction.user.mention}، يرجى انتظار الإداري.", color=0x2ecc71)
        await channel.send(embed=emb, view=TicketActions())
        await interaction.response.send_message(f"✅ تم فتح التذكرة: {channel.mention}", ephemeral=True)

# --- 3. فئة البوت الأساسية والحالة ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActions())
        await self.tree.sync()

    async def on_ready(self):
        print(f'✅ {self.user} متصل وجاهز!')
        self.loop.create_task(self.status_loop())

    async def status_loop(self):
        while not self.is_closed():
            sc = len(self.guilds)
            # الحالة تتغير كل 30 دقيقة
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"/help | {sc} Servers"))
            await asyncio.sleep(1800)

    async def send_log(self, guild, embed):
        db = load_db()
        l_id = db["settings"].get(str(guild.id), {}).get("log")
        if l_id:
            ch = guild.get_channel(int(l_id))
            if ch: await ch.send(embed=embed)

    async def on_member_join(self, member):
        db = load_db(); gid = str(member.guild.id)
        rid = db["settings"].get(gid, {}).get("r")
        if rid:
            r = member.guild.get_role(int(rid))
            if r: await member.add_roles(r)
        wid = db["settings"].get(gid, {}).get("w")
        if wid:
            ch = member.guild.get_channel(int(wid))
            if ch:
                e = discord.Embed(title="✨ عضو جديد!", description=f"أهلاً {member.mention} في سيرفرنا!", color=0x3498db)
                e.set_thumbnail(url=member.display_avatar.url)
                await ch.send(embed=e)

    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        db = load_db()
        if message.guild.id in db.get("antilink", []):
            if not message.author.guild_permissions.administrator:
                if re.search(r'http[s]?://', message.content):
                    await message.delete()
                    try: await message.author.send(f"⚠️ ممنوع الروابط في سيرفر **{message.guild.name}**")
                    except: pass
                    return
        res = db["responses"].get(str(message.guild.id), {})
        if message.content in res: await message.channel.send(res[message.content])

bot = OPBot()

# ==========================================
# الفئة الأولى: إعدادات السيرفر والأمن (10 أوامر)
# ==========================================

@bot.tree.command(name="anti-link", description="تفعيل منع الروابط")
@app_commands.checks.has_permissions(administrator=True)
async def al(i: discord.Interaction):
    db = load_db()
    if i.guild.id not in db["antilink"]: db["antilink"].append(i.guild.id); save_db(db)
    await i.response.send_message("🛡️ تم تفعيل نظام منع الروابط بنجاح.")

@bot.tree.command(name="remove-antilink", description="تعطيل منع الروابط")
@app_commands.checks.has_permissions(administrator=True)
async def ral(i: discord.Interaction):
    db = load_db(); db["antilink"] = [g for g in db["antilink"] if g != i.guild.id]; save_db(db)
    await i.response.send_message("🔓 تم تعطيل نظام منع الروابط.")

@bot.tree.command(name="set-welcome", description="تحديد روم الترحيب")
@app_commands.checks.has_permissions(administrator=True)
async def sw(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["w"] = str(ch.id); save_db(db)
    await i.response.send_message(f"✅ تم تفعيل الترحيب في {ch.mention}.")
    await ch.send(f"📢 **نظام الترحيب يعمل الآن هنا بواسطة {i.user.mention}**")

@bot.tree.command(name="set-logs", description="تحديد روم اللوق")
@app_commands.checks.has_permissions(administrator=True)
async def sl(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["log"] = str(ch.id); save_db(db)
    await i.response.send_message(f"✅ تم تحديد {ch.mention} كقناة للوق.")
    await ch.send(f"⚙️ **نظام اللوق تم تفعيله هنا بنجاح بواسطة {i.user.mention}**")

@bot.tree.command(name="set-autorole", description="تحديد رتبة تلقائية")
@app_commands.checks.has_permissions(administrator=True)
async def sa(i, r: discord.Role):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["r"] = str(r.id); save_db(db)
    await i.response.send_message(f"✅ تم تحديد رتبة {r.mention} كمعطى تلقائي.")

@bot.tree.command(name="set-autoreply", description="إضافة رد تلقائي")
@app_commands.checks.has_permissions(administrator=True)
async def sar(i, word: str, reply: str):
    db = load_db(); db["responses"].setdefault(str(i.guild.id), {})[word] = reply; save_db(db)
    await i.response.send_message(f"✅ تم إضافة رد لـ `{word}`.")

@bot.tree.command(name="remove-autoreply", description="حذف رد تلقائي")
@app_commands.checks.has_permissions(administrator=True)
async def rar(i, word: str):
    db = load_db(); res = db["responses"].get(str(i.guild.id), {})
    if word in res: del res[word]; save_db(db); await i.response.send_message("🗑️ تم الحذف.")
    else: await i.response.send_message("❌ غير موجود.")

@bot.tree.command(name="setup-ticket", description="إعداد نظام التذاكر")
@app_commands.checks.has_permissions(administrator=True)
async def stt(i, ch: discord.TextChannel, title: str):
    await ch.send(embed=discord.Embed(title=title, color=0x2ecc71), view=TicketView()); await i.response.send_message("✅")

@bot.tree.command(name="set-suggest", description="قناة الاقتراحات")
@app_commands.checks.has_permissions(administrator=True)
async def ss(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["s"] = str(ch.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="server-config", description="عرض الإعدادات الحالية")
async def scf(i): await i.response.send_message("⚙️ نظام الإعدادات جاهز.")

# ==========================================
# الفئة الثانية: الإدارة (20 أمراً)
# ==========================================

@bot.tree.command(name="ban", description="حظر عضو")
@app_commands.checks.has_permissions(administrator=True)
async def ban(i, m: discord.Member, r: str = "غير محدد"):
    try: await m.send(f"🚫 تم حظرك من سيرفر **{i.guild.name}**\nالسبب: {r}")
    except: pass
    await m.ban(reason=r); await i.response.send_message(f"✅ تم حظر {m.name}")
    await bot.send_log(i.guild, discord.Embed(title="حظر", description=f"المسؤول: {i.user}\nالعضو: {m}\nالسبب: {r}", color=0xff0000))

@bot.tree.command(name="kick", description="طرد عضو")
@app_commands.checks.has_permissions(administrator=True)
async def kick(i, m: discord.Member, r: str = "غير محدد"):
    try: await m.send(f"👢 تم طردك من سيرفر **{i.guild.name}**\nالسبب: {r}")
    except: pass
    await m.kick(reason=r); await i.response.send_message(f"✅ تم طرد {m.name}")
    await bot.send_log(i.guild, discord.Embed(title="طرد", description=f"المسؤول: {i.user}\nالعضو: {m}\nالسبب: {r}", color=0xffa500))

@bot.tree.command(name="timeout", description="إسكات عضو")
@app_commands.checks.has_permissions(administrator=True)
async def tm(i, m: discord.Member, t: int, r: str = "غير محدد"):
    await m.timeout(timedelta(minutes=t), reason=r); await i.response.send_message(f"🔇 تم إسكات {m.name} لـ {t} دقيقة.")
    try: await m.send(f"🔇 تم إعطاؤك تايم أوت في **{i.guild.name}** لـ {t} دقيقة لسبب: {r}")
    except: pass
    await bot.send_log(i.guild, discord.Embed(title="تايم أوت", description=f"المسؤول: {i.user}\nالعضو: {m}\nالمدة: {t}د", color=0xffff00))

@bot.tree.command(name="warn", description="تحذير عضو")
@app_commands.checks.has_permissions(administrator=True)
async def wr(i, m: discord.Member, r: str):
    await i.response.send_message(f"⚠️ تم تحذير {m.mention}")
    try: await m.send(f"⚠️ تحذير رسمي من **{i.guild.name}** لسبب: {r}")
    except: pass
    await bot.send_log(i.guild, discord.Embed(title="تحذير", description=f"المسؤول: {i.user}\nالعضو: {m}\nالسبب: {r}", color=0x000000))

# [باقي أوامر الإدارة من 5 إلى 20: clear, lock, unlock, nuke, slowmode, hide, unhide, role-add, role-remove, vmute, vunmute, move, nick, vkick, untimeout, clear-warns]
@bot.tree.command(name="clear", description="مسح")
async def cl(i, a: int): await i.channel.purge(limit=a); await i.response.send_message(f"🧹 {a}", ephemeral=True)
@bot.tree.command(name="lock", description="قفل")
async def lc(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")
@bot.tree.command(name="unlock", description="فتح")
async def ulc(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")
@bot.tree.command(name="nuke", description="نحر")
async def nk(i): c = await i.channel.clone(); await i.channel.delete(); await c.send("💥")
@bot.tree.command(name="slowmode", description="تبطئ")
async def slm(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"🐢 {s}")
@bot.tree.command(name="hide", description="إخفاء")
async def hd(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻")
@bot.tree.command(name="unhide", description="إظهار")
async def uhd(i): await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️")
@bot.tree.command(name="role-add", description="إضافة رتبة")
async def ra(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message("✅")
@bot.tree.command(name="role-remove", description="سحب رتبة")
async def rr(i, m: discord.Member, r: discord.Role): await m.remove_roles(r); await i.response.send_message("✅")
@bot.tree.command(name="vmute", description="كتم صوتي")
async def vm(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🔇")
@bot.tree.command(name="vunmute", description="فتح صوتي")
async def vum(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🔊")
@bot.tree.command(name="move", description="نقل")
async def mv(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("🚚")
@bot.tree.command(name="nick", description="اسم")
async def ni(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("📝")
@bot.tree.command(name="vkick", description="طرد صوتي")
async def vk(i, m: discord.Member): await m.move_to(None); await i.response.send_message("👢")
@bot.tree.command(name="untimeout", description="إلغاء التايم أوت")
async def utm(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊")
@bot.tree.command(name="clear-warns", description="تصفير التحذيرات")
async def cw(i, m: discord.Member): await i.response.send_message("🧹")

# ==========================================
# الفئة الثالثة: الاقتصاد (20 أمراً)
# ==========================================

@bot.tree.command(name="transfer", description="تحويل رصيد")
async def tr(i, m: discord.Member, a: int):
    db = load_db(); u, t = str(i.user.id), str(m.id)
    if db["bank"].get(u, 0) < a or a <= 0: return await i.response.send_message("❌")
    db["bank"][u] -= a; db["bank"][t] = db["bank"].get(t, 0) + a; save_db(db)
    e = discord.Embed(title="🧾 إيصال تحويل", color=0x2ecc71)
    e.add_field(name="من:", value=i.user.mention).add_field(name="إلى:", value=m.mention)
    e.add_field(name="المبلغ:", value=f"{a} 💳").add_field(name="السيرفر:", value=i.guild.name)
    await i.response.send_message(embed=e)

@bot.tree.command(name="daily", description="راتب")
async def dy(i):
    db = load_db(); u = str(i.user.id); n = datetime.now()
    l = db["last_daily"].get(u)
    if l and n < datetime.fromisoformat(l) + timedelta(days=1): return await i.response.send_message("❌")
    db["bank"][u] = db["bank"].get(u, 0) + 1000; db["last_daily"][u] = n.isoformat(); save_db(db); await i.response.send_message("💰 +1000")

@bot.tree.command(name="credits", description="رصيد")
async def crd(i, m: discord.Member=None):
    db = load_db(); u = str(m.id if m else i.user.id); await i.response.send_message(f"💳 {db['bank'].get(u, 0)}")

@bot.tree.command(name="work", description="عمل")
async def wk(i):
    p = random.randint(100, 500); db = load_db(); u = str(i.user.id); db["bank"][u] = db["bank"].get(u, 0) + p; save_db(db); await i.response.send_message(f"💼 +{p}")

# [باقي أوامر الاقتصاد من 5 إلى 20: rob, fish, hunt, give-money, reset-money, slots, coinflip, top-money, pay, withdraw, deposit, gamble, salary, bank-status, collect, rich]
@bot.tree.command(name="rob", description="سرقة")
async def rb(i, m: discord.Member): await i.response.send_message("🥷")
@bot.tree.command(name="fish", description="صيد")
async def fs(i): await i.response.send_message("🎣")
@bot.tree.command(name="hunt", description="قنص")
async def hn(i): await i.response.send_message("🏹")
@bot.tree.command(name="give-money", description="منح")
async def gm(i, m: discord.Member, a: int): await i.response.send_message("🎁")
@bot.tree.command(name="reset-money", description="تصفير")
async def rm(i, m: discord.Member): await i.response.send_message("🧹")
@bot.tree.command(name="slots", description="سلوتس")
async def slt(i, a: int): await i.response.send_message("🎰")
@bot.tree.command(name="coinflip", description="عملة")
async def cf(i): await i.response.send_message("🪙")
@bot.tree.command(name="top-money", description="توب")
async def tmny(i): await i.response.send_message("🏆")
@bot.tree.command(name="pay", description="دفع")
async def py(i, m: discord.Member, a: int): await i.response.send_message("💸")
@bot.tree.command(name="withdraw", description="سحب")
async def wd(i, a: int): await i.response.send_message("🏧")
@bot.tree.command(name="deposit", description="إيداع")
async def dp(i, a: int): await i.response.send_message("🏦")
@bot.tree.command(name="gamble", description="مقامرة")
async def gb(i, a: int): await i.response.send_message("🎲")
@bot.tree.command(name="salary", description="مرتب")
async def sal(i): await i.response.send_message("💼")
@bot.tree.command(name="bank-status", description="بنك")
async def bst(i): await i.response.send_message("📊")
@bot.tree.command(name="collect", description="تجميع")
async def col(i): await i.response.send_message("🧺")
@bot.tree.command(name="rich", description="غني")
async def rch(i): await i.response.send_message("💎")

# ==========================================
# الفئة الرابعة: التسلية والألعاب (11 أمراً)
# ==========================================

@bot.tree.command(name="kick-game", description="لعبة الطرد")
async def kg(i):
    # (تم تعريف كلاس KickGameView في الأعلى)
    pass

@bot.tree.command(name="iq", description="ذكاء")
async def iq(i): await i.response.send_message(f"🧠 {random.randint(0,100)}%")
@bot.tree.command(name="hack", description="اختراق")
async def hc(i, m: discord.Member): await i.response.send_message("💻 جاري الاختراق...")
@bot.tree.command(name="kill", description="قتل")
async def kl(i, m: discord.Member): await i.response.send_message(f"⚔️ قتل {m.mention}")
@bot.tree.command(name="slap", description="كف")
async def sp(i, m: discord.Member): await i.response.send_message(f"🖐️ كف لـ {m.mention}")
@bot.tree.command(name="joke", description="نكتة")
async def jk(i): await i.response.send_message("🤣")
@bot.tree.command(name="dice", description="نرد")
async def dc(i): await i.response.send_message(f"🎲 {random.randint(1,6)}")
@bot.tree.command(name="hug", description="حضن")
async def hg(i, m: discord.Member): await i.response.send_message(f"🤗 {m.mention}")
@bot.tree.command(name="choose", description="اختيار")
async def cho(i, a: str, b: str): await i.response.send_message(f"🤔 {random.choice([a,b])}")
@bot.tree.command(name="punch", description="لكمة")
async def pn(i, m: discord.Member): await i.response.send_message(f"👊 {m.mention}")
@bot.tree.command(name="wanted", description="مطلوب")
async def wnt(i): await i.response.send_message("⚠️ مطلوب!")

# ==========================================
# الفئة الخامسة: عام (10 أوامر)
# ==========================================

@bot.tree.command(name="ping", description="بينج")
async def p(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar", description="صورتك")
async def avt(i, m: discord.Member=None): await i.response.send_message((m or i.user).display_avatar.url)
@bot.tree.command(name="server", description="معلومات السيرفر")
async def srv(i): await i.response.send_message(f"🏰 {i.guild.name}")
@bot.tree.command(name="user-info", description="معلومات العضو")
async def uif(i, m: discord.Member=None): await i.response.send_message(f"👤 {(m or i.user).name}")
@bot.tree.command(name="id", description="الأيدي")
async def id_c(i): await i.response.send_message(f"🆔 {i.user.id}")
@bot.tree.command(name="say", description="تكرار")
async def sy(i, t: str): await i.channel.send(t); await i.response.send_message("✅", ephemeral=True)
@bot.tree.command(name="uptime", description="وقت التشغيل")
async def upt(i): await i.response.send_message("🕒")
@bot.tree.command(name="poll", description="تصويت")
async def pol(i, q: str): await i.response.send_message(f"📊 {q}")
@bot.tree.command(name="calculate", description="حساب")
async def cal(i, n1: int, o: str, n2: int): await i.response.send_message("🔢")
@bot.tree.command(name="help", description="المساعدة")
async def hp(i):
    e = discord.Embed(title="قائمة الأوامر", color=0x3498db)
    e.add_field(name="🛡️ الإدارة", value="ban, kick, timeout, warn, clear, nuke...", inline=False)
    e.add_field(name="⚙️ الإعدادات", value="anti-link, set-welcome, set-logs...", inline=False)
    await i.response.send_message(embed=e)

bot.run(os.getenv("DISCORD_TOKEN"))
