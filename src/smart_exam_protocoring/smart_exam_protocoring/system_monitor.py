#!/usr/bin/env python3
"""System monitor node for observing end-to-end topic health and content."""

from collections import defaultdict

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, String
from sensor_msgs.msg import Image

from smart_exam_protocoring_msgs.msg import (
    AlertStatus,
    DetectedObjectArray,
    FaceData,
    ViolationEvent,
)

# ANSI color codes for terminal output
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_CYAN   = "\033[96m"
_GREY   = "\033[90m"


def _severity_color(severity: str) -> str:
    return {
        "high":   _RED,
        "medium": _YELLOW,
        "low":    _CYAN,
    }.get(severity.lower(), _RESET)


class SystemMonitorNode(Node):
    """Subscribe to core topics and report both pipeline health and message content."""

    def __init__(self):
        super().__init__("system_monitor_node")

        self.declare_parameter("monitor_period_sec", 2.0)
        self.monitor_period_sec = float(self.get_parameter("monitor_period_sec").value)

        # Message counters (for the health summary line)
        self.counts = defaultdict(int)

        # Latest content snapshots for the three key downstream topics
        self.latest_behavior: str = "—"
        self.latest_violation: str = "—"
        self.latest_alert: str = "—"
        self.latest_violation_active: bool = False
        self.latest_alert_active: bool = False
        self.latest_alert_severity: str = "none"

        # ── Subscriptions ──────────────────────────────────────────────────────
        self.create_subscription(Image,              "/camera_frames", self._hit("/camera_frames"), 10)
        self.create_subscription(FaceData,           "/face_data",     self._hit("/face_data"),     10)
        self.create_subscription(DetectedObjectArray,"/object_data",   self._hit("/object_data"),   10)
        self.create_subscription(Float32,            "/depth_data",    self._hit("/depth_data"),    10)

        self.create_subscription(String,        "/behavior_state",  self._behavior_cb,   10)
        self.create_subscription(ViolationEvent,"/violation_event", self._violation_cb,  10)
        self.create_subscription(AlertStatus,   "/alert_status",    self._alert_cb,      10)

        self.timer = self.create_timer(self.monitor_period_sec, self.report_status)
        self.get_logger().info("System monitor node initialized")

    # ── Generic message counter ────────────────────────────────────────────────

    def _hit(self, topic):
        def cb(_msg):
            self.counts[topic] += 1
        return cb

    # ── Content callbacks ──────────────────────────────────────────────────────

    def _behavior_cb(self, msg: String) -> None:
        self.counts["/behavior_state"] += 1
        self.latest_behavior = msg.data

    def _violation_cb(self, msg: ViolationEvent) -> None:
        self.counts["/violation_event"] += 1
        self.latest_violation_active = msg.is_violation
        self.latest_violation = (
            f"violation={msg.is_violation}  severity={msg.severity}  reason={msg.reason}"
        )

    def _alert_cb(self, msg: AlertStatus) -> None:
        self.counts["/alert_status"] += 1
        self.latest_alert_active = msg.active
        self.latest_alert_severity = msg.severity
        self.latest_alert = f"active={msg.active}  severity={msg.severity}  msg=\"{msg.message}\""

    # ── Periodic report ────────────────────────────────────────────────────────

    def report_status(self):
        sensor_topics = [
            "/camera_frames",
            "/face_data",
            "/object_data",
            "/depth_data",
        ]

        # ── Health summary line ────────────────────────────────────────────────
        parts = [f"{t.split('/')[-1]}:{self.counts.get(t, 0)}" for t in sensor_topics]
        downstream = (
            f"behavior:{self.counts.get('/behavior_state', 0)}  "
            f"violation:{self.counts.get('/violation_event', 0)}  "
            f"alert:{self.counts.get('/alert_status', 0)}"
        )
        self.get_logger().info(
            f"{_GREY}[sensors] {' | '.join(parts)}{_RESET}"
        )

        # ── Behavior state ─────────────────────────────────────────────────────
        if self.latest_behavior == "NORMAL":
            bcolor = _GREEN
        elif self.latest_behavior == "—":
            bcolor = _GREY
        else:
            bcolor = _YELLOW

        self.get_logger().info(
            f"{_BOLD}[behavior_state  ]{_RESET}  {bcolor}{self.latest_behavior}{_RESET}"
        )

        # ── Violation event ────────────────────────────────────────────────────
        vcolor = _RED if self.latest_violation_active else _GREEN
        self.get_logger().info(
            f"{_BOLD}[violation_event ]{_RESET}  {vcolor}{self.latest_violation}{_RESET}"
        )

        # ── Alert status ───────────────────────────────────────────────────────
        acolor = _severity_color(self.latest_alert_severity) if self.latest_alert_active else _GREEN
        self.get_logger().info(
            f"{_BOLD}[alert_status    ]{_RESET}  {acolor}{self.latest_alert}{_RESET}"
        )

        self.get_logger().info(f"{_GREY}{'─' * 60}{_RESET}")

        self.counts.clear()


def main(args=None):
    rclpy.init(args=args)
    node = SystemMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down system monitor node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
