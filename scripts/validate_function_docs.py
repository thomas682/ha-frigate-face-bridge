#!/usr/bin/env python3
"""Validate an atomic, dependency-free function inventory against HEAD sources."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from build_function_docs import (
    build_catalog_data,
    dynamic_gui_specs,
    find_js_functions,
    git_head,
    line_at,
    source_tree_digest,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs/functions.yaml"
HANDBOOK = ROOT / "docs/handbuch.md"
ID_BASELINE = ROOT / "docs/function-id-baseline.json"
PYTHON_DIR = ROOT / "frigate-face-bridge/app"
JAVASCRIPT = PYTHON_DIR / "static/app.js"
HTML = PYTHON_DIR / "static/index.html"
CONFIG = ROOT / "frigate-face-bridge/config.yaml"
ID_PATTERN = re.compile(r"^ffb\.(python|javascript|route|gui|config|operation)\.[a-z0-9]+(?:[._-][a-z0-9]+)*$")
ROUTE_PATTERN = re.compile(r'@app\.(get|post|put|patch|delete)\("([^"]+)"\)')
UNIT_TYPES = ("python", "javascript", "route", "gui", "config", "operation")
REQUIRED_FIELDS = {
    "id", "unit_type", "unit_ref", "name", "technical_reference", "category",
    "description", "short_help", "audience", "visibility", "prerequisites",
    "permissions", "inputs", "outputs", "side_effects", "behavior", "security",
    "dependencies", "handbook_ref", "gui_refs", "tests", "status",
    "verified_version", "source_ref",
    "review_evidence", "source_fingerprint",
}
BEHAVIOR_FIELDS = {"loading", "success", "empty", "error", "cancel", "retry"}
FORBIDDEN_GROUP_FIELDS = {
    "python_symbols", "js_symbols", "api_refs", "config_refs", "script_refs",
    "source_refs", "event_refs",
}
UNIT_SPECIFIC_FIELDS = {
    "description", "short_help", "visibility", "prerequisites", "permissions",
    "inputs", "outputs", "side_effects", "security", "dependencies", "gui_refs",
}
CANONICAL_FIELDS = REQUIRED_FIELDS - {"tests"}
OPERATIONAL_FILES = {
    ".github/workflows/lint.yml",
    "deploy/docker-compose.yml",
    "frigate-face-bridge/Dockerfile",
    "frigate-face-bridge/run.sh",
}


def meaningful(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        return len(text) >= 3 and text not in {"N/A", "n/a", "-"}
    if isinstance(value, dict):
        return bool(value) and all(meaningful(key) and meaningful(item) for key, item in value.items())
    return value is not None


def python_units() -> dict[str, str]:
    units: dict[str, str] = {}

    def visit(body: list[ast.stmt], module: str, path: Path, parents: list[str]) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = ".".join([module, *parents, node.name])
                units[qualified] = f"{path.relative_to(ROOT)}:{node.lineno}"
                visit(node.body, module, path, [*parents, node.name])
            elif isinstance(node, ast.ClassDef):
                visit(node.body, module, path, [*parents, node.name])

    for path in sorted(PYTHON_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visit(tree.body, path.stem, path, [])
    for path in sorted((ROOT / "scripts").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visit(tree.body, f"scripts.{path.stem}", path, [])
    return units


def javascript_units() -> dict[str, str]:
    text = JAVASCRIPT.read_text(encoding="utf-8")
    return {
        name: f"{JAVASCRIPT.relative_to(ROOT)}:{line}"
        for name, line, _params, _body in find_js_functions(text)
    }


def route_units() -> dict[str, str]:
    path = PYTHON_DIR / "main.py"
    text = path.read_text(encoding="utf-8")
    return {
        f"{method.upper()} {route}": f"{path.relative_to(ROOT)}:{text.count(chr(10), 0, match.start()) + 1}"
        for match in ROUTE_PATTERN.finditer(text)
        for method, route in [match.groups()]
    }


class InteractiveParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.units: dict[str, str] = {}
        self.doc_ids: dict[str, str] = {}
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        doc_id = attrs.get("data-doc-id", "")
        relevant = tag in {"a", "button", "form", "input", "select", "textarea", "img"} or bool(attrs.get("id"))
        if not relevant:
            return
        if not doc_id:
            self.errors.append(f"GUI element {tag} at line {self.getpos()[0]} lacks data-doc-id")
            return
        if attrs.get("id"):
            ref = f"#{attrs['id']}"
        elif attrs.get("data-target-view"):
            ref = f"[data-target-view={attrs['data-target-view']}]"
        elif attrs.get("data-comm-stage"):
            ref = f"[data-comm-stage={attrs['data-comm-stage']}]"
        else:
            ref = doc_id
        if ref in self.units:
            self.errors.append(f"duplicate GUI reference {ref}")
        self.units[ref] = f"{HTML.relative_to(ROOT)}:{self.getpos()[0]}"
        self.doc_ids[ref] = doc_id


def gui_units() -> dict[str, str]:
    parser = InteractiveParser()
    parser.feed(HTML.read_text(encoding="utf-8"))
    js_text = JAVASCRIPT.read_text(encoding="utf-8")
    for spec in dynamic_gui_specs(js_text):
        if spec["marker"] in js_text:
            parser.units[spec["ref"]] = f"{JAVASCRIPT.relative_to(ROOT)}:{line_at(js_text, js_text.index(spec['marker']))}"
            parser.doc_ids[spec["ref"]] = spec["id"]
    return parser.units


def gui_bindings() -> tuple[dict[str, str], list[str]]:
    parser = InteractiveParser()
    parser.feed(HTML.read_text(encoding="utf-8"))
    js_text = JAVASCRIPT.read_text(encoding="utf-8")
    for spec in dynamic_gui_specs(js_text):
        if spec["marker"] in js_text:
            parser.doc_ids[spec["ref"]] = spec["id"]
    return parser.doc_ids, parser.errors


def accessibility_errors() -> list[str]:
    text = HTML.read_text(encoding="utf-8")
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for match in re.finditer(r"<(input|select|textarea|img)([^>]*data-doc-id=\"([^\"]+)\"[^>]*)>", line):
            tag, attrs, doc_id = match.groups()
            if tag in {"input", "select", "textarea"} and "<label" not in line and not re.search(r'aria-label(?:ledby)?="[^"]+"', attrs):
                errors.append(f"{doc_id} lacks an accessible label at line {line_number}")
            if tag == "img" and not re.search(r'alt="[^"]+"', attrs):
                errors.append(f"{doc_id} lacks non-empty alt text at line {line_number}")
    for match in re.finditer(r"<(button|a)([^>]*data-doc-id=\"([^\"]+)\"[^>]*)>(.*?)</\1>", text, re.DOTALL):
        _tag, attrs, doc_id, body = match.groups()
        visible_name = re.sub(r"<[^>]+>", " ", body).strip()
        if not visible_name and not re.search(r'aria-label(?:ledby)?="[^"]+"', attrs):
            errors.append(f"{doc_id} lacks an accessible name")
    return errors


def config_units() -> dict[str, str]:
    units: dict[str, str] = {}
    stack: list[tuple[int, str]] = []
    in_schema = False
    for line_number, raw_line in enumerate(CONFIG.read_text(encoding="utf-8").splitlines(), 1):
        if raw_line == "schema:":
            in_schema = True
            continue
        if not in_schema or not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        if indent == 0:
            break
        stripped = raw_line.strip().removeprefix("- ")
        match = re.match(r"([A-Za-z0-9_]+):(?:\s*(.*))?$", stripped)
        if not match:
            continue
        key, value = match.groups()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        field = ".".join([item[1] for item in stack] + [key])
        if value:
            units[field] = f"{CONFIG.relative_to(ROOT)}:{line_number}"
        else:
            stack.append((indent, key))
    return units


def expected_units() -> dict[str, dict[str, str]]:
    return {
        "python": python_units(),
        "javascript": javascript_units(),
        "route": route_units(),
        "gui": gui_units(),
        "config": config_units(),
        "operation": {path: path for path in OPERATIONAL_FILES},
    }


def load_catalog(errors: list[str]) -> dict[str, Any]:
    try:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Katalog ist kein gueltiges JSON-kompatibles YAML: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append("Katalogwurzel muss ein Objekt sein")
        return {}
    return data


def source_path(source_ref: str) -> Path:
    return ROOT / source_ref.split("::", 1)[0].rsplit(":", 1)[0]


def baseline_from_base_ref(ref: str) -> dict[str, str] | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:docs/function-id-baseline.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    entries = data.get("entries") if isinstance(data, dict) else None
    return entries if isinstance(entries, dict) else None


def compare_historical_ids(
    historical: dict[str, str], current: dict[str, Any], label: str, errors: list[str]
) -> None:
    for unit, historical_id in historical.items():
        if unit not in current:
            errors.append(f"{label} documentation unit disappeared without migration: {unit}")
        elif current[unit] != historical_id:
            errors.append(f"{label} documentation ID changed for {unit}: {historical_id} -> {current[unit]}")


def validate() -> tuple[list[str], Counter[str]]:
    errors: list[str] = []
    data = load_catalog(errors)
    if not data:
        return errors, Counter()
    for field in ("schema_version", "project", "audited_head", "audited_source_digest", "id_baseline", "audit_method", "review_evidence"):
        if not meaningful(data.get(field)):
            errors.append(f"Top-Level-Pflichtfeld fehlt oder ist leer: {field}")
    if data.get("audited_head") != git_head():
        errors.append(f"audited_head does not match repository HEAD: {data.get('audited_head')!r}")
    if data.get("audited_source_digest") != source_tree_digest():
        errors.append("audited_source_digest does not match the current inventory source tree")
    entries = data.get("functions")
    if not isinstance(entries, list) or not entries:
        errors.append("functions muss eine nicht leere Liste sein")
        return errors, Counter()

    expected = expected_units()
    canonical_data = build_catalog_data(data)
    canonical_entries = {(entry["unit_type"], entry["unit_ref"]): entry for entry in canonical_data["functions"]}
    seen_ids: set[str] = set()
    seen_units: Counter[tuple[str, str]] = Counter()
    counts: Counter[str] = Counter()
    handbook = HANDBOOK.read_text(encoding="utf-8") if HANDBOOK.exists() else ""
    bindings, binding_errors = gui_bindings()
    errors.extend(binding_errors)
    errors.extend(accessibility_errors())
    forbidden_phrases = (
        "zeigt oder protokolliert einen Lade-/Startzustand",
        "konkrete Leerwerte und Ausnahmen folgen dem Codepfad",
        "fuer dieses Symbol dokumentierte Rueckgabe",
        "behandelt oder propagiert Fehler exakt gemaess Implementierung",
        "wirkt nur auf dieses Konfigurationsfeld",
    )

    for index, entry in enumerate(entries):
        label = f"functions[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} muss ein Objekt sein")
            continue
        missing = REQUIRED_FIELDS - entry.keys()
        if missing:
            errors.append(f"{label} Pflichtfelder fehlen: {', '.join(sorted(missing))}")
        grouped = FORBIDDEN_GROUP_FIELDS & entry.keys()
        if grouped:
            errors.append(f"{label} enthaelt verbotene Gruppenfelder: {', '.join(sorted(grouped))}")
        for field in REQUIRED_FIELDS & entry.keys():
            if not meaningful(entry[field]):
                errors.append(f"{label}.{field} ist nicht substanziell; N/A braucht eine Begruendung")
        entry_text = json.dumps(entry, ensure_ascii=False)
        for phrase in forbidden_phrases:
            if phrase in entry_text:
                errors.append(f"{label} contains rejected generic wording: {phrase}")

        doc_id = entry.get("id", "")
        unit_type = entry.get("unit_type", "")
        unit_ref = entry.get("unit_ref", "")
        if not isinstance(doc_id, str) or not ID_PATTERN.fullmatch(doc_id):
            errors.append(f"{label}.id ist ungueltig: {doc_id!r}")
        if doc_id in seen_ids:
            errors.append(f"doppelte Dokumentations-ID: {doc_id}")
        seen_ids.add(doc_id)
        if unit_type not in UNIT_TYPES:
            errors.append(f"{doc_id}: ungueltiger unit_type {unit_type!r}")
            continue
        counts[unit_type] += 1
        seen_units[(unit_type, unit_ref)] += 1
        if entry.get("technical_reference") != unit_ref:
            errors.append(f"{doc_id}: technical_reference muss exakt dem einzelnen unit_ref entsprechen")
        canonical = canonical_entries.get((unit_type, unit_ref))
        if canonical:
            for field in CANONICAL_FIELDS:
                if entry.get(field) != canonical.get(field):
                    errors.append(f"{doc_id}: canonical field differs from source-derived value: {field}")
        if unit_type == "gui" and bindings.get(unit_ref) != doc_id:
            errors.append(f"{doc_id}: data-doc-id binding for {unit_ref} is missing or differs ({bindings.get(unit_ref)!r})")
        if entry.get("status") != "verified":
            errors.append(f"{doc_id}: aktive Einheit muss verified sein")
        behavior = entry.get("behavior")
        if not isinstance(behavior, dict) or set(behavior) != BEHAVIOR_FIELDS:
            errors.append(f"{doc_id}: behavior muss genau loading/success/empty/error/cancel/retry enthalten")
        source_ref = str(entry.get("source_ref", ""))
        if not source_path(source_ref).exists():
            errors.append(f"{doc_id}: Quellreferenz existiert nicht: {source_ref}")
        expected_source = expected[unit_type].get(unit_ref)
        if expected_source is not None and source_ref != expected_source:
            errors.append(f"{doc_id}: Quellreferenz ist nicht exakt: erwartet {expected_source}, erhalten {source_ref}")
        handbook_ref = str(entry.get("handbook_ref", ""))
        anchor = handbook_ref.removeprefix("docs/handbuch.md#")
        if not anchor or f'<a id="{anchor}"></a>' not in handbook:
            errors.append(f"{doc_id}: Handbuchanker fehlt")
        test_ref = entry.get("tests")
        if isinstance(test_ref, str) and not test_ref.startswith("N/A:"):
            if not source_path(test_ref).exists():
                errors.append(f"{doc_id}: Testreferenz existiert nicht: {test_ref}")
            elif "::" in test_ref:
                test_path, test_name = test_ref.split("::", 1)
                definitions = {
                    node.name
                    for node in ast.parse((ROOT / test_path).read_text(encoding="utf-8")).body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                if test_name not in definitions:
                    errors.append(f"{doc_id}: referenzierte Testfunktion existiert nicht: {test_ref}")

    for unit_type, discovered in expected.items():
        documented = {ref for (kind, ref), amount in seen_units.items() if kind == unit_type and amount > 0}
        missing = set(discovered) - documented
        stale = documented - set(discovered)
        duplicates = sorted(ref for (kind, ref), amount in seen_units.items() if kind == unit_type and amount != 1)
        if missing:
            errors.append(f"Undokumentierte {unit_type}-Einheiten: {', '.join(sorted(missing))}")
        if stale:
            errors.append(f"Veraltete {unit_type}-Einheiten: {', '.join(sorted(stale))}")
        if duplicates:
            errors.append(f"Nicht 1:1 dokumentierte {unit_type}-Einheiten: {', '.join(duplicates)}")
        if counts[unit_type] != len(discovered):
            errors.append(f"Falsche Anzahl {unit_type}: {counts[unit_type]} statt {len(discovered)}")

    exclusions = data.get("exclusions")
    if not isinstance(exclusions, list) or not exclusions:
        errors.append("Ausschluesse muessen als begruendete Liste dokumentiert sein")
    else:
        for index, exclusion in enumerate(exclusions):
            if not isinstance(exclusion, dict) or not all(meaningful(exclusion.get(field)) for field in ("scope", "reason", "evidence")):
                errors.append(f"exclusions[{index}] braucht scope, reason und evidence")
    try:
        baseline = json.loads(ID_BASELINE.read_text(encoding="utf-8"))
        baseline_entries = baseline.get("entries") if isinstance(baseline, dict) else None
    except (OSError, json.JSONDecodeError) as exc:
        baseline_entries = None
        errors.append(f"documentation ID baseline cannot be read: {exc}")
    current_ids = {f"{entry.get('unit_type')}:{entry.get('unit_ref')}": entry.get("id") for entry in entries if isinstance(entry, dict)}
    if not isinstance(baseline_entries, dict):
        errors.append("documentation ID baseline must contain an entries object")
    else:
        compare_historical_ids(baseline_entries, current_ids, "worktree baseline", errors)
        for unit in sorted(set(current_ids) - set(baseline_entries)):
            errors.append(f"documentation unit is missing from ID baseline: {unit}")

    base_ref = os.environ.get("FUNCTION_DOCS_BASE_REF", "").strip()
    if base_ref:
        base_entries = baseline_from_base_ref(base_ref)
        if base_entries is not None:
            compare_historical_ids(base_entries, current_ids, f"base ref {base_ref}", errors)

    sensitive_docs = CATALOG.read_text(encoding="utf-8") + "\n" + handbook
    for private_pattern in (
        r"fossflow\.loca(?:ldomain)?", r"homeassistant\.localdomain", r"192\.168\.2\.", r"/Users/", r"/var/folders/", r"/data/(?:options|faces)\.json",
        r"\b(?:Thomas|Birgit|Marie|Maja)\b", r"\b(?:wohnzimmer|garage)[-_a-z0-9]*\b", r"b3b46a83",
    ):
        if re.search(private_pattern, sensitive_docs, re.IGNORECASE):
            errors.append(f"private internal detail copied into published documentation: {private_pattern}")
    return errors, counts


def main() -> int:
    errors, counts = validate()
    if errors:
        print("Funktionsdokumentation ungueltig:")
        for error in errors:
            print(f"- {error}")
        return 1
    total = sum(counts.values())
    details = ", ".join(f"{kind}={counts[kind]}" for kind in UNIT_TYPES)
    print(f"Funktionsdokumentation gueltig: {total} atomare Eintraege ({details}); 1:1-Abdeckung ohne Gruppierung.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
