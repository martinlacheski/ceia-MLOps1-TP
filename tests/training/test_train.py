from datetime import datetime, timedelta

import pandas as pd

from ceml_rain.training.train import (
    build_candidate_specs,
    parse_args,
    select_training_features,
    temporal_train_test_split,
)


def test_select_training_features_excludes_leakage_columns():
    columns = [
        "fecha",
        "lluvia_mm",
        "llovio",
        "lluvia_mm_lag_1",
        "lluvia_mm_rolling_7_sum",
        "dias_lluvia_rolling_7",
        "mes",
        "dia_anio",
        "dia_semana",
        "y_lluvia_mm_t1",
        "y_llueve_t1",
    ]

    assert select_training_features(columns) == [
        "dia_anio",
        "dia_semana",
        "dias_lluvia_rolling_7",
        "lluvia_mm_lag_1",
        "lluvia_mm_rolling_7_sum",
        "mes",
    ]


def test_temporal_train_test_split_preserves_temporal_order():
    start = datetime(2024, 1, 1)
    dataset = pd.DataFrame(
        {
            "fecha": [start + timedelta(days=offset) for offset in range(10)],
            "y_llueve_t1": [offset % 2 == 0 for offset in range(10)],
        }
    )

    train_df, test_df = temporal_train_test_split(dataset, test_fraction=0.3)

    assert len(train_df) == 7
    assert len(test_df) == 3
    assert train_df["fecha"].max() < test_df["fecha"].min()


def test_build_candidate_specs_reports_missing_xgboost_when_unavailable(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "xgboost":
            raise ModuleNotFoundError("No module named 'xgboost'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    candidates, skipped = build_candidate_specs(random_state=42, include_xgboost=True)

    assert [candidate.name for candidate in candidates] == ["logistic_regression", "random_forest"]
    assert skipped == [{"model": "xgboost_classifier", "reason": "xgboost_not_installed"}]


def test_parse_args_accepts_serving_output_dir():
    args = parse_args(["--serving-output-dir", "data/models/rain_t1/current"])

    assert str(args.serving_output_dir) == "data/models/rain_t1/current"
