"""
Redis-based frequency tracking for fraud detection.

This module provides atomic operations for tracking transaction patterns
and frequency metrics in real-time using Redis data structures:
- Counters for transaction counts
- Sets for unique devices/IPs/types
- Float counters for velocity (amount) tracking

All operations include automatic TTL management and use Redis pipelines
for optimal performance.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from redis.asyncio import Redis

from src.core.logging import get_logger
from src.modules.rule_engine.enums import TimeWindow

logger = get_logger("storage.redis.frequency")

# Redis key prefixes
KEY_PREFIX_TXN_COUNT = "freq:account:{account_id}:txn_count:{window}:{time_key}"
KEY_PREFIX_TO_ACCOUNT = "freq:to_account:{account_id}:txn_count:{window}:{time_key}"
KEY_PREFIX_DEVICES = "freq:account:{account_id}:devices:{window}:{time_key}"
KEY_PREFIX_IPS = "freq:account:{account_id}:ips:{window}:{time_key}"
KEY_PREFIX_TYPES = "freq:account:{account_id}:types:{window}:{time_key}"
KEY_PREFIX_VELOCITY = "freq:account:{account_id}:velocity:{window}:{time_key}"


def get_ttl_for_window(time_window: TimeWindow) -> int:
    """
    Get TTL in seconds for a time window.

    TTL is set to 2x the window duration to ensure data availability
    for overlapping time window checks.

    Args:
        time_window: Time window enum value

    Returns:
        TTL in seconds
    """
    ttl_mapping = {
        TimeWindow.MINUTE: 120,  # 2 minutes
        TimeWindow.FIVE_MINUTES: 600,  # 10 minutes
        TimeWindow.TEN_MINUTES: 1200,  # 20 minutes
        TimeWindow.FIFTEEN_MINUTES: 1800,  # 30 minutes
        TimeWindow.THIRTY_MINUTES: 3600,  # 1 hour
        TimeWindow.HOUR: 7200,  # 2 hours
        TimeWindow.SIX_HOURS: 43200,  # 12 hours
        TimeWindow.TWELVE_HOURS: 86400,  # 24 hours
        TimeWindow.DAY: 172800,  # 2 days
        TimeWindow.WEEK: 1209600,  # 2 weeks
        TimeWindow.MONTH: 5184000,  # ~2 months (60 days)
    }
    return ttl_mapping.get(time_window, 7200)  # Default to 2 hours


def get_time_window_key(
    time_window: TimeWindow, timestamp: Optional[datetime] = None
) -> str:
    """
    Generate time-based key suffix for Redis keys based on window granularity.

    Examples:
        MINUTE: "2025-10-21-14-35"
        HOUR: "2025-10-21-14"
        DAY: "2025-10-21"
        WEEK: "2025-W43"
        MONTH: "2025-10"

    Args:
        time_window: Time window granularity
        timestamp: Timestamp to generate key for (defaults to now)

    Returns:
        Time key string for Redis
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    if time_window in (
        TimeWindow.MINUTE,
        TimeWindow.FIVE_MINUTES,
        TimeWindow.TEN_MINUTES,
        TimeWindow.FIFTEEN_MINUTES,
        TimeWindow.THIRTY_MINUTES,
    ):
        # Minute-level granularity
        return timestamp.strftime("%Y-%m-%d-%H-%M")
    elif time_window in (
        TimeWindow.HOUR,
        TimeWindow.SIX_HOURS,
        TimeWindow.TWELVE_HOURS,
    ):
        # Hour-level granularity
        return timestamp.strftime("%Y-%m-%d-%H")
    elif time_window == TimeWindow.DAY:
        # Day-level granularity
        return timestamp.strftime("%Y-%m-%d")
    elif time_window == TimeWindow.WEEK:
        # Week-level granularity (ISO week)
        return timestamp.strftime("%Y-W%W")
    elif time_window == TimeWindow.MONTH:
        # Month-level granularity
        return timestamp.strftime("%Y-%m")
    else:
        # Default to hour-level
        return timestamp.strftime("%Y-%m-%d-%H")


def generate_frequency_key(
    account_id: str,
    metric_type: str,
    time_window: TimeWindow,
    timestamp: Optional[datetime] = None,
) -> str:
    """
    Generate Redis key for frequency tracking.

    Args:
        account_id: Account identifier
        metric_type: Type of metric (txn_count, velocity, devices, ips, types, to_account)
        time_window: Time window for tracking
        timestamp: Timestamp for key generation (defaults to now)

    Returns:
        Complete Redis key
    """
    time_key = get_time_window_key(time_window, timestamp)
    window_str = time_window.value

    key_templates = {
        "txn_count": KEY_PREFIX_TXN_COUNT,
        "to_account": KEY_PREFIX_TO_ACCOUNT,
        "devices": KEY_PREFIX_DEVICES,
        "ips": KEY_PREFIX_IPS,
        "types": KEY_PREFIX_TYPES,
        "velocity": KEY_PREFIX_VELOCITY,
    }

    template = key_templates.get(metric_type, KEY_PREFIX_TXN_COUNT)
    return template.format(account_id=account_id, window=window_str, time_key=time_key)


# === COUNTER OPERATIONS ===


async def increment_transaction_count(
    redis: Redis,
    account_id: str,
    time_window: TimeWindow,
    increment_by: int = 1,
    ttl_seconds: Optional[int] = None,
) -> int:
    """
    Increment transaction counter for an account.

    Args:
        redis: Async Redis client
        account_id: Account identifier
        time_window: Time window for counting
        increment_by: Amount to increment (default: 1)
        ttl_seconds: Custom TTL (defaults to 2x window duration)

    Returns:
        New counter value after increment
    """
    key = generate_frequency_key(account_id, "txn_count", time_window)

    # Use pipeline for atomic operation
    async with redis.pipeline(transaction=True) as pipe:
        pipe.incrby(key, increment_by)
        pipe.expire(key, ttl_seconds or get_ttl_for_window(time_window))
        results = await pipe.execute()

    new_count = results[0]

    logger.debug(
        f"Incremented transaction count for account {account_id}",
        account_id=account_id,
        time_window=time_window.value,
        new_count=new_count,
        redis_key=key,
    )

    return new_count


async def get_transaction_count(
    redis: Redis, account_id: str, time_window: TimeWindow
) -> int:
    """
    Get current transaction count for an account.

    Args:
        redis: Async Redis client
        account_id: Account identifier
        time_window: Time window to query

    Returns:
        Current transaction count (0 if key doesn't exist)
    """
    key = generate_frequency_key(account_id, "txn_count", time_window)
    count = await redis.get(key)

    result = int(count) if count else 0

    logger.debug(
        f"Retrieved transaction count for account {account_id}",
        account_id=account_id,
        time_window=time_window.value,
        count=result,
    )

    return result


async def increment_to_account_count(
    redis: Redis,
    to_account_id: str,
    time_window: TimeWindow,
    increment_by: int = 1,
    ttl_seconds: Optional[int] = None,
) -> int:
    """
    Increment counter for transactions TO a specific account.

    Args:
        redis: Async Redis client
        to_account_id: Destination account identifier
        time_window: Time window for counting
        increment_by: Amount to increment (default: 1)
        ttl_seconds: Custom TTL

    Returns:
        New counter value after increment
    """
    key = generate_frequency_key(to_account_id, "to_account", time_window)

    async with redis.pipeline(transaction=True) as pipe:
        pipe.incrby(key, increment_by)
        pipe.expire(key, ttl_seconds or get_ttl_for_window(time_window))
        results = await pipe.execute()

    new_count = results[0]

    logger.debug(
        f"Incremented to_account count for {to_account_id}",
        to_account_id=to_account_id,
        new_count=new_count,
    )

    return new_count


async def get_to_account_count(
    redis: Redis, to_account_id: str, time_window: TimeWindow
) -> int:
    """
    Get current count of transactions TO a specific account.

    Args:
        redis: Async Redis client
        to_account_id: Destination account identifier
        time_window: Time window to query

    Returns:
        Current transaction count
    """
    key = generate_frequency_key(to_account_id, "to_account", time_window)
    count = await redis.get(key)
    return int(count) if count else 0


# === SET OPERATIONS (devices, IPs, types) ===


async def add_device_to_account(
    redis: Redis,
    account_id: str,
    device_id: str,
    time_window: TimeWindow,
    ttl_seconds: Optional[int] = None,
) -> int:
    """
    Add device to account's device set and return total unique devices count.

    Args:
        redis: Async Redis client
        account_id: Account identifier
        device_id: Device identifier to add
        time_window: Time window for tracking
        ttl_seconds: Custom TTL

    Returns:
        Total number of unique devices for account in time window
    """
    key = generate_frequency_key(account_id, "devices", time_window)

    async with redis.pipeline(transaction=True) as pipe:
        pipe.sadd(key, device_id)
        pipe.expire(key, ttl_seconds or get_ttl_for_window(time_window))
        pipe.scard(key)
        results = await pipe.execute()

    unique_count = results[2]

    logger.debug(
        f"Added device to account {account_id}",
        account_id=account_id,
        device_id=device_id,
        unique_devices=unique_count,
    )

    return unique_count


async def get_unique_devices_count(
    redis: Redis, account_id: str, time_window: TimeWindow
) -> int:
    """
    Get number of unique devices for an account.

    Args:
        redis: Async Redis client
        account_id: Account identifier
        time_window: Time window to query

    Returns:
        Number of unique devices
    """
    key = generate_frequency_key(account_id, "devices", time_window)
    count = await redis.scard(key)  # type: ignore
    return count


async def add_ip_to_account(
    redis: Redis,
    account_id: str,
    ip_address: str,
    time_window: TimeWindow,
    ttl_seconds: Optional[int] = None,
) -> int:
    """
    Add IP address to account's IP set and return total unique IPs count.

    Args:
        redis: Async Redis client
        account_id: Account identifier
        ip_address: IP address to add
        time_window: Time window for tracking
        ttl_seconds: Custom TTL

    Returns:
        Total number of unique IPs for account in time window
    """
    key = generate_frequency_key(account_id, "ips", time_window)

    async with redis.pipeline(transaction=True) as pipe:
        pipe.sadd(key, ip_address)
        pipe.expire(key, ttl_seconds or get_ttl_for_window(time_window))
        pipe.scard(key)
        results = await pipe.execute()

    unique_count = results[2]

    logger.debug(
        f"Added IP to account {account_id}",
        account_id=account_id,
        ip_address=ip_address,
        unique_ips=unique_count,
    )

    return unique_count


async def get_unique_ips_count(
    redis: Redis, account_id: str, time_window: TimeWindow
) -> int:
    """
    Get number of unique IP addresses for an account.

    Args:
        redis: Async Redis client
        account_id: Account identifier
        time_window: Time window to query

    Returns:
        Number of unique IPs
    """
    key = generate_frequency_key(account_id, "ips", time_window)
    count = await redis.scard(key)  # type: ignore
    return count


async def add_transaction_type(
    redis: Redis,
    account_id: str,
    transaction_type: str,
    time_window: TimeWindow,
    ttl_seconds: Optional[int] = None,
) -> int:
    """
    Add transaction type to account's type set and return total unique types count.

    Args:
        redis: Async Redis client
        account_id: Account identifier
        transaction_type: Transaction type to add
        time_window: Time window for tracking
        ttl_seconds: Custom TTL

    Returns:
        Total number of unique transaction types for account in time window
    """
    key = generate_frequency_key(account_id, "types", time_window)

    async with redis.pipeline(transaction=True) as pipe:
        pipe.sadd(key, transaction_type)
        pipe.expire(key, ttl_seconds or get_ttl_for_window(time_window))
        pipe.scard(key)
        results = await pipe.execute()

    unique_count = results[2]

    logger.debug(
        f"Added transaction type to account {account_id}",
        account_id=account_id,
        transaction_type=transaction_type,
        unique_types=unique_count,
    )

    return unique_count


async def get_unique_types_count(
    redis: Redis, account_id: str, time_window: TimeWindow
) -> int:
    """
    Get number of unique transaction types for an account.

    Args:
        redis: Async Redis client
        account_id: Account identifier
        time_window: Time window to query

    Returns:
        Number of unique transaction types
    """
    key = generate_frequency_key(account_id, "types", time_window)
    count = await redis.scard(key)  # type: ignore
    return count


# === VELOCITY OPERATIONS (amount tracking) ===


async def increment_velocity(
    redis: Redis,
    account_id: str,
    amount: float,
    time_window: TimeWindow,
    ttl_seconds: Optional[int] = None,
) -> float:
    """
    Add amount to velocity counter and return total.

    Velocity tracks the total transaction amount within a time window,
    useful for detecting unusual spending patterns.

    Args:
        redis: Async Redis client
        account_id: Account identifier
        amount: Transaction amount to add
        time_window: Time window for tracking
        ttl_seconds: Custom TTL

    Returns:
        Total amount for account in time window
    """
    key = generate_frequency_key(account_id, "velocity", time_window)

    async with redis.pipeline(transaction=True) as pipe:
        pipe.incrbyfloat(key, amount)
        pipe.expire(key, ttl_seconds or get_ttl_for_window(time_window))
        results = await pipe.execute()

    total_amount = float(results[0])

    logger.debug(
        f"Incremented velocity for account {account_id}",
        account_id=account_id,
        amount=amount,
        total_velocity=total_amount,
    )

    return total_amount


async def get_velocity(redis: Redis, account_id: str, time_window: TimeWindow) -> float:
    """
    Get total transaction amount for an account in time window.

    Args:
        redis: Async Redis client
        account_id: Account identifier
        time_window: Time window to query

    Returns:
        Total amount (velocity) in time window
    """
    key = generate_frequency_key(account_id, "velocity", time_window)
    amount = await redis.get(key)
    return float(amount) if amount else 0.0


# === BATCH OPERATIONS ===


async def track_transaction_metrics(
    redis: Redis,
    from_account: str,
    to_account: str,
    amount: float,
    device_id: Optional[str],
    ip_address: Optional[str],
    transaction_type: str,
    time_window: TimeWindow,
) -> Dict[str, Any]:
    """
    Track all frequency metrics for a transaction in a single batch operation.

    This function uses Redis pipeline to perform all tracking operations atomically,
    minimizing network overhead and ensuring consistency.

    Args:
        redis: Async Redis client
        from_account: Source account identifier
        to_account: Destination account identifier
        amount: Transaction amount
        device_id: Optional device identifier
        ip_address: Optional IP address
        transaction_type: Transaction type
        time_window: Time window for all metrics

    Returns:
        Dictionary with all updated metric values
    """
    logger.info(
        "Tracking transaction metrics in batch",
        from_account=from_account,
        to_account=to_account,
        amount=amount,
        time_window=time_window.value,
        event="frequency_batch_start",
    )

    ttl = get_ttl_for_window(time_window)

    # Track from_account metrics
    txn_count = await increment_transaction_count(
        redis, from_account, time_window, ttl_seconds=ttl
    )
    velocity = await increment_velocity(
        redis, from_account, amount, time_window, ttl_seconds=ttl
    )
    unique_types = await add_transaction_type(
        redis, from_account, transaction_type, time_window, ttl_seconds=ttl
    )

    # Track to_account metrics
    to_account_count = await increment_to_account_count(
        redis, to_account, time_window, ttl_seconds=ttl
    )

    # Track optional metrics
    unique_devices = 0
    if device_id:
        unique_devices = await add_device_to_account(
            redis, from_account, device_id, time_window, ttl_seconds=ttl
        )

    unique_ips = 0
    if ip_address:
        unique_ips = await add_ip_to_account(
            redis, from_account, ip_address, time_window, ttl_seconds=ttl
        )

    metrics = {
        "from_account": from_account,
        "to_account": to_account,
        "txn_count": txn_count,
        "to_account_count": to_account_count,
        "velocity": velocity,
        "unique_devices": unique_devices,
        "unique_ips": unique_ips,
        "unique_types": unique_types,
        "time_window": time_window.value,
    }

    logger.info(
        "Transaction metrics tracked successfully",
        event="frequency_batch_complete",
        metrics=metrics,
    )

    return metrics
