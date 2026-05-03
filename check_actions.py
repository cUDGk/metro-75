import sqlite3, sys
db = sys.argv[1]
c = sqlite3.connect(db)
print('=== Sample actions (10) ===')
for r in c.execute("SELECT sim_time, agent, content FROM memory WHERE kind='action' ORDER BY ts LIMIT 10").fetchall():
    print(r[:2], '/', r[2][:80])
print('=== Last actions ===')
for r in c.execute("SELECT sim_time, agent, content FROM memory WHERE kind='action' ORDER BY ts DESC LIMIT 5").fetchall():
    print(r[:2], '/', r[2][:80])
print('=== Action sim_time distribution ===')
for r in c.execute("SELECT sim_time, COUNT(*) FROM memory WHERE kind='action' GROUP BY sim_time ORDER BY sim_time LIMIT 20").fetchall():
    print(r)
print('=== Digest contents (3) ===')
for r in c.execute("SELECT sim_time, agent, content FROM memory WHERE kind='digest' ORDER BY ts LIMIT 3").fetchall():
    print(r[0], '/', r[1])
    print('  ', r[2][:200])
