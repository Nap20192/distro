import sys
import re

for line in sys.stdin:
    line = re.sub(r'[^\w\s]', '', line.lower())
    words = line.split()
    for word in words:
        print(f"{word}\t1")
