from flask import Flask, render_template, request, redirect, session, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'secret_key_123'

# ================== CONFIG ==================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123'
app.config['MYSQL_DB'] = 'image_saas'

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

mysql = MySQL(app)

# ================== HOME ==================
@app.route('/')
def home():
    return redirect('/login')

# ================== REGISTER ==================
@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        email = request.form['username'].strip()
        password = request.form['password']

        # KIỂM TRA CÓ @ HAY KHÔNG
        if '@' not in email:
            msg = 'Email không hợp lệ (phải chứa @)'
            return render_template('register.html', message=msg)

        # Mã hóa mật khẩu
        password_hash = generate_password_hash(password)

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s", (email,))
        if cur.fetchone():
            msg = 'Email đã tồn tại'
        else:
            cur.execute(
                "INSERT INTO users(username, password, plan) VALUES(%s,%s,'FREE')",
                (email, password_hash)
            )
            mysql.connection.commit()
            return redirect('/login')

    return render_template('register.html', message=msg)


# ================== LOGIN ==================
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id, password FROM users WHERE username=%s",
            (email,)
        )
        user = cur.fetchone()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            return redirect('/gallery')
        else:
            msg = 'Sai email hoặc mật khẩu'

    return render_template('login.html', message=msg)

# ================== LOGOUT ==================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ================== GALLERY ==================
@app.route('/gallery', methods=['GET', 'POST'])
def gallery():
    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()

    # Upload ảnh
    if request.method == 'POST':
        file = request.files['image']
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(UPLOAD_FOLDER, filename))

            cur.execute(
                "INSERT INTO images(user_id, filename) VALUES(%s,%s)",
                (session['user_id'], filename)
            )
            mysql.connection.commit()

    # Lấy ảnh
    cur.execute(
        "SELECT id, filename FROM images WHERE user_id=%s",
        (session['user_id'],)
    )
    images = cur.fetchall()

    image_list = [{'id': i[0], 'filename': i[1]} for i in images]

    return render_template('gallery.html', images=image_list)

# ================== DELETE IMAGE ==================
@app.route('/delete/<int:image_id>', methods=['POST'])
def delete_image(image_id):
    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT filename FROM images WHERE id=%s AND user_id=%s",
        (image_id, session['user_id'])
    )
    img = cur.fetchone()

    if img:
        filepath = os.path.join(UPLOAD_FOLDER, img[0])
        if os.path.exists(filepath):
            os.remove(filepath)

        cur.execute("DELETE FROM images WHERE id=%s", (image_id,))
        mysql.connection.commit()

    return redirect('/gallery')

# ================== SERVE IMAGE ==================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ================== PRICING ==================
@app.route('/pricing')
def pricing():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('pricing.html')

# ================== CHANGE PASSWORD ==================
@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect('/login')

    msg = ''
    if request.method == 'POST':
        old = request.form['old_password']
        new = request.form['new_password']

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT password FROM users WHERE id=%s",
            (session['user_id'],)
        )
        current = cur.fetchone()[0]

        if not check_password_hash(current, old):
            msg = 'Mật khẩu cũ không đúng'
        else:
            cur.execute(
                "UPDATE users SET password=%s WHERE id=%s",
                (generate_password_hash(new), session['user_id'])
            )
            mysql.connection.commit()
            msg = 'Đổi mật khẩu thành công'

    return render_template('change_password.html', message=msg)

# ================== FORGOT PASSWORD ==================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    msg = ''
    if request.method == 'POST':
        email = request.form['username']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s", (email,))
        user = cur.fetchone()

        if user:
            session['reset_user_id'] = user[0]
            return redirect('/reset-password')
        else:
            msg = 'Email không tồn tại'

    return render_template('forgot_password.html', message=msg)

# ================== RESET PASSWORD ==================
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_user_id' not in session:
        return redirect('/login')

    msg = ''
    if request.method == 'POST':
        new = request.form['new_password']

        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE users SET password=%s WHERE id=%s",
            (generate_password_hash(new), session['reset_user_id'])
        )
        mysql.connection.commit()
        session.pop('reset_user_id')
        msg = 'Đặt lại mật khẩu thành công'

    return render_template('reset_password.html', message=msg)

# ================== RUN ==================
if __name__ == '__main__':
    app.run(debug=True)
