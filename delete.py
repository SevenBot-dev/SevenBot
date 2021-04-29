import os
import sys
for o in os.listdir("./cogs"):
    if not o.endswith(".py"):
        continue
    with open("./cogs/" + o, "r", encoding="utf8") as f:
        b = f.read().splitlines()
        for i, c in enumerate(list(b)):
            if sys.argv[1] in c:
                b[i] = "# " + c
    with open("./cogs/" + o, "w", encoding="utf8") as f:
        f.write("\n".join(b) + "\n")
