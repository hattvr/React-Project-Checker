import json
import os
import subprocess
import time
import signal
import platform

from selenium import webdriver
from datetime import datetime
from selenium import webdriver

errored_repos = []

class NodeServer:
    def __init__(self, path, vite_project=False):
        self.path = path
        self.vite_project = vite_project
        self.process = None
    
    def start(self):
        self.process = subprocess.Popen(
            ['npm', 'run', 'dev'] 
            if self.vite_project else
            ['npm', 'start'], 
            cwd=self.path, 
            shell=True if os_is_windows else False,
            preexec_fn=os.setsid if not os_is_windows else None
        )
        
        time.sleep(5)
    
    def stop(self):
        if os_is_windows:
            subprocess.run(
                args=["taskkill", "/f", "/t", "/pid", str(self.process.pid)],
                shell=True,
            )
        else:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            
def find_react_project(path: str):
    for root, dirs, _ in os.walk(path):
        if "node_modules" in dirs:
            dirs.remove("node_modules")
        if "src" in dirs:
            return root

    return None

options = webdriver.ChromeOptions()
options.add_argument("start-maximized")
options.add_argument("disable-infobars")
options.add_argument("disable-extensions")
options.add_argument("--disable-notifications")
options.add_argument("--log-level=3")
options.add_argument("--headless")

driver = webdriver.Chrome(options=options)
os_is_windows: bool = platform.system() == "Windows"

subprocess.run(
    args=["npm", "install"],
    cwd="back-end-rest-server/",
    shell=True if os_is_windows else False
)

back_end_server = subprocess.Popen(
    args=["npm", "run", "start"],
    cwd="back-end-rest-server/",
    shell=True if os_is_windows else False,
    preexec_fn=os.setsid if not os_is_windows else None
)

repositories = json.load(open('repos.json'))
for index, repo in enumerate(repositories, start=1):
    print(f"[{index}] Checking {repo['name']} [{repo['url']}]")
    if repo['url'] is None:
        print(f"[{index}] Skipping {repo['name']} as URL is not provided")
        continue
    
    nickname = repo['name'].replace(" ", "-").lower()
    directory_path = f"repositories/{nickname}"    
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        os.system(f"cd {directory_path} && git clone {repo['url']}")
    else:
        os.system(f"cd {directory_path}/{repo['url'].split('/')[-1]} && git reset --hard")
        os.system(f"cd {directory_path}/{repo['url'].split('/')[-1]} && git pull")

    project_path = find_react_project(f"{directory_path}/{repo['url'].split('/')[-1]}")
    if project_path is None:
        print(f"[{index}] Skipping {repo['name']} as React project not found")
        continue
    
    print(f"Project Path: {project_path}")
    
    try:
        pkg_fp = f"{project_path}/package.json"
        with open(pkg_fp, "r") as f:
            package_json = json.load(f)
            
        is_vite_project = bool("devDependencies" in package_json and "vite" in package_json["devDependencies"])
        script_command = "vite" if is_vite_project else "react-scripts start"
        env_command = "cross-env " if os_is_windows else ""
        package_json['scripts']['dev' if is_vite_project else 'start'] = f"{env_command}BROWSER=none {script_command}"
        package_json['dependencies']['react-scripts'] = "5.0.1"

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

        server_process = NodeServer(project_path, is_vite_project)
        server_process.start()
        
        driver.get(f"http://localhost:{'5173' if is_vite_project else '3000'}")
        time.sleep(5)
        
        os.makedirs(f"screenshots/{nickname}", exist_ok=True)
        driver.save_screenshot(f"screenshots/{nickname}/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png")
        print(f"Screenshot saved for {repo['name']}")

        server_process.stop()
    except Exception as e:
        print(f"[{index}] Error occurred while checking {repo['name']}: {e}")
        errored_repos.append(repo['name'])
        continue
        
driver.quit()
print(f"\033[92mSnapshotted {len(repositories) - len(errored_repos)} repositories successfully\033[0m")
print(f"\033[91mErrored Repositories: {errored_repos}\033[0m")
        
