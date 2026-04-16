import sys
import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32
from cv_bridge import CvBridge
import torch
import cv2
import numpy as np

# =========================================================
# FIX 1: Robust path handling
# =========================================================
DEPTH_ANYTHING_PATH = "/home/ahmed/Depth-Anything-V2/checkpoints/"

if not os.path.exists(DEPTH_ANYTHING_PATH):
    raise FileNotFoundError(f"Depth-Anything-V2 not found at {DEPTH_ANYTHING_PATH}")

if DEPTH_ANYTHING_PATH not in sys.path:
    sys.path.insert(0, DEPTH_ANYTHING_PATH)

try:
    from depth_anything_v2.dpt import DepthAnythingV2
except Exception as e:
    raise ImportError(f"Failed to import DepthAnythingV2: {e}")


class DepthEstimationNode(Node):
    def __init__(self):
        super().__init__('depth_node')

        self.declare_parameter('depth_threshold', 0.5)
        self.depth_threshold = self.get_parameter('depth_threshold').value

        self.subscription = self.create_subscription(
            Image, '/camera_frames', self.image_callback, 10)

        self.depth_pub = self.create_publisher(Image, '/depth_data', 10)
        self.avg_depth_pub = self.create_publisher(Float32, '/depth_mean', 10)

        self.bridge = CvBridge()

        # Safer device selection
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.get_logger().info(f"Using device: {self.device}")

        # =========================================================
        # FIX 3: Load model safely with File Integrity Check
        # =========================================================
        try:
            self.model = DepthAnythingV2(
                encoder='vits',
                features=64,
                out_channels=[48, 96, 192, 384]
            )

            checkpoint = os.path.expanduser(
                '/home/ahmed/Depth-Anything-V2/checkpoints/'
            )

            if not os.path.exists(checkpoint):
                raise FileNotFoundError(f"Checkpoint not found at {checkpoint}")
            
            # NEW: Check if file is likely corrupted (too small)
            file_size = os.path.getsize(checkpoint)
            if file_size < 100_000_000: # VITS should be ~100MB+
                raise ValueError(f"Checkpoint file at {checkpoint} is too small ({file_size} bytes). It is likely corrupted.")

            self.model.load_state_dict(
                torch.load(checkpoint, map_location=self.device)
            )

            self.model.to(self.device)
            self.model.eval()

            # Optimization for CPU inference
            if self.device == 'cpu':
                self.model = torch.optimize_for_inference(torch.jit.script(self.model))

            self.get_logger().info("Depth model loaded successfully ✅")

        except Exception as e:
            self.get_logger().error(f"Model loading failed: {e}")
            raise

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

            # Performance: Depth Anything V2 works well on smaller inputs
            # 320x240 is good for CPU. 518 is their native "sweet spot" if you have a GPU.
            small_frame = cv2.resize(frame, (320, 240))

            with torch.no_grad():
                # infer_image returns a numpy array
                depth = self.model.infer_image(small_frame)

            depth_min = depth.min()
            depth_max = depth.max()

            if depth_max - depth_min < 1e-6:
                return

            depth_norm = (depth - depth_min) / (depth_max - depth_min)
            avg_depth = float(np.mean(depth_norm))

            # Publish depth image
            depth_img = (depth_norm * 255).astype(np.uint8)
            depth_msg = self.bridge.cv2_to_imgmsg(depth_img, encoding='mono8')
            self.depth_pub.publish(depth_msg)

            # Publish mean
            avg_msg = Float32()
            avg_msg.data = avg_depth
            self.avg_depth_pub.publish(avg_msg)

        except Exception as e:
            self.get_logger().error(f"Inference failed: {e}")


def main(args=None):
    rclpy.init(args=args)
    try:
        node = DepthEstimationNode()
        rclpy.spin(node)
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()