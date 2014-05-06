import sys, zipfile, os
import ftplib
import xml.etree.ElementTree as ET
import sqlite3

# Unzipping method courtesy of Stack Overflow's phihag
def unzip(source_filename, dest_dir):
    with zipfile.ZipFile(source_filename) as zf:
        for member in zf.infolist():
            # Path traversal defense copied from
            # http://hg.python.org/cpython/file/tip/Lib/http/server.py#l789
            words = member.filename.split('/')
            path = dest_dir
            for word in words[:-1]:
                drive, word = os.path.splitdrive(word)
                head, word = os.path.split(word)
                if word in (os.curdir, os.pardir, ''): continue
                path = os.path.join(path, word)
            zf.extract(member, path)

# Set to local language
language = 'English'
if not language in {'English', 'French', 'German'}:
	sys.exit('Invalid language specified')

# Check if there is a new database available and download it
print 'Connecting to trion database...'
trionServer = ftplib.FTP('ftp.trionworlds.com')
trionServer.login()
trionServer.cwd('/rift/data')
files = trionServer.nlst()
for fileName in files:
	if "Rift_Discoveries_" in fileName:
		break
		
if os.path.isfile('./oldRepo'):
	with open("./oldRepo", 'r+') as oldRepo:
		for line in oldRepo:
			if line == fileName:
				print 'Local database is up to date'
				sys.exit()

print 'Downloading %s...' % fileName
repo = open(fileName, 'wb+')
trionServer.retrbinary('RETR %s' % fileName, repo.write)
repo.close()

print 'Extracting discoveries...'
unzip('./%s' % fileName, './')

# Open a local database and initialise the tables
db = sqlite3.connect('tmp.db')
db.row_factory = sqlite3.Row
cursor = db.cursor()

print 'Parsing items...'
cursor.execute("DROP TABLE IF EXISTS Items")
cursor.execute("DROP TABLE IF EXISTS ItemStats")
cursor.execute("DROP TABLE IF EXISTS ItemCallings")
cursor.execute("DROP TABLE IF EXISTS ItemSets")

cursor.execute("CREATE TABLE Items (ItemKey VARCHAR(30) PRIMARY KEY, Name VARCHAR(50), Slot VARCHAR(20), ArmorType VARCHAR(25), Armor INT, Cooldown INT, OnUse VARCHAR(50), RequiredLevel INT, Rarity VARCHAR(10), Binding VARCHAR(20), CallingRequired INT DEFAULT 0, SetId INT, SetName VARCHAR(30), GivesSetBonus INT, Craftable INT DEFAULT 0)")
cursor.execute("CREATE TABLE ItemStats (ItemKey VARCHAR(30), Stat VARCHAR(50), StatValue INT)")
cursor.execute("CREATE TABLE ItemCallings (ItemKey VARCHAR(30) PRIMARY KEY, Warrior INT, Cleric INT, Rogue INT, Mage INT)")
cursor.execute("CREATE TABLE ItemSets (ItemKey VARCHAR(30), Pieces INT, Bonus VARCHAR(50))")
db.commit()

# Process the Items discoveries xml file
xmlTree = ET.iterparse('./Items.xml', events=("start", "end"))
xmlTree = iter(xmlTree)
event, Items = xmlTree.next()

for event, item in xmlTree:
	if event == "end" and item.tag == "Item":
		if item.find('ItemKey') is None:
			continue
		
		# Ignore crafted items with augments
		if item.find('IsAugmented').text == 1 or item.find('IsAugmented').text == "True":
			continue
		
		ItemKey = item.find('ItemKey').text
		itemQuery = "INSERT INTO Items (ItemKey"
		itemValue = (ItemKey,)
			
		print 'Parsing ' + ItemKey + '...'
		
		# Get a bunch of useful (but not always present) information
		if item.find('Armor') is not None:
			itemQuery += ", Armor"
			itemValue += (item.find('Armor').text,)
			
		if item.find('ArmorType') is not None:
			itemQuery += ", ArmorType"
			itemValue += (item.find('ArmorType').text,)
			
		if item.find('Binding') is not None:
			itemQuery += ", Binding"
			itemValue += (item.find('Binding').text,)
		elif item.find('AccountBound') is not None:
			itemQuery += ", Binding"
			itemValue += (item.find('AccountBound').text,)
		
		if item.find('RequiredCallings') is not None:
			itemQuery += ", CallingRequired"
			itemValue += (1,)
		
			WarriorUsable, ClericUsable, RogueUsable, MageUsable = [0 for _ in range(1,5)]
			for calling in item.find('RequiredCallings').findall('Calling'):
				if calling.text == "Warrior":
					WarriorUsable = 1
				elif calling.text == "Cleric":
					ClericUsable = 1
				elif calling.text == "Rogue":
					RogueUsable = 1
				elif calling.text == "Mage":
					MageUsable = 1
			cursor.execute("INSERT INTO ItemCallings VALUES (?,?,?,?,?)", (ItemKey, WarriorUsable, ClericUsable, RogueUsable, MageUsable))
			
		if item.find('Cooldown') is not None:
			itemQuery += ", Cooldown"
			itemValue += (int(round(float(item.find('Cooldown').text))),)
			
		if item.find('ItemSet') is not None:
			SetId = item.find('ItemSet').find('FamilyId').text
			SetName = item.find('ItemSet').find('FamilyName').find(language).text
			itemQuery += ", SetId, SetName"
			itemValue += (SetId, SetName)
			
			if item.find('ItemSet').find('Bonuses') is not None:
				itemQuery += ", GivesSetBonus"
				itemValue += (1,)
				for entry in item.find('ItemSet').find('Bonuses').findall('Bonus'):
					pieces = entry.find('RequiredPieces').text
					bonus = entry.find('Description').find('English').text
					cursor.execute("INSERT INTO ItemSets VALUES (?,?,?)", (ItemKey, pieces, bonus))
			
		if item.find('Name') is not None and item.find('Name').find(language) is not None:
			itemQuery += ", Name"
			itemValue += (item.find('Name').find(language).text,)
			
		if item.find('OnEquip') is not None:
			for stat in item.find('OnEquip')._children:
				cursor.execute("INSERT INTO ItemStats VALUES (?,?,?)", (ItemKey, stat.tag, stat.text))
			
		if item.find('OnUse') is not None:
			if item.find('OnUse').find('Ability') is not None:
				itemQuery += ", OnUse"
				itemValue += (item.find('OnUse').find('Ability').find(language).text,)
			elif item.find('OnUse').find('Tooltip') is not None:
				itemQuery += ", OnUse"
				itemValue += (item.find('OnUse').find('Tooltip').find(language).text,)
			
		if item.find('Rarity') is not None:
			itemQuery += ", Rarity"
			itemValue += (item.find('Rarity').text,)
			
		if item.find('RequiredLevel') is not None:
			itemQuery += ", RequiredLevel"
			itemValue += (item.find('RequiredLevel').text,)
			
		if item.find('Slot') is not None:
			itemQuery += ", Slot"
			itemValue += (item.find('Slot').text,)
			
		# Write a new row to the database
		itemQuery += ") VALUES (?" + ",?".join(['' for _ in range(1, len(itemValue)+1)]) + ")"
		cursor.execute(itemQuery, itemValue)
		
		# Cull the parse tree to prevent it ballooning in memory
		Items.clear()

print 'Parsing recipes...'
# Initialise the tables
cursor.execute("DROP TABLE IF EXISTS Recipes")
cursor.execute("DROP TABLE IF EXISTS Ingredients")

cursor.execute("CREATE TABLE Recipes (RecipeKey VARCHAR(30) PRIMARY KEY, Name VARCHAR(50), ItemKey VARCHAR(30), Quantity INT, RequiredSkill VARCHAR(20), RequiredSkillPoints INT)")
cursor.execute("CREATE TABLE Ingredients (RecipeKey VARCHAR(30), ItemKey VARCHAR(30), Name VARCHAR(50), Quantity INT)")
db.commit()

# Process the Recipes discoveries xml file
xmlTree = ET.iterparse('./Recipes.xml', events=("start", "end"))
xmlTree = iter(xmlTree)
event, Recipes = xmlTree.next()

for event, recipe in xmlTree:
	if event == "end" and recipe.tag == "Recipe":
		if recipe.find('Id') is None:
			continue
			
		RecipeKey = recipe.find('Id').text
		print 'Parsing ' + RecipeKey + '...'
		
		# Read the information
		ItemKey = recipe.find("Creates").find("Item").find("ItemKey").text
		cursor.execute("UPDATE Items SET Craftable=1 WHERE ItemKey=?", (ItemKey,))
		
		Quantity = recipe.find("Creates").find("Item").find("Quantity").text
		Name = recipe.find("Name").find(language).text
		recipeQuery = "INSERT INTO Recipes (RecipeKey, ItemKey, Quantity, Name"
		recipeValue = (RecipeKey, ItemKey, Quantity, Name)
		
		if recipe.find('Ingredients') is not None:
			for ingredient in recipe.find('Ingredients').findall('Item'):
				ItemKey = ingredient.find('ItemKey').text
				Quantity = ingredient.find('Quantity').text
				cursor.execute("SELECT Name FROM Items WHERE ItemKey=?", (ItemKey,))
				Name = cursor.fetchone()['Name']
				cursor.execute("INSERT INTO Ingredients VALUES (?,?,?,?)", (RecipeKey, ItemKey, Name, Quantity))
			
		if recipe.find('RequiredSkill') is not None:
			recipeQuery += ", RequiredSkill"
			recipeValue += (recipe.find('RequiredSkill').text,)
			
		if recipe.find('RequiredSkillPoints') is not None:
			recipeQuery += ", RequiredSkillPoints"
			recipeValue += (recipe.find('RequiredSkillPoints').text,)
			
		recipeQuery += ") VALUES (?" + ",?".join(['' for _ in range(1, len(recipeValue)+1)]) + ")"
		cursor.execute(recipeQuery, recipeValue)
		
		# Cull the parse tree to prevent it ballooning in memory
		Recipes.clear()

# Write to the HDD
db.commit()
db.close()

# Remember that we've updated the database
with open("./oldRepo", 'w+') as oldRepo:
	oldRepo.write(fileName)

os.remove('./%s' % fileName)

# Swap out the old database for the new
if os.path.exists('discoveries.db'):
	oldDBinUse = True
	while oldDBinUse:
		try:
			os.remove('discoveries.db')
			oldDBinUse = False
		except WindowsError:
			pass

os.rename('./tmp.db', './discoveries.db')
