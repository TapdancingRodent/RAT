import sys, pkgutil, shlex, os
import riftChatBotUtils, botFunctionModules

# Look up a function (including sub-options)
def resolve_function(argList):
	if argList and argList[0] in __botFunctions__:
		func, opt, desc = __botFunctions__[argList[0]]
		n = 1

		while argList[n:] and argList[n] in opt:
			func, opt, desc = opt[argList[n]]
			n += 1
		
	else:
		func=opt=desc = None
		n = 0
		
	return (func, opt, desc, argList[n:])

# Help function - mostly just an alias for the --help option
def bot_help(riftBot, req):
	req.toGuild = req.fromGuild
	req.toWhisp = req.fromWhisp
	
	if req.argList:
		func, opt, desc, remArgs = resolve_function(req.argList)
		
		if func:
			req.argList = ['--help']
			req = func(riftBot, req)
			
		else:
			req.response += ['No help found for ' + req.argList[0]]
			
	else:
		req.response += ['Available functions: ' + ', '.join([bF for bF in sorted(__botFunctions__)]), 'Usage: !help [function]']
	
	return req
	
# A list of available functions - this will be fully populated during submodule importing
__botFunctions__ = {
	'help'	: (bot_help, [], "Get help information")
	}

if __name__ == "__main__":
	# Some basic validation
	if len(sys.argv) < 4:
		sys.exit('Please supply a username, password and character name')
	
	# Collect data from stdin
	username = sys.argv[1]
	password = sys.argv[2]
	charName = sys.argv[3].lower()

	# Initialise a chat bot
	if len(sys.argv) == 5:
		locale = sys.argv[4]
		bot = riftChatBotUtils.riftChatBot(locale)
	else:
		bot = riftChatBotUtils.riftChatBot()
	if bot.login(username, password, charName):
		sys.exit('Unexpected login error, aborting...')
	
	# Initialise the database
	print 'Initialising databases...'
	DB = bot.dbConnect()
	cursor = DB.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS alts (player VARCHAR(30) PRIMARY KEY, altGroup INT)")
	cursor.execute("CREATE TABLE IF NOT EXISTS altConfirmations (player VARCHAR(30), altGroup INT, playerConfirmed INT, groupConfirmed INT, CONSTRAINT pk_confID PRIMARY KEY (player, altGroup))")
	cursor.execute("CREATE TABLE IF NOT EXISTS timers (timerId INT PRIMARY KEY, player VARCHAR(30), playerId VARCHAR(30), sendGuild INT, message VARCHAR(255), timeStamp VARCHAR(30))")
	cursor.execute("CREATE TABLE IF NOT EXISTS quotes (quoteId INT PRIMARY KEY, player VARCHAR(30), playerId VARCHAR(30), quote VARCHAR(255), score INT)")
	cursor.execute("CREATE TABLE IF NOT EXISTS quoteVotes (quoteId INT, player VARCHAR(30), rating INT, CONSTRAINT pk_voteID PRIMARY KEY (quoteId, player))")
	cursor.execute("CREATE TABLE IF NOT EXISTS admins (player VARCHAR(30) PRIMARY KEY, playerId VARCHAR(30))")
	
	# Backwards compatibility patch-esque-ness
	cols = [col[1] for col in cursor.execute("PRAGMA table_info(timers)").fetchall()]
	if not 'timeStamp' in cols:
		cursor.execute("ALTER TABLE timers ADD COLUMN timeStamp VARCHAR(30) DEFAULT '01/01/00'")

	DB.commit()
	DB.close()
		
	# import all the bot functions found in the botFunctionModules folder
	for importer, moduleName, _ in pkgutil.walk_packages(['botFunctionModules']):
		module = importer.find_module(moduleName).load_module(moduleName)
		exec('%s = module' % moduleName)
		
		for func in module.__botFunctions__:
			__botFunctions__[func] = module.__botFunctions__[func]
			
		if module.__bot_init__:
			module.__bot_init__(bot)
	
	# Begin listening to chat
	print 'Listening for chat messages...'
	while True:
		req = bot.getRequest()
		if req:
			numRetries = 0
			req.resolve_function = resolve_function
			print 'Received message: ' + req.message
			
			# Parse the request
			lex = shlex.shlex(req.message)
			lex.quotes = '"'
			lex.whitespace_split = True
			lex.commentors = ''
			lex.escapedquotes = ''
			req.argList = list(lex)
			req.argList = [arg.strip('"') for arg in req.argList]
			
			# If "!" was the query string, instead give help
			if not req.argList:
				req.argList = ['help']
			
			# Get the correct subfunction
			func, opt, desc, req.argList = req.resolve_function(req.argList)
			if func:
				# Run the function
				req = func(bot, req)
				
			else:
				req.toGuild = req.fromGuild
				req.toWhisp = req.fromWhisp
				req.response += ['Function ' + req.argList[0] + ' not recognised']
			
			# Debug messages
			print 'Responding:'
			for message in req.response:
				print '\t' + message
				
			# Send response to chat
			bot.sendResponse(req)
