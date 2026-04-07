"""警報關聯分析技能 — 找出警報碼的共現模式與因果關係。

分析方法：
1. 時間窗口內的警報共現頻率（co-occurrence matrix）
2. 頻繁項目集挖掘（Apriori-like）
3. 時序因果分析：A 發生後 B 是否高機率跟隨
4. 產出警報關聯圖與維護建議
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from src.skills.base import BaseSkill, ProgressCallback, SkillInput, SkillOutput, SkillStatus
from src.utils.logger import get_logger

logger = get_logger("skill.alarm_correlation")


class AlarmCorrelationSkill(BaseSkill):
    """警報關聯分析 — 挖掘警報碼共現模式與時序因果。"""

    skill_id = "alarm_correlation"
    display_name = "警報關聯分析"
    description = "分析警報碼的共現模式、頻繁組合與時序因果關係"
    version = "1.0.0"

    async def execute(
        self,
        inp: SkillInput,
        progress_cb: ProgressCallback = None,
    ) -> SkillOutput:
        """執行警報關聯分析。

        Parameters (inp.parameters):
            alarm_code_col: str — 警報碼欄位名（預設自動偵測）
            timestamp_col: str — 時間戳記欄位（預設用 index）
            window_minutes: int — 共現時間窗口（預設 60 分鐘）
            min_support: int — 最低出現次數門檻（預設 3）
        """
        df = inp.dataframe
        if df is None:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["未收到 DataFrame 輸入"],
            )

        window_min = inp.parameters.get("window_minutes", 60)
        min_support = inp.parameters.get("min_support", 3)

        if progress_cb:
            await progress_cb(0.1, "識別警報欄位...")

        alarm_col = inp.parameters.get("alarm_code_col") or self._find_alarm_col(df)
        if not alarm_col:
            return SkillOutput(
                status=SkillStatus.ERROR,
                errors=["無法識別警報碼欄位，請指定 alarm_code_col 參數"],
            )

        if progress_cb:
            await progress_cb(0.3, "計算警報頻率統計...")

        result = self._analyze(df, alarm_col, window_min, min_support)

        if progress_cb:
            await progress_cb(1.0, f"分析完成 — {result['unique_alarms']} 種警報碼")

        return SkillOutput(
            status=SkillStatus.SUCCESS,
            data=result,
            dataframe=df,
            summary=(
                f"警報關聯分析：{result['unique_alarms']} 種警報, "
                f"{result['total_events']} 筆事件, "
                f"{len(result['frequent_pairs'])} 組頻繁共現"
            ),
        )

    @staticmethod
    def _find_alarm_col(df: pd.DataFrame) -> str | None:
        """自動偵測警報碼欄位。"""
        candidates = [
            "alarm_code",
            "alarm",
            "fault_code",
            "error_code",
            "event_code",
            "status_code",
        ]
        cols_lower = {c.lower().strip(): c for c in df.columns}
        for cand in candidates:
            if cand in cols_lower:
                return cols_lower[cand]
        # 找含有 "alarm" 或 "fault" 的欄位
        for col_lower, col_orig in cols_lower.items():
            if "alarm" in col_lower or "fault" in col_lower or "error" in col_lower:
                return col_orig
        return None

    def _analyze(
        self,
        df: pd.DataFrame,
        alarm_col: str,
        window_min: int,
        min_support: int,
    ) -> dict[str, Any]:
        """核心分析邏輯。"""
        alarms = df[alarm_col].dropna()
        total_events = len(alarms)
        unique_alarms = int(alarms.nunique())

        # 1. 頻率統計
        freq = alarms.value_counts().to_dict()
        top_alarms = [
            {
                "code": str(code),
                "count": int(cnt),
                "ratio_pct": round(cnt / max(total_events, 1) * 100, 1),
            }
            for code, cnt in list(freq.items())[:20]
        ]

        # 2. 時間窗口共現分析
        frequent_pairs: list[dict[str, Any]] = []
        temporal_patterns: list[dict[str, Any]] = []

        if isinstance(df.index, pd.DatetimeIndex) and total_events > 0:
            window = pd.Timedelta(minutes=window_min)
            pair_counter: Counter = Counter()
            sequence_counter: Counter = Counter()

            # 按時間排序
            sorted_idx = alarms.sort_index().index
            alarm_values = alarms.loc[sorted_idx]

            # 滑動窗口找共現
            for i in range(len(sorted_idx)):
                t_i = sorted_idx[i]
                code_i = str(alarm_values.iloc[i])

                for j in range(i + 1, len(sorted_idx)):
                    t_j = sorted_idx[j]
                    if t_j - t_i > window:
                        break
                    code_j = str(alarm_values.iloc[j])

                    if code_i != code_j:
                        pair = tuple(sorted([code_i, code_j]))
                        pair_counter[pair] += 1
                        # 時序因果：i 先發生，j 後發生
                        sequence_counter[(code_i, code_j)] += 1

                # 限制搜索範圍避免 O(n²) 太慢
                if i > 5000:
                    break

            # 頻繁共現對
            frequent_pairs = [
                {"pair": list(pair), "count": cnt, "support": cnt}
                for pair, cnt in pair_counter.most_common(20)
                if cnt >= min_support
            ]

            # 時序因果模式（A → B 的條件機率）
            for (a, b), cnt in sequence_counter.most_common(20):
                a_total = freq.get(a, freq.get(int(a) if a.isdigit() else a, 0))
                if isinstance(a_total, int) and a_total > 0 and cnt >= min_support:
                    conditional_prob = cnt / a_total
                    if conditional_prob > 0.1:
                        temporal_patterns.append(
                            {
                                "antecedent": a,
                                "consequent": b,
                                "count": cnt,
                                "conditional_probability": round(conditional_prob, 3),
                            }
                        )

        # 3. 時段分布
        hourly_dist: dict[str, int] = {}
        if hasattr(df.index, "hour"):
            hourly = alarms.groupby(df.index.hour).count()
            hourly_dist = {str(h): int(c) for h, c in hourly.items()}

        return {
            "unique_alarms": unique_alarms,
            "total_events": total_events,
            "top_alarms": top_alarms,
            "frequent_pairs": frequent_pairs,
            "temporal_patterns": temporal_patterns[:10],
            "hourly_distribution": hourly_dist,
            "window_minutes": window_min,
            "min_support": min_support,
        }
