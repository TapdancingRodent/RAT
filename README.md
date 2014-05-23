RAT - Rift Assistance Toolbox
===========

A utility bot for Rift which serves requests over the Rift Mobile HTTP interface

Once installed, execute riftChatBot.py with arguments: username password character

This will log into Rift Mobile over HTTPS and begin listening for commands on guild and whisper chat. Any chat string beginning with a "!" character will be interpreted as a chat bot command.

Some examples of current functionality:  
- !alts add Sardines           - Registers Sardines as your alt
- !is Sardines                 - Checks if Sardines is online or on a known alt
- !recipe Chrysoprase Treasure - Get ingredients for Luminous Chrysoprase Treasure
- !timers add 3m30s CQ ending  - Schedules a chat alert
- !calc 181*(3/4)+150/4        - Performs a mathematical calculation
- !help                        - Access help information
- !items -class=mage Twyl      - Lists mage usable items with Twyl in the name
    * N.B. Items are stored in a database named discoveries.db which is created from Trion's published discoveries database (available at ftp://ftp.trionworlds.com/rift/data/) using the included parseDiscoveries.py

With version 1.1, RAT is equipped to handle DKP tables. To get started, you'll need to register at least one player as an admin using the script addAdmin.py to allow use of the "!su" (superuser) command:  
    ./addAdmin *bot_name*.db player

Managing tables is performed using the "!dkp tables" subfunctions, support exists for the following dkp systems:
- suicide
- zerosum
- plain

For instance:  
    !su dkp tables add suicide 10man "Loot table for 10 man instances"

Managing raiders within tables and changing of players' dkp is done using the "!dkp raiders" and "!dkp modify" subfunctions.

Requirements:
* python 2.7+
	