"""Acceptance tests for the budget subsystem (spec §7.2)."""
import asyncio
import pytest
from uuid import uuid4

from budget.tokenizer import estimate_tokens
from budget.session_budget import SessionBudget


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 1


def test_estimate_tokens_cjk():
    # 4 CJK chars / 1.6 = 2.5 → floor → 2
    assert estimate_tokens("你好世界") == 2


def test_estimate_tokens_latin():
    # 11 chars / 1.3 = 8.46 → floor → 8
    assert estimate_tokens("Hello world") == 8


def test_estimate_tokens_mixed():
    # "Hello " = 6 Latin chars → int(6/1.3) = 4
    # "世界"     = 2 CJK chars  → int(2/1.6) = 1
    # total = 5
    assert estimate_tokens("Hello 世界") == 5


@pytest.mark.asyncio
async def test_reserve_succeeds_within_cap():
    b = SessionBudget(uuid4(), cap=1000)
    assert await b.reserve(500) is True
    assert b.reserved == 500


@pytest.mark.asyncio
async def test_reserve_fails_over_cap():
    b = SessionBudget(uuid4(), cap=1000)
    await b.reserve(900)
    assert await b.reserve(200) is False


@pytest.mark.asyncio
async def test_charge_reconciles_reservation():
    b = SessionBudget(uuid4(), cap=1000)
    await b.reserve(500)
    await b.charge(actual_out=300, reserved=500)
    assert b.reserved == 0
    assert b.consumed == 300


@pytest.mark.asyncio
async def test_budget_status_transitions():
    b = SessionBudget(uuid4(), cap=1000)
    assert b.status == "healthy"
    await b.reserve(900)
    assert b.status == "warning"
    await b.charge(actual_out=950, reserved=900)
    # consumed=950, reserved=0 → 95% → still warning
    assert b.status == "warning"
    await b.reserve(60)
    assert b.status == "exhausted"


@pytest.mark.asyncio
async def test_concurrent_reservations_no_overshoot():
    b = SessionBudget(uuid4(), cap=1000)
    results = await asyncio.gather(*[b.reserve(600) for _ in range(3)])
    assert sum(results) == 1   # only one succeeds
    assert b.reserved == 600
