"""
Reusable In-Memory Paper Broker Template with Realistic Fees and Slippage.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class PositionSide(str, Enum):
    FLAT = "FLAT"
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class Position:
    symbol: str
    side: PositionSide = PositionSide.FLAT
    size: float = 0.0
    entry_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    peak_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

class PaperBroker:
    def __init__(
        self,
        initial_cash: float = 10000.0,
        maker_fee: float = 0.0002,   # 0.02%
        taker_fee: float = 0.0004,   # 0.04%
        slippage_bps: float = 1.5     # 1.5 bps
    ):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage_pct = slippage_bps / 10000.0
        self.positions: Dict[str, Position] = {}

    def get_position(self, symbol: str) -> Position:
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]

    def get_equity(self) -> float:
        return self.cash + sum(p.unrealized_pnl for p in self.positions.values())

    def on_tick(self, symbol: str, price: float):
        pos = self.get_position(symbol)
        if pos.side == PositionSide.FLAT:
            return

        if pos.side == PositionSide.LONG:
            pos.peak_price = max(pos.peak_price, price)
            pos.unrealized_pnl = (price - pos.entry_price) * pos.size
            if pos.stop_loss and price <= pos.stop_loss:
                self.close(symbol, price)
            elif pos.take_profit and price >= pos.take_profit:
                self.close(symbol, price)
        elif pos.side == PositionSide.SHORT:
            pos.peak_price = min(pos.peak_price, price)
            pos.unrealized_pnl = (pos.entry_price - price) * pos.size
            if pos.stop_loss and price >= pos.stop_loss:
                self.close(symbol, price)
            elif pos.take_profit and price <= pos.take_profit:
                self.close(symbol, price)

    def open(self, symbol: str, side: PositionSide, qty: float, price: float, sl: Optional[float], tp: Optional[float]):
        pos = self.get_position(symbol)
        exec_price = price * (1.0 + self.slippage_pct if side == PositionSide.LONG else 1.0 - self.slippage_pct)
        fee = exec_price * qty * self.taker_fee
        self.cash -= fee
        pos.side = side
        pos.size = qty
        pos.entry_price = exec_price
        pos.peak_price = exec_price
        pos.stop_loss = sl
        pos.take_profit = tp

    def close(self, symbol: str, price: float):
        pos = self.get_position(symbol)
        if pos.side == PositionSide.FLAT:
            return
        exec_price = price * (1.0 - self.slippage_pct if pos.side == PositionSide.LONG else 1.0 + self.slippage_pct)
        fee = exec_price * pos.size * self.taker_fee
        pnl = ((exec_price - pos.entry_price) if pos.side == PositionSide.LONG else (pos.entry_price - exec_price)) * pos.size
        self.cash += pnl - fee
        pos.realized_pnl += pnl
        pos.side = PositionSide.FLAT
        pos.size = 0.0
        pos.unrealized_pnl = 0.0
