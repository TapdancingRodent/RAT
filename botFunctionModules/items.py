import riftChatBotUtils
import os
import sqlite3
from contextlib import closing

__item_options_str__ = 'Options: -[~]crafted -[~]usable -id=? -class=? -slot=? -rarity=? -binding=? -level(<,>,=,~)?'

# Search for an item in the database
def bot_item(riftBot, req):
	if not req.argList:
		req.response += ['Usage: !item [options] [~]name']
		req.response += [__item_options_str__]
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["item"]
		req.response += [desc]
		req.response += ['Usage: !item [options] [~]name']
		req.response += [__item_options_str__]
	
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
					
					req.response += [item['Name']]
					
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
						req.response += [tags]
					
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
						req.response += [", ".join([s for s in sorted(statsList)])]
						
					if item['OnUse']:
						req.response += ["Use: %s" % item['OnUse']]
					
					# Look up item set information (Gilded Battle Gear etc)
					if item['SetId']:
						req.response += ["Set: %s" % item['SetName']]
						if item['GivesSetBonus']:
							cursor.execute("SELECT * FROM ItemSets WHERE ItemKey=?", (ItemKey,))
							bonuses = cursor.fetchall()
							for bonus in bonuses:
								req.response += ["%i: %s" % (bonus['Pieces'], bonus['Bonus'])]
						
				else:
					req.response += ['No items found']
		
		else:
			req.response += ['Items database not found']
			
	return req

# Search for a number of items in the items database
def bot_items(riftBot, req):
	if not req.argList:
		req.response += ['Usage: !items [options] [~]name']
		req.response += [__item_options_str__]
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["items"]
		req.response += [desc]
		req.response += ['Usage: !items [options] [~]name']
		req.response += [__item_options_str__]
		
	
	else:
		# Load the items database
		if os.path.isfile('discoveries.db'):
			with closing(sqlite3.connect('discoveries.db')) as itemsDB:
				itemsDB.row_factory = sqlite3.Row
				
				# Get a list of matching items and append them to the response list
				itemList = bot_items_query(req, itemsDB).fetchall()
				if itemList:
					for n, item in enumerate(itemList):
						req.response += [item['Name']]
						if n == 2 and len(itemList) > 4:
							req.response += ['%i entries truncated' % (len(itemList)-n-1)]
							break
						
				else:
					req.response += ['No items found']
			
		else:
			req.response += ['Items database not found']
			
	return req

# Look up items in an items database (used by bot_item and bot_items)
def bot_items_query(req, itemsDB):
	cursor = itemsDB.cursor()
	
	itemQuery = []
	itemValue = ()
	for arg in req.argList:
		if arg[0] == '-':
			optStr = arg.strip("-").lower()
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
						req.response += ['Unrecognised level argument']
						
				except ValueError:
					req.response += ['Error: Level given non-integer argument']
			
			elif '=' in optStr:
				opt, val = optStr.split("=")
				if opt in 'class':
					if val in 'warrior':
						itemQuery += ["(CallingRequired=0 OR Warrior=1)"]
					
					elif val in 'cleric':
						itemQuery += ["(CallingRequired=0 OR Cleric=1)"]
						
					elif val in 'rogue':
						itemQuery += ["(CallingRequired=0 OR Rogue=1)"]
						
					elif val in 'mage':
						itemQuery += ["(CallingRequired=0 OR Mage=1)"]
				
				elif opt in 'usable':
					itemQuery += ["OnUse IS NOT NULL"]
				
				elif opt in '~usable':
					itemQuery += ["OnUse IS NULL"]
				
				elif opt in 'slot':
					itemQuery += ["Slot LIKE ?"]
					itemValue += ("%%%s%%" % val,)
				
				elif opt in '~slot':
					itemQuery += ["Slot NOT LIKE ?"]
					itemValue += ("%%%s%%" % val,)
				
				elif opt in 'binding':
					itemQuery += ["Binding LIKE ?"]
					itemValue += ("%%%s%%" % val,)
				
				elif opt in '~binding':
					itemQuery += ["Binding NOT LIKE ?"]
					itemValue += ("%%%s%%" % val,)
				
				elif opt in 'rarity':
					itemQuery += ["Rarity=? COLLATE NOCASE"]
					itemValue += (val,)
					
				elif opt in 'id':
					itemQuery += ["itemKey LIKE ?"]
					itemValue += ("%%%s%%" % val,)
					
				elif opt in '~id':
					itemQuery += ["itemKey NOT LIKE ?"]
					itemValue += ("%%%s%%" % val,)
				
			elif optStr in 'crafted':
				itemQuery += ["Craftable=?"]
				itemValue += (1,)
					
			elif optStr in '~crafted':
				itemQuery += ["Craftable=?"]
				itemValue += (0,)
				
			else:
				req.response += ['Unrecognised option: %s' % arg]
				
		else:
		
			if arg[0] == '~':
				itemQuery += ["Name NOT LIKE ?"]
				itemValue += ("%%%s%%" % arg[1:],)
				
			else:
				itemQuery += ["Name LIKE ?"]
				itemValue += ("%%%s%%" % arg,)
			
	itemQuery = "SELECT Items.ItemKey AS ItemKey, Name FROM Items LEFT JOIN ItemCallings ON Items.ItemKey=ItemCallings.ItemKey WHERE %s LIMIT 100" % " AND ".join(itemQuery)
	
	return cursor.execute(itemQuery, itemValue)

# Look up a recipe in the items database
def bot_recipe(riftBot, req):
	if not req.argList:
		req.response += ['Usage: !recipe [-]name']
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["recipe"]
		req.response += [desc]
		req.response += ['Usage: !recipe [-]name']
	
	else:
		req.toGuild = req.fromGuild
		req.toWhisp = req.fromWhisp
		
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
					
					req.response += ["Recipe: %s (%i %s)" % (recipe['Name'], recipe['RequiredSkillPoints'], recipe['RequiredSkill'])]
					
					# Collect ingredients
					cursor.execute("SELECT * FROM Ingredients WHERE RecipeKey=?", (RecipeKey,))
					ingredients = cursor.fetchall()
					req.response += [", ".join(["%i %s" % (ingr['Quantity'], ingr['Name']) for ingr in ingredients])]
					
					cursor.execute("SELECT Name FROM Items WHERE ItemKey=?", (ItemKey,))
					req.response += ["Creates: %s %s" % (str(recipe['Quantity']), cursor.fetchone()['Name'])]
					
				else:
					req.response += ['No recipes found']
		
		else:
			req.response += ['Recipes database not found']
		
	return req

# Look up a number of recipes in the items database
def bot_recipes(riftBot, req):
	if not req.argList:
		req.response += ['Usage: !recipe [~]name']
		
	elif req.argList[0] in ['-h', '--help']:
		func, opts, desc = __botFunctions__["recipes"]
		req.response += [desc]
		req.response += ['Usage: !recipes [~]name']
	
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
						req.response += [recipe['Name']]
						if n == 2 and len(recipeList) > 4:
							req.response += ['%i entries truncated' % (len(recipeList)-n-1)]
							break
						
				else:
					req.response += ['No recipes found']
		else:
			req.response += ['Recipes database not found']
			
	return req
	
# Look up recipes in an items database (used by bot_recipe and bot_recipes)
def bot_recipes_query(req, recipesDB):
	cursor = recipesDB.cursor()
	
	recipeQuery = []
	recipeValue = ()
	for arg in req.argList:
		if arg[0] == '~':
			recipeQuery += ["Name NOT LIKE ?"]
			recipeValue += ("%%%s%%" % arg[1:],)
		else:
			recipeQuery += ["Name LIKE ?"]
			recipeValue += ("%%%s%%" % arg,)
			
	recipeQuery = "SELECT RecipeKey, Name FROM Recipes WHERE %s LIMIT 100 COLLATE NOCASE" % " AND ".join(recipeQuery)
	
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
