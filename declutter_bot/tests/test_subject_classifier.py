from declutter_bot.tools.subject_classifier import (
    extract_keywords,
    classify_by_folder,
    classify_by_filename,
    classify_by_seed_map,
    classify_subject,
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
# Step 1 — classify_by_folder
# ---------------------------------------------------------

def test_classify_by_folder_matches_subject_folder():
    result = classify_by_folder("/Users/student/AP Bio/chapter3_notes.pdf")
    assert result == "biology"

def test_classify_by_folder_ignores_generic_folders():
    # "documents" is too generic — should not match
    result = classify_by_folder("/Users/student/documents/notes.pdf")
    assert result is None

def test_classify_by_folder_matches_math_folder():
    result = classify_by_folder("/Users/student/Calculus/homework1.pdf")
    assert result == "math"


# ---------------------------------------------------------
# Step 2 — classify_by_filename
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
# Step 3 — classify_by_seed_map
# ---------------------------------------------------------

def test_classify_by_seed_map_catches_keyword_in_path():
    result = classify_by_seed_map("/Users/student/homework/essay_draft.docx")
    assert result == "english"

def test_classify_by_seed_map_chemistry():
    result = classify_by_seed_map("/Users/student/stoichiometry_notes.pdf")
    assert result == "chemistry"


# ---------------------------------------------------------
# Full pipeline — classify_subject
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
