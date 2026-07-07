import os
import discord
from discord.ext import commands, tasks
import dotenv

dotenv.load_dotenv()

intents = discord.Intents.none()
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="! ", intents=intents, help_command=None)

button_messages = {}

class SendModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="送信する", timeout=None)
        
        self.content = discord.ui.TextInput(
            label="メッセージ内容を入力してください。",
            style=discord.TextStyle.long,
            required=True,
            max_length=1800,
        )
        self.add_item(self.content)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        thread_name = interaction.channel.name
        try:
            user_id = thread_name.split("(")[1].removesuffix(")")
            user = await interaction.client.fetch_user(int(user_id))
        except Exception:
            await interaction.followup.send(content="チャンネル名からユーザーIDを解析できませんでした。", ephemeral=True)
            return

        if not user:
            await interaction.followup.send(content=f"そのメンバーが存在しません。\nユーザーid: {user_id}", ephemeral=True)
            return
        
        try:
            await user.send(content=self.content.value + f"\n-# {interaction.user.name}が担当しています。")
        except discord.Forbidden:
            await interaction.followup.send(content="ユーザーがDMを閉じてお出かけ中か、ブロックされているため送信できませんでした。", ephemeral=True)
            return

        channel = bot.get_channel(1523887748287692850)
        if channel:
            webhooks = await channel.webhooks()
            webhook = discord.utils.get(webhooks, name=thread_name)
            if webhook:
                await webhook.send(
                    content=self.content.value, 
                    allowed_mentions=discord.AllowedMentions.none(), 
                    thread=interaction.channel,
                    avatar_url=interaction.user.display_avatar.url,
                    username=interaction.user.name
                )

            button_message = button_messages.get(thread_name)
            if button_message:
                try:
                    await button_message.delete()
                except discord.NotFound:
                    pass

            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label="送信", custom_id="reply_send", style=discord.ButtonStyle.primary))
            button_messages[thread_name] = await interaction.channel.send(view=view)

@tasks.loop(seconds=10)
async def status_loop():
    await bot.change_presence(activity=discord.CustomActivity(name="連絡はDMへ", emoji="📩"))

@bot.event
async def on_ready():
    status_loop.start()
    print('Ready.')

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data.get("component_type") == 2:
            custom_id = interaction.data.get("custom_id")
            if custom_id == "reply_send":
                await interaction.response.send_modal(SendModal())

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    if message.guild:
        return
    
    thread_name = f"{message.author.name} ({message.author.id})"
    channel = bot.get_channel(1523887748287692850)
    
    if not channel:
        print("指定されたチャンネルが見つかりません。")
        return

    webhooks = await channel.webhooks()
    webhook = discord.utils.get(webhooks, name=thread_name)
    
    if not webhook:
        webhook = await channel.create_webhook(name=thread_name)

    target_thread = None
    for t in channel.threads:
        if t.name == thread_name:
            target_thread = t
            break

    if not target_thread:
        target_thread = await channel.create_thread(
            name=thread_name, 
            type=discord.ChannelType.public_thread
        )

    button_message = button_messages.get(thread_name)
    if button_message:
        try:
            await button_message.delete()
        except discord.NotFound:
            pass

    await webhook.send(
        content=message.content, 
        allowed_mentions=discord.AllowedMentions.none(), 
        thread=target_thread,
        avatar_url=message.author.display_avatar.url,
        username=message.author.name
    )
    
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="送信", custom_id="reply_send", style=discord.ButtonStyle.primary))
    button_messages[thread_name] = await target_thread.send(view=view, content="送信は返信は下のボタンから行えます。")

bot.run(os.environ.get('TOKEN'))