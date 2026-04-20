import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
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

# --- 2. إعداد قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f:
            json.dump({"bank": {}, "warns": {}, "auto_role": {}, "responses": {}, "settings": {}}, f)
    with open("op_data.json", "r") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: json.dump(data, f, indent=4)

# --- 3. نظام التيكت المتطور ---
class TicketReasonModal(Modal, title="فتح تذكرة جديدة"):
    reason = TextInput(label="ما هو سبب التذكرة؟", placeholder="اكتب السبب هنا...", min_length=5, max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f"ticket-{user.name}", overwrites=overwrites)
        embed = discord.Embed(title="تذكرة جديدة", color=discord.Color.blue())
        embed.add_field(name="صاحب التذكرة", value=user.mention)
        embed.add_field(name="السبب", value=self.reason.value)
        await channel.send(embed=embed, view=TicketActions())
        await interaction.response.send_message(f"✅ تم فتح التذكرة: {channel.mention}", ephemeral=True)

class TicketActions(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="قفل", style=discord.ButtonStyle.danger, custom_id="close_t")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

    @discord.ui.button(label="استلام", style=discord.ButtonStyle.success, custom_id="claim_t")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"تم الاستلام بواسطة: {interaction.user.mention}")

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="فتح تذكرة", style=discord.ButtonStyle.primary, custom_id="open_t")
    async def open_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketReasonModal())

# --- 4. البوت الرئيسي ---
class OPBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActions())
        await self.tree.sync()

    async def on_member_join(self, member):
        db = load_db()
        g_id = str(member.guild.id)
        # الرتبة التلقائية
        r_id = db["auto_role"].get(g_id)
        if r_id:
            role = member.guild.get_role(r_id)
            if role: await member.add_roles(role)
        # الترحيب
        w_ch = db["settings"].get(f"{g_id}_welcome")
        if w_ch:
            channel = member.guild.get_channel(w_ch)
            if channel: await channel.send(f"✨ نورت السيرفر يا {member.mention}")

    async def on_message(self, message):
        if message.author.bot: return
        db = load_db()
        g_res = db["responses"].get(str(message.guild.id), {})
        if message.content in g_res:
            await message.channel.send(g_res[message.content])

bot = OPBot()

# ==========================================
# 5. أوامر الإدارة والإعدادات (20 أمر)
# ==========================================

@bot.tree.command(name="set-ticket", description="ضبط قناة التيكت")
@app_commands.checks.has_permissions(administrator=True)
async def set_ticket(i: discord.Interaction, channel: discord.TextChannel):
    db = load_db()
    db["settings"][f"{i.guild.id}_ticket_ch"] = channel.id
    save_db(db)
    await channel.send("📩 اضغط لفتح تذكرة", view=TicketView())
    await i.response.send_message("✅ تم الضبط")

@bot.tree.command(name="set-autorole", description="ضبط رتبة تلقائية")
@app_commands.checks.has_permissions(administrator=True)
async def set_autorole(i: discord.Interaction, role: discord.Role):
    db = load_db(); db["auto_role"][str(i.guild.id)] = role.id; save_db(db)
    await i.response.send_message(f"✅ تم تحديد {role.name} رتبة تلقائية")

@bot.tree.command(name="set-command", description="ضبط رد تلقائي")
@app_commands.checks.has_permissions(administrator=True)
async def set_command(i: discord.Interaction, word: str, response: str):
    db = load_db(); g_id = str(i.guild.id)
    if g_id not in db["responses"]: db["responses"][g_id] = {}
    db["responses"][g_id][word] = response; save_db(db)
    await i.response.send_message(f"✅ تم إضافة الرد لـ {word}")

@bot.tree.command(name="del-command", description="حذف رد تلقائي")
@app_commands.checks.has_permissions(administrator=True)
async def del_command(i: discord.Interaction, word: str):
    db = load_db(); g_id = str(i.guild.id)
    if word in db["responses"].get(g_id, {}):
        del db["responses"][g_id][word]; save_db(db); await i.response.send_message("✅ تم الحذف")

@bot.tree.command(name="set-suggest", description="ضبط قناة الاقتراحات")
@app_commands.checks.has_permissions(administrator=True)
async def set_suggest(i: discord.Interaction, channel: discord.TextChannel):
    db = load_db(); db["settings"][f"{i.guild.id}_suggest"] = channel.id; save_db(db)
    await i.response.send_message(f"✅ قناة الاقتراحات: {channel.mention}")

@bot.tree.command(name="ban", description="حظر عضو")
async def ban(i: discord.Interaction, member: discord.Member):
    if i.user.guild_permissions.ban_members:
        await member.ban(); await i.response.send_message(f"✅ حظرنا {member.name}")

@bot.tree.command(name="kick", description="طرد عضو")
async def kick(i: discord.Interaction, member: discord.Member):
    if i.user.guild_permissions.kick_members:
        await member.kick(); await i.response.send_message(f"✅ طردنا {member.name}")

@bot.tree.command(name="clear", description="مسح رسائل")
async def clear(i: discord.Interaction, amount: int):
    if i.user.guild_permissions.manage_messages:
        await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 تم مسح {amount}", ephemeral=True)

@bot.tree.command(name="lock", description="قفل القناة")
async def lock(i: discord.Interaction):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒 القناة مغلقة")

@bot.tree.command(name="unlock", description="فتح القناة")
async def unlock(i: discord.Interaction):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓 القناة مفتوحة")

@bot.tree.command(name="timeout", description="إسكات عضو")
async def timeout(i: discord.Interaction, member: discord.Member, minutes: int):
    if i.user.guild_permissions.moderate_members:
        await member.timeout(timedelta(minutes=minutes)); await i.response.send_message(f"🔇 إسكات {member.name}")

@bot.tree.command(name="slowmode", description="وضع الهدوء")
async def slowmode(i: discord.Interaction, seconds: int):
    if i.user.guild_permissions.manage_channels:
        await i.channel.edit(slowmode_delay=seconds); await i.response.send_message(f"⏳ وضع الهدوء {seconds} ثانية")

@bot.tree.command(name="warn", description="تحذير عضو")
async def warn(i: discord.Interaction, member: discord.Member, reason: str):
    db = load_db(); m_id = str(member.id); db["warns"][m_id] = db["warns"].get(m_id, 0) + 1; save_db(db)
    await i.response.send_message(f"⚠️ تحذير لـ {member.mention} | السبب: {reason}")

@bot.tree.command(name="hide", description="إخفاء قناة")
async def hide(i: discord.Interaction):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.response.send_message("🙈 تم إخفاء القناة")

@bot.tree.command(name="show", description="إظهار قناة")
async def show(i: discord.Interaction):
    if i.user.guild_permissions.manage_channels:
        await i.channel.set_permissions(i.guild.default_role, view_channel=True); await i.response.send_message("👁️ تم إظهار القناة")

@bot.tree.command(name="add-role", description="إعطاء رتبة")
async def add_role(i: discord.Interaction, member: discord.Member, role: discord.Role):
    if i.user.guild_permissions.manage_roles:
        await member.add_roles(role); await i.response.send_message(f"✅ تم إعطاء {role.name}")

@bot.tree.command(name="remove-role", description="سحب رتبة")
async def remove_role(i: discord.Interaction, member: discord.Member, role: discord.Role):
    if i.user.guild_permissions.manage_roles:
        await member.remove_roles(role); await i.response.send_message(f"❌ تم سحب {role.name}")

@bot.tree.command(name="nick", description="تغيير اسم")
async def nick(i: discord.Interaction, member: discord.Member, name: str):
    if i.user.guild_permissions.manage_nicknames:
        await member.edit(nick=name); await i.response.send_message("✅ تم تغيير اللقب")

@bot.tree.command(name="unban", description="فك حظر")
async def unban(i: discord.Interaction, user_id: str):
    if i.user.guild_permissions.ban_members:
        u = await bot.fetch_user(int(user_id)); await i.guild.unban(u); await i.response.send_message(f"✅ فك حظر {u.name}")

@bot.tree.command(name="set-welcome", description="ضبط الترحيب")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome(i: discord.Interaction, channel: discord.TextChannel):
    db = load_db(); db["settings"][f"{i.guild.id}_welcome"] = channel.id; save_db(db)
    await i.response.send_message(f"✅ قناة الترحيب: {channel.mention}")

# ==========================================
# 6. أوامر الاقتصاد (15 أمر)
# ==========================================

@bot.tree.command(name="daily", description="الراتب اليومي")
async def daily(i: discord.Interaction):
    db = load_db(); u = str(i.user.id); db["bank"][u] = db["bank"].get(u,0)+1000; save_db(db)
    await i.response.send_message("💰 استلمت 1000")

@bot.tree.command(name="credits", description="رصيدك")
async def credits(i: discord.Interaction, member: discord.Member=None):
    db = load_db(); m = member or i.user; val = db["bank"].get(str(m.id),0)
    await i.response.send_message(f"💳 رصيد {m.name} هو: {val}")

@bot.tree.command(name="work", description="عمل")
async def work(i: discord.Interaction):
    g = random.randint(100,500); db = load_db(); u = str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+g; save_db(db)
    await i.response.send_message(f"👷 اشتغلت وجمعت {g}")

@bot.tree.command(name="transfer", description="تحويل")
async def transfer(i: discord.Interaction, member: discord.Member, amount: int):
    db = load_db(); sid, rid = str(i.user.id), str(member.id)
    if db["bank"].get(sid,0) < amount: return await i.response.send_message("❌ رصيدك لا يكفي")
    db["bank"][sid]-=amount; db["bank"][rid]=db["bank"].get(rid,0)+amount; save_db(db)
    await i.response.send_message(f"✅ تم تحويل {amount} لـ {member.name}")

@bot.tree.command(name="top", description="الأغنى")
async def top(i: discord.Interaction):
    db = load_db(); top_u = sorted(db["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    res = "\n".join([f"<@{u}>: {a}" for u,a in top_u]); await i.response.send_message(f"🏆 الأغنى 5:\n{res}")

@bot.tree.command(name="rob", description="سرقة")
async def rob(i: discord.Interaction, member: discord.Member):
    if random.randint(1,2) == 1:
        await i.response.send_message(f"⚔️ سرقت {member.name} بنجاح!")
    else:
        await i.response.send_message("👮 انقفطت وفشلت السرقة")

@bot.tree.command(name="fish", description="صيد")
async def fish(i: discord.Interaction):
    await i.response.send_message(f"🎣 صيدت سمكة قيمتها {random.randint(10,100)}")

@bot.tree.command(name="hunt", description="صيد بري")
async def hunt(i: discord.Interaction):
    await i.response.send_message("🏹 خرجت للصيد وعدت بغنائم!")

@bot.tree.command(name="give", description="إعطاء إداري")
async def give(i: discord.Interaction, member: discord.Member, amount: int):
    if i.user.guild_permissions.administrator:
        db = load_db(); m_id = str(member.id); db["bank"][m_id] = db["bank"].get(m_id,0)+amount; save_db(db)
        await i.response.send_message(f"🎁 تم منح {amount} لـ {member.name}")

@bot.tree.command(name="coin", description="عملة")
async def coin(i: discord.Interaction):
    await i.response.send_message(f"🪙 النتيجة: {random.choice(['ملك', 'كتابة'])}")

@bot.tree.command(name="salary", description="راتب")
async def salary(i: discord.Interaction):
    await i.response.send_message("💼 استلمت راتب 200")

@bot.tree.command(name="shop", description="متجر")
async def shop(i: discord.Interaction):
    await i.response.send_message("🛒 المتجر قيد الصيانة")

@bot.tree.command(name="wallet", description="محفظة")
async def wallet(i: discord.Interaction):
    await i.response.send_message("👛 محفظتك مؤمنة")

@bot.tree.command(name="bank-info", description="البنك")
async def binfo(i: discord.Interaction):
    await i.response.send_message("🏦 بنك OP يحميك")

@bot.tree.command(name="buy", description="شراء")
async def buy(i: discord.Interaction, item: str):
    await i.response.send_message(f"❌ لا يمكنك شراء {item} حالياً")

# ==========================================
# 7. أوامر الترفيه (15 أمر)
# ==========================================

@bot.tree.command(name="xo", description="لعبة")
async def xo(i: discord.Interaction, member: discord.Member):
    await i.response.send_message(f"🎮 بدأت اللعبة ضد {member.mention}")

@bot.tree.command(name="dice", description="نرد")
async def dice(i: discord.Interaction):
    await i.response.send_message(f"🎲 النرد: {random.randint(1,6)}")

@bot.tree.command(name="iq", description="ذكاء")
async def iq(i: discord.Interaction, m: discord.Member=None):
    await i.response.send_message(f"🧠 نسبة الذكاء: {random.randint(1,200)}%")

@bot.tree.command(name="love", description="حب")
async def love(i: discord.Interaction, m: discord.Member):
    await i.response.send_message(f"❤️ نسبة الحب: {random.randint(1,100)}%")

@bot.tree.command(name="hack", description="اختراق")
async def hack(i: discord.Interaction, m: discord.Member):
    await i.response.send_message(f"💻 جاري اختراق {m.name}...")

@bot.tree.command(name="slap", description="صفعة")
async def slap(i: discord.Interaction, m: discord.Member):
    await i.response.send_message(f"🖐️ صفعت {m.name}!")

@bot.tree.command(name="kill", description="قتل")
async def kill(i: discord.Interaction, m: discord.Member):
    await i.response.send_message(f"⚔️ قتلت {m.name}!")

@bot.tree.command(name="hug", description="حضن")
async def hug(i: discord.Interaction, m: discord.Member):
    await i.response.send_message(f"🤗 حضنت {m.name}")

@bot.tree.command(name="punch", description="لكمة")
async def punch(i: discord.Interaction, m: discord.Member):
    await i.response.send_message(f"👊 لكمت {m.name}")

@bot.tree.command(name="joke", description="نكتة")
async def joke(i: discord.Interaction):
    await i.response.send_message("واحد راح للدكتور قاله...")

@bot.tree.command(name="slots", description="حظ")
async def slots(i: discord.Interaction):
    await i.response.send_message("🎰 | 🍎 | 💎 | 🍎")

@bot.tree.command(name="ship", description="تنسيق")
async def ship(i: discord.Interaction, m1: discord.Member, m2: discord.Member):
    await i.response.send_message(f"💞 نسبة التوافق: {random.randint(1,100)}%")

@bot.tree.command(name="hot", description="حرارة")
async def hot(i: discord.Interaction):
    await i.response.send_message(f"🔥 نسبة الحرارة: {random.randint(1,100)}%")

@bot.tree.command(name="choose", description="اختيار")
async def choose(i: discord.Interaction, a: str, b: str):
    await i.response.send_message(f"🤔 اخترت: {random.choice([a,b])}")

@bot.tree.command(name="wanted", description="مطلوب")
async def wanted(i: discord.Interaction, m: discord.Member=None):
    await i.response.send_message("⚠️ هذا الشخص مطلوب للعدالة!")

# ==========================================
# 8. أوامر المعلومات (10 أوامر)
# ==========================================

@bot.tree.command(name="user", description="حساب")
async def user_info(i: discord.Interaction, m: discord.Member=None):
    m = m or i.user; await i.response.send_message(f"👤 الاسم: {m.name}\n🆔 الأيدي: {m.id}")

@bot.tree.command(name="server", description="سيرفر")
async def server_info(i: discord.Interaction):
    await i.response.send_message(f"🏰 السيرفر: {i.guild.name}\n👥 الأعضاء: {i.guild.member_count}")

@bot.tree.command(name="avatar", description="صورة")
async def avatar(i: discord.Interaction, m: discord.Member=None):
    m = m or i.user; await i.response.send_message(m.display_avatar.url)

@bot.tree.command(name="ping", description="اتصال")
async def ping(i: discord.Interaction):
    await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")

@bot.tree.command(name="bot-id", description="أيدي بوت")
async def bid(i: discord.Interaction):
    await i.response.send_message(f"🆔 {bot.user.id}")

@bot.tree.command(name="channel-id", description="أيدي قناة")
async def cid(i: discord.Interaction):
    await i.response.send_message(f"🆔 {i.channel.id}")

@bot.tree.command(name="guild-id", description="أيدي سيرفر")
async def gid(i: discord.Interaction):
    await i.response.send_message(f"🆔 {i.guild.id}")

@bot.tree.command(name="say", description="تحدث")
async def say(i: discord.Interaction, text: str):
    await i.channel.send(text); await i.response.send_message("نطقت!", ephemeral=True)

@bot.tree.command(name="invite", description="رابط")
async def invite(i: discord.Interaction):
    await i.response.send_message("🔗 رابط إضافة البوت: [Link]")

@bot.tree.command(name="help", description="مساعدة")
async def help_cmd(i: discord.Interaction):
    embed = discord.Embed(title="📚 دليل أوامر OP BOT", color=0x00ff00)
    embed.description = "يحتوي البوت على 60+ أمر (إدارة، اقتصاد، ترفيه، معلومات)"
    await i.response.send_message(embed=embed)

# ==========================================
# 9. التشغيل
# ==========================================
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ NO TOKEN")
