import discord, requests
from discord.ext import commands, tasks
from mcstatus import JavaServer
import requests
import asyncio

intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content for commands

bot = commands.Bot(command_prefix='!', intents=intents)

updates_enabled = True

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
    'proxy1': 'YOUR_PROXY1_SERVER_ID',
    'proxy2': 'YOUR_PROXY2_SERVER_ID',
    'proxy3': 'YOUR_PROXY3_SERVER_ID',
}

# Minecraft addresses (IP or domain + port)
MC_SERVERS = {
    'main': 'YOUR_MAIN_MC_IP:PORT',
    'proxy1': 'YOUR_PROXY1_MC_IP:PORT',
    'proxy2': 'YOUR_PROXY2_MC_IP:PORT',
    'proxy3': 'YOUR_PROXY3_MC_IP:PORT',
}

# Subdomains to display
SUBDOMAINS = {
    'main': 'Join Via Proxies',
    'proxy1': 'YOUR_NA_PROXY_SUBDOMAIN',
    'proxy2': 'YOUR_EU_PROXY_SUBDOMAIN',
    'proxy3': 'YOUR_ASIA_PROXY_SUBDOMAIN',
}

# Discord channel ID for status message
CHANNEL_ID = YOUR_CHANNEL_ID_HERE  # integer without quotes, e.g. 123456789012345678

# Update interval in seconds
UPDATE_INTERVAL = 60  # 1 minute
# ----------------

headers = {
    'Authorization': f'Bearer {KINETIC_API_KEY}',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}

status_message_id = None  # Will hold the ID of the message to edit
STAFF_ROLE_ID = YOUR_STAFF_ROLE_ID_HERE  # integer without quotes, e.g. 123456789012345678

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
                    ram_str = "?/16gb"
            else:
                kin_status, ram_str = '?/16gb', ''

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
    embed.set_footer(text="Embed updates every 60 seconds")
    return embed


# ------------------------------------ Maintenance command handler ------------------------------------------ #
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
        await ctx.send(f"✅ Maintenance mode set to **{action.upper()}** for **ALL servers**.")
    elif server in SERVER_NAME_MAP:
        key = SERVER_NAME_MAP[server]
        maintenance_status[key] = (action == 'on')
        await ctx.send(f"✅ Maintenance mode for **{server.upper()}** set to **{action.upper()}**.")
    else:
        await ctx.send("⚠️ Invalid server! Use `NA`, `EU`, `ASIA`, `MAIN`, or `ALL`.")
        return

    # Update the status embed in your channel
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"Channel ID {CHANNEL_ID} not found.")
        return

    global status_message_id
    embed = await build_status_embed()

    try:
        msg = await channel.fetch_message(status_message_id)
        await msg.edit(embed=embed)
    except discord.NotFound:
        msg = await channel.send(embed=embed)
        status_message_id = msg.id
# ----------------------------------------------------- Maintenance Command Handler End ------------------------------------------- #
#------------------------------------------------------ Updates on/off command handler start -------------------------------------- #
@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def updates(ctx, toggle: str = None):
    global updates_enabled

    if toggle is None or toggle.lower() not in ('on', 'off'):
        await ctx.send("Usage: `!updates on` or `!updates off`")
        return

    updates_enabled = (toggle.lower() == 'on')

    if updates_enabled:
        if not update_status.is_running():
            update_status.start()
        await ctx.send("✅ Status updates have been **enabled**.")
    else:
        if update_status.is_running():
            update_status.cancel()
        await ctx.send("⛔ Status updates have been **disabled**.")
#------------------------------------------------------ Updates on/off command handler end -------------------------------------- #

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    update_status.start()

@tasks.loop(seconds=UPDATE_INTERVAL)
async def update_status():
    if not updates_enabled:
        return  # Skip updating if disabled

    global status_message_id
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"Channel ID {CHANNEL_ID} not found!")
        return

    embed = await build_status_embed()

    try:
        if status_message_id is None:
            msg = await channel.send(embed=embed)
            status_message_id = msg.id
            print(f"Status message sent: {status_message_id}")
        else:
            msg = await channel.fetch_message(status_message_id)
            await msg.edit(embed=embed)
            print(f"Status message updated: {status_message_id}")
    except discord.NotFound:
        msg = await channel.send(embed=embed)
        status_message_id = msg.id
        print(f"Status message recreated: {status_message_id}")
    except Exception as e:
        print(f"Failed to update status message: {e}")


@bot.command()
async def status(ctx):
    embed = await build_status_embed()
    await ctx.send(embed=embed)
# ----------- other commands added 7/27/25 -------------- #
@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def restart(ctx, server: str):
    server = server.lower()
    if server not in KINETIC_SERVERS or not KINETIC_SERVERS[server]:
        await ctx.send("⚠️ Invalid server.")
        return
    url = f"{KINETIC_PANEL_URL}/api/client/servers/{KINETIC_SERVERS[server]}/power"
    resp = requests.post(url, headers=headers, json={"signal": "restart"})
    if resp.status_code == 204:
        await ctx.send(f"🔄 Restarted **{server}** server.")
    else:
        await ctx.send("❌ Failed to restart.")

@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def start(ctx, server: str):
    server = server.lower()
    if server not in KINETIC_SERVERS or not KINETIC_SERVERS[server]:
        await ctx.send("⚠️ Invalid server.")
        return
    url = f"{KINETIC_PANEL_URL}/api/client/servers/{KINETIC_SERVERS[server]}/power"
    resp = requests.post(url, headers=headers, json={"signal": "start"})
    if resp.status_code == 204:
        await ctx.send(f"▶️ Started **{server}** server.")
    else:
        await ctx.send("❌ Failed to start.")

@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def stop(ctx, server: str):
    server = server.lower()
    if server not in KINETIC_SERVERS or not KINETIC_SERVERS[server]:
        await ctx.send("⚠️ Invalid server.")
        return
    url = f"{KINETIC_PANEL_URL}/api/client/servers/{KINETIC_SERVERS[server]}/power"
    resp = requests.post(url, headers=headers, json={"signal": "stop"})
    if resp.status_code == 204:
        await ctx.send(f"⏹️ Stopped **{server}** server.")
    else:
        await ctx.send("❌ Failed to stop.")

# --- Console Commands ---
def send_console_command(server_id, command):
    url = f"{KINETIC_PANEL_URL}/api/client/servers/{server_id}/command"
    payload = {"command": command}
    resp = requests.post(url, json=payload, headers=headers)
    return resp.status_code

@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def announce(ctx, *, message: str):
    status = send_console_command(KINETIC_SERVERS['main'], f"say {message}")
    if status == 204:
        await ctx.send(f"📢 Announcement sent:\n{message}")
    else:
        await ctx.send(f"⚠️ Failed to send announcement. Status code: {status}")

@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def ban(ctx, player: str, *, reason: str = "No reason provided"):
    command = f"ban {player} {reason}"
    status = send_console_command(KINETIC_SERVERS['main'], command)
    if status == 204:
        await ctx.send(f"🔨 Player **{player}** banned. Reason: {reason}")
    else:
        await ctx.send(f"⚠️ Failed to ban player. Status code: {status}")

@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def kick(ctx, player: str, *, reason: str = "No reason provided"):
    command = f"kick {player} {reason}"
    status = send_console_command(KINETIC_SERVERS['main'], command)
    if status == 204:
        await ctx.send(f"👢 Player **{player}** kicked. Reason: {reason}")
    else:
        await ctx.send(f"⚠️ Failed to kick player. Status code: {status}")

@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def pardon(ctx, player: str):
    command = f"pardon {player}"
    status = send_console_command(KINETIC_SERVERS['main'], command)
    if status == 204:
        await ctx.send(f"✅ Player **{player}** unbanned (pardoned).")
    else:
        await ctx.send(f"⚠️ Failed to unban player. Status code: {status}")

# --- Utility commands ---
@bot.command()
async def ip(ctx, server: str = None):
    """Shows the IP address of a specific server or all servers if none is specified."""
    if server:
        server = server.lower()
        if server not in SUBDOMAINS:
            await ctx.send("⚠️ Invalid server! Use: `main`, `na`, `eu`, or `asia`.")
            return

        ip_address = SUBDOMAINS[server]
        display_name = DISPLAY_NAMES.get(server, server.capitalize())
        await ctx.send(f"**{display_name} IP:** `{ip_address}`")
    else:
        lines = []
        for key in ['main', 'proxy1', 'proxy2', 'proxy3']:
            display_name = DISPLAY_NAMES.get(key, key.capitalize())
            domain = SUBDOMAINS.get(key, "Unknown")
            lines.append(f"**{display_name}**: `{domain}`")
        await ctx.send("**Server IPs:**\n" + "\n".join(lines))
@bot.command()
async def players(ctx):
    lines = []
    for key, address in MC_SERVERS.items():
        try:
            server = JavaServer.lookup(address)
            status = server.status()
            display_name = DISPLAY_NAMES.get(key, key.capitalize())
            lines.append(f"**{display_name}**: {status.players.online}/{status.players.max} players")
        except Exception:
            display_name = DISPLAY_NAMES.get(key, key.capitalize())
            lines.append(f"**{display_name}**: Offline or unreachable")
    await ctx.send("\n".join(lines))

# --- Refresh ---
@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def refresh(ctx):
    await update_status()
    await ctx.send("🔁 Status embed refreshed.")

# --- Set Status Channel ---
@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def setchannel(ctx):
    global CHANNEL_ID
    CHANNEL_ID = ctx.channel.id
    await ctx.send(f"✅ Status updates will now post in {ctx.channel.mention}.")

# --- Ping command ---
@bot.command()
async def ping(ctx):
    import time
    start = time.monotonic()
    msg = await ctx.send("Pinging...")
    end = time.monotonic()
    discord_latency = round(bot.latency * 1000)
    response_time = round((end - start) * 1000)

    # Function to ping Minecraft server (TCP)
    import socket
    def tcp_ping(host, port, timeout=1.5):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    # Get ping for each server using mcstatus (best for RTT)
    from mcstatus import JavaServer
    async def get_mc_ping(address):
        try:
            server = JavaServer.lookup(address)
            latency = server.ping()
            return round(latency)
        except:
            return None

    pings = {}
    for key, addr in MC_SERVERS.items():
        latency = await get_mc_ping(addr)
        display_name = DISPLAY_NAMES.get(key, key.capitalize())
        pings[key] = f"{latency}ms" if latency is not None else "Offline"

    embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
    embed.add_field(name="Discord Latency", value=f"{discord_latency}ms", inline=False)
    embed.add_field(name="Main Server Ping", value=pings.get("main", "N/A"), inline=False)
    embed.add_field(name="NA Proxy Ping", value=pings.get("proxy1", "N/A"), inline=False)
    embed.add_field(name="EU Proxy Ping", value=pings.get("proxy2", "N/A"), inline=False)
    embed.add_field(name="Asia Proxy Ping", value=pings.get("proxy3", "N/A"), inline=False)
    embed.set_footer(text="📍 Bot is hosted in Texas. Minecraft ping is relative to that location.")

    await msg.edit(content=None, embed=embed)

# ------ Cmds//Help command ------
@bot.command(name="cmds")
async def cmds(ctx):
    embed = discord.Embed(title="📘 AoD Server Bot Commands", color=0x00bfff)

    # Public Commands
    public_commands = """
**!cmds** - Show this message.
**!ip** - Get connection info for the servers.
**!players** - See player counts on all servers.
**!ping** - Check latency to bot + servers (note: bot hosted in Texas).
    """.strip()

    # Staff Commands
    staff_commands = """
**!maintenance on/off [server|all]** - Toggle maintenance mode.
**!updates on/off** - Enable/disable embed auto-updates.
**!setchannel** - Set current channel as status channel.
**!refresh** - Force refresh the status message.
**!announce [message]** - Send announcement to the Minecraft server console.
**!ban [user] [reason]** - Ban a user from the Minecraft server.
**!kick [user] [reason]** - Kick a user from the Minecraft server.
**!pardon [user]** - Unban a previously banned user from the Minecraft server.
**!restart [server]** - Restart a KineticHost server.
**!start [server]** - Start a KineticHost server.
**!stop [server]** - Stop a KineticHost server.
    """.strip()

    embed.add_field(name="📢 Public Commands", value=public_commands, inline=False)
    embed.add_field(name="🔐 Staff Commands", value=staff_commands, inline=False)
    embed.set_footer(text="Bot by AoD. Powered by KineticHost API + Minecraft Status")

    await ctx.send(embed=embed)

# ---- DO NOT DELETE BELOW ----
bot.run(DISCORD_TOKEN)
