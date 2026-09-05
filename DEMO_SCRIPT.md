# Demo Video Script (2–3 minutes)
### AI-Based Classroom Attendance System using Face Recognition

Read the narration lines aloud while performing the matching on-screen action.

---

**[0:00 – 0:15] Introduction**
> "Hi, this is my final-year project: an AI-based classroom attendance system that uses face
> recognition to automatically mark student attendance, replacing manual roll-call. Let me walk you
> through how it works."

*(Show the Dashboard page briefly.)*

---

**[0:15 – 0:40] Student Registration**
> "First, I'll register a student. I'll go to 'Register Student', enter their name and register number,
> and capture their photo using the webcam."

*(Navigate to Register Student → fill name/ID → click "Use Webcam" tab → Start Camera → Capture Photo →
Save Student.)*

> "The system detects the face, generates a unique face encoding, and saves the student record. Let's
> register two or three more students the same way."

*(Repeat quickly for 2–3 students, or show one via file upload to demonstrate both options.)*

---

**[0:40 – 0:55] Students List**
> "Here's the Students List page, showing every registered student with their photo. I can search by
> name or ID, and delete a student if needed."

*(Navigate to Students List, show search box.)*

---

**[0:55 – 1:35] Live Face Recognition Attendance**
> "Now let's mark attendance live. I'll go to Live Attendance, start the camera, and click Start
> Recognition."

*(Navigate to Live Attendance → Start Camera → Start Recognition.)*

> "As you can see, the system draws a box around each detected face. Green boxes mean a registered
> student was recognized — their name appears, and they're instantly marked Present. Unrecognized faces
> show up in red as 'Unknown'. Notice it doesn't create duplicate records if the same student is seen
> multiple times."

*(Let it run for a few seconds, then click Stop.)*

---

**[1:35 – 2:00] Automatic Attendance Marking**
> "I can also mark attendance from a single classroom photo instead of a live feed. I'll upload a group
> photo here."

*(Navigate to Upload Classroom Image → choose file → Upload & Process.)*

> "The system detects every face in the photo, matches them against registered students, marks anyone
> recognized as Present, and — importantly — automatically marks every other registered student as
> Absent for today."

---

**[2:00 – 2:25] Dashboard Statistics**
> "Back on the Dashboard, we can see the live statistics update: total students, how many are present,
> how many are absent, and the overall attendance percentage for today."

*(Navigate to Dashboard, point out the stat cards and today's records table.)*

---

**[2:25 – 2:45] Manual Correction**
> "If a mistake happens — say a student was misidentified — the teacher can go to Attendance Records,
> click Edit next to any entry, and manually switch their status between Present and Absent."

*(Navigate to Attendance Records → Edit on a row → change status → Save.)*

---

**[2:45 – 3:00] CSV Export & Conclusion**
> "Finally, all attendance data can be exported as a CSV report with one click, ready to share or archive."

*(Click Export CSV, show the downloaded file briefly.)*

> "That's my AI-based classroom attendance system — built with Python, Flask, OpenCV, and face
> recognition, with a full teacher dashboard for management and correction. Thank you for watching."

*(End on Dashboard or title screen.)*
