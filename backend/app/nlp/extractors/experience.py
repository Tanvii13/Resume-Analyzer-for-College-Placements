"""
Experience and internship extractor.

Module D2 (NLP-07) of the Sprint 2 NLP pipeline.

Reads the EXPERIENCE and INTERNSHIPS sections and returns one ExperienceEntry
per role, with job title, company, location, dates, duration, responsibilities
and the technologies mentioned (via the Module E skill extractor).

Supported header layouts:
    Title                           |  Company | Dates             |  Title at Company | Dates
    Company | Dates                 |  Title                       |  Title, Company (Dates)
    - bullets...                    |  - bullets...                |  - bullets...

Entries are split on header lines that follow bullets, and on date lines when
several roles are listed without bullets.
"""

from datetime import date
import re
from typing import List, Optional, Tuple

from app.nlp.extractors._entries import (
    RawEntry,
    clean_text,
    contains_any,
    dedupe,
    is_detail_block,
    is_location,
    section_blocks,
    sections_named,
    split_fragments,
)
from app.nlp.extractors.base import BaseExtractor
from app.nlp.extractors.skills import SkillExtractor
from app.nlp.preprocessing import SegmentedDocument, TextBlock
from app.nlp.schemas import ExperienceEntry
from app.nlp.sections import SECTION_EXPERIENCE, SECTION_INTERNSHIPS, SectionMap
from app.nlp.utils import DateRange, find_date_range, find_single_date

TITLE_WORDS = [
    "intern", "internship", "engineer", "developer", "analyst", "assistant", "associate",
    "manager", "lead", "researcher", "research", "consultant", "designer", "scientist",
    "trainee", "fellow", "architect", "specialist", "officer", "executive", "tester",
    "administrator", "contributor", "volunteer", "sde", "swe", "head", "coordinator",
    "programmer", "director", "founder", "co-founder", "cofounder", "president",
    "secretary", "mentor", "tutor", "teaching assistant", "ta", "member", "freelancer",
    "freelance", "apprentice", "technician", "representative", "ambassador", "qa",
    "devops", "full stack", "full-stack", "backend", "frontend", "front-end", "back-end",
]
COMPANY_WORDS = [
    "inc", "inc.", "ltd", "ltd.", "limited", "pvt", "pvt.", "private", "llp", "llc",
    "corp", "corporation", "technologies", "technology", "tech", "labs", "lab", "solutions",
    "systems", "software", "services", "consulting", "consultancy", "infotech", "analytics",
    "university", "institute", "college", "foundation", "group", "company", "co.",
    "industries", "enterprises", "studio", "studios", "ventures", "global", "digital",
]
INTERNSHIP_RE = re.compile(r"(?<![a-z])(?:intern|internship|summer\s+trainee|industrial\s+training|apprentice)(?![a-z])", re.I)


def _strip_dates(text: str, date_range: Optional[DateRange]) -> str:
    if date_range and date_range.matched_text:
        text = text.replace(date_range.matched_text, " ")
    # Lone dates like "(May 2024)" and empty brackets left behind
    text = re.sub(r"\(\s*\)|\[\s*\]", " ", text)
    return text


class ExperienceExtractor(BaseExtractor):
    """Extracts ExperienceEntry objects from experience and internship sections."""

    def __init__(self, skill_extractor: Optional[SkillExtractor] = None, today: Optional[date] = None):
        self.skill_extractor = skill_extractor or SkillExtractor()
        self.today = today

    def extract(
        self,
        sections: SectionMap,
        document: Optional[SegmentedDocument] = None,
    ) -> List[ExperienceEntry]:
        entries: List[ExperienceEntry] = []
        for section in sections_named(sections, SECTION_EXPERIENCE, SECTION_INTERNSHIPS):
            for raw in self.group_entries(section_blocks(section)):
                raw.section_name = section.canonical_name
                entry = self.parse_entry(raw)
                if entry is not None:
                    entries.append(entry)
        return entries

    # -- grouping ----------------------------------------------------------

    def group_entries(self, blocks: List[TextBlock]) -> List[RawEntry]:
        """Group blocks into one RawEntry per role."""
        entries: List[RawEntry] = []
        current = RawEntry()
        for block in blocks:
            if is_detail_block(block):
                current.detail_blocks.append(block)
                continue
            if current.detail_blocks:
                entries.append(current)
                current = RawEntry()
            current.header_blocks.append(block)
        if not current.is_empty():
            entries.append(current)

        # Several roles listed back-to-back without bullets: split on date lines
        split: List[RawEntry] = []
        for entry in entries:
            split.extend(self._split_multi_date_header(entry))
        return split

    @staticmethod
    def _split_multi_date_header(entry: RawEntry) -> List[RawEntry]:
        blocks = entry.header_blocks
        dated = [i for i, b in enumerate(blocks) if find_date_range(b.text) or find_single_date(b.text)]
        if len(dated) <= 1:
            return [entry]
        chunks: List[List[TextBlock]] = []
        if dated[0] == 0:
            # Layout "Company | Dates" first: each date line starts an entry
            bounds = dated + [len(blocks)]
            chunks = [blocks[bounds[i]:bounds[i + 1]] for i in range(len(dated))]
        else:
            # Layout "Title" then "Company | Dates": each date line ends an entry
            start = 0
            for i in dated:
                chunks.append(blocks[start:i + 1])
                start = i + 1
            if start < len(blocks):
                chunks[-1].extend(blocks[start:])
        result = [RawEntry(header_blocks=c) for c in chunks if c]
        result[-1].detail_blocks = entry.detail_blocks
        return result

    # -- parsing -----------------------------------------------------------

    def parse_entry(self, raw: RawEntry) -> Optional[ExperienceEntry]:
        headers = raw.header_lines
        details = raw.details
        if not headers and not details:
            return None
        if not headers:
            # Bullets with no header line: keep them, but we can't name the role
            headers = []

        header_text = " | ".join(headers)
        date_range = find_date_range(header_text) or find_date_range(" ".join(details[:1]))

        title, company, location = self._title_company_location(headers, date_range)

        entry = ExperienceEntry(
            company_name=company,
            job_title=title,
            location=location,
            responsibilities=dedupe(details),
            source_section=raw.section_name,
            raw_text=raw.text,
        )

        if date_range:
            entry.start_date = date_range.start.to_iso() if date_range.start else None
            entry.end_date = date_range.end.to_iso() if date_range.end else None
            entry.is_current = date_range.is_current
            entry.duration_months = date_range.duration_months(self.today)
        else:
            single = find_single_date(header_text)
            if single:
                entry.start_date = single.to_iso()

        entry.is_internship = (
            raw.section_name == SECTION_INTERNSHIPS
            or bool(INTERNSHIP_RE.search(header_text))
        )

        tech_text = "\n".join(details + headers)
        if tech_text.strip():
            skills = self.skill_extractor.extract_from_text(tech_text, raw.section_name or SECTION_EXPERIENCE)
            entry.technologies_used = dedupe(
                s.canonical_name for s in skills if s.category != "soft_skills"
            )

        entry.confidence = round(
            0.35 * bool(title) + 0.35 * bool(company) + 0.2 * bool(date_range) + 0.1 * bool(details), 2
        )
        return entry

    def _title_company_location(
        self, headers: List[str], date_range: Optional[DateRange]
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        fragments: List[str] = []
        for line in headers:
            line = _strip_dates(line, date_range)
            # "SDE Intern at Google" / "Developer @ Startup"
            m = re.match(r"^(.*?)\s+(?:at|@)\s+(.+)$", line.strip(), re.I)
            if m and contains_any(m.group(1), TITLE_WORDS):
                fragments.extend([m.group(1), *split_fragments(m.group(2))])
                continue
            for frag in split_fragments(line):
                # "Software Intern, Credence Analytics, Pune" -> comma pieces
                pieces = [p.strip() for p in frag.split(",")] if "," in frag else [frag]
                fragments.extend(p for p in pieces if p)

        title = company = location = None
        leftovers: List[str] = []
        for frag in fragments:
            frag = clean_text(frag) or ""
            if not frag or find_date_range(frag) or re.fullmatch(r"[\d\s/'-]+", frag):
                continue
            if location is None and is_location(frag):
                location = frag
                continue
            if is_location(frag):
                continue
            is_title = contains_any(frag, TITLE_WORDS)
            is_company = contains_any(frag, COMPANY_WORDS)
            if title is None and is_title and not (is_company and not INTERNSHIP_RE.search(frag)):
                title = frag
            elif company is None and is_company and not is_title:
                company = frag
            else:
                leftovers.append(frag)

        # Fill gaps from unclassified fragments, in reading order
        for frag in leftovers:
            if title is None and contains_any(frag, TITLE_WORDS):
                title = frag
            elif company is None:
                company = frag
            elif title is None:
                title = frag
        return title, company, location


__all__ = ["ExperienceExtractor"]
