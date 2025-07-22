# MCServerStatusDiscordBot

Minecraft Server Status Discord Bot

This Discord bot provides real-time status updates for your Minecraft servers, with built-in integration for KineticHost API and direct Minecraft server pings.

Features:

Displays Minecraft server online status and player counts for main and proxy servers.

Fetches resource usage (RAM, status) via KineticHost API for the main server. *Although kinetic does not support ram atm, so I have set it to ?/16gb since my server has a max of 16gb*

Supports toggling maintenance mode per server or all servers.

Commands to enable/disable automatic status updates.

Configurable for different server hosts — users can replace or extend the API integration to support their own hosting provider.

Sends status updates as embeds in a designated Discord channel.

Role-based permissions for management commands.

Setup:

Replace placeholders with your Discord bot token, API key(s), server IDs, Minecraft addresses, and Discord channel/role IDs.

If you use a different hosting provider, update or replace the get_kinetic_status function to fit your API or resource-fetching method.

Run the bot to keep your community informed about server health and maintenance.

Usage:

!maintenance on|off <NA|EU|ASIA|MAIN|ALL> — Toggle maintenance mode.

!updates on|off — Enable or disable automatic updates.

!status — Show current server status.

Required Python Packages:
discord.py mcstatus requests

