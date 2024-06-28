from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory, make_response,session
import csv
import os
from PIL import Image as PILImage
from xhtml2pdf import pisa
import io
from flask import Flask, jsonify
from pymongo import MongoClient
from werkzeug.security import check_password_hash


app = Flask(__name__)
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client['ALL_DATA']  # Your MongoDB database name

# Collection names
STUDENTS_COLLECTION = db['students']
MARKS_COLLECTION = db['marks']
FACULTY_COLLECTION = db['faculty']
ADMIN_COLLECTION = db['admin']
ALL_COLLECTION = db['studenttt']

app.secret_key = 'your_secret_key'   # Necessary for flash messages

ADMIN_CSV ='admin.csv'

@app.route('/')
def index():
    user_type = session.get('user_type')
    return render_template('index.html', user_type=user_type)

@app.route('/about')
def aboutus():
    user_type = session.get('user_type')
    return render_template('aboutus.html', user_type=user_type)

@app.route('/contact')
def contactus():
    user_type = session.get('user_type')
    return render_template('contactus.html', user_type=user_type)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if the email and password match any entry in the MongoDB collection
        user_type, user_id = validate_login(email, password)

        if user_type:
            # Set the user_id in the session
            session['user_id'] = user_id
            session['user_type'] = user_type
            if user_type == 'student':
                return redirect(url_for('vieww', student_id=user_id))
            elif user_type == 'faculty':
                return redirect(url_for('faculty', faculty_id=user_id))
            elif user_type == 'admin':
                return redirect(url_for('admin', user_id=user_id))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

def validate_login(Email, Password):
    student = ALL_COLLECTION.find_one({"Email": Email, 'Password': Password})
    print("VALIDATE LOGIN")
    if student:
        print("IN VALIDATE")
        return student['Type'], student['student_Id']
    return None, None

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_type', None)
    return redirect(url_for('login'))


@app.route('/admin/<user_id>')
def admin(user_id):
    print(user_id)
    user_type = session.get('user_type')
    if user_id and session.get('user_type') == 'admin':
        admin = get_admin_details(user_id)
        return render_template('admin.html', admin=admin, user_type=user_type)
    else:
        flash('You must be logged in as an admin to access this page.', 'error')
        return redirect(url_for('login'))

def get_admin_details(user_id):
    print(f"Fetching details for admin_id: {user_id}")
    admin = ADMIN_COLLECTION.find_one({"admin_id": user_id})
    if admin:
        print(f"Admin details found: {admin}")
        return {
            'name': admin['name'],
            'admin_id': admin['admin_id'],
            'email': admin['email'],
        }
    else:
        print(f"Admin with ID {user_id} not found in the database.")
        return None


@app.route('/faculty/<faculty_id>')
def faculty(faculty_id):
    session_user_id = session.get('user_id')
    user_type = session.get('user_type')

    if session_user_id:
        faculty_details = get_faculty_details(faculty_id)
        if not faculty_details:
            flash('Faculty details not found.', 'error')
            return redirect(url_for('login'))
        return render_template('faculty.html', faculty=faculty_details, user_type=user_type, user_id=faculty_id)
    else:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))

def get_faculty_details(faculty_id):
    faculty = FACULTY_COLLECTION.find_one({"faculty_id": int(faculty_id)})
    if faculty:
        faculty_info = {
            "faculty_id": faculty["faculty_id"],
            "name": faculty["name"],
            "department": faculty["department"],
            "email": faculty["email"],
            "password": faculty["password"],  # Ensure this is hashed
            "subject": faculty["subject"]
        }
        return faculty_info
    return None

@app.route('/facultyA')
def facultyA():
    user_type = session.get('user_type')
    faculty = FACULTY_COLLECTION.find()
    return render_template('facultyA.html', faculty=faculty, user_type=user_type)


@app.route('/student')
def student():
    user_type = session.get('user_type')
    students = list(STUDENTS_COLLECTION.find({}))
    return render_template('student.html', students=students, user_type=user_type)

picFolder = os.path.join('static', 'pics')
app.config['UPLOAD_FOLDER'] = picFolder

# Function to resize an image
def resize_image(input_path, output_path, width, height):
    with PILImage.open(input_path) as img:
        img = img.resize((width, height), PILImage.ANTIALIAS)
        img.save(output_path)

@app.route('/resize_image/<student_id>/<int:width>/<int:height>')
def resize_image_route(student_id, width, height):
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{student_id}.jpg")
    if not os.path.exists(input_path):
        return "Image not found", 404
    
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{student_id}_{width}x{height}.jpg")
    resize_image(input_path, output_path, width, height)
    return send_from_directory(app.config['UPLOAD_FOLDER'], f"{student_id}_{width}x{height}.jpg")


@app.route('/vieww/<student_id>', methods=['POST', 'GET'])
def vieww(student_id):
    user_type = session.get('user_type')

    # Fetch the student details
    student = STUDENTS_COLLECTION.find_one({"student_id": student_id})


    student_details = {
        "id": student['student_id'],
        "name": student['name'],
        "branch": student['branch'],
        "year": student['year']
    }

    # Fetch student marks
    student_marks = list(MARKS_COLLECTION.find({"student_id": student_id}))

    # Convert marks to a format suitable for the template
    student_marks = [{
        "student_id": mark['student_id'],
        "subject": mark['Subject'],
        "marks": mark['Marks'],
        "total": mark['Total']
    } for mark in student_marks]

    return render_template('vieww.html', marks=student_marks, student=student_details, user_type=user_type)

@app.route('/form')
def form():
    
    user_type = session.get('user_type')
    return render_template('form.html', user_type=user_type)

@app.route('/formm')
def formm():
    user_type = session.get('user_type')
    return render_template('formm.html', user_type=user_type)

@app.route('/formFaculty')
def formFaculty():
    user_type = session.get('user_type')
    return render_template('add_faculty_form.html', user_type=user_type)

@app.route('/submit', methods=['POST'])
def submit():
    student_id = request.form['student_id']
    name = request.form['name']
    branch = request.form['branch']
    year = request.form['year']

    # Check if student_id already exists in the database
    existing_student = STUDENTS_COLLECTION.find_one({"student_id": student_id})
    if existing_student:
        flash('Student ID already exists')
        return redirect(url_for('form'))

    # Insert new student data into MongoDB
    STUDENTS_COLLECTION.insert_one({
        "student_id": student_id,
        "name": name,
        "branch": branch,
        "year": int(year)
    })

    return redirect(url_for('student'))


@app.route('/submitf', methods=['POST'])
def submitf():
    Faculty_ID = int(request.form['InputFacultyID'])
    FName = request.form['InputName']
    Department = request.form['InputDepartment']
    Email = request.form['InputFUser']
    Password = request.form['InputFPass']
    Subject = request.form['InputFSub']

    # Check if the faculty ID already exists
    existing_faculty = FACULTY_COLLECTION.find_one({'faculty_id': Faculty_ID})
    if existing_faculty:
        flash('Faculty ID already exists', 'danger')
        return redirect(url_for('formFaculty'))

    # Insert new faculty record into MongoDB
    faculty_record = {
        'faculty_id': Faculty_ID,
        'name': FName,
        'department': Department,
        'email': Email,
        'password': Password,
        'subject': Subject
    }
    FACULTY_COLLECTION.insert_one(faculty_record)

    flash('Faculty added successfully', 'success')
    return redirect(url_for('facultyA'))

@app.route('/submitt', methods=['POST'])
def submitt():
    student_id = request.form['student_id']
    subject = request.form['subject']
    marks = request.form['marks']
    total = request.form['total']

    # Check if the student ID exists in the students collection
    student_exists = STUDENTS_COLLECTION.find_one({"student_id": student_id})

    if not student_exists:
        flash('Student ID does not exist', 'error')
        return redirect(url_for('formm'))

    # Check if the marks for this subject and student already exist
    marks_exist = MARKS_COLLECTION.find_one({"student_id": student_id, "Subject": subject})

    if marks_exist:
        flash('Marks for this subject are already entered for this student', 'error')
        return redirect(url_for('formm'))

    # Insert the new marks into the marks collection
    MARKS_COLLECTION.insert_one({
        "student_id": student_id,
        "Subject": subject,
        "Marks": int(marks),
        "Total": int(total)
    })

    flash('Marks added successfully', 'success')
    return redirect(url_for('vieww', student_id=student_id))

@app.route('/edit_faculty', methods=['POST'])
def edit_faculty():
    user_type = session.get('user_type')
    serial_no = int(request.form['serial_no'])
    faculty = list(FACULTY_COLLECTION.find({}))  # Fetch all faculty
    faculty_to_edit = faculty[serial_no - 1] 
    return render_template('upadte2.html', faculty=faculty_to_edit, user_type=user_type, serial_no=serial_no)


@app.route('/edit', methods=['POST'])
def edit():
    user_type = session.get('user_type')
    serial_no = int(request.form['serial_no'])
    students = list(STUDENTS_COLLECTION.find({}))
    student_to_edit = students[serial_no - 1]  # Get student by serial number
    return render_template('update.html', student=student_to_edit, user_type=user_type,serial_no=serial_no)

@app.route('/update', methods=['POST'])
def update():
    serial_no = int(request.form['serial_no'])
    student_id = request.form['studentId']
    name = request.form['studentName']
    branch = request.form['studentBranch']
    year = int(request.form['studentYear'])

    # Update the student document in MongoDB
    STUDENTS_COLLECTION.update_one(
        {"student_id": student_id},
        {"$set": {"name": name, "branch": branch, "year": year}}
    )

    return redirect(url_for('student'))

    

@app.route('/update2', methods=['POST'])
def update2():
    # serial_no = int(request.form['serial_no'])
    faculty_id = int(request.form['InputFacultyID'])  # Get faculty_id from the form
    name = request.form['InputName']
    department = request.form['InputDepartment']
    email = request.form['InputFUser']
    subject = request.form['InputFSub']

    # Update the faculty document
    FACULTY_COLLECTION.update_one(
        {'faculty_id': faculty_id},
        {"$set": {'name': name, 'department': department, 'email': email, 'subject': subject}}
    )
    
    return redirect(url_for('facultyA'))  # Assuming 'facultyA' is the correct route to redirect after update


@app.route('/delete', methods=['POST'])
def delete():
    serial_no = int(request.form['serial_no'])
    students = list(STUDENTS_COLLECTION.find({}))
    
    if 0 <= serial_no - 1 < len(students):
        student_to_delete = students.pop(serial_no - 1)
        
        # Update MongoDB collection after deleting the document
        for index, student in enumerate(students[serial_no - 1:], start=serial_no):
            STUDENTS_COLLECTION.update_one(
                {"student_id": student['student_id']},
                {"$set": {"serial_no": index}}
            )
        
        # Delete the document from MongoDB
        STUDENTS_COLLECTION.delete_one({"student_id": student_to_delete['student_id']})
        flash('Student deleted successfully', 'success')
    else:
        flash('Invalid serial number', 'error')

    return redirect(url_for('student'))


@app.route('/delete_faculty', methods=['POST'])
def delete_faculty():
    serial_no = int(request.form['serial_no'])
    faculty = list(FACULTY_COLLECTION.find({}))
    
    if 0 <= serial_no - 1 < len(faculty):
        faculty_to_delete = faculty.pop(serial_no - 1)
        
        # Update MongoDB collection after deleting the document
        for index, fac in enumerate(faculty[serial_no - 1:], start=serial_no):
            FACULTY_COLLECTION.update_one(
                {"faculty_id": fac['faculty_id']},
                {"$set": {"serial_no": index}}
            )
        
        # Delete the document from MongoDB
        FACULTY_COLLECTION.delete_one({"faculty_id": faculty_to_delete['faculty_id']})
        flash('Faculty deleted successfully', 'success')
    else:
        flash('Invalid serial number', 'error')

    return redirect(url_for('facultyA'))


@app.route('/delete_mark', methods=['POST'])
def delete_mark():
    student_id = request.form['student_id']
    subject = request.form['subject']

    # Delete the specific document in the marks collection
    result = MARKS_COLLECTION.delete_one({"student_id": student_id, "Subject": subject})

    if result.deleted_count == 1:
        flash('Mark deleted successfully.', 'success')
    else:
        flash('Failed to delete mark: Record not found.', 'error')

    return redirect(url_for('vieww', student_id=student_id))


@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    student_id = request.form.get('student_id')

    # Fetch student details from MongoDB
    student = STUDENTS_COLLECTION.find_one({"student_id": student_id})
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('vieww', student_id=student_id))

    # Fetch student marks from MongoDB
    student_marks = list(MARKS_COLLECTION.find({"student_id": student_id}))

    # Convert marks to a format suitable for the template
    student_marks = [{
        "student_id": mark['student_id'],
        "subject": mark['Subject'],
        "marks": mark['Marks'],
        "total": mark['Total']
    } for mark in student_marks]

    # Render view result page content to HTML
    html_content = render_template('pdf_template.html', marks=student_marks, student=student, user_image=url_for('resize_image_route', student_id=student_id, width=180, height=200))

    # Convert HTML to PDF using xhtml2pdf
    pdf = convert_html_to_pdf(html_content)

    # Set up response headers
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=student_result_{student_id}.pdf'

    return response

def convert_html_to_pdf(source_html):
    result = io.BytesIO()
    pdf = pisa.CreatePDF(io.StringIO(source_html), dest=result)
    if not pdf.err:
        return result.getvalue()
    return None

@app.route('/edit_mark', methods=['POST'])
def edit_mark():
    user_type = session.get('user_type')
    student_id = request.form['student_id']
    subject = request.form['subject']
    marks = request.form['marks']
    total = request.form['total']
    return render_template('edit_mark.html', user_type=user_type, student_id=student_id, subject=subject, marks=marks, total=total)


@app.route('/update_mark', methods=['POST'])
def update_mark():
    student_id = request.form['student_id']
    subject = request.form['subject']
    new_marks = request.form['marks']
    new_total = request.form['total']

    # Update the specific document in the marks collection
    result = MARKS_COLLECTION.update_one(
        {"student_id": student_id, "Subject": subject},
        {"$set": {"Marks": int(new_marks), "Total": int(new_total)}}
    )

    if result.matched_count == 0:
        flash('Mark update failed: Record not found.', 'error')
    elif result.modified_count == 0:
        flash('Mark update failed: No changes were made.', 'warning')
    else:
        flash('Marks updated successfully.', 'success')

    return redirect(url_for('vieww', student_id=student_id))

if __name__ == '__main__':
    app.run(debug=True)


