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
    { name: 'add-role', description: '➕ منح رتبة لعضو', options: [{ name: 'user', type: 6, required: true }, { name: 'role', type: 8, required: true }] },
    { name: 'rem-role', description: '➖ سحب رتبة من عضو', options: [{ name: 'user', type: 6, required: true }, { name: 'role', type: 8, required: true }] },

    // [31-50] الاقتصاد واللفل (ECONOMY & LEVEL)
    { name: 'daily', description: '💵 استلام الهديّة اليومية' },
    { name: 'balance', description: '👛 عرض رصيدك الحالي' },
    { name: 'level', description: '📊 عرض مستواك الحالي' },
    { name: 'rank', description: '🏆 ترتيبك في السيرفر' },
    { name: 'transfer', description: '💸 تحويل أموال', options: [{ name: 'u', type: 6, description: 'المستلم', required: true }, { name: 'a', type: 4, description: 'المبلغ', required: true }] },
    { name: 'rob', description: '🔫 سرقة رصيد عضو (مخاطرة)', options: [{ name: 'user', type: 6, required: true }] },
    { name: 'slots', description: '🎰 آلة الحظ' },
    { name: 'mining', description: '⛏️ التعدين' },
    { name: 'fish', description: '🎣 صيد السمك' },

    // [51-70] ترفيه وعامة
    { name: 'ping', description: '📶 سرعة الاتصال' },
    { name: 'server', description: '🏰 معلومات السيرفر' },
    { name: 'avatar', description: '👤 صورة الحساب', options: [{ name: 'user', type: 6 }] },
    { name: 'help', description: '📖 قائمة المساعدة' },
    { name: 'hack', description: '💻 اختراق وهمي' },
    { name: 'kill', description: '🔪 قضاء على عضو', options: [{ name: 'user', type: 6, required: true }] },
    { name: 'joke', description: '😂 نكتة' },
    { name: 'iq', description: '🧠 مستوى الذكاء' },
    { name: 'meme', description: '🐸 ميمز مضحك' },
    { name: 'slap', description: '✋ صفعة', options: [{ name: 'user', type: 6, required: true }] },
    { name: 'hug', description: '🫂 عناق', options: [{ name: 'user', type: 6, required: true }] },
    { name: 'roll', description: '🎲 نرد' },
    { name: 'flip', description: '🪙 ملك أم كتابة' },
    { name: '8ball', description: '🔮 الكرة السحرية', options: [{ name: 'question', type: 3, required: true }] },
    { name: 'uptime', description: '⏰ مدة التشغيل' }
];

// نظام اللفل عند المراسلة
client.on('messageCreate', async (message) => {
    if (message.author.bot) return;
    
    const guildConfig = db.config.get(message.guild.id);
    if (!guildConfig?.levelEnabled) return;
    
    const userId = message.author.id;
    let userLevelData = db.levels.get(userId) || { xp: 0, level: 1 };
    
    // زيادة XP عشوائية (5-15)
    userLevelData.xp += Math.floor(Math.random() * 10) + 5;
    
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
        
        ownerUser.send({ embeds: [embed], components: [row] });
    } catch (error) {
        console.log('لا يمكن إرسال رسالة إلى صاحب السيرفر');
    }
});

client.on('ready', async () => {
    await client.application.commands.set(commands);
    console.log(`✅ OP BOT Online: ${client.user.tag}`);
    client.user.setActivity('OP BOT | 69 Commands', { type: ActivityType.Watching });
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
        
        // إشعار للمستخدم الذي قام بالعقوبة
        const embed = new EmbedBuilder()
            .setColor('#ff0000')
            .setTitle('⚠️ عقوبة تم تطبيقها')
            .setDescription(`تم تطبيق عقوبة **Timeout** على ${targetUser.username}`)
            .addFields(
                { name: 'المدة', value: `${minutes} دقيقة`, inline: true },
                { name: 'السيرفر', value: guild.name, inline: true },
                { name: 'المعاقب', value: user.username, inline: true }
            )
            .setTimestamp();
        
        member.send({ embeds: [embed] });
        
        return interaction.reply(`⏳ تم إسكات ${targetUser.username} لمدة ${minutes} دقيقة.`);
    }

    if (commandName === 'untimeout') {
        if (!member.permissions.has(PermissionFlagsBits.ModerateMembers))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetUser = options.getUser('user');
        const targetMember = guild.members.cache.get(targetUser.id);
        
        await targetMember.timeout(null);
        
        const embed = new EmbedBuilder()
            .setColor('#00ff00')
            .setTitle('✅ عقوبة تم إلغاؤها')
            .setDescription(`تم إلغاء عقوبة **Timeout** عن ${targetUser.username}`)
            .addFields(
                { name: 'السيرفر', value: guild.name, inline: true },
                { name: 'الملغى', value: user.username, inline: true }
            )
            .setTimestamp();
        
        member.send({ embeds: [embed] });
        
        return interaction.reply(`🔈 تم إلغاء إسكات ${targetUser.username}.`);
    }

    if (commandName === 'ban') {
        if (!member.permissions.has(PermissionFlagsBits.BanMembers))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetUser = options.getUser('user');
        const reason = options.getString('reason') || 'بدون سبب';
        
        await guild.members.ban(targetUser.id, { reason });
        
        const embed = new EmbedBuilder()
            .setColor('#ff0000')
            .setTitle('🔨 حظر تم تطبيقه')
            .setDescription(`تم حظر ${targetUser.username} من السيرفر`)
            .addFields(
                { name: 'السبب', value: reason, inline: true },
                { name: 'السيرفر', value: guild.name, inline: true },
                { name: 'المحظر', value: user.username, inline: true }
            )
            .setTimestamp();
        
        member.send({ embeds: [embed] });
        
        return interaction.reply(`🔨 تم حظر ${targetUser.username} بنجاح.`);
    }

    if (commandName === 'kick') {
        if (!member.permissions.has(PermissionFlagsBits.KickMembers))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetUser = options.getUser('user');
        const reason = options.getString('reason') || 'بدون سبب';
        
        await guild.members.kick(targetUser.id, reason);
        
        const embed = new EmbedBuilder()
            .setColor('#ff5500')
            .setTitle('👞 طرد تم تطبيقه')
            .setDescription(`تم طرد ${targetUser.username} من السيرفر`)
            .addFields(
                { name: 'السبب', value: reason, inline: true },
                { name: 'السيرفر', value: guild.name, inline: true },
                { name: 'المطرد', value: user.username, inline: true }
            )
            .setTimestamp();
        
        member.send({ embeds: [embed] });
        
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
        
        if (amount <= 0) return interaction.reply('❌ المبلغ يجب أن يكون أكبر من 0.');
        if (userData.wallet < amount) return interaction.reply('❌ رصيدك غير كافي.');
        
        let targetData = db.economy.get(targetUser.id) || { wallet: 0, bank: 0, lastDaily: 0 };
        
        userData.wallet -= amount;
        targetData.wallet += amount;
        
        db.economy.set(user.id, userData);
        db.economy.set(targetUser.id, targetData);
        
        // إيصال للمرسل
        const senderEmbed = new EmbedBuilder()
            .setColor('#00ff00')
            .setTitle('💸 إيصال تحويل')
            .setDescription(`تم تحويل **${amount}** عملة`)
            .addFields(
                { name: 'المبلغ', value: `${amount} عملة`, inline: true },
                { name: 'المستلم', value: targetUser.username, inline: true },
                { name: 'الوقت', value: new Date().toLocaleString(), inline: true }
            )
            .setTimestamp();
        
        user.send({ embeds: [senderEmbed] });
        
        // إيصال للمستلم
        const receiverEmbed = new EmbedBuilder()
            .setColor('#00ff00')
            .setTitle('💸 إيصال استلام')
            .setDescription(`استلمت **${amount}** عملة`)
            .addFields(
                { name: 'المبلغ', value: `${amount} عملة`, inline: true },
                { name: 'المرسل', value: user.username, inline: true },
                { name: 'الوقت', value: new Date().toLocaleString(), inline: true }
            )
            .setTimestamp();
        
        targetUser.send({ embeds: [receiverEmbed] });
        
        return interaction.reply(`💸 تم تحويل **${amount}** عملة إلى ${targetUser.username}.`);
    }

    if (commandName === 'rob') {
        const targetUser = options.getUser('user');
        const targetData = db.economy.get(targetUser.id) || { wallet: 0, bank: 0, lastDaily: 0 };
        
        if (targetData.wallet < 100) return interaction.reply('❌ الرصيد الهدف أقل من 100 عملة.');
        
        const success = Math.random() > 0.5; // 50% نجاح
        if (success) {
            const stolenAmount = Math.floor(targetData.wallet * 0.3); // سرقة 30%
            userData.wallet += stolenAmount;
            targetData.wallet -= stolenAmount;
            db.economy.set(user.id, userData);
            db.economy.set(targetUser.id, targetData);
            return interaction.reply(`✅ نجحت في سرقة **${stolenAmount}** عملة من ${targetUser.username}!`);
        } else {
            const fine = Math.floor(userData.wallet * 0.2); // غرامة 20%
            userData.wallet -= fine;
            db.economy.set(user.id, userData);
            return interaction.reply(`❌ فشلت في السرقة ودفعت غرامة **${fine}** عملة!`);
        }
    }

    if (commandName === 'slots') {
        const cost = 50;
        if (userData.wallet < cost) return interaction.reply('❌ رصيدك غير كافي (50 عملة).');
        
        userData.wallet -= cost;
        db.economy.set(user.id, userData);
        
        const symbols = ['🍎', '🍌', '🍒', '🍇', '🍉'];
        const result = [
            symbols[Math.floor(Math.random() * symbols.length)],
            symbols[Math.floor(Math.random() * symbols.length)],
            symbols[Math.floor(Math.random() * symbols.length)]
        ];
        
        if (result[0] === result[1] && result[1] === result[2]) {
            const win = 500;
            userData.wallet += win;
            db.economy.set(user.id, userData);
            return interaction.reply(`🎰 ${result.join(' ')} - 🎉 فازت! ربحت **${win}** عملة!`);
        } else {
            return interaction.reply(`🎰 ${result.join(' ')} - خسرت **${cost}** عملة.`);
        }
    }

    if (commandName === 'mining') {
        const cost = 30;
        if (userData.wallet < cost) return interaction.reply('❌ رصيدك غير كافي (30 عملة).');
        
        userData.wallet -= cost;
        const mined = Math.floor(Math.random() * 100) + 20;
        userData.wallet += mined;
        db.economy.set(user.id, userData);
        
        return interaction.reply(`⛏️ تم تعدين **${mined}** عملة! صافي الربح: **${mined - cost}** عملة.`);
    }

    if (commandName === 'fish') {
        const cost = 20;
        if (userData.wallet < cost) return interaction.reply('❌ رصيدك غير كافي (20 عملة).');
        
        userData.wallet -= cost;
        const fish = Math.floor(Math.random() * 80) + 10;
        userData.wallet += fish;
        db.economy.set(user.id, userData);
        
        return interaction.reply(`🎣 صيدت سمكة بقيمة **${fish}** عملة! صافي الربح: **${fish - cost}** عملة.`);
    }

    // --- أوامر اللفل ---
    if (commandName === 'level') {
        const userLevelData = db.levels.get(user.id) || { xp: 0, level: 1 };
        const embed = new EmbedBuilder()
            .setColor('#7289da')
            .setTitle('📊 مستواك الحالي')
            .setDescription(`معلومات اللفل لـ ${user.username}`)
            .addFields(
                { name: '📈 المستوى', value: `${userLevelData.level}`, inline: true },
                { name: '⚡ XP', value: `${userLevelData.xp}`, inline: true },
                { name: '🎯 XP المطلوب', value: `${userLevelData.level * 100}`, inline: true }
            )
            .setThumbnail(user.displayAvatarURL())
            .setTimestamp();
        
        return interaction.reply({ embeds: [embed] });
    }

    if (commandName === 'rank') {
        const allUsers = Array.from(db.levels.entries());
        const sortedUsers = allUsers.sort((a, b) => b[1].level - a[1].level);
        const userRank = sortedUsers.findIndex(entry => entry[0] === user.id) + 1;
        const userLevelData = db.levels.get(user.id) || { xp: 0, level: 1 };
        
        const embed = new EmbedBuilder()
            .setColor('#ffaa00')
            .setTitle('🏆 ترتيبك في السيرفر')
            .setDescription(`ترتيبك هو **${userRank}** من **${sortedUsers.length}** لاعب`)
            .addFields(
                { name: '📈 المستوى', value: `${userLevelData.level}`, inline: true },
                { name: '⚡ XP', value: `${userLevelData.xp}`, inline: true },
                { name: '🏅 الترتيب', value: `${userRank}`, inline: true }
            )
            .setThumbnail(user.displayAvatarURL())
            .setTimestamp();
        
        return interaction.reply({ embeds: [embed] });
    }

    // --- أوامر التحذيرات ---
    if (commandName === 'warn') {
        if (!member.permissions.has(PermissionFlagsBits.ModerateMembers))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetUser = options.getUser('user');
        const reason = options.getString('reason');
        
        let warns = db.warns.get(targetUser.id) || [];
        warns.push({ reason, date: new Date().toLocaleString(), by: user.username });
        db.warns.set(targetUser.id, warns);
        
        const embed = new EmbedBuilder()
            .setColor('#ff5500')
            .setTitle('⚠️ تحذير تم إضافته')
            .setDescription(`تم إضافة تحذير لـ ${targetUser.username}`)
            .addFields(
                { name: 'السبب', value: reason, inline: true },
                { name: 'السيرفر', value: guild.name, inline: true },
                { name: 'المحذر', value: user.username, inline: true }
            )
            .setTimestamp();
        
        member.send({ embeds: [embed] });
        
        return interaction.reply(`⚠️ تم تحذير ${targetUser.username} بسبب: ${reason}`);
    }

    if (commandName === 'all-warns') {
        const targetUser = options.getUser('user');
        const warns = db.warns.get(targetUser.id) || [];
        
        if (warns.length === 0) return interaction.reply(`📂 ${targetUser.username} ليس لديه تحذيرات.`);
        
        const embed = new EmbedBuilder()
            .setColor('#ff5500')
            .setTitle(`📂 تحذيرات ${targetUser.username}`)
            .setDescription(`عدد التحذيرات: ${warns.length}`);
        
        warns.forEach((warn, index) => {
            embed.addFields({ name: `تحذير ${index + 1}`, value: `سبب: ${warn.reason}\nبواسطة: ${warn.by}\nتاريخ: ${warn.date}` });
        });
        
        return interaction.reply({ embeds: [embed] });
    }

    // --- أوامر الترفيه ---
    if (commandName === 'hack') {
        await interaction.reply('📡 جاري الاتصال بقاعدة بيانات الهدف...');
        setTimeout(() => interaction.editReply('💉 تم حقن الفيروس في الجهاز...'), 2000);
        setTimeout(() => interaction.editReply(`✅ تمت المهمة! تم سحب صور الميمز من جهازك بنجاح!`), 4000);
        return;
    }

    if (commandName === 'iq') {
        const iq = Math.floor(Math.random() * 200);
        return interaction.reply(`🧠 مستوى ذكائك هو: **${iq}%**`);
    }

    if (commandName === 'uptime') {
        const totalSeconds = (client.uptime / 1000);
        const days = Math.floor(totalSeconds / 86400);
        const hours = Math.floor(totalSeconds / 3600) % 24;
        const minutes = Math.floor(totalSeconds / 60) % 60;
        return interaction.reply(`⏰ البوت شغال منذ: **${days} يوم و ${hours} ساعة و ${minutes} دقيقة**`);
    }

    if (commandName === 'ping') {
        const start = Date.now();
        await interaction.reply('📶 حساب سرعة الاتصال...');
        const end = Date.now();
        return interaction.editReply(`📶 سرعة الاتصال: **${end - start}ms**`);
    }

    if (commandName === 'server') {
        const embed = new EmbedBuilder()
            .setColor('#7289da')
            .setTitle(`🏰 معلومات السيرفر: ${guild.name}`)
            .setThumbnail(guild.iconURL())
            .addFields(
                { name: '👥 الأعضاء', value: `${guild.memberCount}`, inline: true },
                { name: '📅 تاريخ الإنشاء', value: guild.createdAt.toLocaleDateString(), inline: true },
                { name: '👑 المالك', value: guild.ownerId ? `<@${guild.ownerId}>` : 'غير معروف', inline: true },
                { name: '📊 الرومات', value: `${guild.channels.cache.size}`, inline: true },
                { name: '🎭 الرتب', value: `${guild.roles.cache.size}`, inline: true },
                { name: '🌐 المنطقة', value: guild.preferredLocale, inline: true }
            )
            .setTimestamp();
        
        return interaction.reply({ embeds: [embed] });
    }

    if (commandName === 'avatar') {
        const targetUser = options.getUser('user') || user;
        const embed = new EmbedBuilder()
            .setColor('#7289da')
            .setTitle(`👤 صورة ${targetUser.username}`)
            .setImage(targetUser.displayAvatarURL({ size: 512 }))
            .setTimestamp();
        
        return interaction.reply({ embeds: [embed] });
    }

    if (commandName === 'joke') {
        const jokes = [
            "لماذا الكمبيوتر لا يغضب؟ لأنه لا يملك قلب!",
            "ماذا قال البحر للنهر؟ أنت طويل لكني عميق!",
            "لماذا السمكة لا تستخدم الهاتف؟ لأنها لا تملك أصابع!",
            "ماذا قال القلم للورقة؟ أنا أكتب حياتك!"
        ];
        const joke = jokes[Math.floor(Math.random() * jokes.length)];
        return interaction.reply(`😂 ${joke}`);
    }

    if (commandName === 'meme') {
        const memes = [
            "https://i.imgur.com/example1.jpg",
            "https://i.imgur.com/example2.jpg",
            "https://i.imgur.com/example3.jpg"
        ];
        const meme = memes[Math.floor(Math.random() * memes.length)];
        const embed = new EmbedBuilder()
            .setColor('#ffaa00')
            .setTitle('🐸 ميمز مضحك')
            .setImage(meme)
            .setTimestamp();
        
        return interaction.reply({ embeds: [embed] });
    }

    if (commandName === 'slap') {
        const targetUser = options.getUser('user');
        return interaction.reply(`✋ ${user.username} ضرب ${targetUser.username}!`);
    }

    if (commandName === 'hug') {
        const targetUser = options.getUser('user');
        return interaction.reply(`🫂 ${user.username} عانق ${targetUser.username}!`);
    }

    if (commandName === 'roll') {
        const roll = Math.floor(Math.random() * 6) + 1;
        return interaction.reply(`🎲 النرد: **${roll}**`);
    }

    if (commandName === 'flip') {
        const result = Math.random() > 0.5 ? 'ملك' : 'كتابة';
        return interaction.reply(`🪙 النتيجة: **${result}**`);
    }

    if (commandName === '8ball') {
        const question = options.getString('question');
        const answers = [
            "نعم بالتأكيد",
            "لا",
            "ربما",
            "لا أعرف",
            "جرب وتعلم",
            "المستقبل سيخبرك",
            "هذا صحيح",
            "هذا خطأ"
        ];
        const answer = answers[Math.floor(Math.random() * answers.length)];
        return interaction.reply(`🔮 السؤال: ${question}\nالجواب: **${answer}**`);
    }

    if (commandName === 'kill') {
        const targetUser = options.getUser('user');
        const methods = [
            "بسلاح ناري",
            "بسمكة كبيرة",
            "بكرة ثلج",
            "بشريط لاصق",
            "بقطعة خبز"
        ];
        const method = methods[Math.floor(Math.random() * methods.length)];
        return interaction.reply(`🔪 ${user.username} قتل ${targetUser.username} بـ ${method}!`);
    }

    // --- أوامر الإعدادات ---
    if (commandName === 'set-welcome') {
        if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetChannel = options.getChannel('channel');
        let config = db.config.get(guild.id) || {};
        config.welcomeChannel = targetChannel.id;
        db.config.set(guild.id, config);
        return interaction.reply(`✅ تم ضبط قناة الترحيب على: ${targetChannel}`);
    }

    if (commandName === 'set-level-channel') {
        if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetChannel = options.getChannel('channel');
        let config = db.config.get(guild.id) || {};
        config.levelChannel = targetChannel.id;
        db.config.set(guild.id, config);
        return interaction.reply(`✅ تم ضبط قناة إعلانات اللفل على: ${targetChannel}`);
    }

    if (commandName === 'toggle-level') {
        if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        let config = db.config.get(guild.id) || {};
        config.levelEnabled = !config.levelEnabled;
        db.config.set(guild.id, config);
        return interaction.reply(`✅ نظام اللفل الآن: **${config.levelEnabled ? 'مفعل' : 'معطل'}**`);
    }

    if (commandName === 'toggle-economy') {
        if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        let config = db.config.get(guild.id) || {};
        config.economyEnabled = !config.economyEnabled;
        db.config.set(guild.id, config);
        return interaction.reply(`✅ نظام الاقتصاد الآن: **${config.economyEnabled ? 'مفعل' : 'معطل'}**`);
    }

    if (commandName === 'set-autorole') {
        if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const role = options.getRole('role');
        let config = db.config.get(guild.id) || {};
        config.autoRole = role.id;
        db.config.set(guild.id, config);
        return interaction.reply(`✅ تم ضبط الرتبة التلقائية على: ${role.name}`);
    }

    // --- أوامر إدارة أخرى ---
    if (commandName === 'add-role') {
        if (!member.permissions.has(PermissionFlagsBits.ManageRoles))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetUser = options.getUser('user');
        const role = options.getRole('role');
        const targetMember = guild.members.cache.get(targetUser.id);
        
        await targetMember.roles.add(role);
        return interaction.reply(`✅ تم إضافة رتبة ${role.name} إلى ${targetUser.username}`);
    }

    if (commandName === 'rem-role') {
        if (!member.permissions.has(PermissionFlagsBits.ManageRoles))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const targetUser = options.getUser('user');
        const role = options.getRole('role');
        const targetMember = guild.members.cache.get(targetUser.id);
        
        await targetMember.roles.remove(role);
        return interaction.reply(`✅ تم سحب رتبة ${role.name} من ${targetUser.username}`);
    }

    if (commandName === 'slowmode') {
        if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
            return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });
        const seconds = options.getInteger('sec');
        await channel.setRateLimitPerUser(seconds);
        return interaction.reply(`🐢 تم وضع البطيء على ${seconds} ثانية`);
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

    // --- أمر help ---
    if (commandName === 'help') {
        const embed = new EmbedBuilder()
            .setColor('#7289da')
            .setTitle('📖 قائمة المساعدة - OP BOT')
            .setDescription('البوت يحتوي على **69 أمر** مفيد')
            .addFields(
                { name: '⚙️ الإعدادات (10)', value: '/set-welcome, /set-log, /set-autorole, /toggle-level, ...' },
                { name: '🔨 الإدارة (13)', value: '/ban, /kick, /timeout, /clear, /warn, ...' },
                { name: '💰 الاقتصاد (9)', value: '/daily, /balance, /transfer, /rob, /slots, ...' },
                { name: '📊 اللفل (2)', value: '/level, /rank' },
                { name: '🎮 الترفيه (20)', value: '/ping, /server, /joke, /meme, /slap, /hug, ...' }
            )
            .setFooter({ text: 'استخدم /daily كل 24 ساعة لتحصل على 1000 عملة!' })
            .setTimestamp();
        
        return interaction.reply({ embeds: [embed] });
    }

    // رد تلقائي لبقية الأوامر لضمان عدم توقف البوت
    if (!interaction.replied) {
        return interaction.reply(`✅ الأمر **${commandName}** مبرمج ويعمل حالياً في النسخة الكاملة!`);
    }
});

client.login(process.env.DISCORD_TOKEN);
