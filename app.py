"""
app.py
------
AI-Based Classroom Attendance System using Face Recognition.
Main Flask application: routes, request handling, and view logic.

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""

import os
import csv
import io
from datetime import datetime

import cv2
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, send_file, Response
)
from werkzeug.utils import secure_filename

from utils import database as db
from utils.face_recognition_utils import (
    generate_encoding, recognize_faces, decode_base64_image,
    delete_encoding, NoFaceDetectedError, MultipleFacesError
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENTS_DIR = os.path.join(BASE_DIR, "dataset", "students")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app = Flask(__name__)
app.secret_key = "classroom-attendance-secret-key-change-in-production"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

# Ensure required folders exist at startup
for folder in [
    os.path.join(BASE_DIR, "database"),
    STUDENTS_DIR,
    os.path.join(STUDENTS_DIR, "samples"),
    os.path.join(STUDENTS_DIR, "model"),
    UPLOADS_DIR,
    os.path.join(BASE_DIR, "static", "css"),
    os.path.join(BASE_DIR, "static", "js"),
    os.path.join(BASE_DIR, "static", "images"),
]:
    os.makedirs(folder, exist_ok=True)

db.init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/student_photo/<path:filename>")
def student_photo(filename):
    """Serve student reference photos stored in dataset/students/ (outside static/)."""
    from flask import send_from_directory
    return send_from_directory(STUDENTS_DIR, filename)


# ---------------------------------------------------------------------------
# HOME / DASHBOARD
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    total, present, absent, pct = db.today_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    todays_records = db.get_attendance_by_date(today)
    return render_template(
        "dashboard.html",
        total=total, present=present, absent=absent, pct=pct,
        records=todays_records, today=today
    )


# ---------------------------------------------------------------------------
# STUDENT REGISTRATION
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        name = request.form.get("name", "").strip()

        if not student_id or not name:
            flash("Student ID and Name are required.", "danger")
            return redirect(url_for("register"))

        if db.get_student_by_id(student_id):
            flash(f"Student ID '{student_id}' is already registered.", "danger")
            return redirect(url_for("register"))

        image_file = request.files.get("image_file")
        webcam_data = request.form.get("webcam_image")

        image_bytes = None
        ext = "jpg"

        if image_file and image_file.filename and allowed_file(image_file.filename):
            ext = secure_filename(image_file.filename).rsplit(".", 1)[1].lower()
            image_bytes = image_file.read()
        elif webcam_data:
            import base64
            if "," in webcam_data:
                webcam_data = webcam_data.split(",")[1]
            image_bytes = base64.b64decode(webcam_data)
            ext = "jpg"
        else:
            flash("Please upload a photo or capture one using the webcam.", "danger")
            return redirect(url_for("register"))

        safe_name = secure_filename(f"{student_id}.{ext}")
        image_path = os.path.join(STUDENTS_DIR, safe_name)
        with open(image_path, "wb") as f:
            f.write(image_bytes)

        try:
            encoding_path = generate_encoding(image_path, student_id)
        except NoFaceDetectedError as e:
            os.remove(image_path)
            flash(str(e), "danger")
            return redirect(url_for("register"))
        except MultipleFacesError as e:
            os.remove(image_path)
            flash(str(e), "danger")
            return redirect(url_for("register"))
        except Exception as e:
            os.remove(image_path)
            flash(f"Error processing face image: {e}", "danger")
            return redirect(url_for("register"))

        relative_image_path = os.path.join("dataset", "students", safe_name)
        success, message = db.add_student(student_id, name, relative_image_path, encoding_path)

        if success:
            flash(f"Student '{name}' registered successfully!", "success")
            return redirect(url_for("students"))
        else:
            os.remove(image_path)
            delete_encoding(student_id)
            flash(message, "danger")
            return redirect(url_for("register"))

    return render_template("register.html")


# ---------------------------------------------------------------------------
# STUDENT MANAGEMENT
# ---------------------------------------------------------------------------

@app.route("/students")
def students():
    query = request.args.get("q", "").strip()
    student_list = db.search_students(query) if query else db.get_all_students()
    return render_template("students.html", students=student_list, query=query)


@app.route("/students/delete/<student_id>", methods=["POST"])
def delete_student_route(student_id):
    student = db.get_student_by_id(student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("students"))

    image_full_path = os.path.join(BASE_DIR, student["image_path"])
    if os.path.exists(image_full_path):
        os.remove(image_full_path)
    delete_encoding(student_id)
    db.delete_student(student_id)

    flash(f"Student '{student['name']}' deleted.", "success")
    return redirect(url_for("students"))


# ---------------------------------------------------------------------------
# LIVE ATTENDANCE (WEBCAM)
# ---------------------------------------------------------------------------

@app.route("/live_attendance")
def live_attendance():
    return render_template("live_attendance.html")


@app.route("/recognize_frame", methods=["POST"])
def recognize_frame():
    """
    Receives a single base64-encoded webcam frame from the browser (JS),
    runs face recognition, marks attendance for recognized students,
    and returns JSON describing what was found (for on-screen overlay).
    """
    data = request.get_json(silent=True)
    if not data or "image" not in data:
        return jsonify({"error": "No image data received."}), 400

    try:
        frame = decode_base64_image(data["image"])
        if frame is None:
            return jsonify({"error": "Could not decode image."}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid image data: {e}"}), 400

    try:
        results = recognize_faces(frame)
    except Exception as e:
        return jsonify({"error": f"Recognition failed: {e}"}), 500

    recognized = []
    for r in results:
        top, right, bottom, left = r["box"]
        if r["student_id"]:
            student = db.get_student_by_id(r["student_id"])
            name = student["name"] if student else "Unknown"
            db.mark_attendance(r["student_id"], status="Present")
            recognized.append({
                "student_id": r["student_id"],
                "name": name,
                "confidence": r["confidence"],
                "box": [top, right, bottom, left],
                "known": True
            })
        else:
            recognized.append({
                "student_id": None,
                "name": "Unknown",
                "confidence": 0,
                "box": [top, right, bottom, left],
                "known": False
            })

    return jsonify({"faces": recognized})


# ---------------------------------------------------------------------------
# UPLOAD CLASSROOM IMAGE ATTENDANCE
# ---------------------------------------------------------------------------

@app.route("/upload_attendance", methods=["GET", "POST"])
def upload_attendance():
    if request.method == "POST":
        image_file = request.files.get("classroom_image")

        if not image_file or image_file.filename == "":
            flash("Please select a classroom image to upload.", "danger")
            return redirect(url_for("upload_attendance"))

        if not allowed_file(image_file.filename):
            flash("Invalid file type. Please upload a PNG or JPG image.", "danger")
            return redirect(url_for("upload_attendance"))

        filename = secure_filename(f"classroom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        save_path = os.path.join(UPLOADS_DIR, filename)
        image_file.save(save_path)

        frame = cv2.imread(save_path)
        if frame is None:
            flash("Could not read the uploaded image. Please try another file.", "danger")
            return redirect(url_for("upload_attendance"))

        try:
            results = recognize_faces(frame)
        except Exception as e:
            flash(f"Face recognition failed: {e}", "danger")
            return redirect(url_for("upload_attendance"))

        if len(results) == 0:
            flash("No faces were detected in the uploaded classroom image.", "warning")
            return redirect(url_for("upload_attendance"))

        recognized_names = []
        unknown_count = 0
        today = datetime.now().strftime("%Y-%m-%d")

        for r in results:
            if r["student_id"]:
                student = db.get_student_by_id(r["student_id"])
                if student:
                    db.mark_attendance(r["student_id"], status="Present", date=today)
                    recognized_names.append(student["name"])
            else:
                unknown_count += 1

        # Any registered student not detected in this image is marked Absent
        db.mark_absent_for_unmarked(today)

        flash(
            f"Processed image: {len(recognized_names)} student(s) recognized and marked Present"
            + (f", {unknown_count} unknown face(s) ignored." if unknown_count else "."),
            "success"
        )
        return redirect(url_for("attendance_records"))

    return render_template("upload_attendance.html")


# ---------------------------------------------------------------------------
# ATTENDANCE RECORDS
# ---------------------------------------------------------------------------

@app.route("/attendance_records")
def attendance_records():
    date_filter = request.args.get("date", "").strip()
    if date_filter:
        records = db.get_attendance_by_date(date_filter)
    else:
        records = db.get_all_attendance()
    return render_template("attendance_records.html", records=records, date_filter=date_filter)


@app.route("/edit_attendance/<int:record_id>", methods=["GET", "POST"])
def edit_attendance(record_id):
    record = db.get_attendance_record(record_id)
    if not record:
        flash("Attendance record not found.", "danger")
        return redirect(url_for("attendance_records"))

    if request.method == "POST":
        new_status = request.form.get("status")
        if new_status not in ("Present", "Absent"):
            flash("Invalid status.", "danger")
            return redirect(url_for("edit_attendance", record_id=record_id))
        db.update_attendance_status(record_id, new_status)
        flash(f"Attendance for {record['name']} updated to {new_status}.", "success")
        return redirect(url_for("attendance_records"))

    return render_template("edit_attendance.html", record=record)


# ---------------------------------------------------------------------------
# EXPORT CSV
# ---------------------------------------------------------------------------

@app.route("/export_csv")
def export_csv():
    date_filter = request.args.get("date", "").strip()
    records = db.get_attendance_by_date(date_filter) if date_filter else db.get_all_attendance()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Student Name", "Date", "Time", "Status"])
    for r in records:
        writer.writerow([r["student_id"], r["name"], r["date"], r["time"], r["status"]])

    output.seek(0)
    filename = f"attendance_{date_filter or 'all'}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


# ---------------------------------------------------------------------------
# ERROR HANDLERS
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("base.html", content_404=True), 404


@app.errorhandler(500)
def server_error(e):
    flash(f"An internal error occurred: {e}", "danger")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
