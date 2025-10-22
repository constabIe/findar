#!/usr/bin/env python3
"""
Utility script to check Celery configuration and registered tasks.
"""

from src.modules.queue.celery_config import celery_app

print("=" * 80)
print("CELERY CONFIGURATION CHECK")
print("=" * 80)

print(f"\n📦 App name: {celery_app.main}")
print(f"🔗 Broker URL: {celery_app.conf.broker_url}")
print(f"💾 Result backend: {celery_app.conf.result_backend}")

print("\n📋 Registered Tasks:")
print("-" * 80)
for task_name in sorted(celery_app.tasks.keys()):
    if not task_name.startswith("celery."):
        print(f"  ✓ {task_name}")

print("\n🔄 Task Routes:")
print("-" * 80)
for task_name, route_config in celery_app.conf.task_routes.items():
    print(f"  • {task_name}")
    print(f"    → queue: {route_config.get('queue')}")
    print(f"    → routing_key: {route_config.get('routing_key')}")

print("\n📬 Configured Queues:")
print("-" * 80)
for queue in celery_app.conf.task_queues:
    print(f"  • {queue.name}")
    print(f"    → exchange: {queue.exchange.name}")
    print(f"    → routing_key: {queue.routing_key}")

print("\n" + "=" * 80)
print("To start worker with all queues:")
print("celery -A src.modules.queue.celery_config:celery_app worker \\")
print("  --loglevel=info \\")
print("  --queues=transactions,rule_executions,celery")
print("=" * 80)
