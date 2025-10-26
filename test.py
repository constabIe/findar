#!/usr/bin/env python3
"""
Простой нагрузочный скрипт:
- 10000 запросов к http://localhost/api/v1/transactions (можно изменить URL)
- средняя скорость ~250 req/s (джиттер ±50 -> диапазон ~200-300)
- concurrency = 100 (одновременных запросов)
- выводит итоговые метрики

Требуется: pip install aiohttp
Запуск: python simple_load.py
"""

import asyncio
import aiohttp
import random
import time
import json
from collections import Counter

TOTAL = 10_000
TARGET_MEAN_RPS = 250.0   # средняя целевая скорость
RPS_JITTER = 50.0         # +/- jitter -> даёт ~200-300 rps
CONCURRENCY = 100
URL = "http://localhost/api/v1/transactions"

FROM_ACCOUNTS = [f"A{100000 + i}" for i in range(40)]
TO_ACCOUNTS = [f"REC{100 + i}" for i in range(40)]
TYPES = ["transfer", "withdrawal", "payment", "refund", "cash_out"]
CURRENCIES = ["USD", "EUR", "GBP", "RUB"]
LOCATIONS = ["US", "GB", "DE", "NL", "RU", "IN", "BR", "CN", "RS", "TR"]
DEVICES = [f"DEVICE_{c}" for c in ("A", "B", "C", "D", "E", "X", "Y")]


def random_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


def make_payload():
    # простая, но разнообразная генерация
    roll = random.random()
    if roll < 0.8:
        amount = round(random.uniform(1, 2000), 2)
    elif roll < 0.95:
        amount = round(random.uniform(2000, 50000), 2)
    else:
        amount = round(random.uniform(50000, 500000), 2)

    # 30% - выбрать из небольшой группы, чтобы получить кластеры одинаковых from_account
    if random.random() < 0.3:
        from_acc = random.choice(FROM_ACCOUNTS[:10])
    else:
        from_acc = random.choice(FROM_ACCOUNTS)

    payload = {
        "amount": amount,
        "from_account": from_acc,
        "to_account": random.choice(TO_ACCOUNTS),
        "type": random.choice(TYPES),
        "device_id": random.choice(DEVICES),
        "location": random.choice(LOCATIONS),
        "currency": random.choice(CURRENCIES),
        "ip_address": random_ip(),
    }
    return payload


async def sender(session, payload, stats):
    t0 = time.perf_counter()
    try:
        async with session.post(URL, json=payload, timeout=10) as resp:
            text = await resp.text()
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


async def main():
    stats = {
        "sent": 0,
        "success": 0,
        "failed": 0,
        "status_counts": Counter(),
        "errors": Counter(),
        "latencies": [],
    }

    connector = aiohttp.TCPConnector(limit=CONCURRENCY * 2)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=5, sock_read=10)
    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        start = time.time()
        tasks = []

        # Интервал между запросами = 1 / target_rps. Каждый запрос использует независимый
        # target_rps со случайным джиттером в пределах +/- RPS_JITTER.
        for i in range(TOTAL):
            # джиттерим целевой rps для этого запроса
            target_rps = max(1.0, random.gauss(TARGET_MEAN_RPS, RPS_JITTER / 2.0))
            interval = 1.0 / target_rps

            # задержка перед постановкой следующего запроса (асинхронно, без блокировки отправки)
            await asyncio.sleep(interval)

            payload = make_payload()
            stats["sent"] += 1

            # fire-and-forget с семафором для контроля concurrency
            await sem.acquire()

            async def run_and_release(pl, st):
                try:
                    await sender(session, pl, st)
                finally:
                    sem.release()

            tasks.append(asyncio.create_task(run_and_release(payload, stats)))

        # дождаться завершения всех тасков
        await asyncio.gather(*tasks, return_exceptions=True)
        end = time.time()

    # Сводка
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
    if avg_latency_ms is not None:
        lat_ms_sorted = sorted(lat_list)
        def pct(p): return lat_ms_sorted[int(len(lat_ms_sorted) * p)]
        print(f"Latency ms (avg/p50/p95/min/max): "
              f"{avg_latency_ms:.1f} / {pct(0.5)*1000:.1f} / {pct(0.95)*1000:.1f} / {min(lat_list)*1000:.1f} / {max(lat_list)*1000:.1f}")
    print("Status counts:", dict(stats["status_counts"]))
    if stats["errors"]:
        print("Top errors:", stats["errors"].most_common(10))


if __name__ == "__main__":
    asyncio.run(main())
