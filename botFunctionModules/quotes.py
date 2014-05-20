import riftChatBotUtils

__quotes_options_str__ = 'Options: -player=? -submitter=? -score(<,>,=,~)?'

# The functionality for displaying login messages has not yet been implemented
# # !login is basically an alias for !login show
# def bot_login(riftBot, req):
	# if req.argList and req.argList[0] in ['-h', '--help']:
		# func, opts, desc = __botFunctions__["login"]
		# req.response.append(desc)
		# req.response.append('Options: %s' % ",".join(__login_options__))
		# return req
		
	# return bot_login_show(riftBot, req)
	
# # Clear a user's login message
# def bot_login_clear(riftBot, req):
	# return req
	
# # Set a user's login message
# def bot_login_set(riftBot, req):
	# return req
	
# # Print a user's login message
# def bot_login_show(riftBot, req):
	# return req
	
# Output server time
def bot_quote(riftBot, req):
	if not req.argList or req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["quote"]
		req.response.append(desc)
		req.response.append('Usage: !quote player')
		
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Get the player's last message in guild chat
		player = req.argList[0].lower()
		guildMessages = riftBot.guildMessages()
		quoteText = ''
		for message in reversed(guildMessages):
			if message['senderName'].lower() == player and message['message'][0] is not '!':
				quoteText = message['message']
				break
		
		# Error guarding
		if quoteText:
			# Get a new timer ID
			quoteId = cursor.execute("SELECT MAX(quoteId) AS m FROM quotes").fetchone()
			if quoteId and quoteId['m']:
				quoteId = quoteId['m'] + 1
			else:
				quoteId = 1
			
			# Store the new quote
			cursor.execute("INSERT INTO quotes VALUES (?,?,?,?)", (quoteId, player, req.requester, quoteText))
			cursor.execute("INSERT INTO quoteVotes VALUES (?,?,?,?)", (quoteId, req.requester, req.requesterId, 1))
			req.response.append('Quote added:')
			req.response.append('%i | "[%s]: %s"' % (quoteId, player.title(), quoteText))
			DB.commit()
		
		else:
			req.response.append('No messages found for player: %s' % player.title())
		
		DB.close()
		
	return req

# List quotes
def bot_quotes(riftBot, req):
	if not req.argList or req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["quotes"]
		req.response.append(desc)
		req.response.append('Usage: !quotes [options] [[~]text ..]')
		req.response.append(__quotes_options_str__)
		
	else:
		DB = riftBot.dbConnect()
		
		# Get a list of matching quotes and append them to the response list
		quotesList = bot_quotes_query(req, DB).fetchall()
		if quotesList:
			for n, quote in enumerate(quotesList):
				req.response.append('%i | "[%s]: %s" (%i)' % (quote['quoteId'], quote['player'].title(), quote['quote'], quote['score']))
				if n == 2 and len(quotesList) > 4:
					req.response.append('%i entries truncated' % (len(quotesList)-n-1))
					break
				
		else:
			req.response.append('No quotes found')
				
		DB.close()
			
	return req

# Add a quote
def bot_quotes_add(riftBot, req):
	if not req.argList or req.argList[0] in ['-h', '--help']:
		func, opts, desc = __quotes_options__["add"]
		req.response.append(desc)
		req.response.append('Usage: !quotes add player text')
		
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		if len(req.argList) > 1:
			player = req.argList[0].lower()
			quoteText = " ".join(req.argList[1:])
				
			# Get a new timer ID
			quoteId = cursor.execute("SELECT MAX(quoteId) AS m FROM quotes").fetchone()
			if quoteId and quoteId['m']:
				quoteId = quoteId['m'] + 1
			else:
				quoteId = 1
			
			# Store the new quote
			cursor.execute("INSERT INTO quotes VALUES (?,?,?,?)", (quoteId, player, req.requester, quoteText))
			cursor.execute("INSERT INTO quoteVotes VALUES (?,?,?,?)", (quoteId, req.requester, req.requesterId, 1))
			req.response.append('Quote added:')
			req.response.append('%i | "[%s]: %s"' % (quoteId, player.title(), quoteText))
			DB.commit()
		
		else:
			req.response.append('Error: no quote supplied')
		
		DB.commit()
		DB.close()
		
	return req

# Down vote a quote
def bot_quotes_downvote(riftBot, req):
	if not req.argList or req.argList[0] in ['-h', '--help']:
		func, opts, desc = __quote_options__["downvote"]
		req.response.append(desc)
		req.response.append('Usage: !quotes downvote ID [ID ..]')
		
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Iterate over the list of quotes to downvote
		numAffected = 0
		for arg in req.argList:
			# Make sure the quote ID is valid
			ID = None
			try:
				ID = arg
			except ValueError:
				req.response.append('Synatax Error: %s not recognised' % arg)
			
			if ID:
				# Make sure the quote exists and downvote it
				cursor.execute("SELECT 1 FROM quotes WHERE quoteId=?", (ID,))
				if cursor.fetchone():
					cursor.execute("INSERT OR REPLACE INTO quoteVotes VALUES (?,?,?,?)", (ID, req.requester.lower(), req.requesterId, -1))
					numAffected += 1
				
				else:
					req.response.append('No quote exists with ID %i' % ID)
		
		if numAffected:
			if numAffected == 1:
				req.response.append('1 downvote registered')
			else:
				req.response.append('%i downvotes registered' % numAffected)
		
		DB.commit()
		DB.close()
			
	return req

# Remove all of a user's quotes
def bot_quotes_purge(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __quotes_options__["purge"]
		req.response.append(desc)
		req.response.append('Usage: !quotes purge')
		
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Get a list of the player's quotes and remove them all
		quotes = cursor.execute("SELECT * FROM quotes WHERE player=?", (req.requester,)).fetchall()
		for quote in quotes:
			cursor.execute("DELETE FROM quoteVotes WHERE quoteId=?", (quote['quoteId'],))
		cursor.execute("DELETE FROM quotes WHERE player=?", (req.requester,))
		req.response.append('%i quotes purged' % cursor.rowcount)
				
		DB.commit()
		DB.close()
			
	return req

# Search for quotes using extended options
def bot_quotes_query(req, quotesDB):
	cursor = quotesDB.cursor()
	
	quotesQuery = []
	quotesValue = ()
	verbose = False
	for arg in req.argList:
		if arg[0] == '-':
			optStr = arg.strip("-").lower()
			
			# Options based on the quote's score
			if len(optStr) > 6 and optStr[0:5] == 'score':
				try:
					if optStr[5] == '<':
						itemValue += (int(optStr[6:]),)
						itemQuery += ["score<?"]
						
					elif optStr[5] == '>':
						itemValue += (int(optStr[6:]),)
						itemQuery += ["score>?"]
						
					elif optStr[5] == '=':
						itemValue += (int(optStr[6:]),)
						itemQuery += ["score=?"]
						
					elif optStr[5] == '~':
						itemValue += (int(optStr[6:]),)
						itemQuery += ["score<>?"]
					
					else:
						req.response.append('Unrecognised score argument')
						
				except ValueError:
					req.response.append('Error: Score given non-integer argument')
			
			# Options based on origin
			if '=' in optStr:
				opt, val = optStr.split("=")
				if opt in ['p', 'player']:
					quotesQuery += ["player=?"]
					quotesValue += (val,)
					
				if opt in ['s', 'submitter']:
					quotesQuery += ["submitter=?"]
					quotesValue += (val,)
				
			else:
				req.response.append('Unrecognised option: %s' % arg)
				
		else:
		
			# Pure string matching options
			if arg[0] == '~':
				quotesQuery += ["quote NOT LIKE ?"]
				quotesValue += ("%%%s%%" % arg[1:],)
				
			else:
				quotesQuery += ["quote LIKE ?"]
				quotesValue += ("%%%s%%" % arg,)
		
	# Output
	if quotesQuery:
		quotesQuery = "SELECT quotes.quoteId as quoteId, quotes.player AS player, quotes.quote AS quote, SUM(rating) AS score FROM quotes JOIN quoteVotes USING (quoteId) WHERE %s GROUP BY quoteId ORDER BY score DESC LIMIT 100" % " AND ".join(quotesQuery)
	else:
		quotesQuery = "SELECT quotes.quoteId as quoteId, quotes.player AS player, quotes.quote AS quote, SUM(rating) AS score FROM quotes JOIN quoteVotes USING (quoteId) GROUP BY quoteId ORDER BY score DESC LIMIT 100"
	
	return cursor.execute(quotesQuery, quotesValue)

# Remove a user's quote
def bot_quotes_remove(riftBot, req):
	if not req.argList or req.argList[0] in ['-h', '--help']:
		func, opts, desc = __quotes_options__["remove"]
		req.response.append(desc)
		req.response.append('Usage: !quotes remove ID [ID ..]')
		
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Iterate over all of the quotes the user has input
		numAffected = 0
		for arg in req.argList:
			# Check that the ID is valid
			ID = None
			try:
				ID = arg
			except ValueError:
				req.response.append('Synatax Error: %s not recognised' % arg)
			
			# Check that the quote exists and if it does remove it
			if ID:
				quote = cursor.execute("SELECT * FROM quotes WHERE quoteId=?", (ID)).fetchone()
				if quote:
					if quote['player'] == req.requester or quote['submitter'] == req.requester:
						cursor.execute("DELETE FROM quoteVotes WHERE quoteId=?", (ID,))
						cursor.execute("DELETE FROM quotes WHERE quoteId=?", (ID,))
						numAffected += cursor.rowcount
						
					else:
						req.response.append('You do not own quote with ID %i' % ID)
				
				else:
					req.response.append('No quote exists with ID %i' % ID)
		
		if numAffected:
			if numAffected == 1:
				req.response.append('1 downvote registered')
			else:
				req.response.append('%i downvotes registered' % numAffected)
		
		DB.commit()
		DB.close()
			
	return req
	
# Up vote a quote
def bot_quotes_upvote(riftBot, req):
	if not req.argList or req.argList[0] in ['-h', '--help']:
		func, opts, desc = __quotes_options__["upvote"]
		req.response.append(desc)
		req.response.append('Usage: !quotes upvote ID [ID ..]')
		
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
	
		# Iterate over the list of quotes to downvote
		numAffected = 0
		for arg in req.argList:
			# Make sure the quote ID is valid
			ID = None
			try:
				ID = arg
			except ValueError:
				req.response.append('Synatax Error: %s not recognised' % arg)
			
			if ID:
				# Make sure the quote exists and upvote it
				cursor.execute("SELECT 1 FROM quotes WHERE quoteId=?", (ID,))
				if cursor.fetchone():
					cursor.execute("INSERT OR REPLACE INTO quoteVotes VALUES (?,?,?,?)", (ID, req.requester.lower(), req.requesterId, 1))
					numAffected += 1
				
				else:
					req.response.append('No quote exists with ID %i' % ID)
		
		if numAffected:
			if numAffected == 1:
				req.response.append('1 upvote registered')
			else:
				req.response.append('%i upvotes registered' % numAffected)
		
		DB.commit()
		DB.close()
			
	return req

# Run on bot startup
def __bot_init__(riftBot):
	DB = riftBot.dbConnect()
	cursor = DB.cursor()
	
	cursor.execute("CREATE TABLE IF NOT EXISTS quotes (quoteId INT PRIMARY KEY, player VARCHAR(30), submitter VARCHAR(30), quote VARCHAR(255))")
	cursor.execute("CREATE TABLE IF NOT EXISTS quoteVotes (quoteId INT, player VARCHAR(30), playerId VARCHAR(30), rating INT, CONSTRAINT pk_voteID PRIMARY KEY (quoteId, player))")
	
	DB.commit()
	DB.close()

# __login_options__ = {
	# 'clear'	: (bot_login_clear, [], "Clear your login message"),
	# 'set'	: (bot_login_set, [], "Set your login message"),
	# 'print'	: (bot_login_show, [], "Print your login message")
	# }
	
# A list of options for the timers function
__quotes_options__ = {
	'add'		: (bot_quotes_add, [], "Add a new quote"),
	'downvote'	: (bot_quotes_downvote, [], "Downvote a quote by ID"),
	'purge'		: (bot_quotes_purge, [], "Remove all of your quotes"),
	'remove'	: (bot_quotes_remove, [], "Remove a quote by ID"),
	'upvote'	: (bot_quotes_upvote, [], "Upvote a quote by ID")
	}

# A list of functions contained in this module, format: (function, options, description)
__botFunctions__ = {
	# 'login'	: (bot_login, __login_options__, "Set a login message"),
	'quote'	: (bot_quote, [], "Quote a player's  last message"),
	'quotes': (bot_quotes, __quotes_options__, "Store / manage quotes")
	}
	