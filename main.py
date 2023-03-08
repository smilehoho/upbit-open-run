import time
from dataclasses import dataclass
from decimal import Decimal

import pyupbit
from dotenv import dotenv_values


@dataclass
class GoldenEgg:
    ticker: str
    max_value: int = 1000000
    target_rate_of_return: float = 1.02
    add_coefficient: int = 30
    is_new: bool = True


class Constants:
    FIRST_BUY_VALUE: int = 5001
    ORDER_DELAY: int = 13
    LOOP_DELAY: int = 13
    ADD_BUY_RATE: float = 0.1


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


upbit = pyupbit.Upbit(**dotenv_values())
egg = GoldenEgg(ticker="KRW-WAVES", max_value=400000)

while True:
    balances = upbit.get_balances()
    krw = next(filter(lambda x: x["currency"] == "KRW", balances))
    balance = next(filter(lambda x: x["currency"] == egg.ticker.split("-")[1], balances), None)
    orders = upbit.get_order(egg.ticker)

    # first buy
    if egg.is_new is True and balance is None:
        result = upbit.buy_market_order(egg.ticker, Constants.FIRST_BUY_VALUE)
        print(now(), "FIRST", result)
        time.sleep(Constants.ORDER_DELAY)
        continue

    # sell
    if float(balance["balance"]) > 0:
        price = float(balance["avg_buy_price"]) * egg.target_rate_of_return
        price = pyupbit.get_tick_size(price, "ceil")
        volume = Decimal(balance["balance"])

        # cancel
        for o in filter(lambda x: x["side"] == "ask" and float(x["price"]) != price, orders):
            upbit.cancel_order(o["uuid"])
            print(now(), "CANCEL", o["market"], o["uuid"])
            volume += Decimal(o["remaining_volume"])

        o = upbit.sell_limit_order(egg.ticker, price, volume)
        amount = Decimal(o["price"]) * Decimal(o["volume"])
        egg.is_new = False
        print(now(), "SELL", o["market"], f'{o["price"]} * {o["volume"]} = {amount:,.0f}')
        time.sleep(Constants.ORDER_DELAY)
        continue

    # add buy
    if next(filter(lambda x: x["side"] == "bid", orders), None) is None:
        value = (float(balance["balance"]) + float(balance["locked"])) * float(balance["avg_buy_price"])

        if value > egg.max_value:
            time.sleep(Constants.LOOP_DELAY)
            continue

        ratio = value / egg.max_value
        price = float(balance["avg_buy_price"]) * (1 - ratio / egg.add_coefficient)
        price = pyupbit.get_tick_size(price, "floor")
        volume = value * Constants.ADD_BUY_RATE / price
        o = upbit.buy_limit_order(egg.ticker, price, volume)
        amount = Decimal(o["price"]) * Decimal(o["volume"])
        print(now(), "BUY", o["market"], f'{o["price"]} * {o["volume"]} = {amount:,.0f}')
        time.sleep(Constants.ORDER_DELAY)

    if egg.is_new is False and balance is None:
        print(now(), "FINISH..")
        break

    time.sleep(Constants.LOOP_DELAY)
