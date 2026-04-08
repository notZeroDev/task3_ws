#!/usr/bin/env python3
"""Face detection node that consumes camera frames and publishes face data."""

import os

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from smart_exam_protocoring_msgs.msg import BoundingBox, FaceData


class FaceDetectionNode(Node):
    """Detect faces using Haar Cascade and publish bounding boxes."""

    def __init__(self):
        super().__init__("face_detection_node")

        self.declare_parameter("scale_factor", 1.1)
        self.declare_parameter("min_neighbors", 5)
        self.declare_parameter("display_window", True)

        self.scale_factor = float(self.get_parameter("scale_factor").value)
        self.min_neighbors = int(self.get_parameter("min_neighbors").value)
        self.display_window = bool(self.get_parameter("display_window").value)

        # OpenCV GUI requires a display server; disable window output in headless runs.
        if self.display_window and not os.environ.get("DISPLAY"):
            self.get_logger().warn(
                "display_window is enabled but DISPLAY is not set. "
                "Disabling OpenCV window output."
            )
            self.display_window = False

        if self.display_window:
            cv2.namedWindow("Face Detection", cv2.WINDOW_NORMAL)

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            raise RuntimeError(f"Failed to load Haar Cascade at: {cascade_path}")

        self.bridge = CvBridge()
        self.subscription = self.create_subscription(
            Image,
            "/camera_frames",
            self.image_callback,
            10,
        )
        self.publisher = self.create_publisher(FaceData, "/face_data", 10)

        self.get_logger().info(
            "Face detection node initialized: "
            f"scale_factor={self.scale_factor}, min_neighbors={self.min_neighbors}"
        )

    def image_callback(self, msg: Image) -> None:
        """Handle incoming frames, detect faces, and publish bounding boxes."""
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().error(f"Failed to convert image message: {exc}")
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
        )

        boxes = []

        for x, y, w, h in faces:
            box = BoundingBox()
            box.x = int(x)
            box.y = int(y)
            box.w = int(w)
            box.h = int(h)
            boxes.append(box)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.putText(
            frame,
            f"Faces: {len(faces)}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2,
        )

        out_msg = FaceData()
        out_msg.header = msg.header
        out_msg.boxes = boxes
        self.publisher.publish(out_msg)

        if self.display_window:
            cv2.imshow("Face Detection", frame)
            cv2.waitKey(1)

    def destroy_node(self):
        """Clean up resources."""
        if self.display_window:
            cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = FaceDetectionNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down face detection node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
