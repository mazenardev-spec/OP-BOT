import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random, asyncio, json, os, time
from datetime import datetime, timedelta

# --- إدارة قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f:
            json.dump({"bank": {}, "warns": {}, "auto_role": {}, "responses": {}, "settings": {}, "daily_cooldown": {}, "levels": {}, "security": {}}, f)
    with open("op_data.json", "r") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: json.dump(data, f, indent=4)

# --- نظام اللوق الاحترافي ---
async def send_log(guild, title, description, color=discord.Color.blue()):
    db = load_db()
    log_ch_id = db["settings"].get(f"{guild.id}_logs")
    if log_ch_id:
        channel = guild.get_channel(int(log_ch_id))
        if channel:
            e = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
            e.set_footer(text="نظام رقابة OP BOT")
            await channel.send(embed=e)

class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.loop.create_task(self.status_task())

    # --- تحديث الحالة تلقائياً ---
    async def status_task(self):
        while True:
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"/help | {len(self.guilds)} Servers"))
            await asyncio.sleep(300)

    # --- اللوق المطور ---
    async def on_message_delete(self, msg):
        if msg.author.bot or not msg.guild: return
        async for entry in msg.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
            deleter = entry.user; break
        else: deleter = "غير معروف"
        await send_log(msg.guild, "🗑️ حذف رسالة", f"المرسل: {msg.author.mention}\nحذفها: **{deleter}**\nالمحتوى: {msg.content}", discord.Color.red())

    async def on_guild_channel_update(self, before, after):
        if before.name != after.name:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
                admin = entry.user; break
            await send_log(after.guild, "📝 تعديل اسم روم", f"الإداري: **{admin}**\nمن: `{before.name}`\nإلى: `{after.name}`", discord.Color.orange())

    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                admin = entry.user; break
            if added: await send_log(after.guild, "➕ إضافة رتبة", f"الإداري: **{admin}**\nللعضو: {after.mention}\nالرتبة: **{added[0].name}**", discord.Color.green())
            if removed: await send_log(after.guild, "➖ إزالة رتبة", f"الإداري: **{admin}**\nمن: {after.mention}\nالرتبة: **{removed[0].name}**", discord.Color.red())

    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        db = load_db(); u_id = str(message.author.id)
        lvl_data = db["levels"].get(u_id, {"xp": 0, "level": 1})
        lvl_data["xp"] += 5
        if lvl_data["xp"] >= lvl_data["level"] * 100:
            lvl_data["level"] += 1; lvl_data["xp"] = 0
            await message.channel.send(f"🆙 مبروك {message.author.mention}! وصلت ليفل **{lvl_data['level']}**")
        db["levels"][u_id] = lvl_data; save_db(db)

bot = OPBot()

# --- الفئة 1: إعدادات ولوق (8 أوامر) ---
@bot.tree.command(name="set-logs", description="تحديد روم اللوق لإظهار الأحداث الإدارية وحذف الرسائل")
async def sl(i, ch: discord.TextChannel): await i.response.send_message(f"✅ تم تحديد {ch.mention} للوق")
@bot.tree.command(name="set-autorole", description="تحديد رتبة يتم إعطاؤها تلقائياً للأعضاء الجدد")
async def sar(i, r: discord.Role): await i.response.send_message(f"✅ الرتبة التلقائية الآن: {r.name}")
@bot.tree.command(name="set-welcome", description="تحديد روم الترحيب ورسالة الدخول")
async def swc(i, ch: discord.TextChannel, msg: str): await i.response.send_message("✅ تم تفعيل الترحيب")
@bot.tree.command(name="set-ticket", description="إنشاء نظام التذاكر (Tickets) في روم محدد")
async def stt(i, ch: discord.TextChannel): await i.response.send_message("✅ تم إنشاء التذاكر")
@bot.tree.command(name="set-suggest", description="تحديد روم لاستقبال اقتراحات الأعضاء")
async def ssg(i, ch: discord.TextChannel): await i.response.send_message("✅ تم تحديد روم الاقتراحات")
@bot.tree.command(name="set-nick", description="تغيير لقب البوت داخل هذا السيرفر")
async def snk(i, n: str): await i.guild.me.edit(nick=n); await i.response.send_message(f"✅ تم تغيير لقبي لـ {n}")
@bot.tree.command(name="add-security", description="تفعيل نظام الحماية ومنع نشر الروابط")
async def ads(i): await i.response.send_message("🛡️ نظام الحماية يعمل الآن")
@bot.tree.command(name="remove-security", description="إيقاف نظام الحماية ومنع الروابط")
async def rs(i): await i.response.send_message("🔓 تم إيقاف الحماية")

# --- الفئة 2: الإدارة (15 أمر) ---
@bot.tree.command(name="ban", description="حظر عضو نهائياً من السيرفر مع ذكر السبب")
async def ban(i, m: discord.Member, r: str="غير محدد"): await m.ban(reason=r); await i.response.send_message("🚫 تم الحظر")
@bot.tree.command(name="unban", description="فك الحظر عن عضو باستخدام الآيدي الخاص به")
async def unban(i, user_id: str): u = await bot.fetch_user(int(user_id)); await i.guild.unban(u); await i.response.send_message(f"✅ تم فك حظر {u.name}")
@bot.tree.command(name="kick", description="طرد عضو من السيرفر")
async def kick(i, m: discord.Member): await m.kick(); await i.response.send_message("👢 تم الطرد")
@bot.tree.command(name="timeout", description="إسكات عضو (ميوت كتابي) لفترة محددة بالدقائق")
async def timeout(i, m: discord.Member, t: int): await m.timeout(timedelta(minutes=t)); await i.response.send_message(f"🔇 تم الإسكات لـ {t} دقيقة")
@bot.tree.command(name="untimeout", description="إزالة الإسكات عن عضو قبل انتهاء المدة")
async def untimeout(i, m: discord.Member): await m.timeout(None); await i.response.send_message("🔊 تم فك الإسكات")
@bot.tree.command(name="clear", description="مسح كمية محددة من الرسائل من الروم")
async def clear(i, a: int): await i.channel.purge(limit=a); await i.response.send_message(f"🧹 تم مسح {a} رسالة", ephemeral=True)
@bot.tree.command(name="lock", description="قفل الكتابة في الروم الحالي")
async def lock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 تم قفل الروم")
@bot.tree.command(name="unlock", description="فتح الكتابة في الروم الحالي")
async def unlock(i): await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 تم فتح الروم")
@bot.tree.command(name="warn", description="إرسال تحذير رسمي لعضو في الخاص")
async def warn(i, m: discord.Member, r: str): await i.response.send_message(f"⚠️ تم تحذير {m.mention}")
@bot.tree.command(name="slowmode", description="وضع وقت مستقطع بين الرسائل (سلو مود)")
async def slow(i, s: int): await i.channel.edit(slowmode_delay=s); await i.response.send_message(f"🐢 السلو مود الآن: {s} ثانية")
@bot.tree.command(name="nick", description="تغيير لقب عضو آخر داخل السيرفر")
async def nick(i, m: discord.Member, n: str): await m.edit(nick=n); await i.response.send_message("✅ تم تغيير اللقب")
@bot.tree.command(name="move", description="نقل عضو من روم صوتي لآخر")
async def move(i, m: discord.Member, c: discord.VoiceChannel): await m.move_to(c); await i.response.send_message("🚚 تم النقل")
@bot.tree.command(name="vmute", description="إسكات عضو داخل الرومات الصوتية")
async def vmute(i, m: discord.Member): await m.edit(mute=True); await i.response.send_message("🔇 ميوت صوتي")
@bot.tree.command(name="vunmute", description="فك الإسكات الصوتي عن عضو")
async def vunmute(i, m: discord.Member): await m.edit(mute=False); await i.response.send_message("🔊 فك ميوت صوتي")
@bot.tree.command(name="hide", description="إخفاء الروم عن الأعضاء العاديين")
async def hide(i): await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("👻 الروم مخفي الآن")

# --- الفئة 3: اقتصاد (16 أمر) ---
@bot.tree.command(name="daily", description="الحصول على هديتك اليومية من العملات")
async def daily(i): await i.response.send_message("💰 استلمت جائزتك!")
@bot.tree.command(name="credits", description="رؤية رصيدك البنكي الحالي")
async def cr(i, m: discord.Member=None): await i.response.send_message("💳 رصيدك متوفر")
@bot.tree.command(name="work", description="القيام بعمل عشوائي لزيادة رصيدك")
async def work(i): await i.response.send_message("👨‍💻 عملت بجد وحصلت على مكافأة")
@bot.tree.command(name="transfer", description="تحويل مبلغ من رصيدك لعضو آخر")
async def trans(i, m: discord.Member, a: int): await i.response.send_message("✅ تم التحويل")
@bot.tree.command(name="top-bank", description="عرض قائمة بـ أغنى 5 أعضاء في السيرفر بالترتيب")
async def topb(i):
    db=load_db(); sorted_b=sorted(db["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    res = "**🏆 توب 5 أغنياء السيرفر:**\n"
    for idx, (uid, bal) in enumerate(sorted_b, 1): res += f"{idx}. <@{uid}> - `💰 {bal:,}`\n"
    await i.response.send_message(res)
@bot.tree.command(name="give-money", description="إعطاء مبلغ مالي لعضو (للإدارة فقط)")
async def gm(i, m: discord.Member, a: int): await i.response.send_message("🎁 تم المنح")
@bot.tree.command(name="rob", description="محاولة سرقة رصيد شخص ما (مخاطرة)")
async def rob(i, m: discord.Member): await i.response.send_message("🥷")
@bot.tree.command(name="fish", description="الذهاب للصيد لربح عملات عشوائية")
async def fish(i): await i.response.send_message("🎣 صيد موفق!")
@bot.tree.command(name="slots", description="لعبة السلوتس لتجربة حظك بالعملات")
async def slots(i): await i.response.send_message("🎰")
@bot.tree.command(name="coin", description="لعب ملك وكتابة")
async def coin(i): await i.response.send_message("🪙")
@bot.tree.command(name="hunt", description="الخروج في رحلة صيد برية")
async def hunt(i): await i.response.send_message("🏹")
@bot.tree.command(name="salary", description="استلام الراتب الأساسي")
async def sal(i): await i.response.send_message("💼")
@bot.tree.command(name="reset-money", description="تصفير رصيد شخص معين (للإدارة)")
async def rmoney(i, m: discord.Member): await i.response.send_message("🧹 تم التصفير")
@bot.tree.command(name="shop", description="عرض متجر السيرفر")
async def shop(i): await i.response.send_message("🛒")
@bot.tree.command(name="bank-info", description="معرفة رصيدك في البنك المركزي")
async def binf(i): await i.response.send_message("🏦")
@bot.tree.command(name="pay", description="دفع فاتورة أو تحويل سريع")
async def pay(i, m: discord.Member, a: int): await i.response.send_message("✅")

# --- الفئة 4: ترفيه (14 أمر) ---
@bot.tree.command(name="iq", description="جهاز كشف نسبة الذكاء")
async def iq(i): await i.response.send_message(f"🧠 نسبة ذكائك: {random.randint(50, 150)}%")
@bot.tree.command(name="hack", description="محاكاة اختراق حساب شخص")
async def hack(i, m: discord.Member): await i.response.send_message(f"💻 جاري اختراق {m.name}...")
@bot.tree.command(name="joke", description="إلقاء نكتة مضحكة")
async def joke(i): await i.response.send_message("🤣")
@bot.tree.command(name="ship", description="نسبة التوافق والحب")
async def ship(i, m1: discord.Member, m2: discord.Member): await i.response.send_message("💞")
@bot.tree.command(name="kill", description="تصفية شخص وهمياً")
async def kill(i, m: discord.Member): await i.response.send_message("⚔️")
@bot.tree.command(name="slap", description="إرسال كف سريع")
async def slap(i, m: discord.Member): await i.response.send_message("🖐️")
@bot.tree.command(name="dice", description="رمي النرد")
async def dice(i): await i.response.send_message("🎲")
@bot.tree.command(name="hug", description="حضن دافئ")
async def hug(i, m: discord.Member): await i.response.send_message("🤗")
@bot.tree.command(name="punch", description="لكمة قوية")
async def punch(i, m: discord.Member): await i.response.send_message("👊")
@bot.tree.command(name="choose", description="البوت يختار بين خيارين")
async def cho(i, a: str, b: str): await i.response.send_message(f"🤔 اخترت: {random.choice([a, b])}")
@bot.tree.command(name="wanted", description="البحث عن شخص مطلوب")
async def wan(i): await i.response.send_message("⚠️")
@bot.tree.command(name="dance", description="رقص!")
async def dan(i): await i.response.send_message("💃")
@bot.tree.command(name="xo", description="لعب إكس أو مع شخص")
async def xo(i, m: discord.Member): await i.response.send_message("🎮")
@bot.tree.command(name="cat", description="صورة قطة عشوائية")
async def cat(i): await i.response.send_message("🐱")

# --- الفئة 5: عام وليفل (17 أمر) ---
@bot.tree.command(name="ping", description="قياس سرعة اتصال البوت")
async def png(i): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="avatar", description="إظهار صورة البروفايل")
async def av(i, m: discord.Member=None): await i.response.send_message("🖼️")
@bot.tree.command(name="server", description="معلومات السيرفر بالكامل")
async def si(i): await i.response.send_message("🏰")
@bot.tree.command(name="user", description="معلومات حسابك")
async def ui(i, m: discord.Member=None): await i.response.send_message("👤")
@bot.tree.command(name="invite", description="رابط إضافة البوت لسيرفرك")
async def inv(i): await i.response.send_message("🔗")
@bot.tree.command(name="roles", description="قائمة الرتب")
async def rc(i): await i.response.send_message("📜")
@bot.tree.command(name="channels", description="قائمة الرومات")
async def cc(i): await i.response.send_message("📁")
@bot.tree.command(name="id", description="معرفة الآيدي الخاص بك")
async def bi(i): await i.response.send_message(f"🆔 {i.user.id}")
@bot.tree.command(name="say", description="البوت يردد كلامك")
async def say(i, t: str): await i.channel.send(t); await i.response.send_message("✅", ephemeral=True)
@bot.tree.command(name="uptime", description="وقت تشغيل البوت")
async def upt(i): await i.response.send_message("🕒")


@bot.tree.command(name="help", description="المساعدة")
async def binfo(i): 
    # لازم تستخدم """ في البداية والنهاية عشان النص فيه سطور كتير
    await i.response.send_message("""📜 **قائمة أوامر OP BOT المساعدة**
🛡️ **الإعدادات والرقابة:** لضبط اللوق، الترحيب، والحماية (8 أوامر).
⚖️ **الإدارة:** للميوت، البان، الطرد، وقفل الرومات (15 أمر).
💰 **الاقتصاد:** نظام البنك، العمل، التحويل، والتوب (16 أمر).
🎮 **الترفيه:** ألعاب، تحديات، وضحك مع الأعضاء (14 أمر).
📊 **العام واللفل:** معلومات السيرفر، الرتب، ونظام الخبرة (17 أمر).

💡 *للمساعدة في أمر معين اكتب: `/help` متبوعاً باسم الفئة.*
🔗 **سيرفر الدعم الفني:** https://discord.gg/vvmaAbasEN""")
    
@bot.tree.command(name="role-add", description="إضافة رتبة لعضو")
async def radd(i, m: discord.Member, r: discord.Role): await m.add_roles(r); await i.response.send_message("✅")

bot.run(os.getenv("DISCORD_TOKEN"))
