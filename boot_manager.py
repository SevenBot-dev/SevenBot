import os
import subprocess
import sys
import time

if sys.platform == "win32":
    cmd = "python main.py"
else:
    cmd = "exec python3.9 main.py"
p = subprocess.Popen(cmd, shell=True)

while True:
    res = subprocess.run(
        "git pull origin main --dry-run".split(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if "main.py" in res.stdout:
        p.kill()
        res = subprocess.run(
            "git pull origin main".split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        p = subprocess.Popen(cmd, shell=True)
    elif "origin/" in res.stdout:
        subprocess.run(
            "git pull origin main".split(), stdout=subprocess.DEVNULL
        )
    elif os.path.exists("./reboot"):
        os.remove("./reboot")
        p.kill()
        p = subprocess.Popen(cmd, shell=True)
    elif os.path.exists("./shutdown"):
        os.remove("./shutdown")
        p.kill()
        break
    time.sleep(10)
