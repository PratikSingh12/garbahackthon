"""
Command Line Interface for Job Hunt Autopilot.
Run with: python -m job_autopilot.cli --input data/sample_inbox.json
"""

import argparse
import os
import sys
from datetime import datetime, timezone

# Ensure robust unicode output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from job_autopilot.parser import load_inbox
from job_autopilot.tracker import JobHuntTracker
from job_autopilot.models import StageEnum


def main():
    parser = argparse.ArgumentParser(
        description="Job Hunt Autopilot: Track every application. Catch every fake offer."
    )
    parser.add_argument(
        "--input",
        "-i",
        default="data/sample_inbox.json",
        help="Path to sample inbox file (.json or .mbox)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["auto", "json", "mbox"],
        default="auto",
        help="Inbox file format (default: auto)",
    )
    parser.add_argument(
        "--reference-date",
        "-r",
        default=None,
        help="Reference date for calculating 7-day follow-ups (YYYY-MM-DD). Defaults to latest email date.",
    )
    parser.add_argument(
        "--export-csv",
        default=None,
        help="Path to export results as CSV",
    )

    args = parser.parse_args()
    console = Console()

    # Resolve input path
    input_path = args.input
    if not os.path.isabs(input_path) and not os.path.exists(input_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate = os.path.join(base_dir, input_path)
        if os.path.exists(candidate):
            input_path = candidate

    if not os.path.exists(input_path):
        console.print(f"[bold red]Error:[/bold red] Input file not found: {input_path}")
        sys.exit(1)

    # Reference date handling
    ref_dt = None
    if args.reference_date:
        try:
            ref_dt = datetime.strptime(args.reference_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            console.print(f"[yellow]Warning: Invalid date format for --reference-date. Using latest email date.[/yellow]")

    # Banner
    banner_text = Text()
    banner_text.append("✈️  JOB HUNT AUTOPILOT\n", style="bold cyan")
    banner_text.append("Track every application. Catch every fake offer.\n", style="bold white")
    banner_text.append("Designed for high-volume post-layoff job searches.", style="italic dim")
    console.print(Panel(banner_text, border_style="cyan", expand=False))

    console.print(f"\n[cyan]📥 Ingesting inbox from:[/cyan] {input_path}")
    emails = load_inbox(input_path, format_hint=args.format)
    console.print(f"[green]✓ Successfully loaded {len(emails)} emails.[/green]\n")

    # Run Tracker
    tracker = JobHuntTracker(reference_date=ref_dt)
    records = tracker.process_emails(emails)
    stats = tracker.get_stats()

    # Executive KPI Summary Cards
    summary_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    summary_table.add_column("Total Emails", justify="center")
    summary_table.add_column("Applications", justify="center")
    summary_table.add_column("Interviews", justify="center", style="bold cyan")
    summary_table.add_column("Legit Offers", justify="center", style="bold green")
    summary_table.add_column("Rejections", justify="center", style="dim")
    summary_table.add_column("Follow-ups Due (≥7d)", justify="center", style="bold yellow")
    summary_table.add_column("🚨 Scams Caught", justify="center", style="bold red on black")

    summary_table.add_row(
        str(stats.total_emails),
        str(stats.total_applications),
        str(stats.interviews_scheduled),
        str(stats.offers_received),
        str(stats.rejections_count),
        f"[yellow]{stats.follow_ups_due}[/yellow]",
        f"[bold red]{stats.scams_flagged}[/bold red]",
    )
    console.print(summary_table)

    # 1. SCAM RADAR (CRITICAL - HIGHLIGHTED IN BOLD RED WITH REASONS)
    scam_records = [r for r in records if r.is_scam]
    if scam_records:
        console.print("\n")
        console.print(Panel("[bold red]🚨 SCAM RADAR: FAKE OFFERS FLAGGED WITH REASONS[/bold red]\nTargeted predatory scams exploiting laid-off candidates", border_style="red"))
        
        scam_table = Table(box=box.HEAVY_EDGE, border_style="red", header_style="bold red")
        scam_table.add_column("#", justify="center", width=4)
        scam_table.add_column("Impersonated Entity", style="bold white", width=22)
        scam_table.add_column("Sender / Domain", style="dim", width=30)
        scam_table.add_column("Subject Line", width=34)
        scam_table.add_column("Identified Scam Reasons & Trap Analysis", style="red")

        for idx, s in enumerate(scam_records, 1):
            reasons_fmt = "\n".join([f"• {r}" for r in s.scam_reasons])
            scam_table.add_row(
                str(idx),
                s.company,
                s.sender_email or s.sender,
                s.latest_subject,
                reasons_fmt
            )
        console.print(scam_table)

    # 2. 7-DAY FOLLOW-UP REMINDERS
    follow_up_records = [r for r in records if r.follow_up_due]
    if follow_up_records:
        console.print("\n")
        console.print(Panel("[bold yellow]⏰ FOLLOW-UP RADAR: 7+ DAYS ELAPSED WITH NO RESPONSE[/bold yellow]\nCandidate action recommended to keep application warm", border_style="yellow"))
        
        fu_table = Table(box=box.ROUNDED, border_style="yellow", header_style="bold yellow")
        fu_table.add_column("Company", style="bold white")
        fu_table.add_column("Role", style="cyan")
        fu_table.add_column("Days Silent", justify="center", style="bold red")
        fu_table.add_column("Action / Guidance", style="white")

        for r in follow_up_records:
            fu_table.add_row(
                r.company,
                r.role,
                f"{r.days_elapsed} days",
                f"Follow-up email template ready to send to {r.company}."
            )
        console.print(fu_table)

    # 3. PIPELINE OVERVIEW (Applied, Interview, Offer, Rejected)
    console.print("\n")
    console.print(Panel("[bold cyan]📋 COMPLETE APPLICATION PIPELINE TRACKER[/bold cyan]", border_style="cyan"))
    
    pipeline_table = Table(box=box.SIMPLE_HEAD, header_style="bold")
    pipeline_table.add_column("Stage", width=12)
    pipeline_table.add_column("Company", style="bold", width=18)
    pipeline_table.add_column("Role", width=32)
    pipeline_table.add_column("Date", justify="center", width=12)
    pipeline_table.add_column("Status / Follow-Up Alert", width=36)

    stage_styles = {
        StageEnum.OFFER: ("[bold green]OFFER[/bold green]", "green"),
        StageEnum.INTERVIEW: ("[bold cyan]INTERVIEW[/bold cyan]", "cyan"),
        StageEnum.APPLIED: ("[blue]APPLIED[/blue]", "blue"),
        StageEnum.REJECTED: ("[dim]REJECTED[/dim]", "dim"),
        StageEnum.SCAM: ("[bold red]FAKE OFFER[/bold red]", "red"),
    }

    for r in records:
        stage_tag, _ = stage_styles.get(r.current_stage, (r.current_stage.value.upper(), "white"))
        status_note = ""
        if r.current_stage == StageEnum.OFFER:
            status_note = "[bold green]🎉 Formal offer extended![/bold green]"
        elif r.current_stage == StageEnum.INTERVIEW:
            status_note = "[bold cyan]💬 Technical screen / Loop active[/bold cyan]"
        elif r.current_stage == StageEnum.REJECTED:
            status_note = "[dim]Archived - Closed[/dim]"
        elif r.current_stage == StageEnum.SCAM:
            status_note = "[bold red]🚫 BLOCKED: Predatory Fraud[/bold red]"
        elif r.current_stage == StageEnum.APPLIED:
            if r.follow_up_due:
                status_note = f"[bold yellow]⚠️ Follow-up due ({r.days_elapsed}d elapsed)[/bold yellow]"
            else:
                status_note = f"[dim]In review ({r.days_elapsed}d ago)[/dim]"

        pipeline_table.add_row(
            stage_tag,
            r.company,
            r.role,
            r.application_date.strftime("%b %d"),
            status_note
        )
    console.print(pipeline_table)

    # Optional CSV Export
    if args.export_csv:
        import pandas as pd
        data = [{
            "company": r.company,
            "role": r.role,
            "stage": r.current_stage.value,
            "days_elapsed": r.days_elapsed,
            "follow_up_due": r.follow_up_due,
            "is_scam": r.is_scam,
            "scam_reasons": "; ".join(r.scam_reasons),
            "date": r.application_date.isoformat(),
            "latest_subject": r.latest_subject
        } for r in records]
        df = pd.DataFrame(data)
        df.to_csv(args.export_csv, index=False)
        console.print(f"\n[green]✓ Exported {len(df)} records to CSV: {args.export_csv}[/green]")

    console.print("\n[bold green]✓ Pipeline completed successfully![/bold green]\n")


if __name__ == "__main__":
    main()
