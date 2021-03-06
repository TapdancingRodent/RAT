import sys
import sqlite3

# Add a sudoer to the specified database
# Usage:
# $> python addAdmin bot_name.db Sardines
if len(sys.argv) != 3:
	sys.exit('Please supply a database and player name')

dbName = sys.argv[1]
sudoer = sys.argv[2].lower()

DB = sqlite3.connect(dbName)
c = DB.cursor()

c.execute("INSERT INTO admins (player) VALUES (?)", (sudoer,))
print "%s added" % sudoer
DB.commit()
DB.close()
 