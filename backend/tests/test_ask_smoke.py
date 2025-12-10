#!/usr/bin/env python3
"""
Simple smoke test for /ask endpoint.
Sends a code-oriented query and prints the JSON response.
"""
import json
import sys

URL = "http://127.0.0.1:8000/ask"
PAYLOAD = {
    "query": "find and explain the merge sort code",
    "k": 5
}


def run_with_requests():
    try:
        import requests
    except ImportError:
        return None, "requests not installed"

    try:
        r = requests.post(URL, json=PAYLOAD, timeout=10)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text
    except Exception as e:
        return None, str(e)


def run_with_urllib():
    from urllib import request, error
    import urllib.parse
    data = json.dumps(PAYLOAD).encode('utf-8')
    req = request.Request(URL, data=data, headers={'Content-Type': 'application/json'})
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
            try:
                return resp.getcode(), json.loads(body)
            except Exception:
                return resp.getcode(), body
    except error.URLError as e:
        return None, str(e)


if __name__ == '__main__':
    code, resp = run_with_requests()
    if code is None and resp == "requests not installed":
        code, resp = run_with_urllib()

    print("Status:", code)
    print("Response:")
    print(json.dumps(resp, indent=2, ensure_ascii=False))

    # Quick check: list sources paths if present
    if isinstance(resp, dict) and resp.get('sources'):
        print("\nDetected sources (top):")
        for s in resp['sources'][:10]:
            print(" -", s.get('path') or s.get('source'))
