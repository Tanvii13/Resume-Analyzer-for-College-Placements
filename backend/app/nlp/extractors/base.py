"""
Abstract Base Extractor for NLP entity extraction modules.

Module C, D, and E base class.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.nlp.preprocessing import SegmentedDocument
from app.nlp.sections import SectionMap


class BaseExtractor(ABC):
    """
    Abstract base class for all domain-specific resume extractors.

    Ensures consistent interface across Contact, Education, Experience,
    Projects, Skills, and Certifications extractors.
    """

    @abstractmethod
    def extract(
        self,
        sections: SectionMap,
        document: Optional[SegmentedDocument] = None,
    ) -> Any:
        """
        Extract structured entities from classified sections and/or segmented document.

        Args:
            sections: Classified SectionMap from Module B.
            document: Optional SegmentedDocument from Module A for source-order lookup.

        Returns:
            Structured domain model representing extracted entities.
        """
        pass
