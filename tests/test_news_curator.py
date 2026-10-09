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
