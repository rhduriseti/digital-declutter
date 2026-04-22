import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track, Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich import box

from declutter_bot.tools.scan_folder import scan_folder
from declutter_bot.core.index_manager import update_index_with_scan, load_index, save_index, load_combined_index, untrack_folder
from declutter_bot.connectors.gdrive import GoogleDriveConnector
from declutter_bot.tools.categorize_files import categorize_files
from declutter_bot.tools.detect_duplicates import detect_duplicates
from declutter_bot.tools.generate_report import generate_report, generate_report_for_scan
from declutter_bot.tools.generate_organised_view import generate_organised_view
from declutter_bot.tools.search_index import search_index
from declutter_bot.tools.delete_duplicates import get_deletable_paths, delete_duplicates
from declutter_bot.tools.scan_folder import is_project_folder
from declutter_bot.core.blacklist_manager import add_to_blacklist, remove_from_blacklist, load_blacklist, is_blacklisted
from declutter_bot.core.staging_manager import restore_file, restore_all, empty_staging, get_staging_summary
from declutter_bot.core.utils import format_size


console = Console()


# ------------------------------------------------------------
# Verbose helpers (B + C only)
# ------------------------------------------------------------
def vprint(msg, args):
    if args.verbose:
        console.print(f"[bold blue][VERBOSE][/bold blue] {msg}")


def wprint(msg):
    console.print(f"[yellow][WARN][/yellow] {msg}")


# ------------------------------------------------------------
# Plain text fallback helpers
# ------------------------------------------------------------
def print_plain_scan_summary(report):
    print("\n=== SUMMARY ===")
    print(f"Total files: {report['total_files']}")
    print(f"Total size: {format_size(report['total_size_bytes'])}")
    print("Categories:")
    for cat, count in report["categories"].items():
        print(f"  - {cat}: {count}")
    print(f"Duplicate files: {len(report['duplicates'])}")
    print(f"Space saved by deleting duplicates: {format_size(report['space_saved_by_deleting_duplicates_bytes'])}")
    if report["duplicates"]:
        print("Duplicates:")
        for f in report["duplicates"]:
            origin = "temp file — safe to delete" if f["duplicate_of"] == "__temp_file__" else f"duplicate of {f['duplicate_of']}"
            print(f"  - {f['path']} ({origin}, {format_size(f['size_bytes'])})")


def print_plain_search_results(results, query):
    print(f"\nSearch results for '{query}':")
    if not results:
        print("No results found.")
        return
    for r in results:
        print(f"- {r['name']} ({r.get('category', '-')}) → {r['path']}")


def print_plain_global_report(report):
    print("\n=== GLOBAL REPORT ===")
    print(f"Total files: {report['total_files']}")
    print(f"Total size: {format_size(report['total_size_bytes'])}")
    print("Categories:")
    for cat, count in report["categories"].items():
        print(f"  - {cat}: {count}")
    print(f"Duplicate files: {len(report['duplicates'])}")
    print(f"Space saved by deleting duplicates: {format_size(report['space_saved_by_deleting_duplicates_bytes'])}")
    if report["duplicates"]:
        print("Duplicates:")
        for f in report["duplicates"]:
            origin = "temp file — safe to delete" if f["duplicate_of"] == "__temp_file__" else f"duplicate of {f['duplicate_of']}"
            print(f"  - {f['path']} ({origin}, {format_size(f['size_bytes'])})")


# ------------------------------------------------------------
# Pretty Rich renderers
# ------------------------------------------------------------
def render_scan_report(report, folder):
    console.print()
    console.print(Panel.fit(f"[bold cyan]Scan Summary for[/] [white]{folder}[/]", border_style="cyan"))

    stats = Table(show_header=False, box=box.SIMPLE)
    stats.add_row("Total files", str(report["total_files"]))
    stats.add_row("Total size", format_size(report['total_size_bytes']))
    console.print(stats)
    console.print()

    cat_table = Table(title="Categories", box=box.MINIMAL_DOUBLE_HEAD)
    cat_table.add_column("Category", style="bold green")
    cat_table.add_column("Count", justify="right")
    for cat, count in report["categories"].items():
        cat_table.add_row(cat, str(count))
    console.print(cat_table)
    console.print()

    dup_files = report["duplicates"]
    space_saved = report["space_saved_by_deleting_duplicates_bytes"]
    dup_table = Table(title=f"Duplicate Files  |  Space saved: {format_size(space_saved)}", box=box.MINIMAL_DOUBLE_HEAD)
    dup_table.add_column("Duplicate File", style="bold magenta")
    dup_table.add_column("Duplicate Of", style="cyan")
    dup_table.add_column("Size", justify="right")
    for f in dup_files:
        origin = "temp file — safe to delete" if f["duplicate_of"] == "__temp_file__" else f["duplicate_of"]
        dup_table.add_row(f["path"], origin, format_size(f['size_bytes']))
    console.print(dup_table)
    console.print()


def render_search_results(results, query):
    table = Table(title=f"🔍 Search Results for '{query}'")
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Path", style="magenta")

    for r in results:
        table.add_row(r["name"], r.get("category", "-"), r["path"])

    console.print(table)


def render_organised_view(index: dict, source: str = None):
    organised = generate_organised_view(index if not source else {
        k: v for k, v in index.items() if v.get("source") == source
    })

    if not organised:
        console.print("[yellow]No files in index yet. Run a scan first.[/yellow]")
        return

    total = sum(len(files) for files in organised.values())
    console.print()
    console.print(Panel.fit(f"[bold cyan]Organised View[/]  —  {total} files", border_style="cyan"))

    table = Table(box=box.MINIMAL_DOUBLE_HEAD, show_lines=False)
    table.add_column("Category", style="bold green", width=16)
    table.add_column("File", style="white")
    table.add_column("Source", style="cyan", width=14)
    table.add_column("Size", justify="right", width=9)
    table.add_column("", width=4)  # duplicate flag

    for cat, files in organised.items():
        first = True
        for f in files:
            table.add_row(
                cat if first else "",
                f["name"],
                f["source"],
                format_size(f["size_bytes"]),
                "[yellow]⚠[/yellow]" if f["duplicate_of"] else "",
            )
            first = False

    console.print(table)


def render_global_report(report):
    summary = Table(title="📊 Summary Report")
    summary.add_column("Metric", style="cyan", no_wrap=True)
    summary.add_column("Value", style="magenta")

    summary.add_row("Total Files", str(report["total_files"]))
    summary.add_row("Total Size", format_size(report['total_size_bytes']))
    summary.add_row("Categories", str(len(report["categories"])))
    summary.add_row("Duplicate Files", str(len(report["duplicates"])))
    summary.add_row("Space Saved by Deleting Duplicates", format_size(report['space_saved_by_deleting_duplicates_bytes']))

    console.print(summary)

    if report["duplicates"]:
        console.print()
        dup_table = Table(title="Duplicate Files", box=box.MINIMAL_DOUBLE_HEAD)
        dup_table.add_column("Duplicate File", style="bold magenta")
        dup_table.add_column("Duplicate Of", style="cyan")
        dup_table.add_column("Size", justify="right")
        for f in report["duplicates"]:
            origin = "temp file — safe to delete" if f["duplicate_of"] == "__temp_file__" else f["duplicate_of"]
            dup_table.add_row(f["path"], origin, format_size(f['size_bytes']))
        console.print(dup_table)


# ------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------
def folder_in_index(index: dict, folder: str) -> bool:
    """Return True if at least one file from this folder exists in the index."""
    from pathlib import Path
    folder_path = Path(folder).resolve()
    return any(
        Path(path).resolve().is_relative_to(folder_path)
        for path in index
    )


def run_pipeline(folder, args):
    folder_path = Path(folder)

    vprint("Scanning folder...", args)
    try:
        scanned = scan_folder(folder)
    except PermissionError as e:
        console.print(f"[red]{e}[/red]")
        console.print("To remove from blacklist: [bold]declutter blacklist remove <folder>[/bold]")
        return None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:

        # Step 1 — Indexing (real progress, we know the count)
        t_index = progress.add_task("Indexing files...", total=len(scanned))
        update_index_with_scan(scanned, "local")
        progress.update(t_index, completed=len(scanned))

        # Step 2 — Load index
        index = load_index("local")
        total = len(index)

        # Step 3 — Categorising (only files that are new or modified since last categorisation)
        needs_cat = sum(
            1 for e in index.values()
            if not e.get("category") or
            e.get("categorised_modified_at", e.get("modified_at")) != e.get("modified_at")
        )
        t_cat = progress.add_task("Categorising files...", total=max(needs_cat, 1))
        index = categorize_files(index)
        progress.update(t_cat, completed=max(needs_cat, 1))

        # Step 4 — Detecting duplicates
        t_dup = progress.add_task("Detecting duplicates...", total=total)
        index = detect_duplicates(index)
        progress.update(t_dup, completed=total)

        # Step 5 — Saving
        t_save = progress.add_task("Saving index...", total=1)
        save_index(index, "local")
        progress.update(t_save, completed=1)

        # Step 6 — Report
        t_report = progress.add_task("Generating report...", total=1)
        report = generate_report_for_scan(index, folder_path)
        progress.update(t_report, completed=1)

    console.print("✨ [bold green]Scan complete![/bold green]")
    return report


# ------------------------------------------------------------
# Drive pipeline
# ------------------------------------------------------------

def run_drive_pipeline(account_name: str, args):
    """Scan a Google Drive account and update the index."""
    connector = GoogleDriveConnector(account_name)

    try:
        console.print(f"Scanning Google Drive ({account_name})...")
        scanned = connector.scan()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        return None

    console.print(f"Found [bold]{len(scanned)}[/bold] files.")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:

        source_id = f"gdrive:{account_name}"
        t_index = progress.add_task("Indexing files...", total=len(scanned))
        update_index_with_scan(scanned, source_id)
        progress.update(t_index, completed=len(scanned))

        index = load_index(source_id)
        total = len(index)

        needs_cat = sum(
            1 for e in index.values()
            if not e.get("category") or
            e.get("categorised_modified_at", e.get("modified_at")) != e.get("modified_at")
        )
        t_cat = progress.add_task("Categorising files...", total=max(needs_cat, 1))
        index = categorize_files(index)
        progress.update(t_cat, completed=max(needs_cat, 1))

        t_dup = progress.add_task("Detecting duplicates...", total=total)
        index = detect_duplicates(index)
        progress.update(t_dup, completed=total)

        t_save = progress.add_task("Saving index...", total=1)
        save_index(index, source_id)
        progress.update(t_save, completed=1)

        t_report = progress.add_task("Generating report...", total=1)
        report = generate_report(index)
        progress.update(t_report, completed=1)

    console.print("✨ [bold green]Drive scan complete![/bold green]")
    return report


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Declutter Engine CLI")
    sub = parser.add_subparsers(dest="command")

    # scan
    scan_cmd = sub.add_parser("scan", help="Scan a folder or Drive account and update index")
    scan_cmd.add_argument("folder", nargs="?", help="Local folder to scan (omit when using --source gdrive:*)")
    scan_cmd.add_argument("--source", default="local", help="Source to scan: 'local' (default) or 'gdrive:<account>'")
    scan_cmd.add_argument("--json", action="store_true")
    scan_cmd.add_argument("--pretty", action="store_true")
    scan_cmd.add_argument("--verbose", action="store_true")

    # search
    search_cmd = sub.add_parser("search", help="Search the index")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--json", action="store_true")
    search_cmd.add_argument("--pretty", action="store_true")
    search_cmd.add_argument("--verbose", action="store_true")

    # report
    report_cmd = sub.add_parser("report", help="Show summary report")
    report_cmd.add_argument("--source", default=None, help="Filter by source: 'local', 'gdrive:<account>', or omit for all")
    report_cmd.add_argument("--organised", action="store_true", help="Show files grouped by subject category")
    report_cmd.add_argument("--json", action="store_true")
    report_cmd.add_argument("--pretty", action="store_true")
    report_cmd.add_argument("--verbose", action="store_true")

    # blacklist
    bl_cmd = sub.add_parser("blacklist", help="Manage folder blacklist")
    bl_sub = bl_cmd.add_subparsers(dest="bl_action")
    bl_add = bl_sub.add_parser("add", help="Add a folder to the blacklist")
    bl_add.add_argument("folder")
    bl_remove = bl_sub.add_parser("remove", help="Remove a folder from the blacklist")
    bl_remove.add_argument("folder")
    bl_sub.add_parser("show", help="Show all blacklisted folders")

    # staging
    st_cmd = sub.add_parser("staging", help="Manage staged (soft-deleted) files")
    st_sub = st_cmd.add_subparsers(dest="st_action")
    st_sub.add_parser("show", help="Show all files currently in staging")
    st_restore = st_sub.add_parser("restore", help="Restore staged files to original location")
    st_restore.add_argument("--file", help="Restore a specific file by its original path")
    st_restore.add_argument("--all", action="store_true", help="Restore all staged files")
    st_sub.add_parser("empty", help="Permanently delete all staged files and free disk space")

    # drive-login
    drive_login_cmd = sub.add_parser("drive-login", help="Connect a Google Drive account")
    drive_login_cmd.add_argument("account_name", help="Nickname for this account, e.g. 'school' or 'personal'")

    # drive-logout
    drive_logout_cmd = sub.add_parser("drive-logout", help="Disconnect a Google Drive account")
    drive_logout_cmd.add_argument("account_name", help="Account nickname to disconnect")

    # drive-accounts
    sub.add_parser("drive-accounts", help="List all connected Google Drive accounts")

    # untrack
    untrack_cmd = sub.add_parser("untrack", help="Remove a folder's files from the index (without blacklisting)")
    untrack_cmd.add_argument("folder", help="Local folder to remove from index")

    # delete-duplicates
    delete_cmd = sub.add_parser("delete-duplicates", help="Delete duplicate files")
    delete_cmd.add_argument("--dry-run", action="store_true", help="Preview what would be deleted without making changes")
    delete_cmd.add_argument("--permanent", action="store_true", help="Permanently delete instead of moving to Trash")
    delete_cmd.add_argument("--folder", help="Only delete duplicates inside this folder")
    delete_cmd.add_argument("--interactive", action="store_true", help="Confirm each file one by one before deleting")
    delete_cmd.add_argument("--verbose", action="store_true", help="Show scan progress if auto-scan is triggered")

    args = parser.parse_args()

    # -------------------------
    # scan
    # -------------------------
    if args.command == "scan":
        if args.source.startswith("gdrive:"):
            account_name = args.source.split(":", 1)[1]
            report = run_drive_pipeline(account_name, args)
            label = args.source
        else:
            if not args.folder:
                console.print("[red]Error: folder is required for local scan.[/red]")
                console.print("Usage: declutter scan <folder>")
                console.print("       declutter scan --source gdrive:<account>")
                return
            report = run_pipeline(args.folder, args)
            label = args.folder

        if report is None:
            return

        if args.json:
            print(json.dumps(report, indent=2))
            return

        if args.pretty:
            render_scan_report(report, label)
        else:
            print_plain_scan_summary(report)
        return

    # -------------------------
    # search
    # -------------------------
    if args.command == "search":
        index = load_combined_index()
        results = search_index(index, args.query)

        if args.json:
            print(json.dumps(results, indent=2))
            return

        if args.pretty:
            render_search_results(results, args.query)
        else:
            print_plain_search_results(results, args.query)
        return

    # -------------------------
    # report
    # -------------------------
    if args.command == "report":
        index = load_combined_index()

        if args.organised:
            render_organised_view(index, source=args.source)
            return

        if args.source:
            index = {k: v for k, v in index.items() if v.get("source") == args.source}
        report = generate_report(index)

        if args.json:
            print(json.dumps(report, indent=2))
            return

        if args.pretty:
            render_global_report(report)
        else:
            print_plain_global_report(report)
        return

    # -------------------------
    # blacklist
    # -------------------------
    if args.command == "blacklist":
        if args.bl_action == "add":
            added, purged = add_to_blacklist(args.folder)
            if added:
                console.print(f"[green]Added to blacklist:[/green] {args.folder}")
                if purged > 0:
                    console.print(f"[yellow]Removed {purged} entries from index.[/yellow]")
            else:
                console.print(f"[yellow]Already blacklisted:[/yellow] {args.folder}")

        elif args.bl_action == "remove":
            removed = remove_from_blacklist(args.folder)
            if removed:
                console.print(f"[green]Removed from blacklist:[/green] {args.folder}")
            else:
                console.print(f"[yellow]Not found in blacklist:[/yellow] {args.folder}")

        elif args.bl_action == "show":
            folders = load_blacklist()
            if not folders:
                console.print("[yellow]Blacklist is empty.[/yellow]")
            else:
                console.print(f"\n[bold]Blacklisted folders ({len(folders)}):[/bold]")
                for f in sorted(folders):
                    console.print(f"  [magenta]{f}[/magenta]")
        else:
            console.print("Usage: declutter blacklist [add|remove|show]")
        return

    # -------------------------
    # staging
    # -------------------------
    if args.command == "staging":
        if args.st_action == "show":
            entries = get_staging_summary()
            if not entries:
                console.print("[yellow]Staging is empty. Nothing to restore or delete.[/yellow]")
            else:
                total_bytes = sum(e["size_bytes"] for e in entries)
                table = Table(title=f"Staged Files  |  {len(entries)} file(s)  |  {format_size(total_bytes)} recoverable", box=box.MINIMAL_DOUBLE_HEAD)
                table.add_column("Original Path", style="magenta")
                table.add_column("Staged At", style="cyan")
                table.add_column("Size", justify="right")
                for e in entries:
                    table.add_row(e["original_path"], e["staged_at"], format_size(e['size_bytes']))
                console.print(table)
                console.print("\nTo restore all:        [bold]declutter staging restore --all[/bold]")
                console.print("To free disk space:    [bold]declutter staging empty[/bold]")

        elif args.st_action == "restore":
            if args.all:
                restored, failed = restore_all()
                console.print(f"[green]Restored {restored} file(s).[/green]")
                if failed:
                    console.print(f"[yellow]Failed to restore {failed} file(s) — they may have been deleted from staging.[/yellow]")
            elif args.file:
                if restore_file(args.file):
                    console.print(f"[green]Restored:[/green] {args.file}")
                else:
                    console.print(f"[red]Not found in staging:[/red] {args.file}")
            else:
                console.print("Usage: declutter staging restore --file <path>  OR  --all")

        elif args.st_action == "empty":
            entries = get_staging_summary()
            if not entries:
                console.print("[yellow]Staging is already empty.[/yellow]")
                return
            total_bytes = sum(e["size_bytes"] for e in entries)
            console.print(f"\n[bold red]WARNING: This will permanently delete {len(entries)} staged file(s) ({format_size(total_bytes)}). This cannot be undone.[/bold red]")
            answer = input("Type YES to confirm: ").strip()
            if answer != "YES":
                console.print("[yellow]Aborted.[/yellow]")
                return
            deleted, bytes_freed = empty_staging()
            console.print(f"[green]Done.[/green] Permanently deleted {deleted} file(s), freed {format_size(bytes_freed)}.")
        else:
            console.print("Usage: declutter staging [show|restore|empty]")
        return

    # -------------------------
    # untrack
    # -------------------------
    if args.command == "untrack":
        removed = untrack_folder(args.folder)
        if removed > 0:
            console.print(f"[green]Removed {removed} entries for:[/green] {args.folder}")
            console.print(f"[dim]Folder is not blacklisted — you can scan it again anytime.[/dim]")
        else:
            console.print(f"[yellow]No index entries found for:[/yellow] {args.folder}")
        return

    # -------------------------
    # delete-duplicates
    # -------------------------
    if args.command == "delete-duplicates":
        index = load_combined_index()

        if args.folder and not folder_in_index(index, args.folder):
            folder_path = Path(args.folder).resolve()
            if is_blacklisted(args.folder):
                console.print(f"[red]'{args.folder}' is on the blacklist — skipping scan.[/red]")
                console.print("To remove it from the blacklist: [bold]declutter blacklist remove <folder>[/bold]")
                return
            if is_project_folder(folder_path):
                console.print(f"[red]'{args.folder}' looks like a project folder — skipping auto-scan.[/red]")
                console.print("To scan it anyway: [bold]declutter scan <folder>[/bold]")
                console.print("To blacklist it permanently: [bold]declutter blacklist add <folder>[/bold]")
                return
            console.print(f"[yellow]Folder not scanned yet. Scanning {args.folder} first...[/yellow]")
            run_pipeline(args.folder, args)
            index = load_combined_index()

        targets = get_deletable_paths(index, folder=args.folder)

        if not targets:
            scope = f" in {args.folder}" if args.folder else ""
            console.print(f"[green]No duplicates found{scope}. Nothing to delete.[/green]")
            return

        total_bytes = sum(t["size_bytes"] for t in targets)
        scope_label = f" in [white]{args.folder}[/white]" if args.folder else ""
        console.print(f"\nFound [bold]{len(targets)}[/bold] duplicate file(s){scope_label} — "
                      f"[bold]{format_size(total_bytes)}[/bold] recoverable\n")

        for t in targets:
            origin = "temp file" if t["duplicate_of"] == "__temp_file__" else f"duplicate of {t['duplicate_of']}"
            console.print(f"  [magenta]{t['path']}[/magenta]  ([cyan]{origin}[/cyan], {format_size(t['size_bytes'])})")

        # Dry run — stop here
        if args.dry_run:
            console.print("\n[yellow]Dry run — no files were deleted.[/yellow]")
            return

        # Default (no flags) — confirm once before moving to staging
        if not args.permanent and not args.interactive:
            answer = input("\nMove all to staging? Files can be recovered with 'declutter staging restore --all'. [y/N]: ").strip().lower()
            if answer != "y":
                console.print("[yellow]Aborted.[/yellow]")
                return

        # Permanent delete — confirm all upfront (unless interactive, which confirms per file)
        if args.permanent and not args.interactive:
            console.print(
                "\n[bold red]WARNING: This will permanently delete the files listed above."
                " This cannot be undone.[/bold red]"
            )
            answer = input("Type YES to confirm: ").strip()
            if answer != "YES":
                console.print("[yellow]Aborted.[/yellow]")
                return

        # Interactive — filter targets to only confirmed files
        if args.interactive:
            confirmed = []
            action_word = "permanently delete" if args.permanent else "move to Trash"
            console.print()
            for t in targets:
                origin = "temp file" if t["duplicate_of"] == "__temp_file__" else f"duplicate of {t['duplicate_of']}"
                console.print(f"[magenta]{t['path']}[/magenta]  ({origin}, {format_size(t['size_bytes'])})")
                if args.permanent:
                    console.print(f"[bold red]WARNING: {action_word} is permanent and cannot be undone.[/bold red]")
                answer = input(f"  {action_word.capitalize()}? [y/N]: ").strip().lower()
                if answer == "y":
                    confirmed.append(t)
                else:
                    console.print("  [yellow]Skipped.[/yellow]")
            targets = confirmed

        if not targets:
            console.print("\n[yellow]No files selected. Nothing deleted.[/yellow]")
            return

        # Execute deletion
        action = "Permanently deleting" if args.permanent else "Moving to Trash"
        console.print(f"\n{action} {len(targets)} file(s)...")

        updated_index, deleted, skipped = delete_duplicates(index, targets=targets, permanent=args.permanent)
        local_entries = {k: v for k, v in updated_index.items() if v.get("source") == "local"}
        save_index(local_entries, "local")

        console.print(f"\n[green]Done.[/green] Deleted [bold]{len(deleted)}[/bold] file(s).")
        if skipped:
            console.print(f"\n[yellow]Skipped {len(skipped)} Drive file(s) — open in Drive to delete manually:[/yellow]")
            for s in skipped:
                link = updated_index.get(s, {}).get("web_view_link")
                name = updated_index.get(s, {}).get("name", s)
                if link:
                    console.print(f"  [cyan]{name}[/cyan]")
                    console.print(f"  [blue underline]{link}[/blue underline]")
                else:
                    console.print(f"  [cyan]{name}[/cyan]  (no link available)")
        return

    # -------------------------
    # drive-login
    # -------------------------
    if args.command == "drive-login":
        try:
            GoogleDriveConnector.login(args.account_name)
            console.print(f"[green]Connected Google Drive account:[/green] {args.account_name}")
            console.print(f"Run [bold]declutter scan --source gdrive:{args.account_name}[/bold] to scan it.")
        except FileNotFoundError as e:
            console.print(f"[red]{e}[/red]")
        except Exception as e:
            console.print(f"[red]Login failed:[/red] {e}")
        return

    # -------------------------
    # drive-logout
    # -------------------------
    if args.command == "drive-logout":
        connector = GoogleDriveConnector(args.account_name)
        if connector.token_path.exists():
            connector.logout()
            console.print(f"[green]Disconnected:[/green] {args.account_name}")
            console.print(f"[dim]Index preserved — reconnect with drive-login to restore without rescanning.[/dim]")
        else:
            console.print(f"[yellow]No account found with name:[/yellow] {args.account_name}")
        return

    # -------------------------
    # drive-accounts
    # -------------------------
    if args.command == "drive-accounts":
        accounts = GoogleDriveConnector.list_accounts()
        if not accounts:
            console.print("[yellow]No Google Drive accounts connected.[/yellow]")
            console.print("To connect one: [bold]declutter drive-login <name>[/bold]")
        else:
            console.print(f"\n[bold]Connected Drive accounts ({len(accounts)}):[/bold]")
            for name in sorted(accounts):
                console.print(f"  [cyan]{name}[/cyan]  →  declutter scan --source gdrive:{name}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
