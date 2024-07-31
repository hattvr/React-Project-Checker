import json
import os
import subprocess
import time
import signal

from selenium import webdriver
from datetime import datetime
from selenium import webdriver

class NodeServer:
    def __init__(self, path):
        self.path = path
        self.process = None
    
    def start(self):
        self.process = subprocess.Popen(['npm', 'start'], cwd=self.path, preexec_fn=os.setsid)
        time.sleep(10)
    
    def stop(self):
        if self.process:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.wait()

options = webdriver.ChromeOptions()
options.add_argument("start-maximized")
options.add_argument("disable-infobars")
options.add_argument("disable-extensions")
options.add_argument("--headless")

driver = webdriver.Chrome(options=options)

repositories = json.load(open('repos.json'))
for index, repo in enumerate(repositories, start=1):
    print(f"[{index}] Checking {repo['name']} [{repo['url']}]")

    if not os.path.exists(repo['name']):
        os.system(f"mkdir '{repo['name']}'")
        os.system(f"cd '{repo['name']}' && git clone {repo['url']}")
    else:
        os.system(f"cd '{repo['name']}/{repo['url'].split('/')[-1]}' && git reset --hard")
        os.system(f"cd '{repo['name']}/{repo['url'].split('/')[-1]}' && git pull")

    with open(f"{repo['name']}/{repo['url'].split('/')[-1]}/package.json") as f:
        package_json = json.load(f)
        package_json['scripts']['start'] = "BROWSER=none react-scripts start"
    
    with open(f"{repo['name']}/{repo['url'].split('/')[-1]}/package.json", "w") as f:
        json.dump(package_json, f, indent=4)

    subprocess.run(["npm", "install"], cwd=f"{repo['name']}/{repo['url'].split('/')[-1]}")

    server_process = NodeServer(f"{repo['name']}/{repo['url'].split('/')[-1]}")
    server_process.start()
    
    driver.get("http://localhost:3000")
    time.sleep(10)
    
    os.makedirs(f"screenshots/{repo['name']}", exist_ok=True)
    driver.save_screenshot(f"screenshots/{repo['name']}/{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.png")
    print(f"Screenshot saved for {repo['name']}")

    server_process.stop()