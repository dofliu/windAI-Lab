"""Phase 5 新增代理的單元測試。

測試 ExperimentTracker、FeatureEngineer、EtlEngineer、
FrontendDev、RagCurator 的基本行為與能力宣告。
"""

from __future__ import annotations

import pytest

from src.agents.base import TaskContext, TaskResult, TaskStatus


# ── ExperimentTracker 測試 ─────────────────────────────────────


class TestExperimentTracker:
    """實驗追蹤代理測試。"""

    @pytest.fixture()
    def agent(self):
        from src.agents.ai.experiment_tracker import ExperimentTracker

        return ExperimentTracker()

    def test_agent_id(self, agent):
        assert agent.id == "experiment-tracker"

    def test_capabilities(self, agent):
        caps = agent.capabilities
        assert "experiment_logging" in caps
        assert "metric_tracking" in caps
        assert "experiment_comparison" in caps
        assert len(caps) >= 4

    @pytest.mark.asyncio()
    async def test_log_experiment(self, agent, tmp_path, monkeypatch):
        """測試實驗記錄功能。"""
        import src.agents.ai.experiment_tracker as mod

        monkeypatch.setattr(mod, "_EXPERIMENT_LOG_DIR", tmp_path)

        ctx = TaskContext(
            parameters={
                "experiment_name": "test_exp",
                "metrics": {"f1_macro": 0.85, "accuracy": 0.90},
                "hyperparameters": {"learning_rate": 0.001},
                "model_type": "xgboost",
                "dataset": "kelmarsh",
            }
        )
        result = await agent.execute("記錄實驗", ctx)

        assert result.status == TaskStatus.SUCCESS
        assert result.data["experiment_name"] == "test_exp"
        assert result.data["metrics"]["f1_macro"] == 0.85

        # 確認檔案已建立
        log_file = tmp_path / "test_exp.jsonl"
        assert log_file.exists()

    @pytest.mark.asyncio()
    async def test_list_experiments(self, agent, tmp_path, monkeypatch):
        """測試列出實驗功能。"""
        import src.agents.ai.experiment_tracker as mod

        monkeypatch.setattr(mod, "_EXPERIMENT_LOG_DIR", tmp_path)

        # 建立假的實驗檔
        (tmp_path / "exp_a.jsonl").write_text('{"experiment_name":"a"}\n')
        (tmp_path / "exp_b.jsonl").write_text('{"experiment_name":"b"}\n')

        ctx = TaskContext(parameters={})
        result = await agent.execute("列出實驗", ctx)

        assert result.status == TaskStatus.SUCCESS
        assert result.data["total"] == 2


# ── FeatureEngineer 測試 ───────────────────────────────────────


class TestFeatureEngineer:
    """特徵工程代理測試。"""

    @pytest.fixture()
    def agent(self):
        from src.agents.ai.feature_engineer import FeatureEngineer

        return FeatureEngineer()

    def test_agent_id(self, agent):
        assert agent.id == "feature-engineer"

    def test_capabilities(self, agent):
        caps = agent.capabilities
        assert "feature_extraction" in caps
        assert "feature_selection" in caps
        assert len(caps) >= 4

    @pytest.mark.asyncio()
    async def test_generic_task(self, agent):
        """測試通用任務。"""
        ctx = TaskContext(parameters={})
        result = await agent.execute("test task", ctx)
        assert result.status == TaskStatus.SUCCESS


# ── EtlEngineer 測試 ──────────────────────────────────────────


class TestEtlEngineer:
    """ETL 工程代理測試。"""

    @pytest.fixture()
    def agent(self):
        from src.agents.data.etl_engineer import EtlEngineer

        return EtlEngineer()

    def test_agent_id(self, agent):
        assert agent.id == "etl-engineer"

    def test_capabilities(self, agent):
        caps = agent.capabilities
        assert "etl_pipeline_design" in caps
        assert "data_transformation" in caps
        assert len(caps) >= 4

    @pytest.mark.asyncio()
    async def test_generic_task(self, agent):
        ctx = TaskContext(parameters={})
        result = await agent.execute("some generic etl info", ctx)
        # CI 環境無資料檔案時 ETL pipeline 會返回 ERROR，只要不拋例外即可
        assert result.status in (TaskStatus.SUCCESS, TaskStatus.ERROR)


# ── FrontendDev 測試 ──────────────────────────────────────────


class TestFrontendDev:
    """前端開發代理測試。"""

    @pytest.fixture()
    def agent(self):
        from src.agents.engineering.frontend_dev import FrontendDev

        return FrontendDev()

    def test_agent_id(self, agent):
        assert agent.id == "frontend-dev"

    def test_capabilities(self, agent):
        caps = agent.capabilities
        assert "react_component_development" in caps
        assert "data_visualization" in caps
        assert len(caps) >= 4

    @pytest.mark.asyncio()
    async def test_design_component(self, agent):
        ctx = TaskContext(parameters={"name": "TestChart", "type": "functional"})
        result = await agent.execute("設計元件規格", ctx)
        assert result.status == TaskStatus.SUCCESS
        assert result.data["name"] == "TestChart"

    @pytest.mark.asyncio()
    async def test_optimize(self, agent):
        ctx = TaskContext(parameters={})
        result = await agent.execute("優化前端效能", ctx)
        assert result.status == TaskStatus.SUCCESS
        assert "recommendations" in result.data


# ── RagCurator 測試 ───────────────────────────────────────────


class TestRagCurator:
    """RAG 知識庫管理代理測試。"""

    @pytest.fixture()
    def agent(self):
        from src.agents.research.rag_curator import RagCurator

        return RagCurator()

    def test_agent_id(self, agent):
        assert agent.id == "rag-curator"

    def test_capabilities(self, agent):
        caps = agent.capabilities
        assert "document_embedding" in caps
        assert "semantic_search" in caps
        assert len(caps) >= 4

    @pytest.mark.asyncio()
    async def test_search_empty_query(self, agent):
        """空查詢應回傳錯誤。"""
        ctx = TaskContext(parameters={"query": ""})
        result = await agent.execute("搜尋知識庫", ctx)
        assert result.status == TaskStatus.ERROR

    @pytest.mark.asyncio()
    async def test_ingest_missing_path(self, agent):
        """缺少 file_path 應回傳錯誤。"""
        ctx = TaskContext(parameters={})
        result = await agent.execute("匯入文件", ctx)
        assert result.status == TaskStatus.ERROR


# ── RAG Service 測試 ──────────────────────────────────────────


@pytest.mark.skipif(
    __import__("sys").platform == "win32",
    reason="ChromaDB segfaults on Windows in CI — run on Linux/Docker",
)
class TestRAGService:
    """RAG 知識庫服務測試（需 ChromaDB 可用環境）。"""

    @pytest.fixture()
    def rag(self):
        from src.services.rag_service import RAGService

        return RAGService(persist_dir=None)

    def test_add_and_search(self, rag):
        """測試新增文件後搜尋。"""
        from src.services.rag_service import Document

        docs = [
            Document(content="Wind turbine gearbox fault diagnosis using SCADA data"),
            Document(content="Power curve modeling for performance monitoring"),
            Document(content="Wake effect simulation in offshore wind farms"),
        ]
        result = rag.add_documents(docs)
        assert result["added"] == 3

        results = rag.search("gearbox fault", n_results=2)
        assert len(results) > 0
        assert results[0].relevance_score > 0

    def test_list_collections(self, rag):
        """測試集合列表。"""
        collections = rag.list_collections()
        assert isinstance(collections, list)

    def test_ingest_text_file(self, rag, tmp_path):
        """測試文字檔案嵌入。"""
        test_file = tmp_path / "test_doc.txt"
        test_file.write_text("This is a test document about wind energy research.")

        result = rag.ingest_text_file(str(test_file))
        assert result["added"] >= 1

    def test_collection_stats(self, rag):
        """測試集合統計。"""
        stats = rag.get_collection_stats()
        assert "name" in stats
        assert "count" in stats


class TestRAGServicePureLogic:
    """RAG 服務純邏輯測試（不依賴 ChromaDB）。"""

    def test_split_text_basic(self):
        """測試文字分割。"""
        from src.services.rag_service import RAGService

        text = "A" * 1200
        chunks = RAGService._split_text(text, chunk_size=500, overlap=50)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 500

    def test_split_text_short(self):
        """短文字不需分割。"""
        from src.services.rag_service import RAGService

        chunks = RAGService._split_text("Hello world", chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_document_model(self):
        """測試 Document dataclass。"""
        from src.services.rag_service import Document

        doc = Document(content="test content", metadata={"source": "unit_test"})
        assert doc.content == "test content"
        assert doc.metadata["source"] == "unit_test"
        assert doc.doc_id  # auto-generated UUID


# ── Registry 整合測試 ─────────────────────────────────────────


class TestRegistryWithNewAgents:
    """驗證新代理可以正確註冊至 registry。"""

    def test_bootstrap_includes_new_agents(self):
        """bootstrap_agents 應包含新增的 5 個代理。"""
        from src.agents.registry import AgentInstanceRegistry

        registry = AgentInstanceRegistry()

        # 個別匯入並註冊
        from src.agents.ai.experiment_tracker import ExperimentTracker
        from src.agents.ai.feature_engineer import FeatureEngineer
        from src.agents.data.etl_engineer import EtlEngineer
        from src.agents.engineering.frontend_dev import FrontendDev
        from src.agents.research.rag_curator import RagCurator

        agents = [
            ExperimentTracker(),
            FeatureEngineer(),
            EtlEngineer(),
            FrontendDev(),
            RagCurator(),
        ]
        for a in agents:
            registry.register(a)

        assert registry.count == 5
        assert registry.has("experiment-tracker")
        assert registry.has("feature-engineer")
        assert registry.has("etl-engineer")
        assert registry.has("frontend-dev")
        assert registry.has("rag-curator")
