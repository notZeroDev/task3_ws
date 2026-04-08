#!/usr/bin/env python3
"""
Camera streaming node that publishes frames from a video file or camera to a ROS 2 topic.
"""

import os

import cv2
import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class CameraNode(Node):
    """ROS 2 Node for streaming camera/video frames."""

    def __init__(self):
        super().__init__("camera_node")

        package_share_dir = get_package_share_directory("smart_exam_protocoring")
        default_video_path = os.path.join(package_share_dir, "data", "video.mp4")

        # Declare parameters
        self.declare_parameter(
            "camera_source", default_video_path
        )  # Default to packaged video
        self.declare_parameter("frame_rate", 30)  # Default to 30 FPS
        self.declare_parameter("frame_id", "camera_frame")

        # Get parameter values
        camera_source = self.get_parameter("camera_source").value
        self.frame_rate = self.get_parameter("frame_rate").value
        self.frame_id = str(self.get_parameter("frame_id").value)

        # Convert camera_source to appropriate type
        try:
            self.camera_source = int(camera_source)
        except ValueError:
            # If not an integer, treat as file path
            self.camera_source = str(camera_source)
        self.is_file_source = isinstance(self.camera_source, str)

        # Initialize OpenCV capture
        try:
            self.cap = cv2.VideoCapture(self.camera_source)
            if not self.cap.isOpened():
                self.get_logger().error(
                    f"Failed to open camera/video source: {self.camera_source}"
                )
                raise RuntimeError(f"Cannot open camera source: {self.camera_source}")

            self.get_logger().info(f"Camera source opened: {self.camera_source}")
        except Exception as e:
            self.get_logger().error(f"Error initializing camera: {e}")
            raise

        # Create publisher
        self.publisher_ = self.create_publisher(Image, "/camera_frames", 10)

        # Create bridge for converting OpenCV images to ROS messages
        self.bridge = CvBridge()

        # Calculate timer period from frame rate
        timer_period = 1.0 / self.frame_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info(
            f"Camera node initialized with frame_rate={self.frame_rate} FPS"
        )

    def timer_callback(self):
        """Capture frame from camera and publish to topic."""
        ret, frame = self.cap.read()

        if not ret:
            if self.is_file_source:
                # Rewind to the first frame when a video file reaches EOF.
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    self.get_logger().warn("Failed to read frame after video rewind")
                    return
            else:
                self.get_logger().warn("Failed to read frame from camera")
                return

        try:
            # Convert frame to ROS Image message
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.frame_id
            self.publisher_.publish(msg)
            self.get_logger().debug("Frame published")
        except Exception as e:
            self.get_logger().error(f"Error publishing frame: {e}")

    def destroy_node(self):
        """Clean up resources."""
        if self.cap:
            self.cap.release()
        self.get_logger().info("Camera released")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    camera_node = CameraNode()

    try:
        rclpy.spin(camera_node)
    except KeyboardInterrupt:
        camera_node.get_logger().info("Shutting down camera node...")
    finally:
        camera_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
