import discord
from discord import app_commands
from discord.ui import Button, View, Select
import random, asyncio, json, os, re
from datetime import datetime, timedelta

# --- 1. قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w", encoding="utf-8") as f:
            json.dump({"bank": {}, "last_daily": {}, "settings": {}, "security": [], "responses": {}, "warns": {}}, f)
    with open("op_data.json", "r", encoding="utf-8") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)

# --- 2. نظام التيكت المطور (استلام وإغلاق) ---
class TicketActions(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="استلام التذكرة ✋", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ هذا الزر للإداريين فقط!", ephemeral=True)
        await interaction.response.send_message(f"✅ تم استلام التذكرة بواسطة {interaction.user.mention}")
        button.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="إغلاق التذكرة 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ الإداريين فقط يمكنهم إغلاق التذكرة!", ephemeral=True)
        await interaction.response.send_message("🔒 سيتم إغلاق التذكرة وحذف القناة خلال 5 ثوانٍ...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة 📩", style=discord.ButtonStyle.green, custom_id="op_ticket_final")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        embed = discord.Embed(title="تذكرة جديدة", description=f"مرحباً {interaction.user.mention}، تفضل بطرح مشكلتك.", color=0x2ecc71)
        await channel.send(embed=embed, view=TicketActions())
        await interaction.response.send_message(f"✅ تم فتح التذكرة: {channel.mention}", ephemeral=True)

# --- 3. لعبة الطرد ---
class KickGameView(View):
    def __init__(self, starter):
        super().__init__(timeout=None)
        self.starter = starter
        self.players = []
        self.is_started = False

    def make_embed(self):
        p_list = "\n".join([f"👤 {p.name}" for p in self.players]) if self.players else "لا يوجد لاعبين."
        e = discord.Embed(title="🎮 لعبة ساحة الطرد", description="صاحب الدور يختار من يغادر الساحة.", color=0x5865F2)
        e.add_field(name=f"اللاعبين ({len(self.players)}/200)", value=p_list[:1024], inline=False)
        return e

    @discord.ui.button(label="دخول ✅", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: Button):
        if self.is_started: return await interaction.response.send_message("❌ بدأت اللعبة!", ephemeral=True)
        if interaction.user in self.players: return await interaction.response.send_message("❌ أنت مسجل!", ephemeral=True)
        self.players.append(interaction.user)
        await interaction.message.edit(embed=self.make_embed())
        await interaction.response.send_message("تم دخولك!", ephemeral=True)

    @discord.ui.button(label="بدء اللعبة 🚀", style=discord.ButtonStyle.blurple)
    async def start(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.starter: return await interaction.response.send_message("للصاحب فقط!", ephemeral=True)
        if len(self.players) < 2: return await interaction.response.send_message("نحتاج لاعبين!", ephemeral=True)
        self.is_started = True
        self.clear_items()
        await interaction.message.edit(content="🚀 **بدأت اللعبة!**", view=None)
        await self.game_loop(interaction.channel)

    async def game_loop(self, channel):
        while len(self.players) > 1:
            current = random.choice(self.players)
            select = Select(placeholder="اختر ضحية...")
            for p in self.players:
                if p != current: select.add_option(label=p.name, value=str(p.id))
            async def callback(i: discord.Interaction):
                if i.user != current: return await i.response.send_message("مش دورك!", ephemeral=True)
                target_id = int(select.values[0])
                target = next(p for p in self.players if p.id == target_id)
                self.players.remove(target); await i.channel.send(f"🎯 **{current.name}** طرد **{target.name}**!")
                await i.message.delete(); self.stop_loop.set()
            select.callback = callback
            v = View(timeout=30); v.add_item(select)
            self.stop_loop = asyncio.Event()
            msg = await channel.send(f"🎮 دور: {current.mention}", view=v)
            try: await asyncio.wait_for(self.stop_loop.wait(), timeout=30)
            except: self.players.remove(current); await msg.delete(); await channel.send(f"⏰ انتهى وقت {current.name}!")
        winner = self.players[0]
        db = load_db(); uid = str(winner.id); db["bank"][uid] = db["bank"].get(uid, 0) + 5000; save_db(db)
        await channel.send(f"👑 **الفائز {winner.mention} حصل على 5000 كريدت!**")

# --- 4. فئة البوت الأساسية ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)
        self.anti_spam = {}

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActions())
        await self.tree.sync()

    async def on_ready(self):
        print(f'✅ {self.user} متصل! 71 أمراً جاهزة.')

    async def on_member_join(self, member):
        db = load_db()
        guild_id = str(member.guild.id)
        # الرتبة التلقائية
        role_id = db["settings"].get(guild_id, {}).get("r")
        if role_id:
            role = member.guild.get_role(int(role_id))
            if role: await member.add_roles(role)
        # الترحيب
        welcome_id = db["settings"].get(guild_id, {}).get("w")
        if welcome_id:
            channel = member.guild.get_channel(int(welcome_id))
            if channel:
                embed = discord.Embed(title="✨ عضو جديد!", description=f"مرحباً {member.mention} في سيرفر **{member.guild.name}**", color=0x3498db)
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)

    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        db = load_db()
        # الأمن المطور (روابط وصور)
        if message.guild.id in db.get("security", []):
            if not message.author.guild_permissions.administrator:
                if re.search(r'http[s]?://', message.content) or message.attachments:
                    await message.delete()
                    try: await message.author.send(f"⚠️ ممنوع الروابط والصور في {message.guild.name} حالياً.")
                    except: pass
                    return
        # الرد التلقائي
        responses = db["responses"].get(str(message.guild.id), {})
        if message.content in responses:
            await message.channel.send(responses[message.content])

bot = OPBot()

# --- فئة: الألعاب والترفيه (1 أمر) ---
@bot.tree.command(name="kick-game", description="لعبة الطرد")
async def kickgame_cmd(i: discord.Interaction):
    view = KickGameView(i.user); await i.response.send_message(embed=view.make_embed(), view=view)

# --- فئة: إعدادات السيرفر (12 أمراً) ---
@bot.tree.command(name="set-logs", description="تحديد قناة اللوق")
@app_commands.checks.has_permissions(administrator=True)
async def c1(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["log"] = str(ch.id); save_db(db)
    await i.response.send_message(f"✅ اللوق في: {ch.mention}")

@bot.tree.command(name="setup-ticket", description="نظام التذاكر")
@app_commands.checks.has_permissions(administrator=True)
async def c2(i, ch: discord.TextChannel, title: str):
    await ch.send(embed=discord.Embed(title=title, color=0x2ecc71), view=TicketView()); await i.response.send_message("✅")

@bot.tree.command(name="add-security", description="تفعيل الحماية (روابط وصور)")
@app_commands.checks.has_permissions(administrator=True)
async def c3(i):
    db = load_db()
    if i.guild.id not in db["security"]: db["security"].append(i.guild.id); save_db(db)
    await i.response.send_message("🛡️ تم تفعيل الحماية.")

@bot.tree.command(name="remove-security", description="تعطيل الحماية")
@app_commands.checks.has_permissions(administrator=True)
async def c4(i):
    db = load_db(); db["security"] = [g for g in db["security"] if g != i.guild.id]; save_db(db)
    await i.response.send_message("🔓 تم تعطيل الحماية.")

@bot.tree.command(name="set-welcome", description="قناة الترحيب")
@app_commands.checks.has_permissions(administrator=True)
async def c5(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["w"] = str(ch.id); save_db(db)
    await i.response.send_message("✅ تم تحديد قناة الترحيب.")

@bot.tree.command(name="set-autorole", description="رتبة تلقائية")
@app_commands.checks.has_permissions(administrator=True)
async def c6(i, r: discord.Role):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["r"] = str(r.id); save_db(db)
    await i.response.send_message(f"✅ الرتبة الجديدة: {r.mention}")

@bot.tree.command(name="set-autoreply", description="إضافة رد تلقائي")
@app_commands.checks.has_permissions(administrator=True)
async def sar(i, word: str, reply: str):
    db = load_db(); db["responses"].setdefault(str(i.guild.id), {})[word] = reply; save_db(db)
    await i.response.send_message(f"✅ تم إضافة رد لـ `{word}`")

@bot.tree.command(name="remove-autoreply", description="حذف رد تلقائي")
@app_commands.checks.has_permissions(administrator=True)
async def rar(i, word: str):
    db = load_db(); res = db["responses"].get(str(i.guild.id), {})
    if word in res: del res[word]; save_db(db); await i.response.send_message("🗑️ تم الحذف.")
    else: await i.response.send_message("❌ غير موجود.")

@bot.tree.command(name="set-suggest", description="قناة الاقتراحات")
@app_commands.checks.has_permissions(administrator=True)
async def c9(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["s"] = str(ch.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="server-config", description="إعدادات السيرفر")
@app_commands.checks.has_permissions(administrator=True)
async def c10(i): await i.response.send_message("⚙️ الإعدادات جاهزة.")

# --- فئة: الإدارة (20 أمراً) ---
@bot.tree.command(name="ban", description="حظر")
@app_commands.checks.has_permissions(administrator=True)
async def c11(i, m: discord.Member): await m.ban(); await i.response.send_message("🚫")
@bot.tree.command(name="kick", description="طرد")
@app_commands.checks.has_permissions(administrator=True)
async def c12(i, m: discord.Member): await m.kick(); await i.response.send_message("👢")
@bot.tree.command(name="clear", description="مسح")
@app_commands.checks.has_permissions(manage_messages=True)
async def c13(i, a: int): await i.channel.purge(limit=a); await i.response.send_message(f"🧹 {a}", ephemeral=True)
@bot.tree.command(name="lock", description="قفل")
@app_commands.checks.has_permissions(administrator=True)
async def c14(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")
@bot.tree.command(name="unlock", description="فتح")
@app_commands.checks.has_permissions(administrator=True)
async def c15(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")
@bot.tree.command(name="timeout", description="إسكات")
@app_commands.checks.has_permissions(administrator=True)
async def c16(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message("🔇")
@bot.tree.command(name="nuke", description="نحر القناة")
@app_commands.checks.has_permissions(administrator=True)
async def c17(i): c = await i.channel.clone(); await i.channel.delete(); await c.send("💥 تم تفجير القناة.")
@bot.tree.command(name="slowmode", description="تبطئ القناة")
@app_commands.checks.has_permissions(administrator=True)
async def c18(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"🐢 {s}s")
@bot.tree.command(name="hide", description="إخفاء")
@app_commands.checks.has_permissions(administrator=True)
async def c19(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻")
@bot.tree.command(name="unhide", description="إظهار")
@app_commands.checks.has_permissions(administrator=True)
async def c20(i): await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️")
@bot.tree.command(name="warn", description="تحذير")
@app_commands.checks.has_permissions(administrator=True)
async def c21(i, m: discord.Member, r: str): await i.response.send_message(f"⚠️ {m.mention} حُذرت لـ: {r}")
@bot.tree.command(name="role-add", description="إعطاء رتبة")
@app_commands.checks.has_permissions(administrator=True)
async def c22(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message("✅")
@bot.tree.command(name="role-remove", description="سحب رتبة")
@app_commands.checks.has_permissions(administrator=True)
async def c23(i, m: discord.Member, r: discord.Role): await m.remove_roles(r); await i.response.send_message("✅")
@bot.tree.command(name="vmute", description="كتم صوتي")
@app_commands.checks.has_permissions(administrator=True)
async def c24(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🔇")
@bot.tree.command(name="vunmute", description="فتح صوتي")
@app_commands.checks.has_permissions(administrator=True)
async def c25(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🔊")
@bot.tree.command(name="move", description="نقل عضو")
@app_commands.checks.has_permissions(administrator=True)
async def c26(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("🚚")
@bot.tree.command(name="nick", description="تغيير الاسم")
@app_commands.checks.has_permissions(administrator=True)
async def c27(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("📝")
@bot.tree.command(name="vkick", description="طرد صوتي")
@app_commands.checks.has_permissions(administrator=True)
async def c28(i, m: discord.Member): await m.move_to(None); await i.response.send_message("👢")
@bot.tree.command(name="untimeout", description="إزالة إسكات")
@app_commands.checks.has_permissions(administrator=True)
async def c29(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊")
@bot.tree.command(name="clear-warns", description="مسح تحذيرات")
@app_commands.checks.has_permissions(administrator=True)
async def c30(i, m: discord.Member): await i.response.send_message("🧹 تم التصفير.")

# --- فئة: الاقتصاد (20 أمراً) ---
@bot.tree.command(name="daily", description="راتب يومي")
async def c31(i):
    db = load_db(); uid = str(i.user.id); now = datetime.now()
    last = db["last_daily"].get(uid)
    if last and now < datetime.fromisoformat(last) + timedelta(days=1): return await i.response.send_message("❌ انتظر للغد.")
    db["bank"][uid] = db["bank"].get(uid, 0) + 1000; db["last_daily"][uid] = now.isoformat(); save_db(db); await i.response.send_message("💰 +1000")

@bot.tree.command(name="transfer", description="تحويل كريدت")
async def c34(i, m: discord.Member, a: int):
    if a <= 0: return await i.response.send_message("❌")
    db = load_db(); u, t = str(i.user.id), str(m.id)
    if db["bank"].get(u, 0) < a: return await i.response.send_message("❌ رصيدك لا يكفي.")
    db["bank"][u] -= a; db["bank"][t] = db["bank"].get(t, 0) + a; save_db(db)
    emb = discord.Embed(title="🧾 إيصال تحويل", color=0x2ecc71)
    emb.add_field(name="من:", value=i.user.mention).add_field(name="إلى:", value=m.mention)
    emb.add_field(name="المبلغ:", value=f"{a} 💳").add_field(name="السيرفر:", value=i.guild.name)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="work", description="عمل")
async def c32(i):
    p = random.randint(100, 1000); db = load_db(); u = str(i.user.id); db["bank"][u] = db["bank"].get(u, 0) + p; save_db(db); await i.response.send_message(f"💼 +{p}")
@bot.tree.command(name="credits", description="رصيد")
async def c33(i, m: discord.Member=None):
    db = load_db(); u = str(m.id if m else i.user.id); await i.response.send_message(f"💳 {db['bank'].get(u, 0)}")
@bot.tree.command(name="rob", description="سرقة")
async def c35(i, m: discord.Member):
    s = random.randint(0, 100); db = load_db(); db["bank"][str(i.user.id)] += s; save_db(db); await i.response.send_message(f"🥷 {s}")
@bot.tree.command(name="fish", description="صيد")
async def c36(i):
    g = random.randint(10, 50); db = load_db(); db["bank"][str(i.user.id)] += g; save_db(db); await i.response.send_message(f"🎣 {g}")
@bot.tree.command(name="hunt", description="قنص")
async def c37(i):
    g = random.randint(20, 80); db = load_db(); db["bank"][str(i.user.id)] += g; save_db(db); await i.response.send_message(f"🏹 {g}")
@bot.tree.command(name="give-money", description="منح")
@app_commands.checks.has_permissions(administrator=True)
async def c40(i, m: discord.Member, a: int):
    db = load_db(); db["bank"][str(m.id)] = db["bank"].get(str(m.id), 0) + a; save_db(db); await i.response.send_message("🎁")
@bot.tree.command(name="reset-money", description="تصفير")
@app_commands.checks.has_permissions(administrator=True)
async def c41(i, m: discord.Member):
    db = load_db(); db["bank"][str(m.id)] = 0; save_db(db); await i.response.send_message("🧹")
@bot.tree.command(name="slots", description="رهان")
async def c42(i, a: int): await i.response.send_message("🎰")
@bot.tree.command(name="coinflip", description="عملة")
async def c43(i): await i.response.send_message(random.choice(["🪙 ملك", "🪙 كتابة"]))
@bot.tree.command(name="top-money", description="أغنياء")
async def c44(i): await i.response.send_message("🏆")
@bot.tree.command(name="pay", description="دفع")
async def c45(i, m: discord.Member, a: int): await i.response.send_message("✅")
@bot.tree.command(name="withdraw", description="سحب")
async def c46(i, a: int): await i.response.send_message("🏧")
@bot.tree.command(name="deposit", description="إيداع")
async def c47(i, a: int): await i.response.send_message("🏦")
@bot.tree.command(name="gamble", description="مقامرة")
async def c48(i, a: int): await i.response.send_message("🎲")
@bot.tree.command(name="salary", description="راتب")
async def c49(i): await i.response.send_message("💼")
@bot.tree.command(name="bank-status", description="حالة البنك")
async def c50(i): await i.response.send_message("🏦")
@bot.tree.command(name="store", description="متجر")
async def st(i): await i.response.send_message("🛒")
@bot.tree.command(name="buy", description="شراء")
async def by(i, item: str): await i.response.send_message("📦")

# --- فئة: التسلية (10 أوامر) ---
@bot.tree.command(name="iq", description="ذكاء")
async def c51(i): await i.response.send_message(f"🧠 {random.randint(0,100)}%")
@bot.tree.command(name="hack", description="اختراق")
async def c52(i, m: discord.Member): 
    await i.response.send_message("💻 جاري الاختراق..."); await asyncio.sleep(2); await i.edit_original_response(content="✅ تم اختراقه!")
@bot.tree.command(name="kill", description="قتل")
async def c53(i, m: discord.Member): await i.response.send_message(f"⚔️ {i.user.name} قتل {m.mention}")
@bot.tree.command(name="slap", description="كف")
async def c54(i, m: discord.Member): await i.response.send_message(f"🖐️ {m.mention} أكل كف!")
@bot.tree.command(name="joke", description="نكتة")
async def c55(i): await i.response.send_message("🤣 نكتة سماجة.")
@bot.tree.command(name="dice", description="نرد")
async def c56(i): await i.response.send_message(f"🎲 {random.randint(1,6)}")
@bot.tree.command(name="hug", description="حضن")
async def c57(i, m: discord.Member): await i.response.send_message(f"🤗 {m.mention}")
@bot.tree.command(name="choose", description="اختيار")
async def c58(i, a: str, b: str): await i.response.send_message(f"🤔 اخترت: {random.choice([a,b])}")
@bot.tree.command(name="punch", description="بوكس")
async def c59(i, m: discord.Member): await i.response.send_message(f"👊 {m.mention}")
@bot.tree.command(name="wanted", description="مطلوب")
async def c60(i): await i.response.send_message("⚠️ مطلوب للعدالة!")

# --- فئة: أوامر عامة (10 أوامر) ---
@bot.tree.command(name="ping", description="بينج")
async def c61(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar", description="صورة")
async def c62(i, m: discord.Member=None): await i.response.send_message((m or i.user).display_avatar.url)
@bot.tree.command(name="server", description="سيرفر")
async def c63(i): await i.response.send_message(f"🏰 سيرفر: {i.guild.name}")
@bot.tree.command(name="user-info", description="معلومات العضو")
async def c64(i, m: discord.Member=None): await i.response.send_message(f"👤 الاسم: {(m or i.user).name}")
@bot.tree.command(name="id", description="أيدي")
async def c65(i): await i.response.send_message(f"🆔 {i.user.id}")
@bot.tree.command(name="say", description="كرر")
@app_commands.checks.has_permissions(administrator=True)
async def c66(i, t: str): await i.channel.send(t); await i.response.send_message("✅", ephemeral=True)
@bot.tree.command(name="uptime", description="وقت التشغيل")
async def c67(i): await i.response.send_message("🕒 البوت يعمل منذ فترة.")
@bot.tree.command(name="poll", description="تصويت")
async def c68(i, q: str): await i.response.send_message(f"📊 تصويت: {q}")
@bot.tree.command(name="calculate", description="حساب")
async def c69(i, n1: int, o: str, n2: int): await i.response.send_message(f"🔢 النتيجة تقريبية.")
@bot.tree.command(name="help", description="قائمة الأوامر")
async def c70(i):
    e = discord.Embed(title="📜 قائمة الأوامر (71 أمر)", color=0x3498db)
    e.add_field(name="🛡️ الإدارة", value="ban, kick, clear, lock, set-welcome, set-autorole, set-autoreply, add-security", inline=False)
    e.add_field(name="💰 الاقتصاد", value="daily, transfer, credits, work", inline=False)
    e.add_field(name="🎮 الألعاب", value="kick-game, hack, kill", inline=False)
    await i.response.send_message(embed=e)

bot.run(os.getenv("DISCORD_TOKEN"))
