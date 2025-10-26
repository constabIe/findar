#!/usr/bin/env python3
"""
Improved load tester script.

Fixes applied:
- Accepts `--url`, `--total`, `--concurrency` CLI args.
- Uses 127.0.0.1 by default (avoids localhost IPv6/IPv4 issues).
- Performs a quick TCP/connectivity check with retries before starting to
  avoid immediate connection errors.
- Keeps original payload generation and reporting but makes connector and
  semaphore handling more robust.

Requires: pip install aiohttp
Usage: python test.py --url http://127.0.0.1:8080/api/v1/transactions
"""

import argparse
import asyncio
import random
import time
import sys
from collections import Counter
from urllib.parse import urlparse

import aiohttp
import json

# Defaults
DEFAULT_TOTAL = 1000
DEFAULT_MEAN_RPS = 100.0
DEFAULT_RPS_JITTER = 50.0
DEFAULT_CONCURRENCY = 100
DEFAULT_URL = "http://localhost:8000/api/v1/transactions"

FROM_ACCOUNTS = [f"A{100000 + i}" for i in range(40)]
TO_ACCOUNTS = [f"REC{100 + i}" for i in range(40)]
TYPES = ["transfer", "withdrawal", "payment", "refund", "cash_out"]
CURRENCIES = ["USD", "EUR", "GBP", "RUB"]
LOCATIONS = ["US", "GB", "DE", "NL", "RU", "IN", "BR", "CN", "RS", "TR"]
DEVICES = [f"DEVICE_{c}" for c in ("A", "B", "C", "D", "E", "X", "Y")]


def random_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


def make_payload():
    roll = random.random()
    if roll < 0.8:
        amount = round(random.uniform(1, 2000), 2)
    elif roll < 0.95:
        amount = round(random.uniform(2000, 50000), 2)
    else:
        amount = round(random.uniform(50000, 500000), 2)

    if random.random() < 0.3:
        from_acc = random.choice(FROM_ACCOUNTS[:10])
    else:
        from_acc = random.choice(FROM_ACCOUNTS)

    return {
        "amount": amount,
        "from_account": from_acc,
        "to_account": random.choice(TO_ACCOUNTS),
        "type": random.choice(TYPES),
        "device_id": random.choice(DEVICES),
        "location": random.choice(LOCATIONS),
        "currency": random.choice(CURRENCIES),
        "ip_address": random_ip(),
    }


async def sender(session: aiohttp.ClientSession, url: str, payload: dict, stats: dict):
    t0 = time.perf_counter()
    if stats.get("verbose"):
        # print compact JSON of payload
        try:
            print("Sending:", json.dumps(payload, ensure_ascii=False))
        except Exception:
            print("Sending:", payload)
    try:
        async with session.post(url, json=payload) as resp:
            _ = await resp.text()
            elapsed = time.perf_counter() - t0
            stats["latencies"].append(elapsed)
            stats["status_counts"][resp.status] += 1
            if 200 <= resp.status < 300:
                stats["success"] += 1
            else:
                stats["failed"] += 1
    except Exception as e:
        elapsed = time.perf_counter() - t0
        stats["latencies"].append(elapsed)
        stats["failed"] += 1
        stats["errors"][type(e).__name__] += 1


async def tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


def percentile(lat_list, p: float):
    if not lat_list:
        return None
    lat_sorted = sorted(lat_list)
    idx = int(len(lat_sorted) * p)
    idx = max(0, min(idx, len(lat_sorted) - 1))
    return lat_sorted[idx]


async def main():
    parser = argparse.ArgumentParser(description="Simple load tester")
    parser.add_argument("--url", default=DEFAULT_URL, help="Target URL")
    parser.add_argument("--total", type=int, default=DEFAULT_TOTAL, help="Total requests")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Concurrent requests")
    parser.add_argument("--verbose", action="store_true", help="Print each payload being sent")
    args = parser.parse_args()

    URL = args.url
    TOTAL = args.total
    CONCURRENCY = args.concurrency
    VERBOSE = args.verbose

    parsed = urlparse(URL)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    # quick tcp check with retries
    max_retries = 5
    backoff = 0.5
    ok = False
    for attempt in range(1, max_retries + 1):
        if await tcp_check(host, port, timeout=2.0):
            ok = True
            break
        print(f"Connection to {host}:{port} failed (attempt {attempt}/{max_retries}), retrying in {backoff}s...")
        await asyncio.sleep(backoff)
        backoff *= 2

    if not ok:
        print(f"Cannot reach {host}:{port}. Check that the server is running and the URL is correct: {URL}")
        sys.exit(1)

    stats = {
        "sent": 0,
        "success": 0,
        "failed": 0,
        "status_counts": Counter(),
        "errors": Counter(),
        "latencies": [],
        "verbose": VERBOSE,
    }

    connector = aiohttp.TCPConnector(limit=0)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=5, sock_read=10)
    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        start = time.time()
        tasks = []

        for i in range(TOTAL):
            # jitter target rps to spread requests
            target_rps = max(1.0, random.gauss(DEFAULT_MEAN_RPS, DEFAULT_RPS_JITTER / 2.0))
            interval = 1.0 / target_rps
            await asyncio.sleep(interval)

            payload = make_payload()
            stats["sent"] += 1

            await sem.acquire()

            async def run_and_release(pl, st):
                try:
                    await sender(session, URL, pl, st)
                finally:
                    sem.release()

            tasks.append(asyncio.create_task(run_and_release(payload, stats)))

        await asyncio.gather(*tasks, return_exceptions=True)
        end = time.time()

    elapsed = end - start
    sent = stats["sent"]
    success = stats["success"]
    failed = stats["failed"]
    avg_rps = sent / elapsed if elapsed > 0 else 0
    lat_list = stats["latencies"]
    avg_latency_ms = (sum(lat_list) / len(lat_list) * 1000) if lat_list else None

    print("\n=== RESULT ===")
    print(f"Total requested: {sent}")
    print(f"Success (2xx):   {success}")
    print(f"Failed:          {failed}")
    print(f"Elapsed sec:     {elapsed:.2f}")
    print(f"Avg throughput:  {avg_rps:.2f} req/s")
    if avg_latency_ms is not None and lat_list:
        p50_v = percentile(lat_list, 0.5)
        p95_v = percentile(lat_list, 0.95)
        p50 = p50_v * 1000 if p50_v is not None else None
        p95 = p95_v * 1000 if p95_v is not None else None
        print(
            "Latency ms (avg/p50/p95/min/max): "
            f"{avg_latency_ms:.1f} / {p50:.1f} / {p95:.1f} / {min(lat_list)*1000:.1f} / {max(lat_list)*1000:.1f}"
        )
    print("Status counts:", dict(stats["status_counts"]))
    if stats["errors"]:
        print("Top errors:", stats["errors"].most_common(10))


if __name__ == "__main__":
    asyncio.run(main())
