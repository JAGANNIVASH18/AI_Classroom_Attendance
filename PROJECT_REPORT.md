# Project Report: AI-Based Classroom Attendance System using Face Recognition

## 1. Project Title
**AI-Based Classroom Attendance System using Face Recognition**

## 2. Problem Statement
Traditional classroom attendance relies on manual roll-call or physical sign-in sheets. This method has
several drawbacks: it consumes valuable class time, is prone to proxy attendance (one student marking
another present), can be error-prone when class sizes are large, and produces records that are tedious
to compile, correct, or analyze later. There is a clear need for an automated, tamper-resistant, and
fast way to record attendance accurately.

## 3. Objective
To design and implement a system that uses AI-based face recognition to automatically detect and
identify students from a webcam feed or classroom photograph, and to record their attendance without
manual intervention — while still allowing teachers to review and correct records when necessary.

## 4. Proposed Solution
The system allows a teacher to register each student once, capturing their name, register number, and a
reference face photo. During a class session, the teacher can either run a live webcam recognition
session or upload a single photo of the classroom. The system detects all faces present, compares each
detected face against the database of registered face encodings, and marks matching students as
**Present**. For the classroom-photo mode, any registered student who is not detected in the photo is
automatically marked **Absent**. All records are timestamped and stored in a database, with a dashboard
summarizing attendance statistics and a records page for manual review and correction.

## 5. Technologies Used
- **Python 3** — core programming language for the backend and AI logic.
- **Flask** — lightweight web framework used to build the routes, request handling, and server-rendered UI.
- **OpenCV (`opencv-contrib-python`)** — provides the entire computer-vision pipeline:
  - **Haar Cascade Classifier** (`cv2.CascadeClassifier`) for face *detection*.
  - **LBPH Face Recognizer** (`cv2.face.LBPHFaceRecognizer_create`) for face *recognition*, trained
    on-the-fly from registered students' normalized face samples.
- **SQLite** — a lightweight, file-based relational database used to store student and attendance data,
  requiring no separate database server — ideal for a self-contained college project.
- **HTML, CSS, JavaScript, Bootstrap 5** — used to build a responsive, professional dashboard UI, including
  webcam capture via the browser's `getUserMedia` API and live overlay drawing via the Canvas API.

> This project intentionally avoids `dlib`/`face_recognition`, which require CMake and a C++ compiler
> to install. Using OpenCV's built-in Haar Cascade + LBPH keeps the entire stack installable with a
> single `pip install`, which matters for a project meant to be set up quickly on any lab or personal
> Windows machine.

## 6. System Architecture

```
      Camera (Live Webcam)         Uploaded Classroom Image
                 \                          /
                  \                        /
                   v                      v
              +-----------------------------------+
              |         Face Detection             |
              |  (OpenCV Haar Cascade Classifier)  |
              +-----------------------------------+
                              |
                              v
              +-----------------------------------+
              |        Face Recognition            |
              |   (OpenCV LBPH Face Recognizer)    |
              +-----------------------------------+
                              |
                              v
              +-----------------------------------+
              |       Student Database             |
              |   (registered students + encodings)|
              +-----------------------------------+
                              |
                              v
              +-----------------------------------+
              |      Attendance Processing         |
              | (mark Present / Absent, dedupe)    |
              +-----------------------------------+
                              |
                              v
              +-----------------------------------+
              |         SQLite Database            |
              |   (students table, attendance table)|
              +-----------------------------------+
                              |
                              v
              +-----------------------------------+
              |         Teacher Dashboard          |
              | (stats, records, correction, CSV)  |
              +-----------------------------------+
```

## 7. Modules

1. **Student Registration Module** — captures student details and reference photo, generates and stores
   a face encoding, and prevents duplicate student IDs.
2. **Face Recognition Module** (`utils/face_recognition_utils.py`) — handles face detection, encoding
   generation, loading known encodings, and matching detected faces against known students.
3. **Live Attendance Module** — browser webcam capture + periodic frame POSTing to a recognition
   endpoint, with real-time bounding-box overlay and instant attendance marking.
4. **Classroom Image Attendance Module** — bulk recognition from a single uploaded photo, marking
   detected students Present and all other registered students Absent for that date.
5. **Attendance Management Module** (`utils/database.py`) — schema definitions and all read/write logic
   for students and attendance, including duplicate-prevention and status-correction functions.
6. **Dashboard Module** — aggregates and displays today's totals, present/absent counts, and attendance
   percentage.
7. **Student Management Module** — list, search, and delete registered students (also removing their
   stored photo and encoding).
8. **Export Module** — generates a CSV attendance report, optionally filtered by date.

## 8. Database Design

**students**

| Column         | Type    | Notes                          |
|----------------|---------|---------------------------------|
| id             | INTEGER | Primary key, auto-increment    |
| student_id     | TEXT    | Unique register number/ID      |
| name           | TEXT    | Student's full name            |
| image_path     | TEXT    | Path to reference photo        |
| encoding_path  | TEXT    | Path to saved face encoding     |
| created_at     | TEXT    | Registration timestamp         |

**attendance**

| Column      | Type    | Notes                                              |
|-------------|---------|-----------------------------------------------------|
| id          | INTEGER | Primary key, auto-increment                        |
| student_id  | TEXT    | Foreign key → students.student_id                  |
| date        | TEXT    | Attendance date (YYYY-MM-DD)                       |
| time        | TEXT    | Time recorded                                       |
| status      | TEXT    | 'Present' or 'Absent'                              |
|             |         | UNIQUE(student_id, date) prevents duplicate rows    |

## 9. Results and Expected Accuracy
In good lighting with clear, front-facing registration photos, the OpenCV Haar Cascade + LBPH pipeline
typically achieves recognition accuracy in the **80–92%** range for small-to-medium student groups
(under ~30–40 registered faces). This is somewhat lower than deep-learning-based approaches (such as
dlib's ResNet embeddings), reflecting the trade-off made here: LBPH is a lightweight, classical
computer-vision technique that requires no compiled dependencies and trains almost instantly, at the
cost of some accuracy compared to deep embeddings. Real classroom accuracy is affected by:
- Lighting conditions and camera resolution
- Face angle/occlusion (masks, extreme side profiles)
- Distance from camera and image sharpness
- Similarity between individuals (e.g. identical twins) increasing false-match risk
- Quality of the original registration photo

## 10. Advantages
- Eliminates time spent on manual roll-call.
- Reduces proxy/false attendance.
- Produces a searchable, timestamped digital record automatically.
- Manual correction ensures teachers retain final control over the record.
- Runs entirely locally with a lightweight database — no cloud dependency or recurring cost.

## 11. Limitations
- Accuracy depends heavily on lighting, pose, and camera quality — more so than with deep-learning
  approaches, since LBPH relies on local texture patterns rather than learned facial features.
- Not inherently resistant to spoofing (e.g., a printed photo) without additional anti-spoofing measures.
- Haar Cascade detection is CPU-friendly but less accurate than deep CNN detectors in difficult
  conditions (poor lighting, extreme angles, partial occlusion).
- Large classes with many faces in one frame can slow down per-frame processing on modest hardware.
- SQLite is suitable for single-teacher/single-machine use, not built for concurrent multi-user access
  at scale.

## 12. Future Enhancements
- Switch to a deep-learning-based detector/recognizer (e.g., a CNN embedding model) for higher
  accuracy in challenging conditions, if the development environment can support the extra build
  dependencies.
- Move to a cloud-hosted database (e.g., PostgreSQL/Firebase) for multi-device, multi-teacher access.
- Build a companion mobile application for on-the-go attendance.
- Add liveness/anti-spoofing detection to prevent photo-based spoofing.
- Support multiple simultaneous camera feeds for larger venues.
- Send automated email/SMS notifications to parents for absentees.
