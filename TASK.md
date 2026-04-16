# Distributed Smart Exam Proctoring System using ROS

## 1. Project Overview
A distributed system designed to monitor students during an exam using ROS. The system analyzes a video stream to detect faces, prohibited objects (e.g., phones, books), and suspicious behavior.

**Key Integrations:**
* OpenCV camera streaming
* Haar Cascade face detection
* YOLO object detection
* Depth estimation
* Behavior analysis
* Rule evaluation
* Alert system

**System Specs:**
* Total system: 8 nodes
* Input: Laptop camera or Video file
* Hardware: No external hardware required

---

## 2. Core Idea & Pipeline
The system continuously monitors a student and detects violations.

**Pipeline Steps:**
1. Capture frame
2. Detect face (Haar)
3. Detect objects (YOLO)
4. Estimate depth
5. Analyze behavior
6. Evaluate rules
7. Trigger alerts (actions)
8. Monitor system

---

## 3. Required Nodes

### 4.1 Camera Stream Node
* **Responsibility:** Capture frames and convert them to ROS Image.
* **Topics Published:** `/camera_frames`
* **Parameters:** `camera_source`, `frame_rate`
* **Internal Logic:** ROS1 uses cv2 → Image; ROS2 uses OpenCV → Image.

### 4.2 Face Detection Node
* **Responsibility:** Detect faces using Haar Cascade.
* **Topics Published:** `/face_data`
* **Topics Subscribed:** `/camera_frames`
* **Parameters:** `scale_factor`, `min_neighbors`
* **Internal Logic:** Detect face bounding boxes.

### 4.3 Object Detection Node
* **Responsibility:** Detect prohibited objects (phone, book).
* **Topics Published:** `/object_data`
* **Topics Subscribed:** `/camera_frames`
* **Parameters:** `confidence_threshold`
* **Internal Logic:** Run YOLO.

### 4.4 Depth Estimation Node
* **Responsibility:** Estimate distance.
* **Topics Published:** `/depth_data`
* **Topics Subscribed:** `/camera_frames`
* **Parameters:** `depth_threshold`
* **Internal Logic:** Estimate how far objects are.

### 4.5 Behavior Analysis Node
* **Responsibility:** Analyze student behavior.
* **Topics Published:** `/behavior_state`
* **Topics Subscribed:** `/face_data`, `/object_data`, `/depth_data`
* **Parameters:** `attention_threshold`
* **Internal Logic:** Detect looking away, object usage, and unusual distance.

### 4.6 Rule Evaluation Node
* **Responsibility:** Decide if violation occurs.
* **Topics Published:** `/violation_event`
* **Topics Subscribed:** `/behavior_state`
* **Services Provided:** `/check_violation`
* **Parameters:** `violation_rules`
* **Internal Logic:** Apply rules to behavior.

### 4.7 Alert Action Node
* **Responsibility:** Trigger alerts.
* **Topics Published:** `/alert_status`
* **Topics Subscribed:** `/violation_event`
* **Actions Used:** `/alert_action`
* **Parameters:** `alert_level`
* **Internal Logic:** Send warning (simulated).

### 4.8 System Monitor Node
* **Responsibility:** Monitor full system.
* **Topics Subscribed:** All topics
* **Internal Logic:** Display system status.

---

## 4. System Rules
* **Input:** Camera or video at a minimum of 5 FPS.
* **Detection Requirements:** Must detect a face and at least 1 prohibited object.
* **Behavior Logic:** Must combine face + object + depth data.
* **Alert Execution:** Alerts must be triggered via actions.

---

## 5. Required ROS Communication
* **Topics:** `/camera_frames`, `/face_data`, `/object_data`, `/depth_data`, `/behavior_state`, `/violation_event`, `/alert_status`.
* **Services:** `/check_violation` (Used for rule validation).
* **Actions:** `/alert_action` (Used for alert execution).
* **Parameters:** detection thresholds, behavior thresholds, violation rules, alert levels.

---

## 6. Main Objectives
* **A. Multi-Perception Integration:** Combine Haar + YOLO + Depth.
* **B. Behavior Understanding:** Focus on reasoning, not just detection.
* **C. Decision Making:** Rule-based violation detection.
* **D. Action Communication:** Alerts triggered via action server.
* **E. Debugging:** Ensure full pipeline works.