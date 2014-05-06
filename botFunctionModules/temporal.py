import riftChatBotUtils
import datetime, threading

# Warn guildmates that CQ is about to end
def bot_cq(riftBot, req):
	req.argList = ['3m30s', 'CQ ending soon']
	
	return bot_timers_add(riftBot, req)

# Output server date
def bot_date(riftBot, req):
	req.toGuild = req.fromGuild
	req.toWhisp = req.fromWhisp
	
	dtdt = datetime.datetime
	req.response += [dtdt.strftime(dtdt.utcnow(), '%d/%m/%y')]
	return req
		
# Output server time
def bot_time(riftBot, req):
	req.toGuild = req.fromGuild
	req.toWhisp = req.fromWhisp
	
	dtdt = datetime.datetime
	req.response += [dtdt.strftime(dtdt.utcnow(), '%X')]
	return req

# !timers is basically an alias for !timers list
def bot_timers(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		req.toGuild = req.fromGuild
		req.toWhisp = req.fromWhisp
		
		func, opts, desc = __botFunctions__["timers"]
		req.response += [desc]
		req.response += ['Options: %s' % ",".join(__timers_options__)]
		return req
		
	return bot_timers_list(riftBot, req)
	
# Register a new timer
def bot_timers_add(riftBot, req):
	req.toGuild = req.fromGuild
	req.toWhisp = req.fromWhisp
	
	if not req.argList:
		req.response += ['Usage: !timers add hh:mm[:ss]/[Ah][Bm][Cs]']
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __timers_options__["add"]
		req.response += [desc]
		req.response += ['Usage: !timers add hh:mm[:ss]/[Ah][Bm][Cs]']
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		dtdt = datetime.datetime
		now = dtdt.utcnow()
		
		countdown = ''
		
		# Process the user's input from one of two formats
		timeStr = req.argList[0]
		if any([c in ['h','m','s'] for c in timeStr]):
			# HHhMMmSSs
			if ':' in timeStr:
				req.response += ['Syntax Error']
				
			else:
				h,m,s = [0,0,0]
				try:
					n1 = 0
					for n2, c in enumerate(timeStr):
						if c in ['h', 'H']:
							h = int(timeStr[n1:n2])
							n1 = n2+1
							
						elif c in ['m', 'M']:
							m = int(timeStr[n1:n2])
							n1 = n2+1
							
						elif c in ['s', 'S']:
							s = int(timeStr[n1:n2])
							n1 = n2+1
						
					countdown = datetime.timedelta(hours=h, minutes=m, seconds=s)
					timerTime = now + countdown
				
				except ValueError:
					req.response += ['Syntax Error']

		elif ':' in timeStr and timeStr.count(":") < 3:
			# HH:MM:SS
			if timeStr.count(":") == 2:
				try:
					fromMidnight = dtdt.strptime(timeStr, '%H:%M:%S').time()
					
				except ValueError:
					req.response += ['Syntax Error']
					
			elif timeStr.count(":") == 1:
				try:
					fromMidnight = dtdt.strptime(timeStr, '%H:%M').time()
					
				except ValueError:
					req.response += ['Syntax Error']
			
			# If we successfully parsed user input, convert to time to wait
			if fromMidnight:
				timerTime = dtdt.combine(now.date(), fromMidnight)
				if timerTime < now:
					countdown = timerTime - now + datetime.timedelta(days=1)
				else:
					countdown = timerTime - now
				
		else:
			req.response += ['Syntax Error']
		
		# If a time to wait was successfully parsed
		if countdown:
			# Get a new timer ID
			timerId = cursor.execute("SELECT MAX(timerId) AS m FROM timers").fetchone()
			if timerId and timerId['m']:
				timerId = timerId['m'] + 1
			else:
				timerId = 1
				
			# Register the timer in the database
			alertToGuild = (1 if req.toGuild else 0)
			cursor.execute("INSERT INTO timers VALUES (?,?,?,?,?,?)", (timerId, req.requester, req.requesterId, alertToGuild, ' '.join(req.argList[1:]), timerTime.strftime('%c')))
			DB.commit()
			
			# Set the timer and store it
			timer = threading.Timer(countdown.total_seconds(), bot_timers_trigger, [riftBot, timerId])
			timer.daemon = True
			timer.start()
			req.response += ['timer with ID %i due in %0.0fs' % (timerId, countdown.total_seconds())]
			if not riftBot.appendTimer(timerId, timer):
				req.response += ['Error: this timer is uninterruptible!']
	
		DB.close()
		
	return req

# List pending timers
def bot_timers_list(riftBot, req):
	req.toGuild = req.fromGuild
	req.toWhisp = req.fromWhisp
		
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __timers_options__["list"]
		req.response += [desc]
		req.response += ['Usage: !timers list [player]']
	
	else:
		# Default is the user
		if req.argList:
			main = req.argList[0].lower()
		else:
			main = req.requester
		
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Get a list of the player's timers and output them
		timers = cursor.execute("SELECT timerId, message, timeStamp FROM timers WHERE player=?", (main,)).fetchall()
		if timers:
			for timer in timers:
				countdown = datetime.datetime.strptime(timer['timeStamp'], '%c') - datetime.datetime.utcnow()
				req.response += ['Timer %i: %s due in %is' % (timer['timerId'], timer['message'], countdown.total_seconds())]
		
		else:
			req.response += ['%s has no pending timers' % main.title()]
		
		DB.close()
		
	return req

# Remove a pending timer
def bot_timers_remove(riftBot, req):
	req.toGuild = req.fromGuild
	req.toWhisp = req.fromWhisp
	
	if not req.argList:
		req.response += ['Usage: !timers rem ID [ID ..]']
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __timers_options__["rem"]
		req.response += [desc]
		req.response += ['Usage: !timers rem ID [ID ..]']
	
	else:
		# Load the timers database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Get a list of timers this user owns
		timers = cursor.execute("SELECT timerId FROM timers WHERE player=?", (req.requester,)).fetchall()
		playerTimers = [timer['timerId'] for timer in timers]
		for arg in req.argList:
			# Get the timer the user specified
			timer = cursor.execute("SELECT * FROM timers WHERE timerId=?", (int(arg),)).fetchone()
			if timer:
				try:
					if int(arg) in playerTimers or req.su:
						# Remove the timer from the database and cancel the timer function
						cursor.execute("DELETE FROM timers WHERE timerId=?", (int(arg),))
						if cursor.rowcount > 0 and riftBot.removeTimer(int(arg)):
							req.response += ['Timer %s removed' % arg]
							DB.commit()
							
						else:
							req.response += ['Error: Removal of timer %s failed' % arg]
							DB.rollback()
							
					else:
						req.response += ['%s does not own timer %s' % (req.requester.title(), arg)]
					
				except ValueError:
					req.response += ['%s is not a valid timer ID' % arg]
						
			else:
				req.response += ['No timer pending with ID %s' % arg]
			
		DB.close()
		
	return req
	
# The function passed to threading.Timer which outputs the message in future
def bot_timers_trigger(riftBot, timerId):
	# Connect to the database
	DB = riftBot.dbConnect()
	cursor = DB.cursor()
	
	# Create a new request object to output the response
	req = riftChatBotUtils.riftChatRequest()
		
	# Look up the triggered timer
	timerInfo = cursor.execute("SELECT player, playerId, sendGuild, message FROM timers WHERE timerId=?", (timerId,)).fetchone()
	if timerInfo:
		# Prepare the request object
		req.requester = timerInfo['player']
		req.requesterId = timerInfo['playerId']
		if timerInfo['sendGuild'] == 1:
			req.toGuild = True
		req.toWhisp = True
		req.response += ["%s's Timer: %s" % (timerInfo['player'].title(), timerInfo['message'])]
		
		# Remove the timer from the database
		cursor.execute("DELETE FROM timers WHERE timerId=?", (timerId,))
		DB.commit()
		riftBot.removeTimer(timerId)
		
	else:
		# Something has gone awfully wrong
		req.toGuild = True
		req.toWhisp = False
		req.response += ['Error: An orphaned timer was triggered']
	
	DB.close()
		
	riftBot.sendResponse(req)

# Run on bot startup
def __bot_init__(riftBot):
	# Retrieve any previously created timers and start them again
	DB = riftBot.dbConnect()
	cursor = DB.cursor()
	
	# Retrieve old timers (i.e. in case we just crashed)
	timers = cursor.execute("SELECT * FROM timers").fetchall()
	for oldTimer in timers:
		if oldTimer['timerId'] and oldTimer['timeStamp']:
			timerTime = datetime.datetime.strptime(oldTimer['timeStamp'], '%c')
			countdown = timerTime - datetime.datetime.utcnow()
			
			# Have we missed it?
			if countdown.total_seconds < 0:
				if countdown.total_seconds > -300:
					# Trigger the timer if its less than 5 minutes late, no point necroing
					bot_timers_trigger(riftBot, oldTimer['timerId'])
					
				else:
					cursor.execute("DELETE FROM timers WHERE timerid=?", (timer['timerId'],))
				
			else:
				# Set the timer and store it
				timer = threading.Timer(countdown.total_seconds(), bot_timers_trigger, [riftBot, oldTimer['timerId']])
				timer.daemon = True
				timer.start()
				riftBot.appendTimer(oldTimer['timerId'], timer)
				
		else:
			cursor.execute("DELETE FROM timers WHERE timerid=?", (timer['timerId'],))

# A list of options for the timers function
__timers_options__ = {
	'add'	: (bot_timers_add, [], "Add a chat alert"),
	'list'	: (bot_timers_list, [], "List chat alerts"),
	'remove': (bot_timers_remove, [], "Remove a chat alert")
	}

# A list of functions contained in this module, format: (function, options, description)
__botFunctions__ = {
	'cq'	: (bot_cq, [], "Alias for !timer 3m30s CQ ending soon"),
	'date'	: (bot_date, [], "Print server date"),
	'time'	: (bot_time, [], "Print server time"),
	'timers': (bot_timers, __timers_options__, "Schedule / manage chat alerts")
	}
	