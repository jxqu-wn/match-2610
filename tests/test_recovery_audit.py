import json

from evaluation.submission_quality.recovery import needs_repacking


def test_recovery_selects_actual_packing_changes_without_reference_answers():
    def output(removed, rows=0):
        return {"trace": [{"omitted_whole_evidence": removed,
                           "messages": [{}, {"content": json.dumps({"source_row_evidence": [{}] * rows})}]}]}
    assert needs_repacking(output(["source_row:original:5"]))
    assert needs_repacking(output(["definition_dependency:knowledge:1"], 3))
    assert not needs_repacking(output(["knowledge:1"], 2))
    assert not needs_repacking(output(["example:3"]))
