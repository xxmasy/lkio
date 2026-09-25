"""LKIO Vue Template Structural Parser (B-05 Approved Baseline)
Extracts component references, event bindings, and property bindings from Vue SFC templates.

Enforces:
- LOCK-VUE-02: Template evidence taxonomy (extraction_method = "static_template")
- LOCK-VUE-03: Structured bindings preservation (directive, argument, expression, modifiers)
               without premature serialization or function call assumptions.
- LOCK-VUE-03b: Tag name preservation (raw tag_name + normalized_name in PascalCase).
- LOCK-VUE-06: Preflight parser strategy; unsupported preprocessors (e.g. pug) gracefully degraded.
"""

from html.parser import HTMLParser
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Standard HTML5 elements to exclude from component references
STANDARD_HTML_TAGS = {
    "a", "abbr", "address", "area", "article", "aside", "audio", "b", "base",
    "bdi", "bdo", "blockquote", "body", "br", "button", "canvas", "caption",
    "cite", "code", "col", "colgroup", "data", "datalist", "dd", "del",
    "details", "dfn", "dialog", "div", "dl", "dt", "em", "embed", "fieldset",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
    "h6", "head", "header", "hgroup", "hr", "html", "i", "iframe", "img",
    "input", "ins", "kbd", "label", "legend", "li", "link", "main", "map",
    "mark", "menu", "meta", "meter", "nav", "noscript", "object", "ol",
    "optgroup", "option", "output", "p", "picture", "pre", "progress", "q",
    "rp", "rt", "ruby", "s", "samp", "script", "search", "section", "select",
    "slot", "small", "source", "span", "strong", "style", "sub", "summary",
    "sup", "table", "tbody", "td", "template", "textarea", "tfoot", "th",
    "thead", "time", "title", "tr", "track", "u", "ul", "var", "video",
    "wbr", "svg", "path", "g", "circle", "rect", "line", "polygon", "polyline",
    "text", "use", "defs", "clippath", "mask", "pattern"
}

_TAG_NAME_RE = re.compile(r"^<\s*([a-zA-Z0-9_\-]+)")


def to_pascal_case(name: str) -> str:
    """Converts kebab-case or snake_case tag name to PascalCase (e.g. 'el-button' -> 'ElButton')."""
    if "-" in name or "_" in name:
        parts = re.split(r"[-_]", name)
        return "".join(p.capitalize() for p in parts if p)
    # If already capitalized or camelCase, ensure first letter is capitalized
    return name[:1].upper() + name[1:] if name else name


class VueTemplateParser(HTMLParser):
    """Parses Vue template HTML content into structural facts."""

    def __init__(self, base_line: int = 1):
        super().__init__()
        self.base_line = base_line
        self.component_references: list[dict[str, Any]] = []
        self.event_bindings: list[dict[str, Any]] = []
        self.property_bindings: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        line, col = self.getpos()
        actual_line = self.base_line + line - 1

        # Preserve raw tag case using get_starttag_text() (LOCK-VUE-03b)
        raw_text = self.get_starttag_text() or ""
        match = _TAG_NAME_RE.match(raw_text)
        raw_tag = match.group(1) if match else tag

        # 1. Component Reference Extraction
        if raw_tag.lower() not in STANDARD_HTML_TAGS:
            norm_name = to_pascal_case(raw_tag)
            self.component_references.append({
                "tag_name": raw_tag,
                "normalized_name": norm_name,
                "start_line": actual_line,
                "start_column": col,
                "evidence": {
                    "method": "static_template",
                    "node_type": "element",
                },
            })

        # 2. Directives and Bindings Extraction (LOCK-VUE-03)
        for attr_key, attr_val in attrs:
            val_str = attr_val if attr_val is not None else ""

            if attr_key.startswith("@") or attr_key.startswith("v-on:"):
                raw_evt = attr_key[1:] if attr_key.startswith("@") else attr_key[5:]
                evt_parts = raw_evt.split(".")
                evt_name = evt_parts[0]
                modifiers = evt_parts[1:]
                self.event_bindings.append({
                    "directive": "on",
                    "event": evt_name,
                    "expression": val_str,
                    "modifiers": modifiers,
                    "start_line": actual_line,
                    "start_column": col,
                })

            elif attr_key.startswith("v-model"):
                raw_model = attr_key[7:]  # after 'v-model'
                arg = None
                modifiers: list[str] = []
                if raw_model.startswith(":"):
                    rest = raw_model[1:]
                    parts = rest.split(".")
                    arg = parts[0]
                    modifiers = parts[1:]
                elif raw_model.startswith("."):
                    modifiers = raw_model[1:].split(".")

                self.property_bindings.append({
                    "directive": "model",
                    "argument": arg,
                    "expression": val_str,
                    "modifiers": modifiers,
                    "start_line": actual_line,
                    "start_column": col,
                })

            elif attr_key.startswith(":") or attr_key.startswith("v-bind:"):
                raw_prop = attr_key[1:] if attr_key.startswith(":") else attr_key[7:]
                prop_parts = raw_prop.split(".")
                prop_name = prop_parts[0]
                modifiers = prop_parts[1:]
                self.property_bindings.append({
                    "directive": "bind",
                    "argument": prop_name,
                    "expression": val_str,
                    "modifiers": modifiers,
                    "start_line": actual_line,
                    "start_column": col,
                })


def parse_vue_template(template_content: str, base_line: int = 1, lang: str = "html") -> dict[str, Any]:
    """Parses template content into structural facts dictionary.

    Handles language preprocessors (e.g. pug) gracefully by returning warning without crashing.
    """
    clean_lang = (lang or "html").lower()
    if clean_lang in ["pug", "jade"]:
        logger.warning("Vue template lang='%s' is not supported in MVP2-B static extraction.", clean_lang)
        return {
            "unsupported_language": clean_lang,
            "component_references": [],
            "event_bindings": [],
            "property_bindings": [],
        }

    parser = VueTemplateParser(base_line=base_line)
    try:
        parser.feed(template_content)
    except Exception as exc:
        logger.warning("Error parsing Vue template content at line %d: %s", base_line, exc)

    return {
        "component_references": parser.component_references,
        "event_bindings": parser.event_bindings,
        "property_bindings": parser.property_bindings,
    }
