"""
Project extractor.

Module D3 (NLP-08) of the Sprint 2 NLP pipeline.

Reads the PROJECTS section and returns one ProjectEntry per project with its
title, description, highlights, URLs, dates and technologies. Technologies are
linked through the Module E skill extractor, so project tech stacks use the
same canonical skill names as the rest of the profile.

Supported layouts:
    Title | React, Node.js | Jan 2024              Title (Python, FastAPI)
    - bullet ...                                   A one-paragraph description.
    Title: one-line summary                        - Title: description as a bullet
    Tech Stack: Python, Flask                      GitHub: github.com/user/repo
"""

import re
from typing import List, Optional

from app.nlp.extractors._entries import (
    RawEntry,
    clean_text,
    dedupe,
    find_urls,
    is_detail_block,
    section_blocks,
    sections_named,
    split_fragments,
    strip_urls,
)
from app.nlp.extractors.base import BaseExtractor
from app.nlp.extractors.skills import SkillExtractor
from app.nlp.preprocessing import SegmentedDocument, TextBlock
from app.nlp.schemas import ProjectEntry
from app.nlp.sections import SECTION_PROJECTS, SectionMap
from app.nlp.utils import find_date_range, find_single_date

TECH_LINE_RE = re.compile(
    r"^\s*(?:tech(?:nolog(?:y|ies))?(?:\s*stack)?|tools?(?:\s*(?:&|and)\s*technologies)?|"
    r"stack|built\s+(?:with|using)|languages?|skills?\s*used|technologies\s*used)\s*[:\-–]\s*(.+)$",
    re.IGNORECASE,
)
LINK_LABEL_RE = re.compile(
    r"^\s*(?:github|repo(?:sitory)?|source(?:\s*code)?|code|link|live(?:\s*demo)?|demo|"
    r"website|url|deployed(?:\s*at)?|project\s*link)\s*[:\-–]?\s*",
    re.IGNORECASE,
)
# "Title: description" or "Title - description" with a short title
TITLE_PREFIX_RE = re.compile(r"^(?P<title>[^:.!?]{2,70}?)\s*(?::|\s[-–—]\s)\s*(?P<rest>.+)$")

MAX_TITLE_WORDS = 10


def _word_count(text: str) -> int:
    return len(text.split())


def _looks_like_sentence(text: str) -> bool:
    """Long or punctuated lines are descriptions, not titles."""
    return _word_count(text) > MAX_TITLE_WORDS or text.rstrip().endswith((".", "!", "?"))


class ProjectExtractor(BaseExtractor):
    """Extracts ProjectEntry objects from the projects section."""

    def __init__(self, skill_extractor: Optional[SkillExtractor] = None):
        self.skill_extractor = skill_extractor or SkillExtractor()

    def extract(
        self,
        sections: SectionMap,
        document: Optional[SegmentedDocument] = None,
    ) -> List[ProjectEntry]:
        projects: List[ProjectEntry] = []
        for section in sections_named(sections, SECTION_PROJECTS):
            for raw in self.group_entries(section_blocks(section)):
                entry = self.parse_entry(raw)
                if entry is not None:
                    projects.append(entry)
        return projects

    # -- grouping ----------------------------------------------------------

    def group_entries(self, blocks: List[TextBlock]) -> List[RawEntry]:
        entries: List[RawEntry] = []
        current: Optional[RawEntry] = None

        def flush():
            nonlocal current
            if current is not None and not current.is_empty():
                entries.append(current)
            current = None

        has_titles = any(
            not is_detail_block(b) and not _looks_like_sentence(b.text)
            and not TECH_LINE_RE.match(b.text) and not LINK_LABEL_RE.match(b.text)
            for b in blocks
        )

        for block in blocks:
            text = block.text.strip()
            if is_detail_block(block):
                if current is None:
                    if not has_titles and TITLE_PREFIX_RE.match(text):
                        # Bullet-list style: each "Title: description" bullet is a project
                        entries.append(RawEntry(header_blocks=[block]))
                        continue
                    current = RawEntry()
                elif not has_titles and TITLE_PREFIX_RE.match(text) and not TECH_LINE_RE.match(text) \
                        and not LINK_LABEL_RE.match(text):
                    flush()
                    entries.append(RawEntry(header_blocks=[block]))
                    continue
                current.detail_blocks.append(block)
                continue

            # Non-bullet line
            if TECH_LINE_RE.match(text) or LINK_LABEL_RE.match(text) or (
                    current is not None and _looks_like_sentence(text)):
                if current is None:
                    current = RawEntry()
                current.detail_blocks.append(block)
                continue
            # A short non-bullet line is a new project title
            flush()
            current = RawEntry(header_blocks=[block])
        flush()
        return entries

    # -- parsing -----------------------------------------------------------

    def parse_entry(self, raw: RawEntry) -> Optional[ProjectEntry]:
        header = " | ".join(raw.header_lines)
        details = raw.details
        if not header and not details:
            return None

        entry = ProjectEntry(raw_text=raw.text)
        tech_sources: List[str] = []

        # URLs anywhere in the project
        for url in find_urls(raw.text):
            if re.search(r"github\.com|gitlab\.com|bitbucket\.org", url, re.I):
                entry.github_url = entry.github_url or url
            else:
                entry.project_url = entry.project_url or url

        # Dates in the header
        date_range = find_date_range(header)
        if date_range:
            entry.start_date = date_range.start.to_iso() if date_range.start else None
            entry.end_date = date_range.end.to_iso() if date_range.end else None
            header = header.replace(date_range.matched_text, " ")
        else:
            single = find_single_date(header)
            if single:
                entry.end_date = single.to_iso()
                header = re.sub(r"\(?\s*(?:[A-Za-z]{3,9}\.?\s*)?'?\d{2,4}\s*\)?\s*$", "", header).strip()

        header = strip_urls(header)
        title, header_rest = self._split_title(header)
        entry.title = title
        if header_rest:
            tech_sources.append(header_rest)
            if _looks_like_sentence(header_rest) or not self._is_mostly_skills(header_rest):
                entry.description = clean_text(header_rest)

        highlights: List[str] = []
        for line in details:
            tech = TECH_LINE_RE.match(line)
            if tech:
                tech_sources.append(tech.group(1))
                continue
            if LINK_LABEL_RE.match(line) and not clean_text(strip_urls(LINK_LABEL_RE.sub("", line))):
                continue  # pure link line, already captured
            text = clean_text(strip_urls(line)) if find_urls(line) else line.strip()
            if not text:
                continue
            tech_sources.append(text)
            highlights.append(text)

        # A non-bullet paragraph right after the title is the description
        para_blocks = [b.text.strip() for b in raw.detail_blocks if not is_detail_block(b)]
        if entry.description is None:
            for para in para_blocks:
                if para in highlights:
                    entry.description = clean_text(para)
                    highlights.remove(para)
                    break
        if entry.description is None and highlights and len(highlights) == 1 and not raw.header_lines:
            entry.description = highlights.pop()
        entry.highlights = dedupe(highlights)

        if tech_sources:
            skills = self.skill_extractor.extract_from_text("\n".join(tech_sources), SECTION_PROJECTS)
            entry.technologies = dedupe(s.canonical_name for s in skills if s.category != "soft_skills")

        if entry.title is None and entry.description is None and not entry.highlights:
            return None
        entry.confidence = round(
            0.5 * bool(entry.title) + 0.25 * bool(entry.description or entry.highlights)
            + 0.15 * bool(entry.technologies) + 0.1 * bool(entry.github_url or entry.project_url), 2
        )
        return entry

    def _split_title(self, header: str):
        """Split a header line into (title, rest)."""
        header = re.sub(r"\s+", " ", header or "").strip(" \t|,;:-–—")
        if not header:
            return None, None
        # "Title (React, Node.js)"
        m = re.match(r"^(?P<title>[^()]+?)\s*\((?P<rest>[^()]+)\)\s*(?P<tail>.*)$", header)
        if m and not _looks_like_sentence(m.group("title")):
            rest = " ".join(x for x in (m.group("rest"), m.group("tail")) if x and x.strip())
            return clean_text(m.group("title")), clean_text(rest)
        frags = split_fragments(header)
        if len(frags) > 1 and not _looks_like_sentence(frags[0]):
            return clean_text(frags[0]), clean_text(" | ".join(frags[1:]))
        m = TITLE_PREFIX_RE.match(header)
        if m and _word_count(m.group("title")) <= MAX_TITLE_WORDS:
            return clean_text(m.group("title")), clean_text(m.group("rest"))
        if _looks_like_sentence(header):
            return None, clean_text(header)
        return clean_text(header), None

    def _is_mostly_skills(self, text: str) -> bool:
        """True for lines like 'React, Node.js, MongoDB' (a tech list, not prose)."""
        pieces = [p.strip() for p in re.split(r"[,|/]", text) if p.strip()]
        if not pieces:
            return False
        skills = self.skill_extractor.extract_from_text(text, SECTION_PROJECTS)
        return len(skills) >= max(1, len(pieces) // 2)


__all__ = ["ProjectExtractor"]
