RAT - Rift Assistance Toolbox
===========

A utility bot for Rift which serves requests over the Rift Mobile HTTP interface

Once installed, execute riftChatBot.py with arguments: username password character

This will log into Rift Mobile over HTTPS and begin listening for commands on guild and whisper chat. Any chat string beginning with a "!" character will be interpreted as a chat bot command.

Current functionality includes:
* !alts - Register / manage lists of alternate characters
* !calc - Evaluate arbitrary mathematical expressions
* !items - Retrieve information about in-game items  
	N.B. Items are stored in a database named discoveries.db which is created from Trion's published discoveries database (available at ftp://ftp.trionworlds.com/rift/data/) using the included parseDiscoveries.py
* !roll - Generate random integers
* !timers - Schedule chat alerts

Requirements:
* python 2.7+
	