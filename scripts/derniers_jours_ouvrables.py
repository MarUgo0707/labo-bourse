"""Affiche les N derniers jours ouvrables avant aujourd'hui (utile aux tests). Usage : python scripts/derniers_jours_ouvrables.py 2"""
import datetime as dt
import sys

n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
d, jours = dt.date.today(), []
while len(jours) < n:
    d -= dt.timedelta(days=1)
    if d.weekday() < 5:
        jours.append(d.isoformat())
print(" ".join(reversed(jours)))
