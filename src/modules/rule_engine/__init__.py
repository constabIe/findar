"""
Rule Engine module for fraud detection.

This module provides a comprehensive rule engine for evaluating financial transactions
against configurable fraud detection rules. It supports multiple rule types:

- Threshold rules: Amount limits, frequency checks, time-based restrictions
- Pattern rules: Transaction sequence analysis, structuring detection
- Composite rules: Logical combinations of other rules
- ML rules: Machine learning-based risk scoring

Key Features:
- Hot reload of rules without system restart
- Redis caching for performance
- Comprehensive audit logging
- Flexible parameter configuration
- Real-time evaluation with correlation tracking

Components:
- models: SQLModel database models for rules and transactions
- schemas: Pydantic schemas for API requests/responses and validation
- enums: Enumeration types for consistent value handling
"""

from .models import Transaction, Rule, RuleExecution, RuleCache
from .schemas import (
    # Parameter schemas
    ThresholdRuleParams,
    PatternRuleParams,
    CompositeRuleParams,
    MLRuleParams,
    
    # Evaluation schemas
    RuleEvaluationRequest,
    RuleEvaluationResult,
    RuleContext,
    TransactionEvaluationResult,
    
    # Management schemas
    RuleCreateRequest,
    RuleUpdateRequest,
    RuleResponse,
    RuleListResponse,
    
    # Cache schemas
    CacheStatusResponse,
    HotReloadRequest,
    HotReloadResponse,
)
from .enums import (
    RuleType,
    RuleStatus,
    TransactionStatus,
    TransactionType,
    RuleMatchStatus,
    RiskLevel,
    ThresholdOperator,
    TimeWindow,
    CompositeOperator,
    CacheStatus,
)

# Export all public components
__all__ = [
    # Models
    "Transaction",
    "Rule", 
    "RuleExecution",
    "RuleCache",
    
    # Parameter Schemas
    "ThresholdRuleParams",
    "PatternRuleParams", 
    "CompositeRuleParams",
    "MLRuleParams",
    
    # Evaluation Schemas
    "RuleEvaluationRequest",
    "RuleEvaluationResult",
    "RuleContext", 
    "TransactionEvaluationResult",
    
    # Management Schemas
    "RuleCreateRequest",
    "RuleUpdateRequest",
    "RuleResponse",
    "RuleListResponse",
    
    # Cache Schemas
    "CacheStatusResponse",
    "HotReloadRequest",
    "HotReloadResponse",
    
    # Enums
    "RuleType",
    "RuleStatus",
    "TransactionStatus", 
    "TransactionType",
    "RuleMatchStatus",
    "RiskLevel",
    "ThresholdOperator",
    "TimeWindow", 
    "CompositeOperator",
    "CacheStatus",
]

# Module metadata
__version__ = "1.0.0"
__author__ = "Findar Team"
__description__ = "Fraud detection rule engine with hot reload and caching"
