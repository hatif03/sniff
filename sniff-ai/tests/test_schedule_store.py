"""Tests for ScheduleStore's atomic tick-claim logic (src/integrations/supabase_client.py).

This is the reliability-critical piece of the scheduling feature: the FastAPI
backend autoscales to multiple Cloud Run instances, so claiming a due
schedule must be safe under concurrent/overlapping tick calls. Real
row-level serialization is a Postgres guarantee we can't exercise without a
live database, so these tests verify the piece we *can* control: the claim
always issues the correct WHERE guards, and correctly reports failure when
the underlying update affects zero rows (which is exactly what happens when
a concurrent caller already claimed the row first).
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.integrations.supabase_client import ScheduleStore


def _store_with_mock_client() -> tuple[ScheduleStore, MagicMock]:
    store = ScheduleStore.__new__(ScheduleStore)  # skip __init__'s real create_client call
    mock_client = MagicMock()
    store.client = mock_client
    return store, mock_client


def test_claim_due_schedule_issues_correct_guards():
    store, mock_client = _store_with_mock_client()
    table = mock_client.table.return_value
    update_chain = table.update.return_value
    eq1 = update_chain.eq.return_value
    eq2 = eq1.eq.return_value
    lte = eq2.lte.return_value
    lte.execute.return_value = MagicMock(data=[{"schedule_id": "sched_abc"}])

    now = datetime(2026, 1, 1, 12, 0, 0)
    won = store.claim_due_schedule("sched_abc", interval_minutes=30, now=now)

    assert won is True
    mock_client.table.assert_called_with("schedules")
    table.update.assert_called_once()
    updated_fields = table.update.call_args[0][0]
    assert updated_fields["next_run_at"] == (now + timedelta(minutes=30)).isoformat()
    assert updated_fields["last_triggered_at"] == now.isoformat()
    update_chain.eq.assert_called_with("schedule_id", "sched_abc")
    eq1.eq.assert_called_with("enabled", True)
    eq2.lte.assert_called_with("next_run_at", now.isoformat())


def test_claim_due_schedule_loses_race_when_already_claimed():
    """A concurrent tick already moved next_run_at into the future - the
    UPDATE's own WHERE clause then matches zero rows, postgrest returns an
    empty data list, and claim_due_schedule must report this as a loss, not
    raise or silently report success."""
    store, mock_client = _store_with_mock_client()
    execute_result = (
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.lte.return_value.execute
    )
    execute_result.return_value = MagicMock(data=[])

    won = store.claim_due_schedule("sched_abc", interval_minutes=30, now=datetime(2026, 1, 1, 12, 0, 0))

    assert won is False


def test_get_due_schedule_ids_filters_enabled_and_due():
    store, mock_client = _store_with_mock_client()
    select_chain = mock_client.table.return_value.select.return_value.eq.return_value.lte.return_value
    select_chain.execute.return_value = MagicMock(data=[{"schedule_id": "a"}, {"schedule_id": "b"}])

    ids = store.get_due_schedule_ids(datetime(2026, 1, 1, 12, 0, 0))

    assert ids == ["a", "b"]
    mock_client.table.return_value.select.return_value.eq.assert_called_with("enabled", True)
