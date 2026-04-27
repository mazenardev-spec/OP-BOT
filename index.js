const { 
    Client, GatewayIntentBits, Partials, EmbedBuilder, 
    ActionRowBuilder, ButtonBuilder, ButtonStyle, 
    ChannelType, PermissionsBitField, ActivityType 
} = require('discord.js');
const fs = require('fs');

// --- 1. قاعدة البيانات ---
const dbPath = './op_bot_db.json';
function loadDB() {
    if (!fs.existsSync(dbPath)) fs.writeFileSync(dbPath, JSON.stringify({ bank: {}, guilds: {} }));
    return JSON.parse(fs.readFileSync(dbPath, 'utf8'));
}
function saveDB(db) { fs.writeFileSync(dbPath, JSON.stringify(db, null, 4)); }
function getUser(db, uid) {
    if (!db.bank[uid]) db.bank[uid] = { w: 0, daily: 0, xp: 0, lvl: 1 };
    return db.bank[uid];
}
function getGuild(db, gid) {
    if (!db.guilds[gid]) db.guilds[gid] = { log: null, wel: null, arole: null, replies: {} };
    return db.guilds[gid];
}

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildVoiceStates
    ],
    partials: [Partials.Message, Partials.Channel, Partials.Reaction]
});

// --- 2. مصفوفة الـ 70 أمر ---
client.once('ready', async () => {
    console.log(`✅ ${client.user.tag} Online!`);

    const updateStatus = () => {
        client.user.setActivity(`/help | ${client.guilds.cache.size} Servers`, { type: ActivityType.Watching });
    };
    updateStatus();
    setInterval(updateStatus, 3600000);

    const commands = [
        // الإدارة (25)
        { name: 'ban', description: 'حظر عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'reason', type: 3 }] },
        { name: 'kick', description: 'طرد عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'reason', type: 3 }] },
        { name: 'timeout', description: 'إسكات عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'minutes', type: 4, required: true }] },
        { name: 'unban', description: 'فك حظر (ID)', options: [{ name: 'id', type: 3, required: true }] },
        { name: 'clear', description: 'مسح رسائل', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'lock', description: 'قفل القناة' },
        { name: 'unlock', description: 'فتح القناة' },
        { name: 'hide', description: 'إخفاء القناة' },
        { name: 'unhide', description: 'إظهار القناة' },
        { name: 'nuke', description: 'تطهير القناة' },
        { name: 'slowmode', description: 'وضع البطيء', options: [{ name: 'seconds', type: 4, required: true }] },
        { name: 'set-log', description: 'تحديد روم السجلات', options: [{ name: 'channel', type: 7, required: true }] },
        { name: 'set-welcome', description: 'تحديد روم الترحيب', options: [{ name: 'channel', type: 7, required: true }] },
        { name: 'set-autorole', description: 'رتبة تلقائية', options: [{ name: 'role', type: 8, required: true }] },
        { name: 'set-ticket', description: 'إرسال رسالة التيكت', options: [{ name: 'channel', type: 7, required: true }] },
        { name: 'warn', description: 'تحذير عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'reason', type: 3 }] },
        { name: 'role-add', description: 'إعطاء رتبة', options: [{ name: 'user', type: 6, required: true }, { name: 'role', type: 8, required: true }] },
        { name: 'role-remove', description: 'سحب رتبة', options: [{ name: 'user', type: 6, required: true }, { name: 'role', type: 8, required: true }] },
        { name: 'nick', description: 'تغيير لقب عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'name', type: 3, required: true }] },
        { name: 'vmute', description: 'ميوت صوتي', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'vunmute', description: 'فك ميوت صوتي', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'vkick', description: 'طرد من الروم الصوتي', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'move', description: 'سحب عضو لرومك', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'slow-off', description: 'إيقاف الوضع البطيء' },
        { name: 'all-unmute', description: 'فك الميوت عن الجميع' },

        // الاقتصاد (20)
        { name: 'work', description: 'العمل لكسب المال' },
        { name: 'daily', description: 'الراتب اليومي' },
        { name: 'credits', description: 'رصيدك الحالي', options: [{ name: 'user', type: 6 }] },
        { name: 'transfer', description: 'تحويل مبالغ', options: [{ name: 'user', type: 6, required: true }, { name: 'amount', type: 4, required: true }] },
        { name: 'top', description: 'قائمة الأغنياء' },
        { name: 'slots', description: 'لعبة السلوتس', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'coinflip', description: 'ملك أو كتابة', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'fish', description: 'صيد سمك' },
        { name: 'hunt', description: 'رحلة صيد' },
        { name: 'beg', description: 'شحاتة' },
        { name: 'rob', description: 'سرقة عضو', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'give-money', description: 'إعطاء مال (للأدمن)', options: [{ name: 'user', type: 6, required: true }, { name: 'amount', type: 4, required: true }] },
        { name: 'reset-money', description: 'تصفير بنك عضو', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'shop', description: 'متجر السيرفر' },
        { name: 'buy', description: 'شراء رتبة من المتجر', options: [{ name: 'item', type: 3, required: true }] },
        { name: 'profile', description: 'ملفك الشخصي المالي' },
        { name: 'miner', description: 'التنقيب عن الذهب' },
        { name: 'bet', description: 'رهان سريع', options: [{ name: 'amount', type: 4, required: true }] },
        { name: 'lb-xp', description: 'ترتيب اللفل' },
        { name: 'withdraw', description: 'سحب من البنك' },

        // الترفيه والعام (25)
        { name: 'ping', description: 'سرعة البوت' },
        { name: 'iq', description: 'نسبة ذكائك' },
        { name: 'love', description: 'نسبة الحب', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'avatar', description: 'صورة الحساب', options: [{ name: 'user', type: 6 }] },
        { name: 'joke', description: 'نكتة' },
        { name: 'hack', description: 'اختراق وهمي', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'kill', description: 'تصفية عضو', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'slap', description: 'صفعة', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'hug', description: 'حضن', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'punch', description: 'لكمة', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'dice', description: 'رمي النرد' },
        { name: 'user-info', description: 'معلومات الحساب', options: [{ name: 'user', type: 6 }] },
        { name: 'server-info', description: 'معلومات السيرفر' },
        { name: 'bot-stats', description: 'إحصائيات البوت' },
        { name: 'meme', description: 'ميمز عشوائي' },
        { name: 'choose', description: 'اختيار عشوائي', options: [{ name: '1', type: 3, required: true }, { name: '2', type: 3, required: true }] },
        { name: 'wanted', description: 'صورة مطلوب (تاغ)', options: [{ name: 'user', type: 6 }] },
        { name: 'ship', description: 'توافق بين اثنين', options: [{ name: 'u1', type: 6, required: true }, { name: 'u2', type: 6, required: true }] },
        { name: 'reverse', description: 'قلب النص', options: [{ name: 'text', type: 3, required: true }] },
        { name: 'shorten', description: 'تقصير رابط', options: [{ name: 'link', type: 3, required: true }] },
        { name: 'calculate', description: 'حاسبة', options: [{ name: 'op', type: 3, required: true }] },
        { name: 'google', description: 'بحث جوجل', options: [{ name: 'q', type: 3, required: true }] },
        { name: 'set-autoreply', description: 'إضافة رد تلقائي', options: [{ name: 'word', type: 3, required: true }, { name: 'reply', type: 3, required: true }] },
        { name: 'del-autoreply', description: 'حذف رد تلقائي', options: [{ name: 'word', type: 3, required: true }] },
        { name: 'help', description: 'قائمة الأوامر' }
    ];

    await client.application.commands.set(commands);
});

// --- 3. نظام اللفل والترحيب ---
client.on('messageCreate', async msg => {
    if (msg.author.bot || !msg.guild) return;
    const db = loadDB();
    const u = getUser(db, msg.author.id);
    const gd = getGuild(db, msg.guild.id);

    u.xp += 10;
    if (u.xp >= u.lvl * 150) {
        u.lvl++; u.xp = 0;
        msg.reply(`🎉 مبروك! لفل أب إلى **${u.lvl}**`);
    }

    if (gd.replies[msg.content]) msg.channel.send(gd.replies[msg.content]);
    saveDB(db);
});

client.on('guildMemberAdd', async member => {
    const db = loadDB();
    const gd = getGuild(db, member.guild.id);
    if (gd.wel) {
        const ch = member.guild.channels.cache.get(gd.wel);
        if (ch) ch.send({ embeds: [new EmbedBuilder().setTitle('عضو جديد!').setDescription(`نورتنا ${member}`).setColor('#4ade80')] });
    }
    if (gd.arole) member.roles.add(gd.arole).catch(() => {});
});

// --- 4. تنفيذ الأوامر (الإدارة والاقتصاد) ---
client.on('interactionCreate', async i => {
    if (!i.isChatInputCommand()) return;
    
    const db = loadDB();
    const { commandName, options, user, guild, channel } = i;

    // منع خطأ "The application did not respond" عن طريق الرد الأولي إذا كان الأمر سيأخذ وقتاً
    // لكن هنا سنستخدم الرد المباشر لكل حالة

    try {
        // الإدارة
        if (commandName === 'clear') {
            const amt = options.getInteger('amount');
            await channel.bulkDelete(amt > 100 ? 100 : amt);
            return i.reply({ content: `🧹 تم مسح ${amt} رسالة`, ephemeral: true });
        }
        if (commandName === 'lock') {
            await channel.permissionOverwrites.edit(guild.id, { SendMessages: false });
            return i.reply('🔒 تم قفل القناة');
        }
        if (commandName === 'ping') {
            return i.reply(`🏓 Pong! \`${client.ws.ping}ms\``);
        }
        if (commandName === 'set-welcome') {
            getGuild(db, guild.id).wel = options.getChannel('channel').id;
            saveDB(db);
            return i.reply('✅ تم ضبط قناة الترحيب بنجاح!');
        }

        // الاقتصاد البسيط
        if (commandName === 'work') {
            const r = Math.floor(Math.random() * 800) + 200;
            getUser(db, user.id).w += r;
            saveDB(db);
            return i.reply(`💼 عملت بجد وكسبت **${r}** من العملات!`);
        }

        // تيكت
        if (commandName === 'set-ticket') {
            const row = new ActionRowBuilder().addComponents(
                new ButtonBuilder().setCustomId('op_t').setLabel('فتح تذكرة').setStyle(ButtonStyle.Primary)
            );
            await options.getChannel('channel').send({ content: '**نظام الدعم الفني | OP BOT**\nاضغط على الزر أدناه لفتح تذكرة.', components: [row] });
            return i.reply('✅ تم إرسال رسالة التيكت.');
        }

        // --- رد تلقائي للأوامر الـ 70 التي لم تبرمجها بعد ---
        // هذا الجزء هو الحل السحري لمشكلة "The application did not respond"
        if (!i.replied) {
            return i.reply({ 
                content: `🛠️ الأمر **/${commandName}** قيد التجهيز وسيتم إطلاقه في التحديث القادم لـ **OP BOT**!`, 
                ephemeral: true 
            });
        }

    } catch (err) {
        console.error(err);
        if (!i.replied) i.reply({ content: '❌ حدث خطأ داخلي أثناء تنفيذ هذا الأمر.', ephemeral: true });
    }

    saveDB(db);
});

// --- 5. نظام التيكت ---
client.on('interactionCreate', async i => {
    if (!i.isButton()) return;

    if (i.customId === 'op_t') {
        const tc = await i.guild.channels.create({
            name: `ticket-${i.user.username}`,
            type: ChannelType.GuildText,
            permissionOverwrites: [
                { id: i.guild.id, deny: [PermissionsBitField.Flags.ViewChannel] },
                { id: i.user.id, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages] }
            ]
        });
        i.reply({ content: `تم فتح تذكرتك هنا: ${tc}`, ephemeral: true });
        const row = new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('cl_t').setLabel('إغلاق').setStyle(ButtonStyle.Danger));
        tc.send({ content: `مرحباً بك ${i.user} في الدعم الفني، يرجى كتابة مشكلتك وسيرد عليك الإدارة قريباً.`, components: [row] });
    }
    
    if (i.customId === 'cl_t') {
        i.reply('🔒 سيتم حذف التذكرة نهائياً خلال 5 ثوانٍ...');
        setTimeout(() => i.channel.delete().catch(() => {}), 5000);
    }
});

client.login(process.env.DISCORD_TOKEN);
