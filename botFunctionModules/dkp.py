import riftChatBotUtils
import os, datetime, sqlite3, shutil, random, sets
from contextlib import closing

__dkpSystems__ = ['suicide', 'zerosum', 'plain']
dkpDir = './dkpTables'

# Not really a function
def bot_dkp(riftBot, req):
	func, opts, desc = __botFunctions__["dkp"]
	req.response.append(desc)
	req.response.append('Options: %s' % ", ".join(__dkp_options__))
	return req

# Just an alias for raiders list
def bot_dkp_modify(riftBot, req):
	func, opts, desc = __dkp_options__["modify"]
	req.response.append(desc)
	req.response.append('Options: %s' % ", ".join(__modify_options__))
	return req

# Modify a single player's dkp in a plain table
def bot_dkp_modify_add(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp modify add [-commit] [-note=?] table reason raider [raider ..] N[%]')
	
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __modify_options__["add"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp modify add [-commit] [-note=?] table reason raider [raider ..] N[%]')
	
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			# Strip special arguments
			confirmed = False
			notes = ""
			for n in reversed(range(len(req.argList))):
				if req.argList[n] == "-commit":
					confirmed = True
					del req.argList[n]
				
				elif req.argList[n].startswith("-note="):
					req.argList[n].strip("-note=")
					notes = req.argList[n]
					del req.argList[n]
			
			if not confirmed:
				req.response.append('Running in test mode (use -commit)')
					
			if len(req.argList) > 3:
				name = req.argList[0]
				if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
					reason = req.argList[1]
					playersList = [req.argList[2].lower()]
					
					for n, arg in enumerate(req.argList[3:]):
						pcMode = False
						if arg.endswith("%"):
							arg = arg[-1]
							pcMode = True
						
						dkpChange = None
						try:
							dkpChange = float(arg)
							
						except ValueError:
							pass
						
						if dkpChange is None:
							playersList += [arg.lower()]
						
						else:
							break
					
					print playersList
					
					if dkpChange is not None:
						# Connect to the database
						with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
							dkpDB.row_factory = sqlite3.Row
							dkpCursor = dkpDB.cursor()
							
							metadata = dkpCursor.execute("SELECT * FROM metadata").fetchone()
							currentTransaction = metadata['currentTransaction']+1
							tableType = metadata['type']
							
							if tableType == "plain":
								cursor.execute("INSERT INTO dkpTransactions VALUES (?,?,?,?,?,?)", (name, currentTransaction, req.requester, req.requesterId, "dkp change %s" % (" ".join(req.argList)), datetime.datetime.utcnow().strftime('%c')))
								
								# Purge any old rolled-back changes to the database
								transactionsOverwritten = bot_dkp_tables_cleanup(dkpDB, currentTransaction)
								if transactionsOverwritten > 0:
									req.response.append('Warning: %i rolled back changes will be deleted' % transactionsOverwritten)
									if confirmed:
										bot_dkp_tables_backup('%s_%s' % (riftBot.charName, name))
								
								# Iterate through the players list adding a new entry in history
								notInTable = []
								playersList = []
								somethingDone = False
								for player in playersList:
									playerActive = dkpCursor.execute("SELECT 1 FROM activeRaiders WHERE player=?", (player,)).fetchone()
									
									if playerActive:
										if pcMode:
											# Changing by a percentage (for taxes etc)
											playersDkp = dkpCursor.execute("SELECT dkp FROM currentDkp WHERE player=?", (player,)).fetchone()['dkp']
											dkpCursor.execute("INSERT INTO history VALUES (?,?,?,?,?)", (player, (playersDkp * dkpChange / 100), reason, notes, currentTransaction))
											req.response.append('%i) %0.0f dkp added to %s' % (currentTransaction, (playersDkp * dkpChange / 100), player.title()))
										
										else:
											# Changing by fixed amount
											dkpCursor.execute("INSERT INTO history VALUES (?,?,?,?,?)", (player, dkpChange, reason, notes, currentTransaction))
											somethingDone = True
											playersList.append(player)
										
									else:
										notInTable.append(player)
								
								if playersList:
									req.response.append('%i) %0.0f dkp added to %s' % (currentTransaction, dkpChange, [p.title() for p in playersList]))
									
								if notInTable:
									req.response.append('%s not in table: %s' % (", ".join([p.title() for p in notInTable]), name))
								
								dkpCursor.execute("UPDATE metadata SET currentTransaction=?", (currentTransaction,))
										
								if confirmed and somethingDone:
									DB.commit()
									dkpDB.commit()
									
								else:
									DB.rollback()
									dkpDB.rollback()
							
							else:
								req.response.append('dkp change can only be used on "plain" type DKP tables')
					
					else:
						req.response.append('Syntax Error')
					
				else:
					req.response.append('Error: No table with name: %s' % name)
					
			else:
				req.response.append('Syntax Error')
			
			
		else:
			req.response.append('Managing dkp tables must be done as a super user')
	
		DB.close()
		
	return req

# Move a player a few places in a suicide table
def bot_dkp_modify_bump(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp modify bump [-commit] [-note=?] table reason raider [raider ..]')
	
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __modify_options__["bump"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp modify bump [-commit] [-note=?] table reason raider [raider ..]')
	
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			# Strip a few special arguments
			confirmed = False
			notes = ""
			for n in reversed(range(len(req.argList))):
				if req.argList[n] == "-commit":
					confirmed = True
					del req.argList[n]
				
				elif req.argList[n].startswith("-note="):
					req.argList[n].strip("-note=")
					notes = req.argList[n]
					del req.argList[n]
			
			if not confirmed:
				req.response.append('Running in test mode (use -commit)')
			
			if len(req.argList) > 3:
				name = req.argList[0]
				if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
					reason = req.argList[1]
					playersList = [player.lower() for player in req.argList[2:-1]]
					
					dkpChange = None
					try:
						dkpChange = int(req.argList[-1])
					
					except ValueError:
						pass
					
					if dkpChange:
						# Load the dkp database
						with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
							dkpDB.row_factory = sqlite3.Row
							dkpCursor = dkpDB.cursor()
							
							metadata = dkpCursor.execute("SELECT * FROM metadata").fetchone()
							currentTransaction = metadata['currentTransaction']+1
							tableType = metadata['type']
							
							if tableType == "suicide":
								cursor.execute("INSERT INTO dkpTransactions VALUES (?,?,?,?,?,?)", (name, currentTransaction, req.requester, req.requesterId, "dkp suicide %s" % (" ".join(req.argList)), datetime.datetime.utcnow().strftime('%c')))
								
								# Purge any old rolled-back changes to the database
								transactionsOverwritten = bot_dkp_tables_cleanup(dkpDB, currentTransaction)
								if transactionsOverwritten > 0:
									req.response.append('Warning: %i rolled back changes will be deleted' % transactionsOverwritten)
									if confirmed:
										bot_dkp_tables_backup('%s_%s' % (riftBot.charName, name))
								
								# Get players current DKP
								currentDkp = dkpCursor.execute("SELECT * FROM currentDkp").fetchall()
								playersDkp = [None for _ in playersList]
								for n, cD in enumerate(currentDkp):
									for p, player in enumerate(playersList):
										if player == cD['player']:
											playersDkp[p] = cD['dkp']
											break
								
								# Check that everyone is present
								notInTable = []
								for n in reversed(range(len(playersList))):
									if playersDkp[n] is None:
										notInTable.append(playersList[n])
										del playersDkp[n]
										del playersList[n]
								
								if notInTable:
									req.response.append('%s not in table: %s' % (", ".join([p.title() for p in notInTable]), name))
								
								# Arrange the players so that their order is preserved
								if dkpChange >= 0:
									playerRecords = sorted(zip([d for d in playersDkp], playersList), key=lambda p: p[0], reverse=True)
								
								else:
									playerRecords = sorted(zip([d for d in playersDkp], playersList), key=lambda p: p[0])
								
								# Loop through and make the changes
								for dkp, player in playerRecords:
									if dkpChange >= 0:
										dkpCursor.execute("INSERT INTO history SELECT player, -1, 'bookkeeping', '', ? FROM currentDkp WHERE dkp>? AND dkp<=?", (currentTransaction, dkp, dkp+dkpChange))
									
									else:
										dkpCursor.execute("INSERT INTO history SELECT player, 1, 'bookkeeping', '', ? FROM currentDkp WHERE dkp<? AND dkp>=?", (currentTransaction, dkp, dkp+dkpChange))
									
									dkpCursor.execute("INSERT INTO history VALUES (?,?,?,?,?)", (player, dkpChange, reason, notes, currentTransaction))
								
								if playersList:
									req.response.append('%i) %s added %i dkp' % (currentTransaction, ", ".join([p.title() for p in playersList]), dkpChange))
									
									# Correct the table of any people who went off the ends
									minDkp = dkpCursor.execute("SELECT MIN(dkp) AS m FROM currentDkp").fetchone()['m']
									if not minDkp == 1:
										dkpCursor.execute("INSERT INTO history SELECT player, ?, 'bookkeeping', '', ? FROM currentDkp", (-minDkp+1, currentTransaction))
									
									# Remove any gaps in the dkp list
									unused = [i['i'] for i in dkpCursor.execute("SELECT * FROM unusedIndexes ORDER BY i").fetchall()]
									# Perhaps risky infinite loop to catch wider gaps
									while len(unused) > 1:
										for n in range(len(unused)-1):
											dkpCursor.execute("INSERT INTO history SELECT player, ?, 'bookkeeping', '', ? FROM currentDkp WHERE dkp>? AND dkp<?", (-n-1, currentTransaction, unused[n], unused[n+1]))
										
										unused = [i['i'] for i in dkpCursor.execute("SELECT * FROM unusedIndexes ORDER BY i").fetchall()]
								
								dkpCursor.execute("UPDATE metadata SET currentTransaction=?", (currentTransaction,))
								
								if confirmed and playersList:
									DB.commit()
									dkpDB.commit()
								
								else:
									DB.rollback()
									dkpDB.rollback()
							
							else:
								req.response.append('dkp suicide can only be used on "suicide" type DKP tables')
					
					else:
						req.response.append('Error: Failed to parse dkp value')
				
				else:
					req.response.append('Error: No table with name: %s' % name)
			
			else:
				req.response.append('Syntax Error')
		
		else:
			req.response.append('Managing dkp tables must be done as a super user')
	
		DB.close()
		
	return req

# Move dkp around in a zerosum dkp table
def bot_dkp_modify_reassign(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp modify reassign [-commit] [-note=?] table reason gainer [gainer ..] N loser [loser ..]')
	
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __modify_options__["reassign"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp modify reassign [-commit] [-note=?] table reason gainer [gainer ..] N loser [loser ..]')
	
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			# Catch special function arguments
			confirmed = False
			notes = ""
			for n in reversed(range(len(req.argList))):
				if req.argList[n] == "-commit":
					confirmed = True
					del req.argList[n]
				
				elif req.argList[n].startswith("-note="):
					req.argList[n].replace("-note=", "")
					notes = req.argList[n]
					del req.argList[n]
			
			if not confirmed:
				req.response.append('Running in test mode (use -commit)')
			
			if len(req.argList) > 3:
				name = req.argList[0]
				if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
					# Gather input arguments
					reason = req.argList[1]
					gList = []
					for n, arg in enumerate(req.argList[2:]):
						gChange = None
						try:
							gChange = float(arg)
							
						except ValueError:
							pass
						
						if gChange is None:
							gList.append(arg.lower())
						
						else:
							lList = [arg.lower() for arg in req.argList[2+n+1:]]
							break
					
					gSet = sets.Set(gList)
					lSet = sets.Set(lList)
					
					if gChange is not None:
						# Load the dkp database
						with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
							dkpDB.row_factory = sqlite3.Row
							dkpCursor = dkpDB.cursor()
							
							metadata = dkpCursor.execute("SELECT * FROM metadata").fetchone()
							currentTransaction = metadata['currentTransaction']+1
							tableType = metadata['type']
							
							if tableType == "zerosum":
								cursor.execute("INSERT INTO dkpTransactions VALUES (?,?,?,?,?,?)", (name, currentTransaction, req.requester, req.requesterId, "dkp reassign %s" % (" ".join(req.argList)), datetime.datetime.utcnow().strftime('%c')))
								
								# Purge any old rolled-back changes to the database
								transactionsOverwritten = bot_dkp_tables_cleanup(dkpDB, currentTransaction)
								if transactionsOverwritten > 0:
									req.response.append('Warning: %i rolled back changes will be deleted' % transactionsOverwritten)
									if confirmed:
										bot_dkp_tables_backup('%s_%s' % (riftBot.charName, name))
								
								activeRaiders = [aR['player'] for aR in dkpCursor.execute("SELECT * FROM activeRaiders").fetchall()]
								aRSet = sets.Set(activeRaiders)
								
								itsAllGood = True
								# Do some sanity checks
								if len(lSet & gSet) > 0:
									req.response.append('Error: losing players and gaining players share a member')
									itsAllGood = False
								
								elif not lSet <= aRSet or not gSet <= aRSet:
									req.response.append('%s not in table: %s' % (", ".join((lSet - aRSet) | (gSet - aRSet)), name))
									itsAllGood = False
								
								# If a group was empty use "all other active players"
								if len(lSet) == 0:
									lSet = aRSet - gSet
								
								elif len(gSet) == 0:
									gSet = aRSet - lSet
									
								elif len(gSet) == 0:
									req.response.append('Error: Gaining players list is empty')
									itsAllGood = False
								
								if len(lSet) == 0:
									req.response.append('Error: Losing players list is empty')
									itsAllGood = False
								
								# Pre-flight checks complete, move the dkp around
								if itsAllGood:
									lChange = -gChange * len(gSet) / len(lSet)
									
									dkpCursor.executemany("INSERT INTO history VALUES (?,?,?,?,?)", [(p, gChange, reason, notes, currentTransaction) for p in gSet])
									dkpCursor.executemany("INSERT INTO history VALUES (?,?,?,?,?)", [(p, lChange, reason, notes, currentTransaction) for p in lSet])
									
									req.response.append('%i) %s added %0.0f dkp' % (currentTransaction, ", ".join(gSet), gChange))
									req.response.append('%i) %s added %0.0f dkp' % (currentTransaction, ", ".join(lSet), lChange))
									
								dkpCursor.execute("UPDATE metadata SET currentTransaction=?", (currentTransaction,))
								
								if confirmed and itsAllGood:
									DB.commit()
									dkpDB.commit()
									
								else:
									DB.rollback()
									dkpDB.rollback()
							
							else:
								req.response.append('dkp reassign can only be used on "zerosum" type DKP tables')
					
					else:
						req.response.append('Error: Failed to parse dkp value')
					
				else:
					req.response.append('Error: No table with name: %s' % name)
					
			else:
				req.response.append('Syntax Error: Too few arguments')
			
			
		else:
			req.response.append('Managing dkp tables must be done as a super user')
	
		DB.close()
		
	return req

# Drop a raider to the bottom of a DKP table
def bot_dkp_modify_suicide(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp modify suicide [-commit] [-note=?] table reason raider [raider ..]')
	
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __modify_options__["suicide"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp modify suicide [-commit] [-note=?] table reason raider [raider ..]')
	
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			# Catch special input arguments
			confirmed = False
			notes = ""
			for n in reversed(range(len(req.argList))):
				if req.argList[n] == "-commit":
					confirmed = True
					del req.argList[n]
				
				elif req.argList[n].startswith("-note="):
					req.argList[n].strip("-note=")
					notes = req.argList[n]
					del req.argList[n]
			
			if not confirmed:
				req.response.append('Running in test mode (use -commit)')
					
			if len(req.argList) > 2:
				name = req.argList[0]
				if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
					reason = req.argList[1]
					playersList = [player.lower() for player in req.argList[2:]]
					
					# Load the DKP database
					with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
						dkpDB.row_factory = sqlite3.Row
						dkpCursor = dkpDB.cursor()
						
						metadata = dkpCursor.execute("SELECT * FROM metadata").fetchone()
						currentTransaction = metadata['currentTransaction']+1
						tableType = metadata['type']
						
						if tableType == "suicide":
							cursor.execute("INSERT INTO dkpTransactions VALUES (?,?,?,?,?,?)", (name, currentTransaction, req.requester, req.requesterId, "dkp suicide %s" % (" ".join(req.argList)), datetime.datetime.utcnow().strftime('%c')))
							
							# Purge any old rolled-back changes to the database
							transactionsOverwritten = bot_dkp_tables_cleanup(dkpDB, currentTransaction)
							if transactionsOverwritten > 0:
								req.response.append('Warning: %i rolled back changes will be deleted' % transactionsOverwritten)
								if confirmed:
									bot_dkp_tables_backup('%s_%s' % (riftBot.charName, name))
							
							currentDkp = dkpCursor.execute("SELECT * FROM currentDkp").fetchall()
							
							# Retrieve current DKP information
							playersDkp = [None for p in playersList]
							for cD in currentDkp:
								for p, player in enumerate(playersList):
									if player == cD['player']:
										playersDkp[p] = cD['dkp']
										break
							
							# Purge any players not in the dkp table
							notInTable = []
							for n in reversed(range(len(playersList))):
								if playersDkp[n] is None:
									notInTable.append(playersList[n])
									del playersDkp[n]
									del playersList[n]
							
							if notInTable:
								req.response.append('%s not in table: %s' % (", ".join(notInTable), name))
							
							# Arrange the players so that their order is preserved and cull the herd
							playerRecords = sorted(zip([d for d in playersDkp], playersList), key=lambda p: p[0], reverse=True)
							for n, record in enumerate(playerRecords):
								dkp, player = record
								# Move all other players up on
								dkpCursor.execute("INSERT INTO history SELECT player, 1, 'bookkeeping', '', ? FROM currentDkp WHERE dkp<?", (currentTransaction, dkp+n))
								
								# Drop the player to the bottom of the table
								dkpCursor.execute("INSERT INTO history VALUES (?,?,?,?,?)", (player, 1-dkp-n, reason, notes, currentTransaction))
								
								req.response.append('%i) %s lost %i dkp' % (currentTransaction, player, dkp-1))
							
							dkpCursor.execute("UPDATE metadata SET currentTransaction=?", (currentTransaction,))
									
							if confirmed and playerRecords:
								DB.commit()
								dkpDB.commit()
								
							else:
								DB.rollback()
								dkpDB.rollback()
							
						else:
							req.response.append('dkp suicide can only be used on "suicide" type DKP tables')
				
				else:
					req.response.append('Error: No table with name: %s' % name)
					
			else:
				req.response.append('Syntax Error')
			
			
		else:
			req.response.append('Managing dkp tables must be done as a super user')
	
		DB.close()
		
	return req

# Just an alias for raiders list
def bot_dkp_raiders(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __dkp_options__["raiders"]
		req.response.append(desc)
		req.response.append('Options: %s' % ", ".join(__raiders_options__))
		return req
		
	return bot_dkp_raiders_list(riftBot, req)

# Insert a player into a dkp table
def bot_dkp_raiders_add(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp raiders add [-commit] table raider [raider ..]')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __raiders_options__["add"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp raiders add [-commit] table raider [raider ..]')
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			confirmed = False
			for n in reversed(range(len(req.argList))):
				if req.argList[n] == "-commit":
					confirmed = True
					del req.argList[n]
			
			if not confirmed:
				req.response.append('Running in test mode (use -commit)')
			
			if len(req.argList) > 1:
				name = req.argList[0]
				if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
					# Load the database
					with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
						dkpDB.row_factory = sqlite3.Row
						dkpCursor = dkpDB.cursor()
						
						metadata = dkpCursor.execute("SELECT * FROM metadata").fetchone()
						currentTransaction = metadata['currentTransaction']+1
						tableType = metadata['type']
						
						cursor.execute("INSERT INTO dkpTransactions VALUES (?,?,?,?,?,?)", (name, currentTransaction, req.requester, req.requesterId, "dkp raiders add %s" % (" ".join(req.argList)), datetime.datetime.utcnow().strftime('%c')))
						
						# Purge any old rolled-back changes to the database
						transactionsOverwritten = bot_dkp_tables_cleanup(dkpDB, currentTransaction)
						if transactionsOverwritten > 0:
							req.response.append('Warning: %i rolled back changes will be deleted' % transactionsOverwritten)
							if confirmed:
								bot_dkp_tables_backup('%s_%s' % (riftBot.charName, name))
						
						# Validate the player list
						playersList = []
						inTable = []
						for player in [player.lower() for player in req.argList[1:]]:
							playerActive = dkpCursor.execute("SELECT 1 FROM activeRaiders WHERE player=?", (player,)).fetchone()
							
							if not playerActive:
								playersList += [player]
								
							else:
								inTable.append(player.title())
						
						if inTable:
							req.response.append('Error: %s already in table: %s' % (", ".join(inTable), name))
						
						# Actually insert the players into the database
						if playersList:
							dkpCursor.executemany("INSERT INTO raiders VALUES (?,1,?)", [(p, currentTransaction) for p in playersList])
							
							# Initial dkp values will depend on the table type
							# For suicide players we insert into the middle of the table
							if tableType == "suicide":
								tableMean = dkpCursor.execute("SELECT AVG(dkp) AS m FROM currentDkp").fetchone()
								if tableMean['m'] is None:
									tableMean = 1
									
								elif tableMean['m'] % 1 == 0.5:
									tableMean = tableMean['m'] + random.choice([0.5, -0.5])
									
								else:
									tableMean = tableMean['m']
									
								initialValues = [v + tableMean for v in range(1, len(playersList)+1)]
									
								dkpCursor.execute("INSERT INTO history SELECT player,?,'bookkeeping','',? FROM currentDkp WHERE dkp>=?", (len(playersList), currentTransaction, tableMean))
							
							else:
								initialValues = [0 for player in playersList]
							
							dkpCursor.executemany("INSERT INTO history VALUES (?,?,'insertion','',?)", [(p, iV, currentTransaction) for p, iV in zip(playersList, initialValues)])
							
							req.response.append('%i) %s added to table: %s' % (currentTransaction, ", ".join([p.title() for p in playersList]), name))
						
						dkpCursor.execute("UPDATE metadata SET currentTransaction=?", (currentTransaction,))
								
						if confirmed and playersList:
							DB.commit()
							dkpDB.commit()
							
						else:
							DB.rollback()
							dkpDB.rollback()
				
				else:
					req.response.append('Error: No table with name: %s' % name)
					
			else:
				req.response.append('Syntax Error')
			
			
		else:
			req.response.append('Managing dkp tables must be done as a super user')
	
		DB.close()
		
	return req

# Show a rough history of a raider's DKP changes
def bot_dkp_raiders_history(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __raiders_options__["history"]
		req.response.append(desc)
		req.response.append('Usage: !dkp raiders history table [player]')
		
	else:
		verbose = False
		for n in reversed(range(len(req.argList))):
			if req.argList[n] in ['-v', '--verbose']:
				verbose = True
				del req.argList[n]
		
		if req.argList:
			name = req.argList[0]
			if not req.argList[1:]:
				player = req.requester
			
			else:
				player = req.argList[1].lower()
			
			if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
				# Load the database
				with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
					dkpDB.row_factory = sqlite3.Row
					dkpCursor = dkpDB.cursor()
					
					# Return a detailed dkp list if the player exists
					playersDkp = dkpCursor.execute("SELECT * FROM currentDkp WHERE player=?", (player,)).fetchone()
					if playersDkp:
						total = playersDkp['dkp']
						if verbose:
							# Verbose mode outputs the entire player history
							req.response.append('%s: %i dkp total' % (player.title(), total))
							req.response.append(' {0: <5} | {1: <3} | {2}, {3}'.format("dkp", "ID", "reason", "notes"))
							history = dkpCursor.execute("SELECT * FROM currentHistory WHERE player=?", (player,)).fetchall()
							for change in history:
								if change['notes']:
									req.response.append(' {0: <5} | {1: <3} | {2}, {3}'.format(change['dkpChange'], change['transactionId'], change['reason'], change['notes']))
								else:
									req.response.append(' {0: <5} | {1: <3} | {2}'.format(change['dkpChange'], change['transactionId'], change['reason']))
						
						else:
							# Non-verbose mode gives a summary
							looted = dkpCursor.execute("SELECT SUM(dkpChange) AS s FROM currentHistory WHERE player=? AND (reason LIKE 'item' OR reason LIKE 'loot')", (player,)).fetchone()['s']
							misc = dkpCursor.execute("SELECT SUM(dkpChange) AS s FROM currentHistory WHERE player=? AND ((reason='bookkeeping') OR (reason NOT LIKE 'item' AND reason NOT LIKE 'loot' AND dkpChange<0))", (player,)).fetchone()['s']
							gained = dkpCursor.execute("SELECT SUM(dkpChange) AS s FROM currentHistory WHERE player=? AND dkpChange>0 AND reason<>'bookkeeping'", (player,)).fetchone()['s']
							
							req.response.append('%s: %i (%i gained, %i looted, %i misc)' % (player.title(), total, gained, looted, misc))
					
					else:
						req.response.append('%s not in table: %s' % (player.title(), name))
			
			else:
				req.response.append('Error: No table with name: %s' % name)
		
		else:
			req.response.append('Syntax Error')
	
	return req

def bot_dkp_raiders_list(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __raiders_options__["list"]
		req.response.append(desc)
		req.response.append('Usage: !dkp raiders list table')
		
	else:
		if req.argList:
			name = req.argList[0]
			
			if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
				# Load the database
				with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
					dkpDB.row_factory = sqlite3.Row
					dkpCursor = dkpDB.cursor()
					
					playersList = dkpCursor.execute("SELECT player FROM activeRaiders").fetchall()
					playersList = [p['player'] for p in playersList]
					
					if playersList:
						req.response.append(", ".join([p.title() for p in playersList]))
				
			else:
				req.response.append('Error: No table with name: %s' % name)
		
		else:
			req.response.append('Syntax Error')
	
	return req

def bot_dkp_raiders_purge(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp raiders purge [-commit] raider [raider ..]')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __raiders_options__["purge"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp raiders purge [-commit] raider [raider ..]')
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			confirmed = False
			for n in reversed(range(len(req.argList))):
				if req.argList[n] == "-commit":
					confirmed = True
					del req.argList[n]
			
			if not confirmed:
				req.response.append('Running in test mode (use -commit)')
				
			# Log the use of su
			cursor.execute("INSERT INTO dkpTransactions VALUES (?,?,?,?,?,?)", ('_ALL_TABLES', '_VARIABLE_', req.requester, req.requesterId, "dkp raiders purge %s" % (" ".join(req.argList)), datetime.datetime.utcnow().strftime('%c')))
				
			if confirmed:
				DB.commit()
				
			else:
				DB.rollback()
				
			# Open each dkp table
			for name in [t for t in os.listdir(dkpDir) if t.startswith(riftBot.charName) and not "_DELETED_" in t]:
				with closing(sqlite3.connect('%s/%s' % (dkpDir, name))) as dkpDB:
					dkpDB.row_factory = sqlite3.Row
					dkpCursor = dkpDB.cursor()
					
					# Get the current state of the database
					metadata = dkpCursor.execute("SELECT * FROM metadata").fetchone()
					currentTransaction = metadata['currentTransaction']+1
					tableType = metadata['type']
					
					# Purge any old rolled-back changes to the database
					transactionsOverwritten = bot_dkp_tables_cleanup(dkpDB, currentTransaction)
					if transactionsOverwritten > 0:
						req.response.append('Warning: %i rolled back changes will be deleted' % transactionsOverwritten)
						if confirmed:
							bot_dkp_tables_backup('%s_%s' % (riftBot.charName, name))
					
					# Iterate through the players, check if they exist and remove them
					recycledDkp = 0
					playersList = []
					for player in [player.lower() for player in req.argList]:
						playerActive = dkpCursor.execute("SELECT 1 FROM activeRaiders WHERE player=?", (player,)).fetchone()
						
						if playerActive:
							# Get the current dkp of the player
							finalDkp = dkpCursor.execute("SELECT dkp FROM currentDkp WHERE player=?", (player,)).fetchone()
							if finalDkp:
								finalDkp = finalDkp['dkp']
								
							else:
								finalDkp = 0
							
							# Mark the player as retired and recycle any of their dkp
							dkpCursor.execute("INSERT INTO raiders VALUES (?,?,?)", (player, 0, currentTransaction))
							dkpCursor.execute("INSERT INTO history VALUES (?,?,?,?,?)", (player, -finalDkp, 'retiring', '', currentTransaction))
							
							if tableType == "suicide":
								# We need to bump a bunch of people down one
								dkpCursor.execute("INSERT INTO history SELECT player,-1,'bookkeeping','',? FROM currentDkp WHERE dkp>=?", (currentTransaction, finalDkp))
								playersList.append(player)
							
							elif tableType == "zerosum":
								recycledDkp += finalDkp
								req.response.append('%i) %s removed from %s recycling %f dkp' % (currentTransaction, player.title(), name, finalDkp))
								
							else:
								playersList.append(player)
					
					if playersList:
						req.response.append('%i) %s removed from %s' % (currentTransaction, ", ".join([p.title() for p in playersList]), name))
					
					if tableType == "zerosum":
						numActive = dkpCursor.execute("SELECT COUNT(*) AS c FROM activeRaiders").fetchone()['c']
						if recycledDkp != 0 and numActive:
							dkpCursor.execute("INSERT INTO history SELECT player,?,'bookkeeping','',? FROM activeRaiders", (recycledDkp/numActive, currentTransaction))
					
					dkpCursor.execute("UPDATE metadata SET currentTransaction=?", (currentTransaction,))
					
					if confirmed:
						dkpDB.commit()
						
					else:
						dkpDB.rollback()
		
		else:
			req.response.append('Managing dkp tables must be done as a super user')
	
		DB.close()
		
	return req

# Remove players from DKP tables
def bot_dkp_raiders_remove(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp raiders remove [-commit] table raider [raider ..]')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __raiders_options__["remove"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp raiders remove [-commit] table raider [raider ..]')
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			# Check if the user has confirmed the transaction
			confirmed = False
			for n in reversed(range(len(req.argList))):
				if req.argList[n] == "-commit":
					confirmed = True
					del req.argList[n]
			
			if not confirmed:
				req.response.append('Running in test mode (use -commit)')
			
			# Check that we have enough information
			if len(req.argList) > 1:
				name = req.argList[0]
				
				# Open the dkp table
				if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
					with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
						dkpDB.row_factory = sqlite3.Row
						dkpCursor = dkpDB.cursor()
						
						# Get the current state of the database
						metadata = dkpCursor.execute("SELECT * FROM metadata").fetchone()
						currentTransaction = metadata['currentTransaction']+1
						tableType = metadata['type']
						
						# Log the use of su
						cursor.execute("INSERT INTO dkpTransactions VALUES (?,?,?,?,?,?)", (name, currentTransaction, req.requester, req.requesterId, "dkp raiders remove %s" % (" ".join(req.argList)), datetime.datetime.utcnow().strftime('%c')))
						
						# Purge any old rolled-back changes to the database
						transactionsOverwritten = bot_dkp_tables_cleanup(dkpDB, currentTransaction)
						if transactionsOverwritten > 0:
							req.response.append('Warning: %i rolled back changes will be deleted' % transactionsOverwritten)
							if confirmed:
								bot_dkp_tables_backup('%s_%s' % (riftBot.charName, name))
						
						# Iterate through the players, check if they exist and remove them
						recycledDkp = 0
						playersList = []
						notInTable = []
						for player in [player.lower() for player in req.argList[1:]]:
							playerActive = dkpCursor.execute("SELECT 1 FROM activeRaiders WHERE player=?", (player,)).fetchone()
							
							if playerActive:
								# Get the current dkp of the player
								finalDkp = dkpCursor.execute("SELECT dkp FROM currentDkp WHERE player=?", (player,)).fetchone()
								if finalDkp:
									finalDkp = finalDkp['dkp']
									
								else:
									finalDkp = 0
								
								# Mark the player as retired and recycle any of their dkp
								dkpCursor.execute("INSERT INTO raiders VALUES (?,?,?)", (player, 0, currentTransaction))
								dkpCursor.execute("INSERT INTO history VALUES (?,?,?,?,?)", (player, -finalDkp, 'retiring', '', currentTransaction))
								
						
								if tableType == "suicide":
									# We need to bump a bunch of people down one
									dkpCursor.execute("INSERT INTO history SELECT player,-1,'bookkeeping','',? FROM currentDkp WHERE dkp>=?", (currentTransaction, finalDkp))
									playersList.append(player)
								
								elif tableType == "zerosum":
									recycledDkp += finalDkp
									req.response.append('%i) %s removed from %s recycling %f dkp' % (currentTransaction, player.title(), name, initialValue))
									
								else:
									playersList.append(player)
									
							else:
								notInTable.append(player)
						
						if notInTable:
							req.response.append('%s not in table: %s' % (", ".join([p.title() for p in notInTable]), name))
						
						if playersList and not tableType == "zerosum":
							req.response.append('%i) %s removed from %s' % (currentTransaction, ", ".join([p.title() for p in playersList]), name))
						
						if tableType == "zerosum":
							numActive = dkpCursor.execute("SELECT COUNT(*) AS c FROM activeRaiders").fetchone()['c']
							if recycledDkp != 0 and numActive:
								dkpCursor.execute("INSERT INTO history SELECT player,?,'bookkeeping','',? FROM activeRaiders", (currentTransaction, recycledDkp/numActive, currentTransaction))
						
						dkpCursor.execute("UPDATE metadata SET currentTransaction=?", (currentTransaction,))
					
								
						if confirmed:
							DB.commit()
							dkpDB.commit()
							
						else:
							DB.rollback()
							dkpDB.rollback()
				
				else:
					req.response.append('Error: No table with name: %s' % name)
					
			else:
				req.response.append('Syntax Error')
			
			
		else:
			req.response.append('Managing dkp tables must be done as a super user')
	
		DB.close()
		
	return req

# Show a player's current DKP
def bot_dkp_raiders_total(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __raiders_options__["total"]
		req.response.append(desc)
		req.response.append('Usage: !dkp raiders total table [player ..]')
		
	else:
		if req.argList:
			name = req.argList[0]
			if not req.argList[1:]:
				playersList = [req.requester]
			
			else:
				playersList = [arg.lower() for arg in req.argList[1:]]
			
			if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
				# Load the database
				with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
					dkpDB.row_factory = sqlite3.Row
					dkpCursor = dkpDB.cursor()
					
					playersDkp = [None for _ in playersList]
					notInTable = []
					for p in reversed(range(len(playersList))):
						playerRecord = dkpCursor.execute("SELECT * FROM currentDkp WHERE player=?", (playersList[p],)).fetchone()
						if playerRecord:
							playersDkp[p] = playerRecord['dkp']
							
						else:
							notInTable.append(playersList[p])
							del playersList[p]
							del playersDkp[p]
					
					if notInTable:
						req.response.append("%s not in table: %s" % (", ".join([p.title() for p in notInTable]), name))
					
					if playersList:
						req.response.append(", ".join(['%s:%0.0f' % (p.title(), playersDkp[n]) for n,p in enumerate(playersList)]))
				
			else:
				req.response.append('Error: No table with name: %s' % name)
		
		else:
			req.response.append('Syntax Error')
	
	return req

# Just an alias for tables list
def bot_dkp_tables(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __dkp_options__["tables"]
		req.response.append(desc)
		req.response.append('Options: %s' % ", ".join(__tables_options__))
		return req
		
	return bot_dkp_tables_list(riftBot, req)

# Backup a table to prevent loss of any information
def bot_dkp_tables_backup(dbName):
	suffixes = []
	for name in os.listdir(dkpDir):
		if name.startswith('%s_DELETED_' % dbName):
			try:
				suffixes.append(int(name.replace('.db', '').replace('%s_DELETED_' % dbName, '')))
			
			except ValueError:
				pass # something bad has happened but there isn't much I can do about it
	
	suffix = max(suffixes) + 1 if suffixes else 1
	
	shutil.copy('%s/%s.db' % (dkpDir, dbName), '%s/%s_DELETED_%i.db' % (dkpDir, dbName, suffix))
	return

# Add a DKP table
def bot_dkp_tables_create(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp tables add [-commit] type name description')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __tables_options__["add"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp tables add [-commit] type name description')
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			confirmed = False
			for n in reversed(range(len(req.argList))):
				if req.argList[n] == "-commit":
					confirmed = True
					del req.argList[n]
			
			if not confirmed:
				req.response.append('Running in test mode (use -commit)')
					
			if len(req.argList) > 1:
				# Gather input arguments
				type = req.argList[0]
				name = req.argList[1]
				desc = " ".join(req.argList[2:])
				
				if type in __dkpSystems__:
					if not "_" in name and not "." in name:
						if not os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
							cursor.execute("INSERT INTO dkpTransactions VALUES (?,?,?,?,?,?)", (name, 0, req.requester, req.requesterId, "dkp tables add %s" % (" ".join(req.argList)), datetime.datetime.utcnow().strftime('%c')))
							
							# Connect to the new DKP database
							with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
								dkpDB.row_factory = sqlite3.Row
								dkpCursor = dkpDB.cursor()
								
								# Initialise a couple of tables and a shed load of useful views, set metadata
								dkpCursor.execute("CREATE TABLE IF NOT EXISTS metadata (type VARCHAR(10), description VARCHAR(255), currentTransaction INT)")
								dkpCursor.execute("INSERT INTO metadata VALUES (?, ?, 0)", (type, desc))
								dkpCursor.execute("CREATE TABLE IF NOT EXISTS history (player VARCHAR(30), dkpChange REAL, reason VARCHAR(30), notes VARCHAR(255), transactionId INT)")
								dkpCursor.execute("CREATE TABLE IF NOT EXISTS raiders (player VARCHAR(30), active INT, transactionId INT)")
								dkpCursor.execute("CREATE VIEW IF NOT EXISTS activeRaiders AS SELECT player FROM (SELECT player, active, MAX(transactionId) FROM raiders WHERE transactionId<=(SELECT currentTransaction FROM metadata LIMIT 1) GROUP BY player) WHERE active=1")
								dkpCursor.execute("CREATE VIEW IF NOT EXISTS currentHistory AS SELECT player, dkpChange, reason, notes, transactionId FROM activeRaiders JOIN history USING (player) WHERE transactionId<=(SELECT currentTransaction FROM metadata LIMIT 1)")
								dkpCursor.execute("CREATE VIEW IF NOT EXISTS currentDkp AS SELECT player, SUM(dkpChange) AS dkp FROM activeRaiders JOIN history USING (player) WHERE transactionId<=(SELECT currentTransaction FROM metadata LIMIT 1) GROUP BY player ORDER BY dkp DESC")
								dkpCursor.execute("CREATE VIEW IF NOT EXISTS unusedIndexes AS SELECT cD1.dkp+1 AS i FROM currentDkp AS cD1 LEFT OUTER JOIN currentDkp AS cD2 ON cD1.dkp+1 = cD2.dkp WHERE cD2.dkp IS NULL")
								
								if confirmed:
									DB.commit()
									dkpDB.commit()
									
								else:
									DB.rollback()
									dkpDB.rollback()
									
								dkpDB.close()
								
								if not confirmed:
									os.remove('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))
									
								req.response.append('Created table: %s' % name)
						
						else:
							req.response.append('Error: A table with name %s already exists' % name)
						
					else:
						req.response.append('Error: Table names cannot contain "_" or "."')
					
				else:
					req.response.append('Syntax Error')
					
			else:
				req.response.append('Syntax Error')
			
			
		else:
			req.response.append('Managing dkp tables must be done as a super user')
	
		DB.close()
		
	return req

# Remove old dkp changes
def bot_dkp_tables_cleanup(dkpDB, currentTransaction):
	rowsOverwritten = 0
	dkpCursor = dkpDB.cursor()
	rowsOverwritten += dkpCursor.execute("DELETE FROM raiders WHERE transactionId>=?", (currentTransaction,)).rowcount
	rowsOverwritten += dkpCursor.execute("DELETE FROM history WHERE transactionId>=?", (currentTransaction,)).rowcount
	
	return rowsOverwritten

# Delete an existing table (a copy is preserved)
def bot_dkp_tables_delete(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp tables remove [-commit] name')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __tables_options__["remove"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp tables remove [-commit] name')
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			confirmed = False
			for n in reversed(range(len(req.argList))):
				if req.argList[n] == "-commit":
					confirmed = True
					del req.argList[n]
			
			if not confirmed:
				req.response.append('Running in test mode (use -commit)')
			
			name = req.argList[0]
			if not "_" in name and not "." in name:
				if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
					cursor.execute("INSERT INTO dkpTransactions VALUES (?,?,?,?,?,?)", (name, 'N/A', req.requester, req.requesterId, "dkp tables remove %s" % (" ".join(req.argList)), datetime.datetime.utcnow().strftime('%c')))
					
					if confirmed:
						bot_dkp_tables_backup('%s_%s' % (riftBot.charName, name))
						os.remove('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))
						
					req.response.append('Deleted table: %s' % name)
					
					if confirmed:
						DB.commit()
						
					else:
						DB.rollback()
					
				else:
					req.response.append('Error: No table with name: %s' % name)
				
			else:
				req.response.append('Error: Tables may not contain the characters: _ or .')
			
		else:
			req.response.append('Managing dkp tables must be done as a super user')
	
	return req

# List existing DKP tables
def bot_dkp_tables_list(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __tables_options__["list"]
		req.response.append(desc)
		req.response.append('Usage: !dkp tables list [-type=?] [-name=?] [-description=?] [name]')
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		nameArgs = []
		dkpQuery = []
		dkpValue = ()
		for arg in req.argList:
			if arg[0] == '-':
				optStr = arg.strip("-").lower()
				
				if '=' in optStr:
					# Table type option
					opt, val = optStr.split("=")
					if opt in ['t', 'type']:
						if val in __dkpSystems__:
							dkpQuery += ["type=?"]
							dkpValue += (val,)
							
						else:
							req.response.append('Unrecognised table type: %s' % val)
							
					# Table description option
					elif opt in ['d', 'desc', 'description']:
						dkpQuery += ["description LIKE ?"]
						dkpValue += ("%%%s%%" % val,)
							
					# Table name option
					elif opt in ['n', 'name']:
						nameArgs += [val]
					
					else:
						req.response.append('Unrecognised option: %s' % arg)
						
				else:
					req.response.append('Unrecognised option: %s' % arg)
					
			else:
				nameArgs += [arg]
		
		if dkpQuery:
			dkpQuery = "SELECT * FROM metadata WHERE %s" % " AND ".join(dkpQuery)
		
		else:
			dkpQuery = "SELECT * FROM metadata"
		
		# Get a list of dkp tables
		dkpTables = os.listdir(dkpDir)
		matchFound = False
		for table in dkpTables:
			# Match table name
			name = table.strip('.db').strip('%s_' % riftBot.charName)
			if all([n in name for n in nameArgs]) and "_DELETED_" not in name:
				# Check metadata for table type and description
				with closing(sqlite3.connect('%s/%s' % (dkpDir, table))) as dkpDB:
					dkpDB.row_factory = sqlite3.Row
					dkpCursor = dkpDB.cursor()
					
					tableData = dkpCursor.execute(dkpQuery, dkpValue).fetchone()
					
					if tableData:
						req.response.append('%s "%s": %s' % (tableData['type'], name, tableData['description']))
						matchFound = True
		
		if not matchFound:
			req.response.append('No tables found')
		
		DB.close()
		
	return req

# Modify an existing table (not yet implemented)
def bot_dkp_tables_modify(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp tables modify [-commit] [-type=?] [-name=?] [-description=?] name')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __tables_options__["modify"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp tables modify [-commit] [-type=?] [-name=?] [-description=?] name')
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		req.response.append('Functionality not yet implemented')
	
		DB.close()
		
	return req

# Roll a table back to a previous transaction
def bot_dkp_tables_rollback(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !su dkp tables rollback [-commit] name transaction')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __tables_options__["rollback"]
		req.response.append(desc)
		req.response.append('Usage: !su dkp tables rollback [-commit] name transaction')
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		# Obviously this'll only work if the user is an admin
		if req.su:
			confirmed = False
			for n in reversed(range(len(req.argList))):
				if req.argList[n] == "-commit":
					confirmed = True
					del req.argList[n]
			
			if not confirmed:
				req.response.append('Running in test mode (use -commit)')
			
			if req.argList > 1:
				name = req.argList[0]
				if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
					toTransaction = -1
					try:
						toTransaction = int(req.argList[1])
					except:
						pass
					
					# Connect to the DKP database
					with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
						dkpDB.row_factory = sqlite3.Row
						dkpCursor = dkpDB.cursor()
						
						# Some error checking
						maxRaiderTrans = dkpCursor.execute("SELECT MAX(transactionId) AS m FROM raiders").fetchone()['m']
						maxHistoryTrans = dkpCursor.execute("SELECT MAX(transactionId) AS m FROM history").fetchone()['m']
						
						if maxRaiderTrans is None or maxHistoryTrans is None:
							maxTransaction = 0
							
						else:
							maxTransaction = max(maxRaiderTrans, maxHistoryTrans)
						
						if toTransaction >= 0 and toTransaction <= maxTransaction:
							# Change the database transaction
							cursor.execute("INSERT INTO dkpTransactions VALUES (?,?,?,?,?,?)", (name, toTransaction, req.requester, req.requesterId, "dkp tables rollback %s" % (" ".join(req.argList)), datetime.datetime.utcnow().strftime('%c')))
							
							dkpCursor.execute("UPDATE metadata SET currentTransaction=?", (toTransaction,))
							
							if confirmed:
								DB.commit()
								dkpDB.commit()
								
							else:
								DB.rollback()
								dkpDB.rollback()
								
							dkpDB.close()
								
							req.response.append('%s rolled back to transaction %i' % (name, toTransaction))
							
						else:
							req.response.append('Error: transaction must be an integer between 0 and %i: %s supplied' % (maxTransaction, req.argList[1]))
				
				else:
					req.response.append('Error: No table with name: %s' % name)
				
			else:
				req.response.append('Syntax Error')
			
		else:
			req.response.append('Managing dkp tables must be done as a super user')
	
	return req

# Query an historic transaction
def bot_dkp_transaction(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __tables_options__["list"]
		req.response.append(desc)
		req.response.append('Usage: !dkp transactions [-player=?] [-id(<,>,=,~)?] [-command=?] [table]')
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		t = bot_dkp_transactions_query(req, DB).fetchone()
		if t:
			req.response.append("%s|%i) %s: %s @ %s" % (t['tableName'], t['transactionId'], t['player'], t['command'], t['timeStamp']))
		
		else:
			req.response.append('No transactions found')
		
		DB.close()
	
	return req

# Query historic transactions
def bot_dkp_transactions(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __tables_options__["list"]
		req.response.append(desc)
		req.response.append('Usage: !dkp transactions [-player=?] [-id(<,>,=,~)?] [-command=?] [table]')
		
	else:
		# Connect to the database
		DB = riftBot.dbConnect()
		cursor = DB.cursor()
		
		transList = bot_dkp_transactions_query(req, DB).fetchall()
		if transList:
			req.response.append(" {0:<6} | {1:<3} | {2} @ {3}".format("table", "ID", "player", "date"))
			for n, t in enumerate(transList):
				req.response.append(" {0:<6} | {1:<3} | {2} @ {3}".format(t['tableName'], t['transactionId'], t['player'], t['timeStamp']))
				
				if n == 4 and len(transList) > 6:
					req.response.append('%i entries truncated' % (len(transList)-n-1))
					break
		
		else:
			req.response.append('No transactions found')
		
		DB.close()
	
	return req

# Perform a query of historic transactions with useful options
def bot_dkp_transactions_query(req, DB):
	cursor = DB.cursor()
	dkpQuery = []
	dkpValue = ()
	for arg in req.argList:
		if arg[0] == '-':
			optStr = arg.strip("-").lower()
			# Options based on id
			if len(optStr) > 3 and optStr[0:2] == 'id':
				try:
					if optStr[2] == '<':
						dkpValue += (int(optStr[3:]),)
						dkpQuery += ["transactionId<?"]
						
					elif optStr[2] == '>':
						dkpValue += (int(optStr[3:]),)
						dkpQuery += ["transactionId>?"]
						
					elif optStr[2] == '=':
						dkpValue += (int(optStr[3:]),)
						dkpQuery += ["transactionId=?"]
						
					elif optStr[2] == '~':
						dkpValue += (int(optStr[3:]),)
						dkpQuery += ["transactionId<>?"]
					
					else:
						req.response.append('Unrecognised id argument')
						
				except ValueError:
					req.response.append('Error: ID given non-integer argument')
			
			elif '=' in optStr:
				# Table type option
				opt, val = optStr.split("=")
				if opt in ['p', 'player']:
					dkpQuery += ["player=?"]
					dkpValue += (val,)
					
				# Table description option
				elif opt in ['c', 'command']:
					dkpQuery += ["command LIKE ?"]
					dkpValue += ("%%%s%%" % val,)
				
				elif opt in ['n', 'name']:
					dkpQuery += ["tableName LIKE ?"]
					dkpValue += ("%%%s%%" % val,)
				
				elif opt in ['t', 'table']:
					dkpQuery += ["tableName LIKE ?"]
					dkpValue += ("%%%s%%" % val,)
				
				else:
					req.response.append('Unrecognised option: %s' % arg)
					
			else:
				req.response.append('Unrecognised option: %s' % arg)
				
		else:
			dkpQuery += ["tableName LIKE ?"]
			dkpValue += ("%%%s%%" % arg,)
	
	if dkpQuery:
		dkpQuery = "SELECT * FROM dkpTransactions WHERE %s LIMIT 100" % " AND ".join(dkpQuery)
	
	else:
		dkpQuery = "SELECT * FROM dkpTransactions LIMIT 100"
	
	return cursor.execute(dkpQuery, dkpValue)

# Determine a winner in a DKP contest
def bot_dkp_winner(riftBot, req):
	if req.argList and req.argList[0] in ['-h', '--help']:
		func, opts, desc = __dkp_options__["winner"]
		req.response.append(desc)
		req.response.append('Usage: !dkp winner table player [player ..]')
		
	else:
		if len(req.argList) > 1:
			name = req.argList[0]
			playersList = [arg.lower() for arg in req.argList[1:]]
			
			if os.path.exists('%s/%s_%s.db' % (dkpDir, riftBot.charName, name)):
				# Load the database
				with closing(sqlite3.connect('%s/%s_%s.db' % (dkpDir, riftBot.charName, name))) as dkpDB:
					dkpDB.row_factory = sqlite3.Row
					dkpCursor = dkpDB.cursor()
					
					# Get all players DKPs
					playersDkp = [None for _ in playersList]
					notInTable = []
					for p in reversed(range(len(playersList))):
						playersRecord = dkpCursor.execute("SELECT * FROM currentDkp WHERE player=?", (playersList[p],)).fetchone()
						if playersRecord:
							playersDkp[p] = playersRecord['dkp']
							
						else:
							notInTable.append(playersList[p])
							del playersList[p]
							del playersDkp[p]
					
					if notInTable:
						req.response.append("%s not in table: %s" % (", ".join([p.title() for p in notInTable]), name))
					
					# Return the winner
					if playersList:
						winnerDkp = None
						winners = []
						for dkp, player in sorted(zip([d for d in playersDkp], playersList), key=lambda p: p[0], reverse=True):
							if dkp >= winnerDkp:
								winnerDkp = dkp
								winners.append(player)
							
							else:
								break
						
						if len(winners) > 1:
							winner = random.choice(winners)
							req.response.append("%s tied with %0.0f dkp, I rolled %s" % (", ".join([p.title() for p in winners]), winnerDkp, winner.title()))
						
						else:
							req.response.append("%s wins with %0.0f dkp" % (winner.title(), dkp))
			
			else:
				req.response.append('Error: No table with name: %s' % name)
		
		else:
			req.response.append('Syntax Error')
	
	return req

# Run on bot startup
def __bot_init__(riftBot):
	DB = riftBot.dbConnect()
	cursor = DB.cursor()
	
	cursor.execute("CREATE TABLE IF NOT EXISTS dkpTransactions (tableName VARCHAR(20), transactionId INT, player VARCHAR(30), playerId VARCHAR(30), command VARCHAR(255), timeStamp VARCHAR(30))")
	
	DB.commit()
	DB.close()
	
	if not os.path.isdir(dkpDir):
		os.mkdir(dkpDir)

__modify_options__ = {
	'add'			: (bot_dkp_modify_add, [], "Change raiders DKP (plain)"),
	'bump'			: (bot_dkp_modify_bump, [], "Move players a few places (suicide)"),
	'reassign'		: (bot_dkp_modify_reassign, [], "Shift dkp from one group of players to another (zerosum)"),
	'suicide'		: (bot_dkp_modify_suicide, [], "Drop players to the bottom of the list (suicide)")
	}

# A list of options for the users subfunctions
__raiders_options__ = {
	'add'		: (bot_dkp_raiders_add, [], "Add raiders to a DKP table"),
	'history'	: (bot_dkp_raiders_history, [], "Show raider's DKP history"),
	'list'		: (bot_dkp_raiders_list, [], "List active raiders in a DKP table"),
	'purge'		: (bot_dkp_raiders_purge, [], "Remove raiders from all DKP tables"),
	'remove'	: (bot_dkp_raiders_remove, [], "Remove raiders from a DKP table"),
	'total'		: (bot_dkp_raiders_total, [], "Show raiders current total DKP")
	}

# A list of options for the tables subfunctions
__tables_options__ = {
	'create'	: (bot_dkp_tables_create, [], "Create a new DKP table"),
	'delete'	: (bot_dkp_tables_delete, [], "Remove a DKP table (irreversible)"),
	'list'		: (bot_dkp_tables_list, [], "List existing DKP tables"),
	'modify'	: (bot_dkp_tables_modify, [], "Modify an existing DKP table (irreversible)"),
	'rollback'	: (bot_dkp_tables_rollback, [], "Revert a table to a previous state")
	}

# A list of options for the dkp functions
__dkp_options__ = {
	'modify'		: (bot_dkp_modify, __modify_options__, "Manage raiders DKP"),
	'raiders'		: (bot_dkp_raiders, __raiders_options__, "Manage active raider roster"),
	'tables'		: (bot_dkp_tables, __tables_options__, "Manage DKP tables"),
	'transaction'	: (bot_dkp_transaction, [], "Detail a historic DKP transaction"),
	'transactions'	: (bot_dkp_transactions, [], "List historical DKP transactions"),
	'winner'		: (bot_dkp_winner, [], "Determine the winner of a DKP contest")
	}

# A list of functions contained in this module, format: (function, options, description)
__botFunctions__ = {
	'dkp'	: (bot_dkp, __dkp_options__, "Manage DKP")
	}
	