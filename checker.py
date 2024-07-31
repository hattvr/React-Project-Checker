import json
import os
import subprocess
import time
import signal
import platform

from selenium import webdriver
from datetime import datetime
from selenium import webdriver

class NodeServer:
    def __init__(self, path):
        self.path = path
        self.process = None
    
    def start(self):
        self.process = subprocess.Popen(
            ['npm', 'start'], 
            cwd=self.path, 
            shell=True if os_is_windows else False,
            preexec_fn=os.setsid if not os_is_windows else None
        )
        
        time.sleep(10)
    
    def stop(self):
        if os_is_windows:
            subprocess.run(["taskkill", "/f", "/im", "node.exe"], shell=True)
        else:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            
def find_react_project(path: str):
    for root, dirs, _ in os.walk(path):
        if "src" in dirs:
            return root

    return None

options = webdriver.ChromeOptions()
options.add_argument("start-maximized")
options.add_argument("disable-infobars")
options.add_argument("disable-extensions")
options.add_argument("--headless")

driver = webdriver.Chrome(options=options)
os_is_windows: bool = platform.system() == "Windows"

repositories = json.load(open('repos.json'))
for index, repo in enumerate(repositories, start=1):    
    print(f"[{index}] Checking {repo['name']} [{repo['url']}]")
    if repo['url'] is None:
        print(f"[{index}] Skipping {repo['name']} as URL is not provided")
        continue

    directory_name = repo['name'].replace(" ", "-").lower()
    
    if not os.path.exists(directory_name):
        os.system(f"mkdir {directory_name}")
        os.system(f"cd {directory_name} && git clone {repo['url']}")
    else:
        os.system(f"cd {directory_name}/{repo['url'].split('/')[-1]} && git reset --hard")
        os.system(f"cd {directory_name}/{repo['url'].split('/')[-1]} && git pull")

    project_path = find_react_project(f"{directory_name}/{repo['url'].split('/')[-1]}")
    
    pkg_fp = f"{project_path}/package.json"
    with open(pkg_fp, "r") as f:
        package_json = json.load(f)

    if os_is_windows:
        package_json['scripts']['start'] = "cross-env BROWSER=none react-scripts start"
    else:
        package_json['scripts']['start'] = "BROWSER=none react-scripts start"

    with open(pkg_fp, "w") as f:
        json.dump(package_json, f, indent=4)

    install_operations = ["npm", "install"]
    if os_is_windows:
        install_operations.append("--save")
        install_operations.append("cross-env")

    subprocess.run(
        args=install_operations,
        cwd=project_path,
        shell=True if os_is_windows else False
    )

    server_process = NodeServer(project_path)
    server_process.start()
    
    driver.get("http://localhost:3000")
    time.sleep(5)
    
    os.makedirs(f"screenshots/{directory_name}", exist_ok=True)
    driver.save_screenshot(f"screenshots/{directory_name}/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png")
    print(f"Screenshot saved for {repo['name']}")

    server_process.stop()