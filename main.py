import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import random, asyncio, json, os, time
from datetime import datetime, timedelta
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

# --- 2. قاعدة البيانات (تم تحديث المفاتيح للأنظمة الجديدة) ---
def load_db():
    if not os.path.exists("op_data.json"):
        with open("op_data.json", "w") as f:
            json.dump({
                "bank": {}, "warns": {}, "auto_role": {}, 
                "responses": {}, "settings": {}, "daily_cooldown": {},
                "levels": {}, "security": {}
            }, f)
    with open("op_data.json", "r") as f: return json.load(f)

def save_db(data):
    with open("op_data.json", "w") as f: json.dump(data, f, indent=4)

# --- 3. أنظمة التفاعل (تيكت) ---
class TicketReasonModal(Modal, title="فتح تذكرة جديدة"):
    reason = TextInput(label="سبب التذكرة؟", placeholder="اكتب السبب هنا...", min_length=5)
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)
        await channel.send(f"مرحباً {interaction.user.mention}، سيتم الرد عليك قريباً.\nالسبب: {self.reason.value}", view=TicketActions())
        await interaction.response.send_message(f"✅ تم فتح تذكرتك: {channel.mention}", ephemeral=True)

class TicketActions(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="قفل", style=discord.ButtonStyle.danger, custom_id="close_t")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة", style=discord.ButtonStyle.primary, custom_id="open_t")
    async def open_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketReasonModal())

# --- 4. فئة البوت والأحداث ---
class OPBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(TicketActions())
        await self.tree.sync()

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name=f"/help | {len(self.guilds)} Servers"))
        print(f"Logged in as {self.user}")

    async def on_member_join(self, member):
        db = load_db(); g_id = str(member.guild.id)
        role_id = db["auto_role"].get(g_id)
        if role_id:
            role = member.guild.get_role(role_id)
            if role: await member.add_roles(role)
        
        welcome_ch_id = db["settings"].get(f"{g_id}_welcome")
        if welcome_ch_id:
            channel = member.guild.get_channel(welcome_ch_id)
            if channel:
                embed = discord.Embed(title="عضو جديد وصل!", description=f"نورت السيرفر يا {member.mention}!\nأنت العضو رقم **{member.guild.member_count}**", color=0x00ff00)
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)

    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        db = load_db()
        g_id, u_id = str(message.guild.id), str(message.author.id)

        # حماية: سبام وروابط
        if db["security"].get(g_id, False):
            if "http" in message.content or "discord.gg" in message.content:
                if not message.author.guild_permissions.manage_messages:
                    await message.delete()
                    return await message.channel.send(f"⚠️ {message.author.mention} ممنوع الروابط!", delete_after=5)

        # نظام ليفلات تلقائي
        if g_id not in db["levels"]: db["levels"][g_id] = {}
        if u_id not in db["levels"][g_id]: db["levels"][g_id][u_id] = {"xp": 0, "level": 0}
        db["levels"][g_id][u_id]["xp"] += random.randint(5, 15)
        if db["levels"][g_id][u_id]["xp"] >= (db["levels"][g_id][u_id]["level"] + 1) * 100:
            db["levels"][g_id][u_id]["level"] += 1
            db["levels"][g_id][u_id]["xp"] = 0
            try: await message.channel.send(f"🆙 {message.author.mention} مبروك ليفل **{db['levels'][g_id][u_id]['level']}**!")
            except: pass
        save_db(db)

        # الردود التلقائية (نفس نظامك القديم)
        replies = db["responses"].get(g_id, {})
        if message.content in replies:
            await message.channel.send(replies[message.content])

    # --- أحداث اللوج (Logs) ---
    async def on_message_delete(self, message):
        db = load_db(); log_id = db["settings"].get(f"{message.guild.id}_logs")
        if log_id:
            ch = message.guild.get_channel(log_id)
            if ch:
                emb = discord.Embed(title="🗑️ حذف رسالة", color=discord.Color.red())
                emb.add_field(name="المرسل", value=message.author.mention)
                emb.add_field(name="المحتوى", value=message.content or "صورة/ملف")
                await ch.send(embed=emb)

    async def on_guild_role_create(self, role):
        db = load_db(); log_id = db["settings"].get(f"{role.guild.id}_logs")
        if log_id:
            ch = role.guild.get_channel(log_id)
            if ch: await ch.send(f"🆕 رتبة جديدة: **{role.name}**")

bot = OPBot()

# ==========================================
# 5. أوامر الإدارة (15 أمر - القديم + الجديد)
# ==========================================

@bot.tree.command(name="set-welcome", description="تحديد روم الترحيب")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome(i: discord.Interaction, channel: discord.TextChannel):
    db = load_db(); db["settings"][f"{i.guild.id}_welcome"] = channel.id; save_db(db)
    await i.response.send_message(f"✅ تم تحديد {channel.mention}")

@bot.tree.command(name="set-autorole", description="رتبة تلقائية")
@app_commands.checks.has_permissions(manage_roles=True)
async def set_autorole(i: discord.Interaction, role: discord.Role):
    db = load_db(); db["auto_role"][str(i.guild.id)] = role.id; save_db(db)
    await i.response.send_message(f"✅ الرتبة التلقائية هي: {role.name}")

@bot.tree.command(name="set-logs", description="تحديد روم اللوج")
@app_commands.checks.has_permissions(administrator=True)
async def set_logs(i: discord.Interaction, channel: discord.TextChannel):
    db = load_db(); db["settings"][f"{i.guild.id}_logs"] = channel.id; save_db(db)
    await i.response.send_message(f"✅ تم ضبط اللوج في {channel.mention}")

@bot.tree.command(name="add-security", description="تفعيل الحماية")
@app_commands.checks.has_permissions(administrator=True)
async def add_sec(i: discord.Interaction):
    db = load_db(); db["security"][str(i.guild.id)] = True; save_db(db)
    await i.response.send_message("🛡️ تم تفعيل الحماية.")

@bot.tree.command(name="remove-security", description="إلغاء الحماية")
@app_commands.checks.has_permissions(administrator=True)
async def rem_sec(i: discord.Interaction):
    db = load_db(); db["security"][str(i.guild.id)] = False; save_db(db)
    await i.response.send_message("🔓 تم إيقاف الحماية.")

@bot.tree.command(name="kick")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(i: discord.Interaction, member: discord.Member, reason: str="غير محدد"):
    try: await member.send(f"👞 تم طردك من {i.guild.name} | السبب: {reason}")
    except: pass
    await member.kick(); await i.response.send_message(f"✅ طردنا {member.name}")

@bot.tree.command(name="ban")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(i: discord.Interaction, member: discord.Member, reason: str="غير محدد"):
    try: await member.send(f"🚫 تم حظرك من {i.guild.name} | السبب: {reason}")
    except: pass
    await member.ban(); await i.response.send_message(f"✅ حظرنا {member.name}")

@bot.tree.command(name="unban")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(i: discord.Interaction, user_id: str):
    user = await bot.fetch_user(int(user_id)); await i.guild.unban(user)
    await i.response.send_message(f"✅ فك الحظر عن {user.name}")

@bot.tree.command(name="warn")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(i: discord.Interaction, member: discord.Member, reason: str):
    db = load_db(); m_id = str(member.id); db["warns"][m_id] = db["warns"].get(m_id, 0) + 1; save_db(db)
    await i.response.send_message(f"⚠️ تحذير لـ {member.mention}: {reason}")

@bot.tree.command(name="show-warns")
async def show_warns(i: discord.Interaction, member: discord.Member):
    db = load_db(); count = db["warns"].get(str(member.id), 0)
    await i.response.send_message(f"👤 {member.name} لديه {count} تحذير.")

@bot.tree.command(name="clear")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(i: discord.Interaction, amount: int):
    await i.channel.purge(limit=amount); await i.response.send_message(f"🧹 تم المسح.", ephemeral=True)

@bot.tree.command(name="lock")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=False); await i.response.send_message("🔒")

@bot.tree.command(name="unlock")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(i: discord.Interaction):
    await i.channel.set_permissions(i.guild.default_role, send_messages=True); await i.response.send_message("🔓")

@bot.tree.command(name="set-reply")
@app_commands.checks.has_permissions(manage_messages=True)
async def set_reply(i: discord.Interaction, word: str, reply: str):
    db = load_db(); g_id = str(i.guild.id)
    if g_id not in db["responses"]: db["responses"][g_id] = {}
    db["responses"][g_id][word] = reply; save_db(db); await i.response.send_message("✅ تم الإضافة")

@bot.tree.command(name="timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(i: discord.Interaction, member: discord.Member, minutes: int, reason: str="غير محدد"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    try: await member.send(f"🔇 تم إسكاتك في {i.guild.name} لمدة {minutes}د")
    except: pass
    await i.response.send_message(f"✅ تم إسكات {member.name}")

# ==========================================
# 6. أوامر الاقتصاد (15 أمر - القديم + المطور)
# ==========================================

@bot.tree.command(name="daily")
async def daily(i: discord.Interaction):
    db = load_db(); u = str(i.user.id); now = time.time()
    last = db["daily_cooldown"].get(u, 0)
    if now - last < 86400:
        return await i.response.send_message(f"❌ انتظر `{str(timedelta(seconds=int(86400-(now-last))))}`", ephemeral=True)
    db["bank"][u] = db["bank"].get(u,0)+1000; db["daily_cooldown"][u] = now; save_db(db)
    await i.response.send_message("💰 تم استلام 1000")

@bot.tree.command(name="credits")
async def credits(i: discord.Interaction, m: discord.Member=None):
    db = load_db(); m = m or i.user; await i.response.send_message(f"💳 {m.name}: {db['bank'].get(str(m.id),0)}")

@bot.tree.command(name="work")
async def work(i: discord.Interaction):
    g = random.randint(100,500); db = load_db(); u = str(i.user.id); db["bank"][u]=db["bank"].get(u,0)+g; save_db(db)
    await i.response.send_message(f"👷 ربحت {g}")

@bot.tree.command(name="transfer")
async def transfer(i: discord.Interaction, m: discord.Member, amount: int):
    db = load_db(); sid, rid = str(i.user.id), str(m.id)
    if db["bank"].get(sid,0) < amount: return await i.response.send_message("❌ رصيدك لا يكفي")
    db["bank"][sid]-=amount; db["bank"][rid]=db["bank"].get(rid,0)+amount; save_db(db)
    await i.response.send_message(f"✅ حولت {amount} لـ {m.name}")

@bot.tree.command(name="top")
async def top(i: discord.Interaction):
    db = load_db(); top_u = sorted(db["bank"].items(), key=lambda x:x[1], reverse=True)[:5]
    res = "\n".join([f"<@{u}>: {a}" for u,a in top_u]); await i.response.send_message(f"🏆 Top 5 Bank:\n{res}")

@bot.tree.command(name="top-levels")
async def top_levels(i: discord.Interaction):
    db = load_db(); g_id = str(i.guild.id)
    if g_id not in db["levels"]: return await i.response.send_message("لا بيانات.")
    top = sorted(db["levels"][g_id].items(), key=lambda x:x[1]['level'], reverse=True)[:5]
    res = "\n".join([f"<@{u}>: Lvl {d['level']}" for u,d in top])
    await i.response.send_message(f"🏆 Top 5 Levels:\n{res}")

@bot.tree.command(name="fish")
async def fish(i: discord.Interaction): await i.response.send_message(f"🎣 اصطدت سمكة بقيمة {random.randint(10,100)}")
@bot.tree.command(name="hunt")
async def hunt(i: discord.Interaction): await i.response.send_message("🏹 صيد موفق!")
@bot.tree.command(name="coin")
async def coin(i: discord.Interaction): await i.response.send_message(f"🪙 النتيجة: {random.choice(['ملك','كتابة'])}")
@bot.tree.command(name="give")
@app_commands.checks.has_permissions(administrator=True)
async def give(i: discord.Interaction, m: discord.Member, a: int):
    db = load_db(); db["bank"][str(m.id)]=db["bank"].get(str(m.id),0)+a; save_db(db); await i.response.send_message("🎁 تم المنح")
@bot.tree.command(name="salary")
async def salary(i: discord.Interaction): await i.response.send_message("💼 راتب إضافي +200")
@bot.tree.command(name="slots")
async def slots(i: discord.Interaction): await i.response.send_message("🎰 جرب حظك")
@bot.tree.command(name="rob")
async def rob(i: discord.Interaction, m: discord.Member):
    if random.randint(1,2)==1: await i.response.send_message(f"⚔️ سرقت {m.name} بنجاح!")
    else: await i.response.send_message("👮 الإمساك بك! فشلت السرقة")
@bot.tree.command(name="wallet")
async def wallet(i: discord.Interaction): await i.response.send_message("👛 محفظتك فارغة حالياً")
@bot.tree.command(name="shop")
async def shop(i: discord.Interaction): await i.response.send_message("🛒 المتجر قريباً")
@bot.tree.command(name="bank-info")
async def binfo(i: discord.Interaction): await i.response.send_message("🏦 بنك OP آمن 100%")

# ==========================================
# 7. أوامر الترفيه (15 أمر - القديم)
# ==========================================

@bot.tree.command(name="iq")
async def iq(i: discord.Interaction, m: discord.Member=None): await i.response.send_message(f"🧠 IQ: {random.randint(1,200)}%")
@bot.tree.command(name="hack")
async def hack(i: discord.Interaction, m: discord.Member):
    await i.response.send_message(f"💻 اختراق {m.name}..."); await asyncio.sleep(2)
    await i.edit_original_response(content="✅ تم الاختراق بنجاح!")
@bot.tree.command(name="ship")
async def ship(i: discord.Interaction, m1: discord.Member, m2: discord.Member): await i.response.send_message(f"💞 نسبة الحب: {random.randint(1,100)}%")
@bot.tree.command(name="slap")
async def slap(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"🖐️ كف خماسي لـ {m.name}")
@bot.tree.command(name="kill")
async def kill(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"⚔️ تم تصفية {m.name}")
@bot.tree.command(name="joke")
async def joke(i: discord.Interaction): await i.response.send_message("مرة واحد...")
@bot.tree.command(name="dice")
async def dice(i: discord.Interaction): await i.response.send_message(f"🎲 النتيجة: {random.randint(1,6)}")
@bot.tree.command(name="hug")
async def hug(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"🤗 حضن لـ {m.name}")
@bot.tree.command(name="punch")
async def punch(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"👊 لكمة لـ {m.name}")
@bot.tree.command(name="hot")
async def hot(i: discord.Interaction): await i.response.send_message(f"🔥 الحرارة: {random.randint(1,100)}%")
@bot.tree.command(name="choose")
async def choose(i: discord.Interaction, a: str, b: str): await i.response.send_message(f"🤔 أختار: {random.choice([a,b])}")
@bot.tree.command(name="wanted")
async def wanted(i: discord.Interaction, m: discord.Member=None): await i.response.send_message("⚠️ مطلوب للعدالة!")
@bot.tree.command(name="love")
async def love(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"❤️ يحبك بنسبة: {random.randint(1,100)}%")
@bot.tree.command(name="dance")
async def dance(i: discord.Interaction): await i.response.send_message("💃 أرقص!")
@bot.tree.command(name="xo")
async def xo(i: discord.Interaction, m: discord.Member): await i.response.send_message(f"🎮 تحدي XO مع {m.mention}")

# ==========================================
# 8. أوامر معلومات وعامة (15 أمر)
# ==========================================

@bot.tree.command(name="help")
async def help_cmd(i: discord.Interaction):
    emb = discord.Embed(title="قائمة أوامر OP BOT", color=0x00aaff)
    emb.add_field(name="🛡️ الإدارة", value="`ban`, `kick`, `timeout`, `set-logs`, `lock`, `security`...", inline=False)
    emb.add_field(name="💰 الاقتصاد", value="`daily`, `credits`, `transfer`, `top-levels`, `work`...", inline=False)
    emb.add_field(name="🎮 الترفيه", value="`iq`, `hack`, `ship`, `joke`, `kill`, `dice`...", inline=False)
    await i.response.send_message(embed=emb)

@bot.tree.command(name="ping")
async def ping(i: discord.Interaction): await i.response.send_message(f"🏓 {round(bot.latency*1000)}ms")
@bot.tree.command(name="user-info")
async def uinfo(i: discord.Interaction, m: discord.Member=None):
    m = m or i.user; await i.response.send_message(f"👤 {m.name} | ID: {m.id}")
@bot.tree.command(name="server")
async def server(i: discord.Interaction): await i.response.send_message(f"🏰 {i.guild.name}")
@bot.tree.command(name="avatar")
async def avatar(i: discord.Interaction, m: discord.Member=None):
    m = m or i.user; await i.response.send_message(m.display_avatar.url)
@bot.tree.command(name="suggest")
async def suggest(i: discord.Interaction, text: str):
    db = load_db(); ch_id = db["settings"].get(f"{i.guild.id}_suggest")
    if ch_id:
        ch = i.guild.get_channel(ch_id)
        msg = await ch.send(embed=discord.Embed(title="اقتراح جديد", description=text, color=0xffff00))
        await msg.add_reaction("✅"); await msg.add_reaction("❌")
        await i.response.send_message("✅ تم الإرسال.")
    else: await i.response.send_message("❌ حدد قناة الاقتراحات أولاً.")

@bot.tree.command(name="members")
async def mems(i: discord.Interaction): await i.response.send_message(f"👥 عدد الأعضاء: {i.guild.member_count}")
@bot.tree.command(name="uptime")
async def uptime(i: discord.Interaction): await i.response.send_message("🕒 البوت يعمل 24/7")
@bot.tree.command(name="bot-id")
async def bid(i: discord.Interaction): await i.response.send_message(bot.user.id)
@bot.tree.command(name="guild-id")
async def gid(i: discord.Interaction): await i.response.send_message(i.guild.id)
@bot.tree.command(name="channel-id")
async def cid(i: discord.Interaction): await i.response.send_message(i.channel.id)
@bot.tree.command(name="roles")
async def roles(i: discord.Interaction): await i.response.send_message(f"📜 عدد الرتب: {len(i.guild.roles)}")
@bot.tree.command(name="channels")
async def chans(i: discord.Interaction): await i.response.send_message(f"📁 عدد القنوات: {len(i.guild.channels)}")
@bot.tree.command(name="invite")
async def invite(i: discord.Interaction): await i.response.send_message("🔗 https://discord.com/api/oauth2/authorize...")
@bot.tree.command(name="say")
@app_commands.checks.has_permissions(manage_messages=True)
async def say(i: discord.Interaction, t: str): await i.channel.send(t); await i.response.send_message("تم", ephemeral=True)

# --- 9. التشغيل ---
if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
