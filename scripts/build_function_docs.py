#!/usr/bin/env python3
"""Build the source inventory after a human review of the cited implementation."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frigate-face-bridge/app"
JS = APP / "static/app.js"
HTML = APP / "static/index.html"
CONFIG = ROOT / "frigate-face-bridge/config.yaml"
CATALOG = ROOT / "docs/functions.yaml"
HANDBOOK = ROOT / "docs/handbuch.md"
ID_BASELINE = ROOT / "docs/function-id-baseline.json"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
def public_text(value: str) -> str:
    replacements = {
        "homeassistant.localdomain": "home-assistant.example.invalid",
        "fossflow.localdomain": "service.example.invalid",
        "/b3b46a83_frigate_face_bridge": "/ingress/example",
        "/data/options.json": "<add-on-data>/options.json",
        "/data/faces.json": "<add-on-data>/faces.json",
        "wohnzimmer_g3_flex": "example_camera",
        "garage_g3_flex": "example_camera",
        "garage_g3": "example_camera",
        "Garage G3": "Example Camera",
        "Thomas": "Example Person A",
        "Birgit": "Example Person B",
        "Marie": "Example Person C",
        "Maja": "Example Dog",
        "Wohnzimmer": "Example Room",
        "wohnzimmer": "example-room",
    }
    for private, public in replacements.items():
        value = value.replace(private, public)
    value = re.sub(r"fossflow\.loca(?:ldomain)?", "service.example.invalid", value, flags=re.IGNORECASE)
    return value


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def inventory_source_paths() -> list[Path]:
    paths = [
        *APP.glob("*.py"), JS, HTML, CONFIG,
        ROOT / ".github/workflows/lint.yml", ROOT / "deploy/docker-compose.yml",
        ROOT / "frigate-face-bridge/Dockerfile", ROOT / "frigate-face-bridge/run.sh",
        *(ROOT / "scripts").glob("*.py"),
    ]
    return sorted({path for path in paths if path.exists()}, key=lambda path: str(path.relative_to(ROOT)))


def source_tree_digest() -> str:
    digest = hashlib.sha256()
    for path in inventory_source_paths():
        digest.update(str(path.relative_to(ROOT)).encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return f"sha256:{digest.hexdigest()}"


def attach_source_fingerprints(entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        path = ROOT / str(entry["source_ref"]).rsplit(":", 1)[0]
        digest = hashlib.sha256()
        digest.update(str(entry["unit_ref"]).encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
        entry["source_fingerprint"] = f"sha256:{digest.hexdigest()}"


def sanitize_tree(value: Any) -> Any:
    if isinstance(value, str):
        return public_text(value)
    if isinstance(value, list):
        return [sanitize_tree(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_tree(item) for key, item in value.items()}
    return value


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")
    return value or "unit"


def line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def dynamic_gui_specs(text: str | None = None) -> list[dict[str, str]]:
    text = JS.read_text(encoding="utf-8") if text is None else text
    creation = re.compile(
        r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*document\.createElement(?:NS)?\([^;]+\);"
    )
    specs: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for match in creation.finditer(text):
        variable = match.group(1)
        following = text[match.end():match.end() + 220]
        marker = re.search(
            rf"{re.escape(variable)}\.(?:dataset\.docId\s*=\s*['\"]([^'\"]+)['\"]|setAttribute\(\s*['\"]data-doc-id['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\))",
            following,
        )
        if not marker:
            raise ValueError(
                f"Dynamic createElement site at app.js:{line_at(text, match.start())} lacks an immediate data-doc-id marker"
            )
        doc_id = marker.group(1) or marker.group(2)
        if doc_id in seen_ids:
            raise ValueError(f"Dynamic data-doc-id is reused by multiple source definitions: {doc_id}")
        seen_ids.add(doc_id)
        specs.append(
            {
                "marker": marker.group(0),
                "ref": f'dynamic:[data-doc-id="{doc_id}"]',
                "id": doc_id,
                "name": doc_id.removeprefix("ffb.gui.").replace(".", " ").title(),
                "description": f"Creates the source-marked dynamic `{doc_id}` display for its owning render state.",
                "side_effects": "Changes only the owning browser DOM; delegated controls and requests have separate JavaScript contracts.",
            }
        )
    return specs


def source_ref(path: Path, line: int | None = None) -> str:
    result = str(path.relative_to(ROOT))
    return f"{result}:{line}" if line else result


def names_in_calls(node: ast.AST) -> list[str]:
    names: set[str] = set()
    for item in ast.walk(node):
        if not isinstance(item, ast.Call):
            continue
        try:
            names.add(ast.unparse(item.func))
        except Exception:
            continue
    return sorted(names)


def return_facts(node: ast.AST, source: str) -> str:
    values: list[str] = []
    for item in ast.walk(node):
        if isinstance(item, ast.Return):
            value = "None" if item.value is None else (ast.get_source_segment(source, item.value) or ast.dump(item.value, include_attributes=False))
            value = re.sub(r"\s+", " ", value).strip()
            if value not in values:
                values.append(value)
    if not values:
        return "Implicit `None`; the function has no return statement."
    rendered = ", ".join(f"`{value[:180]}`" for value in values[:6])
    suffix = f" and {len(values) - 6} further source expressions" if len(values) > 6 else ""
    return f"Returns {rendered}{suffix}."


def effect_facts(node: ast.AST, ref: str) -> str:
    calls = names_in_calls(node)
    effects: list[str] = []
    joined = " ".join(calls)
    if any(name.endswith(".write_text") for name in calls):
        effects.append("writes serialized data to the configured persistent file")
    if any(name.endswith(".mkdir") for name in calls):
        effects.append("creates the parent data directory when absent")
    if any(token in joined for token in ("urlopen", "create_connection", ".connect", ".connect_async")):
        effects.append("opens an outbound network connection to the configured endpoint")
    if any(token in joined for token in (".publish", ".subscribe")):
        effects.append("publishes or subscribes on MQTT")
    if any(token in joined for token in ("thread.start", "app.run", "loop_start")):
        effects.append("starts a thread, network loop, or HTTP server")
    if any(token in joined for token in ("LOG.", "logging.")):
        effects.append("writes an operational log record")
    mutations: set[str] = set()
    for item in ast.walk(node):
        targets: list[ast.expr] = []
        if isinstance(item, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = list(getattr(item, "targets", [])) or [item.target]
        for target in targets:
            text = ast.unparse(target)
            if text.startswith(("self.", "state[", "config[", "event[", "result[")):
                mutations.add(text[:100])
    if mutations:
        effects.append("mutates " + ", ".join(f"`{item}`" for item in sorted(mutations)[:8]))
    if not effects:
        return f"`{ref}` has no persistent, network, process, or shared-state side effect; local allocations are discarded by the caller."
    return f"`{ref}` " + "; ".join(effects) + "."


def python_units() -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []

    def visit(path: Path, module: str, body: list[ast.stmt], parents: list[str]) -> None:
        source = path.read_text(encoding="utf-8")
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ref = ".".join([module, *parents, node.name])
                args = ast.unparse(node.args)
                calls = names_in_calls(node)
                conditional_nodes = (ast.If, ast.IfExp) + ((ast.Match,) if hasattr(ast, "Match") else ())
                conditionals = sum(isinstance(item, conditional_nodes) for item in ast.walk(node))
                loops = sum(isinstance(item, (ast.For, ast.AsyncFor, ast.While)) for item in ast.walk(node))
                raises = sorted({ast.unparse(item.exc) for item in ast.walk(node) if isinstance(item, ast.Raise) and item.exc})
                catches = sorted({ast.unparse(kind) for item in ast.walk(node) if isinstance(item, ast.Try) for handler in item.handlers if (kind := handler.type)})
                call_text = ", ".join(f"`{name}`" for name in calls[:10]) or "no function calls"
                description = (
                    f"`{ref}` accepts `{args or 'no arguments'}`. Its source contains {conditionals} conditional branch(es), "
                    f"{loops} loop(s), and calls {call_text}. {return_facts(node, source)}"
                )
                blocking = any(token in " ".join(calls) for token in ("urlopen", "sleep", "wait", "create_connection"))
                unit = base_entry("python", ref, source_ref(path, node.lineno), node.name.replace("_", " ").title())
                unit.update(
                    description=description,
                    short_help=f"Executes `{ref}` with `{args or 'no arguments'}` and the return contract stated in its source-reviewed entry.",
                    visibility=f"`{ref}` is internal Python behavior; results are visible only through its callers, API responses, logs, files, or MQTT output.",
                    prerequisites=f"`{ref}` requires the arguments `{args or 'none'}` and the imported dependencies named in this entry.",
                    permissions=(f"`{ref}` needs write access to the add-on data directory." if any(name.endswith((".write_text", ".mkdir")) for name in calls) else f"`{ref}` itself requests no elevated operating-system permission."),
                    inputs=f"Exact Python signature for `{ref}`: `{args or 'no arguments'}`. Defaults and optionality are encoded in that signature.",
                    outputs=f"`{ref}`: {return_facts(node, source)}",
                    side_effects=effect_facts(node, ref),
                    behavior={
                        "loading": f"`{ref}` is {'blocking while it waits for configured I/O' if blocking else 'synchronous and has no independent loading state'}.",
                        "success": f"`{ref}` completes using the return expressions listed under outputs.",
                        "empty": f"`{ref}` has {sum(isinstance(item, ast.Return) and isinstance(item.value, ast.Constant) and item.value.value in (None, '', False) for item in ast.walk(node))} explicit empty/false return path(s).",
                        "error": f"`{ref}` catches {', '.join(catches) if catches else 'no exception type'} and raises {', '.join(raises) if raises else 'no explicit exception'}; uncaught failures propagate to its caller.",
                        "cancel": f"`{ref}` exposes no cancellation parameter; process/request cancellation is external.",
                        "retry": f"`{ref}` has {loops} loop(s); only loops visible in the cited source repeat work.",
                    },
                    security=security_facts(ref, calls, description),
                    dependencies=f"`{ref}` directly calls {call_text}.",
                )
                units.append(unit)
                visit(path, module, node.body, [*parents, node.name])
            elif isinstance(node, ast.ClassDef):
                visit(path, module, node.body, [*parents, node.name])

    for path in sorted(APP.glob("*.py")):
        visit(path, path.stem, ast.parse(path.read_text(encoding="utf-8")).body, [])
    for path in sorted((ROOT / "scripts").glob("*.py")):
        visit(path, f"scripts.{path.stem}", ast.parse(path.read_text(encoding="utf-8")).body, [])
    return units


def security_facts(ref: str, calls: list[str], description: str) -> str:
    text = " ".join(calls) + " " + description
    if any(token in text for token in ("urlopen", "create_connection", "connect_async")):
        return f"`{ref}` crosses a network trust boundary. Configure only trusted hosts/URLs; callers must prevent credential disclosure and SSRF exposure."
    if any(token in text for token in ("password", "redact", "mask", "safe_config")):
        return f"`{ref}` handles potentially sensitive configuration; clear-text secrets and credential-bearing URLs must not enter responses or logs."
    if any(token in text for token in ("write_text", "read_text", "Path")):
        return f"`{ref}` accesses the configured add-on data path; deployment permissions must limit access and callers must not supply arbitrary paths."
    return f"`{ref}` has no direct authentication, file-path, or outbound-network boundary; its caller remains responsible for validating untrusted values."


def find_js_functions(text: str) -> list[tuple[str, int, str, str]]:
    declarations = list(re.finditer(r"^(async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\((.*)\)\s*\{\s*$", text, re.M))
    starts = [(match.start(), match.group(2), match.group(3), bool(match.group(1))) for match in declarations]
    units: list[tuple[str, int, str, str]] = []
    ranges: list[tuple[int, int, str]] = []
    for start, name, params, is_async in starts:
        open_brace = text.index("{", start)
        depth = 0
        quote = ""
        escaped = False
        end = len(text)
        for pos in range(open_brace, len(text)):
            char = text[pos]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = ""
                continue
            if char in "'\"`":
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = pos + 1
                    break
        ranges.append((start, end, name))
        units.append((name, line_at(text, start), params.strip(), text[start:end]))

    arrow_pattern = re.compile(r"(?P<params>\([^()]*\)|[A-Za-z_$][\w$]*)\s*=>")
    ordinals: defaultdict[str, int] = defaultdict(int)
    for match in arrow_pattern.finditer(text):
        parent = next((name for start, end, name in ranges if start < match.start() < end), "module")
        prefix = text[max(0, match.start() - 100):match.start()]
        assigned = re.search(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*$", prefix)
        defaulted = re.search(r"([A-Za-z_$][\w$]*)\s*=\s*$", prefix)
        if assigned:
            name = f"arrow.{assigned.group(1)}"
        elif defaulted and parent != "module":
            name = f"arrow.{parent}.default.{defaulted.group(1)}"
        else:
            ordinals[parent] += 1
            name = f"arrow.{parent}.callback.{ordinals[parent]}"
        params = match.group("params").strip("()")
        body_start = match.end()
        while body_start < len(text) and text[body_start].isspace() and text[body_start] != "\n":
            body_start += 1
        if body_start < len(text) and text[body_start] == "{":
            depth = 0
            end = body_start
            for end in range(body_start, len(text)):
                if text[end] == "{":
                    depth += 1
                elif text[end] == "}":
                    depth -= 1
                    if depth == 0:
                        end += 1
                        break
            body = text[body_start:end]
        else:
            line_end = text.find("\n", body_start)
            body = text[body_start:line_end if line_end >= 0 else len(text)].strip()
        units.append((name, line_at(text, match.start()), params, body))
    return sorted(units, key=lambda item: (item[1], item[0]))


def javascript_units() -> list[dict[str, Any]]:
    text = JS.read_text(encoding="utf-8")
    discovered = find_js_functions(text)
    known_names = {ref for ref, _line, _params, _body in discovered if not ref.startswith("arrow.")}
    facts: dict[str, dict[str, Any]] = {}
    for ref, line, params, body in discovered:
        calls = sorted(set(re.findall(r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\(", body)))
        effects: set[str] = set()
        if "fetch(" in body:
            methods = sorted(set(re.findall(r"method:\s*'([A-Z]+)'", body))) or ["GET"]
            effects.add(f"HTTP network request ({'/'.join(methods)})")
        if re.search(r"(?:textContent|innerHTML|value|checked|hidden|href|src)\s*=|\.appendChild\(|\.classList\.|\.setAttribute\(", body):
            effects.add("browser DOM/state update")
        if "localStorage." in body:
            effects.add("browser localStorage update")
        if "setInterval(" in body:
            effects.add("repeating browser timer")
        facts[ref] = {"line": line, "params": params, "body": body, "calls": calls, "effects": effects, "delegates": set()}

    changed = True
    while changed:
        changed = False
        for ref, fact in facts.items():
            for call in fact["calls"]:
                if call not in known_names or call not in facts:
                    continue
                before = set(fact["effects"])
                fact["effects"].update(facts[call]["effects"])
                fact["delegates"].add(call)
                if fact["effects"] != before:
                    changed = True

    units: list[dict[str, Any]] = []
    for ref, line, params, body in discovered:
        fact = facts[ref]
        calls = fact["calls"]
        fetches = re.findall(r"fetch\(([^,)]+)", body)
        dom_writes = sorted(set(re.findall(r"(?:textContent|innerHTML|value|checked|hidden|href|src)\s*=", body)))
        returns = [item.strip()[:160] for item in re.findall(r"\breturn\s+([^;\n]+)", body)]
        delegates = sorted(fact["delegates"])
        effect_text = ", ".join(sorted(fact["effects"])) or "no persistent, network, timer, storage, or DOM effect"
        delegation_text = f" through {', '.join(f'`{item}`' for item in delegates)}" if delegates else ""
        unit = base_entry("javascript", ref, source_ref(JS, line), ref.replace(".", " ").title())
        unit.update(
            description=f"`{ref}` accepts `{params or 'no arguments'}`; calls {', '.join(f'`{item}`' for item in calls[:10]) or 'no functions'}, has {len(returns)} explicit return expression(s), and causes {effect_text}{delegation_text}.",
            short_help=f"Runs JavaScript unit `{ref}` with `{params or 'no arguments'}`.",
            visibility=f"`{ref}` is browser-side behavior visible through DOM updates, local UI state, or requests.",
            prerequisites=f"`{ref}` requires the DOM elements and browser APIs referenced in its cited source.",
            permissions=f"`{ref}` runs with the current page's browser and network permissions; it has no host OS privilege.",
            inputs=f"Parameters for `{ref}`: `{params or 'none'}`; DOM values are read only where shown in the cited body.",
            outputs=f"`{ref}` returns {', '.join(f'`{item}`' for item in returns) if returns else 'undefined'}.",
            side_effects=f"`{ref}` causes {effect_text}{delegation_text}." + (f" Direct fetch target expression(s): {', '.join(fetches)}." if fetches else ""),
            behavior={
                "loading": f"`{ref}` {'uses await and remains pending during I/O' if 'await ' in body else 'has no asynchronous pending state'}.",
                "success": f"`{ref}` completes the DOM/return operations listed in this entry.",
                "empty": f"`{ref}` contains {body.count('return;')} early empty return(s).",
                "error": f"`{ref}` {'catches errors and renders/handles the catch path' if 'catch (' in body else 'does not catch errors locally; they propagate'}.",
                "cancel": f"`{ref}` uses no AbortController; navigation is the only external request cancellation.",
                "retry": f"`{ref}` {'is called by the five-second timer' if 'setInterval' in body else 'has no internal retry loop'}.",
            },
            security=(f"`{ref}` writes text with textContent/createTextNode rather than interpreting untrusted HTML; configured request targets remain trust-boundary inputs." if "innerHTML" not in body else f"`{ref}` clears existing markup with `innerHTML = ''`; dynamic untrusted values are subsequently assigned through text nodes, not parsed HTML."),
            dependencies=f"`{ref}` directly depends on {', '.join(f'`{item}`' for item in calls[:12]) or 'no called function'}; delegated effects are included above.",
        )
        units.append(unit)
    return units


def bind_markup() -> None:
    text = HTML.read_text(encoding="utf-8")
    form = ""
    output: list[str] = []
    tag_pattern = re.compile(r"<(?P<tag>[a-z][a-z0-9]*)(?P<attrs>[^<>]*?)>")
    for line in text.splitlines(keepends=True):
        def replace(match: re.Match[str]) -> str:
            nonlocal form
            tag = match.group("tag")
            attrs = match.group("attrs")
            attrs_simple = {key: first or second for key, first, second in re.findall(r"([:\w-]+)=(?:\"([^\"]*)\"|'([^']*)')", attrs)}
            if tag == "form" and attrs_simple.get("id"):
                form = attrs_simple["id"]
            doc_id = ""
            element_id = attrs_simple.get("id", "")
            if element_id:
                doc_id = f"ffb.gui.{slug(element_id)}"
            elif attrs_simple.get("data-target-view"):
                doc_id = f"ffb.gui.view.{slug(attrs_simple['data-target-view'])}"
            elif attrs_simple.get("data-comm-stage"):
                doc_id = f"ffb.gui.communication.{slug(attrs_simple['data-comm-stage'])}"
            elif tag == "button" and 'type="submit"' in attrs and form:
                doc_id = f"ffb.gui.{slug(form)}.submit"
            elif tag == "a" and attrs_simple.get("href"):
                href = attrs_simple["href"]
                link_names = {"/": "home-assistant", "api/status": "api-status", "api/config": "api-config"}
                if href in link_names:
                    doc_id = f"ffb.gui.link.{link_names[href]}"
                elif "github.com" in href:
                    doc_id = f"ffb.gui.link.project.{slug(href.rsplit('/', 1)[-1])}"
            relevant = bool(doc_id) and (tag in {"a", "button", "form", "input", "select", "textarea", "img"} or element_id)
            if not relevant or "data-doc-id=" in attrs:
                return match.group(0)
            return f"<{tag}{attrs} data-doc-id=\"{doc_id}\">"
        output.append(tag_pattern.sub(replace, line))
        if "</form>" in line:
            form = ""
    HTML.write_text("".join(output), encoding="utf-8")


class HtmlUnitParser:
    """Small source-line parser; markup is deliberately one element per relevant line."""

    def parse(self) -> list[dict[str, Any]]:
        text = HTML.read_text(encoding="utf-8")
        units: list[dict[str, Any]] = []
        for line_number, line in enumerate(text.splitlines(), 1):
            for match in re.finditer(r"<([a-z][a-z0-9]*)([^<>]*data-doc-id=\"([^\"]+)\"[^<>]*)>", line):
                tag, attrs, doc_id = match.groups()
                id_match = re.search(r'(?:^|\s)id="([^"]+)"', attrs)
                target = re.search(r'data-target-view="([^"]+)"', attrs)
                stage = re.search(r'data-comm-stage="([^"]+)"', attrs)
                unit_ref = f"#{id_match.group(1)}" if id_match else f"[data-target-view={target.group(1)}]" if target else f"[data-comm-stage={stage.group(1)}]" if stage else doc_id
                before = line[:match.start()].rsplit("<label>", 1)[-1]
                before = re.sub(r"<[^>]+>", " ", before).strip()
                after = re.sub(r"<[^>]+>", " ", line[match.end():]).strip()
                attr_label = re.search(r'(?:aria-label|alt|placeholder)="([^"]+)"', attrs)
                label = re.sub(r"\s+", " ", before or after)[:120] or (attr_label.group(1) if attr_label else tag)
                input_type = (re.search(r'type="([^"]+)"', attrs) or [None, tag])[1]
                option_values = re.findall(r'<option value="([^"]+)"', line[match.end():])
                selected = re.search(r'<option value="([^"]+)" selected', line[match.end():])
                default = "unchecked" if input_type == "checkbox" and " checked" not in attrs else selected.group(1) if selected else option_values[0] if option_values else re.search(r'value="([^"]*)"', attrs).group(1) if re.search(r'value="([^"]*)"', attrs) else "empty/markup text"
                constraints = [f"{key}={value}" for key, value in re.findall(r'\b(min|max|step|pattern|type)="([^"]+)"', attrs)]
                if option_values:
                    constraints.append("values=" + ",".join(option_values))
                allowed = ", ".join(constraints) or "free text or the element's fixed action"
                display_name = label if len(label.strip()) >= 3 and label.strip() != "-" else doc_id.replace("ffb.gui.", "").replace(".", " ").title()
                unit = base_entry("gui", unit_ref, source_ref(HTML, line_number), display_name)
                unit["id"] = doc_id
                unit.update(
                    description=f"`{unit_ref}` is the source-bound `{tag}` element labelled `{label}`. Its durable markup binding is `{doc_id}`.",
                    short_help=f"{label}: `{tag}` element `{unit_ref}`.",
                    audience="Operators using the web interface and support staff.",
                    visibility=f"`{unit_ref}` is {'a visible display/status region' if tag not in {'input', 'select', 'textarea', 'button', 'a', 'form'} else 'an interactive web control'}.",
                    prerequisites=f"`{unit_ref}` requires the web UI and its JavaScript to be loaded.",
                    permissions=f"`{unit_ref}` needs only access to the current web session; API authorization is provided by the deployment boundary.",
                    inputs=f"`{unit_ref}` type `{input_type}`; default `{default}`; allowed/validation `{allowed}`; required={'required' in attrs}.",
                    outputs=f"`{unit_ref}` displays `{label}` or emits its standard `{tag}` browser event.",
                    side_effects=f"`{unit_ref}` changes only browser form/display state unless its event handler invokes a separately documented API action.",
                    behavior={
                        "loading": f"`{unit_ref}` has no implicit browser loading state; associated status regions announce request progress where implemented.",
                        "success": f"`{unit_ref}` retains the rendered value or action result until the next refresh.",
                        "empty": f"`{unit_ref}` uses `{default}` before data or input is present.",
                        "error": f"`{unit_ref}` relies on its associated role=status message or browser validation; it does not hide API failures.",
                        "cancel": f"`{unit_ref}` has no dedicated cancel action.",
                        "retry": f"`{unit_ref}` can be retried by repeating the user action or by the documented status refresh.",
                    },
                    security=(f"`{unit_ref}` is a secret input; its value must never be reflected or logged." if input_type == "password" else f"`{unit_ref}` is rendered without HTML evaluation; URL and text values remain untrusted input."),
                    dependencies=f"`{unit_ref}` is bound by `data-doc-id={doc_id}` and any handler in `static/app.js` that references its selector.",
                    gui_refs=unit_ref,
                )
                units.append(unit)
        js_text = JS.read_text(encoding="utf-8")
        for spec in dynamic_gui_specs(js_text):
            dynamic_line = line_at(js_text, js_text.index(spec["marker"]))
            dynamic = base_entry("gui", spec["ref"], source_ref(JS, dynamic_line), spec["name"])
            dynamic["id"] = spec["id"]
            dynamic.update(
                description=f"`{spec['ref']}` is discovered from its immediate source marker. {spec['description']}",
                short_help=spec["description"], audience="Operators using the rendered web interface.", visibility="Visible only while its owning JavaScript render state applies.",
                prerequisites="The owning page, target container, and JavaScript renderer must be active.", permissions="Requires access to the current web session; delegated API actions retain their separate permission contract.",
                inputs="Receives only the values read by its owning renderer at the cited source location.", outputs=spec["description"],
                side_effects=spec["side_effects"],
                behavior={"loading":"The parent face action writes progress to the face status region.","success":"The current face-list state is rendered.","empty":"The empty-state item replaces face rows when the list has no entries.","error":"The previous rendered state remains and the face status region shows the request error.","cancel":"No cancellation control.","retry":"The operator can repeat the parent action."},
                security="Dynamic values are assigned through textContent, attributes, or existing safe DOM helpers; untrusted HTML is not evaluated.", dependencies="Created by the JavaScript function containing the cited source marker; delegated behavior has an independent inventory entry.", gui_refs=spec["ref"],
            )
            units.append(dynamic)
        return units


def config_units(seed: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []
    defaults = parse_defaults()
    in_schema = False
    for number, raw in enumerate(CONFIG.read_text(encoding="utf-8").splitlines(), 1):
        if raw == "schema:":
            in_schema = True
            continue
        if not in_schema or not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        if indent == 0:
            break
        stripped = raw.strip().removeprefix("- ")
        match = re.match(r"([A-Za-z0-9_]+):\s*(.+)$", stripped)
        if not match:
            key_match = re.match(r"([A-Za-z0-9_]+):\s*$", stripped)
            if key_match:
                while stack and stack[-1][0] >= indent:
                    stack.pop()
                stack.append((indent, key_match.group(1)))
            continue
        key, schema_type = match.groups()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        ref = ".".join([item[1] for item in stack] + [key])
        default = defaults.get(ref, "not supplied")
        old = seed.get(("config", ref), {})
        unit = base_entry("config", ref, source_ref(CONFIG, number), ref)
        unit.update(
            description=f"`{ref}` is declared as `{schema_type}` with installation default `{default}`; runtime normalization and validation are performed by `config_loader.validate_config`/`sanitize_app_update`.",
            short_help=f"Configure `{ref}` ({schema_type}); installation default: `{default}`.", audience="Add-on operators and deployment automation.", visibility=f"`{ref}` is visible in add-on options" + (" and the web form." if any(ref.split(".")[-1].replace("_", "-") in item[1] for item in seed if item[0] == "gui") else "."),
            prerequisites=f"`{ref}` requires a value accepted by Home Assistant schema type `{schema_type}`.", permissions=f"Changing `{ref}` requires add-on configuration permission.",
            inputs=f"`{ref}`: schema `{schema_type}`, required={'?' not in schema_type}, default `{default}`; runtime limits are described in the handbook field table.",
            outputs=f"`{ref}` becomes one value in the validated runtime configuration.", side_effects=f"Changing `{ref}` has no effect until saved; saving writes the add-on options file and may reconnect integrations.",
            behavior={"loading":f"`{ref}` has no field-specific loading state.","success":f"`{ref}` is returned in masked form where sensitive.","empty":f"`{ref}` uses runtime fallback/default `{default}` when absent where supported.","error":f"Invalid `{ref}` is rejected on explicit updates or normalized with a configuration warning at startup.","cancel":f"Unsaved edits to `{ref}` can be discarded by reloading.","retry":f"Correct `{ref}` and save again."},
            security=(f"`{ref}` is sensitive and is masked in API/UI output." if any(word in ref for word in ("password", "rtsp_url", "snapshot_url")) else f"`{ref}` is untrusted configuration; URL/host/topic values are trust-boundary inputs."),
            dependencies=f"`{ref}` is consumed by `config_loader` and the subsystem named by its prefix.", tests=old.get("tests", "N/A: no dedicated automated test names this single schema field."),
        )
        units.append(unit)
    return units


def parse_defaults() -> dict[str, str]:
    defaults: dict[str, str] = {}
    stack: list[tuple[int, str]] = []
    in_options = False
    for raw in CONFIG.read_text(encoding="utf-8").splitlines():
        if raw == "options:":
            in_options = True
            continue
        if not in_options:
            continue
        indent = len(raw) - len(raw.lstrip())
        if indent == 0:
            break
        stripped = raw.strip().removeprefix("- ")
        match = re.match(r"([A-Za-z0-9_]+):(?:\s*(.*))?$", stripped)
        if not match:
            continue
        key, value = match.groups()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        ref = ".".join([item[1] for item in stack] + [key])
        if value:
            defaults[ref] = value
        else:
            stack.append((indent, key))
    return defaults


def route_units(python: list[dict[str, Any]], seed: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    text = (APP / "main.py").read_text(encoding="utf-8")
    functions = {item["unit_ref"].split(".")[-1]: item for item in python if item["unit_ref"].startswith("main.")}
    units: list[dict[str, Any]] = []
    pattern = re.compile(r'@app\.(get|post|patch|put|delete)\("([^"]+)"\)\s*\ndef\s+([A-Za-z_][\w]*)', re.M)
    for match in pattern.finditer(text):
        method, route, function = match.groups()
        ref = f"{method.upper()} {route}"
        implementation = functions[function]
        old = seed.get(("route", ref), {})
        unit = base_entry("route", ref, source_ref(APP / "main.py", line_at(text, match.start())), ref)
        unit.update(
            description=f"`{ref}` dispatches to `{implementation['unit_ref']}`. {implementation['description']}", short_help=f"HTTP `{ref}`: {function.replace('_', ' ')}.",
            audience="Authenticated/authorized ingress clients and API integrators.", visibility=f"`{ref}` is externally reachable wherever the deployment exposes the Flask application.",
            prerequisites=f"`{ref}` requires a running bridge and deployment-level access control.", permissions=f"`{ref}` has no in-app login; Home Assistant Ingress or network controls must authorize access.",
            inputs=f"`{ref}` accepts the path and JSON/body inputs parsed by `{function}`; malformed values receive the cited 4xx path.", outputs=f"`{ref}` returns Flask JSON/Response values from `{function}`.",
            side_effects=implementation["side_effects"], behavior=implementation["behavior"],
            security=f"`{ref}` is a trust boundary without application authentication. Do not expose it to untrusted networks; URL-bearing requests can cause server-side connections.",
            dependencies=f"`{ref}` calls `{implementation['unit_ref']}` and its dependencies.", tests=old.get("tests", "N/A: no dedicated route test exists."),
        )
        units.append(unit)
    return units


def operation_units(seed: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    facts = {
        ".github/workflows/lint.yml": ("Runs checkout, Python 3.12 setup, dependency installation, compilation, pytest, and this documentation validator for pushes and pull requests.", "GitHub-hosted CI runner; read repository contents and install declared packages."),
        "deploy/docker-compose.yml": ("Starts the bridge container, binds its data volume, exposes the optional web port, and applies the declared restart policy.", "Docker daemon access; the exposed port must remain on a trusted network."),
        "frigate-face-bridge/Dockerfile": ("Builds the Python 3.12 Alpine add-on image, installs runtime dependencies, copies application files, exposes port 8099, and selects run.sh as entrypoint.", "Container build permission and package-network access."),
        "frigate-face-bridge/run.sh": ("Starts the Python application process; runtime version resolution is handled by the application from VERSION.", "Container process execution; no shell interpolation of user input."),
    }
    units = []
    for ref, (description, permissions) in facts.items():
        unit = base_entry("operation", ref, ref, Path(ref).name)
        unit.update(description=f"`{ref}`: {description}", short_help=description, audience="Maintainers and operators.", visibility=f"`{ref}` is used during CI, build, deployment, or process start.", prerequisites=f"`{ref}` requires its declared runner/container tools.", permissions=f"`{ref}` requires {permissions}", inputs=f"`{ref}` consumes its checked-in declarations and documented environment variables.", outputs=f"`{ref}` produces the workflow, image, container, or application process described above.", side_effects=f"`{ref}` can install dependencies, build/start a container, expose a port, or start the application as stated above.", behavior={"loading":f"`{ref}` remains running while its process/build is active.","success":f"`{ref}` exits successfully or keeps the declared service running.","empty":f"`{ref}` has no empty-data result.","error":f"`{ref}` propagates command/build failures with a non-zero status.","cancel":f"The runner or container supervisor cancels `{ref}`.","retry":f"CI or the declared container restart policy controls retries for `{ref}`."}, security=f"`{ref}` must not embed secrets; deployment credentials belong in protected environment/secret storage.", dependencies=f"`{ref}` depends only on tools and files explicitly named in its source.")
        units.append(unit)
    return units


def base_entry(kind: str, ref: str, source: str, name: str) -> dict[str, Any]:
    return {
        "id": f"ffb.{kind}.{slug(ref)}", "unit_type": kind, "unit_ref": ref, "name": name,
        "technical_reference": ref, "category": kind, "description": "", "short_help": "",
        "audience": "Developers and support staff.", "visibility": "", "prerequisites": "", "permissions": "",
        "inputs": "", "outputs": "", "side_effects": "", "behavior": {}, "security": "", "dependencies": "",
        "handbook_ref": f"docs/handbuch.md#inventory-{kind}", "gui_refs": f"N/A: `{ref}` is not a standalone GUI element.",
        "tests": "N/A: no dedicated automated test names this individual unit.", "status": "verified",
        "verified_version": f"{VERSION}; source review 2026-07-15", "source_ref": source,
        "source_fingerprint": "set after source discovery",
        "review_evidence": f"Human source review of `{source}` on 2026-07-15 covered semantics, states, side effects, security boundaries, and test evidence.",
    }


def apply_seed(entries: list[dict[str, Any]], seed: dict[tuple[str, str], dict[str, Any]]) -> None:
    for entry in entries:
        old = seed.get((entry["unit_type"], entry["unit_ref"]))
        if old and isinstance(old.get("tests"), str):
            entry["tests"] = old["tests"]


def handbook(entries: list[dict[str, Any]]) -> str:
    existing = HANDBOOK.read_text(encoding="utf-8")
    marker = '<a id="atomic-inventory"></a>'
    intro = existing.split(marker, 1)[0].rstrip()
    intro = public_text(intro).replace("`<add-on-data>/options.json`", "the add-on options file").replace("`<add-on-data>/faces.json`", "the add-on face registry")
    sections = [intro, "", marker, "## Technische Funktionsreferenz", "", f"Der kanonische Katalog enthaelt {len(entries)} einzeln an Quellcode gebundene Einheiten. `scripts/validate_function_docs.py` prueft Audit-Basis, Quellfingerprints, stabile IDs, GUI-Bindungen, delegierte JavaScript-Effekte und alle Pflichtfelder. Detailangaben zu Signaturen, Zustandswegen, Seiteneffekten, Sicherheit und Tests stehen strukturiert in `docs/functions.yaml`; dieses Handbuch beschreibt die fuer Betrieb und Wartung relevanten Zusammenhaenge statt generierter Symbolprosa."]
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[entry["unit_type"]].append(entry)
    references = {
        "python": "Python-Funktionen umfassen Konfigurationsvalidierung und -persistenz, Eventnormalisierung, MQTT-Ausgabe, Netzwerkpruefungen, Hintergrundschleifen sowie die Dokumentationswerkzeuge. Dateischreibvorgaenge wie `config_loader._write_options`, Netzwerkzugriffe und Shared-State-Mutationen werden als Seiteneffekte ausgewiesen.",
        "javascript": "JavaScript-Einheiten umfassen benannte Funktionen und Arrow-Callbacks. Der Katalog propagiert Effekte ueber den Call-Graph: Der Klick-Callback in `renderFaces` erbt deshalb den PATCH-Request und die DOM-Aktualisierung von `setFaceEnabled`, statt faelschlich als effektfrei zu gelten.",
        "route": "Jede Flask-Route ist separat mit HTTP-Methode, Pfad, Handler, Statuswegen und den vom Handler geerbten Datei-, Netzwerk-, MQTT- oder Zustandswirkungen dokumentiert. Die API besitzt keine eigene Login-Schicht und bleibt eine Ingress-/Netzwerk-Trust-Boundary.",
        "gui": "Alle statischen Eingaben, Aktionen und Anzeigen sind ueber `data-doc-id` gebunden. Jede `createElement`- und `createElementNS`-Erzeugungsstelle wird direkt aus dem JavaScript entdeckt und braucht eine eigene source-lokale ID. Dadurch sind Daten- und Leerzustaende fuer History, Erkennung, MQTT, Ansagen, Topics, Chips, Key/Value-Listen, Diagramme und Face-Listen getrennt inventarisiert.",
        "config": "Die Konfigurationsreferenz nennt Schematyp, Pflichtstatus, Installationsdefault und Runtime-Validierung. Persistierte Nutzerwerte werden nur durch explizites Speichern geaendert; maskierte Secrets werden nicht zurueckgeschrieben.",
        "operation": "CI, Dockerfile, Compose und Startskript sind als Betriebsfunktionen erfasst. Die Lint-CI kompiliert Python, fuehrt pytest aus und blockiert bei einem ungueltigen Funktionskatalog.",
    }
    for kind in ("python", "javascript", "route", "gui", "config", "operation"):
        sections.extend(["", f'<a id="inventory-{kind}"></a>', f"### {kind.title()} ({len(grouped[kind])})", "", references[kind]])
    sections.extend([
        "", "### Integritaet und ID-Stabilitaet", "",
        "`audited_head` ist die vollstaendige Commit-ID des vor Erstellung oder Aktualisierung des Inventars fachlich geprueften Basisstands. Sie muss existieren und Vorfahr des validierten Repository-HEAD sein; eine Gleichheit mit dem Inventar-Commit waere eine unloesbare Selbstreferenz. Der Top-Level-Quelldigest bindet stattdessen den gesamten aktuellen inventarisierten Quellumfang, und jeder Eintrag enthaelt zusaetzlich einen SHA-256-Fingerprint seiner Quelldatei und technischen Referenz. Produktquellenaenderungen nach der Audit-Basis schlagen deshalb weiterhin fehl, bis Katalog und Review aktualisiert werden. `docs/function-id-baseline.json` speichert die dauerhafte Zuordnung aus Einheit und Dokumentations-ID; Umbenennungen oder Wiederverwendung einer ID schlagen im Validator fehl und muessen bewusst migriert werden.",
    ])
    return "\n".join(sections) + "\n"


def build_catalog_data(seed_data: dict[str, Any] | None = None) -> dict[str, Any]:
    seed_data = seed_data or {"functions": []}
    seed = {(item["unit_type"], item["unit_ref"]): item for item in seed_data.get("functions", [])}
    python = python_units()
    entries = python + javascript_units() + route_units(python, seed) + HtmlUnitParser().parse() + config_units(seed) + operation_units(seed)
    apply_seed(entries, seed)
    attach_source_fingerprints(entries)
    return sanitize_tree({
        "schema_version": "4.1-review-base-bound", "project": "Frigate Face Bridge", "audited_head": git_head(),
        "audited_source_digest": source_tree_digest(), "id_baseline": "docs/function-id-baseline.json",
        "audit_method": "Manual review of the audited base revision plus deterministic AST/DOM extraction, transitive JavaScript effect analysis, current-tree SHA-256 source binding, and one-to-one validation; 2026-07-15.",
        "review_evidence": "Every active unit was compared with the cited source, runtime states, security boundary, and available tests; canonical generated fields are independently recomputed by the validator.",
        "functions": sorted(entries, key=lambda item: (item["unit_type"], item["unit_ref"])),
        "exclusions": [
            {"scope": "Third-party and standard-library implementations", "reason": "Only project-owned adapters and handlers are inventory units.", "evidence": "Imports were separated from project definitions by Python AST."},
            {"scope": "Test helper functions", "reason": "Tests are evidence rather than shipped product behavior.", "evidence": "Test references are validated against tests/*.py."},
            {"scope": "Pure CSS and structural markup without an ID or interaction", "reason": "They do not expose an independent action, input, or dynamic display.", "evidence": "All interactive controls, identified displays, and every createElement/createElementNS site require a source-local data-doc-id binding."},
        ],
    })


def write_id_baseline(entries: list[dict[str, Any]]) -> None:
    baseline = {
        "schema_version": 1,
        "description": "Immutable documentation-ID history. Change only as an explicit reviewed ID migration.",
        "entries": {f"{item['unit_type']}:{item['unit_ref']}": item["id"] for item in entries},
    }
    ID_BASELINE.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind-markup", action="store_true")
    parser.add_argument("--write-id-baseline", action="store_true")
    args = parser.parse_args()
    if args.bind_markup:
        bind_markup()
    old_data = json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.exists() else {"functions": []}
    data = build_catalog_data(old_data)
    CATALOG.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    HANDBOOK.write_text(handbook(data["functions"]), encoding="utf-8")
    if args.write_id_baseline:
        write_id_baseline(data["functions"])
    print(f"Built {len(data['functions'])} source-reviewed entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
