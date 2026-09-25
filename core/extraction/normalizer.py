"""LKIO Code Symbol Normalization and Deterministic Key Generation (Lock v0.3)
Enforces:
- Language-specific canonical signature extraction (TS/JS vs Java).
- Distinguishes arity, types, optionality (?), rest (...) without arbitrary flattening.
- Lock 3: Symbol Keys do not depend on physical line numbers (line-shift immune).
- 0 Key truncation (supports full logical keys in TEXT storage).
"""

import hashlib
import re
from core.parsing.models import NATIVE_SYMBOL_TYPES

# Precomputed empty signature discriminator: SHA-256("")[:16]
EMPTY_SIGNATURE_DISCRIMINATOR = "e3b0c44298fc1c14"

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_SPACES_RE = re.compile(r"\s*([,:\(\)\{\}\[\]=>;\?\&\|])\s*")


def _split_params(params_body: str) -> list[str]:
    """Splits a comma-separated parameter string respecting nested (), <>, {}, []."""
    params = []
    current = []
    depth_paren = 0
    depth_angle = 0
    depth_curly = 0
    depth_bracket = 0

    for ch in params_body:
        if ch == "(":
            depth_paren += 1
            current.append(ch)
        elif ch == ")":
            depth_paren = max(0, depth_paren - 1)
            current.append(ch)
        elif ch == "<":
            depth_angle += 1
            current.append(ch)
        elif ch == ">":
            depth_angle = max(0, depth_angle - 1)
            current.append(ch)
        elif ch == "{":
            depth_curly += 1
            current.append(ch)
        elif ch == "}":
            depth_curly = max(0, depth_curly - 1)
            current.append(ch)
        elif ch == "[":
            depth_bracket += 1
            current.append(ch)
        elif ch == "]":
            depth_bracket = max(0, depth_bracket - 1)
            current.append(ch)
        elif ch == "," and depth_paren == 0 and depth_angle == 0 and depth_curly == 0 and depth_bracket == 0:
            params.append("".join(current).strip())
            current = []
        else:
            current.append(ch)

    if current:
        token = "".join(current).strip()
        if token:
            params.append(token)
    return params


def canonicalize_ts_signature(params_text: str | None) -> str:
    """Canonicalizes TypeScript / JavaScript parameter signatures.

    Rules:
    - Retains arity and parameter types.
    - Retains optional status (?) and rest status (...).
    - Example: '(id: string, count: number)' -> '(string,number)'
    - Example: '(id?: string)' -> '(string?)'
    - Example: '(...ids: string[])' -> '(...string[])'
    - Example: '()' or None -> '()'
    """
    if not params_text:
        return "()"

    sig = params_text.strip()
    if sig.startswith("(") and sig.endswith(")"):
        sig = sig[1:-1].strip()

    if not sig:
        return "()"

    param_tokens = _split_params(sig)
    canonical_params = []

    for p in param_tokens:
        p_clean = _WHITESPACE_RE.sub(" ", p).strip()
        # Drop default value assignments: e.g. 'count: number = 10' -> 'count: number'
        if "=" in p_clean and not (">=" in p_clean or "<=" in p_clean or "=>" in p_clean):
            # Split on the default '='
            parts = p_clean.split("=", 1)
            p_clean = parts[0].strip()

        # Check for rest param prefix
        is_rest = p_clean.startswith("...")
        if is_rest:
            p_clean = p_clean[3:].strip()

        # Check for type annotation: 'name: type' or 'name?: type'
        if ":" in p_clean:
            name_part, type_part = p_clean.split(":", 1)
            name_clean = name_part.strip()
            type_clean = _PUNCT_SPACES_RE.sub(r"\1", _WHITESPACE_RE.sub(" ", type_part).strip())

            is_optional = name_clean.endswith("?")
            if is_optional:
                type_clean = f"{type_clean}?"
            if is_rest:
                type_clean = f"...{type_clean}"

            canonical_params.append(type_clean)
        else:
            # Untyped JS or plain identifier
            is_optional = p_clean.endswith("?")
            base_type = "any"
            if is_optional:
                base_type = f"{base_type}?"
            if is_rest:
                base_type = f"...{base_type}"
            canonical_params.append(base_type)

    return f"({','.join(canonical_params)})"


def canonicalize_java_signature(params_text: str | None) -> str:
    """Canonicalizes Java parameter signatures to differentiate overloaded methods.

    Rules:
    - Retains parameter type sequence and arity.
    - Strips annotations and parameter variable names.
    - Retains varargs (...).
    - Example: '(String query, Integer page)' -> '(String,Integer)'
    - Example: '(Long id)' -> '(Long)'
    - Example: '(String... args)' -> '(String...)'
    - Example: '()' or None -> '()'
    """
    if not params_text:
        return "()"

    sig = params_text.strip()
    if sig.startswith("(") and sig.endswith(")"):
        sig = sig[1:-1].strip()

    if not sig:
        return "()"

    param_tokens = _split_params(sig)
    canonical_params = []

    for p in param_tokens:
        # Strip annotations like @PathVariable("id") or @NotNull
        p_clean = re.sub(r"@[A-Za-z0-9_]+(?:\([^)]*\))?", "", p)
        # Strip final modifier
        p_clean = re.sub(r"\bfinal\b", "", p_clean)
        p_clean = _WHITESPACE_RE.sub(" ", p_clean).strip()

        # In Java: Type paramName or Type... paramName
        words = p_clean.split(" ")
        if len(words) >= 2:
            # Type is everything except the last token (which is the parameter name)
            type_str = "".join(words[:-1])
        else:
            type_str = p_clean

        type_str = _PUNCT_SPACES_RE.sub(r"\1", type_str)
        canonical_params.append(type_str)

    return f"({','.join(canonical_params)})"


def compute_signature_discriminator(canonical_sig: str | None) -> str:
    """Computes a deterministic 16-hex-character discriminator from a canonical signature.

    Returns:
        16-character hex string representing SHA256(canonical_sig)[:16].
        Returns EMPTY_SIGNATURE_DISCRIMINATOR for empty or None signatures.
    """
    if not canonical_sig:
        return EMPTY_SIGNATURE_DISCRIMINATOR
    cleaned = canonical_sig.strip()
    if not cleaned or cleaned == "()":
        # Note: "()" represents zero-argument callable, not empty signature
        pass
    if not cleaned:
        return EMPTY_SIGNATURE_DISCRIMINATOR
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]


def normalize_rel_path(rel_path: str) -> str:
    """Normalizes relative file path to standard forward slashes without leading/trailing slashes."""
    p = rel_path.replace("\\", "/").strip()
    while p.startswith("/"):
        p = p[1:]
    return p


def build_symbol_key(
    project_key: str,
    file_rel_path: str,
    base_symbol_type: str,
    qualified_name: str,
    signature_discriminator: str | None = None,
    canonical_signature: str | None = None,
) -> str:
    """Generates the canonical deterministic Symbol Key.

    Format:
        SYMBOL:<project_key>:<file_rel_path>:<base_symbol_type>:<qualified_name>:<signature_discriminator>

    Guarantees:
        1. 0 dependency on physical line numbers (immune to line insertions/deletions).
        2. Differentiates overloaded methods/functions in Java / TS via signature_discriminator.
        3. base_symbol_type is strictly constrained to native controlled enum.
        4. 0 truncation: output is full logical key.
    """
    if base_symbol_type not in NATIVE_SYMBOL_TYPES:
        raise ValueError(
            f"Invalid base_symbol_type '{base_symbol_type}' for symbol key. "
            f"Must be one of: {sorted(list(NATIVE_SYMBOL_TYPES))}"
        )

    norm_path = normalize_rel_path(file_rel_path)
    clean_qname = qualified_name.strip()

    if signature_discriminator is None:
        discriminator = compute_signature_discriminator(canonical_signature)
    else:
        discriminator = signature_discriminator.strip()

    return f"SYMBOL:{project_key.strip()}:{norm_path}:{base_symbol_type}:{clean_qname}:{discriminator}"
