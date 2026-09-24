"""Vue SFC Block Slicer
Parses .vue Single File Components into structural blocks (<template>, <script>, <style>)
with 100% physical file line number preservation.
"""

from pathlib import Path
import re
from typing import Any
from ingestion.code.dto import SfcBlock, SfcParseResult

# Regular expression to extract top-level SFC tags with attributes and inner content
TAG_REGEX = re.compile(
    r"<(?P<tag>template|script|style)(?P<attrs>[^>]*)>(?P<content>.*?)</(?P=tag)>",
    re.DOTALL | re.IGNORECASE,
)

# Regex to parse individual attributes from tag opening
ATTR_REGEX = re.compile(r'(?P<key>[\w\-:]+)(?:=["\'](?P<val>[^"\']*)["\'])?')

# Regex for template component usage (PascalCase or kebab-case with hyphens or prefix)
COMPONENT_TAG_REGEX = re.compile(r"<([A-Z][a-zA-Z0-9]+|el-[a-z0-9\-]+)")

# Regex for event bindings in template: @event="handler" or v-on:event="handler"
EVENT_BINDING_REGEX = re.compile(r'(?:@|v-on:)([\w\-:]+)=["\']([^"\']+)["\']')

# Regex for property bindings: :prop="val" or v-model="val" or v-bind:prop="val"
PROP_BINDING_REGEX = re.compile(r'(?::|v-bind:|v-model(?:[:\w\-]+)?)([\w\-:]*)=["\']([^"\']+)["\']')


class SfcBlockSlicer:
    """Slices Vue Single File Components into discrete structural blocks with physical line alignment."""

    def __init__(self, preserve_physical_lines: bool = True):
        self.preserve_physical_lines = preserve_physical_lines

    def slice_file(self, file_path: str | Path, content: str | None = None) -> SfcParseResult:
        path_obj = Path(file_path)
        if content is None:
            content = path_obj.read_text(encoding="utf-8", errors="replace")

        result = SfcParseResult(file_path=str(path_obj).replace("\\", "/"))

        # Find all top-level blocks
        for match in TAG_REGEX.finditer(content):
            tag = match.group("tag").lower()
            attrs_str = match.group("attrs") or ""
            inner_content = match.group("content")

            # Calculate exact physical tag start and end lines (1-based)
            tag_start_line = content[:match.start()].count("\n") + 1
            tag_end_line = content[:match.end()].count("\n") + 1

            start_pos = match.start("content")
            newlines_before = content[:start_pos].count("\n")

            # Parse attributes
            attrs = {}
            for a_match in ATTR_REGEX.finditer(attrs_str):
                k = a_match.group("key")
                v = a_match.group("val") or ""
                attrs[k] = v

            lang = attrs.get("lang", "javascript" if tag == "script" else "html")
            is_setup = "setup" in attrs
            is_scoped = "scoped" in attrs

            # Padded content: exactly replaces all characters before start_pos with equivalent newlines
            padded_content = ("\n" * newlines_before) + inner_content if self.preserve_physical_lines else inner_content

            block = SfcBlock(
                block_type=f"{tag}_setup" if (tag == "script" and is_setup) else tag,
                content=padded_content,
                start_line=tag_start_line,
                end_line=tag_end_line,
                lang=lang,
                is_setup=is_setup,
                is_scoped=is_scoped,
                attributes=attrs,
            )

            if tag == "script":
                result.script_blocks.append(block)
            elif tag == "template":
                result.template_block = block
                self._extract_template_elements(inner_content, result)
            elif tag == "style":
                result.style_blocks.append(block)

        return result

    def _extract_template_elements(self, template_content: str, result: SfcParseResult):
        """Extracts component references, event bindings, and prop bindings from template."""
        # 1. Component tags (e.g. <ElButton>, <CallDetails>, <el-table>)
        components = set()
        for c_match in COMPONENT_TAG_REGEX.finditer(template_content):
            c_name = c_match.group(1)
            # Filter standard HTML tags
            if c_name.lower() not in ["div", "span", "p", "a", "button", "table", "tr", "td", "th", "input", "img", "ul", "li", "h1", "h2", "h3", "h4", "h5", "h6"]:
                components.add(c_name)
        result.component_references = sorted(list(components))

        # 2. Event bindings (e.g. @click="loadLeads")
        events = set()
        for e_match in EVENT_BINDING_REGEX.finditer(template_content):
            evt_name = e_match.group(1)
            evt_handler = e_match.group(2).strip()
            events.add(f"{evt_name}->{evt_handler}")
        result.event_bindings = sorted(list(events))

        # 3. Prop bindings (e.g. :leads="leadList", v-model="form.name")
        props = set()
        for p_match in PROP_BINDING_REGEX.finditer(template_content):
            prop_name = p_match.group(1) or "model"
            prop_val = p_match.group(2).strip()
            props.add(f"{prop_name}->{prop_val}")
        result.property_bindings = sorted(list(props))
