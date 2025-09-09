import requests
import json
import time
import asyncio
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AmazonGraphQLClient:
    def __init__(self, auth_token: str = None):
        # Real Amazon GraphQL endpoint from the provided file
        self.base_url = "https://e5mquma77feepi2bdn4d6h3mpu.appsync-api.us-east-1.amazonaws.com/graphql"
        
        # Headers from the actual Amazon request
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.6',
            'authorization': auth_token or 'Bearer Status|logged-in|Session|eyJhbGciOiJLTVMiLCJ0eXAiOiJKV1QifQ.eyJpYXQiOjE3NTcyNzcxNzksImV4cCI6MTc1NzI4MDc3OX0.AQICAHidzPmCkg52ERUUfDIMwcDZBDzd+C71CJf6w0t6dq2uqwFdEC2XbnFskdWznsBJLDkBAAAAtDCBsQYJKoZIhvcNAQcGoIGjMIGgAgEAMIGaBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDIKBh/a2HxvTCmcHBwIBEIBt6/o4XZAF7z+/kj6IeWJoqpI4vKuUR5LgPlll075tLpxqA8di7vj3hXmWOYZLqff9+LPlRAIl1f7ON4hS0gIpHTWxG9+0pFk4OC+Ef/mJK8bOOPFJV3ni5U93EywsNMpTb1070kKjSuh12Y8Qww==',
            'content-type': 'application/json',
            'country': 'Canada',
            'dnt': '1',
            'iscanary': 'false',
            'origin': 'https://hiring.amazon.ca',
            'priority': 'u=1, i',
            'referer': 'https://hiring.amazon.ca/',
            'sec-ch-ua': '"Not;A=Brand";v="99", "Brave";v="139", "Chromium";v="139"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36'
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Cache for tracking changes
        self.last_jobs = []
        self.last_check = 0
    
    def fetch_job_cards(self, lat: float = None, lng: float = None, distance: int = 100) -> List[Dict[str, Any]]:
        """Fetch available warehouse jobs using the real Amazon GraphQL API
        
        Args:
            lat: Latitude for geographic search (None for Canada-wide search)
            lng: Longitude for geographic search (None for Canada-wide search) 
            distance: Distance in km from lat/lng (ignored if lat/lng are None)
        """
        
        # Real GraphQL query from the provided file
        query = """query searchJobCardsByLocation($searchJobRequest: SearchJobRequest!) {
  searchJobCardsByLocation(searchJobRequest: $searchJobRequest) {
    nextToken
    jobCards {
      jobId
      jobTitle
      jobType
      employmentType
      city
      state
      postalCode
      locationName
      __typename
    }
    __typename
  }
}"""
        
        # Build the search request - conditionally include geoQueryClause
        search_request = {
            "locale": "en-CA",
            "country": "Canada",
            "pageSize": 100,
            "dateFilters": [
                {
                    "key": "firstDayOnSite",
                    "range": {
                        "startDate": datetime.now().strftime("%Y-%m-%d")
                    }
                }
            ]
        }
        
        # Only add geographic constraints if lat/lng are provided
        if lat is not None and lng is not None:
            search_request["geoQueryClause"] = {
                "lat": lat,
                "lng": lng,
                "unit": "km",
                "distance": distance
            }
            logger.info(f"Searching within {distance}km of coordinates ({lat}, {lng})")
        else:
            logger.info("Searching across all of Canada (no geographic constraints)")
        
        variables = {
            "searchJobRequest": search_request
        }
        
        try:
            response = self.session.post(
                self.base_url,
                json={
                    "operationName": "searchJobCardsByLocation",
                    "variables": variables,
                    "query": query
                },
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and 'searchJobCardsByLocation' in data['data']:
                job_cards = data['data']['searchJobCardsByLocation']['jobCards']
                logger.info(f"Fetched {len(job_cards)} job cards from Amazon GraphQL API")
                return job_cards
            else:
                logger.warning(f"Unexpected response structure: {data}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching job cards: {e}")
            return []
    
    def fetch_all_canada_jobs(self) -> List[Dict[str, Any]]:
        """Convenience method to fetch all available jobs across Canada without geographic constraints"""
        return self.fetch_job_cards(lat=None, lng=None)
    
    def fetch_schedule_cards(self, job_id: str, lat: float = 53.337845, lng: float = -113.531304, distance: int = 150) -> List[Dict[str, Any]]:
        """Fetch schedule cards for a specific job ID"""
        
        # Real GraphQL query for schedules from the provided file
        query = """query searchScheduleCards($searchScheduleRequest: SearchScheduleRequest!) {
  searchScheduleCards(searchScheduleRequest: $searchScheduleRequest) {
    nextToken
    scheduleCards {
      scheduleId
      laborDemandAvailableCount
      hireStartDate
      address
      basePay
      city
      currencyCode
      distance
      employmentType
      externalJobTitle
      firstDayOnSite
      hoursPerWeek
      image
      jobId
      __typename
    }
    __typename
  }
}"""
        
        variables = {
            "searchScheduleRequest": {
                "locale": "en-CA",
                "country": "Canada",
                "keyWords": "",
                "equalFilters": [],
                "containFilters": [
                    {
                        "key": "isPrivateSchedule",
                        "val": ["false"]
                    }
                ],
                "rangeFilters": [],
                "orFilters": [],
                "dateFilters": [
                    {
                        "key": "firstDayOnSite",
                        "range": {
                            "startDate": datetime.now().strftime("%Y-%m-%d")
                        }
                    }
                ],
                "sorters": [],
                "pageSize": 1000,
                #
                "jobId": job_id
            }
        }
        # "geoQueryClause": {
        # #     "lat": lat,
        # #     "lng": lng,
        # #     "unit": "km",
        # #     "distance": distance
        # # },
        try:
            response = self.session.post(
                self.base_url,
                json={
                    "operationName": "searchScheduleCards",
                    "variables": variables,
                    "query": query
                },
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            logger.info(f"Scheduledata:{str(data)} ")
            if 'data' in data and 'searchScheduleCards' in data['data']:
                schedule_cards = data['data']['searchScheduleCards']['scheduleCards']
                logger.info(f"Fetched {len(schedule_cards)} schedule cards for job {job_id}")
                return schedule_cards
            else:
                logger.warning(f"Unexpected response structure for schedules: {data}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching schedule cards: {e}")
            return []
    
    def fetch_jobs(self, location: str = None, radius: int = 50) -> List[Dict[str, Any]]:
        """Compatibility wrapper - fetch job cards and convert to old format"""
        job_cards = self.fetch_job_cards()
        
        # Convert job cards to old format for compatibility
        jobs = []
        for card in job_cards:
            job = {
                'jobId': card.get('jobId'),
                'title': card.get('jobTitle'),
                'location': {
                    'city': card.get('city'),
                    'state': card.get('state'),
                    'postalCode': card.get('postalCode')
                },
                'employmentType': card.get('employmentType'),
                'payRate': {
                    'min': card.get('totalPayRateMin'),
                    'max': card.get('totalPayRateMax'),
                    'currency': card.get('currencyCode')
                },
                'scheduleCount': card.get('scheduleCount', 0)
            }
            jobs.append(job)
        
        return jobs
    
    async def get_available_shifts(self, lat: float = 43.7952, lng: float = -79.267, distance: int = 100) -> List[Dict[str, Any]]:
        """Get available shifts with jobId and scheduleId pairs using real API - CONCURRENT VERSION"""
        # First, get all job cards
        job_cards = self.fetch_all_canada_jobs()
        available_shifts = []
        all_application_tasks = []
        
        logger.info(f"🔍 Found {len(job_cards)} job cards, collecting all schedules...")
        
        # Collect ALL job-schedule combinations first
        for job_card in job_cards:
            job_id = job_card.get('jobId')
            if not job_id:
                continue
                
            # Get schedule cards for this job
            schedule_cards = self.fetch_schedule_cards(job_id, lat, lng, distance)
            
            for schedule in schedule_cards:
                schedule_id = schedule.get('scheduleId')
                if not schedule_id:
                    continue
                    
                # Add shift data for tracking
                shift_data = {
                    'jobId': job_id,
                    'scheduleId': schedule_id,
                    'title': job_card.get('jobTitle', 'Unknown Job'),
                    'schedule_name': schedule.get('scheduleName', 'Unknown Schedule'),
                    'available_slots': schedule.get('laborDemandAvailableCount', 0),
                    'job_card': job_card,
                    'schedule': schedule
                }
                available_shifts.append(shift_data)
                
                # Create async task for this application
                task = self.create_application_with_logging(job_id, schedule_id, shift_data)
                all_application_tasks.append(task)
        
        logger.info(f"🚀 LAUNCHING {len(all_application_tasks)} SIMULTANEOUS APPLICATION ATTEMPTS!")
        
        if all_application_tasks:
            # Execute ALL applications simultaneously
            results = await asyncio.gather(*all_application_tasks, return_exceptions=True)
            
            # Process results
            successful_count = 0
            failed_count = 0
            
            for i, result in enumerate(results):
                shift = available_shifts[i]
                if isinstance(result, Exception):
                    logger.error(f"❌ EXCEPTION for {shift['jobId']}-{shift['scheduleId']}: {result}")
                    failed_count += 1
                elif result:
                    logger.info(f"✅ SUCCESS: {shift['title']} - {shift['schedule_name']} ({shift['available_slots']} slots)")
                    successful_count += 1
                else:
                    logger.warning(f"❌ FAILED: {shift['title']} - {shift['schedule_name']}")
                    failed_count += 1
            
            logger.info(f"🎯 RESULTS: {successful_count} SUCCESS, {failed_count} FAILED out of {len(all_application_tasks)} total")
        
        logger.info(f"Found {len(available_shifts)} available shifts")
        return available_shifts
    
    async def create_application_with_logging(self, job_id: str, schedule_id: str, shift_data: Dict[str, Any]) -> bool:
        """Wrapper for create_application_api with enhanced logging for concurrent execution"""
        try:
            result = await self.create_application_api(job_id, schedule_id)
            return result
        except Exception as e:
            logger.error(f"❌ Exception in application for {job_id}-{schedule_id}: {e}")
            return False
    
    async def create_application_api(self, job_id: str, schedule_id: str, candidate_id: str = "18ec5c40-2670-11ee-a91e-69eb9a00e944") -> bool:
        """Create application using direct API call instead of browser automation"""
        
        url = "https://hiring.amazon.ca/application/api/candidate-application/ds/create-application/"
        
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.7',
            'authorization': 'AQICAHidzPmCkg52ERUUfDIMwcDZBDzd+C71CJf6w0t6dq2uqwHN8NcRE0cd1jnBYuQbG2kGAAAEUjCCBE4GCSqGSIb3DQEHBqCCBD8wggQ7AgEAMIIENAYJKoZIhvcNAQcBMB4GCWCGSAFlAwQBLjARBAx/0/baxXANzqN9JGgCARCAggQFO8JTApg9RvUgZskg4rbSaVhzaaCNWMo9chGNjODk8GGT1B5dH0lRRLEvlrvSi+c1BwcJOew4SaD1JBNwrilljkx/YkZnLXPcLcLrirW0XVQGHr25L6Ngwmlx4hEdPKZsHwqgx5J8rfH0b3PaAYLRLFMhAPHIU/lwge7P///N20Pzj5YlIjYUGBhoNrhIHDvorXK97fH93+99vgBMqHtc6LdiE5j4SPR/e6P4zvMVm1qUrmhnpOCuAPJV1ziDKpYs2c2bt8H0NJLGVyLKPTx5omzhQoaJ4/MT+6g4BVJlzzcDDQMngzHqwN3Nw1ObbLW+T/R0H7FiJW0w74ScNYbNm+PSdLYstKVUQfDaxg38ubd0HIXd65PbiKtJHtyEwyczWlRXfx9fpak2DRVa0dXfy7iGKnrR8fFoQYmk0AiN0j1wF3tzBqALHef8tQeArl7gAbltavowgnZeDMiZ+9FAiq6jSW8UW8iYS3LiE7zYr6OrB4k4q9JjHoQvOpgqEzBygLqODURsBa/we1BLQ198d1d7BH3VcfakZJcc7aCpJUEBr9O2CTJguOKUxEXT9C+r6Z9jPimiuYTraw4SGacIormNgwOvwJOHoY3GSZWFTWoPTPz/CLyolXdMUfLFqC2Wxk+ND8f8fPe2tKei+7YZMrPq6E4066dWrcpAepfVokLvYcTj0fnjr5LMu+j4Kh3VK/tl6H8e3eGvNAIYBh6dekMKIH8tefyVLKtlwCVNF86p/Z/LJSgRrutYwvjxto4l/hatG85DwHvnX0WzUy8Y0yNh+bDV3pYyS2sc20s6Wy4fEapfW2tpAJ4gx6o1LgKX9l/B4KN74PPPL7jxKl0qbZj2hTBH6mG4fY6inXwR2ud4CHT6IXnBkH2jVp0p+h14v8jJW63uhFYF9YALL+uFrjkUOJj4HNPvBe/NMtnHPcNPVMp5F/nsFTcRkR+zffrXRlSG0V8lB6WlRRPOs9DYl7WMhFYuXrr5DGAgL0WNpDvwg/GTSLjpW3RnnKWQuaoTf1uqml7jIy9CqgGAC/IJTKdxC6SLMnZ9gNoNGoHHbYPr6PNlS4edRv5GOe02nemtzjPkvulipNTbb9apT7OT/h/Sbtgc520CD0WqXzn44gT//9VcPmTn3vDoxiPDqXM8ZcIJfAmuba2Qz0JEfii12Cp8usGIZYpqxU7yOqgxNLFCXqui2U9bY09EpA9N96vHUBnj4MicIJ7ZPL9UMEYS643o9VtPENeKwFlBARNcPeWAVfl0yuS+tXPxT0BCwAZ9km5ZIagW2nrBfV74DV1qOMFdchriT8mNDOE4E8aFQOjP1RDxbwz45UEonW5pdCZgkdzuTW8Zh7aNqX2NTF0Sz+5Wtx3r',
            'bb-ui-version': 'bb-ui-v2',
            'content-type': 'application/json;charset=UTF-8',
            'dnt': '1',
            'origin': 'https://hiring.amazon.com',
            'priority': 'u=1, i',
            'referer': 'https://hiring.amazon.com/application/us/?CS=true&jobId=JOB-US-0000010894&jobTitle=Amazon%20Fulfillment%20Center%20Warehouse%20Associate&locale=en-US&scheduleId=SCH-US-0000618577&ssoEnabled=1',
            'sec-ch-ua': '"Not;A=Brand";v="99", "Brave";v="139", "Chromium";v="139"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        }

        cookies = {
            'session-id': '146-4179320-3649416',
            'session-id-time': '2082787201l',
            'lc-main': 'en_US',
            'sp-cdn': '"L5Z9:CA"',
            'ubid-main': '131-8192175-1085827',
            'session-token': '6HXWE6PztIrY3ittPRk8Hel7VNMb/1iWHwdLLKA3Dhrsye5QtqpvA7VIfsGppKOttMS6RBCjfOovqY45EGNWqQsNBx5RDbvGQWJRmWDJ3Xe8ha6TK3J0xfVevjicrdBY0Sb3AoQQp2Y/m8dYvMhAkCYtTIDopW3/Dg3xYO0Eeae54y9kizwP7IFm5DGp3OriD0jiAwiKkdSbcS+52GoL2M4aTZVKsK1Z1CtpfsjB8Zw/SFHb2yfzRWly3OFAXD3tXRdFfeFhYd6lufgeAJODih/lGlLx1eq7KgOGZ8tyGIXacX6hVFH6JUHX0tOD1pQ6TRzvgR7kCqdAUb9aEe+dXDqeVll5MeH2',
            'aws-target-data': '%7B%22support%22%3A%221%22%7D',
            'AMCVS_CCBC879D5572070E7F000101%40AdobeOrg': '1',
            'aws_lang': 'en',
            'AMCVS_7742037254C95E840A4C98A6%40AdobeOrg': '1',
            'aws-target-visitor-id': '1756921204484-513084.44_0',
            's_cc': 'true',
            'awsm-session-csrf': 'e36195c2d1f248339dbd34253078453d',
            'awsm-session': '{"sessionToken":"AAAADmtleS0xNTY4OTU1MzA3PchYGgQZre9lbOhdeAtJviG7TqQUSfo2THnkxzqX9WmFi_bENjwRGxvujfa8a4YJE0uoBipcrbJucPgtBf-X_Xfq-Qqojawp3oZEBmNZQI331-NmySadKmv_y-O6ulkipDWUiKlRfQl9zIC9fNpoS2p-DaTQhz02z9jhJgJkw9PA13bH4yWs-tS2wTJtUPNrYEGWllFFtDtXNrsig9zpUNlLXmTM7-Wc0FhQRvL3pfOLiuO0GdeIi0_f1gxQT-_XpyDJsQq-njn_e89Lq5nopWz198cwFsBTqCqxcObqCt9MGvyh8Xbd0hHnrdtkbPPfjHmp4Lm3wCD1alJalnGQf7c17rOUkmVJmw6uGR3-iLMAJw3rUT-5ELKyfH9VRMYUOFemguFuFjtxTkX0EGVXXsYV02D1kXyr4tIb8A5b6kA4Eh1ht852covbT1f1Oi06H8mrg3Jz-oaz8rehqigMkSUevxgpROHqXHSbvTeu2DbnTe4cPW-wW4DD8EBRbqlF77BVZkP0YWn9J2GOTJhcLag-DnxqjatxvEoKrqJo7bM401IlWjqnY_tpPJigVrC73K4w_i_lExO6ZammY9SHc9rz_Y8mia8HRCovSXpZ3ami94EX6gNt9iKaEyq7EQBZjPCCvPJl18dctvNSZ2xIZQyXNnJbHP0P9dQ_TbsmuQs0assd4e8g3DX0qopzJOp4UW1KqXOBjwA_WtK8qS2is4ZCCgh_v6w6PXP2SLlDWhSfxWI_-R4OaQQSqv2uKwIzFjyNTl_zf2hg6awtKMgpcNvRMVeimHP0ZujYm9bnCLeJKjqVkC-1mj69xIGkYGp5NZGePEzJryXfzbfM5L-L3xdCXCK8QQGQt7HCTU1KSIcPoepb1yFathMq5Ptg0FLQkaCnI3bbLVz2yZmGPci_YtGXNbJ7TDbUifMgZev68sUTwMCKLwxxn1ffES1AFnosDBz16L--oxdtJyrkvQVYIcHkiwMqMdDTVYJLWM5PmcIZheSPdZ4LGm8AvsFYP39SXz1BGi0Fjmc3bbDHRa0THe2I8mrHzvGQST7qR5BKpkMfjEIZ89iP9lO4NgGgSz_-g0SbHMkKAsunmr4HjRMQdTKMpDwHQ_p5EscI6fVGKgSqxGzSqFEBFORJk4ojuPxSCKXTOL5AhKjPmQl7tZGwZBmJua4YD3K8QtbnrfS-fHYmpBKgDi_zX6S3RmFOb1fhKycmt4xmooJiix_LNaZklblgjc3cVc3w1AcOf7Jm8ekyk-zbBmlQ6ydfTv-YWdxPxfd1Uw","refreshToken":null}',
            'awsm-valid-session': 'Tue, 09 Sep 2025 00:31:42 GMT',
            'aws-ubid-main': '561-7327142-7167806',
            's_sq': '%5B%5BB%5D%5D',
            's_eVar60': 'ha%7Claunch_aws-builder-center-2025-console%7Cawssm-2783200_launch%7Csignin%7Cd5142080-a981-466a-b999-ab4fde4d6ddd%7Eha_awssm-2783200_launch',
            'aws-prism-private-beta-allowlisted': 'true',
            'aws-userInfo-signed': 'eyJ0eXAiOiJKV1MiLCJrZXlSZWdpb24iOiJ1cy1lYXN0LTEiLCJhbGciOiJFUzM4NCIsImtpZCI6IjQ1YzkxMTJjLTEwZDMtNDk5NS04NzI2LWQ5ZWQ3ODA0MjYzNSJ9.eyJzdWIiOiIiLCJzaWduaW5UeXBlIjoiUFVCTElDIiwiaXNzIjoiaHR0cHM6XC9cL3NpZ25pbi5hd3MuYW1hem9uLmNvbVwvc2lnbmluIiwia2V5YmFzZSI6IlBjalluVXVvcnhoNVpBRlgrT09YTkVLa0l4bDl1M3FpdE1XVHNHSW5LbkU9IiwiYXJuIjoiYXJuOmF3czppYW06OjUzMzI2NzMyNDcxNTpyb290IiwidXNlcm5hbWUiOiJWaXZlayJ9.38asFEFBIuqsQlx28i9Q5V34fFfO2WV9IcmZdgC1XNRlAyLUO3bWmhs4ElRbUsxgYWxfAFNxrVv1Y59LBIaYgQk8fJiuPXrQLCwIVgSTw5ZFCiIIhhS1p_TcPRxz0bWt',
            'aws-userInfo': '%7B%22arn%22%3A%22arn%3Aaws%3Aiam%3A%3A533267324715%3Aroot%22%2C%22alias%22%3A%22%22%2C%22username%22%3A%22Vivek%22%2C%22keybase%22%3A%22PcjYnUuorxh5ZAFX%2BOOXNEKkIxl9u3qitMWTsGInKnE%5Cu003d%22%2C%22issuer%22%3A%22https%3A%2F%2Fsignin.aws.amazon.com%2Fsignin%22%2C%22signinType%22%3A%22PUBLIC%22%7D',
            'noflush_awsccs_sid': '3e9fdf65c213dfb5bfae1a74b580a5c8a9a3b1b34f00f34fbf6aa5b80a2504d4',
            'aws-signer-token_us-east-1': 'eyJrZXlWZXJzaW9uIjoicmd3NEdtRWYuY1BLZGxiUVVfSllPNC50bTM2T3VvUkUiLCJ2YWx1ZSI6ImswRSszeUkxU2t2cEdBMkRkU1BaR1o5ZVVZMUsyVjRIc0ptTThqekRLNVk9IiwidmVyc2lvbiI6MX0=',
            'regStatus': 'pre-register',
            'AMCV_7742037254C95E840A4C98A6%40AdobeOrg': '1585540135%7CMCIDTS%7C20341%7CMCMID%7C24398453481646198108820397753625393383%7CMCAID%7CNONE%7CMCOPTOUT-1757389599s%7CNONE%7CvVersion%7C4.4.0',
            'adobe-session-id': '08c1ba02-0cc6-4163-869c-b61f4b1796bc',
            'hvh_cs_wlbsid': '200-3968307-5109664',
            'hvh-locale': 'en-US',
            'hvh-default-locale': 'en-US',
            'hvh-country-code': 'CA',
            'hvh-stage': 'prod',
            'aws-waf-token': '381d6aa8-c929-4128-a153-3bf130a5acc5:CAoAe9UWoKQIAAAA:A1pn2weUWwo9SmAeJb4KG0EgDLPeg7L8vCXcFxpz6gFG99/1kAcWPd9jbfifVJWPP/V8El4rfin+mpS5qMIYmQ7kSIAZUGTJXCZN3newML6OtPFyToUfJnPtGxpdB1gYvaMaINjoF7Z8QFk85TgxQYVDoZb+6QVHy78xI2ET30mPfO7Kx1qL4dmA7/IRtOJqNOdjd7dpQK6muqIH',
            'hvhcid': '20477730-8d2b-11f0-a016-2b5a90896789',
            'AMCV_CCBC879D5572070E7F000101%40AdobeOrg': '179643557%7CMCIDTS%7C20340%7CMCMID%7C50577722946221945950058095730794849009%7CMCAID%7CNONE%7CMCOPTOUT-1757394881s%7CNONE%7CvVersion%7C5.5.0',
            'JSESSIONID': '27E9041A8CC63D9946CAC7DB18D3705A',
        }
        
        data = {
            "jobId": job_id,
            "dspEnabled": True,
            "scheduleId": schedule_id,
            "candidateId": candidate_id,
            "activeApplicationCheckEnabled": True
        }
        
        try:
            # Use aiohttp for async HTTP requests
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, cookies=cookies, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"⚡ API SUCCESS: {result}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ API ERROR {response.status}: {error_text}")
                        return False
                        
        except ImportError:
            # Fallback to requests (synchronous)
            try:
                response = requests.post(url, headers=headers, cookies=cookies, json=data)
                if response.status_code == 200:
                    logger.info(f"⚡ API SUCCESS: {response.json()}")
                    return True
                else:
                    logger.error(f"❌ API ERROR {response.status_code}: {response.text}")
                    return False
            except Exception as e:
                logger.error(f"❌ API REQUEST FAILED: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ API REQUEST FAILED: {e}")
            return False
    
    async def ultra_fast_apply_all_available(self, lat: float = 43.7952, lng: float = -79.267, distance: int = 100, max_concurrent: int = 50) -> Dict[str, Any]:
        """Ultra-fast method to apply to ALL available jobs simultaneously with concurrency limit"""
        logger.info(f"🚀 ULTRA-FAST MODE: Applying to ALL available jobs with max {max_concurrent} concurrent requests")
        
        # Get all job cards
        job_cards = self.fetch_all_canada_jobs()
        all_applications = []
        
        # Collect all job-schedule combinations
        for job_card in job_cards:
            job_id = job_card.get('jobId')
            if not job_id:
                continue
                
            schedule_cards = self.fetch_schedule_cards(job_id, lat, lng, distance)
            
            for schedule in schedule_cards:
                schedule_id = schedule.get('scheduleId')
                if not schedule_id:
                    continue
                    
                application_data = {
                    'job_id': job_id,
                    'schedule_id': schedule_id,
                    'title': job_card.get('jobTitle', 'Unknown'),
                    'available_slots': schedule.get('laborDemandAvailableCount', 0)
                }
                all_applications.append(application_data)
        
        logger.info(f"🎯 Found {len(all_applications)} total applications to attempt")
        
        if not all_applications:
            return {'success': 0, 'failed': 0, 'total': 0, 'applications': []}
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_application(app_data):
            async with semaphore:
                try:
                    result = await self.create_application_api(app_data['job_id'], app_data['schedule_id'])
                    return {'app_data': app_data, 'success': result, 'error': None}
                except Exception as e:
                    return {'app_data': app_data, 'success': False, 'error': str(e)}
        
        # Launch all applications with concurrency control
        logger.info(f"💥 LAUNCHING {len(all_applications)} APPLICATIONS (max {max_concurrent} concurrent)")
        start_time = time.time()
        
        results = await asyncio.gather(*[limited_application(app) for app in all_applications], return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Process results
        successful = [r for r in results if not isinstance(r, Exception) and r['success']]
        failed = [r for r in results if isinstance(r, Exception) or not r['success']]
        
        logger.info(f"🎆 ULTRA-FAST RESULTS: {len(successful)} SUCCESS, {len(failed)} FAILED in {duration:.2f} seconds")
        logger.info(f"⚡ Speed: {len(all_applications)/duration:.1f} applications/second")
        
        return {
            'success': len(successful),
            'failed': len(failed),
            'total': len(all_applications),
            'duration': duration,
            'speed_per_second': len(all_applications)/duration,
            'successful_applications': successful,
            'failed_applications': failed
        }
    
    async def rapid_poll_for_new_jobs(self, interval: float = 0.01, lat: float = 43.7952, lng: float = -79.267, distance: int = 100) -> List[Dict[str, Any]]:
        """Rapidly poll for new jobs every 0.01 seconds and return new ones immediately"""
        logger.info(f"Starting rapid polling every {interval} seconds...")
        
        while True:
            try:
                current_shifts = await self.get_available_shifts(lat, lng, distance)
                
                # Check for new shifts by comparing with last check
                new_shifts = []
                current_shift_ids = set()
                
                for shift in current_shifts:
                    shift_id = f"{shift['jobId']}-{shift['scheduleId']}"
                    current_shift_ids.add(shift_id)
                    
                    # Check if this is a new shift
                    if shift_id not in {f"{s['jobId']}-{s['scheduleId']}" for s in self.last_jobs}:
                        new_shifts.append(shift)
                        logger.info(f"🚨 NEW SHIFT DETECTED: {shift['title']} - {shift['schedule_name']} - {shift['available_slots']} slots")
                
                # Update cache
                self.last_jobs = current_shifts
                
                if new_shifts:
                    return new_shifts
                
                # Very short sleep for rapid polling
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in rapid polling: {e}")
                await asyncio.sleep(1)  # Longer sleep on error
    
    async def detect_changes(self, lat: float = 43.7952, lng: float = -79.267, distance: int = 100) -> Dict[str, Any]:
        """Detect changes in available shifts since last check"""
        current_shifts = await self.get_available_shifts(lat, lng, distance)
        
        # Compare with last check
        current_shift_ids = {f"{s['jobId']}-{s['scheduleId']}" for s in current_shifts}
        last_shift_ids = {f"{s['jobId']}-{s['scheduleId']}" for s in self.last_jobs}
        
        new_shifts = [s for s in current_shifts if f"{s['jobId']}-{s['scheduleId']}" not in last_shift_ids]
        removed_shifts = [s for s in self.last_jobs if f"{s['jobId']}-{s['scheduleId']}" not in current_shift_ids]
        
        # Update cache
        self.last_jobs = current_shifts
        
        return {
            'new_shifts': new_shifts,
            'removed_shifts': removed_shifts,
            'total_current': len(current_shifts),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_candidate_id(self, email: str) -> Optional[str]:
        """Get candidate ID for a given email (placeholder implementation)"""
        # Note: This would typically require authentication with Amazon's system
        # For now, this is a placeholder - in practice, candidateId would be obtained
        # through the login process or stored from previous successful authentications
        
        query = """
        query GetCandidate($email: String!) {
            candidate(email: $email) {
                candidateId
                email
                profile {
                    firstName
                    lastName
                }
            }
        }
        """
        
        variables = {"email": email}
        
        try:
            response = self.session.post(
                self.base_url,
                json={
                    "query": query,
                    "variables": variables
                },
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and 'candidate' in data['data']:
                return data['data']['candidate'].get('candidateId')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching candidate ID: {e}")
        
        return None
    
    async def search_shifts_by_location(self, locations: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Search for shifts across multiple locations"""
        shifts_by_location = {}
        
        for location in locations:
            shifts = await self.get_available_shifts(location)
            if shifts:
                shifts_by_location[location] = shifts
                logger.info(f"Found {len(shifts)} shifts in {location}")
            else:
                logger.info(f"No shifts found in {location}")
        
        return shifts_by_location
    
    def build_booking_url(self, job_id: str, schedule_id: str) -> str:
        """Build the booking URL for the Amazon hiring page"""
        base_url = "https://hiring.amazon.ca/application/ca/"
        params = {
            'CS': 'true',
            'jobId': job_id,
            'locale': 'en-CA',
            'query': '',
            'scheduleId': schedule_id,
            'ssoEnabled': '1'
        }
        
        # Build URL with parameters
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        booking_url = f"{base_url}?{param_string}"
        
        logger.info(f"Generated booking URL: {booking_url}")
        return booking_url