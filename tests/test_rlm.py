"""Pytest entrypoints.

These delegate to the existing TestRLM methods so the bodies don't get
duplicated during the initial migration. Inlining the bodies as proper
pytest-idiomatic tests is tracked separately.
"""

from rlm import TestRLM


def test_board_generation_from_piece_list_1():
    TestRLM().test_board_generation_from_piece_list_1()


def test_move_generation_1():
    TestRLM().test_move_generation_1()


def test_move_generation_2():
    TestRLM().test_move_generation_2()


def test_pawn_moves_1():
    TestRLM().test_pawn_moves_1()


def test_entered_move_processing():
    TestRLM().test_entered_move_processing()
