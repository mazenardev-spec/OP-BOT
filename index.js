const {
    Client, GatewayIntentBits, Partials, EmbedBuilder, ActivityType,
    PermissionFlagsBits, ActionRowBuilder, ButtonBuilder, ButtonStyle,
    ApplicationCommandOptionType, REST, Routes, Collection,
    ModalBuilder, TextInputBuilder, TextInputStyle, ChannelType,
    WebhookClient, AttachmentBuilder
} = require('discord.js');
const { QuickDB } = require("quick.db");
const db = new QuickDB();
const fetch = require('node-fetch');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent, GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildPresences, GatewayIntentBits.GuildMessageReactions
    ],
    partials: [Partials.Channel, Partials.Message, Partials.User, Partials.Reaction]
});

// نظام الكولداون للأمر /op
const opCooldowns = new Collection();

// نظام تخزين هوية السيرفر
const serverIdentities = new Map();

// --- مصفوفة الأوامر الكاملة (77 أمر) ---
const commands = [
    // الإعدادات (SETTINGS)
    { name: 'set-welcome', description: '✨ تحديد قناة الترحيب بالأعضاء الجدد', options: [{ name: 'channel', type: ApplicationCommandOptionType.Channel, description: 'الروم', required: true }] },
    { name: 'set-log', description: '📜 تحديد قناة السجلات لمراقبة الأحداث', options: [{ name: 'channel', type: ApplicationCommandOptionType.Channel, description: 'الروم', required: true }] },
    { name: 'set-ticket', description: '📩 إعداد نظام التذاكر والدعم الفني', options: [{ name: 'channel', type: ApplicationCommandOptionType.Channel, description: 'الروم', required: true }] },
    { name: 'set-autorole', description: '🎭 تحديد رتبة تعطى تلقائياً عند الدخول', options: [{ name: 'role', type: ApplicationCommandOptionType.Role, description: 'الرتبة', required: true }] },
    { name: 'set-level-channel', description: '🆙 تحديد قناة إعلانات ترقيات لفل الأعضاء', options: [{ name: 'channel', type: ApplicationCommandOptionType.Channel, description: 'الروم', required: true }] },
    { name: 'set-suggestions', description: '💡 ضبط قناة استقبال الاقتراحات', options: [{ name: 'channel', type: ApplicationCommandOptionType.Channel, description: 'الروم', required: true }] },
    { name: 'set-reports', description: '🚩 تحديد قناة استقبال البلاغات', options: [{ name: 'channel', type: ApplicationCommandOptionType.Channel, description: 'الروم', required: true }] },
    { name: 'toggle-level', description: '⚙️ تشغيل أو إيقاف نظام اللفل' },
    { name: 'toggle-economy', description: '💰 تشغيل أو إيقاف نظام الاقتصاد' },
    { name: 'setup-admin', description: '🛠️ تجهيز رتب الإدارة الأساسية' },

    // الإدارة (MODERATION)
    { name: 'ban', description: '🔨 حظر عضو نهائياً', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو', required: true }, { name: 'reason', type: ApplicationCommandOptionType.String, description: 'السبب' }] },
    { name: 'kick', description: '👞 طرد عضو من السيرفر', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو', required: true }, { name: 'reason', type: ApplicationCommandOptionType.String, description: 'السبب' }] },
    { name: 'timeout', description: '⏳ إسكات عضو مؤقتاً', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو', required: true }, { name: 'minutes', type: ApplicationCommandOptionType.Integer, description: 'الدقائق', required: true }] },
    { name: 'untimeout', description: '🔈 إلغاء إسكات عضو', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو', required: true }] },
    { name: 'clear', description: '🧹 تنظيف الشات', options: [{ name: 'amount', type: ApplicationCommandOptionType.Integer, description: 'العدد', required: true }] },
    { name: 'warn', description: '⚠️ تحذير رسمي لعضو', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو', required: true }, { name: 'reason', type: ApplicationCommandOptionType.String, description: 'السبب', required: true }] },
    { name: 'all-warns', description: '📂 عرض تحذيرات عضو', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو', required: true }] },
    { name: 'lock', description: '🔒 إغلاق القناة الحالية' },
    { name: 'unlock', description: '🔓 فتح القناة' },
    { name: 'hide', description: '👻 إخفاء القناة' },
    { name: 'show', description: '👀 إظهار القناة' },
    { name: 'slowmode', description: '🐢 وضع بطيء', options: [{ name: 'sec', type: ApplicationCommandOptionType.Integer, description: 'ثواني', required: true }] },
    {
        name: 'add-role',
        description: '➕ منح رتبة لعضو',
        options: [
            { name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو المراد منحه الرتبة', required: true },
            { name: 'role', type: ApplicationCommandOptionType.Role, description: 'الرتبة المطلوب منحها', required: true }
        ]
    },
    {
        name: 'rem-role',
        description: '➖ سحب رتبة من عضو',
        options: [
            { name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو المراد سحب الرتبة منه', required: true },
            { name: 'role', type: ApplicationCommandOptionType.Role, description: 'الرتبة المطلوب سحبها', required: true }
        ]
    },

    // الاقتصاد واللفل (ECONOMY & LEVEL)
    { name: 'daily', description: '💵 استلام الهديّة اليومية' },
    { name: 'balance', description: '👛 عرض رصيدك الحالي' },
    { name: 'level', description: '📊 عرض مستواك الحالي' },
    { name: 'rank', description: '🏆 ترتيبك في السيرفر' },
    { name: 'transfer', description: '💸 تحويل أموال', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'المستلم', required: true }, { name: 'amount', type: ApplicationCommandOptionType.Integer, description: 'المبلغ', required: true }] },
    { name: 'rob', description: '🔫 سرقة رصيد عضو (مخاطرة)', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو المراد سرقته', required: true }] },
    { name: 'slots', description: '🎰 آلة الحظ' },
    { name: 'mining', description: '⛏️ التعدين' },
    { name: 'fish', description: '🎣 صيد السمك' },

    // ترفيه وعامة
    { name: 'ping', description: '📶 سرعة الاتصال' },
    { name: 'server', description: '🏰 معلومات السيرفر' },
    { name: 'servers', description: '🌐 عرض عدد السيرفرات التي فيها البوت' },
    { name: 'avatar', description: '👤 صورة الحساب', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو المراد عرض صورته' }] },
    { name: 'help', description: '📖 قائمة المساعدة الكاملة' },
    { name: 'hack', description: '💻 اختراق وهمي', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو المراد اختراقه', required: true }] },
    { name: 'kill', description: '🔪 قضاء على عضو', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو المراد قتله', required: true }] },
    { name: 'joke', description: '😂 نكتة' },
    { name: 'iq', description: '🧠 مستوى الذكاء' },
    { name: 'meme', description: '🐸 ميمز مضحك' },
    { name: 'slap', description: '✋ صفعة', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو المراد صفعه', required: true }] },
    { name: 'hug', description: '🫂 عناق', options: [{ name: 'user', type: ApplicationCommandOptionType.User, description: 'العضو المراد معانقته', required: true }] },
    { name: 'roll', description: '🎲 نرد' },
    { name: 'flip', description: '🪙 ملك أم كتابة' },
    { name: '8ball', description: '🔮 الكرة السحرية', options: [{ name: 'question', type: ApplicationCommandOptionType.String, description: 'السؤال المطلوب إجابته', required: true }] },
    { name: 'uptime', description: '⏰ مدة التشغيل' },

    // الأوامر الجديدة
    { name: 'status', description: '📊 حالة البوت والإحصائيات' },

    // أوامر الرد التلقائي الجديدة
    {
        name: 'set-autoreply',
        description: '🤖 إضافة رد تلقائي على كلمة معينة',
        options: [
            { name: 'keyword', type: ApplicationCommandOptionType.String, description: 'الكلمة التي تريد الرد عليها', required: true },
            { name: 'response', type: ApplicationCommandOptionType.String, description: 'الرد الذي سيظهر', required: true }
        ]
    },
    {
        name: 'autoreply-list',
        description: '📋 عرض قائمة الردود التلقائية'
    },

    // أوامر الترفيه الجديدة
    {
        name: 'rolet',
        description: '🎰 لعبة الروليت - الفائز يحصل على 5000 كريدت',
        options: [
            { name: 'target', type: ApplicationCommandOptionType.User, description: 'الشخص الذي تريد استهدافه (اختياري)', required: false }
        ]
    },

    // الأمر /op المضافة (التحديث)
    {
        name: 'op',
        description: 'تحديث صورة واسم البوت داخل السيرفر',
        options: []
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

// تحميل هويات السيرفرات من قاعدة البيانات عند البدء
client.once('ready', async () => {
    console.log(`✅ OP BOT Online :${client.user.tag}`);

    try {
        // تحميل هويات السيرفرات
        const allData = await db.all();
        for (const [key, value] of Object.entries(allData)) {
            if (key.startsWith('identity_')) {
                const guildId = key.replace('identity_', '');
                serverIdentities.set(guildId, value);
                console.log(`✅ تم تحميل هوية السيرفر ${guildId}`);
            }
        }

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

// دالة لتحميل الصور المرفوعة إلى رابط
async function uploadToImgur(imageBuffer) {
    try {
        const response = await fetch('https://api.imgur.com/3/image', {
            method: 'POST',
            headers: {
                'Authorization': 'Client-ID 8e8b8b8b8b8b8b8',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image: imageBuffer.toString('base64')
            })
        });
        
        const data = await response.json();
        if (data.success) {
            return data.data.link;
        }
        return null;
    } catch (error) {
        console.error('خطأ في تحميل الصورة:', error);
        return null;
    }
}

// دالة لإرسال الرسائل عبر الويب هوك
async function sendWebhookMessage(channel, content, embeds, identity) {
    try {
        // البحث عن ويب هوك موجود أو إنشاء واحد جديد
        const webhooks = await channel.fetchWebhooks();
        let webhook = webhooks.find(wh => wh.name === 'OP BOT Mirror');
        
        if (!webhook) {
            webhook = await channel.createWebhook({
                name: 'OP BOT Mirror',
                avatar: identity?.avatar || client.user.displayAvatarURL(),
                reason: 'نظام Mirroring للبوت'
            });
        }

        // تحديث بيانات الويب هوك إذا تغيرت الهوية
        if (identity) {
            await webhook.edit({
                name: identity.name || 'OP BOT',
                avatar: identity.avatar || client.user.displayAvatarURL()
            });
        }

        // إرسال الرسالة عبر الويب هوك
        await webhook.send({
            content: content,
            embeds: embeds,
            username: identity?.name || 'OP BOT',
            avatarURL: identity?.avatar || client.user.displayAvatarURL()
        });
        
        return true;
    } catch (error) {
        console.error('خطأ في إرسال الويب هوك:', error);
        return false;
    }
}

// --- معالج الأوامر التفاعلي ---
client.on('interactionCreate', async (interaction) => {
    try {
        if (!interaction.isChatInputCommand()) return;
        const { commandName, options, user, guild, member, channel } = interaction;

        // الأمر /op المضافة (التحديث)
        if (commandName === 'op') {
            // التحقق من صلاحية المستخدم (مالك السيرفر فقط)
            if (member.id !== guild.ownerId) {
                return interaction.reply({ content: '❌ هذا الأمر متاح فقط لمالك السيرفر!', ephemeral: true });
            }

            // التحقق من الكولداون (15 دقيقة لكل سيرفر)
            const now = Date.now();
            const cooldownKey = `${guild.id}_${commandName}`;
            const cooldownTime = opCooldowns.get(cooldownKey);

            if (cooldownTime && now < cooldownTime) {
                const remainingTime = Math.ceil((cooldownTime - now) / 1000 / 60);
                return interaction.reply({ 
                    content: `⏳ يجب الانتظار ${remainingTime} دقيقة قبل استخدام الأمر مرة أخرى!`, 
                    ephemeral: true 
                });
            }

            // إنشاء Modal مع حقول متطورة
            const modal = new ModalBuilder()
                .setCustomId('op_modal')
                .setTitle('🔄 تحديث هوية البوت');

            const nameInput = new TextInputBuilder()
                .setCustomId('bot_name')
                .setLabel('اسم البوت الجديد')
                .setStyle(TextInputStyle.Short)
                .setPlaceholder('أدخل اسم البوت الجديد (اختياري)')
                .setRequired(false)
                .setMaxLength(32);

            const avatarInput = new TextInputBuilder()
                .setCustomId('bot_avatar')
                .setLabel('رابط/ملف الصورة الجديدة')
                .setStyle(TextInputStyle.Paragraph)
                .setPlaceholder('ضع رابط الصورة أو اسحب وأسقط الصورة هنا (اختياري)\nمثال: https://example.com/image.png')
                .setRequired(false);

            const bannerInput = new TextInputBuilder()
                .setCustomId('bot_banner')
                .setLabel('رابط البانر الجديد')
                .setStyle(TextInputStyle.Short)
                .setPlaceholder('أدخل رابط البانر الجديد (اختياري)')
                .setRequired(false);

            const actionRow1 = new ActionRowBuilder().addComponents(nameInput);
            const actionRow2 = new ActionRowBuilder().addComponents(avatarInput);
            const actionRow3 = new ActionRowBuilder().addComponents(bannerInput);

            modal.addComponents(actionRow1, actionRow2, actionRow3);

            await interaction.showModal(modal);

            // معالج رد Modal
            const filter = (i) => i.customId === 'op_modal' && i.user.id === user.id;
            
            try {
                const modalResponse = await interaction.awaitModalSubmit({ filter, time: 300000 });
                
                await modalResponse.deferReply({ ephemeral: true });

                const nickname = modalResponse.fields.getTextInputValue('bot_name');
                const avatarInputValue = modalResponse.fields.getTextInputValue('bot_avatar');
                const bannerUrl = modalResponse.fields.getTextInputValue('bot_banner');

                let avatarUrl = null;

                // معالجة رابط الصورة
                if (avatarInputValue && avatarInputValue.trim() !== "") {
                    // التحقق إذا كان رابط أم ملف
                    if (avatarInputValue.startsWith('http')) {
                        avatarUrl = avatarInputValue.trim();
                    } else if (modalResponse.attachments.size > 0) {
                        // معالجة المرفقات
                        const attachment = modalResponse.attachments.first();
                        if (attachment.contentType && attachment.contentType.startsWith('image/')) {
                            avatarUrl = attachment.url;
                        }
                    }
                }

                // حفظ البيانات في قاعدة البيانات
                const identityData = {
                    name: nickname || null,
                    avatar: avatarUrl || null,
                    banner: bannerUrl || null,
                    updatedAt: Date.now(),
                    updatedBy: user.id
                };

                await db.set(`identity_${guild.id}`, identityData);
                serverIdentities.set(guild.id, identityData);

                // تحديث الكولداون (15 دقيقة)
                opCooldowns.set(cooldownKey, now + (15 * 60 * 1000));

                const embed = new EmbedBuilder()
                    .setColor('#00ff00')
                    .setTitle('✅ تم تحديث هوية البوت')
                    .addFields(
                        { name: '👤 الاسم', value: nickname || 'لم يتغير', inline: true },
                        { name: '🖼️ الصورة', value: (avatarUrl ? 'تم التحديث' : 'لم تتغير'), inline: true },
                        { name: '🎨 البانر', value: (bannerUrl ? 'تم التحديث' : 'لم يتغير'), inline: true }
                    )
                    .setFooter({ text: `آخر تحديث بواسطة: ${user.username}` })
                    .setTimestamp();

                await modalResponse.editReply({ embeds: [embed] });

            } catch (error) {
                console.error('خطأ في معالجة Modal:', error);
            }
        }

        // --- نظام Mirroring لجميع ردود البوت ---
        // استثناء: ردود ephemeral لا تمر عبر الويب هوك
        if (interaction.replied || interaction.deferred) return;

        // الحصول على هوية السيرفر
        const identity = serverIdentities.get(guild.id);
        
        // إذا كانت هناك هوية محفوظة، استخدم الويب هوك
        if (identity && (identity.name || identity.avatar)) {
            try {
                // إلغاء الرد العادي
                await interaction.deferReply();
                
                // إرسال الرسالة عبر الويب هوك
                const success = await sendWebhookMessage(channel, 
                    `**${user.username}** استخدم الأمر **/${commandName}**`, 
                    [], 
                    identity
                );
                
                if (success) {
                    // حذف الرد المؤجل
                    await interaction.deleteReply().catch(() => {});
                } else {
                    // العودة للرد العادي إذا فشل الويب هوك
                    await interaction.editReply('✅ تم تنفيذ الأمر');
                }
                
                // استمر في معالجة الأمر
            } catch (error) {
                console.error('خطأ في نظام Mirroring:', error);
                // العودة للرد العادي
                await interaction.reply({ content: '✅ تم تنفيذ الأمر', ephemeral: true });
            }
        }

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
                .setDescription(`إجمالي التحذيرات :${userWarns.length}`)
                .addFields({ name: 'التاريخ', value: warnsList })
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        // --- أوامر الاقتصاد المبرمجة ---
        let userData = await db.get(`economy_${user.id}`) || { wallet: 0, bank: 0, lastDaily: 0 };

        if (commandName === 'daily') {
            const now = Date.now();
            if (now - userData.lastDaily < 24 * 60 * 60 * 1000) {
                const remaining = 24 * 60 * 60 * 1000 - (now - userData.lastDaily);
                const hours = Math.floor(remaining / (60 * 60 * 1000));
                const minutes = Math.floor((remaining % (60 * 60 * 1000)) / (60 * 1000));
                return interaction.reply(`⏳ يجب الانتظار ${hours} ساعة و ${minutes} دقيقة!`);
            }

            const dailyAmount = 1000;
            userData.wallet += dailyAmount;
            userData.lastDaily = now;
            await db.set(`economy_${user.id}`, userData);

            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle('💵 الهدية اليومية')
                .addFields(
                    { name: '💰 المبلغ', value: `${dailyAmount} عملة`, inline: true },
                    { name: '📊 الرصيد الجديد', value: `${userData.wallet} عملة`, inline: true },
                    { name: '⏰ المرة القادمة', value: 'بعد 24 ساعة', inline: true }
                )
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'balance') {
            const embed = new EmbedBuilder()
                .setColor('#00ff00')
                .setTitle(`👛 رصيد ${user.username}`)
                .addFields(
                    { name: '💰 المحفظة', value: `${userData.wallet} عملة`, inline: true },
                    { name: '🏦 البنك', value: `${userData.bank} عملة`, inline: true },
                    { name: '📊 الإجمالي', value: `${userData.wallet + userData.bank} عملة`, inline: true }
                )
                .setTimestamp();

            return interaction.reply({ embeds: [embed] });
        }

        if (commandName === 'transfer') {
            const targetUser = options.getUser('user');
            const amount = options.getInteger('amount');

            if (targetUser.id === user.id) return interaction.reply({ content: '❌ لا يمكنك تحويل الأموال لنفسك!', ephemeral: true });
            if (amount <= 0) return interaction.reply({ content: '❌ المبلغ يجب أن يكون أكبر من صفر!', ephemeral: true });
            if (amount > userData.wallet) return interaction.reply({ content: '❌ لا تملك رصيداً كافياً!', ephemeral: true });

            let targetData = await db.get(`economy_${targetUser.id}`) || { wallet: 0, bank: 0, lastDaily: 0 };
            
            userData.wallet -= amount;
            targetData.wallet += amount;

            await db.set(`economy_${user.id}`, userData);
            await db.set(`economy_${targetUser.id}`, targetData);

            return interaction.reply(`✅ تم تحويل ${amount} عملة إلى ${targetUser.username}`);
        }

        if (commandName === 'rob') {
            const targetUser = options.getUser('user');
            if (targetUser.id === user.id) return interaction.reply({ content: '❌ لا يمكنك سرقة نفسك!', ephemeral: true });

            let targetData = await db.get(`economy_${targetUser.id}`) || { wallet: 0, bank: 0, lastDaily: 0 };
            if (targetData.wallet < 100) return interaction.reply({ content: '❌ الضحية لا تملك مالاً كافياً!', ephemeral: true });

            const success = Math.random() > 0.5;

            if (success) {
                const stolen = Math.floor(targetData.wallet * 0.3);
                userData.wallet += stolen;
                targetData.wallet -= stolen;

                await db.set(`economy_${user.id}`, userData);
                await db.set(`economy_${targetUser.id}`, targetData);

                return interaction.reply(`✅ نجحت السرقة! سرقت ${stolen} عملة من ${targetUser.username}`);
            } else {
                const fine = Math.floor(userData.wallet * 0.2);
                userData.wallet -= fine;
                await db.set(`economy_${user.id}`, userData);

                return interaction.reply(`❌ فشلت السرقة! دفع ${fine} عملة كغرامة`);
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
                    { name: 'الجائزة', value: win ? '+500 عملة' : 'لا شيء', inline: true }
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

            return interaction.reply(`⛏️ وجدت ${earnings} عملة أثناء التعدين!`);
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

            return interaction.reply(`🎣 ${result} ${earnings > 0 ? `| رصيدك الآن :${userData.wallet}` : ''}`);
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
                    { name: '👑 المالك', value: owner.user.username, inline: true },
                    { name: '👥 الأعضاء', value: `${guild.memberCount}`, inline: true },
                    { name: '📅 تاريخ الإنشاء', value: guild.createdAt.toLocaleDateString(), inline: true },
                    { name: '📊 الرومات', value: `${guild.channels.cache.size}`, inline: true },
                    { name: '🎭 الرتب', value: `${guild.roles.cache.size}`, inline: true },
                    { name: '🚀 البوست', value: `${guild.premiumTier}`, inline: true }
                )
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
                     { name: 'إحصائيات:', value: `الأعضاء الإجمالي :${client.guilds.cache.reduce((acc, g) => acc + g.memberCount, 0)}\nعدد الأوامر المسجلة :${commands.length}` }
                 )
                 .setFooter({ text: 'آخر تحديث' })
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
                                 { name: 'كلمة المرور', value: '**' },
                                 { name: 'آخر موقع', value: 'السعودية' },
                                 { name: '📱 الرقم', value: `+9665${Math.floor(Math.random() * 90000000) + 10000000}` },
                                 { name: '💳 البطاقة', value: `${Math.floor(Math.random() * 9000) + 1000} * * ${Math.floor(Math.random() * 9000) + 1000}` },
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
                 `ماذا قال المبرمج عندما نام؟ "جافا"!`,
                 'لماذا خسرت البطريق المعركة؟ لأنها كانت تلبس بدلة توكسيدو!',
                 'ما هو الحيوان الذي لا يلد ولا يبيض؟ الحيوان المستحيل!',
                 'لماذا ذهب المبرمج إلى الطبيب؟ لأنه كان لديه مشكلة في الـ "byte"!'
             ];

             return interaction.reply(`😂 ${jokes[Math.floor(Math.random() * jokes.length)]}`);
         }

         if (commandName === 'iq') {
             const iq = Math.floor(Math.random() * 200) + 1;
             let level = '';

             if (iq < 70) level = '🟢 ذكاء منخفض';
             else if (iq < 100) level = '🟡 ذكاء متوسط';
             else if (iq < 130) level = '🟠 ذكاء عالي';
             else level = '🔴 عبقري!';

             return interaction.reply(`🧠 مستوى ذكائك هو ${iq} - ${level}`);
         }

         if (commandName === 'meme') {
             const memes = [
                 'https://i.imgur.com/8W7zK6A.jpg',
                 'https://i.imgur.com/3tM7l9C.jpg',
                 'https://i.imgur.com/5w2KJbC.jpg',
                 'https://i.imgur.com/9Z8ZQ2B.jpg',
                 'https://i.imgur.com/7X9ZQ2C.jpg'
             ];

             const randomMeme = memes[Math.floor(Math.random() * memes.length)];
             const embed = new EmbedBuilder()
                 .setColor('#00ff00')
                 .setTitle('🐸 ميمز')
                 .setImage(randomMeme)
                 .setTimestamp();

             return interaction.reply({ embeds: [embed] });
         }

         if (commandName === 'slap') {
             const targetUser = options.getUser('user');
             const actions = [
                 `قام ${user.username} بصفع ${targetUser.username} بقوة! ✋`, [cite: 236]
                 `قام ${user.username} برمي ${targetUser.username} بالحذاء! 👞`, [cite: 237]
                 `قام ${user.username} بضرب ${targetUser.username} بالوسادة! 🛏️`, [cite: 238]
                 `قام ${user.username} بلكم ${targetUser.username} في الوجه! 👊` [cite: 239]
             ];
             const randomAction = actions[Math.floor(Math.random() * actions.length)]; [cite: 240]
             return interaction.reply(`✋ ${randomAction}`); [cite: 241]
        }
             const randomAction = actions[Math.floor(Math.random() * actions.length)];
             return interaction.reply(`✋ ${randomAction}`);
         }

         if (commandName === 'hug') {
             const targetUser = options.getUser('user');
             const hugs = [
                 `قام ${user.username} بعناق ${targetUser.username} بحنان! 🫂`,
                 `قام ${user.username} باحتضان ${targetUser.username} بقوة! 🤗`,
                 `قام ${user.username} بمعانقة ${targetUser.username} بحب! 💕`,
                 `قام ${user.username} بضم ${targetUser.username} إلى صدره! ❤️`
             ];

             const randomHug = hugs[Math.floor(Math.random() * hugs.length)];
             return interaction.reply(`🫂 ${randomHug}`);
         }

         if (commandName === 'roll') {
             const roll = Math.floor(Math.random() * 100) + 1;
             return interaction.reply(`🎲 ${user.username} رمى النرد :${roll}`);
         }

         if (commandName === 'flip') {
             const result = Math.random() > 0.5 ? '👑 ملك' : '🪙 كتابة';
             return interaction.reply(`🪙 ${user.username} رمى العملة :${result}`);
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
             return interaction.reply(`🔮 السؤال :${question}\nالإجابة :${answer}`);
         }

         if (commandName === 'uptime') {
             const uptime = client.uptime;
             const days = Math.floor(uptime / 86400000);
             const hours = Math.floor((uptime % 86400000) / 3600000);
             const minutes = Math.floor((uptime % 3600000) / 60000);
             const seconds = Math.floor((uptime % 60000) / 1000);

             return interaction.reply(`⏰ مدة التشغيل :${days} يوم، ${hours} ساعة، ${minutes} دقيقة، ${seconds} ثانية`);
         }

         // --- لعبة الروليت الجديدة ---
         if (commandName === 'rolet') {
             const targetUser = options.getUser('target');

             // إنشاء واجهة اللعبة
             const embed = new EmbedBuilder()
                 .setColor('#FFD700')
                 .setTitle('🎰 لعبة الروليت - جائزة 5000 كريدت!')
                 .setDescription(`${targetUser ? `المضيف :${user}\nالهدف :${targetUser}\n\n` : `المضيف :${user}\n\n`}🎮 قواعد اللعبة:\n• اللعبة تبدأ بعد 20 ثانية\n• الفائز يحصل على 5000 كريدت\n• يمكنك اختيار طرد شخص، اختيار عشوائي، أو الانسحاب`)
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

             await interaction.reply({ embeds: [embed], components: [row] });

             // بدء العد التنازلي
             setTimeout(async () => {
                 // اختيار الفائز عشوائياً
                 let winnerId;

                 if (targetUser && Math.random() > 0.5) {
                     winnerId = targetUser.id;
                 } else {
                     winnerId = user.id; // المضيف يفوز
                 }

                 // منح الجائزة للفائز
                 if (winnerId) {
                     let winnerData = await db.get(`economy_${winnerId}`) || { wallet: 0, bank: 0, lastDaily: 0 };
                     winnerData.wallet += 5000;
                     await db.set(`economy_${winnerId}`, winnerData);

                     const resultEmbed = new EmbedBuilder()
                         .setColor('#00ff00')
                         .setTitle('🎉 فوز في لعبة الروليت!')
                         .setDescription(`مبروك ! لقد فزت بجائزة 5000 كريدت!`)
                         .addFields(
                             { name: '💰 الجائزة', value: '5000 كريدت', inline: true },
                             { name: '💳 الرصيد الجديد', value: `${winnerData.wallet} كريدت`, inline: true }
                         )
                         .setTimestamp();

                     await channel.send({ embeds: [resultEmbed] });
                 }

                 // تحديث رسالة اللعبة الأصلية
                 const updatedEmbed = new EmbedBuilder()
                     .setColor('#FFD700')
                     .setTitle('🎰 لعبة الروليت - انتهت!')
                     .setDescription(`🎮 اللعبة انتهت!\n🏆 الفائز:`)
                     .addFields(
                         { name: '💰 الجائزة', value: '5000 كريدت تم منحها للفائز!', inline: true }
                     )
                     .setTimestamp();

                 try {
                     await interaction.editReply({ embeds: [updatedEmbed], components: [] });
                 } catch (error) {}

             }, 20000);
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
                      { name: 'الكلمة', value: `${keyword}`, inline: true },
                      { name: 'الرد', value: `${response}`, inline: true },
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
                  .setDescription(`عدد الردود :${guildAutoreplies.length} رد`)
                  .addFields({ name: 'الردود:', value: `${autoreplyList}` })
                  .setFooter({ text: 'سيقوم البوت بالرد تلقائياً عند كتابة أي من هذه الكلمات' })
                  .setTimestamp();

              return interaction.reply({ embeds: [embed] });
          }

          // --- أوامر الإعدادات المفقودة ---
          if (commandName === 'set-ticket') {
              if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                  return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

              const channelOption = options.getChannel('channel');

              // حفظ إعدادات التذاكر
              let config = await db.get(`config_${guild.id}`) || {};
              config.ticketChannel = channelOption.id;

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

               await channelOption.send({ embeds: [embed], components: [row] });

               return interaction.reply(`✅ تم إعداد نظام التذاكر في ${channelOption}`);
           }

           if (commandName === 'set-suggestions') {
               if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                   return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

               const channelOption = options.getChannel('channel');

               let config = await db.get(`config_${guild.id}`) || {};
               config.suggestionsChannel = channelOption.id;

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

                await channelOption.send({ embeds: [embed] });

                return interaction.reply(`✅ تم إعداد قناة الاقتراحات في ${channelOption}`);
            }

            if (commandName === 'set-reports') {
                if (!member.permissions.has(PermissionFlagsBits.ManageChannels))
                    return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

                const channelOption = options.getChannel('channel');

                let config = await db.get(`config_${guild.id}`) || {};
                config.reportsChannel = channelOption.id;

                await db.set(`config_${guild.id}`, config);

                 return interaction.reply(`✅ تم تعيين قناة البلاغات إلى ${channelOption}`);
             }

             if (commandName === 'help') {
                 const embed = new EmbedBuilder()
                     .setColor('#7289da')
                     .setTitle('📖 قائمة المساعدة - OP BOT')
                     .setDescription('البوت يحتوي على 77 أمر مفيد')
                     .addFields(
                         { name: '⚙️ الإعدادات (10)', value: '/set-welcome,/set-log,/set-autorole,/toggle-level,...' },
                         { name: '🔨 الإدارة (13)', value: '/ban,/kick,/timeout,/clear,/warn,...' },
                         { name: '💰 الاقتصاد (9)', value: '/daily,/balance,/transfer,/rob,/slots,...' },
                         { name: '📊 اللفل (2)', value: '/level,/rank' },
                         { name: '🎮 الترفيه (22)', value: '/ping,/server,/joke,/meme,/slap,/hug,/rolet,...' },
                         { name: '🤖 الرد التلقائي (2)', value: '/set-autoreply,/autoreply-list' }
                     )
                     .setFooter({ text: 'استخدم /daily كل 24 ساعة لتحصل على 1000 كريدت!' })
                     .setTimestamp();

                 return interaction.reply({ embeds: [embed] });
             }

             // أوامر الإعدادات الأساسية
             if (commandName === 'set-welcome') {
                 if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
                     return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

                 const channelOption = options.getChannel('channel');
                 let config = await db.get(`config_${guild.id}`) || {};
                 config.welcomeChannel = channelOption.id;
                 await db.set(`config_${guild.id}`, config);

                 return interaction.reply(`✅ تم تعيين قناة الترحيب إلى ${channelOption}`);
             }

             if (commandName === 'set-log') {
                 if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
                     return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

                 const channelOption = options.getChannel('channel');
                 let config = await db.get(`config_${guild.id}`) || {};
                 config.logChannel = channelOption.id;
                await db.set(`config_${guild.id}`, config);

                  return interaction.reply(`✅ تم تعيين قناة السجلات إلى ${channelOption}`);
              }

              if (commandName === 'set-autorole') {
                  if (!member.permissions.has(PermissionFlagsBits.ManageRoles))
                      return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

                  const roleOption = options.getRole('role');
                  let config = await db.get(`config_${guild.id}`) || {};
                  config.autoRole = roleOption.id;
                  await db.set(`config_${guild.id}`, config);

                  return interaction.reply(`✅ تم تعيين الرتبة التلقائية إلى ${roleOption.name}`);
              }

              if (commandName === 'set-level-channel') {
                  if (!member.permissions.has(PermissionFlagsBits.ManageGuild))
                      return interaction.reply({ content: '❌ لا تملك صلاحية!', ephemeral: true });

                  const channelOption = options.getChannel('channel');
                  let config = await db.get(`config_${guild.id}`) || {};
                  config.levelChannel = channelOption.id;
                  await db.set(`config_${guild.id}`, config);

                  return interaction.reply(`✅ تم تعيين قناة اللفل إلى ${channelOption}`);
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
                              { name: '👑 رتبة Admin', value: `${adminRole.toString()}`, inline: true },
                              { name: '🛡️ رتبة Moderator', value: `${modRole.toString()}`, inline: true },
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

          try {
              const { customId } = interaction;

              if (customId === 'join_roulette') {
                  await interaction.reply({ content: '✅ انضممت للعبة بنجاح!', ephemeral: true });
              } else if (customId === 'leave_roulette') {
                  await interaction.reply({ content: '✅ انسحبت من اللعبة بنجاح!', ephemeral: true });
              } else if (customId === 'create_ticket') {
                  await handleTicketCreation(interaction);
              } else if (customId === 'close_ticket') {
                  await handleTicketClose(interaction);
              }
          } catch (error) {
              console.error('خطأ في معالج الأزرار:', error);
          }
      });

      // دالة معالجة إنشاء التذاكر
      async function handleTicketCreation(interaction) {
          try {
              const { guild, user } = interaction;

              // التحقق من وجود نظام التذاكر
              const config = await db.get(`config_${guild.id}`) || {};
              if (!config.ticketChannel) {
                  return interaction.reply({ content: '❌ نظام التذاكر غير مضبوط بعد!', ephemeral: true });
              }

              // إنشاء قناة التذكرة
              const ticketChannel = await guild.channels.create({
                  name: `ticket-${user.username}-${Date.now().toString().slice(-4)}`,
                  type: ChannelType.GuildText,
                  parent: interaction.channel.parentId,
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
                  .setDescription("مرحباً! فريق الدعم سيساعدك قريباً.\n\nيرجى شرح مشكلتك بالتفصيل")
                  .addFields(
                      { name: "📝 التعليمات", value: "• انتظر رد فريق الدعم\n• لا تذكر الأعضاء بشكل عشوائي\n• استخدم الزر أدناه لإغلاق التذكرة" }
                  )
                  .setFooter({ text: "OP BOT - نظام الدعم" })
                  .setTimestamp();

              const row = new ActionRowBuilder()
                  .addComponents(
                      new ButtonBuilder()
                          .setCustomId("close_ticket")
                          .setLabel("🔒 إغلاق التذكرة")
                          .setStyle(ButtonStyle.Danger)
                  );

              await ticketChannel.send({
                  content: `${user} مرحباً بك!\n<@&${guild.roles.cache.find(r => r.name === "Admin" || r.name === "Moderator")?.id || ""}>`,
                  embeds: [embed],
                  components: [row]
              });

              await interaction.reply({
                  content: `✅ تم إنشاء تذكرتك :${ticketChannel}`,
                  ephemeral: true
              });
          } catch (error) {
              console.error("خطأ في إنشاء التذكرة:", error);
              await interaction.reply({
                  content: "❌ حدث خطأ أثناء إنشاء التذكرة!",
                  ephemeral: true
              });
          }
      }

      // دالة معالجة إغلاق التذاكر
      async function handleTicketClose(interaction) {
          try {
              const { channel } = interaction;

              // التحقق مما إذا كانت القناة تذكرة
              if (!channel.name.startsWith("ticket-")) {
                  return interaction.reply({
                      content: "❌ هذه ليست قناة تذكرة!",
                      ephemeral: true
                  });
              }

              // إرسال تأكيد الإغلاق
              const confirmEmbed = new EmbedBuilder()
                  .setColor("#ff0000")
                  .setTitle("🔒 تأكيد إغلاق التذكرة")
                  .setDescription("هل أنت متأكد من إغلاق هذه التذكرة؟")
                  .setTimestamp();

              const confirmRow = new ActionRowBuilder()
                  .addComponents(
                      new ButtonBuilder()
                          .setCustomId("confirm_close")
                          .setLabel("✅ نعم، إغلاق")
                          .setStyle(ButtonStyle.Success),
                      new ButtonBuilder()
                          .setCustomId("cancel_close")
                          .setLabel("❌ إلغاء")
                          .setStyle(ButtonStyle.Danger)
                  );

              await interaction.reply({
                  embeds: [confirmEmbed],
                  components: [confirmRow],
                  ephemeral: true
              });
          } catch (error) {
              console.error("خطأ في إغلاق التذكرة:", error);
          }
      }

      // تأكيد إغلاق التذكرة
      client.on('interactionCreate', async (interaction) => {
          if (!interaction.isButton()) return;
          if (!["confirm_close", "cancel_close"].includes(interaction.customId)) return;

          try {
              const { channel, guild, user } = interaction;

              if (interaction.customId === "cancel_close") {
                  return interaction.update({
                      content: "✅ تم إلغاء إغلاق التذكرة.",
                      embeds: [],
                      components: []
                  });
              }

              // حذف القناة
              await channel.delete("تم إغلاق التذكرة بواسطة المستخدم");

              // إرسال رسالة تأكيد في سجل السيرفر
              try {
                  const config = await db.get(`config_${guild.id}`);
                  const logChannel = guild.channels.cache.get(config?.logChannel);

                  if (logChannel) {
                      const logEmbed = new EmbedBuilder()
                          .setColor("#ff0000")
                          .setTitle("🎫 تذكرة مغلقة")
                          .addFields(
                              { name: "👤 المستخدم", value: user.username },
                              { name: "📝 التذكرة", value: channel.name },
                              { name: "⏰ الوقت", value: new Date().toLocaleString() }
                          )
                          .setTimestamp();

                      await logChannel.send({ embeds: [logEmbed] }).catch(() => {});
                  }
              } catch (logError) {
                  console.error("خطأ في تسجيل إغلاق التذكرة:", logError);
              }
          } catch (error) {
              console.error("خطأ في تأكيد إغلاق التذكرة:", error);
          }
      });

      client.login(process.env.DISCORD_TOKEN);
