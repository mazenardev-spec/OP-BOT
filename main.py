import discord
from discord import app_commands
from discord.ui import Button, View
import random, asyncio, json, os
from datetime import timedelta

# --- 1. إعداد البوت والـ Presence الاحترافي ---
class OPBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.loop.create_task(self.update_status())
        print(f"✅ {self.user} جاهز للعمل بـ 60 أمر!")

    async def update_status(self):
        """تحديث الحالة مثل صورة Nova: /help — {عدد السيرفرات} servers"""
        await self.wait_until_ready()
        while not self.is_closed():
            guild_count = len(self.guilds)
            status = f"/help — {guild_count} servers"
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status))
            await asyncio.sleep(1800) # تحديث كل 30 دقيقة لضمان دقة عدد السيرفرات

bot = OPBot()

# --- 2. نظام قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f: 
            json.dump({"bank": {}, "warns": {}}, f)
    with open("op_data.json", "r") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: json.dump(data, f, indent=4)

# ==========================================
# 3. أمر المساعدة الشامل (/help)
# ==========================================

@bot.tree.command(name="help", description="عرض جميع أوامر OP BOT الـ 60")
async def help_cmd(i: discord.Interaction):
    embed = discord.Embed(title="📚 دليل أوامر OP BOT", color=0x00ff00)
    embed.add_field(name="🛡️ الإدارة (15)", value="`timeout`, `untimeout`, `ban`, `kick`, `clear`, `lock`, `unlock`, `hide`, `show`, `slowmode`, `warn`, `unban`, `nick`, `add-role`, `remove-role`")
    embed.add_field(name="💰 الاقتصاد (15)", value="`daily`, `credits`, `work`, `transfer`, `top`, `rob`, `fish`, `hunt`, `give`, `coin`, `salary`, `shop`, `buy`, `wallet`, `bank-info`")
    embed.add_field(name="🎮 الترفيه (15)", value="`xo`, `dice`, `iq`, `love`, `hack`, `slap`, `kill`, `hug`, `punch`, `joke`, `slots`, `ship`, `hot`, `choose`, `wanted`")
    embed.add_field(name="ℹ️ معلومات (15)", value="`user`, `server`, `avatar`, `ping`, `bot-id`, `channel-id`, `guild-id`, `roles-count`, `boosts`, `owner`, `uptime`, `math`, `say`, `invite`, `perms`")
    await i.response.send_message(embed=embed)

# ==========================================
# 4. أوامر الإدارة مع فحص الصلاحيات (15 أمر)
# ==========================================

@bot.tree.command(name="timeout", description="إسكات عضو")
async def timeout(i: discord.Interaction, member: discord.Member, minutes: int):
    if not i.user.guild_permissions.moderate_members: return await i.response.send_message("❌ لا تملك صلاحية!", ephemeral=True)
    await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🔇 تم إسكات {member.mention}")

@bot.tree.command(name="untimeout", description="فك إسكات عضو")
async def untimeout(i: discord.Interaction, member: discord.Member):
    if not i.user.guild_permissions.moderate_members: return
    await member.timeout(None); await i.response.send_message(f"🔊 فك إسكات {member.mention}")

@bot.tree.command(name="ban", description="حظر عضو")
async def ban(i: discord.Interaction, member: discord.Member):
    if not i.user.guild_permissions.ban_members: return
    await member.ban(); await i.response.send_message(f"✅ تم حظر {member.name}")

@bot.tree.command(name="kick", description="طرد عضو")
async def kick(i: discord.Interaction, member: discord.Member):
    if not i.user.guild_permissions.kick_members: return
    await member.kick(); await i.response.send_message(f"✅ تم طرد {member.name}")

@bot.tree.command(name="clear", description="مسح رسائل")
async def clear(i: discord.Interaction, amount: int):
    if not i.user.guild_permissions.manage_messages: return
    await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 تم مسح {amount} رسالة", ephemeral=True)

@bot.tree.command(name="lock", description="قفل القناة")
async def lock(i: discord.Interaction):
    if not i.user.guild_permissions.manage_channels: return
    await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 القناة مقفلة")

@bot.tree.command(name="unlock", description="فتح القناة")
async def unlock(i: discord.Interaction):
    if not i.user.guild_permissions.manage_channels: return
    await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 القناة مفتوحة")

@bot.tree.command(name="hide", description="إخفاء القناة")
async def hide(i: discord.Interaction):
    if not i.user.guild_permissions.manage_channels: return
    await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("🙈 تم إخفاء القناة")

@bot.tree.command(name="show", description="إظهار القناة")
async def show(i: discord.Interaction):
    if not i.user.guild_permissions.manage_channels: return
    await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️ تم إظهار القناة")

@bot.tree.command(name="slowmode", description="تفعيل وضع البطء")
async def slowmode(i: discord.Interaction, seconds: int):
    if not i.user.guild_permissions.manage_channels: return
    await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ البطء: {seconds}ث")

@bot.tree.command(name="warn", description="تحذير عضو")
async def warn(i: discord.Interaction, member: discord.Member, reason: str):
    if not i.user.guild_permissions.moderate_members: return
    db = load_db(); m_id = str(member.id); db["warns"][m_id] = db["warns"].get(m_id, 0) + 1; save_db(db)
    await i.response.send_message(f"⚠️ تحذير {member.mention} | السبب: {reason}")

@bot.tree.command(name="unban", description="فك حظر بالأيدي")
async def unban(i: discord.Interaction, user_id: str):
    if not i.user.guild_permissions.ban_members: return
    u = await bot.fetch_user(int(user_id)); await i.guild.unban(u); await i.response.send_message(f"✅ فك حظر {u.name}")

@bot.tree.command(name="nick", description="تغيير لقب")
async def nick(i: discord.Interaction, member: discord.Member, name: str):
    if not i.user.guild_permissions.manage_nicknames: return
    await member.edit(nick=name); await i.response.send_message("✅ تم تغيير اللقب")

@bot.tree.command(name="add-role", description="إعطاء رتبة")
async def add_role(i: discord.Interaction, member: discord.Member, role: discord.Role):
    if not i.user.guild_permissions.manage_roles: return
    await member.add_roles(role); await i.response.send_message("✅ تم إضافة الرتبة")

@bot.tree.command(name="remove-role", description="سحب رتبة")
async def remove_role(i: discord.Interaction, member: discord.Member, role: discord.Role):
    if not i.user.guild_permissions.manage_roles: return
    await member.remove_roles(role); await i.response.send_message("❌ تم سحب الرتبة")

# ==========================================
# 5. أوامر الاقتصاد (15 أمر)
# ==========================================

@bot.tree.command(name="daily", description="استلام الراتب اليومي")
async def daily(i: discord.Interaction):
    db = load_db(); u = str(i.user.id); db["bank"][u] = db["bank"].get(u,0)+1000; save_db(db)
    await i.response.send_message("💰 مبروك 1000 كريديت!")

@bot.tree.command(name="credits", description="رؤية الرصيد")
async def credits(i: discord.Interaction, member: discord.Member=None):
    db = load_db(); m = member or i.user; await i.response.send_message(f"💳 رصيد {m.name}: `{db['bank'].get(str(m.id),0)}`")

@bot.tree.command(name="work", description="العمل لجمع المال")
async def work(i: discord.Interaction):
    g = random.randint(100,500); db = load_db(); u = str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+g; save_db(db)
    await i.response.send_message(f"👷 عملت وربحت {g}")

@bot.tree.command(name="transfer", description="تحويل مال")
async def transfer(i: discord.Interaction, member: discord.Member, amount: int):
    db = load_db(); sid, rid = str(i.user.id), str(member.id)
    if db["bank"].get(sid,0) < amount: return await i.response.send_message("❌ رصيدك ناقص")
    db["bank"][sid]-=amount; db["bank"][rid]=db["bank"].get(rid,0)+amount; save_db(db)
    await i.response.send_message(f"✅ تم تحويل {amount} لـ {member.name}")

@bot.tree.command(name="top", description="أغنى 5 في السيرفر")
async def top(i: discord.Interaction):
    db = load_db(); top_users = sorted(db["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    res = "\n".join([f"<@{u}>: {a}" for u,a in top_users]); await i.response.send_message(f"🏆 أغنى الأعضاء:\n{res}")

@bot.tree.command(name="rob", description="محاولة سرقة")
async def rob(i: discord.Interaction, member: discord.Member):
    if random.choice([True, False]): await i.response.send_message(f"⚔️ سرقت {member.name}!")
    else: await i.response.send_message("👮 قفطوك الشرطة!")

@bot.tree.command(name="fish", description="صيد سمك")
async def fish(i: discord.Interaction): await i.response.send_message(f"🎣 اصطدت سمكة بـ {random.randint(10,80)}")

@bot.tree.command(name="hunt", description="صيد غزال")
async def hunt(i: discord.Interaction): await i.response.send_message("🏹 اصطدت غزالاً وربحت مالاً")

@bot.tree.command(name="give", description="منح مال (أدمن فقط)")
async def give(i: discord.Interaction, member: discord.Member, amount: int):
    if not i.user.guild_permissions.administrator: return
    db = load_db(); db["bank"][str(member.id)]=db["bank"].get(str(member.id),0)+amount; save_db(db); await i.response.send_message("🎁 تم المنح")

@bot.tree.command(name="coin", description="تخمين العملة")
async def coin(i: discord.Interaction, choice: str):
    w = random.choice(['ملك', 'كتابة']); await i.response.send_message(f"🪙 {w}! {'فزت' if choice==w else 'خسرت'}")

@bot.tree.command(name="salary", description="استلام الراتب")
async def salary(i: discord.Interaction): await i.response.send_message("💼 راتبك 200 كريديت")

@bot.tree.command(name="shop", description="المتجر")
async def shop(i: discord.Interaction): await i.response.send_message("🛒 المتجر مغلق حالياً")

@bot.tree.command(name="buy", description="شراء عنصر")
async def buy(i: discord.Interaction, item: str): await i.response.send_message(f"❌ العنصر {item} غير متوفر")

@bot.tree.command(name="wallet", description="المحفظة")
async def wallet(i: discord.Interaction): await i.response.send_message("👛 محفظة مشفرة")

@bot.tree.command(name="bank-info", description="نظام البنك")
async def binfo(i: discord.Interaction): await i.response.send_message("🛡️ محمي بواسطة OP")

# ==========================================
# 6. أوامر الترفيه (15 أمر)
# ==========================================

@bot.tree.command(name="xo", description="لعبة XO")
async def xo(i: discord.Interaction, member: discord.Member): await i.response.send_message(f"🎮 تحدي {member.mention}")

@bot.tree.command(name="dice", description="رمي النرد")
async def dice(i: discord.Interaction): await i.response.send_message(f"🎲 النتيجة: {random.randint(1,6)}")

@bot.tree.command(name="iq", description="نسبة الذكاء")
async def iq(i: discord.Interaction, m: discord.Member=None): await i.response.send_message(f"🧠 نسبة ذكاء {m.name if m else 'أنت'} هي {random.randint(1,200)}%")

@bot.tree.command(name="love", description="نسبة الحب")
async def love(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"❤️ نسبة الحب مع {m.name} هي {random.randint(1,100)}%")

@bot.tree.command(name="hack", description="اختراق وهمي")
async def hack(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"💻 جاري اختراق {m.name}...")

@bot.tree.command(name="slap", description="صفع")
async def slap(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"🖐️ كف لـ {m.name}")

@bot.tree.command(name="kill", description="قتل وهمي")
async def kill(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"⚔️ {i.user.name} قتل {m.name}")

@bot.tree.command(name="hug", description="حضن")
async def hug(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"🤗 حضن لـ {m.name}")

@bot.tree.command(name="punch", description="لكمة")
async def punch(i: discord.Interaction, m: discord.Member): await i.response.send_message("👊 بوكس!")

@bot.tree.command(name="joke", description="نكتة")
async def joke(i: discord.Interaction): await i.response.send_message("مرة واحد...")

@bot.tree.command(name="slots", description="آلة الحظ")
async def slots(i: discord.Interaction): await i.response.send_message("🎰 🍎 | 🍎 | 💎")

@bot.tree.command(name="ship", description="توافق شخصين")
async def ship(i: discord.Interaction, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 توافق {m1.name} و {m2.name} هو {random.randint(1,100)}%")

@bot.tree.command(name="hot", description="نسبة الجمال")
async def hot(i: discord.Interaction, m: discord.Member=None): await i.response.send_message(f"🔥 نسبة الجمال {random.randint(1,100)}%")

@bot.tree.command(name="choose", description="البوت يختار")
async def choose(i: discord.Interaction, a: str, b: str): await i.response.send_message(f"🤔 أختار: {random.choice([a,b])}")

@bot.tree.command(name="wanted", description="مطلوب للعدالة")
async def wanted(i: discord.Interaction, m: discord.Member=None): await i.response.send_message("⚠️ مطلوب حياً أو ميتاً")

# ==========================================
# 7. أوامر المعلومات (15 أمر)
# ==========================================

@bot.tree.command(name="user", description="معلومات حسابك")
async def user_info(i: discord.Interaction, m: discord.Member=None):
    m = m or i.user; await i.response.send_message(f"👤 {m.name} | ID: {m.id}")

@bot.tree.command(name="server", description="معلومات السيرفر")
async def server_info(i: discord.Interaction):
    await i.response.send_message(f"🏰 {i.guild.name} | الأعضاء: {i.guild.member_count}")

@bot.tree.command(name="avatar", description="صورتك الشخصية")
async def avatar(i: discord.Interaction, m: discord.Member=None):
    m = m or i.user; await i.response.send_message(m.display_avatar.url)

@bot.tree.command(name="ping", description="سرعة البوت")
async def ping(i: discord.Interaction): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")

@bot.tree.command(name="bot-id", description="أيدي البوت")
async def bid(i: discord.Interaction): await i.response.send_message(bot.user.id)

@bot.tree.command(name="channel-id", description="أيدي القناة")
async def cid(i: discord.Interaction): await i.response.send_message(i.channel.id)

@bot.tree.command(name="guild-id", description="أيدي السيرفر")
async def gid(i: discord.Interaction): await i.response.send_message(i.guild.id)

@bot.tree.command(name="roles-count", description="عدد الرتب")
async def rcount(i: discord.Interaction): await i.response.send_message(len(i.guild.roles))

@bot.tree.command(name="boosts", description="عدد البوستات")
async def boosts(i: discord.Interaction): await i.response.send_message(i.guild.premium_subscription_count)

@bot.tree.command(name="owner", description="صاحب السيرفر")
async def owner(i: discord.Interaction): await i.response.send_message(i.guild.owner.mention)

@bot.tree.command(name="uptime", description="وقت التشغيل")
async def uptime(i: discord.Interaction): await i.response.send_message("🚀 Online")

@bot.tree.command(name="math", description="عملية حسابية")
async def math(i: discord.Interaction, x: int, y: int): await i.response.send_message(f"🔢 الناتج: {x+y}")

@bot.tree.command(name="say", description="تكرار الكلام")
async def say(i: discord.Interaction, text: str): await i.channel.send(text); await i.response.send_message("تم", ephemeral=True)

@bot.tree.command(name="invite", description="رابط الدعوة")
async def invite(i: discord.Interaction): await i.response.send_message("🔗 رابط البوت الخاص بك")

@bot.tree.command(name="perms", description="صلاحيات البوت")
async def perms(i: discord.Interaction): await i.response.send_message("✅ مفعلة بالكامل")

# --- 8. التشغيل الآمن والذكي ---

if __name__ == "__main__":
    # تشغيل نظام الـ Keep Alive عشان البوت ما يطفيش على Render
    keep_alive() 
    
    # هنا بنقول للبوت اقرأ التوكين من إعدادات Render السرية (Environment Variables)
    # عشان GitHub ما يبعتلكش رسائل تحذير تاني
    TOKEN = os.getenv("MTQ5NTgwNzI0NTg1NjgwNDk3Ng.GgZDoM.V2y6J8iRamUv91CeNiNn0Ajilb0uGmFfBcA6DA")
    
    if TOKEN:
        # تشغيل البوت
        asyncio.run(bot.start(TOKEN))
    else:
        print("❌ خطأ: لم يتم العثور على التوكين! تأكد من إضافته في Render باسم DISCORD_TOKEN")