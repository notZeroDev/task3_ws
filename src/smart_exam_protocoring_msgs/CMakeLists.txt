cmake_minimum_required(VERSION 3.8)
project(smart_exam_protocoring_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(action_msgs REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/BoundingBox.msg"
  "msg/FaceData.msg"
  "msg/DetectedObject.msg"
  "msg/DetectedObjectArray.msg"
  "msg/ViolationEvent.msg"
  "msg/AlertStatus.msg"
  "srv/CheckViolation.srv"
  "action/AlertAction.action"
  DEPENDENCIES std_msgs action_msgs
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
