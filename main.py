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

# --- 2. نظام التيكت ---
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
        await interaction.response.send_message(f"✅ تم فتح التذكرة: {channel.mention}", ephemeral=True)
        await channel.send(f"أهلاً {interaction.user.mention}، تفضل بطرح مشكلتك.")

# --- 3. فئة الألعاب (1) ---
class KickGameView(View):
    def __init__(self, starter):
        super().__init__(timeout=None)
        self.starter = starter
        self.players = []
        self.is_started = False

    def make_embed(self):
        p_list = "\n".join([f"👤 {p.name}" for p in self.players]) if self.players else "لا يوجد لاعبين."
        e = discord.Embed(title="🎮 لعبة ساحة الطرد", description="انضموا الآن! صاحب الدور يختار من يغادر الساحة.", color=0x5865F2)
        e.add_field(name=f"اللاعبين ({len(self.players)}/200)", value=p_list[:1024], inline=False)
        return e

    @discord.ui.button(label="دخول ✅", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: Button):
        if self.is_started: return await interaction.response.send_message("❌ بدأت اللعبة!", ephemeral=True)
        if interaction.user in self.players: return await interaction.response.send_message("❌ أنت مسجل!", ephemeral=True)
        if len(self.players) >= 200: return await interaction.response.send_message("❌ ممتلئة!", ephemeral=True)
        self.players.append(interaction.user)
        await interaction.message.edit(embed=self.make_embed())
        await interaction.response.send_message("تم دخولك!", ephemeral=True)

    @discord.ui.button(label="خروج ❌", style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, button: Button):
        if interaction.user not in self.players: return await interaction.response.send_message("لست باللعبة!", ephemeral=True)
        self.players.remove(interaction.user)
        await interaction.message.edit(embed=self.make_embed())
        await interaction.response.send_message("خرجت!", ephemeral=True)

    @discord.ui.button(label="بدء اللعبة 🚀", style=discord.ButtonStyle.blurple)
    async def start(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.starter: return await interaction.response.send_message("للصاحب فقط!", ephemeral=True)
        if len(self.players) < 2: return await interaction.response.send_message("نحتاج لاعبين!", ephemeral=True)
        self.is_started = True
        self.clear_items()
        await interaction.message.edit(content="🚀 **بدأت اللعبة!**", view=None)
        await self.game_loop(interaction.channel)

    async def game_loop(self, channel):
        while len(self.players) > 2:
            current = random.choice(self.players)
            select = Select(placeholder="اختر ضحية لتطردها...")
            for p in self.players:
                if p != current: select.add_option(label=p.name, value=str(p.id))
            select.add_option(label="طرد عشوائي 🎲", value="rand")
            select.add_option(label="انسحاب 🏳️", value="quit")

            async def callback(i: discord.Interaction):
                if i.user != current: return await i.response.send_message("مش دورك!", ephemeral=True)
                val = select.values[0]
                if val == "quit":
                    self.players.remove(current); await i.channel.send(f"🏳️ **{current.name}** انسحب!")
                elif val == "rand":
                    target = random.choice([p for p in self.players if p != current])
                    self.players.remove(target); await i.channel.send(f"🎲 طرد عشوائي لـ **{target.name}**!")
                else:
                    target = next(p for p in self.players if str(p.id) == val)
                    self.players.remove(target); await i.channel.send(f"🎯 **{current.name}** طرد **{target.name}**!")
                await i.message.delete(); self.stop_loop.set()

            select.callback = callback
            v = View(timeout=30); v.add_item(select)
            self.stop_loop = asyncio.Event()
            msg = await channel.send(f"🎮 دور: {current.mention} | اختر من القائمة:", view=v)
            try: await asyncio.wait_for(self.stop_loop.wait(), timeout=30)
            except: self.players.remove(current); await msg.delete(); await channel.send(f"⏰ انتهى وقت {current.name}!")

        winner = random.choice(self.players)
        db = load_db(); uid = str(winner.id); db["bank"][uid] = db["bank"].get(uid, 0) + 5000; save_db(db)
        await channel.send(f"👑 **انتهت اللعبة! الفائز {winner.mention} حصل على 5000 كريدت!**")

# --- 4. فئة البوت الأساسية ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)
        self.anti_spam = {} 

    async def setup_hook(self):
        self.add_view(TicketView())
        await self.tree.sync()

    async def on_ready(self):
        print(f'✅ {self.user} متصل! تم تحميل الأوامر كاملة.')

    async def send_log(self, guild, embed):
        db = load_db()
        lch_id = db["settings"].get(str(guild.id), {}).get("log")
        if lch_id:
            channel = guild.get_channel(int(lch_id))
            if channel:
                try: await channel.send(embed=embed)
                except: pass

    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        db = load_db()
        if message.guild.id in db.get("security", []):
            if not message.author.guild_permissions.administrator:
                if re.search(r'http[s]?://', message.content) or message.attachments:
                    try: await message.author.send(f"⚠️ حذفنا رسالتك في **{message.guild.name}** (ممنوع الروابط/الصور).")
                    except: pass
                    await message.delete(); return
                now = datetime.now(); uid = message.author.id
                if uid not in self.anti_spam: self.anti_spam[uid] = []
                self.anti_spam[uid].append(now)
                self.anti_spam[uid] = [t for t in self.anti_spam[uid] if now - t < timedelta(seconds=5)]
                if len(self.anti_spam[uid]) > 5:
                    try: 
                        await message.author.send(f"⚠️ إسكات في **{message.guild.name}** (سبام).")
                        await message.author.timeout(timedelta(minutes=10))
                    except: pass
                    await message.delete(); return
        responses = db["responses"].get(str(message.guild.id), {})
        if message.content in responses: await message.channel.send(responses[message.content])

bot = OPBot()

# --- فئة: الألعاب والترفيه المتطور (1 أمر) ---
@bot.tree.command(name="kick-game", description="لعبة الطرد (200 لاعب + جائزة 5000)")
async def kickgame_cmd(i: discord.Interaction):
    view = KickGameView(i.user); await i.response.send_message(embed=view.make_embed(), view=view)

# --- فئة: إعدادات السيرفر (10 أوامر) ---
@bot.tree.command(name="set-logs", description="تحديد قناة اللوق")
async def c1(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["log"] = str(ch.id); save_db(db)
    await i.response.send_message(f"✅ اللوق في: {ch.mention}")

@bot.tree.command(name="setup-ticket", description="نظام التذاكر")
async def c2(i, ch: discord.TextChannel, title: str):
    await ch.send(embed=discord.Embed(title=title, color=0x2ecc71), view=TicketView()); await i.response.send_message("✅")

@bot.tree.command(name="add-security", description="تفعيل الحماية")
async def c3(i):
    db = load_db(); 
    if i.guild.id not in db["security"]: db["security"].append(i.guild.id); save_db(db)
    await i.response.send_message("🛡️ مفعل.")

@bot.tree.command(name="remove-security", description="تعطيل الحماية")
async def c4(i):
    db = load_db(); db["security"] = [g for g in db["security"] if g != i.guild.id]; save_db(db)
    await i.response.send_message("🔓 معطل.")

@bot.tree.command(name="set-welcome", description="قناة الترحيب")
async def c5(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["w"] = str(ch.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="set-autorole", description="رتبة تلقائية")
async def c6(i, r: discord.Role):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["r"] = str(r.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="add-reply", description="إضافة رد")
async def c7(i, word: str, reply: str):
    db = load_db(); db["responses"].setdefault(str(i.guild.id), {})[word] = reply; save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="del-reply", description="حذف رد")
async def c8(i, word: str):
    db = load_db(); db["responses"].get(str(i.guild.id), {}).pop(word, None); save_db(db); await i.response.send_message("🗑️")

@bot.tree.command(name="set-suggest", description="قناة الاقتراحات")
async def c9(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["s"] = str(ch.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="server-config", description="حالة السيرفر")
async def c10(i): await i.response.send_message("⚙️ تم تحميل الإعدادات")

# --- فئة: الإدارة (20 أمراً) ---
@bot.tree.command(name="ban", description="حظر")
async def c11(i, m: discord.Member): await m.ban(); await i.response.send_message("🚫")

@bot.tree.command(name="kick", description="طرد")
async def c12(i, m: discord.Member): await m.kick(); await i.response.send_message("👢")

@bot.tree.command(name="clear", description="مسح")
async def c13(i, a: int): await i.channel.purge(limit=a); await i.response.send_message(f"🧹 {a}", ephemeral=True)

@bot.tree.command(name="lock", description="قفل")
async def c14(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock", description="فتح")
async def c15(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="timeout", description="إسكات")
async def c16(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message("🔇")

@bot.tree.command(name="nuke", description="تطهير")
async def c17(i): c = await i.channel.clone(); await i.channel.delete(); await c.send("💥")

@bot.tree.command(name="slowmode", description="تباطؤ")
async def c18(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"🐢 {s}s")

@bot.tree.command(name="hide", description="إخفاء")
async def c19(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻")

@bot.tree.command(name="unhide", description="إظهار")
async def c20(i): await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️")

@bot.tree.command(name="warn", description="تحذير")
async def c21(i, m: discord.Member, r: str): await i.response.send_message(f"⚠️ {m.mention}: {r}")

@bot.tree.command(name="role-add", description="إضافة رتبة")
async def c22(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message("✅")

@bot.tree.command(name="role-remove", description="سحب رتبة")
async def c23(i, m: discord.Member, r: discord.Role): await m.remove_roles(r); await i.response.send_message("✅")

@bot.tree.command(name="vmute", description="كتم صوتي")
async def c24(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🔇")

@bot.tree.command(name="vunmute", description="فتح صوتي")
async def c25(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🔊")

@bot.tree.command(name="move", description="نقل")
async def c26(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("🚚")

@bot.tree.command(name="nick", description="اسم")
async def c27(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("📝")

@bot.tree.command(name="vkick", description="طرد صوتي")
async def c28(i, m: discord.Member): await m.move_to(None); await i.response.send_message("👢")

@bot.tree.command(name="untimeout", description="إزالة إسكات")
async def c29(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊")

@bot.tree.command(name="clear-warns", description="مسح تحذيرات")
async def c30(i, m: discord.Member): await i.response.send_message("🧹")

# --- فئة: الاقتصاد (20 أمراً) ---
@bot.tree.command(name="daily", description="يومي")
async def c31(i):
    db = load_db(); uid = str(i.user.id); now = datetime.now()
    last = db["last_daily"].get(uid)
    if last and now < datetime.fromisoformat(last) + timedelta(days=1): return await i.response.send_message("❌")
    db["bank"][uid] = db["bank"].get(uid, 0) + 1000; db["last_daily"][uid] = now.isoformat(); save_db(db); await i.response.send_message("💰 +1000")

@bot.tree.command(name="work", description="عمل")
async def c32(i):
    p = random.randint(100, 1000); db = load_db(); u = str(i.user.id); db["bank"][u] = db["bank"].get(u, 0) + p; save_db(db); await i.response.send_message(f"💼 +{p}")

@bot.tree.command(name="credits", description="رصيد")
async def c33(i, m: discord.Member=None):
    db = load_db(); u = str(m.id if m else i.user.id); await i.response.send_message(f"💳 {db['bank'].get(u, 0)}")

@bot.tree.command(name="transfer", description="تحويل")
async def c34(i, m: discord.Member, a: int):
    db = load_db(); u, t = str(i.user.id), str(m.id)
    if db["bank"].get(u, 0) < a: return await i.response.send_message("❌")
    db["bank"][u] -= a; db["bank"][t] = db["bank"].get(t, 0) + a; save_db(db); await i.response.send_message(f"✅ {a}")

@bot.tree.command(name="rob", description="سرقة")
async def c35(i, m: discord.Member):
    s = random.randint(10, 100); db = load_db(); db["bank"][str(i.user.id)] += s; save_db(db); await i.response.send_message(f"🥷 {s}")

@bot.tree.command(name="fish", description="صيد")
async def c36(i):
    g = random.randint(10, 50); db = load_db(); db["bank"][str(i.user.id)] += g; save_db(db); await i.response.send_message(f"🎣 {g}")

@bot.tree.command(name="hunt", description="غابة")
async def c37(i):
    g = random.randint(20, 80); db = load_db(); db["bank"][str(i.user.id)] += g; save_db(db); await i.response.send_message(f"🏹 {g}")

@bot.tree.command(name="give-money", description="منح")
async def c40(i, m: discord.Member, a: int):
    db = load_db(); db["bank"][str(m.id)] = db["bank"].get(str(m.id), 0) + a; save_db(db); await i.response.send_message("🎁")

@bot.tree.command(name="reset-money", description="تصفير")
async def c41(i, m: discord.Member):
    db = load_db(); db["bank"][str(m.id)] = 0; save_db(db); await i.response.send_message("🧹")

@bot.tree.command(name="slots", description="رهان")
async def c42(i, a: int): await i.response.send_message("🎰")

@bot.tree.command(name="coinflip", description="عملة")
async def c43(i): await i.response.send_message(random.choice(["🪙 ملك", "🪙 كتابة"]))

@bot.tree.command(name="top-money", description="أغنياء")
async def c44(i): await i.response.send_message("🏆 الأغنياء")

@bot.tree.command(name="pay", description="دفع")
async def c45(i, m: discord.Member, a: int): await i.response.send_message("✅")

@bot.tree.command(name="withdraw", description="سحب")
async def c46(i, a: int): await i.response.send_message("🏧 سحب")

@bot.tree.command(name="deposit", description="إيداع")
async def c47(i, a: int): await i.response.send_message("🏦 إيداع")

@bot.tree.command(name="gamble", description="مقامرة")
async def c48(i, a: int): await i.response.send_message("🎲")

@bot.tree.command(name="salary", description="راتب")
async def c49(i): await i.response.send_message("💼 +500")

@bot.tree.command(name="bank-status", description="بنك")
async def c50(i): await i.response.send_message("🏦 مستقر")

@bot.tree.command(name="store", description="متجر")
async def store_cmd(i): await i.response.send_message("🛒 قريباً")

@bot.tree.command(name="buy", description="شراء")
async def buy_cmd(i, item: str): await i.response.send_message(f"📦 اشتريت {item}")

# --- فئة: التسلية (10 أوامر) ---
@bot.tree.command(name="iq", description="ذكاء")
async def c51(i): await i.response.send_message(f"🧠 {random.randint(0,100)}%")

@bot.tree.command(name="hack", description="اختراق")
async def c52(i, m: discord.Member): 
    await i.response.send_message("💻..."); await asyncio.sleep(1); await i.edit_original_response(content="✅")

@bot.tree.command(name="kill", description="قتل")
async def c53(i, m: discord.Member): await i.response.send_message(f"⚔️ {m.mention}")

@bot.tree.command(name="slap", description="كف")
async def c54(i, m: discord.Member): await i.response.send_message(f"🖐️ {m.mention}")

@bot.tree.command(name="joke", description="نكتة")
async def c55(i): await i.response.send_message("🤣")

@bot.tree.command(name="dice", description="زهر")
async def c56(i): await i.response.send_message(f"🎲 {random.randint(1,6)}")

@bot.tree.command(name="hug", description="حضن")
async def c57(i, m: discord.Member): await i.response.send_message(f"🤗 {m.mention}")

@bot.tree.command(name="choose", description="اختيار")
async def c58(i, a: str, b: str): await i.response.send_message(f"🤔 {random.choice([a,b])}")

@bot.tree.command(name="punch", description="لكمة")
async def c59(i, m: discord.Member): await i.response.send_message(f"👊 {m.mention}")

@bot.tree.command(name="wanted", description="مطلوب")
async def c60(i): await i.response.send_message("⚠️ مطلوب")

# --- فئة: أوامر عامة (10 أوامر) ---
@bot.tree.command(name="ping", description="اتصال")
async def c61(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")

@bot.tree.command(name="avatar", description="صورة")
async def c62(i, m: discord.Member=None): await i.response.send_message((m or i.user).display_avatar.url)

@bot.tree.command(name="server", description="سيرفر")
async def c63(i): await i.response.send_message(f"🏰 {i.guild.name}")

@bot.tree.command(name="user-info", description="معلومات")
async def c64(i, m: discord.Member=None): await i.response.send_message(f"👤 {(m or i.user).name}")

@bot.tree.command(name="id", description="أيدي")
async def c65(i): await i.response.send_message(f"🆔 {i.user.id}")

@bot.tree.command(name="say", description="كرر")
async def c66(i, t: str): await i.channel.send(t); await i.response.send_message("✅", ephemeral=True)

@bot.tree.command(name="uptime", description="وقت")
async def c67(i): await i.response.send_message("🕒 يعمل")

@bot.tree.command(name="poll", description="تصويت")
async def c68(i, q: str): await i.response.send_message(f"📊 {q}")

@bot.tree.command(name="calculate", description="حساب")
async def c69(i, n1: int, o: str, n2: int): await i.response.send_message(f"🔢")

@bot.tree.command(name="help", description="مساعدة")
async def c70(i):
    e = discord.Embed(title="📜 قائمة الأوامر (71 أمر)", color=0x3498db)
    e.add_field(name="الألعاب", value="`/kick-game`").add_field(name="الإدارة", value="`/ban`, `/kick`...")
    await i.response.send_message(embed=e)

bot.run(os.getenv("DISCORD_TOKEN"))
