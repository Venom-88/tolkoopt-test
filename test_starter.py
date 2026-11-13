"""Тесты recommend_price. Запуск: python -m unittest -v test_starter.py"""

import asyncio
import unittest
from decimal import Decimal as D

from starter import recommend_price, sample_fetch_offers


def source(offers, status="success"):
    """Имитация fetch_offers с заданными предложениями."""
    async def fetch():
        return {"status": status, "offers": offers}
    return fetch


def offer(seller, price, days):
    return {"seller": seller, "price": D(price), "delivery_days": days}


class RecommendPriceTest(unittest.IsolatedAsyncioTestCase):

    async def test_example_from_task(self):
        res = await recommend_price(sample_fetch_offers, D("4900.00"), D("4500.00"))
        self.assertEqual(res["price"], D("4728.00"))
        self.assertIsInstance(res["price"], D)
        self.assertEqual(res["decision"], "APPLY")

    async def test_timeout_returns_hold(self):
        async def slow():
            await asyncio.sleep(10)
        res = await recommend_price(slow, D("1000.00"), D("900.00"), timeout_s=0.05)
        self.assertEqual((res["price"], res["decision"]), (D("1000.00"), "HOLD"))

    async def test_source_error_and_partial_return_hold(self):
        async def broken():
            raise ConnectionError("площадка недоступна")
        partial = source([offer("PARTS", "500.00", 1)], status="partial")
        for fetch in (broken, partial):
            res = await recommend_price(fetch, D("1000.00"), D("900.00"))
            self.assertEqual((res["price"], res["decision"]), (D("1000.00"), "HOLD"))

    async def test_no_suitable_offers_hold_even_below_min_price(self):
        fetch = source([
            offer("MyShop", "100.00", 1),     # наш магазин, любой регистр
            offer("NODATE", "100.00", None),  # доставка неизвестна
            offer("SLOW", "100.00", 7),       # дольше 6 дней
        ])
        res = await recommend_price(fetch, D("400.00"), D("500.00"))
        self.assertEqual((res["price"], res["decision"]), (D("400.00"), "HOLD"))

    async def test_rounds_down_to_kopeck(self):
        # 100.30 * 0.985 = 98.7955 -> вниз 98.79 (обычное округление дало бы 98.80)
        fetch = source([offer("PARTS", "100.30", 0)])
        res = await recommend_price(fetch, D("100.00"), D("50.00"))
        self.assertEqual((res["price"], res["decision"]), (D("98.79"), "APPLY"))

    async def test_exactly_30_percent_is_apply(self):
        cheap = source([offer("PARTS", "500.00", 1)])  # 492.50 < min_price
        up = await recommend_price(cheap, D("1000.00"), D("1300.00"))
        down = await recommend_price(cheap, D("1000.00"), D("700.00"))
        self.assertEqual((up["price"], up["decision"]), (D("1300.00"), "APPLY"))
        self.assertEqual((down["price"], down["decision"]), (D("700.00"), "APPLY"))

    async def test_more_than_30_percent_is_review(self):
        cheap = source([offer("PARTS", "500.00", 1)])
        up = await recommend_price(cheap, D("1000.00"), D("1300.01"))
        down = await recommend_price(cheap, D("1000.00"), D("699.99"))
        self.assertEqual(up["decision"], "REVIEW")
        self.assertEqual(down["decision"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
