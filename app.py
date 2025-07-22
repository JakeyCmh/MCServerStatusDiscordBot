import discord
from discord.ext import commands, tasks
from mcstatus import JavaServer
import requests
import asyncio


intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content for commands

bot = commands.Bot(command_prefix='!', intents=intents)

# ---- CONFIG ----
DISCORD_TOKEN = 'YOUR_DISCORD_BOT_TOKEN_HERE'

# KineticHost API stuff
KINETIC_API_KEY = 'YOUR_KINETIC_API_KEY_HERE'
KINETIC_PANEL_URL = 'https://kineticpanel.net'  # Change if needed

maintenance_status = {
    'main': False,
    'proxy1': False,
    'proxy2': False,
    'proxy3': False,
}

SERVER_NAME_MAP = {
    'main': 'main',
    'na': 'proxy1',
    'eu': 'proxy2',
    'asia': 'proxy3',
}

DISPLAY_NAMES = {
    'main': 'Main Server',
    'proxy1': 'NA Proxy',
    'proxy2': 'EU Proxy',
    'proxy3': 'Asia Proxy',
}

# Kinetic server IDs (main + proxies)
KINETIC_SERVERS = {
    'main': 'YOUR_MAIN_SERVER_ID',
    'proxy1': '',
    'proxy2': '',
    'proxy3': '',
}

# Minecraft addresses (IP or domain + port)
MC_SERVERS = {
    'main': 'YOUR_MAIN_MC_SERVER_ADDRESS:PORT',
    'proxy1': 'YOUR_PROXY1_MC_SERVER_ADDRESS:PORT',
    'proxy2': 'YOUR_PROXY2_MC_SERVER_ADDRESS:PORT',
    'proxy3': 'YOUR_PROXY3_MC_SERVER_ADDRESS:PORT',
}

# Subdomains to display
SUBDOMAINS = {
    'main': 'Join Via Proxies',
    'proxy1': 'YOUR_NA_PROXY_SUBDOMAIN',
    'proxy2': 'YOUR_EU_PROXY_SUBDOMAIN',
    'proxy3': 'YOUR_ASIA_PROXY_SUBDOMAIN',
}

# Discord channel ID for status message
CHANNEL_ID = 123456789012345678  # Replace with your channel ID (int)

# Update interval in seconds
UPDATE_INTERVAL = 60  # 5 minutes

# Staff Role ID for command permissions
STAFF_ROLE_ID = 123456789012345678  # Replace with your staff role ID (int)

# ID of the status message to edit (or None to send a new one)
status_message_id = None


headers = {
    'Authorization': f'Bearer {KINETIC_API_KEY}',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}

def get_kinetic_status(server_id):
    try:
        url = f"{KINETIC_PANEL_URL}/api/client/servers/{server_id}"
        resp = requests.get(url, headers=headers, timeout=10)

        resp.raise_for_status()
        data = resp.json().get('attributes', {})

        status = data.get('status', 'unknown')
        resources = data.get('resources', {})
        limits = data.get('limits', {})

        ram_current = resources.get('memory_bytes_used')
        ram_limit = limits.get('memory_bytes')

        if ram_current is None or ram_limit is None:
            return status, None, None

        ram_current_mb = ram_current / (1024 * 1024)
        ram_limit_mb = ram_limit / (1024 * 1024)
        return status, ram_current_mb, ram_limit_mb

    except Exception as e:
        print(f"⚠️ API Error: {e}")
        return 'error', None, None


async def ping_mc_server(address):
    try:
        server = JavaServer.lookup(address)
        status = server.status()
        return True, status.players.online, status.players.max
    except Exception:
        return False, 0, 0


async def build_status_embed():
    lines = []
    for key in ['main', 'proxy1', 'proxy2', 'proxy3']:
        display_name = DISPLAY_NAMES.get(key, key.capitalize())

        # Check maintenance status
        if maintenance_status.get(key, False):
            maintenance_text = "⚠️ **Down for maintenance**"
            status_emoji = "⛔"
            players_online = '-'
            players_max = '-'
            kin_status_str = ""
            ram_str = ""
            subdomain_display = SUBDOMAINS.get(key, "(Connect Via Proxy)") if key != 'main' else "(Connect Via Proxy)"
        else:
            # Normal status check
            if key == 'main':
                kin_status, ram_used, ram_max = get_kinetic_status(KINETIC_SERVERS[key])
                if ram_used is not None and ram_max is not None:
                    ram_str = f"{ram_used:.1f}MB / {ram_max:.1f}MB"
                elif ram_max is not None:
                    ram_str = f"Unknown / {ram_max / 1024:.1f}GB"
                else:
                    ram_str = "N/A"
            else:
                kin_status, ram_str = 'N/A', ''

            mc_online, players_online, players_max = await ping_mc_server(MC_SERVERS[key])
            status_emoji = "🟢" if mc_online else "🔴"
            kin_status_str = kin_status if kin_status != 'error' else 'Unknown'
            subdomain_display = SUBDOMAINS.get(key, "unknown") if key != 'main' else "(Connect Via Proxy)"
            maintenance_text = ""

        line = (
            f"**{display_name}** `{subdomain_display}`\n"
            f"• MC Status: {status_emoji} "
            f"{'Online' if not maintenance_text and mc_online else maintenance_text or 'Offline'}"
            f" ({players_online}/{players_max} players)\n"
        )

        if key == 'main' and not maintenance_text:
            line += (
                f"• KineticHost Status: {kin_status_str}\n"
                f"• RAM Usage: {ram_str}\n"
            )

        lines.append(line)

    embed = discord.Embed(title="Minecraft Server Status", color=0x00ff00)
    embed.description = "\n".join(lines)
    embed.set_footer(text="Data from KineticHost API and MC ping")
    return embed


@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def maintenance(ctx, action: str = None, server: str = None):
    if action is None or server is None:
        await ctx.send("Usage: `!maintenance on|off NA|EU|ASIA|MAIN|ALL`")
        return

    action = action.lower()
    server = server.lower()

    if action not in ('on', 'off'):
        await ctx.send("⚠️ Invalid action! Use `on` or `off`.")
        return

    if server == 'all':
        for key in maintenance_status.keys():
            maintenance_status[key] = (action == 'on')
        await ctx.send(f"✅ Maintenance mode for **ALL servers** set to **{action.upper()}**.")
    elif server not in SERVER_NAME_MAP:
        await ctx.send("⚠️ Invalid server! Use `NA`, `EU`, `ASIA`, `MAIN`, or `ALL`.")
        return
    else:
        key = SERVER_NAME_MAP[server]
        maintenance_status[key] = (action == 'on')
        await ctx.send(f"✅ Maintenance mode for **{server.upper()}** set to **{action.upper()}**.")

    # Update the status embed in your channel
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"Channel ID {CHANNEL_ID} not found.")
        return

    global status_message_id
    if status_message_id is None:
        embed = await build_status_embed()
        msg = await channel.send(embed=embed)
        status_message_id = msg.id
    else:
        try:
            msg = await channel.fetch_message(status_message_id)
            embed = await build_status_embed()
            await msg.edit(embed=embed)
        except discord.NotFound:
            embed = await build_status_embed()
            msg = await channel.send(embed=embed)
            status_message_id = msg.id

@maintenance.error
async def maintenance_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("⛔ You do not have permission to use this command.")


update_enabled = True

@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def updates(ctx, action: str = None):
    global update_enabled
    if action is None:
        await ctx.send("Usage: `!updates on|off`")
        return

    action = action.lower()
    if action not in ('on', 'off'):
        await ctx.send("⚠️ Invalid action! Use `on` or `off`.")
        return

    update_enabled = (action == 'on')
    if update_enabled:
        update_status.start()
        await ctx.send("✅ Updates have been turned ON. Status messages will be updated.")
    else:
        update_status.stop()
        await ctx.send("⚠️ Updates have been turned OFF. Status messages will NOT be updated.")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    if update_enabled:
        update_status.start()


@tasks.loop(seconds=UPDATE_INTERVAL)
async def update_status():
    global status_message_id
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"Channel ID {CHANNEL_ID} not found!")
        return

    embed = await build_status_embed()

    try:
        if status_message_id is None:
            # Send a new message first time
            msg = await channel.send(embed=embed)
            status_message_id = msg.id
            print(f"Status message sent: {status_message_id}")
        else:
            # Edit existing message
            msg = await channel.fetch_message(status_message_id)
            await msg.edit(embed=embed)
            print(f"Status message updated: {status_message_id}")
    except discord.NotFound:
        # Message was deleted; send a new one
        msg = await channel.send(embed=embed)
        status_message_id = msg.id
        print(f"Status message recreated: {status_message_id}")
    except Exception as e:
        print(f"Failed to update status message: {e}")


@bot.command()
async def status(ctx):
    embed = await build_status_embed()
    await ctx.send(embed=embed)


bot.run(DISCORD_TOKEN)
