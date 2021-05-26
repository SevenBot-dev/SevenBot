import time
import subprocess

cmd = "python3.9 main.py"
p = subprocess.Popen("exec " + cmd, shell=True)

while True:
    res = subprocess.run("git pull origin main --dry-run".split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if "main.py" in res.stdout:
        p.kill()
        res = subprocess.run("git pull origin main".split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        p = subprocess.Popen("exec " + cmd, shell=True)
    elif "origin/" in res.stdout:
        subprocess.run("git pull origin main".split(), stdout=subprocess.DEVNULL)
    time.sleep(10)
