"""
face_recognition_utils.py
--------------------------
Face detection + recognition using ONLY OpenCV — no dlib, no face_recognition package,
no CMake, no Visual C++ Build Tools required.

Detection : OpenCV Haar Cascade (cv2.CascadeClassifier)
Recognition: OpenCV's LBPH Face Recognizer (cv2.face.LBPHFaceRecognizer_create),
             which ships with the `opencv-contrib-python` package.

Install with:
    pip install flask opencv-contrib-python numpy

How it works:
    - Every registered student's face is cropped, converted to grayscale, resized to a
      fixed size (200x200), and saved as a training sample.
    - The LBPH recognizer is (re)trained from ALL registered students' samples whenever a
      recognition request comes in and the in-memory model is stale (a student was added/
      removed since the last training). Training on a few dozen student images is fast
      (well under a second), so retraining on-demand is simple and reliable for a
      classroom-sized dataset — no separate "train" step for the user to remember.
    - Each student gets an integer label (their index) that maps back to their student_id
      via a small label_map.pkl file saved alongside the trained model.
"""

import os
import pickle

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDENTS_DIR = os.path.join(BASE_DIR, "dataset", "students")
SAMPLES_DIR = os.path.join(STUDENTS_DIR, "samples")     # grayscale training samples, one per student
MODEL_DIR = os.path.join(STUDENTS_DIR, "model")
MODEL_PATH = os.path.join(MODEL_DIR, "lbph_model.yml")
LABEL_MAP_PATH = os.path.join(MODEL_DIR, "label_map.pkl")

os.makedirs(SAMPLES_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

FACE_SIZE = (200, 200)

# LBPH prediction returns a "distance" (lower = more confident match). Below this
# threshold we accept the match; above it, we treat the face as Unknown.
CONFIDENCE_THRESHOLD = 75.0

_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# In-memory cache of the trained recognizer so we don't retrain on every single request.
_recognizer = None
_label_map = {}               # {int_label: student_id}
_trained_student_ids = set()  # student_ids the current in-memory model was trained on


class NoFaceDetectedError(Exception):
    """Raised when no face could be found in a supplied image."""
    pass


class MultipleFacesError(Exception):
    """Raised during registration when more than one face is found in the reference photo."""
    pass


def _has_lbph():
    return hasattr(cv2, "face") and hasattr(cv2.face, "LBPHFaceRecognizer_create")


def detect_all_faces(gray_image):
    """Return a list of (x, y, w, h) for every face detected in a grayscale image."""
    faces = _face_cascade.detectMultiScale(
        gray_image, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )
    return list(faces)


def generate_encoding(image_path, student_id):
    """
    Detect a single face in the given image, normalize it (grayscale + resize),
    and save it as this student's training sample (.png). Returns the sample path.

    Kept the same function name/signature as the original version so app.py did not
    need to change how it calls this.

    Raises NoFaceDetectedError / MultipleFacesError on bad input images.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise NoFaceDetectedError("Could not read the uploaded/captured image file.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = detect_all_faces(gray)

    if len(faces) == 0:
        raise NoFaceDetectedError("No face was detected in the uploaded/captured image.")
    if len(faces) > 1:
        raise MultipleFacesError(
            "Multiple faces detected in the registration image. "
            "Please use a photo with only the student's face."
        )

    x, y, w, h = faces[0]
    face_crop = gray[y:y + h, x:x + w]
    face_resized = cv2.resize(face_crop, FACE_SIZE)

    sample_path = os.path.join(SAMPLES_DIR, f"{student_id}.png")
    cv2.imwrite(sample_path, face_resized)

    # Invalidate the in-memory model so it retrains including this new student
    _invalidate_model()

    return sample_path


def _invalidate_model():
    global _recognizer, _trained_student_ids
    _recognizer = None
    _trained_student_ids = set()


def _load_all_samples():
    """Load every saved training sample. Returns (list_of_gray_images, list_of_student_ids)."""
    images = []
    student_ids = []
    if not os.path.isdir(SAMPLES_DIR):
        return images, student_ids

    for filename in sorted(os.listdir(SAMPLES_DIR)):
        if filename.lower().endswith(".png"):
            student_id = filename[:-4]
            img = cv2.imread(os.path.join(SAMPLES_DIR, filename), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                images.append(img)
                student_ids.append(student_id)
    return images, student_ids


def _train_recognizer():
    """(Re)train the LBPH recognizer from all currently registered student samples."""
    global _recognizer, _label_map, _trained_student_ids

    if not _has_lbph():
        raise RuntimeError(
            "cv2.face.LBPHFaceRecognizer_create is not available. "
            "Install 'opencv-contrib-python' instead of 'opencv-python' "
            "(pip uninstall opencv-python && pip install opencv-contrib-python)."
        )

    images, student_ids = _load_all_samples()

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    _label_map = {}

    if len(images) == 0:
        # Nothing registered yet — keep an untrained (but valid) recognizer.
        _recognizer = recognizer
        _trained_student_ids = set()
        _save_model()
        return

    labels = []
    for idx, sid in enumerate(student_ids):
        _label_map[idx] = sid
        labels.append(idx)

    recognizer.train(images, np.array(labels))
    _recognizer = recognizer
    _trained_student_ids = set(student_ids)
    _save_model()


def _save_model():
    """Persist the trained model + label map to disk (so a server restart doesn't lose training)."""
    try:
        if _recognizer is not None:
            _recognizer.write(MODEL_PATH)
        with open(LABEL_MAP_PATH, "wb") as f:
            pickle.dump(_label_map, f)
    except Exception:
        # Non-fatal: worst case we just retrain next time from the samples on disk.
        pass


def _load_model_from_disk():
    global _recognizer, _label_map, _trained_student_ids
    if not (os.path.exists(MODEL_PATH) and os.path.exists(LABEL_MAP_PATH)):
        return False
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(MODEL_PATH)
        with open(LABEL_MAP_PATH, "rb") as f:
            label_map = pickle.load(f)
        _recognizer = recognizer
        _label_map = label_map
        _trained_student_ids = set(label_map.values())
        return True
    except Exception:
        return False


def _ensure_trained():
    """Make sure `_recognizer` reflects the current set of registered students."""
    _, current_ids = _load_all_samples()
    current_ids = set(current_ids)

    global _recognizer
    if _recognizer is not None and _trained_student_ids == current_ids:
        return  # already up to date

    if _recognizer is None and _load_model_from_disk() and _trained_student_ids == current_ids:
        return  # loaded a still-valid model from disk

    _train_recognizer()


def recognize_faces(image_bgr):
    """
    Given a BGR image (from OpenCV / a decoded webcam frame), detect all faces and
    match them against registered students using the LBPH recognizer.

    Returns a list of dicts, matching the shape the rest of the app expects:
        [{"student_id": "...", "confidence": 0.87, "box": (top, right, bottom, left)}, ...]
    Unknown faces are returned with student_id = None.
    """
    _ensure_trained()

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    faces = detect_all_faces(gray)

    results = []
    for (x, y, w, h) in faces:
        face_crop = gray[y:y + h, x:x + w]
        face_resized = cv2.resize(face_crop, FACE_SIZE)

        student_id = None
        confidence = 0.0

        if _recognizer is not None and len(_label_map) > 0:
            try:
                label, distance = _recognizer.predict(face_resized)
                if distance <= CONFIDENCE_THRESHOLD and label in _label_map:
                    student_id = _label_map[label]
                    # Convert LBPH distance (lower = better, roughly 0-100+) into a
                    # 0-1 "confidence-like" score for display purposes only.
                    confidence = round(max(0.0, 1 - (distance / 100)), 2)
            except cv2.error:
                pass

        # box format kept as (top, right, bottom, left) to match the original API/JS overlay code.
        # Cast from numpy int32 (returned by detectMultiScale) to plain Python int so the box
        # is JSON-serializable when returned from the /recognize_frame endpoint.
        top, right, bottom, left = int(y), int(x + w), int(y + h), int(x)
        results.append({"student_id": student_id, "confidence": confidence, "box": (top, right, bottom, left)})

    return results


def decode_base64_image(base64_string):
    """Convert a base64-encoded data-URL (from the webcam JS) into an OpenCV BGR image."""
    import base64

    if "," in base64_string:
        base64_string = base64_string.split(",")[1]

    img_bytes = base64.b64decode(base64_string)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return image_bgr


def delete_encoding(student_id):
    """Remove a student's saved training sample (used when deleting a student)."""
    sample_path = os.path.join(SAMPLES_DIR, f"{student_id}.png")
    if os.path.exists(sample_path):
        os.remove(sample_path)
    _invalidate_model()
