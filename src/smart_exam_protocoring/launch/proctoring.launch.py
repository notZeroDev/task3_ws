#!/usr/bin/env python3
"""
Launch file for the Smart Exam Proctoring System.

Starts all 8 nodes in the correct order:
  1. camera_node          — streams frames
  2. face_detection_node  — Haar Cascade face detection
  3. object_detector_node — YOLOv8 object detection
  4. depth_estimation_node— monocular depth heuristic
  5. behavior_analysis_node— combines perception outputs
  6. rule_evaluation_node — maps behavior to violation events
  7. alert_action_node    — executes alerts via action server/client
  8. system_monitor_node  — pipeline health reporter
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory("smart_exam_protocoring")
    default_video = os.path.join(pkg_share, "data", "video.mp4")

    # ── Declare overridable launch arguments ───────────────────────────────────
    camera_source_arg = DeclareLaunchArgument(
        "camera_source",
        default_value=default_video,
        description="Camera index (int) or path to a video file",
    )
    frame_rate_arg = DeclareLaunchArgument(
        "frame_rate",
        default_value="10",
        description="Frames per second published by the camera node",
    )
    model_path_arg = DeclareLaunchArgument(
        "model_path",
        default_value="yolov8n.pt",
        description="Path to the YOLO model weights (.pt file)",
    )
    confidence_threshold_arg = DeclareLaunchArgument(
        "confidence_threshold",
        default_value="0.5",
        description="Minimum YOLO detection confidence",
    )
    display_window_arg = DeclareLaunchArgument(
        "display_window",
        default_value="False",
        description="Show OpenCV debug windows (requires a DISPLAY server)",
    )
    alert_level_arg = DeclareLaunchArgument(
        "alert_level",
        default_value="medium",
        description="Minimum severity level that triggers an alert (low|medium|high)",
    )

    # ── Node definitions ───────────────────────────────────────────────────────

    camera_node = Node(
        package="smart_exam_protocoring",
        executable="camera_node",
        name="camera_node",
        output="screen",
        parameters=[
            {
                "camera_source": LaunchConfiguration("camera_source"),
                "frame_rate": LaunchConfiguration("frame_rate"),
                "frame_id": "camera_frame",
            }
        ],
    )

    face_detection_node = Node(
        package="smart_exam_protocoring",
        executable="face_detection_node",
        name="face_detection_node",
        output="screen",
        parameters=[
            {
                "scale_factor": 1.1,
                "min_neighbors": 5,
                "display_window": LaunchConfiguration("display_window"),
            }
        ],
    )

    object_detector_node = Node(
        package="smart_exam_protocoring",
        executable="object_detector_node",
        name="object_detector_node",
        output="screen",
        parameters=[
            {
                "confidence_threshold": LaunchConfiguration("confidence_threshold"),
                "model_path": LaunchConfiguration("model_path"),
                "display_window": LaunchConfiguration("display_window"),
                "filter_prohibited_only": True,
            }
        ],
    )

    depth_estimation_node = Node(
        package="smart_exam_protocoring",
        executable="depth_estimation_node",
        name="depth_estimation_node",
        output="screen",
        parameters=[
            {
                "depth_threshold": 0.6,
                "display_window": LaunchConfiguration("display_window"),
            }
        ],
    )

    behavior_analysis_node = Node(
        package="smart_exam_protocoring",
        executable="behavior_analysis_node",
        name="behavior_analysis_node",
        output="screen",
        parameters=[
            {
                "attention_threshold": 0.7,
                "depth_far_threshold": 0.75,
                "depth_near_threshold": 0.2,
                "stale_timeout_sec": 1.5,
            }
        ],
    )

    rule_evaluation_node = Node(
        package="smart_exam_protocoring",
        executable="rule_evaluation_node",
        name="rule_evaluation_node",
        output="screen",
        parameters=[
            {
                "violation_rules": [
                    "PROHIBITED_OBJECT:high",
                    "MULTIPLE_FACES:high",
                    "LOOKING_AWAY:medium",
                    "TOO_FAR:medium",
                    "TOO_CLOSE:low",
                    "LOW_ATTENTION:low",
                ],
            }
        ],
    )

    alert_action_node = Node(
        package="smart_exam_protocoring",
        executable="alert_action_node",
        name="alert_action_node",
        output="screen",
        parameters=[
            {
                "alert_level": LaunchConfiguration("alert_level"),
            }
        ],
    )

    system_monitor_node = Node(
        package="smart_exam_protocoring",
        executable="system_monitor_node",
        name="system_monitor_node",
        output="screen",
        parameters=[
            {
                "monitor_period_sec": 2.0,
            }
        ],
    )

    return LaunchDescription(
        [
            # Arguments
            camera_source_arg,
            frame_rate_arg,
            model_path_arg,
            confidence_threshold_arg,
            display_window_arg,
            alert_level_arg,
            # Nodes
            camera_node,
            face_detection_node,
            object_detector_node,
            depth_estimation_node,
            behavior_analysis_node,
            rule_evaluation_node,
            alert_action_node,
            system_monitor_node,
        ]
    )
