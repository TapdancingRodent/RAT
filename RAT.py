import sys, pkgutil, os, datetime
import riftChatBotUtils, botFunctionModules

# A split function which preserves quotes substring
msg = "some text and <a href='something else'>tag</a> as well"
def intelliSplit(msg):
	n = 0
	args = []
	quoteStack = []
	while n < len(msg):
		if msg[n] == '\\':
			n += 1
		elif msg[n] == '"':
			if quoteStack and quoteStack[-1] == '"':
				quoteStack.pop()
			else:
				quoteStack.append('"')
		elif msg[n] == "'":
			if quoteStack and quoteStack[-1] == "'":
				quoteStack.pop()
			else:
				quoteStack.append("'")
		elif msg[n] == "<":
			nextSpace = msg[n+1:].find(" ")
			if nextSpace and not any([c in ['"', "'"] for c in msg[n+1:n+1+nextSpace]]):
				tag = msg[n+1:n+1+nextSpace]
				endXML = msg[n+1:].find("</%s>" % tag)
				if endXML > 0:
					n += endXML
		elif not quoteStack and msg[n] == " ":
			args.append(msg[0:n])
			msg = msg[n+1:]
			n = -1
		n += 1
	if msg:
		args.append(msg)
	return args

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
			print '[%s] Received message: %s' % (datetime.datetime.utcnow().strftime('%c'), req.message)
			
			# Parse the request
			req.argList = [arg.replace('"', '').replace("'", "") for arg in intelliSplit(req.message)]
			
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
