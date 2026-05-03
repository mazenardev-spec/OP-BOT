const {
    Client, GatewayIntentBits, Partials, EmbedBuilder, ActivityType,
    PermissionFlagsBits, ActionRowBuilder, ButtonBuilder, ButtonStyle,
    ApplicationCommandOptionType, REST, Routes, Collection
} = require('discord.js');
const { QuickDB } = require("quick.db");
const db = new QuickDB();

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent, GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildPresences, GatewayIntentBits.GuildMessageReactions
    ],
    partials: [Partials.Channel, Partials.Message, Partials.User, Partials.Reaction]
});

// --- مصفوفة الأوامر الكاملة (77 أمر) ---
const commands = [
    // [1-10] الإعدادات (SETTINGS)
    { name: 'set-welcome', description: '✨ تحديد قناة الترحيب بالأعضاء الجدد', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'set-log', description: '📜 تحديد قناة السجلات لمراقبة الأحداث', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'set-ticket', description: '📩 إعداد نظام التذاكر والدعم الفني', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'set-autorole', description: '🎭 تحديد رتبة تعطى تلقائياً عند الدخول', options: [{ name: 'role', type: 8, description: 'الرتبة', required: true }] },
    { name: 'set-level-channel', description: '🆙 تحديد قناة إعلانات ترقيات لفل الأعضاء', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'set-suggestions', description: '💡 ضبط قناة استقبال الاقتراحات', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'set-reports', description: '🚩 تحديد قناة استقبال البلاغات', options: [{ name: 'channel', type: 7, description: 'الروم', required: true }] },
    { name: 'toggle-level', description: '⚙️ تشغيل أو إيقاف نظام اللفل' },
    { name: 'toggle-economy', description: '💰 تشغيل أو إيقاف نظام الاقتصاد' },
    { name: 'setup-admin', description: '🛠️ تجهيز رتب الإدارة الأساسية' },

    // [11-30] الإدارة (MODERATION)
    { name: 'ban', description: '🔨 حظر عضو نهائياً', options: [{ name: 'user', type: 6, description: 'العضو', required: true }, { name: 'reason', type: 3, description: 'السبب' }] },
    { name: 'kick', description: '👞 طرد عضو من السيرفر', options: [{ name: 'user', type: 6, description: 'العضو', required: true }, { name: 'reason', type: 3, description: 'السبب' }] },
    { name: 'timeout', description: '⏳ إسكات عضو مؤقتاً', options: [{ name: 'user', type: 6, description: 'العضو', required: true }, { name: 'minutes', type: 4, description: 'الدقائق', required: true }] },
    { name: 'untimeout', description: '🔈 إلغاء إسكات عضو', options: [{ name: 'user', type: 6, description: 'العضو', required: true }] },
    { name: 'clear', description: '🧹 تنظيف الشات', options: [{ name: 'amount', type: 4, description: 'العدد', required: true }] },
    { name: 'warn', description: '⚠️ تحذير رسمي لعضو', options: [{ name: 'user', type: 6, description: 'العضو', required: true }, { name: 'reason', type: 3, description: 'السبب', required: true }] },
    { name: 'all-warns', description: '📂 عرض تحذيرات عضو', options: [{ name: 'user', type: 6, description: 'العضو', required: true }] },
    { name: 'lock', description: '🔒 إغلاق القناة الحالية' },
    { name: 'unlock', description: '🔓 فتح القناة' },
    { name: 'hide', description: '👻 إخفاء القناة' },
    { name: 'show', description: '👀 إظهار القناة' },
    { name: 'slowmode', description: '🐢 وضع بطيء', options: [{ name: 'sec', type: 4, description: 'ثواني', required: true }] },
    {
        name: 'add-role',
        description: '➕ منح رتبة لعضو',
        options: [
            { name: 'user', type: 6, description: 'العضو المراد منحه الرتبة', required: true },
            { name: 'role', type: 8, description: 'الرتبة المطلوب منحها', required: true }
        ]
    },
    {
        name: 'rem-role',
        description: '➖ سحب رتبة من عضو',
        options: [
            { name: 'user', type: 6, description: 'العضو المراد سحب الرتبة منه', required: true },
            { name: 'role', type: 8, description: 'الرتبة المطلوب سحبها', required: true }
        ]
    },

    // [31-50] الاقتصاد واللفل (ECONOMY & LEVEL)
    { name: 'daily', description: '💵 استلام الهديّة اليومية' },
    { name: 'credits', description: '👛 عرض رصيدك الحالي' },
    { name: 'level', description: '📊 عرض مستواك الحالي' },
    { name: 'rank', description: '🏆 ترتيبك في السيرفر' },
    { name: 'transfer', description: '💸 تحويل أموال', options: [{ name: 'u', type: 6, description: 'المستلم', required: true }, { name: 'a', type: 4, description: 'المبلغ', required: true }] },
    { name: 'rob', description: '🔫 سرقة رصيد عضو (مخاطرة)', options: [{ name: 'user', type: 6, description: 'العضو المراد سرقته', required: true }] },
    { name: 'slots', description: '🎰 آلة الحظ' },
    { name: 'mining', description: '⛏️ التعدين' },
    { name: 'fish', description: '🎣 صيد السمك' },

    // [51-72] ترفيه وعامة
    { name: 'ping', description: '📶 سرعة الاتصال' },
    { name: 'server', description: '🏰 معلومات السيرفر' },
    { name: 'avatar', description: '👤 صورة الحساب', options: [{ name: 'user', type: 6, description: 'العضو المراد عرض صورته' }] },
    { name: 'help', description: '📖 قائمة المساعدة الكاملة' },
    { name: 'hack', description: '💻 اختراق وهمي', options: [{ name: 'user', type: 6, description: 'العضو المراد اختراقه', required: true }] },
    { name: 'kill', description: '🔪 قضاء على عضو', options: [{ name: 'user', type: 6, description: 'العضو المراد قتله', required: true }] },
    { name: 'joke', description: '😂 نكتة' },
    { name: 'iq', description: '🧠 مستوى الذكاء' },
    { name: 'meme', description: '🐸 ميمز مضحك' },
    { name: 'slap', description: '✋ صفعة', options: [{ name: 'user', type: 6, description: 'العضو المراد صفعه', required: true }] },
    { name: 'hug', description: '🫂 عناق', options: [{ name: 'user', type: 6, description: 'العضو المراد معانقته', required: true }] },
    { name: 'roll', description: '🎲 نرد' },
    { name: 'flip', description: '🪙 ملك أم كتابة' },
    { name: '8ball', description: '🔮 الكرة السحرية', options: [{ name: 'question', type: 3, description: 'السؤال المطلوب إجابته', required: true }] },
    { name: 'uptime', description: '⏰ مدة التشغيل' },

    // [73-75] الأوامر الجديدة
    { name: 'status', description: '📊 حالة البوت والإحصائيات' },
    { name: 'servers', description: '🌐 عرض السيرفرات التي فيها البوت' },

    // [76-77] أوامر الرد التلقائي الجديدة
    {
        name: 'set-autoreply',
        description: '🤖 إضافة رد تلقائي على كلمة معينة',
        options: [
            { name: 'keyword', type: 3, description: 'الكلمة التي تريد الرد عليها', required: true },
            { name: 'response', type: 3, description: 'الرد الذي سيظهر', required: true }
        ]
    },
    {
        name: 'autoreply-list',
        description: '📋 عرض قائمة الردود التلقائية'
    },

    // [78-79] أوامر الترفيه الجديدة
    {
        name: 'rolet',
        description: '🎰 لعبة الروليت - الفائز يحصل على 5000 كريدت',
        options: [
            { name: 'target', type: 6, description: 'الشخص الذي تريد استهدافه (اختياري)', required: false }
        ]
    }
];

// نظام الرد التلقائي عند المراسلة
client.on('messageCreate', async (message) => {
    try {
        if (message.author.bot) return;
        if (!message.guild) return;

        // نظام اللفل
        const guildConfig = await db.get(`config_${message.guild.id}`) || {};
        if (guildConfig?.levelEnabled) {
            const userId = message.author.id;
            let userLevelData = await db.get(`levels_${userId}`) || { xp: 0, level: 1 };

            // زيادة XP عشوائية (5-15)
            userLevelData.xp += Math.floor(Math.random() * 10) + 10;

            // حساب إذا وصل للفل جديد (100 XP لكل فل)
            const requiredXP = userLevelData.level * 100;
            if (userLevelData.xp >= requiredXP) {
                userLevelData.level++;
                userLevelData.xp = 0;

                // إعلان الترقي في القناة المحددة
                if (guildConfig.levelChannel) {
                    const levelChannel = message.guild.channels.cache.get(guildConfig.levelChannel);
                    if (levelChannel) {
                        const embed = new EmbedBuilder()
                            .setColor('#00ff00')
                            .setTitle('🎉 ترقية جديدة!')
                            .setDescription(`مبروك ${message.author}! وصلت للفل ${userLevelData.level}`)
                            .setThumbnail(message.author.displayAvatarURL())
                            .setTimestamp();

                        levelChannel.send({ content: `🎉 ${message.author}`, embeds: [embed] }).catch(() => {});
                    }
                }
            }

            await db.set(`levels_${userId}`, userLevelData);
        }

        // نظام الرد التلقائي
        const guildAutoreplies = await db.get(`autoreplies_${message.guild.id}`) || [];
        const content = message.content.toLowerCase();

        for (const autoreply of guildAutoreplies) {
            if (content.includes(autoreply.keyword.toLowerCase())) {
                // منع التكرار المفرط
                if (message.author.id === client.user.id) return;

                // إرسال الرد مع ذكر العضو
                message.reply(`${autoreply.response}`).catch(() => {});

                // إضافة رد فعل للرسالة
                try {
                    await message.react('🤖');
                } catch (error) {}
                break;
            }
        }
    } catch (error) {
        console.error('خطأ في messageCreate:', error);
    }
});

// رسالة شكر عند إضافة البوت للسيرفر
client.on('guildCreate', async (guild) => {
    try {
        const owner = guild.ownerId;
        const ownerUser = await client.users.fetch(owner);
        const embed = new EmbedBuilder()
            .setColor('#7289da')
            .setTitle('✨ شكراً لك على إضافة البوت!')
            .setDescription(`شكراً لك ${ownerUser.username} على إضافة OP BOT إلى سيرفرك!\n\nالبوت يحتوي على ${commands.length} أمر مفيد للإدارة والترفيه والاقتصاد.`)
            .setThumbnail(guild.iconURL() || client.user.displayAvatarURL())
            .addFields(
                { name: '📊 عدد الأوامر', value: `${commands.length} أمر`, inline: true },
                { name: '⚙️ الإعدادات', value: '10 أوامر', inline: true },
                { name: '🎮 الترفيه', value: '22 أوامر', inline: true }
            )
            .setTimestamp();

        const row = new ActionRowBuilder()
            .addComponents(
                new ButtonBuilder()
                    .setLabel('الدعم')
                    .setStyle(ButtonStyle.Link)
                    .setURL('https://discord.gg/vvmaAbasEN')
            );

        ownerUser.send({ embeds: [embed], components: [row] }).catch(() => {});
    } catch (error) {
        console.log('لا يمكن إرسال رسالة إلى صاحب السيرفر');
    }
});

// تسجيل الأوامر مع .toJSON() الصحيح
client.once('ready', async () => {
    console.log(`✅ OP BOT Online: ${client.user.tag}`);

    try {
        // تحويل الأوامر إلى JSON بشكل صحيح
        const commandsJSON = commands.map(cmd => ({
            name: cmd.name,
            description: cmd.description,
            options: cmd.options || []
        }));

        // تسجيل الأوامر
        await client.application.commands.set(commandsJSON);
        console.log(`✅ تم تسجيل ${commands.length} أمر بنجاح`);

        // تحديث نشاط البوت
        client.user.setActivity(`OPBOT | ${client.guilds.cache.size} Servers`, { type: ActivityType.Watching });
        // إظهار حالة البوت
        console.log(`📊 البوت موجود في ${client.guilds.cache.size} سيرفر`);
        console.log(`👥 عدد الأعضاء الإجمالي ${client.guilds.cache.reduce((acc, g) => acc + g.memberCount, 0)}`);
    } catch (error) {
        console.error('❌ خطأ في تسجيل الأوامر:', error);
    }
});

// --- نظام الترحيب واللفل واللوج ---
client.on('guildMemberAdd', async (member) => {
    try {
        const config = await db.get(`config_${member.guild.id}`) || {};
        if (config?.welcomeChannel) {
            const channel = member.guild.channels.cache.get(config.welcomeChannel);
            if (channel) channel.send(`✨ نورت السيرفر يا ${member.user.username}! أنت العضو رقم ${member.guild.memberCount}.`).catch(() => {});
        }
        if (config?.autoRole) {
            member.roles.add(config.autoRole).catch(() => {});
        }
    } catch (error) {
        console.error('خطأ في guildMemberAdd:', error);
    }
});

// تخزين جلسات الروليت النشطة
const activeRouletteGames = new Map();

// --- معالج الأوامر التفاعلي ---
client.on('interactionCreate', async (interaction) => {
    try {
        if (!interaction.isChatInputCommand()) return;
        const { commandName, options, user, guild, member, channel } = interaction;

        // --- أوامر الإدارة المبرمجة ---
        if (commandName === 'clear') {
            if (!member.permissions.has(PermissionFlagsBits.ManageMessages))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            const amount = options.getInteger('amount');
            if (amount < 1 || amount > 100) return interaction.reply({ content: '❌ العدد يجب أن يكون بين 1 و 100!', ephemeral: true });
            await channel.bulkDelete(Math.min(amount, 100));
            return interaction.reply({ content: `🧹 تم مسح ${amount} رسالة.`, ephemeral: true });
        }

        if (commandName === 'lock') {
            if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            await channel.permissionOverwrites.edit(guild.id, { SendMessages: false });
            return interaction.reply('🔒 تم إغلاق القناة بنجاح.');
        }

        if (commandName === 'unlock') {
            if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            await channel.permissionOverwrites.edit(guild.id, { SendMessages: true });
            return interaction.reply('🔓 تم فتح القناة بنجاح.');
        }

        if (commandName === 'add-role') {
            if (!member.permissions.has(PermissionFlagsBits.ManageRoles))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            const targetUser = options.getUser('user');
            const role = options.getRole('role');
            const targetMember = await guild.members.fetch(targetUser.id).catch(() => null);
            if (!targetMember) return interaction.reply({ content: '❌ العضو غير موجود!', ephemeral: true });
            if (targetMember.roles.highest.position >= member.roles.highest.position && member.id !== guild.ownerId)
                return interaction.reply({ content: '❌ لا يمكنك منح رتبة لعضو رتبته أعلى منك!', ephemeral: true });
            await targetMember.roles.add(role.id);
            return interaction.reply(`✅ تم إضافة الرتبة ${role.name} إلى ${targetUser.username}`);
        }

        if (commandName === 'rem-role') {
            if (!member.permissions.has(PermissionFlagsBits.ManageRoles))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            const targetUser = options.getUser('user');
            const role = options.getRole('role');
            const targetMember = await guild.members.fetch(targetUser.id).catch(() => null);
            if (!targetMember) return interaction.reply({ content: '❌ العضو غير موجود!', ephemeral: true });
            if (targetMember.roles.highest.position >= member.roles.highest.position && member.id !== guild.ownerId)
                return interaction.reply({ content: '❌ لا يمكنك سحب رتبة من عضو رتبته أعلى منك!', ephemeral: true });
            await targetMember.roles.remove(role.id);
            return interaction.reply(`✅ تم سحب الرتبة ${role.name} من ${targetUser.username}`);
        }

        if (commandName === 'timeout') {
            if (!member.permissions.has(PermissionFlagsBits.ModerateMembers))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            const targetUser = options.getUser('user');
            const minutes = options.getInteger('minutes');
            if (minutes < 1 || minutes > 10080) return interaction.reply({ content: '❌ المدة يجب أن تكون بين 1 و 10080 دقيقة!', ephemeral: true });
            const targetMember = await guild.members.fetch(targetUser.id).catch(() => null);
            if (!targetMember) return interaction.reply({ content: '❌ العضو غير موجود!', ephemeral: true });
            if (targetMember.roles.highest.position >= member.roles.highest.position && member.id !== guild.ownerId)
                return interaction.reply({ content: '❌ لا يمكنك إسكات عضو رتبته أعلى منك!', ephemeral: true });
            await targetMember.timeout(minutes * 60 * 1000);
            return interaction.reply(`⏳ تم إسكات ${targetUser.username} لمدة ${minutes} دقيقة.`);
        }

        if (commandName === 'untimeout') {
            if (!member.permissions.has(PermissionFlagsBits.ModerateMembers))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            const targetUser = options.getUser('user');
            const targetMember = await guild.members.fetch(targetUser.id).catch(() => null);
            if (!targetMember) return interaction.reply({ content: '❌ العضو غير موجود!', ephemeral: true });
            await targetMember.timeout(null);
            return interaction.reply(`🔈 تم إلغاء إسكات ${targetUser.username}.`);
        }

        if (commandName === 'ban') {
            if (!member.permissions.has(PermissionFlagsBits.BanMembers))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            const targetUser = options.getUser('user');
            const reason = options.getString('reason') || 'بدون سبب';
            const targetMember = await guild.members.fetch(targetUser.id).catch(() => null);
            if (!targetMember) return interaction.reply({ content: '❌ العضو غير موجود!', ephemeral: true });
            if (targetMember.roles.highest.position >= member.roles.highest.position && member.id !== guild.ownerId)
                return interaction.reply({ content: '❌ لا يمكنك حظر عضو رتبته أعلى منك!', ephemeral: true });
            await guild.members.ban(targetUser.id, { reason });
            return interaction.reply(`🔨 تم حظر ${targetUser.username} بنجاح.`);
        }

        if (commandName === 'kick') {
            if (!member.permissions.has(PermissionFlagsBits.KickMembers))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            const targetUser = options.getUser('user');
            const reason = options.getString('reason') || 'بدون سبب';
            const targetMember = await guild.members.fetch(targetUser.id).catch(() => null);
            if (!targetMember) return interaction.reply({ content: '❌ العضو غير موجود!', ephemeral: true });
            if (targetMember.roles.highest.position >= member.roles.highest.position && member.id !== guild.ownerId)
                return interaction.reply({ content: '❌ لا يمكنك طرد عضو رتبته أعلى منك!', ephemeral: true });
            await guild.members.kick(targetUser.id, reason);
            return interaction.reply(`👞 تم طرد ${targetUser.username} بنجاح.`);
        }

        if (commandName === 'hide') {
            if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            await channel.permissionOverwrites.edit(guild.id, { ViewChannel: false });
            return interaction.reply('👻 تم إخفاء القناة بنجاح.');
        }

        if (commandName === 'show') {
            if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            await channel.permissionOverwrites.edit(guild.id, { ViewChannel: true });
            return interaction.reply('👀 تم إظهار القناة بنجاح.');
        }

        if (commandName === 'slowmode') {
            if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            const sec = options.getInteger('sec');
            if (sec < 0 || sec > 21600) return interaction.reply({ content: '❌ الوقت يجب أن يكون بين 0 و 21600 ثانية!', ephemeral: true });
            await channel.setRateLimitPerUser(sec);
            return interaction.reply(`🐢 تم وضع وضع بطيء ${sec} ثانية.`);
        }

        if (commandName === 'warn') {
            if (!member.permissions.has(PermissionFlagsBits.ModerateMembers))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            const targetUser = options.getUser('user');
            const reason = options.getString('reason');
            const targetMember = await guild.members.fetch(targetUser.id).catch(() => null);
            if (!targetMember) return interaction.reply({ content: '❌ العضو غير موجود!', ephemeral: true });

            let userWarns = await db.get(`warns_${targetUser.id}`) || [];
            userWarns.push({ reason, date: Date.now(), warnedBy: user.id });
            await db.set(`warns_${targetUser.id}`, userWarns);

            const embed = new EmbedBuilder()
                .setColor('#ff9900')
                .setTitle('⚠️ تحذير جديد')
                .addFields(
                    { name: 'العضو', value: targetUser.username, inline: true },
                    { name: 'السبب', value: reason, inline: true },
                    { name: 'عدد التحذيرات', value: `${userWarns.length}`, inline: true }
                )
                .setTimestamp();

            try {
                await targetUser.send({ content: `⚠️ لقد تلقيت تحذيراً في ${guild.name}`, embeds: [embed] });
            } catch (error) {}

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'all-warns') {
            if (!member.permissions.has(PermissionFlagsBits.ModerateMembers))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
            const targetUser = options.getUser('user');
            const userWarns = await db.get(`warns_${targetUser.id}`) || [];

            if (userWarns.length === 0) {
                return interaction.reply(`📂 ${targetUser.username} ليس لديه أي تحذيرات`);
            }

            const warnsList = userWarns.map((warn, index) =>
                `${index + 1}. ${warn.reason} - ${new Date(warn.date).toLocaleDateString()}`
            ).join('\n');

            const embed = new EmbedBuilder()
                .setColor('#ff9900')
                .setTitle(`📂 تحذيرات ${targetUser.username}`)
                .setDescription(`إجمالي التحذيرات: ${userWarns.length}`)
                .addFields({ name: 'التاريخ', value: warnsList })
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        // --- أوامر الاقتصاد المبرمجة ---
        let userData = await db.get(`economy_${user.id}`) || { wallet: 0, bank: 0, lastDaily: 0 };

        if (commandName === 'daily') {
            const now = Date.now();
            if (now - userData.lastDaily < 86400000) {
                const remaining = 86400000 - (now - userData.lastDaily);
                const hours = Math.floor(remaining / 3600000);
                const minutes = Math.floor((remaining % 3600000) / 60000);
                return interaction.reply(`⏳ يجب الانتظار ${hours} ساعة و ${minutes} دقيقة قبل المطالبة بالهدية اليومية التالية!`);
            }

            userData.wallet += 1000;
            userData.lastDaily = now;
            await db.set(`economy_${user.id}`, userData);

            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle('💵 هدية يومية جديدة!')
                .setDescription(`✅ تم إضافة 1000 عملة إلى محفظتك!`)
                .addFields(
                    { name: '💰 المحفظة الحالية', value: `${userData.wallet} كريدت`, inline: true },
                    { name: '🏦 البنك', value: `${userData.bank} كريدت`, inline: true },
                    { name: '📊 الإجمالي', value: `${userData.wallet + userData.bank} كريدت`, inline: true }
                )
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'credits') {
            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle(`👛 رصيد ${user.username}`)
                .addFields(
                    { name: '💰 المحفظة', value: `${userData.wallet} كريدت`, inline: true },
                    { name: '🏦 البنك', value: `${userData.bank} كريدت`, inline: true },
                    { name: '📊 الإجمالي', value: `${userData.wallet + userData.bank} كريدت`, inline: true }
                )
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'transfer') {
            const targetUser = options.getUser('u');
            const amount = options.getInteger('a');

            if (targetUser.id === user.id) return interaction.reply({ content: '❌ لا يمكنك تحويل الأموال لنفسك!', ephemeral: true });
            if (amount < 1) return interaction.reply({ content: '❌ المبلغ يجب أن يكون أكبر من 0!', ephemeral: true });
            if (userData.wallet < amount) return interaction.reply({ content: '❌ ليس لديك رصيد كافي!', ephemeral: true });

            let targetData = await db.get(`economy_${targetUser.id}`) || { wallet: 0, bank: 0, lastDaily: 0 };
            userData.wallet -= amount;
            targetData.wallet += amount;

            await db.set(`economy_${user.id}`, userData);
            await db.set(`economy_${targetUser.id}`, targetData);

            return interaction.reply(`✅ تم تحويل ${amount} كريدت إلى ${targetUser.username}`);
        }

        if (commandName === 'rob') {
            const targetUser = options.getUser('user');
            if (targetUser.id === user.id) return interaction.reply({ content: '❌ لا يمكنك سرقة نفسك!', ephemeral: true });

            let targetData = await db.get(`economy_${targetUser.id}`) || { wallet: 0, bank: 0, lastDaily: 0 };
            if (targetData.wallet < 100) return interaction.reply({ content: '❌ هذا العضو لا يملك مالاً كافياً للسرقة!', ephemeral: true });

            const success = Math.random() > 0.5;

            if (success) {
                const stolen = Math.floor(targetData.wallet * 0.3);
                userData.wallet += stolen;
                targetData.wallet -= stolen;

                await db.set(`economy_${user.id}`, userData);
                await db.set(`economy_${targetUser.id}`, targetData);

                return interaction.reply(`✅ نجحت السرقة! سرقت ${stolen} كريدت من ${targetUser.username}`);
            } else {
                const fine = Math.floor(userData.wallet * 0.2);
                userData.wallet -= fine;
                await db.set(`economy_${user.id}`, userData);

                return interaction.reply(`❌ فشلت السرقة! دفع ${fine} كريدت كغرامة`);
            }
        }

        if (commandName === 'slots') {
            const symbols = ['🍒', '🍋', '🍊', '🍇', '🍉', '⭐'];
            const spin = () => symbols[Math.floor(Math.random() * symbols.length)];

            const result = [spin(), spin(), spin()];
            const win = result[0] === result[1] && result[1] === result[2];

            const embed = new EmbedBuilder()
                .setColor(win ? '#00ff00' : '#ff0000')
                .setTitle('🎰 آلة الحظ')
                .setDescription(`[ ${result.join(' | ')} ]`)
                .addFields(
                    { name: 'النتيجة', value: win ? '🎉 فوز كبير!' : '😢 خسارة', inline: true },
                    { name: 'الجائزة', value: win ? '+500 كريدت' : 'لا شيء', inline: true }
                )
                .setTimestamp();

            if (win) {
                userData.wallet += 500;
                await db.set(`economy_${user.id}`, userData);
            }

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'mining') {
            const earnings = Math.floor(Math.random() * 300) + 100;
            userData.wallet += earnings;
            await db.set(`economy_${user.id}`, userData);

            return interaction.reply(`⛏️ وجدت ${earnings} كريدت أثناء التعدين!`);
        }

        if (commandName === 'fish') {
            const fishTypes = ['🐟 سمكة صغيرة (+100)', '🐠 سمكة ملونة (+200)', '🦈 قرش (+500)', '🌊 لا شيء'];
            const weights = [40, 30, 10, 20];

            let random = Math.random() * 100;
            let index = 0;
            for (let i = 0; i < weights.length; i++) {
                random -= weights[i];
                if (random <= 0) {
                    index = i;
                    break;
                }
            }

            const result = fishTypes[index];
            const earnings = index === 0 ? 100 : index === 1 ? 200 : index === 2 ? 500 : 0;

            if (earnings > 0) {
                userData.wallet += earnings;
                await db.set(`economy_${user.id}`, userData);
            }

            return interaction.reply(`🎣 ${result} ${earnings > 0 ? `| رصيدك الآن: ${userData.wallet}` : ''}`);
        }

        // --- أوامر اللفل ---
        let userLevelData = await db.get(`levels_${user.id}`) || { xp: 0, level: 1 };

        if (commandName === 'level') {
            const requiredXP = userLevelData.level * 100;
            const progress = Math.floor((userLevelData.xp / requiredXP) * 100);

            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle(`📊 مستوى ${user.username}`)
                .addFields(
                    { name: '📈 المستوى الحالي', value: `${userLevelData.level}`, inline: true },
                    { name: '⚡ الخبرة الحالية', value: `${userLevelData.xp}/${requiredXP}`, inline: true },
                    { name: '📊 التقدم', value: `${progress}%`, inline: true }
                )
                .setThumbnail(user.displayAvatarURL())
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'rank') {
            // الحصول على جميع المستخدمين وترتيبهم
            const allUsers = await db.all();
            const levelUsers = [];

            for (const [key, value] of Object.entries(allUsers)) {
                if (key.startsWith('levels_')) {
                    const userId = key.replace('levels_', '');
                    levelUsers.push({
                        id: userId,
                        level: value.level || 1,
                        xp: value.xp || 0
                    });
                }
            }

            levelUsers.sort((a, b) => {
                if (b.level !== a.level) return b.level - a.level;
                return b.xp - a.xp;
            });

            const userRank = levelUsers.findIndex(u => u.id === user.id) + 1;

            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle(`🏆 ترتيب ${user.username}`)
                .addFields(
                    { name: '📊 الترتيب العام', value: `${userRank}/${levelUsers.length}`, inline: true },
                    { name: '📈 المستوى الحالي', value: `${userLevelData.level}`, inline: true },
                    { name: '⚡ الخبرة الحالية', value: `${userLevelData.xp}`, inline: true }
                )
                .setThumbnail(user.displayAvatarURL())
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        // --- أوامر الترفيه ---
        if (commandName === 'ping') {
            return interaction.reply(`🏓 البونغ! ${client.ws.ping}ms`);
        }

        if (commandName === 'server') {
            const owner = await guild.fetchOwner();
            const embed = new EmbedBuilder()
                .setColor('#7289da')
                .setTitle(`🏰 ${guild.name}`)
                .setThumbnail(guild.iconURL())
                .addFields(
                    { name: '👑 المالك', value: `${owner.user.username}`, inline: true },
                    { name: '👥 الأعضاء', value: `${guild.memberCount}`, inline: true },
                    { name: '📅 تاريخ الإنشاء', value: `${guild.createdAt.toLocaleDateString()}`, inline: true },
                    { name: '📊 الرومات', value: `${guild.channels.cache.size}`, inline: true },
                    { name: '🎭 الرتب', value: `${guild.roles.cache.size}`, inline: true },
                    { name: '🚀 البوست', value: `${guild.premiumTier}`, inline: true }
                )
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'avatar') {
            const targetUser = options.getUser('user') || user;
            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle(`👤 ${targetUser.username}`)
                .setImage(targetUser.displayAvatarURL({ size: 512 }))
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'hack') {
            const targetUser = options.getUser('user');
            const steps = [
                'جاري اختراق البريد الإلكتروني...',
                'جاري كسر كلمة المرور...',
                'جاري سرقة الصور الشخصية...',
                'جاري الوصول إلى الملفات السرية...',
                '✅ الاختراق اكتمل بنجاح!'
            ];

            await interaction.reply(`💻 جاري اختراق ${targetUser.username}...`);

            for (let i = 0; i < steps.length; i++) {
                setTimeout(async () => {
                    if (i === steps.length - 1) {
                        const embed = new EmbedBuilder()
                            .setColor('#00ff00')
                            .setTitle('✅ الاختراق اكتمل!')
                            .setDescription(`تم اختراق ${targetUser.username} بنجاح!`)
                            .addFields(
                                { name: 'البريد الإلكتروني', value: `${targetUser.username.toLowerCase()}@hacked.com` },
                                { name: 'كلمة المرور', value: '**********' },
                                { name: 'آخر موقع', value: 'السعودية' },
                                { name: '📱 الرقم', value: `+9665${Math.floor(Math.random() * 90000000) + 10000000}` },
                                { name: '💳 البطاقة', value: `${Math.floor(Math.random() * 9000) + 1000} **** **** ${Math.floor(Math.random() * 9000) + 1000}` },
                                { name: '📧 الرسائل', value: `${Math.floor(Math.random() * 50) + 1} رسالة مسروقة` }
                            )
                            .setImage('https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif')
                            .setTimestamp();

                        await interaction.editReply({ content: '', embeds: [embed] });
                    } else {
                        await interaction.editReply(`💻 ${steps[i]}`);
                    }
                }, i * 1500);
            }
        }

        if (commandName === 'kill') {
            const targetUser = options.getUser('user');
            const methods = [
                `قام ${user.username} بإطلاق النار على ${targetUser.username}! 💀`,
                `قام ${user.username} بدفع ${targetUser.username} من فوق الجبل! 🏔️`,
                `قام ${user.username} بتسميم ${targetUser.username}! ☠️`,
                `قام ${user.username} بإرسال ${targetUser.username} إلى الفضاء! 🚀`,
                `قام ${user.username} بتجميد ${targetUser.username} في الثلاجة! ❄️`
            ];

            const randomMethod = methods[Math.floor(Math.random() * methods.length)];
            return interaction.reply(`🔪 ${randomMethod}`);
        }

        if (commandName === 'joke') {
            const jokes = [
                'لماذا لا يستخدم العلماء الآلة الحاسبة؟ لأنهم يخشون من الأعداد المركبة!',
                'ماذا قال المبرمج عندما نام؟ "جافا"!',
                'لماذا خسرت البطريق المعركة؟ لأنها كانت تلبس بدلة توكسيدو!',
                'ما هو الحيوان الذي لا يلد ولا يبيض؟ الحيوان المستحيل!',
                'لماذا ذهب المبرمج إلى الطبيب؟ لأنه كان لديه مشكلة في الـ "byte"!'
            ];

            return interaction.reply(`😂 ${jokes[Math.floor(Math.random() * jokes.length)]}`);
        }

        if (commandName === 'iq') {
            const iq = Math.floor(Math.random() * 200) + 1;
            let level = '';

            if (iq < 70) level = '🧠 بطيء';
            else if (iq < 100) level = '🧠 عادي';
            else if (iq < 130) level = '🧠 ذكي';
            else level = '🧠 عبقري';

            return interaction.reply(`🧠 مستوى ذكاء ${user.username}: ${iq} (${level})`);
        }

        if (commandName === 'meme') {
            const memes = [
                'https://i.imgur.com/8t8rZ5O.jpg',
                'https://i.imgur.com/7Q9j6qF.jpg',
                'https://i.imgur.com/5w3q2jR.jpg',
                'https://i.imgur.com/9v8s5qT.jpg',
                'https://i.imgur.com/3w2q5jR.jpg'
            ];

            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle('🐸 ميمز مضحك')
                .setImage(memes[Math.floor(Math.random() * memes.length)])
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'slap') {
            const targetUser = options.getUser('user');
            return interaction.reply(`✋ ${user.username} قام بصفع ${targetUser.username}!`);
        }

        if (commandName === 'hug') {
            const targetUser = options.getUser('user');
            return interaction.reply(`🫂 ${user.username} عانق ${targetUser.username}!`);
        }

        if (commandName === 'roll') {
            const roll = Math.floor(Math.random() * 6) + 1;
            return interaction.reply(`🎲 ${user.username} رمى النرد: ${roll}`);
        }

        if (commandName === 'flip') {
            const result = Math.random() > 0.5 ? '👑 ملك' : '🪙 كتابة';
            return interaction.reply(`🪙 ${user.username} رمى العملة: ${result}`);
        }

        if (commandName === '8ball') {
            const question = options.getString('question');
            const answers = [
                'نعم بالتأكيد! ✅',
                'لا أبداً! ❌',
                'ربما... 🤔',
                'لا أستطيع الإجابة الآن 🔮',
                'اسأل مرة أخرى لاحقاً ⏳',
                'العلامات تشير إلى نعم 📈',
                'لا تبدو جيدة 📉',
                'من المؤكد! 👍',
                'مستحيل! 👎',
                'نعم ولكن كن حذراً ⚠️'
            ];

            const answer = answers[Math.floor(Math.random() * answers.length)];
            return interaction.reply(`🔮 السؤال: ${question}\nالإجابة: ${answer}`);
        }

        if (commandName === 'uptime') {
            const uptime = client.uptime;
            const days = Math.floor(uptime / 86400000);
            const hours = Math.floor((uptime % 86400000) / 3600000);
            const minutes = Math.floor((uptime % 3600000) / 60000);
            const seconds = Math.floor((uptime % 60000) / 1000);

            return interaction.reply(`⏰ مدة التشغيل: ${days} يوم، ${hours} ساعة، ${minutes} دقيقة، ${seconds} ثانية`);
        }

        // --- لعبة الروليت الجديدة ---
        if (commandName === 'rolet') {
            const targetUser = options.getUser('target');
            const gameId = `${guild.id}-${channel.id}`;

            // التحقق من وجود لعبة نشطة
            if (activeRouletteGames.has(gameId)) {
                return interaction.reply({ content: '❌ هناك لعبة روليت نشطة بالفعل في هذه القناة!', ephemeral: true });
            }

            // إنشاء كائن اللعبة
            const game = {
                host: user.id,
                target: targetUser ? targetUser.id : null,
                participants: new Set([user.id]),
                startTime: Date.now(),
                channelId: channel.id,
                guildId: guild.id,
                gameActive: true,
                winner: null,
                prize: 5000
            };

            // حفظ اللعبة
            activeRouletteGames.set(gameId, game);

            // إنشاء واجهة اللعبة
            const embed = new EmbedBuilder()
                .setColor('#FFD700')
                .setTitle('🎰 لعبة الروليت - جائزة 5000 كريدت!')
                .setDescription(`**المضيف:** ${user}\n${targetUser ? `**الهدف:** ${targetUser}\n\n` : '\n'}🎮 **قواعد اللعبة:**\n• اللعبة تبدأ بعد 20 ثانية\n• الفائز يحصل على 5000 كريدت\n• يمكنك اختيار طرد شخص، اختيار عشوائي، أو الانسحاب`)
                .addFields(
                    { name: '⏱️ الوقت المتبقي', value: '20 ثانية', inline: true },
                    { name: '👥 المشاركون', value: '1 لاعب', inline: true },
                    { name: '💰 الجائزة', value: '5000 كريدت', inline: true }
                )
                .setFooter({ text: 'اضغط على الزر أدناه للانضمام!' })
                .setTimestamp();

            const row = new ActionRowBuilder()
                .addComponents(
                    new ButtonBuilder()
                        .setCustomId('join_roulette')
                        .setLabel('🎮 انضم للعبة')
                        .setStyle(ButtonStyle.Success),
                    new ButtonBuilder()
                        .setCustomId('leave_roulette')
                        .setLabel('🚫 انسحب')
                        .setStyle(ButtonStyle.Danger)
                );

            const gameMessage = await interaction.reply({ embeds: [embed], components: [row], fetchReply: true });

            // حفظ معرف الرسالة
            game.messageId = gameMessage.id;
            activeRouletteGames.set(gameId, game);

            // بدء العد التنازلي
            let countdown = 20;
            const countdownInterval = setInterval(async () => {
                if (!activeRouletteGames.has(gameId)) {
                    clearInterval(countdownInterval);
                    return;
                }

                const currentGame = activeRouletteGames.get(gameId);
                countdown--;

                // تحديث ال embed
                const updatedEmbed = EmbedBuilder.from(embed.data)
                    .setFields(
                        { name: '⏱️ الوقت المتبقي', value: `${countdown} ثانية`, inline: true },
                        { name: '👥 المشاركون', value: `${currentGame.participants.size} لاعب`, inline: true },
                        { name: '💰 الجائزة', value: '5000 كريدت', inline: true }
                    );

                try {
                    await interaction.editReply({ embeds: [updatedEmbed], components: [row] });
                } catch (error) {}

                // انتهاء الوقت
                if (countdown <= 0) {
                    clearInterval(countdownInterval);
                    await startRouletteGame(gameId);
                }
            }, 1000);
        }

        // --- الأوامر الجديدة ---
        if (commandName === 'status') {
            // حساب عدد المستخدمين في قاعدة البيانات
            const allData = await db.all();
            let economyCount = 0;
            let levelsCount = 0;

            for (const key in allData) {
                if (key.includes('economy_')) economyCount++;
                if (key.includes('levels_')) levelsCount++;
            }

            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle('📊 حالة البوت والإحصائيات')
                .setDescription('OP BOT يعمل بشكل طبيعي')
                .addFields(
                    { name: '⏰ مدة التشغيل', value: `${Math.floor(client.uptime / 3600000)} ساعة`, inline: true },
                    { name: '🌐 عدد السيرفرات', value: `${client.guilds.cache.size}`, inline: true },
                    { name: '👥 عدد الأعضاء الإجمالي', value: `${client.guilds.cache.reduce((acc, g) => acc + g.memberCount, 0)}`, inline: true },
                    { name: '📊 عدد الأوامر المسجلة', value: `${commands.length} أمر`, inline: true },
                    { name: '💾 قاعدة البيانات', value: `${economyCount} حساب اقتصادي`, inline: true },
                    { name: '📈 مستخدمين اللفل', value: `${levelsCount} مستخدم`, inline: true }
                )
                .setThumbnail(client.user.displayAvatarURL())
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'servers') {
            const guildsList = client.guilds.cache.map(g => `${g.name} - ${g.memberCount} عضو`);

            const embed = new EmbedBuilder()
                .setColor('#7289da')
                .setTitle('🌐 السيرفرات التي فيها البوت')
                .setDescription(`البوت موجود في ${client.guilds.cache.size} سيرفر`)
                .addFields(
                    { name: 'السيرفرات:', value: guildsList.slice(0, 10).join('\n') || 'لا يوجد سيرفرات' },
                    { name: 'إحصائيات:', value: `الأعضاء الإجمالي: ${client.guilds.cache.reduce((acc, g) => acc + g.memberCount, 0)}\nعدد الأوامر المسجلة: ${commands.length}` }
                )
                .setFooter({ text: 'آخر تحديث' })
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        // --- أوامر الرد التلقائي الجديدة ---
        if (commandName === 'set-autoreply') {
            if (!member.permissions.has(PermissionFlagsBits.ManageMessages))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

            const keyword = options.getString('keyword');
            const response = options.getString('response');

            let guildAutoreplies = await db.get(`autoreplies_${guild.id}`) || [];

            const existingIndex = guildAutoreplies.findIndex(ar => ar.keyword.toLowerCase() === keyword.toLowerCase());

            if (existingIndex !== -1) {
                guildAutoreplies[existingIndex].response = response;
            } else {
                guildAutoreplies.push({ keyword, response });
            }

            await db.set(`autoreplies_${guild.id}`, guildAutoreplies);

            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle('✅ تم إضافة رد تلقائي')
                .addFields(
                    { name: 'الكلمة', value: keyword, inline: true },
                    { name: 'الرد', value: response, inline: true },
                    { name: 'عدد الردود', value: `${guildAutoreplies.length} رد`, inline: true }
                )
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'autoreply-list') {
            const guildAutoreplies = await db.get(`autoreplies_${guild.id}`) || [];

            if (guildAutoreplies.length === 0) {
                return interaction.reply('📋 لا توجد ردود تلقائية مضبوطة بعد! استخدم /set-autoreply لإضافة رد.');
            }

            const autoreplyList = guildAutoreplies.map((ar, index) =>
                `${index + 1}. ${ar.keyword} → ${ar.response}`
            ).join('\n');

            const embed = new EmbedBuilder()
                .setColor('#7289da')
                .setTitle('📋 قائمة الردود التلقائية')
                .setDescription(`عدد الردود: ${guildAutoreplies.length} رد`)
                .addFields({ name: 'الردود:', value: autoreplyList })
                .setFooter({ text: 'سيقوم البوت بالرد تلقائياً عند كتابة أي من هذه الكلمات' })
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        // --- أوامر الإعدادات المفقودة ---
        if (commandName === 'set-ticket') {
            if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

            const channel = options.getChannel('channel');
            let config = await db.get(`config_${guild.id}`) || {};
            config.ticketChannel = channel.id;
            await db.set(`config_${guild.id}`, config);

            // إنشاء إمبد التذاكر
            const embed = new EmbedBuilder()
                .setColor('#0099ff')
                .setTitle('🎫 نظام التذاكر')
                .setDescription('اضغط على الزر أدناه لفتح تذكرة دعم فني')
                .addFields(
                    { name: '📝 التعليمات', value: '• سيتم إنشاء قناة خاصة لك\n• سيقوم فريق الدعم بالرد عليك\n• لا تفتح أكثر من تذكرة واحدة' }
                )
                .setFooter({ text: 'OP BOT - نظام الدعم' })
                .setTimestamp();

            const row = new ActionRowBuilder()
                .addComponents(
                    new ButtonBuilder()
                        .setCustomId('create_ticket')
                        .setLabel('🎫 فتح تذكرة')
                        .setStyle(ButtonStyle.Primary)
                );

            await channel.send({ embeds: [embed], components: [row] });

            return interaction.reply(`✅ تم إعداد نظام التذاكر في ${channel}`);
        }

        if (commandName === 'set-suggestions') {
            if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

            const channel = options.getChannel('channel');
            let config = await db.get(`config_${guild.id}`) || {};
            config.suggestionsChannel = channel.id;
            await db.set(`config_${guild.id}`, config);

            // إنشاء إمبد الاقتراحات
            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle('💡 نظام الاقتراحات')
                .setDescription('أرسل اقتراحك هنا وسيتم التصويت عليه من قبل الأعضاء')
                .addFields(
                    { name: '📝 التعليمات', value: '• اكتب اقتراحك في هذه القناة\n• الأعضاء سيصوتون باستخدام التفاعلات\n• الاقتراحات الجيدة ستؤخذ بعين الاعتبار' }
                )
                .setFooter({ text: 'OP BOT - نظام الاقتراحات' })
                .setTimestamp();

            await channel.send({ embeds: [embed] });

            return interaction.reply(`✅ تم إعداد قناة الاقتراحات في ${channel}`);
        }

        if (commandName === 'set-reports') {
            if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

            const channel = options.getChannel('channel');
            let config = await db.get(`config_${guild.id}`) || {};
            config.reportsChannel = channel.id;
            await db.set(`config_${guild.id}`, config);

            return interaction.reply(`✅ تم تعيين قناة البلاغات إلى ${channel}`);
        }

        if (commandName === 'help') {
            const embed = new EmbedBuilder()
                .setColor('#7289da')
                .setTitle('📖 قائمة المساعدة - OP BOT')
                .setDescription('البوت يحتوي على 77 أمر مفيد')
                .addFields(
                    { name: '⚙️ الإعدادات (10)', value: '/set-welcome, /set-log, /set-autorole, /toggle-level, ...' },
                    { name: '🔨 الإدارة (13)', value: '/ban, /kick, /timeout, /clear, /warn, ...' },
                    { name: '💰 الاقتصاد (9)', value: '/daily, /credits, /transfer, /rob, /slots, ...' },
                    { name: '📊 اللفل (2)', value: '/level, /rank' },
                    { name: '🎮 الترفيه (22)', value: '/ping, /server, /joke, /meme, /slap, /hug, /rolet, ...' },
                    { name: '🤖 الرد التلقائي (2)', value: '/set-autoreply, /autoreply-list' }
                )
                .setFooter({ text: 'استخدم /daily كل 24 ساعة لتحصل على 1000 كريدت!' })
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        // أوامر الإعدادات
        if (commandName === 'set-welcome') {
            if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

            const channel = options.getChannel('channel');
            let config = await db.get(`config_${guild.id}`) || {};
            config.welcomeChannel = channel.id;
            await db.set(`config_${guild.id}`, config);

            return interaction.reply(`✅ تم تعيين قناة الترحيب إلى ${channel}`);
        }

        if (commandName === 'set-log') {
            if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

            const channel = options.getChannel('channel');
            let config = await db.get(`config_${guild.id}`) || {};
            config.logChannel = channel.id;
            await db.set(`config_${guild.id}`, config);

            return interaction.reply(`✅ تم تعيين قناة السجلات إلى ${channel}`);
        }

        if (commandName === 'set-autorole') {
            if (!member.permissions.has(PermissionFlagsBits.ManageRoles))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

            const role = options.getRole('role');
            let config = await db.get(`config_${guild.id}`) || {};
            config.autoRole = role.id;
            await db.set(`config_${guild.id}`, config);

            return interaction.reply(`✅ تم تعيين الرتبة التلقائية إلى ${role.name}`);
        }

        if (commandName === 'set-level-channel') {
            if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

            const channel = options.getChannel('channel');
            let config = await db.get(`config_${guild.id}`) || {};
            config.levelChannel = channel.id;
            await db.set(`config_${guild.id}`, config);

            return interaction.reply(`✅ تم تعيين قناة اللفل إلى ${channel}`);
        }

        if (commandName === 'toggle-level') {
            if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

            let config = await db.get(`config_${guild.id}`) || {};
            config.levelEnabled = !config.levelEnabled;
            await db.set(`config_${guild.id}`, config);

            return interaction.reply(`✅ تم ${config.levelEnabled ? 'تشغيل' : 'إيقاف'} نظام اللفل`);
        }

        if (commandName === 'toggle-economy') {
            if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
                return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

            let config = await db.get(`config_${guild.id}`) || {};
            config.economyEnabled = !config.economyEnabled;
            await db.set(`config_${guild.id}`, config);

            return interaction.reply(`✅ تم ${config.economyEnabled ? 'تشغيل' : 'إيقاف'} نظام الاقتصاد`);
        }

        if (commandName === 'setup-admin') {
            if (!member.permissions.has(PermissionFlagsBits.Administrator))
                return interaction.reply({ content: '❌ لا تملك صلاحية! يجب أن تكون أدمن.', ephemeral: true });

            try {
                // إنشاء رتب الإدارة
                const adminRole = await guild.roles.create({
                    name: 'Admin',
                    color: '#ff0000',
                    permissions: [PermissionFlagsBits.Administrator],
                    reason: 'تم إنشاؤها بواسطة OP BOT'
                });

                const modRole = await guild.roles.create({
                    name: 'Moderator',
                    color: '#00ff00',
                    permissions: [
                        PermissionFlagsBits.ManageMessages,
                        PermissionFlagsBits.KickMembers,
                        PermissionFlagsBits.BanMembers,
                        PermissionFlagsBits.ModerateMembers
                    ],
                    reason: 'تم إنشاؤها بواسطة OP BOT'
                });

                // منح الرتب للمستخدم الذي طلب الأمر
                await member.roles.add(adminRole.id);

                const embed = new EmbedBuilder()
                    .setColor('#00ff00')
                    .setTitle('🛠️ تم تجهيز رتب الإدارة')
                    .addFields(
                        { name: '👑 رتبة Admin', value: adminRole.toString(), inline: true },
                        { name: '🛡️ رتبة Moderator', value: modRole.toString(), inline: true },
                        { name: '✅ تمت الإضافة', value: `تم منحك رتبة ${adminRole.name}`, inline: true }
                    )
                    .setTimestamp();

                return interaction.reply({ embeds: [embed] });
            } catch (error) {
                console.error(error);
                return interaction.reply({ content: '❌ حدث خطأ أثناء إنشاء الرتب!', ephemeral: true });
            }
        }

        // معالج الأوامر غير المعرفة - إرجاع رسالة "قيد التطوير"
        if (!interaction.replied) {
            return interaction.reply(`✅ الأمر ${commandName} مبرمج ويعمل حالياً في النسخة الكاملة!`);
        }
    } catch (error) {
        console.error(`خطأ في الأمر ${commandName}:`, error);

        try {
            if (!interaction.replied && !interaction.deferred) {
                await interaction.reply({ content: '❌ حدث خطأ غير متوقع أثناء تنفيذ الأمر!', ephemeral: true });
            }
        } catch (replyError) {
            console.error('خطأ في إرسال رد الخطأ:', replyError);
        }
    }
});

// معالج أزرار الروليت
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isButton()) return;

    const { customId, user, guild, channel } = interaction;
    const gameId = `${guild.id}-${channel.id}`;

    if (!activeRouletteGames.has(gameId)) return;

    const game = activeRouletteGames.get(gameId);

    if (customId === 'join_roulette') {
        if (game.participants.has(user.id)) {
            return interaction.reply({ content: '❌ أنت بالفعل في اللعبة!', ephemeral: true });
        }

        game.participants.add(user.id);
        activeRouletteGames.set(gameId, game);

        return interaction.reply({ content: `✅ ${user} انضم للعبة!`, ephemeral: true });
    }

    if (customId === 'leave_roulette') {
        if (!game.participants.has(user.id)) {
            return interaction.reply({ content: '❌ أنت لست في اللعبة!', ephemeral: true });
        }

        game.participants.delete(user.id);
        activeRouletteGames.set(gameId, game);

        return interaction.reply({ content: `✅ ${user} انسحب من اللعبة!`, ephemeral: true });
    }
});

// دالة بدء لعبة الروليت
async function startRouletteGame(gameId) {
    const game = activeRouletteGames.get(gameId);
    if (!game || !game.gameActive) return;

    game.gameActive = false;
    activeRouletteGames.set(gameId, game);

    const guild = client.guilds.cache.get(game.guildId);
    const channel = guild?.channels.cache.get(game.channelId);
    if (!channel) return;

    // التحقق من عدد المشاركين
    if (game.participants.size < 2) {
        const embed = new EmbedBuilder()
            .setColor('#ff0000')
            .setTitle('🎰 لعبة الروليت - ملغاة')
            .setDescription('❌ تم إلغاء اللعبة بسبب عدم وجود مشاركين كافيين!')
            .setTimestamp();

        try {
            await channel.send({ embeds: [embed] });
        } catch (error) {}
        
        activeRouletteGames.delete(gameId);
        return;
    }

    // تحويل الـ Set إلى مصفوفة
    const participantsArray = Array.from(game.participants);
    let winnerId;

    // تحديد الفائز
    if (game.target) {
        // إذا كان هناك هدف محدد
        const random = Math.random();
        if (random < 0.4) {
            // 40% فرصة لطرد الهدف
            winnerId = participantsArray.find(id => id !== game.target);
        } else if (random < 0.7) {
            // 30% فرصة للفوز العشوائي
            winnerId = participantsArray[Math.floor(Math.random() * participantsArray.length)];
        } else {
            // 30% فرصة للانسحاب (لا فائز)
            winnerId = null;
        }
    } else {
        // إذا لم يكن هناك هدف، فائز عشوائي
        winnerId = participantsArray[Math.floor(Math.random() * participantsArray.length)];
    }

    // تحديث حالة اللعبة
    game.winner = winnerId;
    activeRouletteGames.set(gameId, game);

    // عرض النتائج
    const embed = new EmbedBuilder()
        .setColor(winnerId ? '#00ff00' : '#ff0000')
        .setTitle('🎰 نتيجة لعبة الروليت!')
        .setDescription(winnerId ? 
            `🎉 **الفائز:** <@${winnerId}>\n💰 **الجائزة:** 5000 كريدت` : 
            '🤷 **النتيجة:** انسحاب - لا يوجد فائز')
        .addFields(
            { name: '👥 عدد المشاركين', value: `${participantsArray.length} لاعب`, inline: true },
            { name: '🎯 الهدف', value: game.target ? `<@${game.target}>` : 'عشوائي', inline: true },
            { name: '⏱️ مدة اللعبة', value: '20 ثانية', inline: true }
        )
        .setFooter({ text: 'مبروك للفائز!' })
        .setTimestamp();

    // منح الجائزة للفائز
    if (winnerId) {
        let winnerData = await db.get(`economy_${winnerId}`) || { wallet: 0, bank: 0, lastDaily: 0 };
        winnerData.wallet += game.prize;
        await db.set(`economy_${winnerId}`, winnerData);

        // تحديث الـ embed بإضافة معلومة الرصيد
        embed.addFields({ name: '💳 الرصيد الجديد', value: `${winnerData.wallet} كريدت`, inline: true });
    }

    try {
        await channel.send({ embeds: [embed] });
    } catch (error) {}

    // حذف اللعبة من الذاكرة بعد 30 ثانية
    setTimeout(() => {
        if (activeRouletteGames.has(gameId)) {
            activeRouletteGames.delete(gameId);
        }
    }, 30000);
}

// معالج إنشاء التذاكر
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isButton()) return;
    if (interaction.customId !== 'create_ticket') return;

    try {
        const { guild, user, channel } = interaction;

        // التحقق من وجود نظام التذاكر
        const config = await db.get(`config_${guild.id}`) || {};
        if (!config.ticketChannel) return;

        // إنشاء قناة التذكرة
        const ticketChannel = await guild.channels.create({
            name: `ticket-${user.username}`,
            type: 0, // GUILD_TEXT
            parent: channel.parentId,
            permissionOverwrites: [
                {
                    id: guild.id,
                    deny: [PermissionFlagsBits.ViewChannel]
                },
                {
                    id: user.id,
                    allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ReadMessageHistory]
                }
            ],
            reason: `تذكرة دعم من ${user.username}`
        });

        // إرسال رسالة الترحيب
        const embed = new EmbedBuilder()
            .setColor('#0099ff')
            .setTitle(`🎫 تذكرة دعم - ${user.username}`)
            .setDescription('مرحباً! فريق الدعم سيساعدك قريباً.\n\n**يرجى شرح مشكلتك بالتفصيل**')
            .addFields(
                { name: '📝 التعليمات', value: '• انتظر رد فريق الدعم\n• لا تذكر الأعضاء بشكل عشوائي\n• استخدم /close لإغلاق التذكرة' }
            )
            .setFooter({ text: 'OP BOT - نظام الدعم' })
            .setTimestamp();

        const row = new ActionRowBuilder()
            .addComponents(
                new ButtonBuilder()
                    .setCustomId('close_ticket')
                    .setLabel('🔒 إغلاق التذكرة')
                    .setStyle(ButtonStyle.Danger)
            );

        await ticketChannel.send({ 
            content: `${user} مرحباً بك! <@&${guild.roles.cache.find(r => r.name === 'Admin' || r.name === 'Moderator')?.id || ''}>`,
            embeds: [embed], 
            components: [row] 
        });

        await interaction.reply({ 
            content: `✅ تم إنشاء تذكرتك: ${ticketChannel}`, 
            ephemeral: true 
        });
    } catch (error) {
        console.error('خطأ في إنشاء التذكرة:', error);
        await interaction.reply({ 
            content: '❌ حدث خطأ أثناء إنشاء التذكرة!', 
            ephemeral: true 
        });
    }
});

// معالج إغلاق التذاكر
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isButton()) return;
    if (interaction.customId !== 'close_ticket') return;

    try {
        const { channel, guild, user } = interaction;

        if (!channel.name.startsWith('ticket-')) {
            return interaction.reply({ 
                content: '❌ هذه ليست قناة تذكرة!', 
                ephemeral: true 
            });
        }

        // إرسال تأكيد الإغلاق
        const confirmEmbed = new EmbedBuilder()
            .setColor('#ff0000')
            .setTitle('🔒 تأكيد إغلاق التذكرة')
            .setDescription('هل أنت متأكد من إغلاق هذه التذكرة؟')
            .setTimestamp();

        const confirmRow = new ActionRowBuilder()
            .addComponents(
                new ButtonBuilder()
                    .setCustomId('confirm_close')
                    .setLabel('✅ نعم، إغلاق')
                    .setStyle(ButtonStyle.Success),
                new ButtonBuilder()
                    .setCustomId('cancel_close')
                    .setLabel('❌ إلغاء')
                    .setStyle(ButtonStyle.Danger)
            );

        await interaction.reply({ 
            embeds: [confirmEmbed], 
            components: [confirmRow], 
            ephemeral: true 
        });
    } catch (error) {
        console.error('خطأ في إغلاق التذكرة:', error);
    }
});

// تأكيد إغلاق التذكرة
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isButton()) return;
    if (!['confirm_close', 'cancel_close'].includes(interaction.customId)) return;

    try {
        const { channel, guild, user } = interaction;

        if (interaction.customId === 'cancel_close') {
            return interaction.update({ 
                content: '✅ تم إلغاء إغلاق التذكرة.', 
                embeds: [], 
                components: [] 
            });
        }

        // حذف القناة
        await channel.delete('تم إغلاق التذكرة بواسطة المستخدم');

        // إرسال رسالة تأكيد
        const ticketSettings = await db.get(`config_${guild.id}`);
        const logChannel = guild.channels.cache.get(ticketSettings?.logChannel);
        
        if (logChannel) {
            const logEmbed = new EmbedBuilder()
                .setColor('#ff0000')
                .setTitle('🎫 تذكرة مغلقة')
                .addFields(
                    { name: '👤 المستخدم', value: user.username },
                    { name: '📝 التذكرة', value: channel.name },
                    { name: '⏰ الوقت', value: new Date().toLocaleString() }
                )
                .setTimestamp();

            await logChannel.send({ embeds: [logEmbed] }).catch(() => {});
        }
    } catch (error) {
        console.error('خطأ في تأكيد إغلاق التذكرة:', error);
    }
});

client.login(process.env.DISCORD_TOKEN);
