"""
Consolidated Account Manager v1.0.0
Clean Architecture - Konsolidiert 13 Over-Engineering Module in eine saubere Klasse
SOLID Principles: Single Responsibility mit klarer Interface-Trennung
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from enum import Enum
from pathlib import Path
import sys

# Zentrale Konfiguration verwenden
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.central_config_v1_0_0_20250821 import config

class TransactionType(Enum):
    """Transaction Type Enumeration"""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRADE_BUY = "trade_buy"
    TRADE_SELL = "trade_sell"
    FEE = "fee"

class Transaction:
    """Clean Transaction Data Model"""
    
    def __init__(self, transaction_type: TransactionType, amount: Decimal, 
                 symbol: str = "EUR", description: str = ""):
        self.id = self._generate_transaction_id()
        self.type = transaction_type
        self.amount = amount
        self.symbol = symbol
        self.description = description
        self.timestamp = datetime.now()
        self.balance_after = Decimal('0')  # Will be set by account manager
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = int(datetime.now().timestamp() * 1000)
        return f"TXN_{timestamp}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "type": self.type.value,
            "amount": str(self.amount),
            "symbol": self.symbol,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "balance_after": str(self.balance_after)
        }

class PortfolioPosition:
    """Portfolio Position Data Model"""
    
    def __init__(self, symbol: str, quantity: Decimal, average_price: Decimal):
        self.symbol = symbol
        self.quantity = quantity
        self.average_price = average_price
        self.last_updated = datetime.now()
    
    @property
    def market_value(self) -> Decimal:
        """Calculate current market value (simplified)"""
        # In real implementation, this would fetch current market price
        current_price = self.average_price * Decimal('1.05')  # Mock 5% gain
        return self.quantity * current_price
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Calculate unrealized P&L"""
        cost_basis = self.quantity * self.average_price
        return self.market_value - cost_basis
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "symbol": self.symbol,
            "quantity": str(self.quantity),
            "average_price": str(self.average_price),
            "market_value": str(self.market_value),
            "unrealized_pnl": str(self.unrealized_pnl),
            "last_updated": self.last_updated.isoformat()
        }

class RiskAssessment:
    """Risk Assessment Logic - Single Responsibility"""
    
    def __init__(self):
        self.config = config
    
    def assess_account_risk(self, balance: Decimal, positions: Dict[str, PortfolioPosition]) -> Dict[str, Any]:
        """Comprehensive account risk assessment"""
        total_portfolio_value = balance
        total_unrealized_pnl = Decimal('0')
        
        # Calculate portfolio metrics
        for position in positions.values():
            total_portfolio_value += position.market_value
            total_unrealized_pnl += position.unrealized_pnl
        
        # Risk metrics
        cash_ratio = balance / total_portfolio_value if total_portfolio_value > 0 else Decimal('1')
        pnl_ratio = total_unrealized_pnl / total_portfolio_value if total_portfolio_value > 0 else Decimal('0')
        
        # Risk level calculation
        risk_level = self._calculate_risk_level(cash_ratio, pnl_ratio, len(positions))
        
        return {
            "risk_level": risk_level,
            "total_portfolio_value": str(total_portfolio_value),
            "cash_ratio": str(cash_ratio),
            "unrealized_pnl_ratio": str(pnl_ratio),
            "diversification_score": self._calculate_diversification_score(positions),
            "recommendations": self._generate_risk_recommendations(risk_level, cash_ratio)
        }
    
    def _calculate_risk_level(self, cash_ratio: Decimal, pnl_ratio: Decimal, position_count: int) -> str:
        """Calculate overall risk level"""
        risk_score = 0
        
        # Cash ratio factor
        if cash_ratio < Decimal('0.1'):  # Less than 10% cash
            risk_score += 3
        elif cash_ratio < Decimal('0.2'):  # Less than 20% cash
            risk_score += 2
        elif cash_ratio < Decimal('0.3'):  # Less than 30% cash
            risk_score += 1
        
        # P&L factor
        if pnl_ratio < Decimal('-0.2'):  # More than 20% loss
            risk_score += 3
        elif pnl_ratio < Decimal('-0.1'):  # More than 10% loss
            risk_score += 2
        
        # Diversification factor
        if position_count < 3:
            risk_score += 2
        elif position_count < 5:
            risk_score += 1
        
        # Risk level mapping
        if risk_score >= 6:
            return "HIGH"
        elif risk_score >= 3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_diversification_score(self, positions: Dict[str, PortfolioPosition]) -> str:
        """Calculate portfolio diversification score"""
        if len(positions) >= 10:
            return "EXCELLENT"
        elif len(positions) >= 5:
            return "GOOD"
        elif len(positions) >= 3:
            return "MODERATE"
        else:
            return "POOR"
    
    def _generate_risk_recommendations(self, risk_level: str, cash_ratio: Decimal) -> List[str]:
        """Generate risk-based recommendations"""
        recommendations = []
        
        if risk_level == "HIGH":
            recommendations.append("Consider reducing position sizes")
            recommendations.append("Increase cash reserves")
            if cash_ratio < Decimal('0.1'):
                recommendations.append("URGENT: Cash ratio below 10%")
        
        elif risk_level == "MEDIUM":
            recommendations.append("Monitor positions closely")
            if cash_ratio < Decimal('0.2'):
                recommendations.append("Consider increasing cash reserves")
        
        else:  # LOW risk
            recommendations.append("Portfolio risk within acceptable levels")
            if cash_ratio > Decimal('0.5'):
                recommendations.append("Consider increasing investment allocation")
        
        return recommendations

class ConsolidatedAccountManager:
    """
    Consolidated Account Manager - Clean Architecture
    Ersetzt 13 Over-Engineering Module mit sauberer Single-Class-Lösung
    SOLID Principles: Delegation an spezialisierte Komponenten
    """
    
    def __init__(self, initial_balance: Decimal = Decimal('10000')):
        self.account_id = "ACC_MAIN"
        self.balance = initial_balance
        self.positions: Dict[str, PortfolioPosition] = {}
        self.transaction_history: List[Transaction] = []
        self.risk_assessor = RiskAssessment()
        self.created_at = datetime.now()
        
        # Initial deposit transaction
        initial_transaction = Transaction(
            TransactionType.DEPOSIT,
            initial_balance,
            description="Initial account funding"
        )
        initial_transaction.balance_after = initial_balance
        self.transaction_history.append(initial_transaction)
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Get current account balance and summary"""
        total_portfolio_value = self.balance
        total_positions_value = Decimal('0')
        
        for position in self.positions.values():
            total_positions_value += position.market_value
        
        total_portfolio_value += total_positions_value
        
        return {
            "account_id": self.account_id,
            "cash_balance": str(self.balance),
            "positions_value": str(total_positions_value),
            "total_portfolio_value": str(total_portfolio_value),
            "currency": "EUR",
            "last_updated": datetime.now().isoformat()
        }
    
    def deposit_funds(self, amount: Decimal, description: str = "") -> Dict[str, Any]:
        """Deposit funds to account"""
        if amount <= 0:
            return {
                "success": False,
                "error": "Deposit amount must be positive"
            }
        
        # Create transaction
        transaction = Transaction(
            TransactionType.DEPOSIT,
            amount,
            description=description or f"Deposit of {amount} EUR"
        )
        
        # Update balance
        self.balance += amount
        transaction.balance_after = self.balance
        self.transaction_history.append(transaction)
        
        return {
            "success": True,
            "transaction_id": transaction.id,
            "new_balance": str(self.balance),
            "transaction": transaction.to_dict()
        }
    
    def withdraw_funds(self, amount: Decimal, description: str = "") -> Dict[str, Any]:
        """Withdraw funds from account"""
        if amount <= 0:
            return {
                "success": False,
                "error": "Withdrawal amount must be positive"
            }
        
        if amount > self.balance:
            return {
                "success": False,
                "error": "Insufficient funds"
            }
        
        # Create transaction
        transaction = Transaction(
            TransactionType.WITHDRAWAL,
            -amount,  # Negative for withdrawal
            description=description or f"Withdrawal of {amount} EUR"
        )
        
        # Update balance
        self.balance -= amount
        transaction.balance_after = self.balance
        self.transaction_history.append(transaction)
        
        return {
            "success": True,
            "transaction_id": transaction.id,
            "new_balance": str(self.balance),
            "transaction": transaction.to_dict()
        }
    
    def update_position(self, symbol: str, quantity_change: Decimal, 
                       price: Decimal, order_type: str) -> Dict[str, Any]:
        """Update portfolio position from trade"""
        try:
            # Create trade transaction
            transaction_type = TransactionType.TRADE_BUY if quantity_change > 0 else TransactionType.TRADE_SELL
            trade_value = abs(quantity_change * price)
            
            # Update cash balance
            if quantity_change > 0:  # Buy
                if trade_value > self.balance:
                    return {
                        "success": False,
                        "error": "Insufficient funds for purchase"
                    }
                self.balance -= trade_value
            else:  # Sell
                self.balance += trade_value
            
            # Update position
            if symbol in self.positions:
                position = self.positions[symbol]
                old_quantity = position.quantity
                old_value = old_quantity * position.average_price
                
                new_quantity = old_quantity + quantity_change
                if new_quantity <= 0:
                    # Position closed
                    del self.positions[symbol]
                    new_avg_price = Decimal('0')
                else:
                    # Update average price
                    new_value = old_value + (quantity_change * price)
                    new_avg_price = new_value / new_quantity
                    position.quantity = new_quantity
                    position.average_price = new_avg_price
                    position.last_updated = datetime.now()
            else:
                # New position
                if quantity_change > 0:
                    self.positions[symbol] = PortfolioPosition(symbol, quantity_change, price)
                else:
                    return {
                        "success": False,
                        "error": "Cannot sell position that doesn't exist"
                    }
            
            # Create transaction record
            transaction = Transaction(
                transaction_type,
                -trade_value if quantity_change > 0 else trade_value,
                symbol,
                f"{order_type} {abs(quantity_change)} {symbol} @ {price}"
            )
            transaction.balance_after = self.balance
            self.transaction_history.append(transaction)
            
            return {
                "success": True,
                "transaction_id": transaction.id,
                "new_balance": str(self.balance),
                "position": self.positions[symbol].to_dict() if symbol in self.positions else None
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Position update failed: {str(e)}"
            }
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        account_balance = self.get_account_balance()
        risk_assessment = self.risk_assessor.assess_account_risk(self.balance, self.positions)
        
        positions_list = [pos.to_dict() for pos in self.positions.values()]
        
        return {
            "account": account_balance,
            "positions": positions_list,
            "risk_assessment": risk_assessment,
            "summary": {
                "total_positions": len(self.positions),
                "account_age_days": (datetime.now() - self.created_at).days,
                "total_transactions": len(self.transaction_history)
            }
        }
    
    def get_transaction_history(self, limit: int = 50, 
                              transaction_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get transaction history with optional filtering"""
        transactions = self.transaction_history
        
        # Filter by type if specified
        if transaction_type:
            try:
                filter_type = TransactionType(transaction_type.lower())
                transactions = [t for t in transactions if t.type == filter_type]
            except ValueError:
                pass  # Invalid type, return all
        
        # Sort by timestamp (newest first) and limit
        sorted_transactions = sorted(transactions, key=lambda x: x.timestamp, reverse=True)
        return [t.to_dict() for t in sorted_transactions[:limit]]

# Global instance for service use
account_manager = ConsolidatedAccountManager()