import riftChatBotUtils

# !alts is basically an alias for !alts list
def bot_admins(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["admins"]
		req.response += [desc]
		req.response += ['Options: %s' % ",".join(__admins_options__)]
		return req
		
	return bot_admins_list(riftBot, req)
	
# Add an admin
def bot_admins_add(riftBot, req):
	if not req.argList:
		req.response += ['Usage: !admins add character']
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __admins_options__["add"]
		req.response += [desc]
		req.response += ['Usage: !admins add character']
				
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			for arg in req.argList:
				# Add the admin, send a confirmation message
				if cursor.execute("SELECT 1 FROM admins WHERE player=?", (arg.lower(),)).fetchone():
					req.response += ['%s is already an admin' % arg.title()]
					
				else:
					cursor.execute("INSERT INTO admins (player) VALUES (?)", (arg.lower(),))
					req.response += ['%s added (requires registration)' % arg.title()]
				
			DB.commit()
			
		else:
			req.response += ['Managing admins must be done as a super user']
		
		DB.close()
			
	return req

# List admins
def bot_admins_list(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __admins_options__["list"]
		req.response += [desc]
		req.response += ['Usage: !admins list']
	
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		admins = cursor.execute("SELECT player FROM admins").fetchall()
		req.response += ['Admins: %s' % ", ".join([admin['player'].title() for admin in admins])]
		
		DB.close()
		
	return req

# Register an admin's user ID
def bot_admins_register(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __admins_options__["register"]
		req.response += [desc]
		req.response += ['Usage: !admins register']
	
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Check if the player is an admin
		admin = cursor.execute("SELECT * FROM admins WHERE player=?", (req.requester,)).fetchone()
		if admin:
			# Check that they haven't already registered
			if admin['playerId']:
				req.response += ['Error: %s is already registered' % req.requester.title()]
				
			else:
				# Register their playerId
				cursor.execute("UPDATE admins SET playerId=? WHERE player=?", (req.requesterId, req.requester))
				req.response += ["%s's player ID has been registered" % req.requester.title()]
				
			DB.commit()
		
		else:
			req.response += ['%s is not an admin' % req.requester.title()]
		
		DB.close()
		
	return req

# Remove an admin
def bot_admins_remove(riftBot, req):
	if not req.argList:
		req.response += ['Usage: !admins rem character']
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __admins_options__["rem"]
		req.response += [desc]
		req.response += ['Usage: !admins rem character']
	
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			for arg in req.argList:
				# Remove the admin, send a confirmation message
				if cursor.execute("SELECT 1 FROM admins WHERE player=?", (arg.lower(),)).fetchone():
					cursor.execute("DELETE FROM admins WHERE player=?", (arg.lower(),))
					req.response += ['%s removed' % arg.title()]
					
				else:
					req.response += ['%s is not an admin' % arg.title()]
				
			DB.commit()
			
		else:
			req.response += ['Managing admins must be done as a super user']
		
		DB.close()
		
	return req

# Execute a function as an admin
def bot_su(riftBot, req):
	if not req.argList:
		req.response += ['Usage: !su [-user=player] function ..']
	
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["su"]
		req.response += [desc]
		req.response += ['Usage: !su [-user=player] function ..']
		
	else:
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Look up the player in the admins database
		cursor.execute("SELECT 1 FROM admins WHERE player=? AND playerId=?", (req.requester, req.requesterId))
		if cursor.fetchone():
			if len(req.argList[0]) > 7 and req.argList[0][0:6] == "-user=":
				req.requester = req.argList[0][6:].lower()
				req.argList = req.argList[1:]
				
			req.su = True
				
			# Get a new subfunction
			func, opt, desc, req.argList = req.resolve_function(req.argList)
			if func:
				# Run the function
				req = func(riftBot, req)
				
			else:
				req.response += ['Function ' + req.argList[0] + ' not recognised']
				
		elif cursor.execute("SELECT 1 FROM admins WHERE player=?", (req.requester,)).fetchone():
			# The user is not yet fully authorised to run functions
			
			if cursor.execute("SELECT 1 FROM admins WHERE player=?", (req.requester,)).fetchone():
				# At this point it seems most likely that someone is trying to run su inside su
				# So lets make a toothless threat that there is any kind of oversight (hilarious)
				req.response += ['Player ID information resolved inconsistently, this request has been logged' % req.requester.title()]
				
			else:
				req.response += ['%s has not registered']
				
		else:
			req.response += ['%s is not an admin' % req.requester.title()]
			
		DB.close()
		
	return req

# Run on bot startup
def __bot_init__(riftBot):
	pass

# A list of options for the alts function
__admins_options__ = {
	'add'		: (bot_admins_add, [], "Make a player an admin"),
	'list'		: (bot_admins_list, [], "List admins"),
	'register'	: (bot_admins_register, [], "Register your user ID"),
	'remove'	: (bot_admins_remove, [], "Remove an admin")
	}
	
# A list of functions contained in this module, format: (function, options, description)
__botFunctions__ = {
	'su'  : (bot_su, [], "Do things as a super user"),
	'admins'	: (bot_admins, __admins_options__, "Manage admins")
	}
