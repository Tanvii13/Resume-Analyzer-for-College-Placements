"""Central, serializable NLP implementation and configuration provenance."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Optional
from pydantic import BaseModel, ConfigDict, Field

NLP_PIPELINE_VERSION = "5.0.0"
VERSION_METADATA_SCHEMA_VERSION = "1.0.0"
RESUME_PARSER_VERSION = "1.0.0"

class NLPVersionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    schema_version: str = VERSION_METADATA_SCHEMA_VERSION
    pipeline_version: str = NLP_PIPELINE_VERSION
    component_versions: dict[str, str] = Field(default_factory=dict)
    scoring_configuration_version: Optional[str] = None
    scoring_configuration_fingerprint: Optional[str] = None
    taxonomy_version: Optional[str] = None
    taxonomy_fingerprint: Optional[str] = None
    skill_aliases_version: Optional[str] = None
    skill_aliases_fingerprint: Optional[str] = None
    created_at: Optional[datetime] = None

def configuration_fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"

def _file_info(path: Path) -> tuple[Optional[str], Optional[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("version"), configuration_fingerprint(payload)

def build_version_metadata(components: Iterable[str], *, created_at: Optional[datetime] = None,
                           scoring_weights: Optional[Any] = None) -> NLPVersionMetadata:
    """Snapshot only the requested components; constants remain authoritative in owners."""
    from app.nlp.analysis.schemas import SPRINT3_ANALYZER_VERSION
    from app.nlp.content.schemas import CONTENT_ANALYZER_VERSION
    from app.nlp.formatting.schemas import FORMATTING_ANALYZER_VERSION
    from app.nlp.improvement.schemas import IMPROVEMENT_ENGINE_VERSION
    from app.nlp.job_matching.matcher_schemas import MATCHER_ENGINE_VERSION
    from app.nlp.job_matching.schemas import JOB_PARSER_VERSION
    from app.nlp.job_matching.skill_engine import ENGINE_VERSION as SKILL_ENGINE_VERSION
    from app.nlp.recommendations.rules import RULE_SET_VERSION
    from app.nlp.schemas import PIPELINE_VERSION
    from app.nlp.scoring.weights import SCORING_RULE_VERSION
    from app.nlp.taxonomy import SKILL_ALIASES_FILE, SKILLS_TAXONOMY_FILE
    versions = {"resume_parser": RESUME_PARSER_VERSION, "profile_extraction": PIPELINE_VERSION,
        "scoring": SCORING_RULE_VERSION, "formatting": FORMATTING_ANALYZER_VERSION,
        "content": CONTENT_ANALYZER_VERSION, "improvement": IMPROVEMENT_ENGINE_VERSION,
        "recommendations": RULE_SET_VERSION, "analysis": SPRINT3_ANALYZER_VERSION,
        "job_parser": JOB_PARSER_VERSION, "skill_matching": SKILL_ENGINE_VERSION,
        "job_matching": MATCHER_ENGINE_VERSION}
    taxonomy_version, taxonomy_fingerprint = _file_info(SKILLS_TAXONOMY_FILE)
    aliases_version, aliases_fingerprint = _file_info(SKILL_ALIASES_FILE)
    config = scoring_weights.model_dump(mode="json") if scoring_weights is not None else None
    return NLPVersionMetadata(component_versions={x: versions[x] for x in components if x in versions},
        taxonomy_version=taxonomy_version, taxonomy_fingerprint=taxonomy_fingerprint,
        skill_aliases_version=aliases_version, skill_aliases_fingerprint=aliases_fingerprint,
        created_at=created_at, scoring_configuration_version=SCORING_RULE_VERSION if config else None,
        scoring_configuration_fingerprint=configuration_fingerprint(config) if config else None)
