import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_news_curator_structure():
    from news_curator import NewsCurator
    curator = NewsCurator()
    questions = curator.curate_daily_questions(date_str="2026-10-08", count=2)
    assert len(questions) == 2
    q = questions[0]
    assert "question_hi" in q and len(q["question_hi"]) > 5
    assert "question_en" in q and len(q["question_en"]) > 5
    assert len(q["options"]) == 5
    assert q["options"][4]["val"] == "अनुत्तरित प्रश्न / Prefer not to answer"
    assert q["correct_ans"] in ["1", "2", "3", "4"]
    assert "exam_fact_hi" in q
    assert "visual_query" in q

def test_answer_key_distribution_balancing():
    from news_curator import NewsCurator
    curator = NewsCurator()
    mock_questions = []
    for i in range(24):
        mock_questions.append({
            "num": i + 1,
            "correct_ans": "1",  # Biased input from LLM
            "options": [
                {"key": "1", "val": f"Correct {i+1}"},
                {"key": "2", "val": f"Distractor A {i+1}"},
                {"key": "3", "val": f"Distractor B {i+1}"},
                {"key": "4", "val": f"Distractor C {i+1}"},
                {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
            ]
        })
    balanced = curator._balance_and_shuffle_options(mock_questions)
    assert len(balanced) == 24
    counts = {k: sum(1 for q in balanced if q["correct_ans"] == k) for k in ["1", "2", "3", "4"]}
    # In 24 questions, each of 1, 2, 3, 4 must appear exactly 6 times (25% each)!
    for k in ["1", "2", "3", "4"]:
        assert counts[k] == 6, f"Expected 6 for key {k}, got {counts[k]}"

    # Verify that the correct value is indeed at the correct_ans index
    for q in balanced:
        ans_idx = int(q["correct_ans"]) - 1
        assert f"Correct {q['num']}" == q["options"][ans_idx]["val"]
        assert q["options"][4]["val"] == "अनुत्तरित प्रश्न / Prefer not to answer"
