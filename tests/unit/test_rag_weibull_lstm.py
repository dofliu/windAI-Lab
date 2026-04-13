"""RAG 強化、Weibull 風速分佈、LSTM 時序預測測試。"""

from __future__ import annotations

import numpy as np
import pytest

from src.skills.base import SkillInput, SkillStatus

# ════════════════════════════════════════════════════════════════
# RAG 強化
# ════════════════════════════════════════════════════════════════


class TestRAGChunking:
    def test_short_text_single_chunk(self) -> None:
        from src.services.rag_service import RAGService

        chunks = RAGService._split_text("Hello world", 1000, 200)
        assert chunks == ["Hello world"]

    def test_paragraph_aware_split(self) -> None:
        from src.services.rag_service import RAGService

        text = "Paragraph one about wind turbines.\n\nParagraph two about SCADA data.\n\nParagraph three about fault diagnosis."
        chunks = RAGService._split_text(text, 60, 0)
        # 應在段落邊界切割
        assert len(chunks) >= 2
        assert all(c.strip() for c in chunks)

    def test_overlap_added(self) -> None:
        from src.services.rag_service import RAGService

        text = "A" * 100 + "\n\n" + "B" * 100 + "\n\n" + "C" * 100
        chunks = RAGService._split_text(text, 120, 20)
        if len(chunks) > 1:
            # 第二個 chunk 應包含前一個的尾部
            assert len(chunks[1]) > 100

    def test_sentence_split_helper(self) -> None:
        from src.services.rag_service import _split_into_sentences

        text = "First sentence. Second sentence! Third one? 第四句。"
        sentences = _split_into_sentences(text)
        assert len(sentences) >= 3


class TestBGE3EmbeddingFunction:
    def test_class_exists(self) -> None:
        from src.services.rag_service import BGE3EmbeddingFunction

        fn = BGE3EmbeddingFunction()
        assert fn._PREFERRED_MODEL == "BAAI/bge-small-en-v1.5"
        assert fn._FALLBACK_MODEL == "all-MiniLM-L6-v2"

    def test_rag_service_has_embedding_fn(self) -> None:
        from src.services.rag_service import RAGService

        svc = RAGService(persist_dir="/tmp/test_chromadb")
        assert hasattr(svc, "embedding_fn")

    def test_rag_service_has_mmr_search(self) -> None:
        from src.services.rag_service import RAGService

        svc = RAGService()
        assert hasattr(svc, "search_mmr")


# ════════════════════════════════════════════════════════════════
# Weibull 風速分佈
# ════════════════════════════════════════════════════════════════


class TestWeibullModel:
    def test_fit_mle(self) -> None:
        # 生成 Weibull 分佈資料（k=2, c=8）
        from scipy.stats import weibull_min

        from src.models.wind_distribution.weibull_model import WeibullDistributionModel

        np.random.seed(42)
        ws = weibull_min.rvs(2, loc=0, scale=8, size=5000)

        model = WeibullDistributionModel()
        result = model.fit(ws, method="mle")

        assert 1.5 < result.shape_k < 2.5
        assert 7.0 < result.scale_c < 9.0
        assert result.ks_p_value > 0.01  # 擬合良好
        assert result.energy_density_w_m2 > 0
        assert result.sample_count == 5000

    def test_fit_moments(self) -> None:
        from scipy.stats import weibull_min

        from src.models.wind_distribution.weibull_model import WeibullDistributionModel

        np.random.seed(42)
        ws = weibull_min.rvs(2, loc=0, scale=8, size=3000)

        model = WeibullDistributionModel()
        result = model.fit(ws, method="moments")

        assert result.fit_method == "moments"
        assert result.shape_k > 0
        assert result.scale_c > 0

    def test_predict_frequency(self) -> None:
        from scipy.stats import weibull_min

        from src.models.wind_distribution.weibull_model import WeibullDistributionModel

        ws = weibull_min.rvs(2, loc=0, scale=8, size=1000)
        model = WeibullDistributionModel()
        model.fit(ws)

        # 頻率在合理範圍
        freq = model.predict_frequency(8.0)
        assert 0 < freq < 1

    def test_predict_exceedance(self) -> None:
        from scipy.stats import weibull_min

        from src.models.wind_distribution.weibull_model import WeibullDistributionModel

        ws = weibull_min.rvs(2, loc=0, scale=8, size=1000)
        model = WeibullDistributionModel()
        model.fit(ws)

        # 超過 0 m/s 的機率接近 1
        assert model.predict_exceedance(0.1) > 0.9
        # 超過 30 m/s 的機率接近 0
        assert model.predict_exceedance(30.0) < 0.01

    def test_estimate_aep(self) -> None:
        from scipy.stats import weibull_min

        from src.models.wind_distribution.weibull_model import WeibullDistributionModel

        ws = weibull_min.rvs(2, loc=0, scale=8, size=2000)
        model = WeibullDistributionModel()
        model.fit(ws)
        aep = model.estimate_aep()

        assert aep.aep_mwh > 0
        assert 0 < aep.capacity_factor < 1
        assert aep.availability_pct > 0
        assert aep.full_load_hours > 0

    def test_frequency_table(self) -> None:
        from scipy.stats import weibull_min

        from src.models.wind_distribution.weibull_model import WeibullDistributionModel

        ws = weibull_min.rvs(2, loc=0, scale=8, size=1000)
        model = WeibullDistributionModel()
        model.fit(ws)
        table = model.generate_frequency_table()

        assert len(table) > 0
        assert "wind_speed" in table[0]
        assert "probability" in table[0]
        assert "frequency_pct" in table[0]

    def test_too_few_data(self) -> None:
        from src.models.wind_distribution.weibull_model import WeibullDistributionModel

        model = WeibullDistributionModel()
        result = model.fit(np.array([1.0, 2.0]))
        assert result.sample_count == 2  # 不足但不 crash


class TestWeibullSkill:
    def test_import(self) -> None:
        from src.skills.ml.weibull_analysis import WeibullAnalysisSkill

        skill = WeibullAnalysisSkill()
        assert skill.skill_id == "weibull_analysis"

    @pytest.mark.asyncio
    async def test_with_valid_data(self) -> None:
        import pandas as pd
        from scipy.stats import weibull_min

        from src.skills.ml.weibull_analysis import WeibullAnalysisSkill

        np.random.seed(42)
        ws = weibull_min.rvs(2.0, loc=0, scale=8.0, size=2000)
        df = pd.DataFrame({"Wind speed (m/s)_Mean": ws})

        skill = WeibullAnalysisSkill()
        result = await skill.execute(
            SkillInput(parameters={"turbine_id": "WT-01"}, dataframe=df)
        )

        assert result.status == SkillStatus.SUCCESS
        assert "shape_k" in result.data
        assert "scale_c" in result.data
        assert "aep_mwh" in result.data
        assert result.data["aep_mwh"] > 0

    @pytest.mark.asyncio
    async def test_no_wind_col_error(self) -> None:
        import pandas as pd

        from src.skills.ml.weibull_analysis import WeibullAnalysisSkill

        df = pd.DataFrame({"temperature": [20, 21, 22]})
        skill = WeibullAnalysisSkill()
        result = await skill.execute(SkillInput(dataframe=df))
        assert result.status == SkillStatus.ERROR


# ════════════════════════════════════════════════════════════════
# LSTM 時序預測
# ════════════════════════════════════════════════════════════════


class TestLSTMForecaster:
    def test_fit_and_predict(self) -> None:
        from src.models.degradation.lstm_forecaster import LSTMForecaster

        np.random.seed(42)
        # 正弦波 + 噪音
        t = np.linspace(0, 10 * np.pi, 500)
        series = np.sin(t) * 5 + 10 + np.random.normal(0, 0.5, 500)

        forecaster = LSTMForecaster(
            sequence_length=24,
            forecast_horizon=6,
        )
        result = forecaster.fit_and_predict(series, epochs=5)

        assert result.model_type in ("lstm", "ridge_ar")
        assert len(result.predictions) == 6
        assert result.rmse >= 0
        assert result.mae >= 0
        assert result.horizon_steps == 6

    def test_insufficient_data(self) -> None:
        from src.models.degradation.lstm_forecaster import LSTMForecaster

        forecaster = LSTMForecaster(sequence_length=48, forecast_horizon=12)
        result = forecaster.fit_and_predict(np.array([1.0, 2.0, 3.0]))
        assert result.model_type == "insufficient_data"

    def test_predictions_reasonable(self) -> None:
        from src.models.degradation.lstm_forecaster import LSTMForecaster

        np.random.seed(42)
        series = np.random.uniform(5, 15, 300)

        forecaster = LSTMForecaster(sequence_length=20, forecast_horizon=5)
        result = forecaster.fit_and_predict(series, epochs=3)

        if result.predictions:
            # 預測值應在合理範圍內
            preds = np.array(result.predictions)
            assert np.all(preds > -10)
            assert np.all(preds < 50)


class TestLSTMForecastSkill:
    def test_import(self) -> None:
        from src.skills.ml.lstm_forecast import LSTMForecastSkill

        skill = LSTMForecastSkill()
        assert skill.skill_id == "lstm_forecast"
        assert skill.display_name == "LSTM 時序預測"

    @pytest.mark.asyncio
    async def test_with_valid_data(self) -> None:
        import pandas as pd

        from src.skills.ml.lstm_forecast import LSTMForecastSkill

        np.random.seed(42)
        n = 300
        df = pd.DataFrame({
            "Wind speed (m/s)_Mean": np.random.uniform(3, 20, n),
        })

        skill = LSTMForecastSkill()
        result = await skill.execute(
            SkillInput(
                parameters={
                    "turbine_id": "WT-01",
                    "target": "wind_speed",
                    "sequence_length": 20,
                    "forecast_horizon": 5,
                    "epochs": 3,
                },
                dataframe=df,
            )
        )

        assert result.status == SkillStatus.SUCCESS
        assert "predictions" in result.data
        assert len(result.data["predictions"]) == 5
        assert result.data["model_type"] in ("lstm", "ridge_ar")

    @pytest.mark.asyncio
    async def test_insufficient_data(self) -> None:
        import pandas as pd

        from src.skills.ml.lstm_forecast import LSTMForecastSkill

        df = pd.DataFrame({"Wind speed (m/s)_Mean": [5.0, 6.0, 7.0]})
        skill = LSTMForecastSkill()
        result = await skill.execute(
            SkillInput(
                parameters={"sequence_length": 48, "forecast_horizon": 12},
                dataframe=df,
            )
        )
        assert result.status == SkillStatus.ERROR


# ════════════════════════════════════════════════════════════════
# Skill Registry 自動發現
# ════════════════════════════════════════════════════════════════


class TestNewSkillsDiscovery:
    def test_all_new_skills_discoverable(self) -> None:
        from src.skills.registry import SkillRegistry

        registry = SkillRegistry()
        count = registry.auto_discover()
        assert count > 0
        assert registry.has("weibull_analysis")
        assert registry.has("lstm_forecast")
        assert registry.has("anomaly_detection")
        assert registry.has("report_generator")
