#!/usr/bin/env python3
"""
Server Runner for Amazon Job Poller
Handles background service management, monitoring, and control
"""

import os
import sys
import json
import time
import signal
import subprocess
import argparse
from datetime import datetime
from typing import Optional

class ServerManager:
    def __init__(self, config_path: str = "server_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.pid_file = self.config['service']['pid_file']
        
    def load_config(self) -> dict:
        """Load server configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Config file {self.config_path} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in config file: {e}")
            sys.exit(1)
            
    def is_running(self) -> Optional[int]:
        """Check if the service is already running"""
        if not os.path.exists(self.pid_file):
            return None
            
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
                
            # Check if process is actually running
            os.kill(pid, 0)  # This will raise OSError if process doesn't exist
            return pid
        except (OSError, ValueError):
            # Process not running, remove stale PID file
            try:
                os.remove(self.pid_file)
            except OSError:
                pass
            return None
            
    def start_service(self, foreground: bool = False):
        """Start the polling service"""
        # Check if already running
        existing_pid = self.is_running()
        if existing_pid:
            print(f"⚠️  Service is already running (PID: {existing_pid})")
            return
            
        print("🚀 Starting Amazon Job Poller service...")
        
        if foreground:
            # Run in foreground
            cmd = [sys.executable, "simple_poller.py", "--config", self.config_path]
            subprocess.run(cmd)
        else:
            # Run in background
            cmd = [sys.executable, "simple_poller.py", "--config", self.config_path, "--daemon"]
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Write PID file
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
                
            print(f"✅ Service started successfully (PID: {process.pid})")
            print(f"📝 Logs: {self.config['logging']['general_log']}")
            print(f"📊 Success log: {self.config['logging']['success_log']}")
            print(f"❌ Error log: {self.config['logging']['error_log']}")
            
    def stop_service(self):
        """Stop the polling service"""
        pid = self.is_running()
        if not pid:
            print("⚠️  Service is not running")
            return
            
        print(f"🛑 Stopping service (PID: {pid})...")
        
        try:
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to stop
            for _ in range(10):  # Wait up to 10 seconds
                try:
                    os.kill(pid, 0)
                    time.sleep(1)
                except OSError:
                    break
            else:
                # Force kill if it didn't stop gracefully
                print("⚠️  Process didn't stop gracefully, force killing...")
                os.kill(pid, signal.SIGKILL)
                
            # Remove PID file
            try:
                os.remove(self.pid_file)
            except OSError:
                pass
                
            print("✅ Service stopped successfully")
            
        except OSError as e:
            print(f"❌ Error stopping service: {e}")
            
    def restart_service(self):
        """Restart the polling service"""
        print("🔄 Restarting service...")
        self.stop_service()
        time.sleep(2)
        self.start_service()
        
    def status(self):
        """Show service status"""
        pid = self.is_running()
        
        print("📊 Amazon Job Poller Status")
        print("=" * 40)
        
        if pid:
            print(f"Status: ✅ RUNNING (PID: {pid})")
            
            # Show log file info
            logs = self.config['logging']
            for log_type, log_file in logs.items():
                if log_type.endswith('_log') and os.path.exists(log_file):
                    stat = os.stat(log_file)
                    size = stat.st_size
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    print(f"{log_type}: {log_file} ({size} bytes, modified: {modified})")
                    
            # Show recent bookings if available
            success_log = logs.get('success_log')
            if success_log and os.path.exists(success_log):
                try:
                    with open(success_log, 'r') as f:
                        bookings = json.load(f)
                    print(f"📈 Total successful bookings: {len(bookings)}")
                    if bookings:
                        latest = bookings[-1]
                        print(f"🕐 Latest booking: {latest['timestamp']}")
                except Exception:
                    pass
        else:
            print("Status: ❌ NOT RUNNING")
            
        print("\nConfiguration:")
        print(f"  Polling interval: {self.config['polling_settings']['interval_seconds']}s")
        print(f"  Auto-booking: {self.config['polling_settings']['auto_book']}")
        print(f"  Allowed locations: {len(self.config['location_filter']['allowed_locations'])}")
        
    def tail_logs(self, log_type: str = "general", lines: int = 20):
        """Show recent log entries"""
        log_files = {
            'general': self.config['logging']['general_log'],
            'error': self.config['logging']['error_log'],
            'success': self.config['logging']['success_log']
        }
        
        log_file = log_files.get(log_type)
        if not log_file or not os.path.exists(log_file):
            print(f"❌ Log file not found: {log_file}")
            return
            
        print(f"📄 Last {lines} lines from {log_file}:")
        print("=" * 60)
        
        try:
            if log_file.endswith('.json'):
                # Handle JSON log files
                with open(log_file, 'r') as f:
                    data = json.load(f)
                    for entry in data[-lines:]:
                        print(f"[{entry.get('timestamp', 'unknown')}] {entry}")
            else:
                # Handle text log files
                subprocess.run(['tail', '-n', str(lines), log_file])
        except Exception as e:
            print(f"❌ Error reading log file: {e}")

def main():
    parser = argparse.ArgumentParser(description='Amazon Job Poller Server Manager')
    parser.add_argument('--config', default='server_config.json',
                       help='Path to configuration file')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start the service')
    start_parser.add_argument('--foreground', action='store_true',
                             help='Run in foreground (not as daemon)')
    
    # Stop command
    subparsers.add_parser('stop', help='Stop the service')
    
    # Restart command
    subparsers.add_parser('restart', help='Restart the service')
    
    # Status command
    subparsers.add_parser('status', help='Show service status')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Show recent logs')
    logs_parser.add_argument('--type', choices=['general', 'error', 'success'],
                            default='general', help='Type of log to show')
    logs_parser.add_argument('--lines', type=int, default=20,
                            help='Number of lines to show')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    # Create server manager
    manager = ServerManager(args.config)
    
    # Execute command
    if args.command == 'start':
        manager.start_service(foreground=args.foreground)
    elif args.command == 'stop':
        manager.stop_service()
    elif args.command == 'restart':
        manager.restart_service()
    elif args.command == 'status':
        manager.status()
    elif args.command == 'logs':
        manager.tail_logs(args.type, args.lines)

if __name__ == "__main__":
    main()
