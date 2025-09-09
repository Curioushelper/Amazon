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
    curl_command = """curl 'https://hiring.amazon.com/application/api/candidate-application/ds/create-application/' \\
  -H 'accept: application/json, text/plain, */*' \\
  -H 'accept-language: en-US,en;q=0.7' \\
  -H 'authorization: AQICAHidzPmCkg52ERUUfDIMwcDZBDzd+C71CJf6w0t6dq2uqwHN8NcRE0cd1jnBYuQbG2kGAAAEUjCCBE4GCSqGSIb3DQEHBqCCBD8wggQ7AgEAMIIENAYJKoZIhvcNAQcBMB4GCWCGSAFlAwQBLjARBAx/0/baxXANzqN9JGgCARCAggQFO8JTApg9RvUgZskg4rbSaVhzaaCNWMo9chGNjODk8GGT1B5dH0lRRLEvlrvSi+c1BwcJOew4SaD1JBNwrilljkx/YkZnLXPcLcLrirW0XVQGHr25L6Ngwmlx4hEdPKZsHwqgx5J8rfH0b3PaAYLRLFMhAPHIU/lwge7P///N20Pzj5YlIjYUGBhoNrhIHDvorXK97fH93+99vgBMqHtc6LdiE5j4SPR/e6P4zvMVm1qUrmhnpOCuAPJV1ziDKpYs2c2bt8H0NJLGVyLKPTx5omzhQoaJ4/MT+6g4BVJlzzcDDQMngzHqwN3Nw1ObbLW+T/R0H7FiJW0w74ScNYbNm+PSdLYstKVUQfDaxg38ubd0HIXd65PbiKtJHtyEwyczWlRXfx9fpak2DRVa0dXfy7iGKnrR8fFoQYmk0AiN0j1wF3tzBqALHef8tQeArl7gAbltavowgnZeDMiZ+9FAiq6jSW8UW8iYS3LiE7zYr6OrB4k4q9JjHoQvOpgqEzBygLqODURsBa/we1BLQ198d1d7BH3VcfakZJcc7aCpJUEBr9O2CTJguOKUxEXT9C+r6Z9jPimiuYTraw4SGacIormNgwOvwJOHoY3GSZWFTWoPTPz/CLyolXdMUfLFqC2Wxk+ND8f8fPe2tKei+7YZMrPq6E4066dWrcpAepfVokLvYcTj0fnjr5LMu+j4Kh3VK/tl6H8e3eGvNAIYBh6dekMKIH8tefyVLKtlwCVNF86p/Z/LJSgRrutYwvjxto4l/hatG85DwHvnX0WzUy8Y0yNh+bDV3pYyS2sc20s6Wy4fEapfW2tpAJ4gx6o1LgKX9l/B4KN74PPPL7jxKl0qbZj2hTBH6mG4fY6inXwR2ud4CHT6IXnBkH2jVp0p+h14v8jJW63uhFYF9YALL+uFrjkUOJj4HNPvBe/NMtnHPcNPVMp5F/nsFTcRkR+zffrXRlSG0V8lB6WlRRPOs9DYl7WMhFYuXrr5DGAgL0WNpDvwg/GTSLjpW3RnnKWQuaoTf1uqml7jIy9CqgGAC/IJTKdxC6SLMnZ9gNoNGoHHbYPr6PNlS4edRv5GOe02nemtzjPkvulipNTbb9apT7OT/h/Sbtgc520CD0WqXzn44gT//9VcPmTn3vDoxiPDqXM8ZcIJfAmuba2Qz0JEfii12Cp8usGIZYpqxU7yOqgxNLFCXqui2U9bY09EpA9N96vHUBnj4MicIJ7ZPL9UMEYS643o9VtPENeKwFlBARNcPeWAVfl0yuS+tXPxT0BCwAZ9km5ZIagW2nrBfV74DV1qOMFdchriT8mNDOE4E8aFQOjP1RDxbwz45UEonW5pdCZgkdzuTW8Zh7aNqX2NTF0Sz+5Wtx3r' \\
  -H 'bb-ui-version: bb-ui-v2' \\
  -H 'content-type: application/json;charset=UTF-8' \\
  -b 'session-id=146-4179320-3649416; session-id-time=2082787201l; i18n-prefs=USD; lc-main=en_US; sp-cdn="L5Z9:CA"; ubid-main=131-8192175-1085827; session-token=6HXWE6PztIrY3ittPRk8Hel7VNMb/1iWHwdLLKA3Dhrsye5QtqpvA7VIfsGppKOttMS6RBCjfOovqY45EGNWqQsNBx5RDbvGQWJRmWDJ3Xe8ha6TK3J0xfVevjicrdBY0Sb3AoQQp2Y/m8dYvMhAkCYtTIDopW3/Dg3xYO0Eeae54y9kizwP7IFm5DGp3OriD0jiAwiKkdSbcS+52GoL2M4aTZVKsK1Z1CtpfsjB8Zw/SFHb2yfzRWly3OFAXD3tXRdFfeFhYd6lufgeAJODih/lGlLx1eq7KgOGZ8tyGIXacX6hVFH6JUHX0tOD1pQ6TRzvgR7kCqdAUb9aEe+dXDqeVll5MeH2; aws-target-data=%7B%22support%22%3A%221%22%7D; AMCVS_CCBC879D5572070E7F000101%40AdobeOrg=1; aws_lang=en; AMCVS_7742037254C95E840A4C98A6%40AdobeOrg=1; aws-target-visitor-id=1756921204484-513084.44_0; s_cc=true; awsm-session-csrf=e36195c2d1f248339dbd34253078453d; awsm-session={"sessionToken":"AAAADmtleS0xNTY4OTU1MzA3PchYGgQZre9lbOhdeAtJviG7TqQUSfo2THnkxzqX9WmFi_bENjwRGxvujfa8a4YJE0uoBipcrbJucPgtBf-X_Xfq-Qqojawp3oZEBmNZQI331-NmySadKmv_y-O6ulkipDWUiKlRfQl9zIC9fNpoS2p-DaTQhz02z9jhJgJkw9PA13bH4yWs-tS2wTJtUPNrYEGWllFFtDtXNrsig9zpUNlLXmTM7-Wc0FhQRvL3pfOLiuO0GdeIi0_f1gxQT-_XpyDJsQq-njn_e89Lq5nopWz198cwFsBTqCqxcObqCt9MGvyh8Xbd0hHnrdtkbPPfjHmp4Lm3wCD1alJalnGQf7c17rOUkmVJmw6uGR3-iLMAJw3rUT-5ELKyfH9VRMYUOFemguFuFjtxTkX0EGVXXsYV02D1kXyr4tIb8A5b6kA4Eh1ht852covbT1f1Oi06H8mrg3Jz-oaz8rehqigMkSUevxgpROHqXHSbvTeu2DbnTe4cPW-wW4DD8EBRbqlF77BVZkP0YWn9J2GOTJhcLag-DnxqjatxvEoKrqJo7bM401IlWjqnY_tpPJigVrC73K4w_i_lExO6ZammY9SHc9rz_Y8mia8HRCovSXpZ3ami94EX6gNt9iKaEyq7EQBZjPCCvPJl18dctvNSZ2xIZQyXNnJbHP0P9dQ_TbsmuQs0assd4e8g3DX0qopzJOp4UW1KqXOBjwA_WtK8qS2is4ZCCgh_v6w6PXP2SLlDWhSfxWI_-R4OaQQSqv2uKwIzFjyNTl_zf2hg6awtKMgpcNvRMVeimHP0ZujYm9bnCLeJKjqVkC-1mj69xIGkYGp5NZGePEzJryXfzbfM5L-L3xdCXCK8QQGQt7HCTU1KSIcPoepb1yFathMq5Ptg0FLQkaCnI3bbLVz2yZmGPci_YtGXNbJ7TDbUifMgZev68sUTwMCKLwxxn1ffES1AFnosDBz16L--oxdtJyrkvQVYIcHkiwMqMdDTVYJLWM5PmcIZheSPdZ4LGm8AvsFYP39SXz1BGi0Fjmc3bbDHRa0THe2I8mrHzvGQST7qR5BKpkMfjEIZ89iP9lO4NgGgSz_-g0SbHMkKAsunmr4HjRMQdTKMpDwHQ_p5EscI6fVGKgSqxGzSqFEBFORJk4ojuPxSCKXTOL5AhKjPmQl7tZGwZBmJua4YD3K8QtbnrfS-fHYmpBKgDi_zX6S3RmFOb1fhKycmt4xmooJiix_LNaZklblgjc3cVc3w1AcOf7Jm8ekyk-zbBmlQ6ydfTv-YWdxPxfd1Uw","refreshToken":null}; awsm-valid-session=Tue, 09 Sep 2025 00:31:42 GMT; aws-ubid-main=561-7327142-7167806; s_sq=%5B%5BB%5D%5D; s_eVar60=ha%7Claunch_aws-builder-center-2025-console%7Cawssm-2783200_launch%7Csignin%7Cd5142080-a981-466a-b999-ab4fde4d6ddd%7Eha_awssm-2783200_launch; aws-prism-private-beta-allowlisted=true; aws-userInfo-signed=eyJ0eXAiOiJKV1MiLCJrZXlSZWdpb24iOiJ1cy1lYXN0LTEiLCJhbGciOiJFUzM4NCIsImtpZCI6IjQ1YzkxMTJjLTEwZDMtNDk5NS04NzI2LWQ5ZWQ3ODA0MjYzNSJ9.eyJzdWIiOiIiLCJzaWduaW5UeXBlIjoiUFVCTElDIiwiaXNzIjoiaHR0cHM6XC9cL3NpZ25pbi5hd3MuYW1hem9uLmNvbVwvc2lnbmluIiwia2V5YmFzZSI6IlBjalluVXVvcnhoNVpBRlgrT09YTkVLa0l4bDl1M3FpdE1XVHNHSW5LbkU9IiwiYXJuIjoiYXJuOmF3czppYW06OjUzMzI2NzMyNDcxNTpyb290IiwidXNlcm5hbWUiOiJWaXZlayJ9.38asFEFBIuqsQlx28i9Q5V34fFfO2WV9IcmZdgC1XNRlAyLUO3bWmhs4ElRbUsxgYWxfAFNxrVv1Y59LBIaYgQk8fJiuPXrQLCwIVgSTw5ZFCiIIhhS1p_TcPRxz0bWt; aws-userInfo=%7B%22arn%22%3A%22arn%3Aaws%3Aiam%3A%3A533267324715%3Aroot%22%2C%22alias%22%3A%22%22%2C%22username%22%3A%22Vivek%22%2C%22keybase%22%3A%22PcjYnUuorxh5ZAFX%2BOOXNEKkIxl9u3qitMWTsGInKnE%5Cu003d%22%2C%22issuer%22%3A%22https%3A%2F%2Fsignin.aws.amazon.com%2Fsignin%22%2C%22signinType%22%3A%22PUBLIC%22%7D; noflush_awsccs_sid=3e9fdf65c213dfb5bfae1a74b580a5c8a9a3b1b34f00f34fbf6aa5b80a2504d4; aws-signer-token_us-east-1=eyJrZXlWZXJzaW9uIjoicmd3NEdtRWYuY1BLZGxiUVVfSllPNC50bTM2T3VvUkUiLCJ2YWx1ZSI6ImswRSszeUkxU2t2cEdBMkRkU1BaR1o5ZVVZMUsyVjRIc0ptTThqekRLNVk9IiwidmVyc2lvbiI6MX0=; regStatus=pre-register; AMCV_7742037254C95E840A4C98A6%40AdobeOrg=1585540135%7CMCIDTS%7C20341%7CMCMID%7C24398453481646198108820397753625393383%7CMCAID%7CNONE%7CMCOPTOUT-1757389599s%7CNONE%7CvVersion%7C4.4.0; adobe-session-id=08c1ba02-0cc6-4163-869c-b61f4b1796bc; hvh_cs_wlbsid=200-3968307-5109664; hvh-locale=en-US; hvh-default-locale=en-US; hvh-country-code=US; hvh-stage=prod; aws-waf-token=381d6aa8-c929-4128-a153-3bf130a5acc5:CAoAe9UWoKQIAAAA:A1pn2weUWwo9SmAeJb4KG0EgDLPeg7L8vCXcFxpz6gFG99/1kAcWPd9jbfifVJWPP/V8El4rfin+mpS5qMIYmQ7kSIAZUGTJXCZN3newML6OtPFyToUfJnPtGxpdB1gYvaMaINjoF7Z8QFk85TgxQYVDoZb+6QVHy78xI2ET30mPfO7Kx1qL4dmA7/IRtOJqNOdjd7dpQK6muqIH; hvhcid=20477730-8d2b-11f0-a016-2b5a90896789; AMCV_CCBC879D5572070E7F000101%40AdobeOrg=179643557%7CMCIDTS%7C20340%7CMCMID%7C50577722946221945950058095730794849009%7CMCAID%7CNONE%7CMCOPTOUT-1757394881s%7CNONE%7CvVersion%7C5.5.0; JSESSIONID=27E9041A8CC63D9946CAC7DB18D3705A' \\
  -H 'dnt: 1' \\
  -H 'origin: https://hiring.amazon.com' \\
  -H 'priority: u=1, i' \\
  -H 'referer: https://hiring.amazon.com/application/us/?CS=true&jobId=JOB-US-0000010894&jobTitle=Amazon%20Fulfillment%20Center%20Warehouse%20Associate&locale=en-US&scheduleId=SCH-US-0000618577&ssoEnabled=1' \\
  -H 'sec-ch-ua: "Not;A=Brand";v="99", "Brave";v="139", "Chromium";v="139"' \\
  -H 'sec-ch-ua-mobile: ?1' \\
  -H 'sec-ch-ua-platform: "Android"' \\
  -H 'sec-fetch-dest: empty' \\
  -H 'sec-fetch-mode: cors' \\
  -H 'sec-fetch-site: same-origin' \\
  -H 'sec-gpc: 1' \\
  -H 'user-agent: Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36' \\
  --data-raw '{"jobId":"JOB-US-0000010894","dspEnabled":true,"scheduleId":"SCH-US-0000618577","candidateId":"fc5c1d80-f096-11ee-b747-298d2c2cbcfb","activeApplicationCheckEnabled":true}'"""

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
