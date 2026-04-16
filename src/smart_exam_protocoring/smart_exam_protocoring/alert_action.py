#!/usr/bin/env python3
"""Alert action node handling violation events and alert execution."""

import time

import rclpy
from rclpy.action import ActionClient, ActionServer
from rclpy.node import Node

from smart_exam_protocoring_msgs.action import AlertAction
from smart_exam_protocoring_msgs.msg import AlertStatus, ViolationEvent


class AlertActionNode(Node):
    """Execute alert actions and publish resulting alert status."""

    def __init__(self):
        super().__init__("alert_action_node")

        self.declare_parameter("alert_level", "medium")
        self.alert_level = str(self.get_parameter("alert_level").value).lower()

        self.subscription = self.create_subscription(
            ViolationEvent, "/violation_event", self.violation_callback, 10
        )
        self.publisher = self.create_publisher(AlertStatus, "/alert_status", 10)

        self.action_server = ActionServer(
            self, AlertAction, "/alert_action", self.execute_callback
        )
        self.action_client = ActionClient(self, AlertAction, "/alert_action")

        self.get_logger().info("Alert action node initialized")

    def violation_callback(self, msg: ViolationEvent) -> None:
        if not msg.is_violation:
            status = AlertStatus()
            status.header.stamp = self.get_clock().now().to_msg()
            status.header.frame_id = "alert_action"
            status.active = False
            status.severity = "none"
            status.message = "No active violation"
            self.publisher.publish(status)
            return

        if not self.action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().error("Alert action server not available")
            return

        goal = AlertAction.Goal()
        goal.severity = msg.severity
        goal.message = msg.reason
        self.action_client.send_goal_async(goal)

    def execute_callback(self, goal_handle):
        severity = goal_handle.request.severity
        message = goal_handle.request.message

        feedback = AlertAction.Feedback()
        feedback.stage = "received"
        goal_handle.publish_feedback(feedback)

        time.sleep(0.05)
        feedback.stage = "dispatching"
        goal_handle.publish_feedback(feedback)

        effective_level = self._effective_severity(severity)
        alert_text = f"[{effective_level.upper()}] Exam violation: {message}"

        status = AlertStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = "alert_action"
        status.active = True
        status.severity = effective_level
        status.message = alert_text
        self.publisher.publish(status)

        result = AlertAction.Result()
        result.success = True
        result.dispatched_alert = alert_text

        goal_handle.succeed()
        return result

    def _effective_severity(self, incoming_severity: str) -> str:
        rank = {"low": 1, "medium": 2, "high": 3}
        incoming = incoming_severity.lower()
        configured = self.alert_level.lower()
        if rank.get(incoming, 0) >= rank.get(configured, 0):
            return incoming
        return configured

    def destroy_node(self):
        self.action_server.destroy()
        self.action_client.destroy()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = AlertActionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down alert action node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
