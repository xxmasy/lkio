"""Backend Spring Boot Controller Extractor (E-02)
Extracts HTTP endpoints, route mappings, and service calls from Java Spring Boot @RestController classes.

Enforces:
- LOCK-TRACE-01: Objective endpoint contract derived from annotations (@RequestMapping, @GetMapping, @PostMapping).
- LOCK-TRACE-02: Path prefix and method combination normalization.
- LOCK-TRACE-03: Downstream Service invocation capture.
"""

import logging
import re
from typing import Any
from tree_sitter import Node

from core.extraction.normalizer import EMPTY_SIGNATURE_DISCRIMINATOR
from core.graph.api.models import ApiEndpoint, HttpMethod, normalize_api_path
from core.parsing.parser_factory import ParserFactory

logger = logging.getLogger(__name__)

MAPPING_ANNOTATIONS = {
    "GetMapping": HttpMethod.GET,
    "PostMapping": HttpMethod.POST,
    "PutMapping": HttpMethod.PUT,
    "DeleteMapping": HttpMethod.DELETE,
    "PatchMapping": HttpMethod.PATCH,
    "RequestMapping": HttpMethod.ANY,
}


class BackendControllerExtractor:
    """Extracts REST API endpoints from Java Spring Boot controllers using Tree-sitter."""

    def __init__(self, parser_factory: ParserFactory | None = None):
        self.parser_factory = parser_factory or ParserFactory()

    def extract_from_code(
        self,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
    ) -> list[ApiEndpoint]:
        """Extracts backend HTTP endpoints and downstream service invocations from a Java source file."""
        parser = self.parser_factory.get("java")
        tree = parser.parse(code_bytes)
        root = tree.root_node

        endpoints: list[ApiEndpoint] = []
        self._traverse_java_classes(root, code_bytes, project_key, file_rel_path, endpoints)
        return endpoints

    def _find_modifiers(self, node: Node) -> Node | None:
        for c in node.children:
            if c.type == "modifiers":
                return c
        return None

    def _traverse_java_classes(
        self,
        node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        endpoints: list[ApiEndpoint],
    ):
        for child in node.children:
            if child.type == "class_declaration":
                self._inspect_controller_class(child, code_bytes, project_key, file_rel_path, endpoints)
            elif child.child_count > 0:
                self._traverse_java_classes(child, code_bytes, project_key, file_rel_path, endpoints)

    def _inspect_controller_class(
        self,
        class_node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        endpoints: list[ApiEndpoint],
    ):
        name_node = class_node.child_by_field_name("name")
        if not name_node:
            return
        class_name = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")

        # Inspect class-level modifiers / annotations for base path
        class_base_path = ""
        modifiers = self._find_modifiers(class_node)
        if modifiers:
            for mod in modifiers.children:
                if mod.type in {"marker_annotation", "annotation"}:
                    ann_text = code_bytes[mod.start_byte : mod.end_byte].decode("utf-8", errors="replace")
                    if "RequestMapping" in ann_text:
                        match = re.search(r'["\']([^"\']+)["\']', ann_text)
                        if match:
                            class_base_path = match.group(1)

        # Inspect class body for method mappings
        body_node = class_node.child_by_field_name("body")
        if not body_node:
            return

        for child in body_node.children:
            if child.type == "method_declaration":
                self._inspect_controller_method(
                    child, code_bytes, project_key, file_rel_path, class_name, class_base_path, endpoints
                )

    def _inspect_controller_method(
        self,
        method_node: Node,
        code_bytes: bytes,
        project_key: str,
        file_rel_path: str,
        class_name: str,
        class_base_path: str,
        endpoints: list[ApiEndpoint],
    ):
        name_node = method_node.child_by_field_name("name")
        if not name_node:
            return
        method_name = code_bytes[name_node.start_byte : name_node.end_byte].decode("utf-8", errors="replace")
        method_symbol_key = (
            f"SYMBOL:{project_key}:{file_rel_path}:METHOD:{class_name}.{method_name}:{EMPTY_SIGNATURE_DISCRIMINATOR}"
        )

        http_method: HttpMethod | None = None
        method_path = ""

        modifiers = self._find_modifiers(method_node)
        if modifiers:
            for mod in modifiers.children:
                if mod.type in {"marker_annotation", "annotation"}:
                    ann_text = code_bytes[mod.start_byte : mod.end_byte].decode("utf-8", errors="replace")
                    for ann_name, m_type in MAPPING_ANNOTATIONS.items():
                        if ann_name in ann_text:
                            http_method = m_type
                            # Check path argument in annotation
                            match = re.search(r'["\']([^"\']+)["\']', ann_text)
                            if match:
                                method_path = match.group(1)
                            break

        if http_method:
            # Combine base path and method path
            full_raw_path = f"{class_base_path}/{method_path}".replace("//", "/")
            if not full_raw_path.startswith("/"):
                full_raw_path = "/" + full_raw_path

            norm_path = normalize_api_path(full_raw_path)

            # Discover downstream service calls within method body
            service_calls = self._discover_service_calls(method_node, code_bytes)

            endpoint = ApiEndpoint(
                project_key=project_key,
                http_method=http_method,
                raw_path=full_raw_path,
                normalized_path=norm_path,
                source_file_rel_path=file_rel_path,
                line=method_node.start_point.row + 1,
                enclosing_symbol_key=method_symbol_key,
                is_backend_handler=True,
                downstream_service_calls=tuple(service_calls),
                metadata={"class_name": class_name, "method_name": method_name},
            )
            endpoints.append(endpoint)

    def _discover_service_calls(self, method_node: Node, code_bytes: bytes) -> list[str]:
        """Scans method body for service method invocations (e.g. callConfigService.getSdkConfig())."""
        service_invocations: list[str] = []
        body = method_node.child_by_field_name("body")
        if not body:
            return service_invocations

        def _walk(n: Node):
            if n.type == "method_invocation":
                name_n = n.child_by_field_name("name")
                obj_n = n.child_by_field_name("object")
                if name_n and obj_n:
                    obj_text = code_bytes[obj_n.start_byte : obj_n.end_byte].decode("utf-8", errors="replace")
                    m_text = code_bytes[name_n.start_byte : name_n.end_byte].decode("utf-8", errors="replace")
                    if "service" in obj_text.lower():
                        service_invocations.append(f"{obj_text}.{m_text}")
            for c in n.children:
                _walk(c)

        _walk(body)
        return service_invocations
