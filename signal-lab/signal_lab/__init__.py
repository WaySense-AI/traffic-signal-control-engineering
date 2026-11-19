"""Teaching models for the traffic signal control book."""

from .cycle import PiecewiseLinearCycleModel, allocate_green_by_ratio
from .coordination import (
    CorridorSegment,
    common_cycle_s,
    cumulative_travel_times_s,
    downstream_offset_s,
    green_band_width_s,
    green_band_width_sweep_s,
)
from .control import (
    BatchStatus,
    CommandEvent,
    CommandLedger,
    CommandStatus,
    ControlCommand,
    StateVersion,
    accept_state_version,
    aggregate_batch_status,
)
from .demand import (
    MovementDemand,
    critical_flow_ratio,
    degree_of_saturation,
    lane_capacity_vph,
    stage_flow_ratios,
)
from .mapping import (
    FlowAggregate,
    LaneObservation,
    aggregate_lane_movements,
)
from .model import (
    InvariantViolation,
    SignalPlan,
    SignalStage,
    repair_min_green,
    validate_plan,
)
from .quality import DetectionPoint, QualityFlag, assess_series, exponential_moving_average
from .queueing import QueueStep, queue_clearance_cycles, simulate_queue
from .optimizer import (
    AdaptiveDecision,
    AutomationReadiness,
    WebsterResult,
    apply_green_proportions,
    blend_target_ratios,
    evaluate_adaptive_change,
    stage_green_ratios,
    webster_cycle,
)
from .evaluation import (
    MovementEvaluation,
    SiteEvaluation,
    difference_in_differences,
    flow_weighted_speed,
)
from .schedule import DemandProfile, DemandSegment, profile_distance, segment_demand_profiles
from .signals import ControlMode, SignalState, normalize_control_mode
from .timeline import (
    CircularInterval,
    StageWindow,
    apply_offsets,
    green_at,
    iter_stage_seconds,
    normalize_second,
    stage_at,
    stage_windows,
)
from .windows import CountEvent, WindowAggregate, aggregate_count_windows

__all__ = [
    "InvariantViolation",
    "FlowAggregate",
    "AutomationReadiness",
    "AdaptiveDecision",
    "BatchStatus",
    "CommandEvent",
    "CommandLedger",
    "CommandStatus",
    "ControlMode",
    "ControlCommand",
    "CountEvent",
    "CircularInterval",
    "CorridorSegment",
    "DemandProfile",
    "DemandSegment",
    "DetectionPoint",
    "LaneObservation",
    "MovementDemand",
    "MovementEvaluation",
    "PiecewiseLinearCycleModel",
    "profile_distance",
    "QualityFlag",
    "QueueStep",
    "SignalPlan",
    "SignalStage",
    "SignalState",
    "StateVersion",
    "StageWindow",
    "SiteEvaluation",
    "WebsterResult",
    "allocate_green_by_ratio",
    "accept_state_version",
    "aggregate_batch_status",
    "aggregate_lane_movements",
    "aggregate_count_windows",
    "apply_green_proportions",
    "apply_offsets",
    "assess_series",
    "blend_target_ratios",
    "common_cycle_s",
    "cumulative_travel_times_s",
    "critical_flow_ratio",
    "degree_of_saturation",
    "difference_in_differences",
    "downstream_offset_s",
    "exponential_moving_average",
    "evaluate_adaptive_change",
    "flow_weighted_speed",
    "green_band_width_s",
    "green_band_width_sweep_s",
    "green_at",
    "iter_stage_seconds",
    "normalize_control_mode",
    "normalize_second",
    "lane_capacity_vph",
    "stage_green_ratios",
    "webster_cycle",
    "repair_min_green",
    "queue_clearance_cycles",
    "segment_demand_profiles",
    "simulate_queue",
    "stage_flow_ratios",
    "stage_at",
    "stage_windows",
    "validate_plan",
    "WindowAggregate",
]

