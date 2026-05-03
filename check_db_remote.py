import sqlite3, sys
db = sys.argv[1]
c = sqlite3.connect(db)
print(c.execute('SELECT MAX(sim_time), COUNT(*) FROM memory').fetchone())
for r in c.execute('SELECT kind, COUNT(*) FROM memory GROUP BY kind').fetchall():
    print(r)
