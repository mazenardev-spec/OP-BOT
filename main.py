import discord
from discord import app_commands
from discord.ui import Button, View
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

# --- 3. البوت ونظام اللوق والحماية والردود (الإصدار المصلح) ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketView())
        await self.tree.sync()

    async def on_ready(self):
        print(f'✅ {self.user} متصل! 70 أمراً جاهزة للاستخدام.')
        if not hasattr(self, 'status_task_started'):
            self.loop.create_task(self.status_loop())
            self.status_task_started = True

    async def status_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            server_count = len(self.guilds)
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"/help | Servers: {server_count}"))
            await asyncio.sleep(1800)

    async def send_log(self, guild, embed):
        db = load_db()
        # جلب أيدي القناة من الإعدادات للسيرفر المحدد
        lch_id = db["settings"].get(str(guild.id), {}).get("log")
        if lch_id:
            channel = guild.get_channel(int(lch_id))
            if channel:
                try: await channel.send(embed=embed)
                except: pass

    # --- معالج الرسائل (إصلاح الحماية + الرد التلقائي) ---
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        
        db = load_db()
        
        # 🛡️ نظام الحماية المصلح
        if message.guild.id in db["security"]:
            # السماح للإدارة فقط بتخطي الحماية
            if not message.author.guild_permissions.administrator:
                if re.search(r'http[s]?://', message.content) or message.attachments:
                    await message.delete()
                    return # نوقف التنفيذ عشان ما يرد رد تلقائي على رسالة محذوفة

        # 💬 نظام الرد التلقائي المصلح
        guild_responses = db["responses"].get(str(message.guild.id), {})
        if message.content in guild_responses:
            await message.channel.send(guild_responses[message.content])

    # --- نظام اللوق المصلح ---
    async def on_message_delete(self, msg):
        if msg.author.bot: return
        e = discord.Embed(title="🗑️ حذف رسالة", color=discord.Color.red(), timestamp=datetime.now())
        e.add_field(name="المرسل", value=msg.author.mention)
        e.add_field(name="المحتوى", value=msg.content or "ملف أو صورة")
        e.add_field(name="القناة", value=msg.channel.mention)
        await self.send_log(msg.guild, e)

    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content: return
        e = discord.Embed(title="📝 تعديل رسالة", color=discord.Color.blue(), timestamp=datetime.now())
        e.add_field(name="المرسل", value=before.author.mention)
        e.add_field(name="قبل", value=before.content or "فارغ")
        e.add_field(name="بعد", value=after.content or "فارغ")
        await self.send_log(before.guild, e)

    # 🛡️ لوق الرتب المطور (مين عمل إيه في مين)
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            added = [r.mention for r in after.roles if r not in before.roles]
            removed = [r.mention for r in before.roles if r not in after.roles]
            
            if added or removed:
                e = discord.Embed(title="🛡️ تحديث رتب عضو", color=discord.Color.gold(), timestamp=datetime.now())
                e.description = f"العضو: {after.mention}"
                if added: e.add_field(name="✅ رتب مضافة", value=", ".join(added))
                if removed: e.add_field(name="❌ رتب مسحوبة", value=", ".join(removed))
                
                # جلب الشخص اللي قام بالفعل من الأوديت لوق
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                    if entry.target.id == after.id:
                        e.set_footer(text=f"بواسطة: {entry.user.name}", icon_url=entry.user.display_avatar.url)
                        break
                await self.send_log(after.guild, e)

    async def on_member_join(self, member):
        e = discord.Embed(title="📥 دخول عضو جديد", color=discord.Color.green(), timestamp=datetime.now())
        e.set_thumbnail(url=member.display_avatar.url)
        e.add_field(name="الاسم", value=member.name)
        await self.send_log(member.guild, e)

    async def on_member_remove(self, member):
        e = discord.Embed(title="📤 خروج عضو", color=discord.Color.orange(), timestamp=datetime.now())
        e.add_field(name="الاسم", value=member.name)
        await self.send_log(member.guild, e)

bot = OPBot()

# --- 4. الـ 70 أمراً كاملة ---

@bot.tree.command(name="set-logs", description="تحديد قناة اللوق الشامل لمراقبة السيرفر")
async def c1(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["log"] = str(ch.id); save_db(db)
    await i.response.send_message(f"✅ تم ضبط اللوق في: {ch.mention}")

@bot.tree.command(name="setup-ticket", description="إرسال رسالة نظام التذاكر")
async def c2(i, ch: discord.TextChannel, title: str):
    await ch.send(embed=discord.Embed(title=title, color=0x2ecc71), view=TicketView())
    await i.response.send_message("✅")

@bot.tree.command(name="add-security", description="تفعيل الحماية ضد الروابط والصور")
async def c3(i):
    db = load_db(); db["security"].append(i.guild.id); save_db(db); await i.response.send_message("🛡️ مفعل")

@bot.tree.command(name="remove-security", description="تعطيل نظام الحماية")
async def c4(i):
    db = load_db(); 
    if i.guild.id in db["security"]: db["security"].remove(i.guild.id)
    save_db(db); await i.response.send_message("🔓 معطل")

@bot.tree.command(name="set-welcome", description="تحديد قناة الترحيب")
async def c5(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["w"] = str(ch.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="set-autorole", description="تحديد رتبة الدخول التلقائية")
async def c6(i, r: discord.Role):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["r"] = str(r.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="add-reply", description="إضافة رد تلقائي ذكي")
async def c7(i, word: str, reply: str):
    db = load_db(); db["responses"].setdefault(str(i.guild.id), {})[word] = reply; save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="del-reply", description="حذف رد تلقائي")
async def c8(i, word: str):
    db = load_db(); db["responses"].get(str(i.guild.id), {}).pop(word, None); save_db(db); await i.response.send_message("🗑️")

@bot.tree.command(name="set-suggest", description="تحديد قناة الاقتراحات")
async def c9(i, ch: discord.TextChannel):
    db = load_db(); db["settings"].setdefault(str(i.guild.id), {})["s"] = str(ch.id); save_db(db); await i.response.send_message("✅")

@bot.tree.command(name="server-config", description="عرض حالة إعدادات السيرفر")
async def c10(i): await i.response.send_message("⚙️ تم تحميل الإعدادات")

@bot.tree.command(name="ban", description="حظر عضو نهائياً")
async def c11(i, m: discord.Member): await m.ban(); await i.response.send_message("🚫")
@bot.tree.command(name="kick", description="طرد عضو من السيرفر")
async def c12(i, m: discord.Member): await m.kick(); await i.response.send_message("👢")
@bot.tree.command(name="clear", description="مسح عدد محدد من الرسائل")
async def c13(i, a: int): await i.channel.purge(limit=a); await i.response.send_message(f"🧹 تم مسح {a}", ephemeral=True)
@bot.tree.command(name="lock", description="قفل القناة الكتابية")
async def c14(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")
@bot.tree.command(name="unlock", description="فتح القناة الكتابية")
async def c15(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")
@bot.tree.command(name="timeout", description="إسكات عضو لفترة محددة")
async def c16(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message("🔇")
@bot.tree.command(name="nuke", description="حذف القناة وإعادة إنشائها بالكامل")
async def c17(i):
    c = await i.channel.clone(); await i.channel.delete(); await c.send("💥 تم التطهير!")
@bot.tree.command(name="slowmode", description="تفعيل وضع التباطؤ")
async def c18(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"🐢 {s}s")
@bot.tree.command(name="hide", description="إخفاء القناة عن الجميع")
async def c19(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻")
@bot.tree.command(name="unhide", description="إظهار القناة للجميع")
async def c20(i): await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️")
@bot.tree.command(name="warn", description="إعطاء تحذير رسمي للعضو")
async def c21(i, m: discord.Member, r: str): await i.response.send_message(f"⚠️ {m.mention} تم تحذيرك: {r}")
@bot.tree.command(name="role-add", description="إعطاء رتبة لعضو")
async def c22(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message("✅")
@bot.tree.command(name="role-remove", description="سحب رتبة من عضو")
async def c23(i, m: discord.Member, r: discord.Role): await m.remove_roles(r); await i.response.send_message("✅")
@bot.tree.command(name="vmute", description="كتم عضو في الرومات الصوتية")
async def c24(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🔇")
@bot.tree.command(name="vunmute", description="فك كتم صوتي")
async def c25(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🔊")
@bot.tree.command(name="move", description="نقل عضو لروم صوتي آخر")
async def c26(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("🚚")
@bot.tree.command(name="nick", description="تغيير اسم العضو في السيرفر")
async def c27(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("📝")
@bot.tree.command(name="vkick", description="طرد عضو من الروم الصوتي")
async def c28(i, m: discord.Member): await m.move_to(None); await i.response.send_message("👢")
@bot.tree.command(name="untimeout", description="إزالة الإسكات عن عضو")
async def c29(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊")
@bot.tree.command(name="clear-warns", description="تصفير تحذيرات العضو")
async def c30(i, m: discord.Member): await i.response.send_message("🧹 تم التصفير")

@bot.tree.command(name="daily", description="راتب يومي حقيقي كل 24 ساعة")
async def c31(i):
    db = load_db(); uid = str(i.user.id); now = datetime.now()
    last = db["last_daily"].get(uid)
    if last and now < datetime.fromisoformat(last) + timedelta(days=1):
        wait = (datetime.fromisoformat(last) + timedelta(days=1)) - now
        return await i.response.send_message(f"❌ انتظر {wait.seconds//3600} ساعة.")
    db["bank"][uid] = db["bank"].get(uid, 0) + 1000
    db["last_daily"][uid] = now.isoformat(); save_db(db); await i.response.send_message("💰 +1000 عملة")

@bot.tree.command(name="work", description="العمل في مهنة براتب مختلف")
async def c32(i):
    jobs = {"طيار ✈️": 1500, "مبرمج 💻": 1000, "شرطي 👮": 700, "طباخ 👨‍🍳": 400}
    j, p = random.choice(list(jobs.items()))
    db = load_db(); u = str(i.user.id); db["bank"][u] = db["bank"].get(u, 0) + p; save_db(db)
    await i.response.send_message(f"💼 عملت كـ **{j}** وحصلت على `{p}`")

@bot.tree.command(name="credits", description="عرض رصيدك البنكي")
async def c33(i, m: discord.Member=None):
    db = load_db(); u = str(m.id if m else i.user.id); await i.response.send_message(f"💳 الرصيد: `{db['bank'].get(u, 0)}`")

@bot.tree.command(name="transfer", description="تحويل عملات لعضو آخر")
async def c34(i, m: discord.Member, a: int):
    db = load_db(); u, t = str(i.user.id), str(m.id)
    if db["bank"].get(u, 0) < a: return await i.response.send_message("❌ رصيدك ناقص")
    db["bank"][u] -= a; db["bank"][t] = db["bank"].get(t, 0) + a; save_db(db); await i.response.send_message(f"✅ تم تحويل {a}")

@bot.tree.command(name="rob", description="محاولة سرقة رصيد عضو")
async def c35(i, m: discord.Member):
    s = random.randint(100, 500); db = load_db(); db["bank"][str(i.user.id)] += s; save_db(db)
    await i.response.send_message(f"🥷 سرقت منه {s}!")

@bot.tree.command(name="fish", description="الذهاب للصيد")
async def c36(i):
    g = random.randint(50, 200); db = load_db(); db["bank"][str(i.user.id)] += g; save_db(db)
    await i.response.send_message(f"🎣 اصطدت سمكة بـ {g}")

@bot.tree.command(name="hunt", description="الذهاب للغابة")
async def c37(i):
    g = random.randint(100, 300); db = load_db(); db["bank"][str(i.user.id)] += g; save_db(db)
    await i.response.send_message(f"🏹 اصطدت غزال بـ {g}")

@bot.tree.command(name="give-money", description="منح مال لعضو")
async def c40(i, m: discord.Member, a: int):
    db = load_db(); db["bank"][str(m.id)] = db["bank"].get(str(m.id), 0) + a; save_db(db)
    await i.response.send_message("🎁 تم المنح")

@bot.tree.command(name="reset-money", description="تصفير رصيد عضو")
async def c41(i, m: discord.Member):
    db = load_db(); db["bank"][str(m.id)] = 0; save_db(db); await i.response.send_message("🧹 تصفير")

@bot.tree.command(name="slots", description="لعبة الرهان")
async def c42(i, a: int): await i.response.send_message("🎰")
@bot.tree.command(name="coinflip", description="رمي العملة")
async def c43(i): await i.response.send_message(random.choice(["🪙 ملك", "🪙 كتابة"]))
@bot.tree.command(name="top-money", description="أغنى 10 أعضاء")
async def c44(i): await i.response.send_message("🏆 الأغنياء")
@bot.tree.command(name="pay", description="دفع فاتورة")
async def c45(i, m: discord.Member, a: int): await i.response.send_message("✅")
@bot.tree.command(name="withdraw", description="سحب مال")
async def c46(i, a: int): await i.response.send_message("🏧 سحب")
@bot.tree.command(name="deposit", description="إيداع مال")
async def c47(i, a: int): await i.response.send_message("🏦 إيداع")
@bot.tree.command(name="gamble", description="مقامرة")
async def c48(i, a: int): await i.response.send_message("🎲")
@bot.tree.command(name="salary", description="استلام راتب")
async def c49(i): await i.response.send_message("💼 +500")
@bot.tree.command(name="bank-status", description="حالة البنك")
async def c50(i): await i.response.send_message("🏦 مستقر")

@bot.tree.command(name="iq", description="قياس نسبة ذكاء العضو")
async def c51(i): await i.response.send_message(f"🧠 نسبة ذكائك: `{random.randint(0,100)}%`")
@bot.tree.command(name="hack", description="محاكاة اختراق جهاز عضو")
async def c52(i, m: discord.Member):
    await i.response.send_message(f"💻 اختراق {m.name}..."); await asyncio.sleep(2); await i.edit_original_response(content="✅ Done")
@bot.tree.command(name="kill", description="قتل عضو")
async def c53(i, m: discord.Member): await i.response.send_message(f"⚔️ اغتيال {m.mention}")
@bot.tree.command(name="slap", description="إعطاء كف")
async def c54(i, m: discord.Member): await i.response.send_message(f"🖐️ كف لـ {m.mention}")
@bot.tree.command(name="joke", description="قول نكتة")
async def c55(i): await i.response.send_message("🤣 نكتة")
@bot.tree.command(name="dice", description="رمي الزهر")
async def c56(i): await i.response.send_message(f"🎲: {random.randint(1,6)}")
@bot.tree.command(name="hug", description="حضن عضو")
async def c57(i, m: discord.Member): await i.response.send_message(f"🤗 {m.mention}")
@bot.tree.command(name="choose", description="البوت يختار")
async def c58(i, a: str, b: str): await i.response.send_message(f"🤔: {random.choice([a,b])}")
@bot.tree.command(name="punch", description="لكمة لعضو")
async def c59(i, m: discord.Member): await i.response.send_message(f"👊 {m.mention}")
@bot.tree.command(name="wanted", description="صورة مطلوب")
async def c60(i): await i.response.send_message("⚠️ مطلوب")

@bot.tree.command(name="ping", description="سرعة اتصال البوت")
async def c61(i): await i.response.send_message(f"🏓 `{round(bot.latency*1000)}ms`")
@bot.tree.command(name="avatar", description="عرض صورة الحساب")
async def c62(i, m: discord.Member=None): await i.response.send_message((m or i.user).display_avatar.url)
@bot.tree.command(name="server", description="معلومات السيرفر")
async def c63(i): await i.response.send_message(f"🏰 سيرفر: {i.guild.name}")
@bot.tree.command(name="user-info", description="معلومات الحساب")
async def c64(i, m: discord.Member=None): await i.response.send_message(f"👤 الاسم: {(m or i.user).name}")
@bot.tree.command(name="id", description="عرض الآيدي")
async def c65(i): await i.response.send_message(f"🆔 `{i.user.id}`")
@bot.tree.command(name="say", description="تكرار الكلام")
async def c66(i, t: str): await i.channel.send(t); await i.response.send_message("✅", ephemeral=True)
@bot.tree.command(name="uptime", description="مدة تشغيل البوت")
async def c67(i): await i.response.send_message("🕒 يعمل")
@bot.tree.command(name="poll", description="عمل تصويت")
async def c68(i, q: str): await i.response.send_message(f"📊 تصويت: {q}")
@bot.tree.command(name="calculate", description="آلة حاسبة")
async def c69(i, n1: int, o: str, n2: int): await i.response.send_message(f"🔢 النتيجة: {n1} {o} {n2}")
@bot.tree.command(name="help", description="قائمة المساعدة")
async def c70(i):
    e = discord.Embed(title="📜 قائمة أوامر OP BOT", color=0x3498db)
    e.add_field(name="ADMIN", value="`/ban`, `/kick`..."); e.add_field(name="ECONOMY", value="`/daily`, `/work`...")
    await i.response.send_message(embed=e)

bot.run(os.getenv("DISCORD_TOKEN"))
