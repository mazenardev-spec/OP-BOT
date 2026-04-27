const { 
    Client, GatewayIntentBits, Partials, EmbedBuilder, 
    ActionRowBuilder, ButtonBuilder, ButtonStyle, 
    ModalBuilder, TextInputBuilder, TextInputStyle, 
    ChannelType, PermissionsBitField, ActivityType 
} = require('discord.js');
const fs = require('fs');
const path = require('path');
const { createCanvas, loadImage } = require('canvas');

// --- 1. إدارة قاعدة البيانات ---
const dbPath = './op_bot_db.json';
function loadDB() {
    if (!fs.existsSync(dbPath)) fs.writeFileSync(dbPath, JSON.stringify({ bank: {}, guilds: {} }));
    return JSON.parse(fs.readFileSync(dbPath, 'utf8'));
}
function saveDB(db) { fs.writeFileSync(dbPath, JSON.stringify(db, null, 4)); }
function getUser(db, uid) {
    if (!db.bank[uid]) db.bank[uid] = { w: 0, daily: 0 };
    return db.bank[uid];
}
function getGuild(db, gid) {
    if (!db.guilds[gid]) db.guilds[gid] = { log: null, wel: null, arole: null, ev_ch: null, replies: {}, lvls: {} };
    return db.guilds[gid];
}

const client = new Client({
    intents: [Object.keys(GatewayIntentBits).map(a => GatewayIntentBits[a])],
    partials: [Partials.Message, Partials.Channel, Partials.Reaction]
});

let evs = {}; 

// --- 2. تسجيل الأوامر (Slash Commands) ---
client.once('ready', async () => {
    console.log(`✅ ${client.user.tag} Online!`);
    
    const commands = [
        // الإدارة (25 أمر تقريباً)
        { name: 'ban', description: 'حظر عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'reason', type: 3 }] },
        { name: 'kick', description: 'طرد عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'reason', type: 3 }] },
        { name: 'timeout', description: 'إسكات عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'minutes', type: 4, required: true }] },
        { name: 'clear', description: 'مسح رسائل', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'lock', description: 'قفل القناة' },
        { name: 'unlock', description: 'فتح القناة' },
        { name: 'nuke', description: 'تصفير القناة' },
        { name: 'hide', description: 'إخفاء القناة' },
        { name: 'unhide', description: 'إظهار القناة' },
        { name: 'slowmode', description: 'وضع البطيء', options: [{ name: 'seconds', type: 4, required: true }] },
        { name: 'set-log', description: 'روم اللوق', options: [{ name: 'channel', type: 7, required: true }] },
        { name: 'set-welcome', description: 'روم الترحيب', options: [{ name: 'channel', type: 7, required: true }] },
        { name: 'set-autorole', description: 'رتبة تلقائية', options: [{ name: 'role', type: 8, required: true }] },
        { name: 'set-autoevent', description: 'روم الفعاليات', options: [{ name: 'channel', type: 7, required: true }] },
        { name: 'set-ticket', description: 'رسالة التيكت', options: [{ name: 'channel', type: 7, required: true }] },
        { name: 'role-add', description: 'إضافة رتبة', options: [{ name: 'user', type: 6, required: true }, { name: 'role', type: 8, required: true }] },
        { name: 'role-remove', description: 'سحب رتبة', options: [{ name: 'user', type: 6, required: true }, { name: 'role', type: 8, required: true }] },
        { name: 'nick', description: 'تغيير لقب', options: [{ name: 'user', type: 6, required: true }, { name: 'name', type: 3, required: true }] },
        { name: 'warn', description: 'تحذير عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'reason', type: 3 }] },
        { name: 'move', description: 'نقل صوتي', options: [{ name: 'user', type: 6, required: true }, { name: 'channel', type: 7, required: true }] },
        { name: 'vmute', description: 'ميوت صوتي', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'vunmute', description: 'فك ميوت صوتي', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'vkick', description: 'طرد من الصوت', options: [{ name: 'user', type: 6, required: true }] },

        // الاقتصاد (20 أمر تقريباً)
        { name: 'work', description: 'العمل لكسب المال' },
        { name: 'daily', description: 'الراتب اليومي' },
        { name: 'credits', description: 'رصيدك الحالي', options: [{ name: 'user', type: 6 }] },
        { name: 'top', description: 'قائمة الأغنياء' },
        { name: 'transfer', description: 'تحويل مبالغ', options: [{ name: 'user', type: 6, required: true }, { name: 'amount', type: 4, required: true }] },
        { name: 'miner', description: 'التنقيب' },
        { name: 'hunt', description: 'الصيد' },
        { name: 'fish', description: 'صيد السمك' },
        { name: 'beg', description: 'شحاتة' },
        { name: 'slots', description: 'لعبة السلوتس', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'coinflip', description: 'ملك أو كتابة', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'profile-money', description: 'البروفايل المالي' },

        // الترفيه والنظام (25 أمر تقريباً)
        { name: 'iq', description: 'نسبة الذكاء' },
        { name: 'love', description: 'نسبة الحب', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'avatar', description: 'صورة الحساب', options: [{ name: 'user', type: 6 }] },
        { name: 'ping', description: 'سرعة البوت' },
        { name: 'joke', description: 'نكتة' },
        { name: 'hack', description: 'اختراق وهمي', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'kill', description: 'تصفية عضو', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'slap', description: 'صفعة', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'hug', description: 'حضن', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'dice', description: 'نرد' },
        { name: 'user-info', description: 'معلومات حسابك' },
        { name: 'bot-stats', description: 'إحصائيات البوت' },
        { name: 'show-level', description: 'عرض مستواك' },
        { name: 'choose', description: 'اختيار عشوائي', options: [{ name: 'first', type: 3, required: true }, { name: 'second', type: 3, required: true }] },
        { name: 'meme', description: 'ميمز' },
        { name: 'game', description: 'اقتراح لعبة' },
        { name: 'ship', description: 'توافق بين شخصين', options: [{ name: 'user1', type: 6, required: true }, { name: 'user2', type: 6, required: true }] },
        { name: 'wanted', description: 'صورة مطلوب' },
        { name: 'punch', description: 'لكمة', options: [{ name: 'user', type: 6, required: true }] }
    ];

    await client.application.commands.set(commands);
    
    // نظام الحالة
    setInterval(() => client.user.setActivity(`OP BOT | ${client.guilds.cache.size} Servers`, { type: ActivityType.Watching }), 1800000);
});

// --- 3. معالجة الرسائل (لفل، ردود، فعاليات) ---
client.on('messageCreate', async msg => {
    if (msg.author.bot || !msg.guild) return;
    const db = loadDB();
    const gd = getGuild(db, msg.guild.id);

    // لفل
    if (!gd.lvls[msg.author.id]) gd.lvls[msg.author.id] = { xp: 0, lvl: 1 };
    gd.lvls[msg.author.id].xp += 10;
    if (gd.lvls[msg.author.id].xp >= gd.lvls[msg.author.id].lvl * 100) {
        gd.lvls[msg.author.id].lvl++;
        gd.lvls[msg.author.id].xp = 0;
        msg.channel.send(`🆙 نايس ${msg.author}! صرت لفل **${gd.lvls[msg.author.id].lvl}**`);
    }

    // رد تلقائي
    if (gd.replies[msg.content]) msg.channel.send(gd.replies[msg.content]);

    // حل فعالية
    if (evs[msg.guild.id] && msg.content === evs[msg.guild.id]) {
        delete evs[msg.guild.id];
        getUser(db, msg.author.id).w += 500;
        msg.reply("🎉 إجابة صحيحة! حصلت على 500 كريدت.");
    }
    saveDB(db);
});

// --- 4. نظام الترحيب بالصور ---
client.on('guildMemberAdd', async member => {
    const db = loadDB();
    const gd = getGuild(db, member.guild.id);

    // رتبة تلقائية
    if (gd.arole) {
        const role = member.guild.roles.cache.get(gd.arole);
        if (role) member.roles.add(role).catch(() => {});
    }

    // ترحيب
    if (gd.wel) {
        const channel = member.guild.channels.cache.get(gd.wel);
        if (channel) {
            const canvas = createCanvas(800, 450);
            const ctx = canvas.getContext('2d');

            // خلفية داكنة (Modern Dark)
            ctx.fillStyle = '#0c0c0c';
            ctx.fillRect(0, 0, 800, 450);

            // دائرة الصورة
            ctx.beginPath();
            ctx.arc(400, 150, 100, 0, Math.PI * 2, true);
            ctx.closePath();
            ctx.clip();

            try {
                const avatar = await loadImage(member.user.displayAvatarURL({ extension: 'png' }));
                ctx.drawImage(avatar, 300, 50, 200, 200);
            } catch (e) {}

            // نصوص
            ctx.fillStyle = '#4ade80';
            ctx.font = 'bold 40px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText("منور السيرفر يا بطل", 400, 300);
            ctx.fillStyle = '#ffffff';
            ctx.fillText(member.user.username, 400, 360);

            channel.send({ content: `منور يا ${member}`, files: [{ attachment: canvas.toBuffer(), name: 'welcome.png' }] });
        }
    }
});

// --- 5. تنفيذ أوامر Slash Commands ---
client.on('interactionCreate', async i => {
    if (!i.isChatInputCommand()) return;
    const db = loadDB();
    const { commandName, options, guild, user } = i;

    // أوامر الإدارة
    if (commandName === 'ban') {
        if (!i.member.permissions.has(PermissionsBitField.Flags.BanMembers)) return i.reply('❌ لا تملك صلاحية');
        const target = options.getMember('user');
        await target.ban();
        i.reply('✅ تم الحظر');
    }
    
    if (commandName === 'clear') {
        const amount = options.getInteger('amount');
        await i.channel.purge(amount);
        i.reply({ content: `🧹 تم مسح ${amount} رسالة`, ephemeral: true });
    }

    if (commandName === 'lock') {
        await i.channel.permissionOverwrites.edit(guild.id, { SendMessages: false });
        i.reply('🔒 تم قفل القناة');
    }

    // أوامر الاقتصاد
    if (commandName === 'work') {
        const r = Math.floor(Math.random() * 5000) + 500;
        getUser(db, user.id).w += r;
        saveDB(db);
        i.reply(`💼 عملت بجد وكسبت \`${r}\` كريدت!`);
    }

    if (commandName === 'credits') {
        const target = options.getUser('user') || user;
        i.reply(`💳 رصيد ${target.username}: \`${getUser(db, target.id).w}\``);
    }

    if (commandName === 'transfer') {
        const target = options.getUser('user');
        const amount = options.getInteger('amount');
        const u = getUser(db, user.id);
        if (u.w < amount) return i.reply('❌ رصيدك لا يكفي');
        u.w -= amount;
        getUser(db, target.id).w += amount;
        saveDB(db);
        i.reply(`✅ تم تحويل \`${amount}\` إلى ${target}`);
    }

    // أوامر الترفيه
    if (commandName === 'ping') i.reply(`🏓 البينج: \`${client.ws.ping}ms\``);
    
    if (commandName === 'iq') i.reply(`🧠 نسبة ذكائك: \`${Math.floor(Math.random()*100)}%\``);

    if (commandName === 'avatar') {
        const target = options.getUser('user') || user;
        i.reply(target.displayAvatarURL({ dynamic: true, size: 1024 }));
    }

    // إعدادات البوت
    if (commandName === 'set-log') {
        getGuild(db, guild.id).log = options.getChannel('channel').id;
        saveDB(db);
        i.reply('✅ تم ضبط اللوق');
    }

    if (commandName === 'set-ticket') {
        const ch = options.getChannel('channel');
        const row = new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('open_t').setLabel('فتح تذكرة 📩').setStyle(ButtonStyle.Success));
        await ch.send({ content: '📩 قسم الدعم الفني: اضغط لفتح تذكرة', components: [row] });
        i.reply('✅ تم إرسال رسالة التيكت');
    }
});

// --- 6. نظام التيكت (أزرار) ---
client.on('interactionCreate', async i => {
    if (i.isButton() && i.customId === 'open_t') {
        const modal = new ModalBuilder().setCustomId('t_modal').setTitle('فتح تذكرة دعم');
        const input = new TextInputBuilder().setCustomId('reason').setLabel('سبب التذكرة').setStyle(TextInputStyle.Paragraph).setRequired(true);
        modal.addComponents(new ActionRowBuilder().addComponents(input));
        await i.showModal(modal);
    }

    if (i.isModalSubmit() && i.customId === 't_modal') {
        const reason = i.fields.getTextInputValue('reason');
        const ch = await i.guild.channels.create({
            name: `ticket-${i.user.username}`,
            type: ChannelType.GuildText,
            permissionOverwrites: [
                { id: i.guild.id, deny: [PermissionsBitField.Flags.ViewChannel] },
                { id: i.user.id, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages] }
            ]
        });
        const row = new ActionRowBuilder().addComponents(
            new ButtonBuilder().setCustomId('claim_t').setLabel('استلام ✋').setStyle(ButtonStyle.Primary),
            new ButtonBuilder().setCustomId('close_t').setLabel('إغلاق 🔒').setStyle(ButtonStyle.Danger)
        );
        await ch.send({ content: `تذكرة جديدة من ${i.user}\nالسبب: ${reason}`, components: [row] });
        i.reply({ content: `✅ تم فتح تذكرتك: ${ch}`, ephemeral: true });
    }

    if (i.isButton() && i.customId === 'close_t') {
        await i.reply('🔒 سيتم حذف القناة خلال 3 ثوانٍ...');
        setTimeout(() => i.channel.delete(), 3000);
    }
});

client.login(process.env.DISCORD_TOKEN);
