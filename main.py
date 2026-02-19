import os
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv
import json
from core import GMNInterface, ContextManager
import datetime
import shutil
import logging
import signal
import sys
import tempfile
import asyncio

load_dotenv()

class GMNDBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.config = self.load_config()
        self.gmn = GMNInterface()
        self.context = ContextManager()
        self.setup_logging()
        self.setup_signals()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler("system.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("gmnd")

    def setup_signals(self):
        def signal_handler(sig, frame):
            self.logger.info(f"Signal {sig} received. Shutting down...")
            asyncio.create_task(self.close())
            sys.exit(0)
        
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                return json.load(f)
        except Exception:
            return {"resident_channel_id": None, "allowed_channel_ids": [], "default_model": "gemini-1.5-flash"}

    async def setup_hook(self):
        await self.tree.sync()
        self.daily_maintenance.start()

    @tasks.loop(time=datetime.time(hour=3, minute=0))
    async def daily_maintenance(self):
        print("Starting daily maintenance...")
        now_date = datetime.datetime.now().strftime("%Y-%m-%d")
        summary_prompt = "以下の会話ログから、重要な決定事項、共有された情報、および翌日以降も保持すべき文脈を日付付きで簡潔に要約してください。形式：[YYYY-MM-DD] トピック名: 内容"
        
        for guild_folder in os.listdir(self.context.base_data_path):
            guild_path = os.path.join(self.context.base_data_path, guild_folder)
            if not os.path.isdir(guild_path): continue
            
            for channel_folder in os.listdir(guild_path):
                channel_path = os.path.join(guild_path, channel_folder)
                current_file = os.path.join(channel_path, "current.txt")
                archive_file = os.path.join(channel_path, "archive.txt")
                system_file = os.path.join(channel_path, "system.txt")
                
                if os.path.exists(current_file) and os.path.getsize(current_file) > 0:
                    try:
                        # バックアップ作成
                        shutil.copy(current_file, current_file + ".bak")
                        
                        # 要約生成
                        summary = self.gmn.query(summary_prompt, system_file, [current_file])
                        
                        # アーカイブ追記
                        with open(archive_file, "a") as f:
                            f.write(f"\n{summary}\n")
                        
                        # current クリーンアップ
                        open(current_file, 'w').close()
                        print(f"Maintenance completed for channel {channel_folder}")
                    except Exception as e:
                        print(f"Maintenance failed for channel {channel_folder}: {e}")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def on_message(self, message):
        if message.author == self.user:
            return

        # 常駐チャンネルまたはメンションを検知
        is_resident = message.channel.id == self.config.get("resident_channel_id")
        is_mentioned = self.user in message.mentions

        if is_resident or is_mentioned:
            async with message.channel.typing():
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # マルチモーダル対応（簡易版: ファイル名をコンテキストに含めるか、gmnの引数に渡す設計が必要）
                # 仕様書によると -f で渡せるとあるので、gmn インターフェースの拡張が必要かもしれない
                attachments_info = ""
                if message.attachments:
                    attachments_info = f" [Attachments: {', '.join([a.filename for a in message.attachments])}]"

                # コンテキストに記録
                self.context.append_message(message.guild.id, message.channel.id, now, message.author.display_name, message.content + attachments_info)
                
                # gmn 呼び出し
                context_files = self.context.get_context_files(message.guild.id, message.channel.id)
                system_file = self.context._get_path(message.guild.id, message.channel.id, "system.txt")
                if not os.path.exists(system_file):
                    self.context.set_system_prompt(message.guild.id, message.channel.id, "You are a helpful assistant.")

                try:
                    extra_files = []
                    temp_dir = None
                    if message.attachments:
                        temp_dir = tempfile.mkdtemp()
                        for attachment in message.attachments:
                            file_path = os.path.join(temp_dir, attachment.filename)
                            await attachment.save(file_path)
                            extra_files.append(file_path)

                    response = self.gmn.query(message.content, system_file, context_files, extra_files=extra_files)
                    
                    if temp_dir:
                        shutil.rmtree(temp_dir)
                    
                    self.context.append_message(message.guild.id, message.channel.id, now, "Bot", response)
                    
                    for i in range(0, len(response), 2000):
                        await message.channel.send(response[i:i+2000])
                except Exception as e:
                    self.logger.error(f"Error in on_message: {e}")
                    await message.channel.send(f"Error: {e}")

bot = GMNDBot()

@bot.tree.command(name="status", description="gmn の生存確認、コンテキスト量の表示")
async def status(interaction: discord.Interaction):
    await interaction.response.send_message("gmnd is running. gmn interface is active.")

@bot.tree.command(name="config", description="常駐チャンネル等の動作設定を変更")
@app_commands.checks.has_permissions(administrator=True)
async def config(interaction: discord.Interaction, key: str, value: str):
    if key == "resident_channel_id":
        try:
            bot.config["resident_channel_id"] = int(value)
            with open("config.json", "w") as f:
                json.dump(bot.config, f, indent=4)
            await interaction.response.send_message(f"Updated resident_channel_id to {value}")
        except ValueError:
            await interaction.response.send_message("Invalid channel ID")
    else:
        await interaction.response.send_message(f"Configuration key '{key}' is not supported yet.")

@bot.tree.command(name="set_system", description="システムプロンプト（人格設定）を更新")
@app_commands.checks.has_permissions(administrator=True)
async def set_system(interaction: discord.Interaction, prompt: str):
    bot.context.set_system_prompt(interaction.guild_id, interaction.channel_id, prompt)
    await interaction.response.send_message("System prompt updated for this channel.")

class ConfirmClear(discord.ui.View):
    def __init__(self, bot, guild_id, channel_id, scope):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.scope = scope

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.scope == "all":
            files = ["current.txt", "archive.txt"]
        else:
            files = ["current.txt"]
            
        for f in files:
            path = self.bot.context._get_path(self.guild_id, self.channel_id, f)
            if os.path.exists(path):
                os.remove(path)
        await interaction.response.edit_message(content=f"Context ({self.scope}) cleared.", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Operation cancelled.", view=None)

@bot.tree.command(name="clear_context", description="履歴を消去")
@app_commands.checks.has_permissions(administrator=True)
async def clear_context(interaction: discord.Interaction, scope: str = "current"):
    view = ConfirmClear(bot, interaction.guild_id, interaction.channel_id, scope)
    await interaction.response.send_message(f"Really clear the {scope} context?", view=view)

@bot.tree.command(name="model", description="使用する Gemini モデルを切り替え")
async def model(interaction: discord.Interaction, name: str):
    bot.config["default_model"] = name
    with open("config.json", "w") as f:
        json.dump(bot.config, f, indent=4)
    await interaction.response.send_message(f"Default model switched to {name}")

@bot.tree.command(name="help", description="機能一覧と使い方の表示")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="gmnd Help", description="Available commands:")
    embed.add_field(name="/status", value="Check bot and gmn status.", inline=False)
    embed.add_field(name="/config <key> <value>", value="Update bot configuration (Admin only).", inline=False)
    embed.add_field(name="/set_system <prompt>", value="Update system prompt for this channel (Admin only).", inline=False)
    embed.add_field(name="/clear_context <scope>", value="Clear conversation history (Admin only).", inline=False)
    embed.add_field(name="/model <name>", value="Switch default Gemini model.", inline=False)
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token:
        bot.run(token)
    else:
        print("DISCORD_BOT_TOKEN not found in .env")
