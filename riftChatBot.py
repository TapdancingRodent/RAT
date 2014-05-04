#!/c/python27/python.exe
import sys, pkgutil, shlex, os
import riftChatBotUtils, botFunctionModules

# Look up a function (including sub-options)
def get_function(argList):
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
	argList = req.argList
	req.toGuild = req.fromGuild
	req.toWhisp = req.fromWhisp
	
	if argList:
		func, opt, desc, remArgs = get_function(argList)
		
		if func:
			req.argList = ['--help']
			req.argStr = '--help'
			req = func(riftBot, req)
			
		else:
			req.response += ['No help found for ' + argList[0]]
			
	else:
		req.response += ['Available functions: ' + ', '.join([bF for bF in sorted(__botFunctions__)]), 'Usage: !help [function]']
	
	return req
	
# A list of available functions - this will be fully populated during submodule importing
__botFunctions__ = {
	'help'	: (bot_help, [], "Get help information")
	}

if __name__ == "__main__":
	# Some basic validation
	if len(sys.argv) != 4:
		sys.exit('Please supply a username, password and character name')
		
	# import all the bot functions found in the botFunctionModules folder
	for importer, moduleName, _ in pkgutil.walk_packages(['botFunctionModules']):
		module = importer.find_module(moduleName).load_module(moduleName)
		exec('%s = module' % moduleName)
		
		for func in module.__botFunctions__:
			__botFunctions__[func] = module.__botFunctions__[func]
	
	# Collect data from stdin
	username = sys.argv[1]
	password = sys.argv[2]
	charName = sys.argv[3].lower()

	# Initialise a chat bot
	bot = riftChatBotUtils.riftChatBot()
	bot.login(username, password, charName)
	
	# Initialise the database
	DB = bot.dbConnect()
	cursor = DB.cursor()
	cursor.execute("CREATE TABLE IF NOT EXISTS alts (player VARCHAR(30) PRIMARY KEY, altGroup INT)")
	cursor.execute("CREATE TABLE IF NOT EXISTS altConfirmations (player VARCHAR(30), altGroup INT, playerConfirmed INT, groupConfirmed INT, CONSTRAINT pk_confID PRIMARY KEY (player, altGroup))")
	cursor.execute("CREATE TABLE IF NOT EXISTS timers (timerId INT PRIMARY KEY, player VARCHAR(30), playerId VARCHAR(30), sendGuild INT, message VARCHAR(255))")
	cursor.execute("CREATE TABLE IF NOT EXISTS quotes (quoteId INT PRIMARY KEY, playerId VARCHAR(30), quote VARCHAR(255), score INT)")
	cursor.execute("CREATE TABLE IF NOT EXISTS quoteVotes (quoteId INT, player VARCHAR(30), rating INT, CONSTRAINT pk_voteID PRIMARY KEY (quoteId, player))")
	DB.commit()
	DB.close()
	
	# Begin listening to chat
	print 'Listening for chat messages...'
	while True:
		req = bot.getRequest()
		if req:
			numRetries = 0
			print 'Recieved message: ' + req.message
			
			# Parse the request
			lex = shlex.shlex(req.message)
			lex.quotes = '"'
			lex.whitespace_split = True
			lex.commentors = ''
			lex.escapedquotes = ''
			argList = list(lex)
			argList = [arg.strip('"') for arg in argList]
			
			# If "!" was the query string, instead give help
			if not argList:
				argList = ['help']
			
			# Get the correct subfunction
			func, opt, desc, req.argList = get_function(argList)
			req.argStr = ' '.join(req.argList)
			if func:
				# Run the function
				req = func(bot, req)
			else:
				req.response += ['Function ' + req.argList[0] + ' not recognised']
			
			# Debug messages
			print 'Responding:'
			for message in req.response:
				print '\t' + message
				
			# Send response to chat
			bot.sendResponse(req)
