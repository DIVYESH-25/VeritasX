"""
Forensic Result Aggregation Engine
"""

import logging
from typing import List
from backend.schemas.models import ModuleResult, AggregatedResult, ModuleStatus

logger = logging.getLogger("veritasx.aggregation")


class ForensicAggregator:
    """
    Synthesizes individual forensic module outputs into an aggregated forensic verdict.
    Supports weighted scoring, confidence estimation, and risk classification.
    """

    def aggregate(self, results: List[ModuleResult]) -> AggregatedResult:
        """
        Processes module results and calculates overall authenticity score and verdict.
        """
        if not results:
            return AggregatedResult(
                overall_score=0.0,
                overall_confidence=0.0,
                verdict="UNCERTAIN",
                risk_level="LOW",
                summary="No forensic module results available to evaluate.",
                active_module_count=0,
                successful_module_count=0,
            )

        active_count = len(results)
        successful_results = [r for r in results if r.status == ModuleStatus.SUCCESS]
        successful_count = len(successful_results)

        if successful_count == 0:
            return AggregatedResult(
                overall_score=0.0,
                overall_confidence=0.0,
                verdict="UNCERTAIN",
                risk_level="HIGH",
                summary="All forensic modules encountered execution errors during analysis.",
                active_module_count=active_count,
                successful_module_count=0,
            )

        # Weighted calculation based on confidence
        total_weight = sum(r.confidence for r in successful_results)
        if total_weight > 0:
            weighted_score = sum(r.score * r.confidence for r in successful_results) / total_weight
            overall_confidence = sum(r.confidence for r in successful_results) / successful_count
        else:
            weighted_score = sum(r.score for r in successful_results) / successful_count
            overall_confidence = 0.5  # Neutral default when module confidence is unweighted

        weighted_score = round(min(max(weighted_score, 0.0), 1.0), 4)
        overall_confidence = round(min(max(overall_confidence, 0.0), 1.0), 4)

        # Categorical Verdict Determination
        module_list = ", ".join(
            m.module for m in successful_results
        )
        if weighted_score >= 0.70:
            verdict = "AI_GENERATED"
            risk_level = "CRITICAL" if weighted_score >= 0.88 else "HIGH"
            summary = (
                f"High confidence detection of AI manipulation ({round(weighted_score * 100, 1)}% synthetic likelihood) "
                f"across {successful_count}/{active_count} forensic engines ({module_list}). "
                f"This assessment is based on the currently implemented modules: "
                f"Metadata Analysis, Error Level Analysis, and Frequency Analysis. "
                f"Additional forensic modules will be incorporated in future versions. "
                f"This is not a final AI detection result."
            )
        elif weighted_score <= 0.30:
            verdict = "REAL"
            risk_level = "LOW"
            summary = (
                f"Media exhibits organic sensor & compression characteristics consistent with authentic capture "
                f"({round((1 - weighted_score) * 100, 1)}% authenticity likelihood). "
                f"This assessment is based on the currently implemented modules: "
                f"Metadata Analysis, Error Level Analysis, and Frequency Analysis. "
                f"Additional forensic modules will be incorporated in future versions. "
                f"This is not a final AI detection result."
            )
        else:
            verdict = "UNCERTAIN"
            risk_level = "MEDIUM"
            summary = (
                f"Inconclusive forensic markers ({round(weighted_score * 100, 1)}% synthetic likelihood). "
                f"This assessment is based on the currently implemented modules: "
                f"Metadata Analysis, Error Level Analysis, and Frequency Analysis. "
                f"Additional forensic modules will be incorporated in future versions. "
                f"This is not a final AI detection result."
            )

        return AggregatedResult(
            overall_score=weighted_score,
            overall_confidence=overall_confidence,
            verdict=verdict,
            risk_level=risk_level,
            summary=summary,
            active_module_count=active_count,
            successful_module_count=successful_count,
        )
