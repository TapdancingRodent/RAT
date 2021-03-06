import riftChatBotUtils
import os
import sqlite3
from contextlib import closing

__item_options_str__ = 'Options: -[~]crafted -[~]usable -id=? -class=? -slot=? -rarity=? -binding=? -level(<,>,=,~)?'

# Search for an item in the database
def bot_item(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !item [options] [~]name')
		req.response.append(__item_options_str__)
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["item"]
		req.response.append(desc)
		req.response.append('Usage: !item [options] [~]name')
		req.response.append(__item_options_str__)
	
	else:
		# Load the items database
		if os.path.isfile('discoveries.db'):
			with closing(sqlite3.connect('discoveries.db')) as itemsDB:
				itemsDB.row_factory = sqlite3.Row
				
				# Get a list of matching items
				cursor = bot_items_query(req, itemsDB)
				ItemKey = cursor.fetchone()
				
				if ItemKey:
					ItemKey = ItemKey['ItemKey']
				
					# Get full information on the first item found
					cursor.execute("SELECT * FROM Items WHERE ItemKey=?", (ItemKey,))
					item = cursor.fetchone()
					
					req.response.append(item['Name'])
					
					# Collect item tags
					tagsList = []
					if item['Rarity']:
						tagsList += [item['Rarity']]
					if item['Craftable'] == 1:
						tagsList += ["Crafted"]
					if item['Binding']:
						tagsList += [item['Binding']]
					if item['ArmorType']:
						tagsList += [item['ArmorType']]
					if item['Slot']:
						tagsList += [item['Slot']]
					if item['RequiredLevel']:
						tagsList += ["Level %i" % item['RequiredLevel']]
					
					# Check required callings
					if item['CallingRequired'] == 1:
						cursor.execute("SELECT * FROM ItemCallings WHERE ItemKey=?", (ItemKey,))
						callings = cursor.fetchone()
						if callings['Warrior'] == 1:
							tagsList += ["Warrior"]
						if callings['Cleric'] == 1:
							tagsList += ["Cleric"]
						if callings['Rogue'] == 1:
							tagsList += ["Rogue"]
						if callings['Mage'] == 1:
							tagsList += ["Mage"]
						
					tags = ", ".join(tagsList)
					if tags:
						req.response.append(tags)
					
					# List the item's stats
					cursor.execute("SELECT * FROM ItemStats WHERE ItemKey=?", (ItemKey,))
					stats = cursor.fetchall()
					
					statsList = []
					if item['Armor']:
						statsList += ["Armor %i" % item['Armor']]
					for stat in stats:
						# This catches a weird corner case of stats having a string value
						if type(stat['StatValue']) == type(0):
							statsList += ["%s %i" % (stat['Stat'], stat['StatValue'])]
					
					if stats:
						req.response.append(", ".join([s for s in sorted(statsList)]))
					
					if item['OnUse']:
						req.response.append("Use: %s" % item['OnUse'])
					
					if item['OnEquip']:
						req.response.append("Passive: %s" % item['OnEquip'])
					
					# Look up item set information (Gilded Battle Gear etc)
					if item['SetId']:
						req.response.append("Set: %s" % item['SetName'])
						if item['GivesSetBonus']:
							cursor.execute("SELECT * FROM ItemSets WHERE ItemKey=?", (ItemKey,))
							bonuses = cursor.fetchall()
							for bonus in bonuses:
								req.response.append("%i: %s" % (bonus['Pieces'], bonus['Bonus']))
						
				else:
					req.response.append('No items found')
		
		else:
			req.response.append('Items database not found')
			
	return req

# Search for a number of items in the items database
def bot_items(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !items [options] [~]name')
		req.response.append(__item_options_str__)
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["items"]
		req.response.append(desc)
		req.response.append('Usage: !items [options] [~]name')
		req.response.append(__item_options_str__)
		
	
	else:
		# Load the items database
		if os.path.isfile('discoveries.db'):
			with closing(sqlite3.connect('discoveries.db')) as itemsDB:
				itemsDB.row_factory = sqlite3.Row
				
				# Get a list of matching items and append them to the response list
				itemList = bot_items_query(req, itemsDB).fetchall()
				if itemList:
					for n, item in enumerate(itemList):
						req.response.append(item['Name'])
						if n == 2 and len(itemList) > 4:
							req.response.append('%i entries truncated' % (len(itemList)-n-1))
							break
						
				else:
					req.response.append('No items found')
			
		else:
			req.response.append('Items database not found')
			
	return req

# Look up items in an items database using extended search options
def bot_items_query(req, itemsDB):
	cursor = itemsDB.cursor()
	
	itemQuery = []
	itemValue = ()
	for arg in req.argList:
		if arg[0] == '-':
			optStr = arg.strip("-").lower()
			
			# Options based on level requirements
			if len(optStr) > 6 and optStr[0:5] == 'level':
				try:
					if optStr[5] == '<':
						itemValue += (int(optStr[6:]),)
						itemQuery += ["RequiredLevel<?"]
						
					elif optStr[5] == '>':
						itemValue += (int(optStr[6:]),)
						itemQuery += ["RequiredLevel>?"]
						
					elif optStr[5] == '=':
						itemValue += (int(optStr[6:]),)
						itemQuery += ["RequiredLevel=?"]
						
					elif optStr[5] == '~':
						itemValue += (int(optStr[6:]),)
						itemQuery += ["RequiredLevel<>?"]
					
					else:
						req.response.append('Unrecognised level argument')
						
				except ValueError:
					req.response.append('Error: Level given non-integer argument')
			
			elif '=' in optStr:
				# Class requirement options
				opt, val = optStr.split("=")
				if opt in ['c', 'class']:
					if val in ['w', 'warrior']:
						itemQuery += ["(CallingRequired=0 OR Warrior=1)"]
					
					elif val in ['c', 'cleric']:
						itemQuery += ["(CallingRequired=0 OR Cleric=1)"]
						
					elif val in ['r', 'rogue']:
						itemQuery += ["(CallingRequired=0 OR Rogue=1)"]
						
					elif val in ['m', 'mage']:
						itemQuery += ["(CallingRequired=0 OR Mage=1)"]
				
				# Other extended options
				elif opt in ['u', 'usable']:
					itemQuery += ["OnUse IS NOT NULL"]
				
				elif opt in ['~u', '~usable']:
					itemQuery += ["OnUse IS NULL"]
				
				elif opt in ['s', 'slot']:
					itemQuery += ["Slot LIKE ?"]
					itemValue += ("%%%s%%" % val,)
				
				elif opt in ['~s', '~slot']:
					itemQuery += ["Slot NOT LIKE ?"]
					itemValue += ("%%%s%%" % val,)
				
				elif opt in ['b', 'binding']:
					itemQuery += ["Binding LIKE ?"]
					itemValue += ("%%%s%%" % val,)
				
				elif opt in ['~b', '~binding']:
					itemQuery += ["Binding NOT LIKE ?"]
					itemValue += ("%%%s%%" % val,)
				
				elif opt in ['r', 'rarity']:
					itemQuery += ["Rarity=? COLLATE NOCASE"]
					itemValue += (val,)
					
				elif opt in ['i', 'id']:
					itemQuery += ["itemKey LIKE ?"]
					itemValue += ("%%%s%%" % val,)
					
				elif opt in ['~i', '~id']:
					itemQuery += ["itemKey NOT LIKE ?"]
					itemValue += ("%%%s%%" % val,)
				
			elif optStr in ['c', 'crafted']:
				itemQuery += ["Craftable=?"]
				itemValue += (1,)
					
			elif optStr in ['~c', '~crafted']:
				itemQuery += ["Craftable=?"]
				itemValue += (0,)
				
			else:
				req.response.append('Unrecognised option: %s' % arg)
				
		else:
		
			# Pure string matching options
			if arg[0] == '~':
				itemQuery += ["Name NOT LIKE ?"]
				itemValue += ("%%%s%%" % arg[1:],)
				
			else:
				itemQuery += ["Name LIKE ?"]
				itemValue += ("%%%s%%" % arg,)
			
	if itemQuery:
		itemQuery = "SELECT ItemKey, Name FROM Items LEFT JOIN ItemCallings USING (ItemKey) WHERE %s LIMIT 100" % " AND ".join(itemQuery)
	
	else:
		itemQuery = "SELECT ItemKey, Name FROM Items LEFT JOIN ItemCallings USING (ItemKey) LIMIT 100"
	
	return cursor.execute(itemQuery, itemValue)

# Look up a recipe in the items database
def bot_recipe(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !recipe [~]name')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["recipe"]
		req.response.append(desc)
		req.response.append('Usage: !recipe [~]name')
	
	else:
		# Load the items database
		if os.path.isfile('discoveries.db'):
			with closing(sqlite3.connect('discoveries.db')) as recipesDB:
				recipesDB.row_factory = sqlite3.Row
				
				# Get a list of matching recipes
				cursor = bot_recipes_query(req, recipesDB)
				RecipeKey = cursor.fetchone()
				if RecipeKey:
					RecipeKey = RecipeKey['RecipeKey']
				
					# Get full information on the first recipe found
					cursor.execute("SELECT * FROM Recipes WHERE RecipeKey=?", (RecipeKey,))
					recipe = cursor.fetchone()
					ItemKey = recipe['ItemKey']
					
					req.response.append("Recipe: %s (%i %s)" % (recipe['Name'], recipe['RequiredSkillPoints'], recipe['RequiredSkill']))
					
					# Collect ingredients
					cursor.execute("SELECT * FROM Ingredients WHERE RecipeKey=?", (RecipeKey,))
					ingredients = cursor.fetchall()
					req.response.append(", ".join(["%i %s" % (ingr['Quantity'], ingr['Name']) for ingr in ingredients]))
					
					cursor.execute("SELECT Name FROM Items WHERE ItemKey=?", (ItemKey,))
					req.response.append("Creates: %s %s" % (str(recipe['Quantity']), cursor.fetchone()['Name']))
					
				else:
					req.response.append('No recipes found')
		
		else:
			req.response.append('Recipes database not found')
		
	return req

# Look up a number of recipes in the items database
def bot_recipes(riftBot, req):
	if not req.argList:
		req.response.append('Usage: !recipe [~]name')
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["recipes"]
		req.response.append(desc)
		req.response.append('Usage: !recipes [~]name')
	
	else:
		# Load the items database
		if os.path.isfile('discoveries.db'):
			with closing(sqlite3.connect('discoveries.db')) as recipesDB:
				recipesDB.row_factory = sqlite3.Row
				
				# Get a list of matching recipes
				recipeList = bot_recipes_query(req, recipesDB).fetchall()
				if recipeList:
					# Output them
					for n, recipe in enumerate(recipeList):
						req.response.append(recipe['Name'])
						if n == 2 and len(recipeList) > 4:
							req.response.append('%i entries truncated' % (len(recipeList)-n-1))
							break
						
				else:
					req.response.append('No recipes found')
		else:
			req.response.append('Recipes database not found')
			
	return req
	
# Look up recipes in a recipes database using an extended set of options
def bot_recipes_query(req, recipesDB):
	cursor = recipesDB.cursor()
	
	recipeQuery = []
	recipeValue = ()
	for arg in req.argList:
		# Pure string matching options
		if arg[0] == '~':
			recipeQuery += ["Name NOT LIKE ?"]
			recipeValue += ("%%%s%%" % arg[1:],)
		else:
			recipeQuery += ["Name LIKE ?"]
			recipeValue += ("%%%s%%" % arg,)
			
	if recipeQuery:
		recipeQuery = "SELECT RecipeKey, Name FROM Recipes WHERE %s LIMIT 100" % " AND ".join(recipeQuery)
	else:
		recipeQuery = "SELECT RecipeKey, Name FROM Recipes LIMIT 100"
	
	return cursor.execute(recipeQuery, recipeValue)

# Run on bot startup
def __bot_init__(riftBot):
	pass

# A list of functions contained in this module, format: (function, options, description)
__botFunctions__ = {
	'item'		: (bot_item, [], "Get information about an item"),
	'items'		: (bot_items, [], "Get infromation about items"),
	'recipe'	: (bot_recipe, [], "Get information about a recipe"),
	'recipes'	: (bot_recipes, [], "Get information about recipes")
	}
