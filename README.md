# AI-Based Classroom Attendance System using Face Recognition

A complete Flask web application that automatically marks classroom attendance using
face recognition — from a live webcam feed **or** an uploaded classroom photo.

> **This version uses OpenCV only** — Haar Cascade for face detection and the LBPH
> (Local Binary Patterns Histograms) recognizer for face recognition. There is **no
> dependency on `dlib`, `face_recognition`, CMake, or Visual C++ Build Tools** — everything
> installs with a single `pip install` and works reliably on plain Windows Python.

---

## 1. Features

- **Student Registration** — name, register number, photo via file upload or webcam capture, duplicate-ID prevention
- **Face Recognition** — OpenCV Haar Cascade (detection) + OpenCV LBPH recognizer (recognition). No dlib.
- **Live Webcam Attendance** — real-time detection, bounding boxes, auto Present marking, no duplicate same-day records
- **Classroom Photo Attendance** — upload one group photo, recognized students → Present, everyone else registered → Absent
- **Teacher Dashboard** — total/present/absent counts, attendance %, today's records
- **Attendance Records + Manual Correction** — filter by date, flip Present ⇄ Absent
- **Student Management** — search, view, delete
- **CSV Export** — full or date-filtered

---

## 2. Project Structure

```
AI_Classroom_Attendance/
│
├── app.py                        # Flask app: all routes
├── requirements.txt
├── README.md
├── PROJECT_REPORT.md              # Ready-to-use report content
├── DEMO_SCRIPT.md                 # 2-3 min demo video narration script
│
├── database/
│   └── attendance.db              # Created automatically on first run
│
├── dataset/
│   └── students/                  # Registered student reference photos
│       ├── samples/               # Normalized grayscale training samples (.png), one per student
│       └── model/                 # Trained LBPH model (lbph_model.yml) + label map (label_map.pkl)
│
├── uploads/                       # Uploaded classroom photos
│
├── static/
│   ├── css/style.css
│   ├── js/script.js
│   └── images/
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── register.html
│   ├── students.html
│   ├── live_attendance.html
│   ├── upload_attendance.html
│   ├── attendance_records.html
│   └── edit_attendance.html
│
└── utils/
    ├── __init__.py
    ├── database.py                # SQLite schema + CRUD
    └── face_recognition_utils.py  # Encoding + recognition logic
```

---

## 3. Installation (Windows)

### Step 1 — Install Python
Install **Python 3.9–3.12** from https://python.org (tick "Add Python to PATH" during install).
Any recent version works fine — there's no C++ toolchain requirement with this OpenCV-only build.

### Step 2 — Create a virtual environment
Open Command Prompt (or PowerShell) in the project folder:
```
python -m venv venv
```

### Step 3 — Activate it
Command Prompt:
```
venv\Scripts\activate
```
PowerShell:
```
venv\Scripts\Activate.ps1
```
You should see `(venv)` appear at the start of your prompt.

### Step 4 — Install dependencies
```
pip install --upgrade pip
pip install -r requirements.txt
```
This installs only `Flask`, `opencv-contrib-python`, and `numpy` — no CMake, no dlib, no
Visual C++ Build Tools, no long compile times.

### Step 5 — Run the application
```
python app.py
```

### Step 6 — Open the app
Go to: **http://127.0.0.1:5000**

The database and required folders are created automatically the first time you run the app.

---

## 4. How to Test Every Feature

1. **Register students** — go to *Register Student*, fill name + ID, either upload a clear front-facing
   photo (one face only) or use *Use Webcam* → Start Camera → Capture Photo → Save. Register 3–5 students.
2. **View student list** — *Students List* shows thumbnails; use the search box to filter, delete to remove.
3. **Live attendance** — *Live Attendance* → Start Camera → Start Recognition. Recognized faces get a
   green box + name and are marked Present immediately (no duplicate rows for the same day).
4. **Upload classroom image** — *Upload Classroom Image* → choose a group photo → Upload & Process.
   Recognized students are marked Present; every other registered student is marked Absent for that date.
5. **View attendance** — *Attendance Records*, optionally filter by date.
6. **Edit attendance** — click *Edit* on any record, flip Present ⇄ Absent, Save.
7. **Export CSV** — click *Export CSV* (sidebar, or on the records page for a filtered date).

---

## 5. Troubleshooting

### `ModuleNotFoundError: No module named 'cv2.face'` or `AttributeError: module 'cv2' has no attribute 'face'`
You have `opencv-python` installed instead of `opencv-contrib-python` (the `face` module, which
provides LBPH, only ships in the "contrib" build). Fix:
```
pip uninstall opencv-python opencv-python-headless opencv-contrib-python -y
pip install opencv-contrib-python
```

### `ModuleNotFoundError: No module named 'face_recognition'`
This means an old version of the project (or a stray cached `.pyc`) is still trying to import the
old `face_recognition` library. This version doesn't use it at all — confirm `requirements.txt`
only lists `Flask`, `opencv-contrib-python`, and `numpy`, delete any `__pycache__` folders, and
reinstall with `pip install -r requirements.txt`.

### Recognition seems inaccurate / mixes up students
LBPH is a lightweight, classical (non deep-learning) recognizer, so it's more sensitive to lighting
and pose than the previous dlib-based approach. To improve accuracy:
- Use well-lit, front-facing registration photos (avoid strong shadows/backlight).
- Keep the "confidence" threshold (`CONFIDENCE_THRESHOLD` in `utils/face_recognition_utils.py`,
  default `75.0`) tuned — **lower** it for stricter matching (fewer false positives, more
  "Unknown" results) or **raise** it for looser matching.
- Keep classroom photos reasonably sharp and not too far from the camera — very small/blurry faces
  are hard for Haar Cascade to even detect.

### Camera not detected / "Camera unavailable"
- Ensure no other app (Zoom, Teams, another browser tab) is using the webcam.
- Grant camera permission in the browser when prompted (Chrome/Edge address bar → camera icon).
- The Live Attendance page requires the browser's `getUserMedia` API, which needs `http://127.0.0.1`
  or `https://` — it will **not** work if you access the app via a plain IP over HTTP other than localhost.

### "No face detected" during registration
- Use a well-lit, front-facing photo with the face clearly visible and unobstructed.
- Avoid heavy sunglasses, masks, or extreme angles — Haar Cascade works best on frontal faces.

### "Multiple faces detected" during registration
- The registration photo must contain exactly one face. Crop the photo or use a solo picture.

### Port 5000 already in use
Edit the last line of `app.py`:
```python
app.run(debug=True, host="127.0.0.1", port=5001)
```

---

## 6. Notes on the Face Recognition Approach

- **Detection**: `cv2.CascadeClassifier` with the bundled `haarcascade_frontalface_default.xml` —
  a classic, CPU-friendly Viola-Jones detector included with every OpenCV install, no extra download.
- **Recognition**: `cv2.face.LBPHFaceRecognizer_create()` (Local Binary Patterns Histograms), provided
  by `opencv-contrib-python`. Each registered student's face is cropped, grayscaled, and resized to
  200×200 as a training sample.
- **Training**: the app automatically (re)trains the LBPH model in memory whenever the set of
  registered students changes (e.g. after a new registration or a deletion) — there is no manual
  "train" step. The trained model is also cached to disk (`dataset/students/model/`) so a server
  restart doesn't need to retrain from scratch if nothing changed.
- **Matching**: LBPH's `predict()` returns a distance value (lower = better match); faces with a
  distance above `CONFIDENCE_THRESHOLD` (default `75.0`, in `utils/face_recognition_utils.py`) are
  treated as **Unknown** rather than force-matched to the closest student.
- This is a lighter-weight, classical computer-vision approach rather than a deep-learning embedding
  model. It trades some accuracy (versus dlib/deep-learning approaches) for zero compiled
  dependencies and instant installation — a good fit for a college project that needs to "just run"
  on any Windows machine.

---

## 7. Technology Stack

| Layer            | Technology                                   |
|-------------------|-----------------------------------------------|
| Backend           | Python 3, Flask                              |
| Database          | SQLite                                       |
| Face Detection    | OpenCV Haar Cascade (`cv2.CascadeClassifier`)|
| Face Recognition  | OpenCV LBPH (`cv2.face.LBPHFaceRecognizer_create`, via `opencv-contrib-python`) |
| Frontend          | HTML, CSS, JavaScript, Bootstrap 5           |
