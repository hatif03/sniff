"""Tests for shared LLM JSON parsing helpers."""

import json

import pytest

from src.agent.json_response import parse_json_object


def test_parse_json_object_strips_fences():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_object_extracts_embedded_object():
    assert parse_json_object('Analysis:\n{"a": 1}\nDone.') == {"a": 1}


def test_parse_json_object_raises_on_garbage():
    with pytest.raises(json.JSONDecodeError):
        parse_json_object("not json")
