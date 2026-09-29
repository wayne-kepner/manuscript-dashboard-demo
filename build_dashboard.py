"""Build a local manuscript dashboard from a private Markdown pipeline."""

from __future__ import annotations

import argparse
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "pipeline.local.md"
OUTPUT = ROOT / "dashboard.local.html"

STATUS = {
    "admin check": "admin",
    "submitted": "submitted",
    "under review": "review",
    "revise and resubmit": "rr",
    "revised submitted": "revised",
    "accepted": "accepted",
    "rejected": "rejected",
    "published": "published",
}


def clean(value: str) -> str:
    return "" if value.strip() in ("", "—", "-") else value.strip()


def parse_pipeline(source: str) -> dict[str, list[dict[str, str]]]:
    sections: dict[str, list[dict[str, str]]] = {}
    section = ""
    headers: list[str] = []
    for line in source.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            sections[section] = []
            headers = []
        elif section and line.startswith("| "):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if all(set(cell) <= {"-", " ", ":"} for cell in cells):
                continue
            if not headers:
                headers = cells
            elif len(cells) == len(headers):
                sections[section].append(dict(zip(headers, cells)))
            else:
                raise ValueError(f"A row in {section} has {len(cells)} cells; expected {len(headers)}.")
    return sections


def validated_date(value: str, title: str) -> str:
    value = clean(value)
    if not value:
        raise ValueError(f"Add a status change date for {title}.")
    date.fromisoformat(value)
    return value


def manuscript_card(row: dict[str, str]) -> str:
    title = clean(row.get("Title", ""))
    if not title:
        raise ValueError("Every manuscript needs a title.")
    status_name = clean(row.get("Status", "")).lower()
    status = STATUS.get(status_name, "work")
    status_date = validated_date(row.get("Status change noted", ""), title)
    deadline = clean(row.get("Deadline", ""))
    if deadline:
        date.fromisoformat(deadline)
    work_tags = {
        "submission prep": "prep",
        "drafting": "drafting",
        "analysis preparation": "analysis",
        "data acquisition setup": "analysis",
        "formatting": "formatting",
    }
    subtag = work_tags.get(status_name, "") if status == "work" else ""
    attrs = [f'data-status="{status}"', f'data-status-date="{status_date}"']
    if deadline:
        attrs.append(f'data-deadline="{deadline}"')
    if status == "work":
        attrs.append(f'data-status-label="{escape(status_name.title(), quote=True)}"')
    if subtag:
        attrs.append(f'data-subtags="{subtag}"')
    journal = clean(row.get("Journal", "")) or "No journal target"
    details = [
        ("Manuscript ID", clean(row.get("Manuscript ID", ""))),
        ("Notes", clean(row.get("Notes", ""))),
        ("Coauthors", clean(row.get("Coauthors", ""))),
    ]
    details_html = "".join(
        f"<p><b>{label}</b>{escape(value)}</p>" for label, value in details if value
    )
    return (
        f'<article class="item" {" ".join(attrs)}>'
        '<div class="item-head"><div><div class="status-row"></div>'
        f'<h3>{escape(title)}</h3><p class="journal">{escape(journal)}</p>'
        '</div><p class="date-line age-line"></p></div>'
        f'<details><summary>Details</summary><div class="details">{details_html}</div></details>'
        '</article>'
    )


def archive_card(row: dict[str, str]) -> str:
    status = clean(row.get("Status", "")).lower()
    title = clean(row.get("Title", ""))
    journal = clean(row.get("Journal", "")) or "No journal target"
    changed = validated_date(row.get("Status change noted", ""), title)
    return (
        f'<article><span class="badge {escape(status, quote=True)}">{escape(status.title())}</span>'
        f'<h3>{escape(title)}</h3><p>{escape(journal)} · {changed}</p></article>'
    )


def queue_card(row: dict[str, str], section: str) -> str:
    title = clean(row.get("Title", row.get("Task", "")))
    label = clean(row.get("Type", row.get("Role", section.rstrip("s"))))
    note = clean(row.get("Status", row.get("Notes", "")))
    deadline = clean(row.get("Deadline", row.get("Date", "")))
    body = f'<b>{escape(label)}</b><h3>{escape(title)}</h3>'
    if note:
        body += f'<p>{escape(note)}</p>'
    if deadline:
        body += f'<p>Due {escape(deadline)}</p>'
    return f'<article data-pipeline-section="{escape(section, quote=True)}">{body}</article>'


def render_dashboard(source_path: Path = SOURCE, output_path: Path = OUTPUT) -> Path:
    data = parse_pipeline(source_path.read_text(encoding="utf-8"))
    template = (ROOT / "index.html").read_text(encoding="utf-8")
    manuscripts = []
    archive = []
    today = date.today()
    for row in data.get("Manuscripts", []):
        status = clean(row.get("Status", "")).lower()
        changed = date.fromisoformat(validated_date(row.get("Status change noted", ""), row.get("Title", "")))
        if status == "published" or (status == "accepted" and (today - changed).days > 14):
            archive.append(archive_card(row))
        else:
            manuscripts.append(manuscript_card(row))
    queue = [
        queue_card(row, section)
        for section in ("Projects/grants", "Events", "Todos")
        for row in data.get(section, [])
    ]
    for marker, cards in (
        ("<!-- MANUSCRIPT_CARDS -->", manuscripts),
        ("<!-- YEAR_CARDS -->", archive),
        ("<!-- QUEUE_CARDS -->", queue),
    ):
        if template.count(marker) != 1:
            raise ValueError(f"The dashboard template needs exactly one {marker} marker.")
        template = template.replace(marker, "".join(cards))
    output_path.write_text(template, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.resolve() == (ROOT / "index.html").resolve():
        parser.error("Choose a local output file instead of overwriting index.html.")
    print(render_dashboard(args.input, args.output))
