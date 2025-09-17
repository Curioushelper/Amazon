#!/usr/bin/env python3
"""
Curl Config Extractor for Amazon Job Application API
Extracts authentication details from curl request and formats them for server_config.json
"""

import re
import json
from urllib.parse import unquote

def parse_curl_request(curl_command: str) -> dict:
    """Parse curl command and extract headers, cookies, and data"""
    
    # Extract URL
    url_match = re.search(r"curl '([^']+)'", curl_command)
    url = url_match.group(1) if url_match else ""
    
    # Extract headers
    headers = {}
    header_pattern = r"-H '([^:]+):\s*([^']+)'"
    for match in re.finditer(header_pattern, curl_command):
        key = match.group(1).strip()
        value = match.group(2).strip()
        headers[key] = value
    
    # Extract cookies from -b parameter
    cookies = {}
    cookie_match = re.search(r"-b '([^']+)'", curl_command)
    if cookie_match:
        cookie_string = cookie_match.group(1)
        # Split cookies by '; ' and parse key=value pairs
        for cookie in cookie_string.split('; '):
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                cookies[key.strip()] = value.strip()
    
    # Extract data payload
    data = {}
    data_match = re.search(r"--data-raw '([^']+)'", curl_command)
    if data_match:
        try:
            data = json.loads(data_match.group(1))
        except json.JSONDecodeError:
            data = {"raw": data_match.group(1)}
    
    return {
        "url": url,
        "headers": headers,
        "cookies": cookies,
        "data": data
    }

def format_for_graphql_client(parsed_data: dict) -> str:
    """Format extracted data in the same style as graphql_client.py"""
    
    headers = parsed_data["headers"]
    cookies = parsed_data["cookies"]
    data = parsed_data["data"]
    
    # Format headers dictionary
    headers_formatted = "        headers = {\n"
    for key, value in headers.items():
        headers_formatted += f"            '{key}': '{value}',\n"
    headers_formatted += "        }\n"
    
    # Format cookies dictionary
    cookies_formatted = "        cookies = {\n"
    for key, value in cookies.items():
        cookies_formatted += f"            '{key}': '{value}',\n"
    cookies_formatted += "        }\n"
    
    # Format data dictionary
    data_formatted = "        data = {\n"
    for key, value in data.items():
        if isinstance(value, str):
            data_formatted += f"            \"{key}\": \"{value}\",\n"
        elif isinstance(value, bool):
            data_formatted += f"            \"{key}\": {str(value)},\n"
        else:
            data_formatted += f"            \"{key}\": {json.dumps(value)},\n"
    data_formatted += "        }\n"
    
    return f"""
URL: {parsed_data['url']}

{headers_formatted}
{cookies_formatted}
{data_formatted}"""

def extract_config_values(parsed_data: dict) -> dict:
    """Extract key values for server_config.json"""
    
    headers = parsed_data["headers"]
    cookies = parsed_data["cookies"]
    data = parsed_data["data"]
    
    config_values = {
        "authentication": {
            "authorization_token": headers.get("authorization", ""),
            "bb_ui_version": headers.get("bb-ui-version", ""),
            "user_agent": headers.get("user-agent", ""),
            "session_id": cookies.get("session-id", ""),
            "session_token": cookies.get("session-token", ""),
            "aws_waf_token": cookies.get("aws-waf-token", ""),
            "jsessionid": cookies.get("JSESSIONID", ""),
            "hvhcid": cookies.get("hvhcid", "")
        },
        "application_data": {
            "candidate_id": data.get("candidateId", ""),
            "job_id": data.get("jobId", ""),
            "schedule_id": data.get("scheduleId", ""),
            "dsp_enabled": data.get("dspEnabled", True),
            "active_application_check_enabled": data.get("activeApplicationCheckEnabled", True)
        },
        "api_endpoints": {
            "create_application_url": parsed_data["url"]
        }
    }
    
    return config_values

def main():
    # Your curl command
    curl_command = """curl 'https://auth.hiring.amazon.com/api/authorize?countryCode=CA' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: en-US,en;q=0.5' \
  -H 'Access-Control-Allow-Origin: *' \
  -H 'Authorization: AQICAHidzPmCkg52ERUUfDIMwcDZBDzd+C71CJf6w0t6dq2uqwFxXC6HPJBB+8PZ26RplMP9AAAEUjCCBE4GCSqGSIb3DQEHBqCCBD8wggQ7AgEAMIIENAYJKoZIhvcNAQcBMB4GCWCGSAFlAwQBLjARBAwk0Cn65E0Zg9lBfO0CARCAggQFp3AhhhnxJaHZy39SQwFhfBe0M0ZMRvE7JRkzo2Zl8KW07s3Xi9oVaM2XcAUV4YiQlZrn+Dj7fi0hum5Seil7uHRIOal819WKsB+/Z3TDpp7seFYjrtZ0XsfadPE/Ch930G7/K7DfYHZhMcGl3BMVO304pgH/fy9nZOQ60SU3eUnYFqTDhd2CSQK9UEVca4+FESfXErFP1Ytr28mm1rWaVF52NleemA22A8JnyXr8E7r4g5tOaSs4Oiupbq5DZJ2NnSTXfS8k8ocanumNoZ3vqx+A25nEjvcNndQ0kX67Gjy8EqocmkLqDcD6/YtxK5NAHHfhVLHyaLczU+xKF1Rh3YCZy0//H7c7E24c/2am5iuAesufeap4gXdormHxBrFiYSckNB/V8xZl3hJkFMjZN6yGPAvHb5H26sBsn27D9gmr6wH2NqDCTwPa7QMB8JinYyL+BxSO0TyayFNrTiB5Ay/gV09RiDLUpHxWFR7Z2/z/E0LhIdluMH+VamMBokTb38zQ25VRji3B0hJBS5Lb8SDvexTKWUIofG8uKcM724lx6jEcxAmPy+unSh86T9W8HDKeRnXYlRnC8h52v8tPbufjT2DvNLpz4wkd4SEGAbT8tjMV3hq/tSp7i4aUjsXpSzoDWJFIRmFSxitE0Klwgd/JBtC1MFy+olBKUEpDZwn+ve64NdUgM/1OmdMfZYtTNup2rTo7C1cxG6Cns1fec6w4x0r/qxCyTiAdVs2VbEVznlXO5Ea/WVa+3/NY3LhJMyGQpctEwJSw9WGzhEAY9d8QOXn3JsTjQkg15UHBO7M8PMKkJdZw1N9vSOTFli2dKTcsOiZ0Ly5Ncn04K+B05t01RD75QEEKBdUykCIsEGHCP8Baa/V9J+xXnCiAW4q8jebNGrTCkjjaR3DxuIThh9DcWj5E64E43dm7h7uDmaV9it9FE95l+16CwxhnAJ/yKtRISccOdfk2EIyiV8gcRkvHKhXEHseZ+t2DmBRHh6B32rpraRB2VlMmd2Dure3xEPnh/canRc/5Enoh5BYgJRbFW7+kaTKAhv0EqDvdVTWyjDpFPB04EepwBjsrohidGCbhrYLVQ7rd1AcyO731PMKW5/cW1iZ947USM4oJnDhI6yD7k51bKk6ikPURX6dUFYtT6sIQjU22EiB2AJo1sFEGqGIeT+7NGTcoIIE8W1hU7GSxR6RFPX2qCmwXidQRzj8YhGnHRf1RiEDv7xI4UmHgNITtc4S43llT4gxmwL7Rgd8FGbhnD6QAokSb5DU5CwALsaQWoUvg9vhXguQhwnRNdic4/Mp4IgPNbMDcURPOW9kTMR0wjjjHchQvtPEW2Po0qNfww5QN0VSx3VPsLxW+/UTu' \
  -H 'CSRF-Token: eyJhbGciOiJLTVMiLCJ0eXAiOiJKV1QifQ.eyJpYXQiOjE3NTc5ODgwMzMsImV4cCI6MTc1Nzk5MTYzM30.AQICAHidzPmCkg52ERUUfDIMwcDZBDzd+C71CJf6w0t6dq2uqwGyw7x0MLl6VQ5BfoQkP2WBAAAAtDCBsQYJKoZIhvcNAQcGoIGjMIGgAgEAMIGaBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDI1glfsXwVoVlJsuYwIBEIBtrY77GahQfejGzLFioOmu1sbbacdMPBj7EQwGJbCf9RKpz0TO6iyjrspmWtfaL9OaRRRJOr+p3c5/nDpCljVqfJUOOvcvbVyJ4nQ6m8efToPDaef1G+oJtbh10J7lZsROIGaxTfS5Ed4VC/35gQ==' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json' \
  -H 'DNT: 1' \
  -H 'Origin: https://hiring.amazon.ca' \
  -H 'Referer: https://hiring.amazon.ca/' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: cross-site' \
  -H 'Sec-GPC: 1' \
  -H 'User-Agent: Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36' \
  -H 'sec-ch-ua: "Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"' \
  -H 'sec-ch-ua-mobile: ?1' \
  -H 'sec-ch-ua-platform: "Android"' \
  --data-raw '{"redirectUrl":"hiring.amazon.ca","token":"eyJhbGciOiJLTVMiLCJ0eXAiOiJKV1QifQ.eyJpYXQiOjE3NTc5ODgwMzMsImV4cCI6MTc1Nzk5MTYzM30.AQICAHidzPmCkg52ERUUfDIMwcDZBDzd+C71CJf6w0t6dq2uqwGyw7x0MLl6VQ5BfoQkP2WBAAAAtDCBsQYJKoZIhvcNAQcGoIGjMIGgAgEAMIGaBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDI1glfsXwVoVlJsuYwIBEIBtrY77GahQfejGzLFioOmu1sbbacdMPBj7EQwGJbCf9RKpz0TO6iyjrspmWtfaL9OaRRRJOr+p3c5/nDpCljVqfJUOOvcvbVyJ4nQ6m8efToPDaef1G+oJtbh10J7lZsROIGaxTfS5Ed4VC/35gQ=="}'"""

    print("🔍 CURL CONFIG EXTRACTOR")
    print("=" * 50)
    
    # Parse the curl command
    parsed_data = parse_curl_request(curl_command)
    
    print("\n📋 EXTRACTED DATA FOR GRAPHQL_CLIENT.PY:")
    print("=" * 50)
    formatted_code = format_for_graphql_client(parsed_data)
    print(formatted_code)
    
    print("\n🔧 CONFIG VALUES FOR SERVER_CONFIG.JSON:")
    print("=" * 50)
    config_values = extract_config_values(parsed_data)
    print(json.dumps(config_values, indent=2))
    
    print("\n✅ KEY AUTHENTICATION TOKENS:")
    print("=" * 50)
    print(f"Authorization Token: {parsed_data['headers'].get('authorization', 'NOT_FOUND')[:50]}...")
    print(f"Session ID: {parsed_data['cookies'].get('session-id', 'NOT_FOUND')}")
    print(f"Session Token: {parsed_data['cookies'].get('session-token', 'NOT_FOUND')[:50]}...")
    print(f"AWS WAF Token: {parsed_data['cookies'].get('aws-waf-token', 'NOT_FOUND')[:50]}...")
    print(f"Candidate ID: {parsed_data['data'].get('candidateId', 'NOT_FOUND')}")
    print(f"Job ID: {parsed_data['data'].get('jobId', 'NOT_FOUND')}")
    print(f"Schedule ID: {parsed_data['data'].get('scheduleId', 'NOT_FOUND')}")
    
    print("\n💾 SAVE THIS OUTPUT TO UPDATE YOUR SERVER CONFIG!")

if __name__ == "__main__":
    main()
