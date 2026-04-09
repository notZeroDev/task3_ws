#!/usr/bin/env python3
"""
Object detection node that consumes camera frames and publishes
detected prohibited objects (phone, book, etc.) using YOLOv8.
"""

import os

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Header

from smart_exam_protocoring_msgs.msg import DetectedObject, DetectedObjectArray


# Objects considered prohibited during an exam
PROHIBITED_LABELS = {"cell phone", "book", "laptop", "remote", "mouse", "keyboard"}


class ObjectDetectionNode(Node):
    """Detect prohibited objects using YOLOv8 and publish structured results."""

    def __init__(self):
        super().__init__("object_detection_node")

        # ── Parameters ────────────────────────────────────────────────────────
        self.declare_parameter("confidence_threshold", 0.5)
        self.declare_parameter("model_path", "yolov8n.pt")   # nano model by default
        self.declare_parameter("display_window", True)
        self.declare_parameter("filter_prohibited_only", True)

        self.conf_threshold = float(
            self.get_parameter("confidence_threshold").value
        )
        model_path = str(self.get_parameter("model_path").value)
        self.display_window = bool(self.get_parameter("display_window").value)
        self.filter_prohibited = bool(
            self.get_parameter("filter_prohibited_only").value
        )

        # Suppress OpenCV window in headless environments
        if self.display_window and not os.environ.get("DISPLAY"):
            self.get_logger().warn(
                "display_window is enabled but DISPLAY is not set. "
                "Disabling OpenCV window output."
            )
            self.display_window = False

        if self.display_window:
            cv2.namedWindow("Object Detection", cv2.WINDOW_NORMAL)

        # ── Load YOLO model ───────────────────────────────────────────────────
        try:
            from ultralytics import YOLO  # lazy import — not needed at build time
            self.model = YOLO(model_path)
            self.get_logger().info(f"YOLO model loaded from: {model_path}")
        except Exception as exc:
            self.get_logger().error(f"Failed to load YOLO model: {exc}")
            raise

        # ── ROS 2 communication ───────────────────────────────────────────────
        self.bridge = CvBridge()

        self.subscription = self.create_subscription(
            Image,
            "/camera_frames",
            self.image_callback,
            10,
        )
        self.publisher = self.create_publisher(
            DetectedObjectArray,
            "/object_data",
            10,
        )

        self.get_logger().info(
            f"Object detection node initialized | "
            f"conf_threshold={self.conf_threshold} | "
            f"filter_prohibited_only={self.filter_prohibited}"
        )

    # ── Callback ──────────────────────────────────────────────────────────────

    def image_callback(self, msg: Image) -> None:
        """Run YOLO on each incoming frame and publish DetectedObjectArray."""
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().error(f"Failed to convert image message: {exc}")
            return

        detections = self._run_inference(frame)
        ros_msg = self._build_ros_message(msg.header, detections)
        self.publisher.publish(ros_msg)

        if self.display_window:
            annotated = self._draw_detections(frame, detections)
            cv2.imshow("Object Detection", annotated)
            cv2.waitKey(1)

    # ── Inference ─────────────────────────────────────────────────────────────

    def _run_inference(self, frame) -> list[dict]:
        """
        Run YOLOv8 inference and return a list of detection dicts.
        Each dict has: label, confidence, x, y, width, height.
        """
        results = self.model(frame, verbose=False)[0]  # single-frame batch
        detections = []

        for box in results.boxes:
            conf = float(box.conf[0])
            if conf < self.conf_threshold:
                continue

            label = self.model.names[int(box.cls[0])]

            if self.filter_prohibited and label not in PROHIBITED_LABELS:
                continue

            # box.xyxy → [x1, y1, x2, y2]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detections.append(
                {
                    "label": label,
                    "confidence": conf,
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1,
                }
            )

        return detections

    # ── Message building ──────────────────────────────────────────────────────

    def _build_ros_message(
        self, original_header: Header, detections: list[dict]
    ) -> DetectedObjectArray:
        """
        Pack detections into a DetectedObjectArray message.
        Reuse the camera frame's header so timestamps stay aligned.
        """
        array_msg = DetectedObjectArray()
        array_msg.header = original_header   # preserves the original capture time and frame id
        array_msg.total_count = len(detections)

        for det in detections:
            obj = DetectedObject()
            obj.label = det["label"]
            obj.confidence = det["confidence"]
            obj.x = det["x"]
            obj.y = det["y"]
            obj.width = det["width"]
            obj.height = det["height"]
            array_msg.objects.append(obj)

        return array_msg

    # ── Visualization ─────────────────────────────────────────────────────────

    def _draw_detections(self, frame, detections: list[dict]):
        """Draw bounding boxes and labels on a copy of the frame."""
        annotated = frame.copy()

        for det in detections:
            x, y, w, h = det["x"], det["y"], det["width"], det["height"]
            label = det["label"]
            conf = det["confidence"]

            is_prohibited = label in PROHIBITED_LABELS
            color = (0, 0, 255) if is_prohibited else (0, 255, 255)  # red vs yellow

            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                annotated,
                f"{label} {conf:.2f}",
                (x, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

        cv2.putText(
            annotated,
            f"Prohibited objects: {len(detections)}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2,
        )
        return annotated

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def destroy_node(self):
        if self.display_window:
            cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectionNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down object detection node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()