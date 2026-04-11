#!/usr/bin/env python3
"""
Cyber Job Hunter - Cybersecurity Job Scraper & Resume Matcher

Searches federal (USAJobs) and private sector job boards for cybersecurity
positions, then scores and ranks each listing against your resume profile.

Usage:
    python -m cyber_job_hunter.main [options]

Options:
    --federal-only      Search only USAJobs (federal positions)
    --private-only      Search only private sector job boards
    --top N             Show top N results (default: 20)
    --min-score N       Only show jobs with score >= N (default: 0)
    --export FILE       Export results to CSV file
    --no-color          Disable colored output
"""

import argparse
import csv
import os
import sys

from dotenv import load_dotenv

from cyber_job_hunter.resume_profile import RESUME
from cyber_job_hunter.usajobs_client import fetch_all_cyber_jobs
from cyber_job_hunter.private_jobs import fetch_all_private_jobs
from cyber_job_hunter.matcher import rank_jobs

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def color_score(score, use_color=True):
    """Color a score based on its value."""
    if not use_color:
        return f"{score:.1f}"
    if score >= 70:
        return f"{GREEN}{score:.1f}{RESET}"
    elif score >= 40:
        return f"{YELLOW}{score:.1f}{RESET}"
    else:
        return f"{RED}{score:.1f}{RESET}"


def print_banner(use_color=True):
    """Print the tool banner."""
    banner = """
    ╔══════════════════════════════════════════════════════╗
    ║           CYBER JOB HUNTER v1.0                      ║
    ║   Cybersecurity Job Scraper & Resume Matcher          ║
    ╚══════════════════════════════════════════════════════╝
    """
    if use_color:
        print(f"{CYAN}{BOLD}{banner}{RESET}")
    else:
        print(banner)


def print_job(rank, job, score_info, use_color=True):
    """Print a single job result."""
    b = BOLD if use_color else ""
    d = DIM if use_color else ""
    c = CYAN if use_color else ""
    r = RESET if use_color else ""

    score_str = color_score(score_info["total_score"], use_color)
    print(f"\n{'─' * 60}")
    print(f"  {b}#{rank}{r}  Score: {score_str}/100")
    print(f"  {b}{job['title']}{r}")
    print(f"  {c}{job['organization']}{r}", end="")
    if job.get("department"):
        print(f" ({job['department']})", end="")
    print()
    print(f"  Location: {job['location']}")

    if job["salary_min"] != "N/A":
        print(f"  Salary: ${job['salary_min']} - ${job['salary_max']}")

    if job.get("grade") and job["grade"] != "N/A":
        print(f"  Grade: {job['grade']}")

    print(f"  Source: {job['source']}")

    if job.get("open_date") and job["open_date"] != "N/A":
        print(f"  Posted: {job['open_date'][:10]}", end="")
        if job.get("close_date") and job["close_date"] != "N/A":
            print(f"  |  Closes: {job['close_date'][:10]}", end="")
        print()

    print(f"  {d}URL: {job['url']}{r}")

    # Match details
    if score_info["matched_skills"]:
        skills_str = ", ".join(score_info["matched_skills"][:8])
        if len(score_info["matched_skills"]) > 8:
            skills_str += f" (+{len(score_info['matched_skills']) - 8} more)"
        print(f"  {d}Matched skills: {skills_str}{r}")

    if score_info["matched_keywords"]:
        kw_str = ", ".join(score_info["matched_keywords"][:6])
        if len(score_info["matched_keywords"]) > 6:
            kw_str += f" (+{len(score_info['matched_keywords']) - 6} more)"
        print(f"  {d}Matched keywords: {kw_str}{r}")


def print_search_urls(urls, use_color=True):
    """Print manual search URLs for boards that block scraping."""
    b = BOLD if use_color else ""
    c = CYAN if use_color else ""
    r = RESET if use_color else ""

    print(f"\n{'═' * 60}")
    print(f"  {b}MANUAL SEARCH LINKS{r}")
    print(f"  (These sites block scraping - open in your browser)")
    print(f"{'═' * 60}")
    for entry in urls:
        print(f"\n  {b}{entry['board']}{r}")
        print(f"  {c}{entry['url']}{r}")


def print_summary(scored_jobs, use_color=True):
    """Print a summary of results."""
    b = BOLD if use_color else ""
    r = RESET if use_color else ""

    if not scored_jobs:
        print("\n  No jobs found. Try adjusting search parameters.")
        return

    scores = [s["total_score"] for _, s in scored_jobs]
    avg_score = sum(scores) / len(scores)
    high_matches = sum(1 for s in scores if s >= 70)
    med_matches = sum(1 for s in scores if 40 <= s < 70)

    sources = {}
    for job, _ in scored_jobs:
        src = job["source"]
        sources[src] = sources.get(src, 0) + 1

    print(f"\n{'═' * 60}")
    print(f"  {b}SUMMARY{r}")
    print(f"{'═' * 60}")
    print(f"  Total jobs found:    {len(scored_jobs)}")
    print(f"  Average match score: {avg_score:.1f}")
    print(f"  Strong matches (70+): {high_matches}")
    print(f"  Good matches (40-69): {med_matches}")
    print(f"  Sources: {', '.join(f'{k}: {v}' for k, v in sources.items())}")


def export_csv(scored_jobs, filepath):
    """Export results to a CSV file."""
    fieldnames = [
        "rank", "score", "title", "organization", "department",
        "location", "salary_min", "salary_max", "grade", "source",
        "url", "open_date", "close_date", "matched_skills", "matched_keywords",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, (job, score_info) in enumerate(scored_jobs, 1):
            writer.writerow({
                "rank": i,
                "score": score_info["total_score"],
                "title": job["title"],
                "organization": job["organization"],
                "department": job.get("department", ""),
                "location": job["location"],
                "salary_min": job["salary_min"],
                "salary_max": job["salary_max"],
                "grade": job.get("grade", ""),
                "source": job["source"],
                "url": job["url"],
                "open_date": job.get("open_date", ""),
                "close_date": job.get("close_date", ""),
                "matched_skills": "; ".join(score_info["matched_skills"]),
                "matched_keywords": "; ".join(score_info["matched_keywords"]),
            })

    print(f"\n[+] Results exported to: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Cyber Job Hunter - Search & match cybersecurity jobs against your resume"
    )
    parser.add_argument("--federal-only", action="store_true", help="Search only federal jobs (USAJobs)")
    parser.add_argument("--private-only", action="store_true", help="Search only private sector jobs")
    parser.add_argument("--top", type=int, default=20, help="Number of top results to display (default: 20)")
    parser.add_argument("--min-score", type=float, default=0, help="Minimum match score to display (default: 0)")
    parser.add_argument("--export", type=str, help="Export results to CSV file")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    args = parser.parse_args()

    use_color = not args.no_color and sys.stdout.isatty()

    # Load .env for API keys
    load_dotenv()

    print_banner(use_color)

    all_jobs = []
    search_urls = []

    # --- Federal Jobs ---
    if not args.private_only:
        print("\n[*] Searching USAJobs for federal cybersecurity positions...")
        federal_jobs = fetch_all_cyber_jobs(
            target_agencies=RESUME["target_federal_agencies"]
        )
        all_jobs.extend(federal_jobs)

    # --- Private Sector Jobs ---
    if not args.federal_only:
        print("\n[*] Searching private sector job boards...")
        private_jobs, search_urls = fetch_all_private_jobs(
            target_companies=RESUME["target_private_companies"]
        )
        all_jobs.extend(private_jobs)

    if not all_jobs:
        print("\n[!] No jobs found from any source.")
        if search_urls:
            print_search_urls(search_urls, use_color)
        print("\nTips:")
        print("  - For federal jobs: set USAJOBS_API_KEY and USAJOBS_EMAIL in .env")
        print("  - Check your internet connection")
        print("  - Some job boards may be temporarily unavailable")
        return

    # --- Score & Rank ---
    print(f"\n[*] Scoring {len(all_jobs)} jobs against your resume...")
    scored_jobs = rank_jobs(all_jobs, RESUME)

    # Apply minimum score filter
    if args.min_score > 0:
        scored_jobs = [(j, s) for j, s in scored_jobs if s["total_score"] >= args.min_score]

    # --- Display Results ---
    display_count = min(args.top, len(scored_jobs))
    print(f"\n{'═' * 60}")
    b = BOLD if use_color else ""
    r = RESET if use_color else ""
    print(f"  {b}TOP {display_count} CYBERSECURITY JOBS FOR YOUR PROFILE{r}")
    print(f"{'═' * 60}")

    for i, (job, score_info) in enumerate(scored_jobs[:display_count], 1):
        print_job(i, job, score_info, use_color)

    # Summary
    print_summary(scored_jobs, use_color)

    # Manual search URLs
    if search_urls and not args.federal_only:
        print_search_urls(search_urls, use_color)

    # Export
    if args.export:
        export_csv(scored_jobs, args.export)


if __name__ == "__main__":
    main()
