#!/usr/bin/env python3
"""
Simplified Amazon Job Poller for Server Deployment
- Polls jobs based on location filter
- Books shifts automatically using existing graphql_client.py
- Logs successes and failures
- Runs as background service
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import signal

# Import local graphql_client
from graphql_client import AmazonGraphQLClient

class SimpleJobPoller:
    def __init__(self, config_path: str = "server_config.json"):
        """Initialize the simple job poller with configuration"""
        self.config_path = config_path
        self.config = self.load_config()
        self.setup_logging()
        
        # Initialize GraphQL client with auth token
        self.client = AmazonGraphQLClient(self.config['auth_token'])
        
        # Runtime state
        self.running = False
        self.stats = {
            'total_polls': 0,
            'jobs_found': 0,
            'booking_attempts': 0,
            'successful_bookings': 0,
            'failed_bookings': 0,
            'start_time': None
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Config file {self.config_path} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            sys.exit(1)
            
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config['logging']['log_level'], logging.INFO)
        
        # Configure main logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['logging']['general_log']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup error logger
        self.error_logger = logging.getLogger('errors')
        error_handler = logging.FileHandler(self.config['logging']['error_log'])
        error_handler.setFormatter(logging.Formatter('%(asctime)s - ERROR - %(message)s'))
        self.error_logger.addHandler(error_handler)
        self.error_logger.setLevel(logging.ERROR)
        
        # Setup job discovery logger
        self.job_logger = logging.getLogger('job_discoveries')
        job_handler = logging.FileHandler('job_discoveries.log')
        job_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.job_logger.addHandler(job_handler)
        self.job_logger.setLevel(logging.INFO)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def filter_jobs_by_location(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter jobs based on location configuration"""
        if not self.config['location_filter']['enabled']:
            return jobs
            
        allowed_locations = self.config['location_filter']['allowed_locations']
        filtered_jobs = []
        
        for job in jobs:
            job_location = job.get('location', {}).get('city', '')
            if any(allowed_loc.lower() in job_location.lower() for allowed_loc in allowed_locations):
                filtered_jobs.append(job)
                
        return filtered_jobs
        
    def log_successful_booking(self, job: Dict[str, Any], booking_result: Dict[str, Any]):
        """Log successful booking to JSON file"""
        success_data = {
            'timestamp': datetime.now().isoformat(),
            'job_id': job.get('jobId', 'unknown'),
            'location': job.get('location', {}),
            'shift_details': job.get('shift', {}),
            'booking_result': booking_result,
            'stats': self.stats.copy()
        }
        
        # Append to success log file
        success_log_path = self.config['logging']['success_log']
        try:
            # Read existing data
            if os.path.exists(success_log_path):
                with open(success_log_path, 'r') as f:
                    existing_data = json.load(f)
            else:
                existing_data = []
                
            # Append new booking
            existing_data.append(success_data)
            
            # Write back to file
            with open(success_log_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
            self.logger.info(f"✅ Booking logged successfully: {job.get('jobId', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Failed to log successful booking: {e}")
            
    def log_booking_error(self, job: Dict[str, Any], error: str):
        """Log booking error"""
        error_msg = f"BOOKING FAILED - Job ID: {job.get('jobId', 'unknown')} | Location: {job.get('location', {}).get('city', 'unknown')} | Error: {error}"
        self.error_logger.error(error_msg)
        
    def log_job_discoveries(self, jobs: List[Dict[str, Any]], filtered_jobs: List[Dict[str, Any]]):
        """Log job discoveries to file"""
        timestamp = datetime.now().isoformat()
        
        # Log summary
        self.job_logger.info(f"POLL RESULT - Found {len(jobs)} total jobs, {len(filtered_jobs)} in allowed locations")
        
        # Log all found jobs
        if jobs:
            for i, job in enumerate(jobs, 1):
                job_info = {
                    'job_number': i,
                    'job_id': job.get('jobId', 'No ID'),
                    'schedule_id': job.get('scheduleId', 'No Schedule'),
                    'title': job.get('title', 'Unknown Job'),
                    'location': job.get('location', {}).get('city', 'Unknown'),
                    'address': job.get('location', {}).get('address', 'Unknown'),
                    'available_slots': job.get('available_slots', 'Unknown'),
                    'schedule_name': job.get('schedule_name', 'Unknown'),
                    'pay_rate': job.get('pay_rate', 'Unknown'),
                    'start_time': job.get('start_time', 'Unknown'),
                    'end_time': job.get('end_time', 'Unknown')
                }
                
                job_line = f"JOB {i}: {job_info['title']} | ID: {job_info['job_id']} | Schedule: {job_info['schedule_id']} | Location: {job_info['location']} | Address: {job_info['address']} | Slots: {job_info['available_slots']} | Pay: {job_info['pay_rate']} | Time: {job_info['start_time']}-{job_info['end_time']}"
                self.job_logger.info(job_line)
        
        # Log filtered jobs (ones that match location criteria)
        if filtered_jobs:
            self.job_logger.info(f"FILTERED JOBS ({len(filtered_jobs)} match location criteria):")
            for i, job in enumerate(filtered_jobs, 1):
                job_id = job.get('jobId', 'No ID')
                title = job.get('title', 'Unknown Job')
                location = job.get('location', {}).get('city', 'Unknown')
                self.job_logger.info(f"  MATCH {i}: {title} in {location} (ID: {job_id})")
        else:
            self.job_logger.info("NO JOBS MATCH LOCATION FILTER")
            
        # Add separator for readability
        self.job_logger.info("-" * 80)
        
    async def attempt_booking(self, job: Dict[str, Any]) -> bool:
        """Attempt to book a job shift"""
        try:
            self.stats['booking_attempts'] += 1
            
            # Extract job details
            job_id = job.get('jobId')
            if not job_id:
                raise Exception("No job ID found")
                
            self.logger.info(f"🎯 Attempting to book job: {job_id}")
            
            # Extract schedule_id from job data
            schedule_id = job.get('scheduleId')
            if not schedule_id:
                raise Exception("No schedule ID found in job data")
                
            # Use the existing GraphQL client to create application
            # This uses the same method as the original rapid_poller.py
            booking_success = await self.client.create_application_api(
                job_id=job_id,
                schedule_id=schedule_id,
                candidate_id=self.config['candidate_id']
            )
            
            if booking_success:
                self.stats['successful_bookings'] += 1
                booking_result = {
                    'success': True,
                    'job_id': job_id,
                    'schedule_id': schedule_id,
                    'timestamp': datetime.now().isoformat()
                }
                self.log_successful_booking(job, booking_result)
                self.logger.info(f"✅ Successfully booked job: {job_id}")
                return True
            else:
                error_msg = "Failed to create application via API"
                self.stats['failed_bookings'] += 1
                self.log_booking_error(job, error_msg)
                return False
                
        except Exception as e:
            self.stats['failed_bookings'] += 1
            self.log_booking_error(job, str(e))
            self.logger.error(f"❌ Booking failed for job {job.get('jobId', 'unknown')}: {e}")
            return False
            
    async def poll_and_book_jobs(self):
        """Main polling loop - polls jobs and books them"""
        self.logger.info("🚀 Starting job polling and booking service...")
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        coords = self.config['location_filter']['coordinates']
        interval = self.config['polling_settings']['interval_seconds']
        
        while self.running:
            try:
                self.stats['total_polls'] += 1
                
                # Fetch jobs using existing GraphQL client
                jobs = await self.client.get_available_shifts(
                    lat=coords['lat'],
                    lng=coords['lng'],
                    distance=coords['distance_km']
                )
                
                if jobs:
                    self.stats['jobs_found'] += len(jobs)
                    self.logger.info(f"🔍 Found {len(jobs)} total jobs from GraphQL API")
                    
                    # Filter jobs by location
                    filtered_jobs = self.filter_jobs_by_location(jobs)
                    
                    # Log job discoveries to file
                    self.log_job_discoveries(jobs, filtered_jobs)
                    
                    if filtered_jobs:
                        self.logger.info(f"📍 {len(filtered_jobs)} jobs match allowed locations (filtered from {len(jobs)} total)")
                        
                        # Attempt to book each job (if auto_book is enabled)
                        if self.config['polling_settings']['auto_book']:
                            self.logger.info(f"🎯 Starting booking attempts for {len(filtered_jobs)} jobs...")
                            for job in filtered_jobs:
                                if not self.running:  # Check if we should stop
                                    break
                                    
                                await self.attempt_booking(job)
                                
                                # Small delay between bookings
                                await asyncio.sleep(0.1)
                        else:
                            self.logger.info(f"⏸️  Auto-booking disabled, found {len(filtered_jobs)} bookable jobs")
                    else:
                        self.logger.info(f"❌ No jobs found in allowed locations (checked {len(jobs)} jobs)")
                else:
                    # Log when no jobs are found at all
                    if self.stats['total_polls'] % 50 == 0:  # Log every 50 polls when no jobs
                        self.logger.info(f"🔍 No jobs available (poll #{self.stats['total_polls']})")
                        self.job_logger.info(f"NO JOBS AVAILABLE - Poll #{self.stats['total_polls']}")
                    
                # Log stats periodically
                if self.stats['total_polls'] % 100 == 0:
                    self.log_stats()
                    
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}")
                self.error_logger.error(f"POLLING ERROR: {e}")
                
            # Wait before next poll
            await asyncio.sleep(interval)
            
        self.logger.info("🛑 Polling service stopped")
        
    def log_stats(self):
        """Log current statistics"""
        runtime = datetime.now() - self.stats['start_time'] if self.stats['start_time'] else 0
        self.logger.info(f"📊 Stats - Polls: {self.stats['total_polls']} | "
                        f"Jobs Found: {self.stats['jobs_found']} | "
                        f"Bookings: {self.stats['successful_bookings']}/{self.stats['booking_attempts']} | "
                        f"Runtime: {runtime}")
                        
    async def run(self):
        """Run the poller service"""
        try:
            await self.poll_and_book_jobs()
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            self.error_logger.error(f"FATAL ERROR: {e}")
        finally:
            self.log_stats()
            self.logger.info("Service shutdown complete")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Amazon Job Poller')
    parser.add_argument('--config', default='server_config.json', 
                       help='Path to configuration file')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon process')
    
    args = parser.parse_args()
    
    # Create poller instance
    poller = SimpleJobPoller(args.config)
    
    if args.daemon:
        # Run as daemon (background process)
        import daemon
        import daemon.pidfile
        
        pid_file = poller.config['service']['pid_file']
        
        with daemon.DaemonContext(
            pidfile=daemon.pidfile.TimeoutPIDLockFile(pid_file),
            working_directory=os.getcwd(),
            umask=0o002,
        ):
            asyncio.run(poller.run())
    else:
        # Run in foreground
        asyncio.run(poller.run())

if __name__ == "__main__":
    main()
