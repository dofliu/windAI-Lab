"""代理管理服務。

封裝代理狀態管理的業務邏輯，提供代理查詢、狀態更新、
任務指派等功能，作為 API 層與底層 registry 之間的橋樑。
"""

from __future__ import annotations

from datetime import datetime

from src.api.agent_registry import (
    get_agent,
    get_all_agents,
    reset_all_agents,
    update_agent_status,
)
from src.api.models import AgentModel, AgentStatus, AgentTier
from src.core.constants import TASK_ID_PREFIX
from src.core.exceptions import AgentBusyError, AgentNotFoundError
from src.utils.logger import get_logger

logger = get_logger("services.agent")


def get_agent_or_raise(agent_id: str) -> AgentModel:
    """取得代理，若不存在則拋出例外。

    Args:
        agent_id: 代理唯一識別碼。

    Returns:
        代理資料模型。

    Raises:
        AgentNotFoundError: 代理不存在。
    """
    agent = get_agent(agent_id)
    if agent is None:
        raise AgentNotFoundError(agent_id)
    return agent


def assign_task(agent_id: str, task_description: str) -> str:
    """指派任務給指定代理。

    Args:
        agent_id: 代理唯一識別碼。
        task_description: 任務描述。

    Returns:
        任務 ID。

    Raises:
        AgentNotFoundError: 代理不存在。
        AgentBusyError: 代理正在執行其他任務。
    """
    agent = get_agent_or_raise(agent_id)

    if agent.status == AgentStatus.WORKING:
        raise AgentBusyError(agent_id)

    # 生成任務 ID：WLAB-YYYYMMDD-{agent_id}
    today = datetime.now().strftime("%Y%m%d")
    task_id = f"{TASK_ID_PREFIX}-{today}-{agent_id}"

    update_agent_status(
        agent_id,
        status=AgentStatus.WORKING,
        current_task=task_description,
        progress=0.0,
    )

    logger.info(f"任務 {task_id} 已指派給 {agent.display_name}：{task_description}")
    return task_id


def list_agents_by_tier(tier: AgentTier) -> list[AgentModel]:
    """依層級篩選代理。

    Args:
        tier: 代理層級。

    Returns:
        指定層級的代理列表。
    """
    return [a for a in get_all_agents() if a.tier == tier]


def list_agents_by_status(status: AgentStatus) -> list[AgentModel]:
    """依狀態篩選代理。

    Args:
        status: 代理狀態。

    Returns:
        指定狀態的代理列表。
    """
    return [a for a in get_all_agents() if a.status == status]


def reset_all() -> int:
    """重設所有代理至待命狀態。

    Returns:
        重設的代理數量。
    """
    agents = get_all_agents()
    count = len(agents)
    reset_all_agents()
    logger.info(f"已重設 {count} 個代理至待命狀態")
    return count
