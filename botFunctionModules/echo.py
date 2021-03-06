import riftChatBotUtils

# Returns the user's input string
def bot_echo(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !echo text')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["echo"]
		req.response.append(desc)
		req.response.append('Usage: !echo text')
	
	else:
		req.response.append(" ".join(req.argList))
		
	return req

# Says the user's input string in guild chat
def bot_say(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !say text')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["say"]
		req.response.append(desc)
		req.response.append('Usage: !say text')
	
	else:
		req.toGuild = True
		req.toWhisp = req.fromWhisp
		req.response.append(" ".join(req.argList))
		
	return req

# Run on bot startup
def __bot_init__(riftBot):
	pass

# A list of functions contained in this module, format: (function, options, description)
__botFunctions__ = {
	'echo'	: (bot_echo, [], "Return input phrase"),
	'say'	: (bot_say, [], "Say things in guild chat")
	}
