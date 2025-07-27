# MC Server Status Discord Bot
MC Server Status Discord Bot is a Discord bot built to monitor and manage Minecraft servers hosted on KineticHost. (Although, if you put the code through ChatGPT or something, you can change it to a diff host) It provides real-time server status updates, maintenance controls, and essential administrative commands — all accessible directly within your Discord server.

Features
Real-Time Server Status
Continuously updates an embed with player counts, server uptime, RAM usage (Only if your hosts API supports it), and maintenance status for your main Minecraft server and proxies.

Maintenance Mode Management
Enable or disable maintenance mode for individual servers or all servers simultaneously using commands like !maintenance on all.

Update Control
Toggle automatic embed updates on or off with !updates on/off.

Server Power Controls
Restart, start, or stop your servers remotely through Discord commands (!restart, !start, !stop).

Console Command Integration
Send commands such as !announce, !ban, !kick, and !pardon directly to your Minecraft server console.

Public Utility Commands
Accessible by everyone in the Discord server:

!ip — Display server IPs

!players — Show current online player counts

!ping — Check Discord bot latency and Minecraft server pings (note: bot hosted in Texas, ping reflects that)

Staff-Only Controls
Includes !setchannel to set the status message channel and !refresh to manually refresh status embeds.

Configuration
Replace placeholders for your Discord bot token, KineticHost API key, server IDs, role IDs, and channel IDs.

Fully customizable for any Minecraft network setup with proxies. (Or multiple servers, can also just do 1 server with some editing)


