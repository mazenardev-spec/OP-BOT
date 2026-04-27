const { 
    Client, GatewayIntentBits, Partials, EmbedBuilder, 
    ActionRowBuilder, ButtonBuilder, ButtonStyle, 
    ChannelType, PermissionsBitField, ActivityType 
} = require('discord.js');
const fs = require('fs');

const dbPath = './op_bot_db.json';
function loadDB() {
    if (!fs.existsSync(dbPath)) fs.writeFileSync(dbPath, JSON.stringify({ bank: {}, guilds: {} }));
    return JSON.parse(fs.readFileSync(dbPath, 'utf8'));
}
function saveDB(db) { fs.writeFileSync(dbPath, JSON.stringify(db, null, 4)); }

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent, GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildVoiceStates
    ],
    partials: [Partials.Message, Partials.Channel, Partials.Reaction]
});

client.once('ready', async () => {
    console.log(`✅ OP BOT is now Online!`);
    const commands = [
        // الإدارة (25)
        { name: 'ban', description: 'حظر عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'reason', type: 3 }] },
        { name: 'kick', description: 'طرد عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'reason', type: 3 }] },
        { name: 'timeout', description: 'إسكات عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'minutes', type: 4, required: true }] },
        { name: 'unban', description: 'فك حظر', options: [{ name: 'id', type: 3, required: true }] },
        { name: 'clear', description: 'مسح رسائل', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'lock', description: 'قفل القناة' }, { name: 'unlock', description: 'فتح القناة' },
        { name: 'hide', description: 'إخفاء القناة' }, { name: 'unhide', description: 'إظهار القناة' },
        { name: 'nuke', description: 'تطهير القناة' }, { name: 'slowmode', description: 'وضع البطيء', options: [{ name: 'seconds', type: 4, required: true }] },
        { name: 'set-log', description: 'روم السجلات', options: [{ name: 'channel', type: 7, required: true }] },
        { name: 'set-welcome', description: 'روم الترحيب', options: [{ name: 'channel', type: 7, required: true }] },
        { name: 'set-autorole', description: 'رتبة تلقائية', options: [{ name: 'role', type: 8, required: true }] },
        { name: 'set-ticket', description: 'رسالة التيكت', options: [{ name: 'channel', type: 7, required: true }] },
        { name: 'warn', description: 'تحذير عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'reason', type: 3 }] },
        { name: 'role-add', description: 'إعطاء رتبة', options: [{ name: 'user', type: 6, required: true }, { name: 'role', type: 8, required: true }] },
        { name: 'role-remove', description: 'سحب رتبة', options: [{ name: 'user', type: 6, required: true }, { name: 'role', type: 8, required: true }] },
        { name: 'nick', description: 'تغيير لقب', options: [{ name: 'user', type: 6, required: true }, { name: 'name', type: 3, required: true }] },
        { name: 'vmute', description: 'ميوت صوتي', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'vunmute', description: 'فك ميوت صوتي', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'vkick', description: 'طرد صوتي', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'move', description: 'سحب عضو', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'slow-off', description: 'إيقاف البطيء' }, { name: 'all-unmute', description: 'فك ميوت الجميع' },

        // الاقتصاد (20)
        { name: 'work', description: 'العمل' }, { name: 'daily', description: 'يومي' },
        { name: 'credits', description: 'الرصيد', options: [{ name: 'user', type: 6 }] },
        { name: 'transfer', description: 'تحويل', options: [{ name: 'user', type: 6, required: true }, { name: 'amount', type: 4, required: true }] },
        { name: 'top', description: 'الأغنياء' }, { name: 'slots', description: 'سلوتس', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'coinflip', description: 'عملة', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'fish', description: 'صيد سمك' }, { name: 'hunt', description: 'رحلة صيد' }, { name: 'beg', description: 'شحاتة' },
        { name: 'rob', description: 'سرقة', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'give-money', description: 'إعطاء (أدمن)', options: [{ name: 'user', type: 6, required: true }, { name: 'amount', type: 4, required: true }] },
        { name: 'reset-money', description: 'تصفير', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'shop', description: 'المتجر' }, { name: 'buy', description: 'شراء', options: [{ name: 'item', type: 3, required: true }] },
        { name: 'profile', description: 'البروفايل' }, { name: 'miner', description: 'تنقيب' },
        { name: 'bet', description: 'رهان', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'withdraw', description: 'سحب' }, { name: 'lb-xp', description: 'ترتيب اللفل' },

        // عام وترفيه (25)
        { name: 'ping', description: 'بينج' }, { name: 'iq', description: 'ذكاء' },
        { name: 'love', description: 'حب', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'avatar', description: 'افاتار', options: [{ name: 'user', type: 6 }] },
        { name: 'joke', description: 'نكتة' }, { name: 'hack', description: 'هكر', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'kill', description: 'قتل', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'slap', description: 'كف', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'hug', description: 'حضن', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'punch', description: 'بوكس', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'dice', description: 'نرد' }, { name: 'user-info', description: 'معلومات عضو' },
        { name: 'server-info', description: 'سيرفر' }, { name: 'bot-stats', description: 'إحصائيات' },
        { name: 'meme', description: 'ميمز' }, { name: 'calculate', description: 'حاسبة', options: [{ name: 'op', type: 3, required: true }] },
        { name: 'google', description: 'بحث', options: [{ name: 'q', type: 3, required: true }] },
        { name: 'reverse', description: 'قلب نص', options: [{ name: 'text', type: 3, required: true }] },
        { name: 'set-autoreply', description: 'رد تلقائي', options: [{ name: 'word', type: 3, required: true }, { name: 'reply', type: 3, required: true }] },
        { name: 'del-autoreply', description: 'حذف رد', options: [{ name: 'word', type: 3, required: true }] },
        { name: 'show-level', description: 'مستواك' }, { name: 'show-xp', description: 'نقاطك' },
        { name: 'help', description: 'الأوامر' }, { name: 'choose', description: 'اختيار', options: [{ name: '1', type: 3, required: true }, { name: '2', type: 3, required: true }] },
        { name: 'wanted', description: 'مطلوب', options: [{ name: 'user', type: 6 }] }
    ];
    await client.application.commands.set(commands);
});

client.on('messageCreate', async msg => {
    if (msg.author.bot || !msg.guild) return;
    const db = loadDB();
    const u = db.bank[msg.author.id] || { w: 0, daily: 0, xp: 0, lvl: 1 };
    db.bank[msg.author.id] = u;

    u.xp += 10;
    if (u.xp >= u.lvl * 150) {
        u.lvl++; u.xp = 0;
        msg.channel.send(`🎉 مبروك <@${msg.author.id}>! زاد مستواك إلى **${u.lvl}**`);
    }

    const gd = db.guilds[msg.guild.id] || { replies: {} };
    if (gd.replies[msg.content]) msg.reply(gd.replies[msg.content]);
    saveDB(db);
});

client.on('guildMemberAdd', async member => {
    const db = loadDB();
    const gd = db.guilds[member.guild.id];
    if (gd?.arole) member.roles.add(gd.arole).catch(() => {});
    if (gd?.wel) {
        const ch = member.guild.channels.cache.get(gd.wel);
        if (ch) ch.send({ embeds: [new EmbedBuilder().setTitle('نورتنا!').setDescription(`أهلاً بك ${member} في السيرفر`).setColor('#4ade80')] });
    }
});

client.on('interactionCreate', async i => {
    if (!i.isChatInputCommand()) return;
    await i.deferReply({ ephemeral: false }).catch(() => {});
    const db = loadDB();
    const { commandName, options, guild, user } = i;

    try {
        if (commandName === 'ban') {
            const target = options.getUser('user');
            const reason = options.getString('reason') || 'بدون سبب';
            await target.send(`⚠️ تم حظرك من سيرفر **${guild.name}** بسبب: ${reason}`).catch(() => {});
            await guild.members.ban(target, { reason });
            return i.editReply(`✅ تم حظر ${target.tag} وإرسال رسالة له.`);
        }
        if (commandName === 'kick') {
            const target = options.getMember('user');
            const reason = options.getString('reason') || 'بدون سبب';
            await target.send(`⚠️ تم طردك من سيرفر **${guild.name}** بسبب: ${reason}`).catch(() => {});
            await target.kick(reason);
            return i.editReply(`✅ تم طرد ${target.user.tag} وإرسال رسالة له.`);
        }
        if (commandName === 'set-welcome') {
            if (!db.guilds[guild.id]) db.guilds[guild.id] = { replies: {} };
            db.guilds[guild.id].wel = options.getChannel('channel').id;
            saveDB(db);
            return i.editReply('✅ تم ضبط روم الترحيب.');
        }
        if (commandName === 'set-autorole') {
            if (!db.guilds[guild.id]) db.guilds[guild.id] = { replies: {} };
            db.guilds[guild.id].arole = options.getRole('role').id;
            saveDB(db);
            return i.editReply('✅ تم ضبط الرتبة التلقائية.');
        }
        if (commandName === 'show-level') {
            const u = db.bank[user.id] || { lvl: 1 };
            return i.editReply(`📊 يا <@${user.id}>، مستواك الحالي هو: **${u.lvl}**`);
        }
        if (commandName === 'show-xp') {
            const u = db.bank[user.id] || { xp: 0 };
            return i.editReply(`⭐ يا <@${user.id}>، نقاط خبرتك هي: **${u.xp}**`);
        }
        if (commandName === 'set-autoreply') {
            if (!db.guilds[guild.id]) db.guilds[guild.id] = { replies: {} };
            db.guilds[guild.id].replies[options.getString('word')] = options.getString('reply');
            saveDB(db);
            return i.editReply('✅ تم إضافة الرد التلقائي.');
        }

        if (!i.replied) return i.editReply(`🛠️ الأمر **/${commandName}** مبرمج وسيتم تفعيل مهامه قريباً في OP BOT.`);
    } catch (e) {
        console.error(e);
        return i.editReply('❌ حدث خطأ!');
    }
});

client.login(process.env.DISCORD_TOKEN);
