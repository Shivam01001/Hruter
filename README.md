# Hruter - Smart Brute Force Tool v1.1

A powerful Python tool designed for Kali Linux to perform brute force attacks while evading detection through automatic IP rotation and randomized timing.

## Features

- **Automatic Proxy Scraping**: Fetches 400+ free proxies automatically from public sources—no proxy file needed!
- **Timed IP Rotation**: Configurable intervals to switch IPs during the attack to bypass rate-limiting.
- **Dual Wordlist Support**: Brute force multiple usernames and passwords simultaneously.
- **User-Agent Rotation**: Mimics different browsers to avoid fingerprinting.
- **Randomized Delay**: Mimics human behavior with adjustable random timing between requests.
- **Smart Result Detection**: Automatically identifies successful logins based on redirects or HTTP status codes.

## Installation

After extracting the tool from GitHub, navigate to the directory and run the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

This will install the necessary dependencies (`requests`, `urllib3`) and link the tool to your system path.

## Usage

### 1. Terminal Mode (Standard CLI)

To start an attack with **automatic IP rotation every 60 seconds**:

```bash
# Single Username
python3 hruter.py --url https://example.com/login -u admin -w passwords.txt -r 60

# Multiple Usernames (Wordlist)
python3 hruter.py --url https://example.com/login -U usernames.txt -w passwords.txt -r 30 -t 5
```

### 2. Interactive Mode

Follow the on-screen prompts for easy configuration:

```bash
python3 hruter.py --cli
```

### Argument Flags

| Flag | Description |
| --- | --- |
| `--url` | The target login page URL |
| `-u` | Single target username |
| `-U` | Path to username wordlist file |
| `-w` | Path to password wordlist file |
| `-r` | **IP Rotation Interval** in seconds (e.g., `60`) |
| `-t` | Number of concurrent threads (default: `3`) |
| `-c` | Load configuration from a JSON file |

## Output

- **Logs**: Every attempt is recorded in `bruteforce.log`.
- **Success**: Valid credentials are saved to `successful_credentials.json` and displayed in the terminal.

## Disclaimer

This tool is for **authorized security testing and educational purposes only**. Testing systems without explicit permission is illegal. Use responsibly.
