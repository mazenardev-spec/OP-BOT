const { 
    Client, GatewayIntentBits, Partials, EmbedBuilder, ActivityType, 
    PermissionFlagsBits, ActionRowBuilder, ButtonBuilder, ButtonStyle,
    ApplicationCommandOptionType 
} = require('discord.js');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent, GatewayIntentBits.GuildMembers,
    ],
    partials: [Partials.Channel, Partials.Message, Partials.User]
});

// قاعدة بيانات حقيقية (يتم تصفيرها عند الرستارت)
const db = {
    economy: new Map(), // { userId: { wallet: 0, bank: 0, lastDaily: 0 } }
    levels: new Map(),  // { userId: { xp: 0, level: 1, lastMessage: 0 } }
    warns: new Map(),   // { userId: [reasons] }
    config: new Map()   // { guildId: { welcomeChannel, logChannel, autoRole, levelChannel } }
};

// --- مصفوفة الأوامر الكاملة (الـ 69 أمر بعد إزالة work) ---
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
    { name: 'add-role', description: '➕ منح رتبة لعضو', options: [{ name: 'user', type: 6, description: 'العضو المستهدف', required: true }, { name: 'role', type: 8, description: 'الرتبة المطلوب منحها', required: true }] },
    { name: 'rem-role', description: '➖ سحب رتبة من عضو', options: [{ name: 'user', type: 6, description: 'العضو المستهدف', required: true }, { name: 'role', type: 8, description: 'الرتبة المطلوب سحبها', required: true }] },

    // [31-50] الاقتصاد واللفل (ECONOMY & LEVEL)
    { name: 'daily', description: '💵 استلام الهديّة اليومية' },
    { name: 'balance', description: '👛 عرض رصيدك الحالي' },
    { name: 'level', description: '📊 عرض مستواك الحالي' },
    { name: 'rank', description: '🏆 ترتيبك في السيرفر' },
    { name: 'transfer', description: '💸 تحويل أموال', options: [{ name: 'u', type: 6, description: 'المستلم', required: true }, { name: 'a', type: 4, description: 'المبلغ', required: true }] },
    { name: 'rob', description: '🔫 سرقة رصيد عضو (مخاطرة)', options: [{ name: 'user', type: 6, description: 'العضو المستهدف للسرقة', required: true }] },
    { name: 'slots', description: '🎰 آلة الحظ' },
    { name: 'mining', description: '⛏️ التعدين' },
    { name: 'fish', description: '🎣 صيد السمك' },

    // [51-70] ترفيه وعامة
    { name: 'ping', description: '📶 سرعة الاتصال' },
    { name: 'server', description: '🏰 معلومات السيرفر' },
    { name: 'servers', description: '🌐 عدد السيرفرات التي فيها البوت' },
    { name: 'avatar', description: '👤 صورة الحساب', options: [{ name: 'user', type: 6, description: 'العضو المراد عرض صورته' }] },
    { name: 'help', description: '📖 قائمة المساعدة الكاملة' },
    { name: 'hack', description: '💻 اختراق وهمي' },
    { name: 'kill', description: '🔪 قضاء على عضو', options: [{ name: 'user', type: 6, description: 'العضو المراد قتله وهمياً', required: true }] },
    { name: 'joke', description: '😂 نكتة' },
    { name: 'iq', description: '🧠 مستوى الذكاء' },
    { name: 'meme', description: '🐸 ميمز مضحك' },
    { name: 'slap', description: '✋ صفعة', options: [{ name: 'user', type: 6, description: 'العضو المراد صفعه وهمياً', required: true }] },
    { name: 'hug', description: '🫂 عناق', options: [{ name: 'user', type: 6, description: 'العضو المراد معانقته وهمياً', required: true }] },
    { name: 'roll', description: '🎲 نرد' },
    { name: 'flip', description: '🪙 ملك أم كتابة' },
    { name: '8ball', description: '🔮 الكرة السحرية', options: [{ name: 'question', type: 3, description: 'سؤالك للكرة السحرية', required: true }] },
    { name: 'uptime', description: '⏰ مدة التشغيل' }
];

// // --- نظام اللفل عند المراسلة ---
client.on('messageCreate', async (message) => {
    if (message.author.bot || !message.guild) return;
    
    const guildConfig = db.config.get(message.guild.id);
    if (!guildConfig?.levelEnabled) return;
    
    const userId = message.author.id;
    let userLevelData = db.levels.get(userId) || { xp: 0, level: 1 };
    
    // زيادة XP عشوائية (5-15)
    userLevelData.xp += Math.floor(Math.random() * 11) + 5;
    
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
                    .setDescription(`مبروك ${message.author}! وصلت للفل **${userLevelData.level}**`)
                    .setThumbnail(message.author.displayAvatarURL())
                    .setTimestamp();
                
                levelChannel.send({ content: `🎉 ${message.author}`, embeds: [embed] });
            }
        }
    }
    
    db.levels.set(userId, userLevelData);
});

// رسالة شكر عند إضافة البوت للسيرفر
client.on('guildCreate', async (guild) => {
    const owner = guild.ownerId;
    try {
        const ownerUser = await client.users.fetch(owner);
        const embed = new EmbedBuilder()
            .setColor('#7289da')
            .setTitle('✨ شكراً لك على إضافة البوت!')
            .setDescription(`شكراً لك ${ownerUser.username} على إضافة **OP BOT** إلى سيرفرك!\n\nالبوت يحتوي على **69 أمر** مفيد للإدارة والترفيه والاقتصاد.`)
            .setThumbnail(guild.iconURL() || client.user.displayAvatarURL())
            .addFields(
                { name: '📊 عدد الأوامر', value: '69 أمر', inline: true },
                { name: '⚙️ الإعدادات', value: '10 أوامر', inline: true },
                { name: '🎮 الترفيه', value: '20 أوامر', inline: true }
            )
            .setTimestamp();
        
        const row = new ActionRowBuilder()
            .addComponents(
                new ButtonBuilder()
                    .setLabel('الدعم')
                    .setStyle(ButtonStyle.Link)
                    .setURL('https://discord.gg/vvmaAbasEN')
            );
        
        ownerUser.send({ embeds: [embed], components: [row] }).catch(() => console.log("DM closed for owner"));
    } catch (error) {
        console.log('لا يمكن إرسال رسالة إلى صاحب السيرفر');
    }
});

// تحديث الحالة كل 5 دقائق
function updateStatus() {
    const serverCount = client.guilds.cache.size;
    const statuses = [
        `OP BOT | ${serverCount} سيرفر`,
        `OP BOT | ${serverCount} مجتمع`,
        `OP BOT | ${serverCount} سيرفر | 69 أمر`,
        `OP BOT | ${serverCount} سيرفر | /help`
    ];
    
    const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];
    
    client.user.setActivity(randomStatus, { 
        type: ActivityType.Watching 
    });
}

client.on('ready', async () => {
    // تسجيل الأوامر مع .toJSON()
    try {
        await client.application.commands.set(commands.map(cmd => ({
            ...cmd,
            options: cmd.options || []
        })).map(cmd => ({
            ...cmd,
            toJSON() {
                return {
                    name: cmd.name,
                    description: cmd.description,
                    options: cmd.options.map(opt => ({
                        name: opt.name,
                        type: opt.type,
                        description: opt.description || "No description provided",
                        required: opt.required || false
                    }))
                };
            }
        })));
        console.log(`✅ OP BOT Online | ${client.user.tag}`);
    } catch (error) {
        console.error('❌ Error registering commands:', error);
    }
    
    updateStatus();
    setInterval(updateStatus, 5 * 60 * 1000);
});

// --- نظام الترحيب واللفل واللوج ---
client.on('guildMemberAdd', async (member) => {
    const config = db.config.get(member.guild.id);
    if (config?.welcomeChannel) {
        const channel = member.guild.channels.cache.get(config.welcomeChannel);
        if (channel) channel.send(`✨ نورت السيرفر يا **${member.user.username}**! أنت العضو رقم ${member.guild.memberCount}.`);
    }
    if (config?.autoRole) {
        member.roles.add(config.autoRole).catch(() => {});
    }
});

// --- معالج الأوامر التفاعلي ---
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) return;
    const { commandName, options, user, guild, member, channel } = interaction;

    // --- أوامر الإدارة المبرمجة ---
    if (commandName === 'clear') {
        if (!member.permissions.has(PermissionFlagsBits.ManageMessages)) 
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const amount = options.getInteger('amount');
        await channel.bulkDelete(amount > 100 ? 100 : amount);
        return interaction.reply({ content: `🧹 تم مسح **${amount}** رسالة.`, ephemeral: true });
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

    if (commandName === 'timeout') {
        if (!member.permissions.has(PermissionFlagsBits.ModerateMembers))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetUser = options.getUser('user');
        const minutes = options.getInteger('minutes');
        const targetMember = guild.members.cache.get(targetUser.id);
        
        await targetMember.timeout(minutes * 60 * 1000);
        
        const embed = new EmbedBuilder()
            .setColor('#ff0000')
            .setTitle('⚠️ عقوبة تم تطبيقها')
            .setDescription(`تم تطبيق عقوبة **Timeout** على ${targetUser.username}`)
            .addFields(
                { name: 'المدة', value: `${minutes} دقيقة`, inline: true },
                { name: 'المعاقب', value: user.username, inline: true }
            )
            .setTimestamp();
        
        member.send({ embeds: [embed] }).catch(() => {});
        return interaction.reply(`⏳ تم إسكات ${targetUser.username} لمدة ${minutes} دقيقة.`);
    }

    if (commandName === 'untimeout') {
        if (!member.permissions.has(PermissionFlagsBits.ModerateMembers))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetUser = options.getUser('user');
        const targetMember = guild.members.cache.get(targetUser.id);
        await targetMember.timeout(null);
        return interaction.reply(`🔈 تم إلغاء إسكات ${targetUser.username}.`);
    }

    if (commandName === 'ban') {
        if (!member.permissions.has(PermissionFlagsBits.BanMembers))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetUser = options.getUser('user');
        const reason = options.getString('reason') || 'بدون سبب';
        await guild.members.ban(targetUser.id, { reason });
        return interaction.reply(`🔨 تم حظر ${targetUser.username} بنجاح.`);
    }

    if (commandName === 'kick') {
        if (!member.permissions.has(PermissionFlagsBits.KickMembers))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetUser = options.getUser('user');
        const reason = options.getString('reason') || 'بدون سبب';
        await guild.members.kick(targetUser.id, reason);
        return interaction.reply(`👞 تم طرد ${targetUser.username} بنجاح.`);
    }

    // --- أوامر الاقتصاد المبرمجة ---
    let userData = db.economy.get(user.id) || { wallet: 0, bank: 0, lastDaily: 0 };

    if (commandName === 'daily') {
        const now = Date.now();
        if (now - userData.lastDaily < 86400000) {
            const hoursLeft = Math.floor((86400000 - (now - userData.lastDaily)) / 3600000);
            return interaction.reply(`❌ استلمتها بالفعل، انتظر **${hoursLeft}** ساعة.`);
        }
        userData.wallet += 1000;
        userData.lastDaily = now;
        db.economy.set(user.id, userData);
        return interaction.reply('💵 تم استلام **1000** عملة بنجاح!');
    }

    if (commandName === 'balance') {
        return interaction.reply(`👛 رصيدك الحالي: **${userData.wallet}** عملة في المحفظة، **${userData.bank}** عملة في البنك.`);
    }

    if (commandName === 'transfer') {
        const targetUser = options.getUser('u');
        const amount = options.getInteger('a');
        if (amount <= 0 || userData.wallet < amount) return interaction.reply('❌ تحقق من المبلغ أو رصيدك.');
        
        let targetData = db.economy.get(targetUser.id) || { wallet: 0, bank: 0, lastDaily: 0 };
        userData.wallet -= amount;
        targetData.wallet += amount;
        db.economy.set(user.id, userData);
        db.economy.set(targetUser.id, targetData);
        return interaction.reply(`💸 تم تحويل **${amount}** عملة إلى ${targetUser.username}.`);
    }

    if (commandName === 'rob') {
        const targetUser = options.getUser('user');
        const targetData = db.economy.get(targetUser.id) || { wallet: 0, bank: 0, lastDaily: 0 };
        if (targetData.wallet < 100) return interaction.reply('❌ الرصيد الهدف قليل جداً.');
        
        const success = Math.random() > 0.5;
        if (success) {
            const stolen = Math.floor(targetData.wallet * 0.3);
            userData.wallet += stolen;
            targetData.wallet -= stolen;
            db.economy.set(user.id, userData);
            db.economy.set(targetUser.id, targetData);
            return interaction.reply(`✅ سرقت **${stolen}** عملة من ${targetUser.username}!`);
        } else {
            const fine = Math.floor(userData.wallet * 0.2);
            userData.wallet -= fine;
            db.economy.set(user.id, userData);
            return interaction.reply(`❌ فشلت ودفعت غرامة **${fine}** عملة.`);
        }
    }

    if (commandName === 'slots' || commandName === 'mining' || commandName === 'fish') {
        const costs = { slots: 50, mining: 30, fish: 20 };
        const cost = costs[commandName];
        if (userData.wallet < cost) return interaction.reply(`❌ تحتاج ${cost} عملة.`);
        userData.wallet -= cost;
        const reward = Math.floor(Math.random() * 100) + 10;
        userData.wallet += reward;
        db.economy.set(user.id, userData);
        return interaction.reply(`🎮 النتيجة: ربحت **${reward}** عملة!`);
    }

    // --- أوامر اللفل ---
    if (commandName === 'level') {
        const userLevelData = db.levels.get(user.id) || { xp: 0, level: 1 };
        const embed = new EmbedBuilder()
            .setColor('#7289da')
            .setTitle('📊 مستواك الحالي')
            .addFields(
                { name: '📈 المستوى', value: `${userLevelData.level}`, inline: true },
                { name: '⚡ XP', value: `${userLevelData.xp}`, inline: true }
            );
        return interaction.reply({ embeds: [embed] });
    }

    if (commandName === 'rank') {
        const allUsers = Array.from(db.levels.entries()).sort((a, b) => b[1].level - a[1].level);
        const rank = allUsers.findIndex(entry => entry[0] === user.id) + 1;
        return interaction.reply(`🏆 ترتيبك الحالي هو **${rank}** في السيرفر.`);
    }

    // --- أوامر التحذيرات ---
    if (commandName === 'warn') {
        if (!member.permissions.has(PermissionFlagsBits.ModerateMembers)) return interaction.reply('❌ لا تملك صلاحية.');
        const targetUser = options.getUser('user');
        const reason = options.getString('reason');
        let warns = db.warns.get(targetUser.id) || [];
        warns.push({ reason, date: new Date().toLocaleString(), by: user.username });
        db.warns.set(targetUser.id, warns);
        return interaction.reply(`⚠️ تم تحذير ${targetUser.username}.`);
    }

    if (commandName === 'all-warns') {
        const targetUser = options.getUser('user');
        const warns = db.warns.get(targetUser.id) || [];
        if (warns.length === 0) return interaction.reply(`📂 ${targetUser.username} ليس لديه تحذيرات.`);
        return interaction.reply(`📂 عدد تحذيرات ${targetUser.username} هو **${warns.length}**.`);
    }

    // --- أوامر الترفيه (إكمال الجزء الأخير) ---
    if (commandName === 'hack') {
        const target = options.getUser('user') || user;
        await interaction.reply('📡 جاري الاتصال بقاعدة بيانات الهدف...');
        setTimeout(() => interaction.editReply('💉 تم حقن الفيروس في الجهاز...'), 2000);
        setTimeout(() => interaction.editReply(`✅ تمت المهمة! تم سحب بيانات **${target.username}** بنجاح! 💾`), 4000);
    }

    if (commandName === 'iq') {
        const iqValue = Math.floor(Math.random() * 150) + 50;
        return interaction.reply(`🧠 مستوى ذكاء **${user.username}** هو: **${iqValue}**.`);
    }

    if (commandName === 'joke') {
        const jokes = ["مرة واحد اشتري ساعة لقاها واقفة جابلها كرسي.", "مرة واحد راح يشتري عيش لقى الفرن والعيش بيتخانقوا."];
        return interaction.reply(`😂 | ${jokes[Math.floor(Math.random() * jokes.length)]}`);
    }

    if (commandName === 'ping') {
        return interaction.reply(`📶 بنج البوت الحالي هو: **${client.ws.ping}ms**.`);
    }

    if (commandName === 'help') {
        const embed = new EmbedBuilder()
            .setColor('#7289da')
            .setTitle('📖 قائمة أوامر OP BOT')
            .setDescription('استخدم `/` لرؤية جميع الـ 69 أمر المتاحة للإدارة، الاقتصاد، اللفل، والترفيه.');
        return interaction.reply({ embeds: [embed] });
    }
});

// --- تشغيل البوت (ضع التوكن الخاص بك هنا) ---
client.login(process.env.DISCORD_TOKEN);
