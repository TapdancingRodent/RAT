import riftChatBotUtils
import random

# Roll random numbers
def bot_roll(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !roll [min] max')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["roll"]
		req.response.append(desc)
		req.response.append('Usage: !roll [min] max')
	
	else:
		# Get min and max from strings
		try:
			if len(req.argList) == 1:
				min = 1
				max = int(req.argList[0])
				
			else:
				min = int(req.argList[0])
				max = int(req.argList[1])
			
			# Return a random number
			req.response.append('I rolled %i' % random.randint(min, max))
			
		except:
			req.response.append('Syntax Error')
			
	return req

# Run on bot startup
def __bot_init__(riftBot):
	pass
	
# A list of functions contained in this module, format: (function, options, description)
__botFunctions__ = {
	'roll'	: (bot_roll, [], "Roll a random number")
	}
