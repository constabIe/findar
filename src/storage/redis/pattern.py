"""
Redis-based pattern tracking for fraud detection.

This module provides operations for storing and analyzing transaction patterns
over time windows. It stores complete transaction data to enable complex
pattern analysis like structuring detection, recipient patterns, and device-based patterns.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from redis.asyncio import Redis

from src.core.logging import get_logger
from src.modules.rule_engine.enums import TimeWindow

logger = get_logger("storage.redis.pattern")

# Redis key prefix for pattern data
KEY_PREFIX_PATTERN_TXNS = "pattern:txns:{account_id}:{window}"


def get_ttl_for_window(time_window: TimeWindow) -> int:
    """
    Get TTL in seconds for a time window.
    
    TTL is set to 2x the window duration to ensure data availability.
    
    Args:
        time_window: Time window enum value
        
    Returns:
        TTL in seconds
    """
    ttl_mapping = {
        TimeWindow.MINUTE: 120,
        TimeWindow.FIVE_MINUTES: 600,
        TimeWindow.TEN_MINUTES: 1200,
        TimeWindow.FIFTEEN_MINUTES: 1800,
        TimeWindow.THIRTY_MINUTES: 3600,
        TimeWindow.HOUR: 7200,
        TimeWindow.SIX_HOURS: 43200,
        TimeWindow.TWELVE_HOURS: 86400,
        TimeWindow.DAY: 172800,
        TimeWindow.WEEK: 1209600,
        TimeWindow.MONTH: 5184000,
    }
    return ttl_mapping.get(time_window, 7200)


def get_window_duration_seconds(time_window: TimeWindow) -> int:
    """
    Get duration of time window in seconds.
    
    Args:
        time_window: Time window enum value
        
    Returns:
        Duration in seconds
    """
    duration_mapping = {
        TimeWindow.MINUTE: 60,
        TimeWindow.FIVE_MINUTES: 300,
        TimeWindow.TEN_MINUTES: 600,
        TimeWindow.FIFTEEN_MINUTES: 900,
        TimeWindow.THIRTY_MINUTES: 1800,
        TimeWindow.HOUR: 3600,
        TimeWindow.SIX_HOURS: 21600,
        TimeWindow.TWELVE_HOURS: 43200,
        TimeWindow.DAY: 86400,
        TimeWindow.WEEK: 604800,
        TimeWindow.MONTH: 2592000,  # 30 days
    }
    return duration_mapping.get(time_window, 3600)


async def store_transaction_for_pattern(
    redis: Redis,
    account_id: str,
    transaction_data: Dict[str, Any],
    time_window: TimeWindow,
) -> None:
    """
    Store transaction data in Redis for pattern analysis.
    
    Stores complete transaction information in a Redis list with automatic TTL.
    Each transaction is stored as JSON with timestamp for time-based filtering.
    
    Args:
        redis: Async Redis client
        account_id: Account ID (from_account)
        transaction_data: Complete transaction data dict
        time_window: Time window for pattern detection
        
    Transaction data should include:
        - id: Transaction UUID
        - amount: Transaction amount
        - to_account: Recipient account ID
        - device_id: Device identifier
        - timestamp: Transaction timestamp (ISO format)
        - type: Transaction type
        - location: Transaction location (optional)
    """
    try:
        # Generate Redis key
        key = KEY_PREFIX_PATTERN_TXNS.format(
            account_id=account_id, window=time_window.value
        )
        
        # Prepare transaction record with timestamp for filtering
        txn_record = {
            "id": str(transaction_data.get("id")),
            "amount": float(transaction_data.get("amount", 0)),
            "to_account": transaction_data.get("to_account", ""),
            "device_id": transaction_data.get("device_id"),
            "timestamp": transaction_data.get("timestamp", datetime.utcnow().isoformat()),
            "type": transaction_data.get("type", ""),
            "location": transaction_data.get("location"),
        }
        
        # Store as JSON in list
        await redis.lpush(key, json.dumps(txn_record))
        
        # Set TTL
        ttl = get_ttl_for_window(time_window)
        await redis.expire(key, ttl)
        
        logger.debug(
            "Stored transaction for pattern analysis",
            account_id=account_id,
            txn_id=txn_record["id"],
            window=time_window.value,
            event="pattern_txn_stored",
        )
        
    except Exception as e:
        logger.error(
            "Failed to store transaction for pattern analysis",
            account_id=account_id,
            error=str(e),
            event="pattern_store_failed",
        )
        # Don't raise - pattern storage failure shouldn't block transaction processing


async def get_transactions_in_window(
    redis: Redis,
    account_id: str,
    time_window: TimeWindow,
    current_timestamp: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Get all transactions from account within the time window.
    
    Retrieves transactions and filters by timestamp to ensure they fall
    within the specified time window.
    
    Args:
        redis: Async Redis client
        account_id: Account ID to get transactions for
        time_window: Time window for filtering
        current_timestamp: Current time (defaults to now)
        
    Returns:
        List of transaction dictionaries within the time window
    """
    try:
        if current_timestamp is None:
            current_timestamp = datetime.utcnow()
        
        key = KEY_PREFIX_PATTERN_TXNS.format(
            account_id=account_id, window=time_window.value
        )
        
        # Get all transactions from list
        raw_txns = await redis.lrange(key, 0, -1)
        
        if not raw_txns:
            return []
        
        # Parse and filter by time window
        window_duration = get_window_duration_seconds(time_window)
        cutoff_time = current_timestamp - timedelta(seconds=window_duration)
        
        filtered_txns = []
        for raw_txn in raw_txns:
            try:
                txn = json.loads(raw_txn)
                txn_time = datetime.fromisoformat(txn["timestamp"])
                
                # Only include transactions within window
                if txn_time >= cutoff_time:
                    filtered_txns.append(txn)
                    
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(
                    "Failed to parse transaction from Redis",
                    error=str(e),
                    raw_data=raw_txn,
                )
                continue
        
        logger.debug(
            "Retrieved transactions for pattern analysis",
            account_id=account_id,
            window=time_window.value,
            total_stored=len(raw_txns),
            in_window=len(filtered_txns),
            event="pattern_txns_retrieved",
        )
        
        return filtered_txns
        
    except Exception as e:
        logger.error(
            "Failed to retrieve transactions for pattern analysis",
            account_id=account_id,
            window=time_window.value,
            error=str(e),
            event="pattern_retrieve_failed",
        )
        return []


async def analyze_recipient_pattern(
    transactions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze recipient patterns in transaction list.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        Dictionary with recipient pattern analysis:
        - unique_recipients: Count of unique recipients
        - recipients: List of unique recipient IDs
        - all_same_recipient: Boolean, true if all to same recipient
    """
    if not transactions:
        return {
            "unique_recipients": 0,
            "recipients": [],
            "all_same_recipient": False,
        }
    
    recipients = set()
    for txn in transactions:
        to_account = txn.get("to_account")
        if to_account:
            recipients.add(to_account)
    
    return {
        "unique_recipients": len(recipients),
        "recipients": list(recipients),
        "all_same_recipient": len(recipients) == 1,
    }


async def analyze_device_pattern(
    transactions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze device patterns in transaction list.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        Dictionary with device pattern analysis:
        - unique_devices: Count of unique devices
        - devices: List of unique device IDs
        - all_same_device: Boolean, true if all from same device
        - device_velocities: Dict of device_id -> total_amount
        - max_device_velocity: Maximum amount from any single device
    """
    if not transactions:
        return {
            "unique_devices": 0,
            "devices": [],
            "all_same_device": False,
            "device_velocities": {},
            "max_device_velocity": 0.0,
        }
    
    devices = set()
    device_amounts = {}
    
    for txn in transactions:
        device_id = txn.get("device_id")
        amount = float(txn.get("amount", 0))
        
        if device_id:
            devices.add(device_id)
            device_amounts[device_id] = device_amounts.get(device_id, 0.0) + amount
    
    max_velocity = max(device_amounts.values()) if device_amounts else 0.0
    
    return {
        "unique_devices": len(devices),
        "devices": list(devices),
        "all_same_device": len(devices) == 1,
        "device_velocities": device_amounts,
        "max_device_velocity": max_velocity,
    }


async def analyze_amount_pattern(
    transactions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze amount patterns in transaction list.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        Dictionary with amount analysis:
        - total_amount: Sum of all transaction amounts
        - transaction_count: Number of transactions
        - average_amount: Average transaction amount
        - min_amount: Minimum transaction amount
        - max_amount: Maximum transaction amount
    """
    if not transactions:
        return {
            "total_amount": 0.0,
            "transaction_count": 0,
            "average_amount": 0.0,
            "min_amount": 0.0,
            "max_amount": 0.0,
        }
    
    amounts = [float(txn.get("amount", 0)) for txn in transactions]
    total = sum(amounts)
    count = len(amounts)
    
    return {
        "total_amount": total,
        "transaction_count": count,
        "average_amount": total / count if count > 0 else 0.0,
        "min_amount": min(amounts) if amounts else 0.0,
        "max_amount": max(amounts) if amounts else 0.0,
    }
