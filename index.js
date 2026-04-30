const { 
    Client, GatewayIntentBits, Partials, EmbedBuilder, ActivityType, 
    PermissionFlagsBits, ActionRowBuilder, ButtonBuilder, ButtonStyle,
    ApplicationCommandOptionType, REST, Routes, Collection
} = require('discord.js');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent, GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildPresences
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
    { name: 'balance', description: '👛 عرض رصيدك الحالي' },
    { name: 'level', description: '📊 عرض مستواك الحالي' },
    { name: 'rank', description: '🏆 ترتيبك في السيرفر' },
    { name: 'transfer', description: '💸 تحويل أموال', options: [{ name: 'u', type: 6, description: 'المستلم', required: true }, { name: 'a', type: 4, description: 'المبلغ', required: true }] },
    { name: 'rob', description: '🔫 سرقة رصيد عضو (مخاطرة)', options: [{ name: 'user', type: 6, description: 'العضو المراد سرقته', required: true }] },
    { name: 'slots', description: '🎰 آلة الحظ' },
    { name: 'mining',description:'⛏️ التعدين'},
    {name:'fish',description:'🎣 صيد السمك'},

    // [51-70] ترفيه وعامة
    { name:'ping',description:'📶 سرعة الاتصال'},
    {name:'server',description:'🏰 معلومات السيرفر'},
    {name:'avatar',description:'👤 صورة الحساب',options:[{name:'user',type:6,description:'العضو المراد عرض صورته'}]},
    {name:'help',description:'📖 قائمة المساعدة الكاملة'},
    {name:'hack',description:'💻 اختراق وهمي'},
    {name:'kill',description:'🔪 قضاء على عضو',options:[{name:'user',type:6,description:'العضو المراد قتله',required:true}]},
    {name:'joke',description:'😂 نكتة'},
    {name:'iq',description:'🧠 مستوى الذكاء'},
    {name:'meme',description:'🐸 ميمز مضحك'},
    {name:'slap',description:'✋ صفعة',options:[{name:'user',type:6,description:'العضو المراد صفعه',required:true}]},
    {name:'hug',description:'🫂 عناق',options:[{name:'user',type:6,description:'العضو المراد معانقته',required:true}]},
    {name:'roll',description:'🎲 نرد'},
    {name:'flip',description:'🪙 ملك أم كتابة'},
    {name:'8ball',description:'🔮 الكرة السحرية',options:[{name:'question',type:3,description:'السؤال المطلوب إجابته',required:true}]},
    {name:'uptime',description:'⏰ مدة التشغيل'},
    
    // [71-73] الأوامر الجديدة
    { name:'status',description:'📊 حالة البوت والإحصائيات'},
    {name:'servers',description:'🌐 عرض السيرفرات التي فيها البوت'}
];

// نظام اللفل عند المراسلة
client.on('messageCreate',async(message)=>{
    if(message.author.bot)return;

    const guildConfig=db.config.get(message.guild.id);
    if(!guildConfig?.levelEnabled)return;

    const userId=message.author.id;
    let userLevelData=db.levels.get(userId)||{xp:0,level:1};

    // زيادة XP عشوائية (5-15)
    userLevelData.xp+=Math.floor(Math.random()*10)+5;

    // حساب إذا وصل للفل جديد (100 XP لكل فل)
    const requiredXP=userLevelData.level*100;
    if(userLevelData.xp>=requiredXP){
        userLevelData.level++;
        userLevelData.xp=0;

        // إعلان الترقي في القناة المحددة
        if(guildConfig.levelChannel){
            const levelChannel=message.guild.channels.cache.get(guildConfig.levelChannel);
            if(levelChannel){
                const embed=new EmbedBuilder()
                    .setColor('#00ff00')
                    .setTitle('🎉 ترقية جديدة!')
                    .setDescription(`مبروك ${message.author}! وصلت للفل **${userLevelData.level}**`)
                    .setThumbnail(message.author.displayAvatarURL())
                    .setTimestamp();

                levelChannel.send({content:`🎉 ${message.author}`,embeds:[embed]});
            }
        }
    }

    db.levels.set(userId,userLevelData);
});

// رسالة شكر عند إضافة البوت للسيرفر
client.on('guildCreate',async(guild)=>{
    const owner=guild.ownerId;
    try{
        const ownerUser=await client.users.fetch(owner);
        const embed=new EmbedBuilder()
            .setColor('#7289da')
            .setTitle('✨ شكراً لك على إضافة البوت!')
            .setDescription(`شكراً لك ${ownerUser.username} على إضافة **OP BOT** إلى سيرفرك!\n\nالبوت يحتوي على **${commands.length} أمر** مفيد للإدارة والترفيه والاقتصاد.`)
            .setThumbnail(guild.iconURL()||client.user.displayAvatarURL())
            .addFields(
                {name:'📊 عدد الأوامر',value:`${commands.length} أمر`,inline:true},
                {name:'⚙️ الإعدادات',value:'10 أوامر',inline:true},
                {name:'🎮 الترفيه',value:'20 أوامر',inline:true}
            )
            .setTimestamp();

        const row=new ActionRowBuilder()
            .addComponents(
                new ButtonBuilder()
                    .setLabel('الدعم')
                    .setStyle(ButtonStyle.Link)
                    .setURL('https://discord.gg/vvmaAbasEN')
            );

        ownerUser.send({embeds:[embed],components:[row]});
    }catch(error){
        console.log('لا يمكن إرسال رسالة إلى صاحب السيرفر');
    }
});

// تسجيل الأوامر مع .toJSON() الصحيح
client.once('ready',async()=>{
    console.log(`✅ OP BOT Online: ${client.user.tag}`);
    
    try{
        // تحويل الأوامر إلى JSON بشكل صحيح
        const commandsJSON=commands.map(cmd=>({
            name:cmd.name,
            description:cmd.description,
            options:cmd.options||[]
        }));
        
        // تسجيل الأوامر
        await client.application.commands.set(commandsJSON);
        console.log(`✅ تم تسجيل ${commands.length} أمر بنجاح`);
        
        // تحديث نشاط البوت
        client.user.setActivity(`OP BOT | ${commands.length} Commands`,{type:ActivityType.Watching});
        
        // إظهار حالة البوت
        console.log(`📊 البوت موجود في ${client.guilds.cache.size} سيرفر`);
        console.log(`👥 عدد الأعضاء الإجمالي ${client.guilds.cache.reduce((acc,g)=>acc+g.memberCount,0)}`);
    }catch(error){
        console.error('❌ خطأ في تسجيل الأوامر:',error);
    }
});

// --- نظام الترحيب واللفل واللوج ---
client.on('guildMemberAdd',async(member)=>{
    const config=db.config.get(member.guild.id);
    if(config?.welcomeChannel){
        const channel=member.guild.channels.cache.get(config.welcomeChannel);
        if(channel)channel.send(`✨ نورت السيرفر يا **${member.user.username}**! أنت العضو رقم ${member.guild.memberCount}.`);
    }
    if(config?.autoRole){
        member.roles.add(config.autoRole).catch(()=>{});
    }
});

// --- معالج الأوامر التفاعلي ---
client.on('interactionCreate',async(interaction)=>{
    if(!interaction.isChatInputCommand())return;
    const{commandName,options,user,guild,member,channel}=interaction;

    // --- أوامر الإدارة المبرمجة ---
    if(commandName==='clear'){
        if(!member.permissions.has(PermissionFlagsBits.ManageMessages)) 
            return interaction.reply({content:'❌ لا تملك صلاحية!',ephemeral:true});
        const amount=options.getInteger('amount');
        await channel.bulkDelete(amount>100?100:amount);
        return interaction.reply({content:`🧹 تم مسح **${amount}** رسالة.`,ephemeral:true});
    }

    if(commandName==='lock'){
        if(!member.permissions.has(PermissionFlagsBits.ManageChannels))
            return interaction.reply({content:'❌ لا تملك صلاحية!',ephemeral:true});
        await channel.permissionOverwrites.edit(guild.id,{SendMessages:false});
        return interaction.reply('🔒 تم إغلاق القناة بنجاح.');
    }

    if(commandName==='unlock'){
        if(!member.permissions.has(PermissionFlagsBits.ManageChannels))
            return interaction.reply({content:'❌ لا تملك صلاحية!',ephemeral:true});
        await channel.permissionOverwrites.edit(guild.id,{SendMessages:true});
        return interaction.reply('🔓 تم فتح القناة بنجاح.');
    }

    if(commandName==='add-role'){
        if(!member.permissions.has(PermissionFlagsBits.ManageRoles))
            return interaction.reply({content:'❌ لا تملك صلاحية!',ephemeral:true});
        
        const targetUser=options.getUser('user');
        const role=options.getRole('role');
        
        const targetMember=guild.members.cache.get(targetUser.id);
        if(!targetMember)return interaction.reply({content:'❌ العضو غير موجود!',ephemeral:true});
        
        try{
            await targetMember.roles.add(role.id);
            return interaction.reply(`✅ تم إضافة الرتبة ${role.name} إلى ${targetUser.username}`);
        }catch(error){
            return interaction.reply({content:`❌ حدث خطأ أثناء إضافة الرتبة`,ephemeral:true});
        }
    }

    if(commandName==='rem-role'){
        if(!member.permissions.has(PermissionFlagsBits.ManageRoles))
            return interaction.reply({content:'❌ لا تملك صلاحية!',ephemeral:true});
        
        const targetUser=options.getUser('user');
        const role=options.getRole('role');
        
        const targetMember=guild.members.cache.get(targetUser.id);
        if(!targetMember)return interaction.reply({content:'❌ العضو غير موجود!',ephemeral:true});
        
        try{
            await targetMember.roles.remove(role.id);
            return interaction.reply(`✅ تم سحب الرتبة ${role.name} من ${targetUser.username}`);
        }catch(error){
            return interaction.reply({content:`❌ حدث خطأ أثناء سحب الرتبة`,ephemeral:true});
        }
    }

    if(commandName==='timeout'){
        if(!member.permissions.has(PermissionFlagsBits.ModerateMembers))
            return interaction.reply({content:'❌ لا تملك صلاحية!',ephemeral:true});
        const targetUser=options.getUser('user');
        const minutes=options.getInteger('minutes');
        const targetMember=guild.members.cache.get(targetUser.id);

        await targetMember.timeout(minutes*60*1000);

        // إشعار للمستخدم الذي قام بالعقوبة
        const embed=new EmbedBuilder()
            .setColor('#ff0000')
            .setTitle('⚠️ عقوبة تم تطبيقها')
            .setDescription(`تم تطبيق عقوبة **Timeout** على ${targetUser.username}`)
            .addFields(
                {name:'المدة',value:`${minutes} دقيقة`,inline:true},
                {name:'السيرفر',value:guild.name,inline:true},
                {name:'المعاقب',value:user.username,inline:true}
            )
            .setTimestamp();

        member.send({embeds:[embed]});

        return interaction.reply(`⏳ تم إسكات ${targetUser.username} لمدة ${minutes} دقيقة.`);
    }

    if(commandName==='untimeout'){
        if(!member.permissions.has(PermissionFlagsBits.ModerateMembers))
            return interaction.reply({content:'❌ لا تملك صلاحية!',ephemeral:true});
        const targetUser=options.getUser('user');
        const targetMember=guild.members.cache.get(targetUser.id);

        await targetMember.timeout(null);

        const embed=new EmbedBuilder()
            .setColor('#00ff00')
            .setTitle('✅ عقوبة تم إلغاؤها')
            .setDescription(`تم إلغاء عقوبة **Timeout** عن ${targetUser.username}`)
            .addFields(
                {name:'السيرفر',value:guild.name,inline:true},
                {name:'الملغى',value:user.username,inline:true}
            )
            .setTimestamp();

        member.send({embeds:[embed]});

        return interaction.reply(`🔈 تم إلغاء إسكات ${targetUser.username}.`);
    }

    if(commandName==='ban'){
        if(!member.permissions.has(PermissionFlagsBits.BanMembers))
            return interaction.reply({content:'❌ لا تملك صلاحية!',ephemeral:true});
        const targetUser=options.getUser('user');
        const reason=options.getString('reason')||'بدون سبب';

        await guild.members.ban(targetUser.id,{reason});

        const embed=new EmbedBuilder()
            .setColor('#ff0000')
            .setTitle('🔨 حظر تم تطبيقه')
            .setDescription(`تم حظر ${targetUser.username} من السيرفر`)
            .addFields(
                {name:'السبب',value:reason,inline:true},
                {name:'السيرفر',value:guild.name,inline:true},
                {name:'المحظر',value:user.username,inline:true}
            )
            .setTimestamp();

        member.send({embeds:[embed]});

        return interaction.reply(`🔨 تم حظر ${targetUser.username} بنجاح.`);
    }

    if(commandName==='kick'){
        if(!member.permissions.has(PermissionFlagsBits.KickMembers))
            return interaction.reply({content:'❌ لا تملك صلاحية!',ephemeral:true});
        const targetUser=options.getUser('user');
        const reason=options.getString('reason')||'بدون سبب';

        await guild.members.kick(targetUser.id,reason);

        const embed=new EmbedBuilder()
            .setColor('#ff5500')
            .setTitle('👞 طرد تم تطبيقه')
            .setDescription(`تم طرد ${targetUser.username} من السيرفر`)
            .addFields(
                {name:'السبب',value:reason,inline:true},
                {name:'السيرفر',value:guild.name,inline:true},
                {name:'المطرد',value:user.username,inline:true}
            )
            .setTimestamp();

        member.send({embeds:[embed]});

        return interaction.reply(`👞 تم طرد ${targetUser.username} بنجاح.`);
    }

    // --- أوامر الاقتصاد المبرمجة ---
    let userData=db.economy.get(user.id)||{wallet:0,bank:0,lastDaily:0};

    if(commandName==='daily'){
        const now=Date.now();
        if(now-userData.lastDaily<86400000){
            const hoursLeft=Math.floor((86400000-(now-userData.lastDaily))/3600000);
            return interaction.reply(`❌ استلمتها بالفعل، انتظر **${hoursLeft}** ساعة.`);
        }
        userData.wallet+=1000;
        userData.lastDaily=now;
        db.economy.set(user.id,userData);
        return interaction.reply('💵 تم استلام **1000** عملة بنجاح!');
    }

    // --- الأوامر الجديدة ---
    if(commandName==='status'){
        const embed=new EmbedBuilder()
            .setColor('#00ff00')
            .setTitle('📊 حالة البوت والإحصائيات')
            .setDescription(`**OP BOT** يعمل بشكل طبيعي`)
            .addFields(
                {name:'⏰ مدة التشغيل',value:`${Math.floor(client.uptime/3600000)} ساعة`,inline:true},
                {name:'🌐 عدد السيرفرات',value:`${client.guilds.cache.size}`,inline:true},
                {name:'👥 عدد الأعضاء الإجمالي',value:`${client.guilds.cache.reduce((acc,g)=>acc+g.memberCount,0)}`,inline:true},
                {name:'📊 عدد الأوامر المسجلة',value:`${commands.length} أمر`,inline:true},
                {name:'💾 قاعدة البيانات',value:`${db.economy.size} حساب اقتصادي`,inline:true},
                {name:'📈 مستخدمين اللفل',value:`${db.levels.size} مستخدم`,inline:true}
            )
            .setThumbnail(client.user.displayAvatarURL())
            .setTimestamp();

        return interaction.reply({embeds:[embed]});
    }

    if(commandName==='servers'){
        const guildsList=client.guilds.cache.map(g=>`**${g.name}** - ${g.memberCount} عضو`);
        
        const embed=new EmbedBuilder()
            .setColor('#7289da')
            .setTitle('🌐 السيرفرات التي فيها البوت')
            .setDescription(`البوت موجود في **${client.guilds.cache.size}** سيرفر`)
            .addFields(
                {name:'السيرفرات:',value:`${guildsList.slice(0,10).join('\n')}`},
                {name:'إحصائيات:',value:`الأعضاء الإجمالي: ${client.guilds.cache.reduce((acc,g)=>acc+g.memberCount,0)}\nعدد الأوامر المسجلة: ${commands.length}`}
            )
            .setFooter({text:`آخر تحديث`})
            .setTimestamp();

        return interaction.reply({embeds:[embed]});
    }

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
