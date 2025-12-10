#!/usr/bin/env python3
"""
Extended smoke tests for /ask endpoint with several prompt variants.
"""
import json
import sys
import time

URL = "http://127.0.0.1:8000/ask"
QUERIES = [
    {"label": "explicit_code", "payload": {"query": "find and explain the merge sort code", "k": 5}},
    {"label": "algorithm_name_variation", "payload": {"query": "show me merge_sort implementation", "k": 5}},
    {"label": "ambiguous", "payload": {"query": "explain sorting algorithms", "k": 5}},
    {"label": "general_question", "payload": {"query": "what is merge sort?", "k": 5}},
    {"label": "non_code_confusing", "payload": {"query": "show me the introduction chapter", "k": 5}}
]


def post_json(payload):
    try:
        import requests
    except Exception:
        requests = None

    if requests:
        try:
            r = requests.post(URL, json=payload, timeout=30)
            try:
                return r.status_code, r.json()
            except Exception:
                return r.status_code, r.text
        except Exception as e:
            # retry once on timeout/connection issue (LLM may be busy)
            try:
                r = requests.post(URL, json=payload, timeout=30)
                try:
                    return r.status_code, r.json()
                except Exception:
                    return r.status_code, r.text
            except Exception as e2:
                return None, str(e2)
    else:
        # urllib fallback
        from urllib import request, error
        import urllib.parse
        data = json.dumps(payload).encode('utf-8')
        req = request.Request(URL, data=data, headers={'Content-Type': 'application/json'})
        try:
            with request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode('utf-8')
                try:
                    return resp.getcode(), json.loads(body)
                except Exception:
                    return resp.getcode(), body
        except Exception as e:
            # retry once for urllib
            try:
                with request.urlopen(req, timeout=30) as resp:
                    body = resp.read().decode('utf-8')
                    try:
                        return resp.getcode(), json.loads(body)
                    except Exception:
                        return resp.getcode(), body
            except Exception as e2:
                return None, str(e2)


if __name__ == '__main__':
    overall = []
    for q in QUERIES:
        label = q['label']
        payload = q['payload']
        print(f"\n--- Query: {label} -- {payload['query']} ---")
        code, resp = post_json(payload)
        print("Status:", code)
        try:
            print(json.dumps(resp, indent=2, ensure_ascii=False)[:4000])
        except Exception:
            print(str(resp)[:4000])

        # Print top sources if present
        if isinstance(resp, dict) and resp.get('sources'):
            print("Top sources:")
            for s in resp['sources'][:5]:
                print(" -", s.get('path') or s.get('source'))
        else:
            print("No sources returned or response not JSON.")

        overall.append((label, code, resp))
        time.sleep(0.5)

    # summary
    print('\n=== Summary ===')
    for label, code, resp in overall:
        src_count = len(resp.get('sources', [])) if isinstance(resp, dict) else 0
        print(f"{label}: status={code} sources={src_count}")
