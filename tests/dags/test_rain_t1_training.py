import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "dags" / "rain_t1_training.py"
SPEC = importlib.util.spec_from_file_location("rain_t1_training", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_build_compact_summary_returns_expected_fields():
    summary = {
        "mlflow_run_id": "run-123",
        "registered_model": {"version": "7"},
        "best_model": {
            "model_name": "xgboost_classifier",
            "metrics": {
                "average_precision": 0.3533,
                "f1": 0.3492,
            },
        },
    }

    assert MODULE.build_compact_summary(summary) == {
        "model_name": "xgboost_classifier",
        "run_id": "run-123",
        "version": "7",
        "average_precision": 0.3533,
        "f1": 0.3492,
        "serving_output_dir": None,
    }


def test_copy_summary_file_creates_destination_directory(tmp_path):
    source = tmp_path / "tmp" / "summary.json"
    destination = tmp_path / "reports" / "rain_t1_training_summary.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text('{"status": "ok"}\n', encoding="utf-8")

    MODULE.copy_summary_file(source, destination)

    assert destination.read_text(encoding="utf-8") == '{"status": "ok"}\n'
