import socket
import requests
import json
from contextlib import closing

import sqlite3
import xml.sax.saxutils as saxy
import shlex

defaultLocale = 'eu'

class DatabaseError(Exception):
	pass
	
class TimerError(Exception):
	pass

# A dumb class for storing information about the request
class riftChatRequest:
	def __init__(self):
		self.fromGuild = False
		self.fromWhisp = False
		self.toGuild = False
		self.toWhisp = False
		self.su = False
		self.requester = ""
		self.requesterId = ""
		self.message = ""
		self.argList = ""
		self.response = []
	
class riftChatBot:
	def __init__(self, locale=defaultLocale):
		self.authURL = 'https://auth.trionworlds.com:443'
		self.chatURL = 'https://chat-%s.riftgame.com:443' % locale
		self.charName = ""
		self.charID = ""
		self.ticket = None
		self.cookie = None
		self.timers = {}
		self.resolve_function = None
		self.su = False
		
	def __del__(self):
		if self.timers:
			for timerId in self.timers:
				self.timers[timerId].cancel()
		
	def login(self, username, password, charName):
		# Log in to the authorisation server
		print 'Logging in to auth server...'
		authLoginResp = requests.post('%s/auth' % self.authURL, data={'username':username, 'password':password, 'channel':1})

		if authLoginResp.status_code != 200:
			print authLoginResp.text
			return 1

		self.ticket = authLoginResp.content

		# Use the ticket to log into the chat server
		print 'Logging in to chat server...'
		# This is where some kind of server timeout occurs (not sure why) so catch the exception
		try:
			verResp = requests.get('%s/chatservice/versionCheck' % self.chatURL, params={'version':'MAIN-108-55-A-569292'})
			if verResp.json()['status'] == 'failure':
				print 'Server has ended support for this version'
				return 2
		except requests.exceptions.ConnectionError:
			return 3

		chatLoginResp = requests.post('%s/chatservice/loginByTicket' % self.chatURL, data={'ticket':self.ticket})
		self.cookie = chatLoginResp.cookies

		# Log into the chosen character
		print 'Selecting character...'
		charsResp = requests.get('%s/chatservice/chat/characters' % self.chatURL, cookies=self.cookie)
		
		if charsResp.status_code != 200:
			print charsResp.text
			return 4
		
		charList = charsResp.json()['data']
		
		# Find accurate information about the player character
		self.charName = charName
		self.charID = ''
		for char in charList:
			if char['name'].lower() == self.charName:
				self.charID = char['playerId']
				break
			elif char['playerId'] == self.charName:
				self.charID = char['playerId']
				self.charName = char['name'].lower()
				break

		if self.charID == '':
			print 'Character: %s not found' % self.charName
			print 'Try specifying your locale (eu/us) as a fourth argument'
			return 5
		
		# Login to the character
		selCharResp = requests.get('%s/chatservice/chat/selectCharacter' % self.chatURL, params={'characterId':self.charID}, cookies=self.cookie)

		if selCharResp.status_code != 200:
			print 'Login failed'
			print selCharResp.text
			return 6
		
		return 0
		
	def getRequest(self):
		try:
			with closing(requests.get('%s/chatservice/servlet/chatlisten' % self.chatURL, cookies=self.cookie, headers={'User-Agent':'trion/mobile', 'Accept-Encoding':'', 'Cookie2':'$Version=1'}, stream=True)) as chatStream:
				buffer = ''
				table = None
				for character in chatStream.iter_content(1):
					# See if we now have a complete message by attempting to parse it
					buffer += character
					try:
						table = json.loads(buffer)
					except ValueError:
						pass
						
					# Return it if we do
					if table:
						if (table['type'] == 'GuildChat' or table['type'] == 'WhisperChat') and table['value']['message'][0] == '!':
							# Populate a request object
							req = riftChatRequest()
							req.fromGuild = table['type'] == 'GuildChat'
							req.fromWhisp = table['type'] == 'WhisperChat'
							req.message = saxy.unescape(table['value']['message'][1:], {"&apos;":"'", "&quot;":'"'})
							req.requester = table['value']['senderName'].lower()
							req.requesterId = table['value']['senderId']
							
							# By default output to the requester
							req.toGuild = req.fromGuild
							req.toWhisp = req.fromWhisp
							
							return req
							
						else:
							table = None
							buffer = ''
						
		# Catch timeouts
		except socket.error:
			return None
			
		return req
		
	def guildMessages(self):
		guildResp = requests.get('%s/chatservice/guild/listChat' % self.chatURL, params={'characterId':self.charID}, cookies=self.cookie)
		return guildResp.json()['data']
		
	def listFriends(self):
		friendsResp = requests.get('%s/chatservice/internal/friendsAndGuild' % self.chatURL, params={'v':1, 'characterId':self.charID}, cookies=self.cookie)
		return friendsResp.json()['data']['friend']
		
	def listGuild(self):
		guildResp = requests.get('%s/chatservice/internal/friendsAndGuild' % self.chatURL, params={'v':1, 'characterId':self.charID}, cookies=self.cookie)
		return guildResp.json()['data']['guild']
		
	def listFriendsAndGuild(self):
		fAndGResp = requests.get('%s/chatservice/internal/friendsAndGuild' % self.chatURL, params={'v':1, 'characterId':self.charID}, cookies=self.cookie)
		return fAndGResp.json()['data']['friends'] + fAndGResp.json()['data']['guild']
			
	def sendResponse(self, req):
		for message in req.response:
			if req.toGuild:
				self.sendGuild(message)
			if req.toWhisp:
				self.sendPlayer(message, req.requesterId)
		
	def sendGuild(self, message):
		sendChatResp = requests.get('%s/chatservice/guild/addChat' % self.chatURL, cookies=self.cookie, headers={'User-Agent':'trion/mobile','Accept-Encoding':'', 'Cookie2':'$Version=1'}, params={'characterId':self.charID, 'message':message})
		if sendChatResp.status_code != 200:
			print "Failed to send chat message\n"
			print sendChatResp.text + '\n'
			
	def sendPlayer(self, message, recipient):
		sendWhispResp = requests.get('%s/chatservice/chat/whisper' % self.chatURL, cookies=self.cookie, headers={'User-Agent':'trion/mobile', 'Accept-Encoding':'', 'Cookie2':'$Version=1'}, params={'senderId':self.charID, 'recipientId':recipient, 'message':message})
		if sendWhispResp.status_code != 200:
			print "Failed to send whisper\n"
			print sendWhispResp.text + '\n'
		
	def dbConnect(self):
		DB = sqlite3.connect(self.charName + '.db')
		DB.row_factory = sqlite3.Row
		return DB
			
	def appendTimer(self, timerId, timer):
		timerAdded = False
		try:
			if self.timers[timerId]:
				pass
		
		except KeyError:
			self.timers[timerId] = timer
			timerAdded = True
		
		return timerAdded
				
	def removeTimer(self, timerId):
		timerRemoved = False
		try:
			self.timers[timerId].cancel()
			del self.timers[timerId]
			timerRemoved = True
			
		except KeyError:
			pass
			
		except AttributeError:
			pass
		
		return timerRemoved
