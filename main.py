import discord
from discord import app_commands
from discord.ui import Button, View
import random, asyncio, json, os
from datetime import timedelta
from flask import Flask
from threading import Thread

# --- 1. نظام الـ Keep Alive ---
app = Flask('')
@app.route('/')
def home(): return "OP BOT IS ONLINE"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. إعداد البوت وأنظمة التفاعل الجديدة ---

class TicketActions(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="قفل التذكرة", style=discord.ButtonStyle.danger, custom_id="close_t")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("سيتم غلق القناة...")
        await interaction.channel.delete()

    @discord.ui.button(label="استلام", style=discord.ButtonStyle.success, custom_id="claim_t")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"تم الاستلام بواسطة: {interaction.user.mention}")

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="فتح تذكرة", style=discord.ButtonStyle.primary, custom_id="open_t")
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)
        await channel.send(f"مرحباً {interaction.user.mention}، سيتم الرد عليك قريباً.", view=TicketActions())
        await interaction.response.send_message(f"تم فتح التذكرة: {channel.mention}", ephemeral=True)

class OPBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.welcome_channels = {} # لتخزين قناة الترحيب المحددة

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActions())
        await self.tree.sync()
        self.loop.create_task(self.update_status())
        print(f"✅ {self.user} جاهز مع نظام التيكت والترحيب المخصص!")

    async def update_status(self):
        await self.wait_until_ready()
        while not self.is_closed():
            status = f"/help — {len(self.guilds)} servers"
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status))
            await asyncio.sleep(1800)

    # نظام الترحيب الجديد (يعتمد على اختيارك للروم)
    async def on_member_join(self, member):
        ch_id = self.welcome_channels.get(member.guild.id)
        if ch_id:
            channel = member.guild.get_channel(ch_id)
            if channel:
                embed = discord.Embed(title="✨ عضو جديد وصل!", description=f"نورت السيرفر يا {member.mention}", color=0x00ff00)
                embed.set_thumbnail(url=member.display_avatar.url)
                try: await channel.send(embed=embed)
                except: pass

bot = OPBot()

# --- 3. نظام قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f: json.dump({"bank": {}, "warns": {}}, f)
    with open("op_data.json", "r") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: json.dump(data, f, indent=4)

# ==========================================
# 4. الأوامر الجديدة (Ticket & Welcome)
# ==========================================

@bot.tree.command(name="set-ticket", description="إعداد نظام التذاكر في روم معينة")
@app_commands.checks.has_permissions(administrator=True)
async def set_ticket(i: discord.Interaction, channel: discord.TextChannel):
    await channel.send("اضغط على الزر أدناه لفتح تذكرة دعم فني", view=TicketView())
    await i.response.send_message("✅ تم إعداد نظام التيكت.", ephemeral=True)

@bot.tree.command(name="set-welcome", description="تحديد روم الترحيب")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome(i: discord.Interaction, channel: discord.TextChannel):
    bot.welcome_channels[i.guild.id] = channel.id
    await i.response.send_message(f"✅ تم تعيين {channel.mention} كروم ترحيب.")

# ==========================================
# 5. أوامر الإدارة (15 أمر)
# ==========================================

@bot.tree.command(name="help", description="دليل أوامر OP BOT الشامل")
async def help_cmd(i: discord.Interaction):
    embed = discord.Embed(title="📚 أوامر OP BOT", color=0x00ff00)
    embed.add_field(name="🛡️ إدارة وإعداد", value="`set-ticket`, `set-welcome`, `timeout`, `untimeout`, `ban`, `kick`, `clear`, `lock`, `unlock`, `hide`, `show`, `slowmode`, `warn`, `unban`, `nick`, `add-role`, `remove-role`")
    embed.add_field(name="💰 اقتصاد", value="`daily`, `credits`, `work`, `transfer`, `top`, `rob`, `fish`, `hunt`, `give`, `coin`, `salary`, `shop`, `buy`, `wallet`, `bank-info`")
    embed.add_field(name="🎮 ترفيه", value="`xo`, `dice`, `iq`, `love`, `hack`, `slap`, `kill`, `hug`, `punch`, `joke`, `slots`, `ship`, `hot`, `choose`, `wanted`")
    embed.add_field(name="ℹ️ معلومات", value="`user`, `server`, `avatar`, `ping`, `bot-id`, `channel-id`, `guild-id`, `roles-count`, `boosts`, `owner`, `uptime`, `math`, `say`, `invite`, `perms`")
    await i.response.send_message(embed=embed)

@bot.tree.command(name="timeout", description="إسكات عضو لفترة محددة")
async def timeout(i: discord.Interaction, member: discord.Member, minutes: int):
    if not i.user.guild_permissions.moderate_members: return
    await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🔇 {member.mention}")

@bot.tree.command(name="untimeout", description="إزالة الإسكات عن عضو")
async def untimeout(i: discord.Interaction, member: discord.Member):
    if not i.user.guild_permissions.moderate_members: return
    await member.timeout(None); await i.response.send_message(f"🔊 {member.mention}")

@bot.tree.command(name="ban", description="حظر عضو من السيرفر")
async def ban(i: discord.Interaction, member: discord.Member):
    if not i.user.guild_permissions.ban_members: return
    await member.ban(); await i.response.send_message(f"✅ Banned {member.name}")

@bot.tree.command(name="kick", description="طرد عضو من السيرفر")
async def kick(i: discord.Interaction, member: discord.Member):
    if not i.user.guild_permissions.kick_members: return
    await member.kick(); await i.response.send_message(f"✅ Kicked {member.name}")

@bot.tree.command(name="clear", description="مسح عدد معين من الرسائل")
async def clear(i: discord.Interaction, amount: int):
    if not i.user.guild_permissions.manage_messages: return
    await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 {amount}", ephemeral=True)

@bot.tree.command(name="lock", description="قفل القناة الحالية")
async def lock(i: discord.Interaction):
    if not i.user.guild_permissions.manage_channels: return
    await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock", description="فتح القناة المقفلة")
async def unlock(i: discord.Interaction):
    if not i.user.guild_permissions.manage_channels: return
    await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="hide", description="إخفاء القناة")
async def hide(i: discord.Interaction):
    if not i.user.guild_permissions.manage_channels: return
    await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("🙈")

@bot.tree.command(name="show", description="إظهار القناة")
async def show(i: discord.Interaction):
    if not i.user.guild_permissions.manage_channels: return
    await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️")

@bot.tree.command(name="slowmode", description="تحديد وضع الهدوء")
async def slowmode(i: discord.Interaction, seconds: int):
    if not i.user.guild_permissions.manage_channels: return
    await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ {seconds}s")

@bot.tree.command(name="warn", description="إعطاء تحذير لعضو")
async def warn(i: discord.Interaction, member: discord.Member, reason: str):
    if not i.user.guild_permissions.moderate_members: return
    db = load_db(); m_id = str(member.id); db["warns"][m_id] = db["warns"].get(m_id, 0) + 1; save_db(db)
    await i.response.send_message(f"⚠️ {member.mention} | {reason}")

@bot.tree.command(name="unban", description="فك حظر عضو عبر الأيدي")
async def unban(i: discord.Interaction, user_id: str):
    if not i.user.guild_permissions.ban_members: return
    u = await bot.fetch_user(int(user_id)); await i.guild.unban(u); await i.response.send_message(f"✅ Unbanned {u.name}")

@bot.tree.command(name="nick", description="تغيير لقب العضو")
async def nick(i: discord.Interaction, member: discord.Member, name: str):
    if not i.user.guild_permissions.manage_nicknames: return
    await member.edit(nick=name); await i.response.send_message("✅")

@bot.tree.command(name="add-role", description="إضافة رتبة لعضو")
async def add_role(i: discord.Interaction, member: discord.Member, role: discord.Role):
    if not i.user.guild_permissions.manage_roles: return
    await member.add_roles(role); await i.response.send_message("✅")

@bot.tree.command(name="remove-role", description="سحب رتبة من عضو")
async def remove_role(i: discord.Interaction, member: discord.Member, role: discord.Role):
    if not i.user.guild_permissions.manage_roles: return
    await member.remove_roles(role); await i.response.send_message("❌")

# ==========================================
# 6. أوامر الاقتصاد (15 أمر)
# ==========================================

@bot.tree.command(name="daily", description="استلام الراتب اليومي")
async def daily(i: discord.Interaction):
    db = load_db(); u = str(i.user.id); db["bank"][u] = db["bank"].get(u,0)+1000; save_db(db)
    await i.response.send_message("💰 +1000")

@bot.tree.command(name="credits", description="رصيدك الحالي")
async def credits(i: discord.Interaction, member: discord.Member=None):
    db = load_db(); m = member or i.user; await i.response.send_message(f"💳 {m.name}: {db['bank'].get(str(m.id),0)}")

@bot.tree.command(name="work", description="العمل لجمع المال")
async def work(i: discord.Interaction):
    g = random.randint(100,500); db = load_db(); u = str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+g; save_db(db)
    await i.response.send_message(f"👷 {g}")

@bot.tree.command(name="transfer", description="تحويل مال لشخص آخر")
async def transfer(i: discord.Interaction, member: discord.Member, amount: int):
    db = load_db(); sid, rid = str(i.user.id), str(member.id)
    if db["bank"].get(sid,0) < amount: return await i.response.send_message("❌")
    db["bank"][sid]-=amount; db["bank"][rid]=db["bank"].get(rid,0)+amount; save_db(db)
    await i.response.send_message(f"✅ {amount} -> {member.name}")

@bot.tree.command(name="top", description="قائمة أغنى الأعضاء")
async def top(i: discord.Interaction):
    db = load_db(); top_users = sorted(db["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    res = "\n".join([f"<@{u}>: {a}" for u,a in top_users]); await i.response.send_message(f"🏆 Top 5:\n{res}")

@bot.tree.command(name="rob", description="محاولة سرقة عضو")
async def rob(i: discord.Interaction, member: discord.Member):
    if random.choice([True, False]): await i.response.send_message(f"⚔️ تمت السرقة من {member.name}"); return
    await i.response.send_message("👮 فشلت السرقة")

@bot.tree.command(name="fish", description="صيد السمك")
async def fish(i: discord.Interaction): await i.response.send_message(f"🎣 {random.randint(10,80)}")

@bot.tree.command(name="hunt", description="الذهاب للصيد")
async def hunt(i: discord.Interaction): await i.response.send_message("🏹 Hunter!")

@bot.tree.command(name="give", description="إعطاء مال (للمسؤولين)")
async def give(i: discord.Interaction, member: discord.Member, amount: int):
    if not i.user.guild_permissions.administrator: return
    db = load_db(); db["bank"][str(member.id)]=db["bank"].get(str(member.id),0)+amount; save_db(db); await i.response.send_message("🎁")

@bot.tree.command(name="coin", description="لعبة العملة")
async def coin(i: discord.Interaction, choice: str):
    w = random.choice(['ملك', 'كتابة']); await i.response.send_message(f"🪙 {w}")

@bot.tree.command(name="salary", description="استلام الراتب")
async def salary(i: discord.Interaction): await i.response.send_message("💼 200")

@bot.tree.command(name="shop", description="المتجر")
async def shop(i: discord.Interaction): await i.response.send_message("🛒 المتجر فارغ حالياً")

@bot.tree.command(name="buy", description="شراء غرض")
async def buy(i: discord.Interaction, item: str): await i.response.send_message("❌")

@bot.tree.command(name="wallet", description="محفظتك")
async def wallet(i: discord.Interaction): await i.response.send_message("👛")

@bot.tree.command(name="bank-info", description="معلومات البنك")
async def binfo(i: discord.Interaction): await i.response.send_message("🛡️ بنك مؤمن")

# ==========================================
# 7. أوامر الترفيه (15 أمر)
# ==========================================

@bot.tree.command(name="xo", description="لعبة XO")
async def xo(i: discord.Interaction, member: discord.Member): await i.response.send_message(f"🎮 vs {member.mention}")

@bot.tree.command(name="dice", description="رمي النرد")
async def dice(i: discord.Interaction): await i.response.send_message(f"🎲 {random.randint(1,6)}")

@bot.tree.command(name="iq", description="قياس الذكاء")
async def iq(i: discord.Interaction, m: discord.Member=None): await i.response.send_message(f"🧠 {random.randint(1,200)}%")

@bot.tree.command(name="love", description="نسبة الحب")
async def love(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"❤️ {random.randint(1,100)}%")

@bot.tree.command(name="hack", description="اختراق وهمي")
async def hack(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"💻 Hacking {m.name}...")

@bot.tree.command(name="slap", description="صفعة")
async def slap(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"🖐️ Slap {m.name}")

@bot.tree.command(name="kill", description="قتل")
async def kill(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"⚔️ Dead {m.name}")

@bot.tree.command(name="hug", description="عناق")
async def hug(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"🤗 Hug {m.name}")

@bot.tree.command(name="punch", description="لكمة")
async def punch(i: discord.Interaction, m: discord.Member): await i.response.send_message("👊 Punch!")

@bot.tree.command(name="joke", description="نكتة")
async def joke(i: discord.Interaction): await i.response.send_message("مرة واحد...")

@bot.tree.command(name="slots", description="لعبة الحظ")
async def slots(i: discord.Interaction): await i.response.send_message("🎰 🍎|🍎|💎")

@bot.tree.command(name="ship", description="تنسيق عضوين")
async def ship(i: discord.Interaction, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 {random.randint(1,100)}%")

@bot.tree.command(name="hot", description="قياس الحرارة")
async def hot(i: discord.Interaction, m: discord.Member=None): await i.response.send_message(f"🔥 {random.randint(1,100)}%")

@bot.tree.command(name="choose", description="الاختيار بين شيئين")
async def choose(i: discord.Interaction, a: str, b: str): await i.response.send_message(f"🤔 {random.choice([a,b])}")

@bot.tree.command(name="wanted", description="مطلوب للعدالة")
async def wanted(i: discord.Interaction, m: discord.Member=None): await i.response.send_message("⚠️ Wanted!")

# ==========================================
# 8. أوامر المعلومات (15 أمر)
# ==========================================

@bot.tree.command(name="user", description="معلومات الحساب")
async def user_info(i: discord.Interaction, m: discord.Member=None):
    m = m or i.user; await i.response.send_message(f"👤 {m.name}")

@bot.tree.command(name="server", description="معلومات السيرفر")
async def server_info(i: discord.Interaction):
    await i.response.send_message(f"🏰 {i.guild.name}")

@bot.tree.command(name="avatar", description="الصورة الشخصية")
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
async def math(i: discord.Interaction, x: int, y: int): await i.response.send_message(f"🔢 {x+y}")

@bot.tree.command(name="say", description="جعل البوت يقول شيئاً")
async def say(i: discord.Interaction, text: str): await i.channel.send(text); await i.response.send_message("Done", ephemeral=True)

@bot.tree.command(name="invite", description="رابط إضافة البوت")
async def invite(i: discord.Interaction):
    link = "https://discord.com/oauth2/authorize?client_id=1495807245856804976&permissions=8&integration_type=0&scope=bot+applications.commands"
    await i.response.send_message(f"🔗 {link}")

@bot.tree.command(name="perms", description="صلاحياتي")
async def perms(i: discord.Interaction): await i.response.send_message("✅ جاهز")

# ==========================================
# 9. التشغيل
# ==========================================

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ NO TOKEN FOUND")
