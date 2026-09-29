"""Owned model of inspected boolean branches, NOT Adobe code/runtime evidence.

Assumes boolean inputs, stable state during dispatch and a connected observer.
See COMMAND-COMPLETION-MATRIX-2026-09-29.md for exact-build static evidence.
Never loads Adobe binaries, attaches to AE or implements a shipping adapter.
"""
import itertools
import unittest


def setter_branch_model(state, field, value):
    """Represent observed higher-priority suppression and remaining OR state."""
    result = list(state)
    result[field] = value
    # Command: none; group: command; Undo/Redo: command or group.
    prefix = (0, 1, 2, 2)[field]
    if any(state[:prefix]):
        return tuple(result), None
    before = any(state[prefix:])
    after = any(result[prefix:])
    event = None
    if not before and after:
        event = "started"
    elif before and not after:
        event = "completed"
    return tuple(result), event


def run_trace(steps):
    state = (False,) * 4
    events = []
    for field, value in steps:
        state, event = setter_branch_model(state, field, value)
        if event:
            events.append(event)
    return state, events


class CommandActivityModelTests(unittest.TestCase):
    def test_all_128_boolean_transitions_match_aggregate_edges(self):
        cases = 0
        for state in itertools.product((False, True), repeat=4):
            for field in range(4):
                for value in (False, True):
                    with self.subTest(state=state, field=field, value=value):
                        updated, observed = setter_branch_model(state, field, value)
                        expected_state = tuple(value if i == field else state[i]
                                               for i in range(4))
                        before, after = any(state), any(expected_state)
                        expected = ("started" if after else "completed") if before != after else None
                        self.assertEqual(updated, expected_state)
                        self.assertEqual(observed, expected)
                        cases += 1
        self.assertEqual(cases, 128)

    def test_two_commands_in_one_group_have_one_completion(self):
        state, events = run_trace([(1, True), (0, True), (0, False),
                                   (0, True), (0, False), (1, False)])
        self.assertEqual(state, (False,) * 4)
        self.assertEqual(events, ["started", "completed"])

    def test_separate_commands_have_separate_completions(self):
        _, events = run_trace([(0, True), (0, False)] * 2)
        self.assertEqual(events, ["started", "completed"] * 2)

    def test_repeated_values_do_not_emit_duplicate_edges(self):
        for field in range(4):
            with self.subTest(field=field):
                _, events = run_trace([(field, False), (field, True),
                                       (field, True), (field, False), (field, False)])
                self.assertEqual(events, ["started", "completed"])

    def test_undo_redo_overlap_waits_for_last_active_flag(self):
        _, events = run_trace([(2, True), (3, True), (2, False)])
        self.assertEqual(events, ["started"])
        _, events = run_trace([(2, True), (3, True), (2, False), (3, False)])
        self.assertEqual(events, ["started", "completed"])

    def test_activity_cannot_distinguish_mutation_outcomes(self):
        # All these hypothetical operations use the same activity trace.
        # No success/error/no-op payload exists in this model: do not infer one.
        results = [run_trace([(0, True), (0, False)])[1]
                   for _ in ("success", "error", "no-op")]
        self.assertEqual(results, [["started", "completed"]] * 3)


if __name__ == "__main__":
    unittest.main()
