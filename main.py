import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random, asyncio, json, os
from datetime import timedelta
from flask import Flask
from threading import Thread

# --- 1. نظام الـ Keep Alive لضمان العمل 24 ساعة ---
app = Flask('')
@app.route('/')
def home(): return "OP BOT IS ONLINE"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. إدارة قاعدة البيانات ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f:
            json.dump({"bank": {}, "warns": {}, "auto_role": {}, "responses": {}, "settings": {}}, f)
    with open("op_data.json", "r") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: json.dump(data, f, indent=4)

# --- 3. نظام التيكت المتطور ---
class TicketReasonModal(Modal, title="فتح تذكرة جديدة"):
    reason = TextInput(label="ما هو سبب التذكرة؟", placeholder="اكتب السبب هنا...", min_length=5)
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)
        embed = discord.Embed(title="تذكرة جديدة", description=f"صاحب التذكرة: {interaction.user.mention}\nالسبب: {self.reason.value}", color=0x00aaff)
        await channel.send(embed=embed, view=TicketActions())
        await interaction.response.send_message(f"✅ تم فتح تذكرتك: {channel.mention}", ephemeral=True)

class TicketActions(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="قفل التذكرة", style=discord.ButtonStyle.danger, custom_id="close_t")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("سيتم إغلاق التذكرة الآن...")
        await asyncio.sleep(2)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة", style=discord.ButtonStyle.primary, custom_id="open_t")
    async def open_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketReasonModal())

# --- 4. فئة البوت الأساسية ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActions())
        await self.tree.sync()

    async def on_ready(self):
        status = f"/help | {len(self.guilds)} سيرفر"
        await self.change_presence(activity=discord.Game(name=status))
        print(f"✅ تم تشغيل {self.user} بنجاح!")

    async def on_member_join(self, member):
        db = load_db(); g_id = str(member.guild.id)
        # نظام الرتبة التلقائية
        role_id = db["auto_role"].get(g_id)
        if role_id:
            role = member.guild.get_role(role_id)
            if role: await member.add_roles(role)

    async def on_message(self, message):
        if message.author.bot: return
        db = load_db()
        # نظام الردود التلقائية
        replies = db["responses"].get(str(message.guild.id), {})
        if message.content in replies:
            await message.channel.send(replies[message.content])

bot = OPBot()

# ==========================================
# 5. أوامر الإدارة (15 أمر)
# ==========================================

@bot.tree.command(name="set-ticket", description="إعداد التيكت")
@app_commands.checks.has_permissions(administrator=True)
async def set_ticket(i: discord.Interaction, channel: discord.TextChannel):
    msg = await channel.send("📬 لفتح تذكرة اضغط الزر بالأسفل", view=TicketView())
    db = load_db(); db["settings"][f"{i.guild.id}_tmsg"] = msg.id; save_db(db)
    await i.response.send_message("✅ تم تفعيل التيكت", ephemeral=True)

@bot.tree.command(name="remove-ticket", description="إزالة نظام التيكت")
@app_commands.checks.has_permissions(administrator=True)
async def remove_ticket(i: discord.Interaction, channel: discord.TextChannel):
    db = load_db(); msg_id = db["settings"].pop(f"{i.guild.id}_tmsg", None); save_db(db)
    if msg_id:
        try:
            msg = await channel.fetch_message(msg_id); await msg.delete()
        except: pass
    await i.response.send_message("✅ تم إزالة نظام التيكت.")

@bot.tree.command(name="set-autorole", description="تحديد الرتبة التلقائية للجدد")
@app_commands.checks.has_permissions(manage_roles=True)
async def set_autorole(i: discord.Interaction, role: discord.Role):
    db = load_db(); db["auto_role"][str(i.guild.id)] = role.id; save_db(db)
    await i.response.send_message(f"✅ تم ضبط `{role.name}` كرتبة تلقائية.")

@bot.tree.command(name="set-suggestion", description="تحديد قناة الاقتراحات")
@app_commands.checks.has_permissions(administrator=True)
async def set_suggest(i: discord.Interaction, channel: discord.TextChannel):
    db = load_db(); db["settings"][f"{i.guild.id}_suggest"] = channel.id; save_db(db)
    await i.response.send_message(f"✅ قناة الاقتراحات: {channel.mention}")

@bot.tree.command(name="remove-suggestion", description="إلغاء قناة الاقتراحات")
@app_commands.checks.has_permissions(administrator=True)
async def rem_suggest(i: discord.Interaction):
    db = load_db(); db["settings"].pop(f"{i.guild.id}_suggest", None); save_db(db)
    await i.response.send_message("✅ تم إلغاء نظام الاقتراحات.")

@bot.tree.command(name="set-reply", description="إضافة رد تلقائي")
@app_commands.checks.has_permissions(manage_messages=True)
async def set_reply(i: discord.Interaction, word: str, reply: str):
    db = load_db(); g_id = str(i.guild.id)
    if g_id not in db["responses"]: db["responses"][g_id] = {}
    db["responses"][g_id][word] = reply; save_db(db)
    await i.response.send_message(f"✅ تم إضافة الرد: `{word}` -> `{reply}`")

@bot.tree.command(name="remove-reply", description="حذف رد تلقائي")
@app_commands.checks.has_permissions(manage_messages=True)
async def rem_reply(i: discord.Interaction, word: str):
    db = load_db(); g_id = str(i.guild.id)
    if word in db["responses"].get(g_id, {}):
        del db["responses"][g_id][word]; save_db(db); await i.response.send_message("✅ تم الحذف")
    else: await i.response.send_message("❌ غير موجود")

@bot.tree.command(name="kick", description="طرد عضو")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, member: discord.Member):
    await member.kick(); await i.response.send_message(f"👞 تم طرد {member.name}")

@bot.tree.command(name="ban", description="حظر عضو")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member):
    await member.ban(); await i.response.send_message(f"🚫 تم حظر {member.name}")

@bot.tree.command(name="unban", description="فك حظر بالـ ID")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(i: discord.Interaction, user_id: str):
    user = await bot.fetch_user(int(user_id)); await i.guild.unban(user)
    await i.response.send_message(f"✅ فك حظر {user.name}")

@bot.tree.command(name="warn", description="تحذير عضو")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(i: discord.Interaction, member: discord.Member, reason: str):
    db = load_db(); m_id = str(member.id); db["warns"][m_id] = db["warns"].get(m_id, 0) + 1; save_db(db)
    await i.response.send_message(f"⚠️ تحذير لـ {member.mention} | السبب: {reason}")

@bot.tree.command(name="show-warns", description="عرض تحذيرات عضو")
@app_commands.checks.has_permissions(moderate_members=True)
async def show_warns(i: discord.Interaction, member: discord.Member):
    db = load_db(); count = db["warns"].get(str(member.id), 0)
    await i.response.send_message(f"👤 {member.name} لديه {count} تحذير.")

@bot.tree.command(name="remove-warns", description="تصفير تحذيرات الجميع")
@app_commands.checks.has_permissions(administrator=True)
async def remove_warns(i: discord.Interaction):
    db = load_db(); db["warns"] = {}; save_db(db)
    await i.response.send_message("✅ تم تصفير تحذيرات الجميع.")

@bot.tree.command(name="untimeout", description="إزالة إسكات")
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(i: discord.Interaction, member: discord.Member):
    await member.timeout(None); await i.response.send_message(f"🔊 تم فك إسكات {member.name}")

@bot.tree.command(name="clear", description="مسح الشات")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i: discord.Interaction, amount: int):
    await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 مسحت {amount}", ephemeral=True)

# ==========================================
# 6. أوامر الاقتصاد (15 أمر)
# ==========================================

@bot.tree.command(name="daily", description="راتب يومي")
async def daily(i: discord.Interaction):
    db = load_db(); u = str(i.user.id); db["bank"][u] = db["bank"].get(u,0)+1000; save_db(db)
    await i.response.send_message("💰 +1000 عملة")

@bot.tree.command(name="credits", description="رصيدك")
async def credits(i: discord.Interaction, m: discord.Member=None):
    db = load_db(); m = m or i.user; await i.response.send_message(f"💳 {m.name}: {db['bank'].get(str(m.id),0)}")

@bot.tree.command(name="work")
async def work(i: discord.Interaction):
    g = random.randint(100,500); db = load_db(); u = str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+g; save_db(db)
    await i.response.send_message(f"👷 ربحت {g}")

@bot.tree.command(name="rob")
async def rob(i: discord.Interaction, m: discord.Member):
    if random.randint(1,2)==1: await i.response.send_message("⚔️ نجحت السرقة!")
    else: await i.response.send_message("👮 أمسكتك الشرطة!")

@bot.tree.command(name="top")
async def top(i: discord.Interaction):
    db = load_db(); top_u = sorted(db["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    res = "\n".join([f"<@{u}>: {a}" for u,a in top_u]); await i.response.send_message(f"🏆 الأغنى:\n{res}")

@bot.tree.command(name="transfer")
async def transfer(i: discord.Interaction, m: discord.Member, amount: int):
    db = load_db(); sid, rid = str(i.user.id), str(m.id)
    if db["bank"].get(sid,0) < amount: return await i.response.send_message("❌")
    db["bank"][sid]-=amount; db["bank"][rid]=db["bank"].get(rid,0)+amount; save_db(db)
    await i.response.send_message(f"✅ حولت {amount} لـ {m.name}")

@bot.tree.command(name="fish")
async def fish(i: discord.Interaction): await i.response.send_message(f"🎣 صيدت بـ {random.randint(10,100)}")
@bot.tree.command(name="hunt")
async def hunt(i: discord.Interaction): await i.response.send_message("🏹 صيد موفق")
@bot.tree.command(name="coin")
async def coin(i: discord.Interaction): await i.response.send_message(f"🪙 {random.choice(['ملك','كتابة'])}")
@bot.tree.command(name="give")
@app_commands.checks.has_permissions(administrator=True)
async def give(i: discord.Interaction, m: discord.Member, a: int):
    db = load_db(); db["bank"][str(m.id)]=db["bank"].get(str(m.id),0)+a; save_db(db); await i.response.send_message("🎁")
@bot.tree.command(name="salary")
async def salary(i: discord.Interaction): await i.response.send_message("💼 +200")
@bot.tree.command(name="shop")
async def shop(i: discord.Interaction): await i.response.send_message("🛒 قريباً")
@bot.tree.command(name="wallet")
async def wallet(i: discord.Interaction): await i.response.send_message("👛")
@bot.tree.command(name="bank-info")
async def binfo(i: discord.Interaction): await i.response.send_message("🏦 بنك OP")
@bot.tree.command(name="slots")
async def slots(i: discord.Interaction): await i.response.send_message("🎰")

# ==========================================
# 7. أوامر الترفيه (15 أمر)
# ==========================================

@bot.tree.command(name="iq")
async def iq(i: discord.Interaction, m: discord.Member=None): await i.response.send_message(f"🧠 IQ: {random.randint(1,200)}%")
@bot.tree.command(name="hack")
async def hack(i: discord.Interaction, m: discord.Member):
    await i.response.send_message(f"💻 اختراق {m.name}..."); await asyncio.sleep(2)
    await i.edit_original_response(content="✅ تمت العملية بنجاح!")
@bot.tree.command(name="ship")
async def ship(i: discord.Interaction, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 {random.randint(1,100)}%")
@bot.tree.command(name="slap")
async def slap(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"🖐️ كف لـ {m.name}")
@bot.tree.command(name="kill")
async def kill(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"⚔️ قتلت {m.name}")
@bot.tree.command(name="joke")
async def joke(i: discord.Interaction): await i.response.send_message("مرة واحد...")
@bot.tree.command(name="hug")
async def hug(i: discord.Interaction, m: discord.Member): await i.response.send_message("🤗")
@bot.tree.command(name="punch")
async def punch(i: discord.Interaction, m: discord.Member): await i.response.send_message("👊")
@bot.tree.command(name="dice")
async def dice(i: discord.Interaction): await i.response.send_message(f"🎲 {random.randint(1,6)}")
@bot.tree.command(name="hot")
async def hot(i: discord.Interaction): await i.response.send_message(f"🔥 {random.randint(1,100)}%")
@bot.tree.command(name="choose")
async def choose(i: discord.Interaction, a: str, b: str): await i.response.send_message(f"🤔 اخترت {random.choice([a,b])}")
@bot.tree.command(name="wanted")
async def wanted(i: discord.Interaction, m: discord.Member=None): await i.response.send_message("⚠️ مطلوب!")
@bot.tree.command(name="love")
async def love(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"❤️ {random.randint(1,100)}%")
@bot.tree.command(name="dance")
async def dance(i: discord.Interaction): await i.response.send_message("💃")
@bot.tree.command(name="xo")
async def xo(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"🎮 تحدي {m.mention}")

# ==========================================
# 8. أوامر معلومات وعامة (15 أمر)
# ==========================================

@bot.tree.command(name="invite")
async def invite(i: discord.Interaction):
    # رابط الدعوة الذي طلبته
    link = "https://discord.com/oauth2/authorize?client_id=1495807245856804976&permissions=8&integration_type=0&scope=bot+applications.commands"
    await i.response.send_message(f"🔗 أضفني لسيرفرك من هنا:\n{link}")

@bot.tree.command(name="ping")
async def ping(i: discord.Interaction): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="user-info")
async def user_info(i: discord.Interaction, m: discord.Member=None):
    m = m or i.user; await i.response.send_message(f"👤 {m.name} | ID: {m.id}")
@bot.tree.command(name="server")
async def server(i: discord.Interaction): await i.response.send_message(f"🏰 {i.guild.name}")
@bot.tree.command(name="avatar")
async def avatar(i: discord.Interaction, m: discord.Member=None):
    m = m or i.user; await i.response.send_message(m.display_avatar.url)
@bot.tree.command(name="suggest", description="إرسال اقتراح")
async def suggest(i: discord.Interaction, text: str):
    db = load_db(); ch_id = db["settings"].get(f"{i.guild.id}_suggest")
    if ch_id:
        ch = i.guild.get_channel(ch_id)
        embed = discord.Embed(title="اقتراح جديد", description=text, color=0x00ff00)
        embed.set_author(name=i.user.name, icon_url=i.user.display_avatar.url)
        msg = await ch.send(embed=embed); await msg.add_reaction("✅"); await msg.add_reaction("❌")
        await i.response.send_message("✅ تم الإرسال.")
    else: await i.response.send_message("❌ قناة الاقتراحات غير محددة.")

@bot.tree.command(name="help")
async def help_cmd(i: discord.Interaction):
    await i.response.send_message(f"أنا في {len(bot.guilds)} سيرفر. استخدم / لرؤية الأوامر.")

@bot.tree.command(name="uptime")
async def uptime(i: discord.Interaction): await i.response.send_message("🕒 24/7")
@bot.tree.command(name="bot-id")
async def bid(i: discord.Interaction): await i.response.send_message(bot.user.id)
@bot.tree.command(name="channel-id")
async def cid(i: discord.Interaction): await i.response.send_message(i.channel.id)
@bot.tree.command(name="guild-id")
async def gid(i: discord.Interaction): await i.response.send_message(i.guild.id)
@bot.tree.command(name="roles")
async def roles(i: discord.Interaction): await i.response.send_message(f"{len(i.guild.roles)}")
@bot.tree.command(name="channels")
async def channels(i: discord.Interaction): await i.response.send_message(f"{len(i.guild.channels)}")
@bot.tree.command(name="members")
async def members(i: discord.Interaction): await i.response.send_message(f"{i.guild.member_count}")
@bot.tree.command(name="say")
@app_commands.checks.has_permissions(manage_messages=True)
async def say(i: discord.Interaction, t: str): await i.channel.send(t); await i.response.send_message("Done", ephemeral=True)

# --- 9. التشغيل ---
if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
