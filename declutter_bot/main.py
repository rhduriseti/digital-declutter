from declutter_bot.tools.scan_folder import scan_folder
from declutter_bot.core.index_manager import update_index_with_scan, load_index, save_index
from declutter_bot.tools.categorize_files import categorize_files
from declutter_bot.tools.detect_duplicates import detect_duplicates
from declutter_bot.tools.generate_report import generate_report


def run_pipeline(folder: str):
    print(f"📁 Scanning folder: {folder}")

    # Step 1: Scan
    scanned_files = scan_folder(folder)
    print(f"🔍 Found {len(scanned_files)} files")

    # Step 2: Update index.json
    update_index_with_scan(scanned_files)
    print("📄 Index updated")

    # Step 3: Load updated index
    index = load_index()

    # Step 4: Categorize
    index = categorize_files(index)
    print("🏷️ Files categorized")

    # Step 5: Detect duplicates
    index = detect_duplicates(index)
    print("🔁 Duplicate detection complete")

    # Step 6: Generate report
    report = generate_report(index)
    print("📊 Report generated")

    # Step 7: Save final index
    save_index(index)
    print("💾 Index saved")

    return report


if __name__ == "__main__":
    folder = "/Users/radhika/Downloads"
    report = run_pipeline(folder)

    print("\n=== SUMMARY ===")
    print(f"Total files: {report['total_files']}")
    print(f"Total size: {report['total_size_bytes']} bytes")
    print(f"Categories: {report['categories']}")
    print(f"Duplicate groups: {len(report['duplicates'])}")
