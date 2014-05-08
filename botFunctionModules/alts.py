import riftChatBotUtils

# !alts is basically an alias for !alts list
def bot_alts(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["alts"]
		req.response += [desc]
		req.response += ['Options: %s' % ",".join(__alts_options__)]
		return req
		
	return bot_alts_list(riftBot, req)
	
# Add an alt / alts
def bot_alts_add(riftBot, req):
	if not req.argList:
		req.response += ['Usage: !alts add character [character ..]']
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __alts_options__["add"]
		req.response += [desc]
		req.response += ['Usage: !alts add character [character ..]']
				
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Look up alts in the alts database
		groups = []
		for alt in req.argList:
			g = cursor.execute("SELECT altGroup FROM alts WHERE player=?", (alt.lower(),)).fetchone()
			if g:
				groups += [g['altGroup']]
		
		# If the alts are already in a group
		if groups:
			if all(group == groups[0] for group in groups[1:]):
				group = groups[0]
				confirmation = cursor.execute("SELECT groupConfirmed FROM altConfirmations WHERE player=? AND altGroup=?", (req.requester, group)).fetchone()
				
				# If a confirmation is pending for the player, add them to the alt group
				if confirmation and confirmation['groupConfirmed'] == 1:
					cursor.execute("DELETE FROM altConfirmations WHERE player=?", (req.requester,))
					cursor.execute("INSERT OR REPLACE INTO alts VALUES (?,?)", (req.requester, group))
					DB.commit()
					req.response += ['%s confirmed' % req.requester.title()]
				
				# If no confirmation is pending register a request to join the group
				else:
					cursor.execute("INSERT OR REPLACE INTO altConfirmations VALUES (?,?,1,0)", (req.requester, group))
					DB.commit()
					req.response += ['%s added to group %i (requires confirmation)' % (req.requester.title(), group)]
				
			else:
				# Groups are inconsistent
				req.response += ['Database Error: listed alts exist in multiple groups']
			
		else:
			# Look up the player in the alts database
			group = cursor.execute("SELECT altGroup FROM alts WHERE player=?", (req.requester,)).fetchone()
			
			# If the player is already in a group
			if group:
				group = group['altGroup']
				for alt in req.argList:
					# If the alt has already requested to join this group add them to the alt group
					confirmation = cursor.execute("SELECT playerConfirmed FROM altConfirmations WHERE player=? AND altGroup=?", (alt, group)).fetchone()
					if confirmation and confirmation['playerConfirmed']:
						cursor.execute("DELETE FROM altConfirmations WHERE player=?", (alt,))
						cursor.execute("INSERT OR REPLACE INTO alts VALUES (?,?)", (alt, group))
						req.response += ['%s confirmed' % alt.title()]
					
					# Otherwise register the group invite
					else:
						cursor.execute("INSERT OR REPLACE INTO altConfirmations VALUES (?,?,0,1)", (alt.lower(), group))
						req.response += ['%s added to group %i (confirmation required)' % (alt.title(), group)]
				
				DB.commit()
				
			else:
				# Everyone is ungrouped so start a new group and register the request
				if cursor.execute("SELECT COUNT(*) AS n FROM alts").fetchone()['n'] == 0:
					group = 1
				else:
					group = cursor.execute("SELECT MAX(altGroup) AS m FROM alts").fetchone()['m'] + 1
					
				cursor.execute("INSERT INTO alts VALUES(?,?)", (req.requester, group))
				for alt in req.argList:
					cursor.execute("INSERT OR REPLACE INTO altConfirmations VALUES (?,?,0,1)", (alt.lower(), group))
					req.response += ['%s added to group %i (requires confirmation)' % (alt.title(), group)]
					
				DB.commit()
				
		DB.close()
			
	return req

# List a player's alts
def bot_alts_list(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __alts_options__["list"]
		req.response += [desc]
		req.response += ['Usage: !alts list [character]']
	
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Default is to list the user's alts
		if req.argList:
			main = req.argList[0].lower()
		else:
			main = req.requester
		
		# Look up the player's alt group
		altGroup = cursor.execute("SELECT altGroup FROM alts WHERE player=?", (main,)).fetchone()
		
		# If any registered alts are found add them to the response list
		if altGroup:
			altGroup = altGroup['altGroup']
			altList = cursor.execute("SELECT player FROM alts WHERE altGroup=? AND player<>?", (altGroup, main)).fetchall()
			if altList:
				req.response += ['%s has alts: %s' % (main.title(), ", ".join([alt['player'].title() for alt in altList]))]
				
			else:
				req.response += ['%s has no alts' % main.title()]
		
		else:
			req.response += ['%s not listed in alts database' % main.title()]
		
		DB.close()
		
	return req

# De-register an alt
def bot_alts_remove(riftBot, req):
	if not req.argList:
		req.response += ['Usage: !alts rem character [character ..]']
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __alts_options__["rem"]
		req.response += [desc]
		req.response += ['Usage: !alts rem character [character ..]']
	
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Look up the user's alt group
		altGroup = cursor.execute("SELECT altGroup FROM alts WHERE player=?", (req.requester,)).fetchone()
		if altGroup:
			altGroup = altGroup['altGroup']
			for alt in argList:
				# Check that the alt is in the user's group
				for alt in req.argList:
					isAlt = cursor.execute("SELECT * FROM alts WHERE player=? AND altGroup=?", (alt.lower(), altGroup)).fetchone()
					if isAlt or req.su:
						# Purge the alt from the database
						cursor.execute("DELETE FROM alts WHERE player=? AND altGroup=?", (alt.lower(), altGroup))
						req.response += ['%s removed from alts database' % alt]
						
					else:
						# Try to purge the alt from the confirmations database
						cursor.execute("DELETE FROM altConfirmations WHERE player=? AND altGroup=?", (alt.lower(), altGroup))
						if cursor.rowcount > 0:
							req.response += ["%s's join request has been removed" % alt.title()]
							
						else:
							req.response += ['No entry found for %s and %s' % (req.requester.title(), alt)]
				
				DB.commit()
				
		else:
			req.response += ['%s is not in the alts database' % main.title()]
			
		DB.close()
		
	return req

# Query if player is online
def bot_is(riftBot, req):
	if not req.argList:
		req.response += ['Usage: !is character [character ...]']
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["is"]
		req.response += [desc]
		req.response += ['Usage: !is character [character ...]']
		
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()

		# Get guild members list
		guildList = riftBot.listFriendsAndGuild()
		
		# Get a list of lists of alts
		# A little ugly but prevents multiple passes over the (potentially extensive) guild roster
		players = req.argList
		alts = []
		for player in players:
			altGroup = cursor.execute("SELECT altGroup FROM alts WHERE player=?", (player.lower(),)).fetchone()
			if altGroup:
				altGroup = altGroup['altGroup']
				altsList = cursor.execute("SELECT player FROM alts WHERE altGroup=? AND player<>?", (altGroup, player.lower())).fetchall()
				alts += [[alt['player'] for alt in altsList]]
				
			else:
				alts += [[]]
		
		# Note if anyone is actually online
		playerStatus = [0 for player in players]
		altStatus = [[0 for alt in alts[p]] for p, _ in enumerate(players)]
		for member in guildList:
			for p, player in enumerate(players):
				if member['name'].lower() == player.lower():
					if member['onlineGame']:
						playerStatus[p] = 2
					
					elif member['onlineWeb']:
						playerStatus[p] = 1
						
				for a, alt in enumerate(alts[p]):
					if member['name'].lower() == alt:
						if member['onlineGame']:
							altStatus[p][a] = 2
						
						elif member['onlineWeb']:
							altStatus[p][a] = 1
		
		# Make sense of harvested information
		for p, pS in enumerate(playerStatus):
			altsOnline = [(alts[p][a] if aS == 2 else None) for a, aS in enumerate(altStatus[p])]
			altsMobile = [(alts[p][a] if aS == 1 else None) for a, aS in enumerate(altStatus[p])]
			
			# Ordered by usefulness
			if pS == 2:
				req.response += ['%s is online' % players[p].title()]
				
			elif altsOnline and altsOnline[0]:
				req.response += ['%s is online as %s' % (players[p].title(), altsOnline[0].title())]
			
			elif pS == 1:
				req.response += ['%s is on mobile' % players[p].title()]
				
			elif altsMobile and altsMobile[0]:
				req.response += ['%s is on mobile as %s' % (players[p].title(), altsOnline[0].title())]
				
			else:
				req.response += ['%s is not online' % players[p].title()]
		
		DB.close()
		
	return req

# Run on bot startup
def __bot_init__(riftBot):
	pass
	
# A list of options for the alts function
__alts_options__ = {
	'add'	: (bot_alts_add, [], "Add a player to a group of alts"),
	'list'	: (bot_alts_list, [], "List a player's alts"),
	'remove': (bot_alts_remove, [], "Remove a player from a group of alts")
	}
	
# A list of functions contained in this module, format: (function, options, description)
__botFunctions__ = {
	'alts'	: (bot_alts, __alts_options__, "Set / get information about alts"),
	'is'	: (bot_is, [], "Check if player is online")
	}
