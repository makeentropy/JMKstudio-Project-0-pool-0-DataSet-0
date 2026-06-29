"""
账户管理模块

提供资金账户创建、余额管理、利息计算、手续费结构等功能。
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ai_llm_agent_crawler.finance_game.models import (
    Account,
    AccountType,
    Currency,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class FeeStructure:
    """手续费结构"""

    def __init__(
        self,
        maker_fee: float = 0.001,
        taker_fee: float = 0.002,
        deposit_fee: float = 0.0,
        withdrawal_fee: float = 0.005,
        transfer_fee: float = 0.001,
        min_fee: float = 0.0,
        max_fee: Optional[float] = None,
        fee_discount_tiers: Optional[Dict[int, float]] = None,
    ):
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.deposit_fee = deposit_fee
        self.withdrawal_fee = withdrawal_fee
        self.transfer_fee = transfer_fee
        self.min_fee = min_fee
        self.max_fee = max_fee
        self.fee_discount_tiers = fee_discount_tiers or {}

    def calculate_trade_fee(
        self, amount: float, price: float, is_maker: bool = False, volume_tier: int = 0
    ) -> float:
        notional = amount * price
        fee_rate = self.maker_fee if is_maker else self.taker_fee
        discount = self.fee_discount_tiers.get(volume_tier, 0.0)
        effective_rate = fee_rate * (1 - discount)
        fee = notional * effective_rate
        fee = max(fee, self.min_fee)
        if self.max_fee is not None:
            fee = min(fee, self.max_fee)
        return fee

    def calculate_deposit_fee(self, amount: float) -> float:
        return amount * self.deposit_fee

    def calculate_withdrawal_fee(self, amount: float) -> float:
        fee = amount * self.withdrawal_fee
        return max(fee, self.min_fee)

    def calculate_transfer_fee(self, amount: float) -> float:
        fee = amount * self.transfer_fee
        return max(fee, self.min_fee)


class InterestCalculator:
    """利息计算器"""

    def __init__(
        self,
        annual_rate: float = 0.05,
        compound_frequency: str = "daily",
        min_balance_for_interest: float = 0.0,
    ):
        self.annual_rate = annual_rate
        self.compound_frequency = compound_frequency
        self.min_balance_for_interest = min_balance_for_interest

    def get_periods_per_year(self) -> int:
        frequencies = {
            "daily": 365,
            "weekly": 52,
            "monthly": 12,
            "quarterly": 4,
            "annually": 1,
        }
        return frequencies.get(self.compound_frequency, 365)

    def calculate_interest(
        self, principal: float, days: int, rate: Optional[float] = None
    ) -> float:
        if principal < self.min_balance_for_interest:
            return 0.0
        annual_rate = rate if rate is not None else self.annual_rate
        n = self.get_periods_per_year()
        t = days / 365.0
        amount = principal * (1 + annual_rate / n) ** (n * t)
        return amount - principal

    def calculate_simple_interest(self, principal: float, days: int, rate: Optional[float] = None) -> float:
        annual_rate = rate if rate is not None else self.annual_rate
        return principal * annual_rate * (days / 365.0)


class AccountLedger:
    """账户分类账"""

    def __init__(self):
        self._accounts: Dict[str, Account] = {}
        self._transactions: List[Transaction] = []
        self._user_accounts: Dict[str, List[str]] = {}

    def create_account(
        self,
        user_id: str,
        account_type: AccountType = AccountType.MAIN,
        name: str = "",
        initial_balances: Optional[Dict[str, float]] = None,
    ) -> Account:
        account = Account(
            user_id=user_id,
            account_type=account_type,
            name=name or f"{account_type.value}_{user_id[:8]}",
            balances=initial_balances or {},
        )
        self._accounts[account.account_id] = account
        if user_id not in self._user_accounts:
            self._user_accounts[user_id] = []
        self._user_accounts[user_id].append(account.account_id)
        logger.info(f"Account created: {account.account_id} for user {user_id}")
        return account

    def get_account(self, account_id: str) -> Optional[Account]:
        return self._accounts.get(account_id)

    def get_user_accounts(self, user_id: str) -> List[Account]:
        account_ids = self._user_accounts.get(user_id, [])
        return [self._accounts[aid] for aid in account_ids if aid in self._accounts]

    def get_account_by_type(self, user_id: str, account_type: AccountType) -> Optional[Account]:
        accounts = self.get_user_accounts(user_id)
        for acc in accounts:
            if acc.account_type == account_type:
                return acc
        return None

    def get_total_balance(self, user_id: str, currency: str) -> float:
        accounts = self.get_user_accounts(user_id)
        return sum(acc.get_total_balance(currency) for acc in accounts)

    def record_transaction(self, transaction: Transaction) -> None:
        self._transactions.append(transaction)

    def get_transactions(
        self,
        account_id: Optional[str] = None,
        user_id: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        txns = self._transactions
        if account_id:
            txns = [
                t for t in txns
                if t.from_account_id == account_id or t.to_account_id == account_id
            ]
        if user_id:
            user_account_ids = set(self._user_accounts.get(user_id, []))
            txns = [
                t for t in txns
                if t.from_account_id in user_account_ids or t.to_account_id in user_account_ids
            ]
        if transaction_type:
            txns = [t for t in txns if t.transaction_type == transaction_type]
        txns = sorted(txns, key=lambda t: t.created_at, reverse=True)
        return txns[offset:offset + limit]


class AccountManager:
    """账户管理器"""

    def __init__(
        self,
        fee_structure: Optional[FeeStructure] = None,
        interest_calculator: Optional[InterestCalculator] = None,
    ):
        self.ledger = AccountLedger()
        self.fee_structure = fee_structure or FeeStructure()
        self.interest_calculator = interest_calculator or InterestCalculator()
        self.logger = get_logger(f"{__name__}.AccountManager")

    def create_user_accounts(
        self,
        user_id: str,
        initial_balances: Optional[Dict[str, float]] = None,
    ) -> Dict[AccountType, Account]:
        accounts = {}
        balances = initial_balances or {}
        for acc_type in [AccountType.MAIN, AccountType.TRADING, AccountType.SAVINGS, AccountType.REWARD]:
            acc_balances = {}
            if acc_type == AccountType.MAIN:
                acc_balances = balances.copy()
            accounts[acc_type] = self.ledger.create_account(
                user_id=user_id,
                account_type=acc_type,
                initial_balances=acc_balances,
            )
        return accounts

    def deposit(
        self,
        account_id: str,
        currency: str,
        amount: float,
        description: str = "",
        reference_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[Transaction]]:
        account = self.ledger.get_account(account_id)
        if not account:
            self.logger.error(f"Account not found: {account_id}")
            return False, None

        fee = self.fee_structure.calculate_deposit_fee(amount)
        net_amount = amount - fee

        transaction = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            to_account_id=account_id,
            amount=net_amount,
            currency=Currency(currency) if currency in Currency.__members__.values() else Currency.USD,
            fee=fee,
            description=description or f"Deposit of {net_amount} {currency}",
            reference_id=reference_id,
        )

        account.deposit(currency, net_amount)
        self.ledger.record_transaction(transaction)
        self.logger.info(f"Deposit: {net_amount} {currency} to {account_id}")
        return True, transaction

    def withdraw(
        self,
        account_id: str,
        currency: str,
        amount: float,
        description: str = "",
        reference_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[Transaction]]:
        account = self.ledger.get_account(account_id)
        if not account:
            self.logger.error(f"Account not found: {account_id}")
            return False, None

        fee = self.fee_structure.calculate_withdrawal_fee(amount)
        total_required = amount + fee

        if account.get_available_balance(currency) < total_required:
            self.logger.warning(f"Insufficient balance for withdrawal from {account_id}")
            return False, None

        transaction = Transaction(
            transaction_type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED,
            from_account_id=account_id,
            amount=amount,
            currency=Currency(currency) if currency in Currency.__members__.values() else Currency.USD,
            fee=fee,
            description=description or f"Withdrawal of {amount} {currency}",
            reference_id=reference_id,
        )

        success = account.withdraw(currency, total_required)
        if success:
            self.ledger.record_transaction(transaction)
            self.logger.info(f"Withdrawal: {amount} {currency} from {account_id} (fee: {fee})")
            return True, transaction
        return False, None

    def transfer(
        self,
        from_account_id: str,
        to_account_id: str,
        currency: str,
        amount: float,
        description: str = "",
    ) -> Tuple[bool, Optional[Transaction]]:
        from_account = self.ledger.get_account(from_account_id)
        to_account = self.ledger.get_account(to_account_id)

        if not from_account or not to_account:
            self.logger.error("Account not found for transfer")
            return False, None

        fee = self.fee_structure.calculate_transfer_fee(amount)
        total_required = amount + fee

        if from_account.get_available_balance(currency) < total_required:
            self.logger.warning("Insufficient balance for transfer")
            return False, None

        transaction = Transaction(
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.COMPLETED,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            currency=Currency(currency) if currency in Currency.__members__.values() else Currency.USD,
            fee=fee,
            description=description or f"Transfer of {amount} {currency}",
        )

        if from_account.withdraw(currency, total_required):
            to_account.deposit(currency, amount)
            self.ledger.record_transaction(transaction)
            self.logger.info(f"Transfer: {amount} {currency} from {from_account_id} to {to_account_id}")
            return True, transaction
        return False, None

    def apply_interest(self, account_id: str, currency: str, days: int) -> Tuple[bool, Optional[Transaction]]:
        account = self.ledger.get_account(account_id)
        if not account:
            return False, None

        balance = account.get_total_balance(currency)
        interest = self.interest_calculator.calculate_interest(balance, days)

        if interest <= 0:
            return False, None

        transaction = Transaction(
            transaction_type=TransactionType.INTEREST,
            status=TransactionStatus.COMPLETED,
            to_account_id=account_id,
            amount=interest,
            currency=Currency(currency) if currency in Currency.__members__.values() else Currency.USD,
            description=f"Interest for {days} days",
        )

        account.deposit(currency, interest)
        self.ledger.record_transaction(transaction)
        return True, transaction

    def freeze_balance(self, account_id: str, currency: str, amount: float) -> bool:
        account = self.ledger.get_account(account_id)
        if not account:
            return False
        return account.freeze(currency, amount)

    def unfreeze_balance(self, account_id: str, currency: str, amount: float) -> bool:
        account = self.ledger.get_account(account_id)
        if not account:
            return False
        return account.unfreeze(currency, amount)

    def get_account_summary(self, user_id: str) -> Dict[str, Any]:
        accounts = self.ledger.get_user_accounts(user_id)
        total_balances: Dict[str, float] = {}
        for acc in accounts:
            for cur, bal in acc.balances.items():
                total_balances[cur] = total_balances.get(cur, 0.0) + bal

        return {
            "user_id": user_id,
            "account_count": len(accounts),
            "total_balances": total_balances,
            "accounts": [
                {
                    "account_id": acc.account_id,
                    "account_type": acc.account_type.value,
                    "balances": acc.balances,
                    "frozen_balances": acc.frozen_balances,
                }
                for acc in accounts
            ],
        }
