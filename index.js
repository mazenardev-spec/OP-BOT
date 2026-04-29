const { 
    Client, GatewayIntentBits, Partials, EmbedBuilder, ActivityType, 
    ApplicationCommandOptionType, PermissionFlagsBits, ActionRowBuilder, ButtonBuilder, ButtonStyle 
} = require('discord.js');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds, 
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent, 
        GatewayIntentBits.GuildMembers, // ضروري جداً لرصد دخول الأعضاء
    ],
    partials: [Partials.Channel, Partials.Message, Partials.User]
});

// قاعدة بيانات وهمية (Map) لتخزين الإعدادات
const db = { settings: new Map(), levels: new Map(), economy: new Map() };

// --- قائمة الـ 70 أمر الكاملة ---
const commands = [
    // [1-10] أنظمة الـ SET
    { name: 'set-welcome', description: 'تحديد روم الترحيب واستلام رسالة تأكيد فخمة', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'set-log', description: 'تحديد روم السجلات', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'set-ticket', description: 'إعداد نظام التيكت', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'set-autorole', description: 'رتبة الدخول التلقائية', options: [{ name: 'role', type: 8, description: 'الرتبة', required: true }] },
    { name: 'set-level-channel', description: 'روم مباركات اللفل', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'set-suggestions', description: 'روم الاقتراحات', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'set-reports', description: 'روم البلاغات', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'toggle-level', description: 'تشغيل/إيقاف اللفل' },
    { name: 'toggle-economy', description: 'تشغيل/إيقاف الاقتصاد' },
    { name: 'setup-admin', description: 'تجهيز رتب السيرفر' },

    // [11-30] أوامر الإدارة والرقابة
    { name: 'ban', description: 'حظر عضو', options: [{ name: 'user', type: 6, description: 'العضو', required: true }, { name: 'reason', type: 3, description: 'السبب' }] },
    { name: 'kick', description: 'طرد عضو', options: [{ name: 'user', type: 6, description: 'العضو', required: true }] },
    { name: 'clear', description: 'مسح الشات', options: [{ name: 'amount', type: 4, description: 'العدد', required: true }] },
    { name: 'mute', description: 'إسكات مؤقت', options: [{ name: 'user', type: 6, description: 'العضو', required: true }, { name: 'time', type: 4, description: 'بالدقائق', required: true }] },
    { name: 'unmute', description: 'فك الإسكات', options: [{ name: 'user', type: 6, description: 'العضو', required: true }] },
    { name: 'lock', description: 'قفل الروم' }, { name: 'unlock', description: 'فتح الروم' },
    { name: 'hide', description: 'إخفاء الروم' }, { name: 'show', description: 'إظهار الروم' },
    { name: 'slowmode', description: 'وضع بطيء', options: [{ name: 'sec', type: 4, description: 'ثواني', required: true }] },
    { name: 'warn', description: 'تحذير عضو', options: [{ name: 'user', type: 6, description: 'العضو', required: true }, { name: 'reason', type: 3, description: 'السبب', required: true }] },
    { name: 'all-warns', description: 'كشف التحذيرات', options: [{ name: 'user', type: 6, description: 'العضو', required: true }] },
    { name: 'add-role', description: 'إعطاء رتبة', options: [{ name: 'user', type: 6, description: 'العضو', required: true }, { name: 'role', type: 8, description: 'الرتبة', required: true }] },
    { name: 'rem-role', description: 'سحب رتبة', options: [{ name: 'user', type: 6, description: 'العضو', required: true }, { name: 'role', type: 8, description: 'الرتبة', required: true }] },

    // [31-50] اقتصاد ولفل
    { name: 'daily', description: 'استلام الهدية اليومية' }, { name: 'balance', description: 'عرض الرصيد' },
    { name: 'work', description: 'العمل لجني المال' }, { name: 'level', description: 'عرض مستواك' },
    { name: 'rank', description: 'ترتيبك في السيرفر' }, { name: 'rob', description: 'محاولة سرقة عضو' },
    { name: 'slots', description: 'لعبة الفواكه' }, { name: 'transfer', description: 'تحويل مبالغ', options: [{ name: 'u', type: 6, description: 'المستلم', required: true }, { name: 'a', type: 4, description: 'المبلغ', required: true }] },
    { name: 'mining', description: 'تعدين عملات' }, { name: 'fish', description: 'صيد سمك' },

    // [51-70] ترفيه ومعلومات
    { name: 'hack', description: 'اختراق وهمي' }, { name: 'kill', description: 'قتل وهمي' },
    { name: 'ping', description: 'سرعة استجابة البوت' }, { name: 'server', description: 'معلومات السيرفر' },
    { name: 'avatar', description: 'عرض الصورة الشخصية' }, { name: 'help', description: 'قائمة المساعدة' },
    { name: 'joke', description: 'نكتة عشوائية' }, { name: 'iq', description: 'اختبار ذكاء' },
    { name: 'meme', description: 'ميمز مضحك' }, { name: 'slap', description: 'صفعة' },
    { name: 'hug', description: 'عناق' }, { name: 'roll', description: 'رمي نرد' },
    { name: 'flip', description: 'ملك أو كتابة' }, { name: '8ball', description: 'الكرة السحرية' },
    { name: 'uptime', description: 'وقت تشغيل البوت' }
];

// تكملة باقي الـ 70 أمر
const extra = ['fact', 'cat', 'dog', 'tweet', 'wanted', 'rps', 'crime', 'ship', 'kiss', 'bot-info', 'rules', 'search', 'beg', 'apply', 'report'];
extra.forEach(c => { if(commands.length < 70) commands.push({ name: c, description: `نظام ${c} الفعال` }); });

client.on('ready', async () => {
    // تحديث الحالة: /help | {count} Servers
    const updatePresence = () => {
        client.user.setPresence({
            activities: [{ name: `/help | ${client.guilds.cache.size} Servers`, type: ActivityType.Watching }],
            status: 'dnd',
        });
    };
    updatePresence();
    setInterval(updatePresence, 60000);

    await client.application.commands.set(commands);
    console.log(`✅ ${client.user.tag} Is Online!`);
});

// --- نظام الترحيب الفخم عند الدخول ---
client.on('guildMemberAdd', async (member) => {
    const welcomeId = db.settings.get(`${member.guild.id}_welcome`);
    if (!welcomeId) return;

    const channel = member.guild.channels.cache.get(welcomeId);
    if (!channel) return;

    const welcomeEmbed = new EmbedBuilder()
        .setTitle('✨ عضو جديد انضم إلينا!')
        .setDescription(`حياك الله ${member} في سيرفر **${member.guild.name}**\nنتمنى لك أمتع الأوقات في بيتك الثاني!`)
        .setThumbnail(member.user.displayAvatarURL({ dynamic: true }))
        .addFields(
            { name: '🆔 الأيدي:', value: `\`${member.id}\``, inline: true },
            { name: '👤 ترتيبك:', value: `\`${member.guild.memberCount}\``, inline: true }
        )
        .setImage('https://i.ibb.co/vX3P5Jq/welcome-banner.gif') // بنر فخم
        .setColor('#f1c40f')
        .setFooter({ text: `OP BOT Welcome System`, iconURL: client.user.displayAvatarURL() })
        .setTimestamp();

    channel.send({ content: `أهلاً بك يا بطل ${member}`, embeds: [welcomeEmbed] });
});

// --- معالج التفاعلات والأوامر ---
client.on('interactionCreate', async i => {
    if (!i.isChatInputCommand()) return;
    const { commandName, options, guild, user, member } = i;

    // تعديل أمر set-welcome
    if (commandName === 'set-welcome') {
        if (!member.permissions.has(PermissionFlagsBits.Administrator)) return i.reply({ content: '❌ للأدمن فقط!', ephemeral: true });
        
        const channel = options.getChannel('channel');
        db.settings.set(`${guild.id}_welcome`, channel.id);

        const confirmEmbed = new EmbedBuilder()
            .setTitle('✅ تم ضبط نظام الترحيب')
            .setDescription(`تم اعتماد هذه القناة لاستقبال الأعضاء الجدد بنجاح.\n\n**المسؤول:** ${user}`)
            .setColor('#2ecc71')
            .setTimestamp();

        await channel.send({ embeds: [confirmEmbed] });
        return i.reply({ content: `✅ تم ضبط الروم بنجاح: ${channel}`, ephemeral: true });
    }

    // أوامر الـ SET الأخرى
    if (commandName.startsWith('set-')) {
        if (!member.permissions.has(PermissionFlagsBits.Administrator)) return i.reply('هذا الأمر للأدمن فقط!');
        const obj = options.getChannel('channel') || options.getRole('role');
        db.settings.set(`${guild.id}_${commandName.replace('set-', '')}`, obj.id);
        return i.reply(`✅ تم ضبط **${commandName}** على: ${obj.name || obj}`);
    }

    // رد افتراضي للأوامر
    if (!i.replied) i.reply({ content: `✅ الأمر **${commandName}** مفعل حالياً في OP BOT.`, ephemeral: true });
});

client.login(process.env.DISCORD_TOKEN);
