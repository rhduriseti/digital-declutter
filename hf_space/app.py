import os
from pathlib import Path

import gradio as gr
import pandas as pd

from declutter_bot.tools.categorize_files import categorize_files

SUBJECT_EMOJI = {
    "math": "🔢",
    "biology": "🧬",
    "physics": "⚛️",
    "english": "📝",
    "history": "🏛️",
    "spanish": "🇪🇸",
    "art": "🎨",
    "band": "🎵",
    "pe": "⚽",
    "science": "🔬",
    "computer science": "💻",
    "other": "📁",
    "media": "🖼️",
}

GROUP_LABELS = {
    "A": "📂 Filename/folder",
    "B": "📄 File content",
    "C": "🤖 Gemma 4",
    "C_visual": "👁️ Gemma 4 Vision",
    "extension": "🗂️ File type",
    "fallback": "—",
}


def build_entry(file_path: str, original_name: str) -> dict:
    path = Path(file_path)
    stat = path.stat()
    return {
        "path": file_path,
        "name": original_name,
        "extension": Path(original_name).suffix.lower(),
        "size_bytes": stat.st_size,
        "created_at": str(stat.st_ctime),
        "modified_at": str(stat.st_mtime),
        "source": "local",
        "category": None,
        "duplicate_of": None,
    }


def classify_uploaded_files(files, progress=gr.Progress(track_tqdm=True)):
    if not files:
        return None, "⬆️ Upload some school files and click **Classify**."

    progress(0, desc="Building file index…")
    index = {}
    for f in files:
        original_name = Path(f.name).name
        entry = build_entry(f.name, original_name)
        index[f.name] = entry

    total = len(files)
    done_state = [0]

    def on_progress(done, _total):
        done_state[0] = done
        progress(done / _total, desc=f"Classifying {done}/{_total} files…")

    progress(0.05, desc=f"Classifying {total} file{'s' if total > 1 else ''} with Gemma 4…")
    results = categorize_files(index, on_progress=on_progress)

    rows = []
    for path, entry in results.items():
        subject = entry.get("category") or "other"
        emoji = SUBJECT_EMOJI.get(subject, "📄")
        group_raw = entry.get("classification_group", "fallback")
        group_label = GROUP_LABELS.get(group_raw, group_raw)
        conf = entry.get("confidence_score") or 0
        also = entry.get("also_could_be") or "—"

        rows.append({
            "File": Path(path).name,
            "Subject": f"{emoji} {subject}",
            "Classified by": group_label,
            "Confidence": f"{conf:.0%}" if conf else "—",
            "Also could be": also,
        })

    df = pd.DataFrame(rows)

    gemma_count = sum(1 for r in rows if "Gemma" in r["Classified by"])
    vision_count = sum(1 for r in rows if "Vision" in r["Classified by"])

    parts = [f"✅ **{total} file{'s' if total > 1 else ''} classified**"]
    if gemma_count:
        parts.append(f"🤖 Gemma 4 used for **{gemma_count}** file{'s' if gemma_count > 1 else ''}")
    if vision_count:
        parts.append(f"👁️ Vision used for **{vision_count}** image{'s' if vision_count > 1 else ''}")

    return df, "  ·  ".join(parts)


with gr.Blocks(title="Claire — AI School File Organiser") as demo:
    gr.Markdown("""
# 📚 Claire — AI School File Organiser
### Powered by Gemma 4 · Built for the Kaggle Gemma 4 Good Hackathon

Claire helps high school students organise their school files by subject using a 3-stage AI pipeline:

| Stage | Method | Speed |
|-------|--------|-------|
| **1 — Filename & folder** | Keyword matching against subject seed map | Instant |
| **2 — File content** | Reads document text, scores against seed map | Fast |
| **3 — Gemma 4** | Constrained chain-of-thought reasoning · **Vision** for photos of notes & whiteboards | AI |
    """)

    with gr.Row():
        file_input = gr.File(
            label="Upload school files (documents + images)",
            file_count="multiple",
            file_types=[
                ".pdf", ".docx", ".doc", ".txt", ".pptx", ".ppt", ".md", ".csv",
                ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
            ],
        )

    gr.Examples(
        examples=[
            [["examples/spanish_ch7_review.pdf", "examples/bio_notes_unit5.docx",
              "examples/writing_task_final.docx", "examples/assignment4.docx",
              "examples/experiment_writeup_p3.pdf", "examples/unit3_problem_set.docx",
              "examples/IMG_2847.jpg"]],
        ],
        inputs=[file_input],
        label="Try these sample school files",
    )

    classify_btn = gr.Button("🔍 Classify Files", variant="primary", size="lg")
    status_md = gr.Markdown("⬆️ Upload some school files and click **Classify**.")
    results_table = gr.DataFrame(wrap=True)

    gr.Markdown("""
---
**Claire** classifies school files by subject — math, biology, history, English, and more.
Gemma 4's multimodal capability lets it read **handwritten notes**, **whiteboard photos**, and **scanned worksheets** — something no previous Gemma generation could do.

[GitHub](https://github.com/rhduriseti/digital-declutter) · Made with ❤️ for students everywhere
    """)

    classify_btn.click(
        fn=classify_uploaded_files,
        inputs=[file_input],
        outputs=[results_table, status_md],
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
