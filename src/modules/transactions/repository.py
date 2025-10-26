"""
Repository for transaction database operations.

Provides async database access for creating, updating, and querying
transactions in PostgreSQL.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import DatabaseError
from src.modules.rule_engine.enums import TransactionStatus, TransactionType
from src.storage.models import Transaction


class TransactionRepository:
    """
    Repository for managing transactions in the database.

    Handles CRUD operations for transaction records, including
    creation, updates, and queries by various identifiers.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session for database operations
        """
        self.session = session

    async def create_transaction(
        self,
        transaction_id: UUID,
        amount: float,
        from_account: str,
        to_account: str,
        transaction_type: TransactionType,
        correlation_id: str,
        currency: str = "USD",
        description: Optional[str] = None,
        merchant_id: Optional[str] = None,
        location: Optional[str] = None,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Transaction:
        """
        Create a new transaction record in the database.

        Args:
            transaction_id: Unique transaction identifier
            amount: Transaction amount
            from_account: Source account identifier
            to_account: Destination account identifier
            transaction_type: Type of transaction
            correlation_id: Request correlation ID for tracking
            currency: Transaction currency (default: USD)
            description: Optional transaction description
            merchant_id: Optional merchant identifier
            location: Optional transaction location
            device_id: Optional device identifier
            ip_address: Optional IP address

        Returns:
            Created Transaction instance

        Raises:
            DatabaseError: If transaction creation fails
        """
        try:
            transaction = Transaction(
                id=transaction_id,
                amount=amount,
                from_account=from_account,
                to_account=to_account,
                type=transaction_type,
                correlation_id=correlation_id,
                status=TransactionStatus.PENDING,
                currency=currency,
                description=description,
                merchant_id=merchant_id,
                location=location,
                device_id=device_id,
                ip_address=ip_address,
                timestamp=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            self.session.add(transaction)
            await self.session.commit()
            await self.session.refresh(transaction)

            logger.info(
                f"Created transaction: id={transaction.id}, "
                f"correlation_id={transaction.correlation_id}, "
                f"amount={transaction.amount}"
            )

            return transaction

        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Database integrity error creating transaction: {e}")
            raise DatabaseError(
                "Transaction with this ID or correlation_id already exists",
                operation="create_transaction",
                details={"transaction_id": str(transaction_id)},
            )
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating transaction: {e}")
            raise DatabaseError(
                "Failed to create transaction",
                operation="create_transaction",
                details={"error": str(e)},
            )

    async def get_by_id(self, transaction_id: UUID) -> Optional[Transaction]:
        """
        Get a transaction by its ID.

        Args:
            transaction_id: Transaction UUID

        Returns:
            Transaction instance if found, None otherwise
        """
        try:
            stmt = select(Transaction).where(Transaction.id == transaction_id)  # type: ignore
            result = await self.session.execute(stmt)
            transaction = result.scalar_one_or_none()

            if transaction:
                logger.debug(f"Found transaction: id={transaction_id}")
            else:
                logger.debug(f"Transaction not found: id={transaction_id}")

            return transaction

        except Exception as e:
            logger.error(f"Error fetching transaction by ID: {e}")
            raise DatabaseError(
                "Failed to fetch transaction",
                operation="get_by_id",
                details={"transaction_id": str(transaction_id), "error": str(e)},
            )

    async def get_by_correlation_id(self, correlation_id: str) -> Optional[Transaction]:
        """
        Get a transaction by its correlation ID.

        Args:
            correlation_id: Request correlation ID

        Returns:
            Transaction instance if found, None otherwise
        """
        try:
            stmt = select(Transaction).where(
                Transaction.correlation_id == correlation_id  # type: ignore
            )
            result = await self.session.execute(stmt)
            transaction = result.scalar_one_or_none()

            if transaction:
                logger.debug(f"Found transaction by correlation_id: {correlation_id}")
            else:
                logger.debug(
                    f"Transaction not found by correlation_id: {correlation_id}"
                )

            return transaction

        except Exception as e:
            logger.error(f"Error fetching transaction by correlation_id: {e}")
            raise DatabaseError(
                "Failed to fetch transaction",
                operation="get_by_correlation_id",
                details={"correlation_id": correlation_id, "error": str(e)},
            )

    async def update_status(
        self, transaction_id: UUID, status: TransactionStatus
    ) -> Transaction:
        """
        Update transaction status.

        Args:
            transaction_id: Transaction UUID
            status: New transaction status

        Returns:
            Updated Transaction instance

        Raises:
            DatabaseError: If transaction not found or update fails
        """
        try:
            transaction = await self.get_by_id(transaction_id)

            if not transaction:
                raise DatabaseError(
                    "Transaction not found",
                    operation="update_status",
                    details={"transaction_id": str(transaction_id)},
                )

            transaction.status = status
            transaction.updated_at = datetime.utcnow()

            await self.session.commit()
            await self.session.refresh(transaction)

            logger.info(
                f"Updated transaction status: id={transaction_id}, status={status}"
            )

            return transaction

        except DatabaseError:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating transaction status: {e}")
            raise DatabaseError(
                "Failed to update transaction status",
                operation="update_status",
                details={"transaction_id": str(transaction_id), "error": str(e)},
            )

    async def get_all_transactions(
        self,
        limit: Optional[int] = None,
        status_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        from_account: Optional[str] = None,
        to_account: Optional[str] = None,
        currency: Optional[str] = None,
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[Transaction]:
        """
        Get all transactions from database with advanced filtering.

        Args:
            limit: Optional limit for number of transactions to return
            status_filter: Filter by transaction status
            type_filter: Filter by transaction type
            from_account: Filter by source account
            to_account: Filter by destination account
            currency: Filter by currency
            search: Search across multiple text fields
            start_date: Filter transactions after this date
            end_date: Filter transactions before this date

        Returns:
            List of Transaction instances ordered by timestamp (newest first)

        Raises:
            DatabaseError: If query execution fails
        """
        try:
            # Build query with sorting by timestamp (descending - newest first)
            stmt = select(Transaction).order_by(Transaction.timestamp.desc())  # type: ignore

            # Apply filters
            if status_filter:
                stmt = stmt.where(
                    Transaction.status.ilike(f"%{status_filter}%")  # type: ignore
                )

            if type_filter:
                stmt = stmt.where(
                    Transaction.type.ilike(f"%{type_filter}%")  # type: ignore
                )

            if from_account:
                stmt = stmt.where(
                    Transaction.from_account.ilike(f"%{from_account}%")  # type: ignore
                )

            if to_account:
                stmt = stmt.where(
                    Transaction.to_account.ilike(f"%{to_account}%")  # type: ignore
                )

            if currency:
                stmt = stmt.where(
                    Transaction.currency.ilike(f"%{currency}%")  # type: ignore
                )

            if search:
                # Search across multiple text fields
                search_pattern = f"%{search}%"
                stmt = stmt.where(
                    (Transaction.description.ilike(search_pattern))  # type: ignore
                    | (Transaction.merchant_id.ilike(search_pattern))  # type: ignore
                    | (Transaction.location.ilike(search_pattern))  # type: ignore
                    | (Transaction.device_id.ilike(search_pattern))  # type: ignore
                )

            if start_date:
                stmt = stmt.where(Transaction.timestamp >= start_date)  # type: ignore

            if end_date:
                stmt = stmt.where(Transaction.timestamp <= end_date)  # type: ignore

            # Apply limit if specified
            if limit is not None:
                stmt = stmt.limit(limit)

            result = await self.session.execute(stmt)
            transactions = list(result.scalars().all())

            filter_info = []
            if status_filter:
                filter_info.append(f"status={status_filter}")
            if type_filter:
                filter_info.append(f"type={type_filter}")
            if currency:
                filter_info.append(f"currency={currency}")
            if search:
                filter_info.append(f"search={search}")

            logger.info(
                f"Retrieved {len(transactions)} transaction(s)"
                + (f" with filters: {', '.join(filter_info)}" if filter_info else "")
                + (f" and limit={limit}" if limit else " (no limit)")
            )

            return transactions

        except Exception as e:
            logger.error(f"Error fetching all transactions: {e}")
            raise DatabaseError(
                "Failed to fetch transactions",
                operation="get_all_transactions",
                details={"limit": limit, "error": str(e)},
            )
