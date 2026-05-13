"""
Real Gemma integration tests — require Ollama running with gemma3:1b.

These tests are skipped automatically when Ollama is not reachable.
To run them: start Ollama first, then run pytest normally.

  ollama serve   # or open the Ollama desktop app
  pytest declutter_bot/tests/test_gemma_integration.py -v
"""
import tempfile
from pathlib import Path

import pytest

import ollama

from declutter_bot.tools.subject_classifier import classify_group_c
from declutter_bot.tools.categorize_files import categorize_files


# ---------------------------------------------------------
# Skip entire module if gemma3:1b can't actually respond
# (covers: Ollama not running, model not installed, resource limits)
# ---------------------------------------------------------

def _gemma_available() -> bool:
    """Return True only if gemma3:1b loads and responds successfully."""
    try:
        ollama.chat(
            model="gemma3:1b",
            messages=[{"role": "user", "content": "Reply with the single word: ready"}],
        )
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _gemma_available(),
    reason="gemma3:1b is not available — start Ollama and ensure the model is loaded",
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _entry(path: str, ext: str, modified_at: str = "2024-01-01") -> dict:
    return {
        "path": path,
        "name": Path(path).name,
        "extension": ext,
        "size_bytes": 100,
        "created_at": "2024-01-01",
        "modified_at": modified_at,
        "category": None,
        "duplicate_of": None,
    }


# ---------------------------------------------------------
# classify_group_c — real Gemma calls
# ---------------------------------------------------------

def test_gemma_classifies_clear_biology():
    text = (
        "The cell membrane controls what enters and exits the cell. "
        "DNA carries genetic information through chromosomes. "
        "Mitosis is the process of cell division that produces two identical daughter cells. "
        "Photosynthesis converts sunlight into glucose in plant cells."
    )
    subject, confidence, _ = classify_group_c(
        text=text,
        file_path="/Users/student/Biology/cell division notes.txt",
        keyword_scores={"biology": 4},
    )

    assert subject == "biology", f"Expected 'biology', got '{subject}' (confidence={confidence:.2f})"
    assert confidence >= 0.7


def test_gemma_classifies_ambiguous_history_vs_english():
    """
    Core use case: a literature essay ABOUT a historical event.
    Keyword scoring would score 'history' (napoleon, revolution) but
    the file's PURPOSE is english/literature. Gemma should reason correctly.
    """
    text = (
        "This essay analyzes how Romantic poets used Napoleon as a literary symbol of tyranny. "
        "Byron and Shelley wrote poems that referenced the French Revolution as a metaphor "
        "for liberation. The essay argues that these poets were not writing history "
        "but using historical events as allegory for contemporary political critique."
    )
    subject, confidence, _ = classify_group_c(
        text=text,
        file_path="/Users/student/English/Essays/napoleon romanticism essay.docx",
        keyword_scores={"history": 5, "english": 2},
    )

    assert subject == "english", f"Expected 'english', got '{subject}' (confidence={confidence:.2f})"
    assert confidence >= 0.6


def test_gemma_classifies_math_disguised_as_physics():
    """
    A math problem set that uses physics vocabulary (force, velocity)
    but the task is solving equations — it should be 'math'.
    """
    text = (
        "Problem Set 3: Solve the following equations. "
        "1. A force of 10N is applied. Write an equation for velocity as a function of time. "
        "2. Use the quadratic formula to find when acceleration equals zero. "
        "3. Graph the function f(t) = 3t^2 - 6t + 2 and identify the roots."
    )
    subject, confidence, _ = classify_group_c(
        text=text,
        file_path="/Users/student/Math/problem set 3.pdf",
        keyword_scores={"physics": 3, "math": 3},
    )

    assert subject == "math", f"Expected 'math', got '{subject}' (confidence={confidence:.2f})"
    assert confidence >= 0.6


def test_gemma_returns_valid_subject_from_seed_map():
    """Gemma's response must be one of the known subjects or 'other'."""
    from declutter_bot.core.utils import SEED_MAP
    valid_subjects = set(SEED_MAP.keys()) | {"other"}

    text = "Weekly practice schedule for the spring concert season. Rehearsal on Tuesday at 3pm."
    subject, confidence, _ = classify_group_c(
        text=text,
        file_path="/Users/student/Band/spring schedule.txt",
        keyword_scores={"band": 2, "personal": 1},
    )

    assert subject in valid_subjects or subject is None, f"Invalid subject: '{subject}'"


def test_gemma_returns_also_could_be_when_close():
    """When Gemma is uncertain it should populate also_could_be."""
    text = (
        "This document covers the causes of World War I including alliances, "
        "nationalism, and imperialism. Write a short response analyzing the main cause."
    )
    subject, confidence, also = classify_group_c(
        text=text,
        file_path="/Users/student/History/wwi response.txt",
        keyword_scores={"history": 4, "english": 3},
    )

    # If confidence is low, also_could_be should be set
    if confidence < 0.75:
        assert also is not None, "Expected also_could_be to be set for low-confidence result"


# ---------------------------------------------------------
# Full pipeline — categorize_files with real Gemma
# ---------------------------------------------------------

def test_full_pipeline_gemma_resolves_ambiguous_file(tmp_path):
    """
    End-to-end: a file that Groups A+B can't confidently resolve
    gets correctly classified by Gemma in Group C.
    """
    file_path = tmp_path / "napoleon romanticism essay.txt"
    file_path.write_text(
        "This essay examines Napoleon as a literary symbol in Romantic poetry. "
        "Byron and Shelley used the French Revolution as a metaphor for liberation. "
        "The argument is that these poets transformed historical events into allegory."
    )

    index = {str(file_path): _entry(str(file_path), ".txt")}
    updated = categorize_files(index)
    entry = updated[str(file_path)]

    assert entry["category"] == "english", (
        f"Expected 'english', got '{entry['category']}' "
        f"(group={entry['classification_group']}, confidence={entry['confidence_score']:.2f})"
    )
