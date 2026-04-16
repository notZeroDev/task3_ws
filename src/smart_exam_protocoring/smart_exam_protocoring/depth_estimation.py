#!/usr/bin/env python3
"""Depth estimation node publishing normalized scene depth."""

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32


class DepthEstimationNode(Node):
    """Estimate depth from monocular frames using a lightweight heuristic."""

    def __init__(self):
        super().__init__("depth_estimation_node")

        self.declare_parameter("depth_threshold", 0.6)
        self.declare_parameter("display_window", True)

        self.depth_threshold = float(self.get_parameter("depth_threshold").value)
        self.display_window = bool(self.get_parameter("display_window").value)

        self.bridge = CvBridge()
        self.subscription = self.create_subscription(
            Image,
            "/camera_frames",
            self.image_callback,
            10,
        )
        self.depth_pub = self.create_publisher(Float32, "/depth_data", 10)

        if self.display_window:
            cv2.namedWindow("Depth Estimation", cv2.WINDOW_NORMAL)

        self.get_logger().info(
            "Depth estimation node initialized "
            f"(depth_threshold={self.depth_threshold})"
        )

    def image_callback(self, msg: Image) -> None:
        """Estimate normalized depth score and publish on /depth_data."""
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().error(f"Failed to convert image message: {exc}")
            return

        # Convert to a grayscale blur map. Lower local contrast usually means
        # farther objects in low-cost monocular setups.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(np.mean(np.abs(laplacian)))

        # Normalize sharpness into [0, 1], then invert to represent depth.
        normalized_sharpness = min(max(sharpness / 30.0, 0.0), 1.0)
        estimated_depth = float(1.0 - normalized_sharpness)

        depth_msg = Float32()
        depth_msg.data = estimated_depth
        self.depth_pub.publish(depth_msg)

        if self.display_window:
            overlay = frame.copy()
            status = "FAR" if estimated_depth > self.depth_threshold else "NEAR"
            cv2.putText(
                overlay,
                f"Depth: {estimated_depth:.2f} ({status})",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 0, 0),
                2,
            )
            cv2.imshow("Depth Estimation", overlay)
            cv2.waitKey(1)

    def destroy_node(self):
        """Clean up GUI resources."""
        if self.display_window:
            cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DepthEstimationNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down depth estimation node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
