import copy
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location("function_docs_validator", SCRIPTS / "validate_function_docs.py")
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def catalog_data():
    return json.loads((ROOT / "docs/functions.yaml").read_text(encoding="utf-8"))


def test_checked_in_inventory_is_valid():
    errors, counts = validator.validate()

    assert errors == []
    assert sum(counts.values()) >= 513


def test_validator_rejects_generic_auto_verified_wording(tmp_path, monkeypatch):
    data = catalog_data()
    data["functions"][0]["description"] = "konkrete Leerwerte und Ausnahmen folgen dem Codepfad"
    catalog = tmp_path / "functions.yaml"
    catalog.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(validator, "CATALOG", catalog)

    errors, _counts = validator.validate()

    assert any("rejected generic wording" in error for error in errors)


def test_validator_rejects_substantive_field_generic_substitution(tmp_path, monkeypatch):
    data = catalog_data()
    entry = data["functions"][0]
    entry["description"] = "Processes configured input and returns the documented result."
    entry["short_help"] = "Runs this function for the operator."
    entry["outputs"] = "Returns a result when successful."
    entry["behavior"] = {
        "loading": "Shows loading while work runs.",
        "success": "Shows success.",
        "empty": "Shows an empty state.",
        "error": "Shows an error.",
        "cancel": "Can be cancelled externally.",
        "retry": "Can be retried.",
    }
    catalog = tmp_path / "functions.yaml"
    catalog.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(validator, "CATALOG", catalog)

    errors, _counts = validator.validate()

    for field in ("description", "short_help", "outputs", "behavior"):
        assert any(f"canonical field differs from source-derived value: {field}" in error for error in errors)


def test_validator_rejects_duplicate_documentation_id(tmp_path, monkeypatch):
    data = catalog_data()
    duplicate = copy.deepcopy(data["functions"][0])
    duplicate["unit_ref"] = data["functions"][1]["unit_ref"]
    duplicate["technical_reference"] = duplicate["unit_ref"]
    data["functions"].append(duplicate)
    catalog = tmp_path / "functions.yaml"
    catalog.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(validator, "CATALOG", catalog)

    errors, _counts = validator.validate()

    assert any("doppelte Dokumentations-ID" in error for error in errors)


def test_parser_rejects_gui_without_data_doc_id():
    parser = validator.InteractiveParser()
    parser.feed('<label>Name <input id="name"></label>')

    assert parser.errors == ["GUI element input at line 1 lacks data-doc-id"]


def test_validator_discovers_named_and_callback_arrow_functions():
    units = validator.javascript_units()

    assert "arrow.xFor" in units
    assert "arrow.renderFaces.callback.1" in units
    assert "arrow.includeIfChanged.default.transform" in units


def test_every_gui_entry_matches_one_markup_binding():
    bindings, errors = validator.gui_bindings()
    entries = [item for item in catalog_data()["functions"] if item["unit_type"] == "gui"]

    assert errors == []
    assert len(bindings) == len(entries)
    assert {item["unit_ref"]: item["id"] for item in entries} == bindings


def test_render_faces_callback_inherits_delegated_patch_and_dom_effects():
    entry = next(item for item in catalog_data()["functions"] if item["unit_ref"] == "arrow.renderFaces.callback.1")

    assert "setFaceEnabled" in entry["side_effects"]
    assert "HTTP network request (PATCH)" in entry["side_effects"]
    assert "browser DOM/state update" in entry["side_effects"]


def test_dynamic_face_displays_have_independent_stable_bindings():
    bindings, errors = validator.gui_bindings()

    assert errors == []
    assert bindings['dynamic:[data-doc-id="ffb.gui.face.list.empty"]'] == "ffb.gui.face.list.empty"
    assert bindings['dynamic:[data-doc-id="ffb.gui.face.list.item"]'] == "ffb.gui.face.list.item"
    assert bindings['dynamic:[data-doc-id="ffb.gui.face.enabled.toggle"]'] == "ffb.gui.face.enabled.toggle"


def test_all_dynamic_history_mqtt_announcement_topic_and_chip_states_are_discovered():
    bindings, errors = validator.gui_bindings()

    assert errors == []
    for doc_id in (
        "ffb.gui.history.empty", "ffb.gui.history.row", "ffb.gui.recognition.empty",
        "ffb.gui.recognition.row", "ffb.gui.mqtt.empty", "ffb.gui.mqtt.row",
        "ffb.gui.announcement.empty", "ffb.gui.announcement.row",
        "ffb.gui.mqtt.topic.empty", "ffb.gui.mqtt.topic.item",
        "ffb.gui.chip.empty", "ffb.gui.chip.item", "ffb.gui.key-value.item",
    ):
        assert bindings[f'dynamic:[data-doc-id="{doc_id}"]'] == doc_id


def test_adversarial_unmarked_create_element_is_rejected():
    text = validator.JAVASCRIPT.read_text(encoding="utf-8") + "\nconst rogue = document.createElement('aside');\n"

    try:
        validator.dynamic_gui_specs(text)
    except ValueError as exc:
        assert "lacks an immediate data-doc-id marker" in str(exc)
    else:
        raise AssertionError("unmarked dynamic display was accepted")


def test_validator_rejects_canonical_effect_tampering(tmp_path, monkeypatch):
    data = catalog_data()
    entry = next(item for item in data["functions"] if item["unit_ref"] == "arrow.renderFaces.callback.1")
    entry["side_effects"] = "No network or DOM effect."
    catalog = tmp_path / "functions.yaml"
    catalog.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(validator, "CATALOG", catalog)

    errors, _counts = validator.validate()

    assert any("canonical field differs from source-derived value: side_effects" in error for error in errors)


def test_validator_rejects_common_symbol_and_id_rename(tmp_path, monkeypatch):
    data = catalog_data()
    entry = next(item for item in data["functions"] if item["unit_type"] == "python")
    entry["unit_ref"] += "Renamed"
    entry["technical_reference"] = entry["unit_ref"]
    entry["id"] += ".renamed"
    catalog = tmp_path / "functions.yaml"
    catalog.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(validator, "CATALOG", catalog)

    errors, _counts = validator.validate()

    assert any("worktree baseline documentation unit disappeared without migration" in error for error in errors)
    assert any("Veraltete python-Einheiten" in error for error in errors)


def test_base_ref_rejects_coordinated_generator_catalog_baseline_rename(tmp_path, monkeypatch):
    data = catalog_data()
    original_baseline = json.loads((ROOT / "docs/function-id-baseline.json").read_text(encoding="utf-8"))["entries"]
    entry = next(item for item in data["functions"] if item["unit_type"] == "python")
    unit_key = f"python:{entry['unit_ref']}"
    old_id = entry["id"]
    entry["id"] = old_id + ".renamed"

    coordinated_baseline = copy.deepcopy(original_baseline)
    coordinated_baseline[unit_key] = entry["id"]
    baseline_path = tmp_path / "function-id-baseline.json"
    baseline_path.write_text(json.dumps({"entries": coordinated_baseline}), encoding="utf-8")
    catalog = tmp_path / "functions.yaml"
    catalog.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr(validator, "CATALOG", catalog)
    monkeypatch.setattr(validator, "ID_BASELINE", baseline_path)
    monkeypatch.setattr(validator, "build_catalog_data", lambda _seed: data)
    monkeypatch.setattr(validator, "baseline_from_base_ref", lambda _ref: original_baseline)
    monkeypatch.setenv("FUNCTION_DOCS_BASE_REF", "origin/main")

    errors, _counts = validator.validate()

    assert any(f"base ref origin/main documentation ID changed for {unit_key}: {old_id} -> {entry['id']}" in error for error in errors)


def test_validator_rejects_source_fingerprint_tampering(tmp_path, monkeypatch):
    data = catalog_data()
    data["functions"][0]["source_fingerprint"] = "sha256:" + "0" * 64
    catalog = tmp_path / "functions.yaml"
    catalog.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(validator, "CATALOG", catalog)

    errors, _counts = validator.validate()

    assert any("canonical field differs from source-derived value: source_fingerprint" in error for error in errors)


def test_validator_rejects_private_internal_details(tmp_path, monkeypatch):
    data = catalog_data()
    data["functions"][0]["description"] += " http://private-host.fossflow.localdomain"
    catalog = tmp_path / "functions.yaml"
    catalog.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(validator, "CATALOG", catalog)

    errors, _counts = validator.validate()

    assert any("private internal detail" in error for error in errors)
