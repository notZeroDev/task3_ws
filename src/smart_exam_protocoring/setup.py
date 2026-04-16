from glob import glob
from setuptools import find_packages, setup

package_name = "smart_exam_protocoring"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/data", glob("data/*")),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="zero",
    maintainer_email="mohmed.ayman11@gmail.com",
    description="TODO: Package description",
    license="TODO: License declaration",
    extras_require={
        "test": [
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "camera_node=smart_exam_protocoring.camera_stream:main",
            "face_detection_node=smart_exam_protocoring.face_detection:main",
            "object_detector_node=smart_exam_protocoring.object_detector:main",
            "depth_estimation_node=smart_exam_protocoring.depth_estimation:main",
            "behavior_analysis_node=smart_exam_protocoring.behavior_analysis:main",
            "rule_evaluation_node=smart_exam_protocoring.rule_evaluation:main",
            "alert_action_node=smart_exam_protocoring.alert_action:main",
            "system_monitor_node=smart_exam_protocoring.system_monitor:main",
        ],
    },
)
