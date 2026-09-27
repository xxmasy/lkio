"""DTO & Schema Contract Lineage Matcher (Stage 2 Section 4.6).

Discovers and maps fields between Frontend TypeScript interfaces and Backend DTOs/POJOs.
"""

import re
from typing import Dict, List, Tuple
from core.multirepo.models import DtoFieldLineage


class DtoContractMatcher:
    """Extracts and correlates data transfer objects across languages."""

    @classmethod
    def extract_ts_interface_fields(cls, code: str) -> Dict[str, str]:
        """Extracts field names and types from TypeScript interface definition."""
        fields = {}
        # match: fieldName: string; or fieldName?: number;
        matches = re.finditer(r"([A-Za-z0-9_]+)\??\s*:\s*([A-Za-z0-9_<>[\]]+)\s*;", code)
        for m in matches:
            field_name = m.group(1)
            field_type = m.group(2)
            fields[field_name] = field_type
        return fields

    @classmethod
    def extract_java_dto_fields(cls, code: str) -> Dict[str, str]:
        """Extracts field names and types from Java class/DTO fields."""
        fields = {}
        # match: private String fieldName; or private BigDecimal fieldName;
        matches = re.finditer(r"(?:private|protected|public)\s+([A-Za-z0-9_<>[\]]+)\s+([A-Za-z0-9_]+)\s*;", code)
        for m in matches:
            field_type = m.group(1)
            field_name = m.group(2)
            fields[field_name] = field_type
        return fields

    @classmethod
    def match_dto_lineage(
        cls,
        frontend_uri: str,
        frontend_code: str,
        backend_uri: str,
        backend_code: str,
    ) -> List[DtoFieldLineage]:
        """Correlates fields between TS interface and Java DTO."""
        ts_fields = cls.extract_ts_interface_fields(frontend_code)
        java_fields = cls.extract_java_dto_fields(backend_code)

        lineages = []
        for f_name, f_type in ts_fields.items():
            if f_name in java_fields:
                b_type = java_fields[f_name]
                lineages.append(
                    DtoFieldLineage(
                        frontend_field=f_name,
                        frontend_type=f_type,
                        backend_field=f_name,
                        backend_type=b_type,
                        frontend_entity_key=frontend_uri,
                        backend_entity_key=backend_uri,
                        confidence=1.0,
                    )
                )

        return lineages
