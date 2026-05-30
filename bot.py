import discord
from discord.ext import commands
from discord import app_commands, ui
import zipfile
import json
import io
import re
import os
import asyncio
from dotenv import load_dotenv

# --- CONFIGURAÇÕES ---
load_dotenv('bottoken.env')
TOKEN = os.getenv('DISCORD_TOKEN')

ID_MOD_CREATOR_ROLE = 1245882306275573770
ID_TRIAGE_CHANNEL = 1470284207556137021
ID_FORUM_CATEGORIES = [1241215896379330560, 1468674890407346340]

FLAGS = {
    "italy": "🇮🇹", "germany": "🇩🇪", "japan": "🇯🇵", "usa": "🇺🇸", 
    "france": "🇫🇷", "great britain": "🇬🇧", "brazil": "🇧🇷", "england": "🇬🇧", "portugal": "🇵🇹"
}

# --- OPÇÕES DOS MENUS SUSPENSOS ---
CLASS_OPTIONS = [
    discord.SelectOption(label="Toaster", emoji="🍞"),
    discord.SelectOption(label="Street", emoji="🏙️"),
    discord.SelectOption(label="Sport", emoji="🏎️"),
    discord.SelectOption(label="Tuned", emoji="🔧"),
    discord.SelectOption(label="Super", emoji="🔥"),
    discord.SelectOption(label="Hyper", emoji="💎")
]

DRIVETRAIN_OPTIONS = [
    discord.SelectOption(label="AWD"),
    discord.SelectOption(label="RWD"),
    discord.SelectOption(label="FWD")
]

GEARBOX_OPTIONS = [
    discord.SelectOption(label="Manual", emoji="🕹️"),
    discord.SelectOption(label="Automatic", emoji="⚙️")
]

# --- UTILITÁRIOS ---
async def delete_after_delay(file_path: str, delay: int = 180):
    """Remove o ficheiro após o tempo determinado para poupar espaço no servidor."""
    print(f"⏳ [TIMER] Contagem de {delay}s iniciada para remover: {file_path}")
    await asyncio.sleep(delay)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✨ [LIMPEZA] Ficheiro {file_path} removido com sucesso.")
        else:
            print(f"❓ [LIMPEZA] O ficheiro {file_path} já não existia.")
    except Exception as e:
        print(f"❌ [ERRO] Falha ao apagar {file_path}: {e}")

def extract_numbers(text_val, default="?"):
    """Extrai o primeiro número encontrado em uma string."""
    if not text_val or text_val == '?': 
        return default
    nums = re.findall(r'\d+', str(text_val))
    return int(nums[0]) if nums else default

def format_speed(text_val):
    val = extract_numbers(text_val)
    if val == "?": return "?"
    return f"{round(val * 1.609)} km/h" if 'mph' in str(text_val).lower() else f"{val} km/h"

def format_power(text_val):
    val = extract_numbers(text_val)
    return f"{val} HP" if val != "?" else "?"

# --- PROCESSAMENTO DO MOD ---
async def process_zip(file_path):
    """Lê o ui_car.json e extrai as informações e tags do carro."""
    info = {
        'name': '?', 'brand': 'Other', 'author': 'Unknown', 
        'bhp': '?', 'torque': '?', 'weight': '?', 
        'topspeed': '?', '0_100': '?', 'country': '?', 'year': '?',
        'tags': [] 
    }
    preview_file = None
    
    try:
        with zipfile.ZipFile(file_path) as z:
            file_list = z.namelist()
            ui_car_path = next((f for f in file_list if f.lower().endswith('ui_car.json')), None)
            
            if ui_car_path:
                with z.open(ui_car_path) as f:
                    content_bytes = f.read()
                    try:
                        content_text = content_bytes.decode('utf-8-sig')
                    except UnicodeDecodeError:
                        content_text = content_bytes.decode('latin-1', errors='ignore')
                    
                    data = json.loads(content_text, strict=False)
                
                info['brand'] = str(data.get('brand', 'Other')).strip()
                info['author'] = str(data.get('author', 'Unknown')).strip()
                info['name'] = data.get('name', '?')
                info['year'] = data.get('year', '?')
                
                country_raw = str(data.get('country', '')).lower()
                info['country'] = f"{data.get('country', '?')} {FLAGS.get(country_raw, '')}".strip()
                
                raw_tags = data.get('tags', [])
                info['tags'] = [str(t).lower().replace('#', '').strip() for t in raw_tags]
                
                specs = data.get('specs', {}) or data 
                info['bhp'] = format_power(specs.get('bhp', specs.get('power', '?')))
                info['topspeed'] = format_speed(specs.get('topspeed', '?'))
                
                tq = extract_numbers(specs.get('torque', '?'))
                info['torque'] = f"{tq} Nm" if tq != "?" else "?"
                
                wg = extract_numbers(specs.get('weight', '?'))
                info['weight'] = f"{wg} kg" if wg != "?" else "?"
                
                accel = str(specs.get('acceleration', '?')).lower().replace('0-100', '').strip()
                nums_accel = re.findall(r'\d+\.?\d*', accel)
                info['0_100'] = f"{nums_accel[0]}s 0-100" if nums_accel else '?'
            
            img_path = next((f for f in file_list if 'preview.jpg' in f.lower()), None)
            if img_path:
                preview_file = discord.File(io.BytesIO(z.read(img_path)), filename="preview.jpg")
                
    except Exception as e:
        print(f"❌ [ZIP ERROR] Erro ao processar arquivo: {e}")
        return None

    return info, preview_file

# --- INTERFACE DO DISCORD ---
class PostView(ui.View):
    def __init__(self, info, file_img, original_msg):
        super().__init__(timeout=None)
        self.info = info
        self.file_img = file_img
        self.original_msg = original_msg
        
        self.sel_class = "Street"
        self.sel_drive = "RWD"
        self.sel_gear = "Manual"

    @ui.select(placeholder="1. Select Class", options=CLASS_OPTIONS)
    async def select_class(self, interaction: discord.Interaction, select):
        self.sel_class = select.values[0]
        await interaction.response.send_message(f"✅ Class: {self.sel_class}", ephemeral=True)

    @ui.select(placeholder="2. Select Drivetrain", options=DRIVETRAIN_OPTIONS)
    async def select_drive(self, interaction: discord.Interaction, select):
        self.sel_drive = select.values[0]
        await interaction.response.send_message(f"✅ Drivetrain: {self.sel_drive}", ephemeral=True)

    @ui.select(placeholder="3. Select Gearbox", options=GEARBOX_OPTIONS)
    async def select_gear(self, interaction: discord.Interaction, select):
        self.sel_gear = select.values[0]
        await interaction.response.send_message(f"✅ Gearbox: {self.sel_gear}", ephemeral=True)

    @ui.button(label="Confirm & Post", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button):
        # 1. Verifica Permissão
        if not interaction.guild.get_role(ID_MOD_CREATOR_ROLE) in interaction.user.roles:
            return await interaction.response.send_message("❌ You are not allowed to perform this action!", ephemeral=True)

        # 2. Desabilita o botão IMEDIATAMENTE e atualiza a mensagem (isso evita duplo clique/duplicação)
        button.disabled = True
        await interaction.response.edit_message(view=self)

        # Encontra o Fórum da Marca
        forum_target = None
        brand_query = str(self.info['brand']).lower().replace(" ", "-")
        
        for cat_id in ID_FORUM_CATEGORIES:
            category = interaction.client.get_channel(cat_id)
            if category and hasattr(category, 'forums'):
                for channel in category.forums:
                    if brand_query in channel.name.lower():
                        forum_target = channel
                        break
            if forum_target: break

        if not forum_target:
            # Como usamos edit_message, agora usamos followup para avisos
            button.disabled = False
            await interaction.message.edit(view=self)
            return await interaction.followup.send(f"⚠️ Fórum para a marca `{self.info['brand']}` não encontrado!", ephemeral=True)

        # --- LÓGICA DE TAGS (REVERTIDA PARA A SUA IDEIA ORIGINAL) ---
        tags_from_json = set(self.info.get('tags', []))
        tags_from_ui = {self.sel_class.lower(), self.sel_drive.lower(), self.sel_gear.lower()}
        all_desired_tags = tags_from_json.union(tags_from_ui)

        # O Discord filtra e pega apenas as tags que já existem no canal do fórum
        applied_tags = [t for t in forum_target.available_tags if t.name.lower() in all_desired_tags]

        # Formata o Corpo do Post
        content = (
            f"> **Power:** {self.info['bhp']}\n"
            f"> **Torque:** {self.info['torque']}\n"
            f"> **Weight:** {self.info['weight']}\n"
            f"> **Top Speed:** {self.info['topspeed']}\n"
            f"> **0-100:** {self.info['0_100']}\n"
            f"> **Author:** {self.info['author']}\n"
            f"> **Specs:** {self.sel_drive} | {self.sel_gear} | {self.sel_class}\n"
            f"> **Country:** {self.info['country']}\n"
            f"> **Year:** {self.info['year']}"
        )

        try:
            # Cria a Thread no Fórum
            thread = await forum_target.create_thread(
                name=self.info['name'][:100], 
                content=content, 
                file=self.file_img, 
                applied_tags=applied_tags
            )
            
            view_redirect = ui.View()
            view_redirect.add_item(ui.Button(
                label="Direct Download File", 
                url=self.original_msg.jump_url, 
                emoji="💬", 
                style=discord.ButtonStyle.link
            ))
            
            await thread.thread.send(content="**Click Below To Download This File:**", view=view_redirect)
            await interaction.followup.send(f"✅ Mod Successfully Posted in {forum_target.mention}!", ephemeral=True)
            
            await self.original_msg.add_reaction("🏁")
            
        except Exception as e:
            print(f"❌ [POST ERROR] Falha ao criar tópico: {e}")
            button.disabled = False
            await interaction.message.edit(view=self)
            await interaction.followup.send(f"❌ Error posting in forum: {e}", ephemeral=True)

# --- INICIALIZAÇÃO DO BOT ---
class ModBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        print("🔄 Sync Slash Commands...")
        await self.tree.sync()

    async def on_ready(self):
        print(f'🤖 WMC Organizer Online: {self.user} (ID: {self.user.id})')

bot = ModBot()

@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id != ID_TRIAGE_CHANNEL:
        return
    
    if message.attachments and message.attachments[0].filename.endswith('.zip'):
        role = message.guild.get_role(ID_MOD_CREATOR_ROLE)
        if role not in message.author.roles: 
            return
        
        await message.add_reaction('⏳')
        temp_filename = f"temp_{message.attachments[0].filename}"
        print(f"📥 [DISCO] A guardar mod recebido: {temp_filename}")
        
        try:
            await message.attachments[0].save(temp_filename)
            res = await process_zip(temp_filename)
            
            if res:
                info, img = res
                view = PostView(info, img, message)
                await message.reply(f"Organizar Mod: **{info['name']}**", view=view)
            else:
                await message.remove_reaction('⏳', bot.user)
                await message.add_reaction('❌')
                
        finally:
            asyncio.create_task(delete_after_delay(temp_filename, 180))

if __name__ == "__main__":
    bot.run(TOKEN)