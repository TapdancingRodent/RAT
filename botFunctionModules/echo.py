import riftChatBotUtils

# Returns the user's input string
def bot_echo(riftBot, req):
	req.toGuild = req.fromGuild
	req.toWhisp = req.fromWhisp
	
	if not req.argList:
		req.response += ['Usage: !echo text']
		
	elif req.argList[0] in ['-h', '--help', 'help']:
		func, opts, desc = __botFunctions__["echo"]
		req.response += [desc]
		req.response += ['Usage: !echo text']
	
	else:
		req.response += [" ".join(req.argList)]
		
	return req

# Says the user's input string in guild chat
def bot_say(riftBot, req):
	req.toGuild = req.fromGuild
	req.toWhisp = req.fromWhisp
	
	if not req.argList:
		req.response += ['Usage: !say text']
		
	elif req.argList[0] in ['-h', '--help', 'help']:
		func, opts, desc = __botFunctions__["say"]
		req.response += [desc]
		req.response += ['Usage: !say text']
	
	else:
		req.toGuild = True
		req.toWhisp = req.fromWhisp
		req.response += [" ".join(req.argList)]
		
	return req

# A list of functions contained in this module, format: (function, options, description)
__botFunctions__ = {
	'echo'	: (bot_echo, [], "Return input phrase"),
	'say'	: (bot_say, [], "Say things in guild chat")
	}
