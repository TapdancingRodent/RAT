RAT - Rift Assistance Toolbox
===========

A utility bot for Rift which serves requests over the Rift Mobile HTTP interface

Once installed, execute riftChatBot.py with arguments: username password character

This will log into Rift Mobile over HTTPS and begin listening for commands on guild and whisper chat. Any chat string beginning with a "!" character will be interpreted as a chat bot command.

Some examples of current functionality:  
!alts add Sardines           - Registers Sardines as your alt 
!is Sardines                 - Checks if Sardines is online or on a known alt 
!recipe Chrysoprase Treasure - Get ingredients for Luminous Chrysoprase Treasure 
!timers add 3m30s CQ ending  - Schedules a chat alert 
!calc 181*(3/4)+150/4        - Performs a mathematical calculation 
!help                        - Access help information 
!items -class=mage Twyl      - Lists mage usable items with Twyl in the name 
	N.B. Items are stored in a database named discoveries.db which is created from Trion's published discoveries database (available at ftp://ftp.trionworlds.com/rift/data/) using the included parseDiscoveries.py  

Requirements:
* python 2.7+
	