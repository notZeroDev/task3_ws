#!/usr/bin/env python3
"""Behavior analysis node combining face, object, and depth streams."""

import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from smart_exam_protocoring_msgs.msg import DetectedObjectArray, FaceData
from std_msgs.msg import Float32


class BehaviorAnalysisNode(Node):
    """Analyze exam behavior from multimodal perception outputs."""

    def __init__(self):
        super().__init__("behavior_analysis_node")

        self.declare_parameter("attention_threshold", 0.7)
        self.declare_parameter("depth_far_threshold", 0.75)
        self.declare_parameter("depth_near_threshold", 0.2)
        self.declare_parameter("stale_timeout_sec", 1.5)

        self.attention_threshold = float(self.get_parameter("attention_threshold").value)
        self.depth_far_threshold = float(
            self.get_parameter("depth_far_threshold").value
        )
        self.depth_near_threshold = float(
            self.get_parameter("depth_near_threshold").value
        )
        self.stale_timeout_sec = float(self.get_parameter("stale_timeout_sec").value)

        self.latest_face = None
        self.latest_objects = None
        self.latest_depth = None

        self.latest_face_ts = None
        self.latest_objects_ts = None
        self.latest_depth_ts = None

        self.create_subscription(FaceData, "/face_data", self.face_callback, 10)
        self.create_subscription(
            DetectedObjectArray, "/object_data", self.object_callback, 10
        )
        self.create_subscription(Float32, "/depth_data", self.depth_callback, 10)

        self.publisher = self.create_publisher(String, "/behavior_state", 10)
        self.timer = self.create_timer(0.2, self.evaluate_behavior)

        self.get_logger().info("Behavior analysis node initialized")

    def face_callback(self, msg: FaceData) -> None:
        self.latest_face = msg
        self.latest_face_ts = self.get_clock().now()

    def object_callback(self, msg: DetectedObjectArray) -> None:
        self.latest_objects = msg
        self.latest_objects_ts = self.get_clock().now()

    def depth_callback(self, msg: Float32) -> None:
        self.latest_depth = msg.data
        self.latest_depth_ts = self.get_clock().now()

    def _is_stale(self, timestamp) -> bool:
        if timestamp is None:
            return True
        elapsed = (self.get_clock().now() - timestamp).nanoseconds / 1e9
        return elapsed > self.stale_timeout_sec

    def evaluate_behavior(self) -> None:
        # Require at least camera/face data to be fresh; if completely cold, skip.
        if self._is_stale(self.latest_face_ts) and self._is_stale(self.latest_depth_ts):
            return

        reasons = []

        # ── Face data ──────────────────────────────────────────────────────────
        if self._is_stale(self.latest_face_ts):
            # No face data available yet — treat as looking away
            face_count = 0
            self.get_logger().debug("Face data stale, assuming no face detected")
        else:
            face_count = len(self.latest_face.boxes) if self.latest_face else 0

        if face_count == 0:
            reasons.append("LOOKING_AWAY")
        elif face_count > 1:
            reasons.append("MULTIPLE_FACES")

        # ── Object data (YOLO is slow on CPU — treat stale as no detections) ───
        if self._is_stale(self.latest_objects_ts):
            prohibited_count = 0
            self.get_logger().debug("Object data stale, assuming no prohibited objects")
        else:
            prohibited_count = (
                self.latest_objects.total_count if self.latest_objects is not None else 0
            )
        if prohibited_count > 0:
            reasons.append("PROHIBITED_OBJECT")

        # ── Depth data ─────────────────────────────────────────────────────────
        if self._is_stale(self.latest_depth_ts):
            depth_score = math.nan
            self.get_logger().debug("Depth data stale, skipping depth check")
        else:
            depth_score = float(self.latest_depth) if self.latest_depth is not None else math.nan

        if not math.isnan(depth_score):
            if depth_score > self.depth_far_threshold:
                reasons.append("TOO_FAR")
            elif depth_score < self.depth_near_threshold:
                reasons.append("TOO_CLOSE")

        confidence = self._estimate_attention_confidence(face_count, prohibited_count)
        if confidence < self.attention_threshold:
            reasons.append("LOW_ATTENTION")

        behavior = String()
        if reasons:
            behavior.data = "|".join(sorted(set(reasons)))
        else:
            behavior.data = "NORMAL"

        self.publisher.publish(behavior)

    def _estimate_attention_confidence(self, face_count: int, prohibited_count: int) -> float:
        score = 1.0
        if face_count == 0:
            score -= 0.6
        elif face_count > 1:
            score -= 0.3
        if prohibited_count > 0:
            score -= 0.4
        if self.latest_depth is not None:
            if self.latest_depth > self.depth_far_threshold:
                score -= 0.2
            if self.latest_depth < self.depth_near_threshold:
                score -= 0.2
        return max(0.0, min(1.0, score))


def main(args=None):
    rclpy.init(args=args)
    node = BehaviorAnalysisNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down behavior analysis node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
