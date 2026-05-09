import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

from declutter_bot.tools.subject_classifier import (
    # legacy — unchanged
    extract_keywords,
    classify_by_folder,
    classify_by_filename,
    classify_by_seed_map,
    classify_subject,
    # new pipeline
    classify_group_a,
    classify_group_b,
    classify_group_c,
    _is_ambiguous,
)


# ---------------------------------------------------------
# extract_keywords
# ---------------------------------------------------------

def test_extract_keywords_handles_underscores():
    assert "bio" in extract_keywords("AP_Bio_Notes")

def test_extract_keywords_handles_spaces():
    assert "calc" in extract_keywords("calc test 2")

def test_extract_keywords_strips_extension():
    assert "essay" in extract_keywords("essay_draft.docx")

def test_extract_keywords_lowercase():
    keywords = extract_keywords("BIOLOGY_NOTES")
    assert "biology" in keywords


# ---------------------------------------------------------
# Step 1 — classify_by_folder (legacy)
# ---------------------------------------------------------

def test_classify_by_folder_matches_subject_folder():
    result = classify_by_folder("/Users/student/AP Bio/chapter3_notes.pdf")
    assert result == "biology"

def test_classify_by_folder_ignores_generic_folders():
    result = classify_by_folder("/Users/student/documents/notes.pdf")
    assert result is None

def test_classify_by_folder_matches_math_folder():
    result = classify_by_folder("/Users/student/Calculus/homework1.pdf")
    assert result == "math"


# ---------------------------------------------------------
# Step 2 — classify_by_filename (legacy)
# ---------------------------------------------------------

def test_classify_by_filename_matches_bio():
    result = classify_by_filename("/downloads/bio_lab_report.docx")
    assert result == "biology"

def test_classify_by_filename_matches_calc():
    result = classify_by_filename("/downloads/calc_test_2.pdf")
    assert result == "math"

def test_classify_by_filename_no_match():
    result = classify_by_filename("/downloads/radhika_resume.pdf")
    assert result is None


# ---------------------------------------------------------
# Step 3 — classify_by_seed_map (legacy)
# ---------------------------------------------------------

def test_classify_by_seed_map_catches_keyword_in_path():
    result = classify_by_seed_map("/Users/student/homework/essay_draft.docx")
    assert result == "english"

def test_classify_by_seed_map_science():
    result = classify_by_seed_map("/Users/student/science_experiment.pdf")
    assert result == "science"


# ---------------------------------------------------------
# Full legacy pipeline — classify_subject
# ---------------------------------------------------------

def test_classify_subject_folder_wins():
    result = classify_subject("/Users/student/Biology/random_file.pdf")
    assert result == "biology"

def test_classify_subject_filename_fallback():
    result = classify_subject("/Users/student/documents/algebra_notes.pdf")
    assert result == "math"

def test_classify_subject_no_match_returns_none():
    result = classify_subject("/Users/student/documents/radhika_photo.jpg")
    assert result is None


# ---------------------------------------------------------
# Group A — new 3-tuple signature
# ---------------------------------------------------------

def test_classify_group_a_returns_three_tuple():
    subject, confidence, scores = classify_group_a("/Users/student/Biology/notes.pdf")
    assert isinstance(subject, str)
    assert isinstance(confidence, float)
    assert isinstance(scores, dict)

def test_classify_group_a_high_confidence_on_clear_path():
    subject, confidence, scores = classify_group_a("/Users/student/AP Bio/chapter3_notes.pdf")
    assert subject == "biology"
    assert confidence > 0.5
    assert "biology" in scores

def test_classify_group_a_uses_display_name_for_drive():
    # Spaces required — underscores break \b word boundaries in regex matching
    subject, confidence, scores = classify_group_a("gdrive:school/opaque_id_123", display_name="AP Calculus Notes.pdf")
    assert subject == "math"

def test_classify_group_a_returns_empty_scores_for_generic_path():
    _, _, scores = classify_group_a("/Users/student/documents/untitled.pdf")
    assert scores == {} or sum(scores.values()) == 0


# ---------------------------------------------------------
# Group B — new 3-tuple signature, no expanded map
# ---------------------------------------------------------

def test_classify_group_b_returns_three_tuple():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        f.write("photosynthesis cell biology organism")
        path = f.name
    subject, confidence, scores = classify_group_b(path)
    assert isinstance(subject, (str, type(None)))
    assert isinstance(confidence, float)
    assert isinstance(scores, dict)

def test_classify_group_b_scores_biology_content():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        f.write("photosynthesis cell dna mitosis biology")
        path = f.name
    subject, confidence, scores = classify_group_b(path)
    assert subject == "biology"
    assert confidence > 0.5

def test_classify_group_b_empty_file_returns_zero_confidence():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        f.write("")
        path = f.name
    subject, confidence, scores = classify_group_b(path)
    assert subject is None
    assert confidence == 0.0
    assert scores == {}


# ---------------------------------------------------------
# _is_ambiguous
# ---------------------------------------------------------

def test_is_ambiguous_clear_winner_not_ambiguous():
    scores = {"biology": 10, "history": 2}
    assert _is_ambiguous(scores) is False

def test_is_ambiguous_close_scores_are_ambiguous():
    scores = {"biology": 5, "history": 5}
    assert _is_ambiguous(scores) is True

def test_is_ambiguous_within_threshold_is_ambiguous():
    # biology=6, history=5 → biology conf=0.545, history=0.454 → diff=0.09 < 0.15
    scores = {"biology": 6, "history": 5}
    assert _is_ambiguous(scores) is True

def test_is_ambiguous_single_subject_not_ambiguous():
    scores = {"biology": 10}
    assert _is_ambiguous(scores) is False

def test_is_ambiguous_empty_scores_not_ambiguous():
    assert _is_ambiguous({}) is False


# ---------------------------------------------------------
# classify_group_c — Gemma via Ollama (mocked)
# ---------------------------------------------------------

def _mock_ollama_response(subject: str, confidence: float, also_could_be: str = "null"):
    content = json.dumps({
        "subject": subject,
        "confidence": confidence,
        "task_type": "essay",
        "also_could_be": also_could_be,
    })
    mock_response = MagicMock()
    mock_response.message.content = content
    return mock_response

def test_classify_group_c_returns_subject_from_gemma():
    with patch("ollama.chat", return_value=_mock_ollama_response("english", 0.91)):
        subject, confidence, also = classify_group_c(
            text="This essay examines Romantic poets and the French Revolution.",
            file_path="/Users/student/Literature/french_revolution_essay.docx",
            keyword_scores={"history": 4, "english": 2},
        )

    assert subject == "english"
    assert confidence == 0.91
    assert also is None  # high confidence → no runner-up

def test_classify_group_c_returns_also_could_be_when_uncertain():
    with patch("ollama.chat", return_value=_mock_ollama_response("english", 0.65, "history")):
        subject, confidence, also = classify_group_c(
            text="Napoleon essay romantic",
            file_path="/Users/student/essay.docx",
            keyword_scores={"history": 3, "english": 2},
        )

    assert subject == "english"
    assert also == "history"

def test_classify_group_c_rejects_subject_not_in_candidates():
    # Gemma returns a subject that wasn't one of the top-2 candidates offered
    with patch("ollama.chat", return_value=_mock_ollama_response("underwater basket weaving", 0.99)):
        subject, confidence, also = classify_group_c(
            text="some content",
            file_path="/Users/student/weird.docx",
            keyword_scores={"history": 3, "english": 2},
        )

    assert subject is None

def test_classify_group_c_ollama_unavailable_returns_none():
    with patch("ollama.chat", side_effect=Exception("Connection refused")):
        subject, confidence, also = classify_group_c(
            text="some content",
            file_path="/Users/student/essay.docx",
            keyword_scores={"history": 3},
        )

    assert subject is None
    assert confidence == 0.0
    assert also is None
