import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class BehaviorAnalysisNode(Node):
    def __init__(self):
        super().__init__('behavior_node') # Name as per task [cite: 166]

        # Parameters [cite: 86, 146]
        self.declare_parameter('attention_threshold', 0.5)
        self.attention_threshold = self.get_parameter('attention_threshold').value

        # States
        self.face_detected = False
        self.prohibited_object = False
        self.current_depth = 0.5

        # Subscribers [cite: 83, 84, 85]
        self.create_subscription(String, '/face_data', self.face_cb, 10)
        self.create_subscription(String, '/object_data', self.object_cb, 10)
        self.create_subscription(Float32, '/depth_mean', self.depth_cb, 10)

        # Publisher [cite: 81]
        self.behavior_pub = self.create_publisher(String, '/behavior_state', 10)
        
        self.get_logger().info("Behavior Analysis Node Online")

    def face_cb(self, msg):
        self.face_detected = ("detected" in msg.data.lower())

    def object_cb(self, msg):
        self.prohibited_object = ("phone" in msg.data.lower() or "book" in msg.data.lower())

    def depth_cb(self, msg):
        self.current_depth = msg.data
        self.run_logic()

    def run_logic(self):
        """Logic to combine face + object + depth [cite: 127, 151]"""
        reasons = []

        # 1. Face logic [cite: 90]
        if not self.face_detected:
            reasons.append("LOOKING_AWAY")

        # 2. Object logic [cite: 91]
        if self.prohibited_object:
            reasons.append("PROHIBITED_OBJECT")

        # 3. Depth logic [cite: 92]
        if self.current_depth > 0.8: # Example threshold
            reasons.append("TOO_FAR")
        elif self.current_depth < 0.2:
            reasons.append("TOO_CLOSE")

        # Combine into state string
        state_msg = String()
        if not reasons:
            state_msg.data = "NORMAL"
        else:
            state_msg.data = "|".join(reasons)
        
        self.behavior_pub.publish(state_msg)
        self.get_logger().info(f"Behavior: {state_msg.data}")

def main(args=None):
    rclpy.init(args=args)
    node = BehaviorAnalysisNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()