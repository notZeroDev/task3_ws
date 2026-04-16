#!/usr/bin/env python3
"""Rule evaluation node for behavior-based violation decisions."""

from typing import Dict, Tuple

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from smart_exam_protocoring_msgs.msg import ViolationEvent
from smart_exam_protocoring_msgs.srv import CheckViolation


class RuleEvaluationNode(Node):
    """Apply configurable rules to behavior states and publish violations."""

    def __init__(self):
        super().__init__("rule_evaluation_node")

        self.declare_parameter(
            "violation_rules",
            [
                "PROHIBITED_OBJECT:high",
                "MULTIPLE_FACES:high",
                "LOOKING_AWAY:medium",
                "TOO_FAR:medium",
                "TOO_CLOSE:low",
                "LOW_ATTENTION:low",
            ],
        )

        self.rule_map = self._parse_rules(
            self.get_parameter("violation_rules").value
        )

        self.subscription = self.create_subscription(
            String, "/behavior_state", self.behavior_callback, 10
        )
        self.publisher = self.create_publisher(ViolationEvent, "/violation_event", 10)
        self.service = self.create_service(
            CheckViolation, "/check_violation", self.check_violation_callback
        )

        self.get_logger().info("Rule evaluation node initialized")

    def _parse_rules(self, raw_rules) -> Dict[str, str]:
        parsed = {}
        for item in raw_rules:
            if ":" not in item:
                continue
            key, value = item.split(":", 1)
            parsed[key.strip().upper()] = value.strip().lower()
        return parsed

    def _evaluate_state(self, behavior_state: str) -> Tuple[bool, str, str]:
        if behavior_state == "NORMAL":
            return False, "none", "No violation"

        tokens = [token.strip().upper() for token in behavior_state.split("|") if token]
        severities = []
        for token in tokens:
            if token in self.rule_map:
                severities.append(self.rule_map[token])

        severity_rank = {"none": 0, "low": 1, "medium": 2, "high": 3}
        final_severity = "none"
        for sev in severities:
            if severity_rank.get(sev, 0) > severity_rank.get(final_severity, 0):
                final_severity = sev

        if final_severity == "none":
            return False, "none", "No matching violation rule"
        return True, final_severity, behavior_state

    def behavior_callback(self, msg: String) -> None:
        is_violation, severity, reason = self._evaluate_state(msg.data)

        event = ViolationEvent()
        event.header.stamp = self.get_clock().now().to_msg()
        event.header.frame_id = "rule_evaluation"
        event.is_violation = is_violation
        event.severity = severity
        event.reason = reason
        self.publisher.publish(event)

    def check_violation_callback(self, request, response):
        is_violation, severity, reason = self._evaluate_state(request.behavior_state)
        response.is_violation = is_violation
        response.severity = severity
        response.reason = reason
        return response


def main(args=None):
    rclpy.init(args=args)
    node = RuleEvaluationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down rule evaluation node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
