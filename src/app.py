from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
from datetime import timedelta
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
Session(app)

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'contact_management',  # 修改为统一使用contact_management
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'use_unicode': True
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root', 
            password='123456',
            database='contact_management',  # 保持一致
            charset='utf8mb4',
            use_unicode=True,
            autocommit=True
        )
        print(f"✅ 数据库连接成功: {conn.database}")
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        raise e
# 首页/登录页
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# 用户注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # 验证输入
        if len(username) < 3:
            return jsonify({'success': False, 'message': '用户名至少3位'})
        if len(password) < 6:
            return jsonify({'success': False, 'message': '密码至少6位'})
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return jsonify({'success': False, 'message': '用户名只能包含字母、数字和下划线'})
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', 
                          (username, hashed_password))
            conn.commit()
            return jsonify({'success': True, 'message': '注册成功，请登录'})
        except mysql.connector.IntegrityError:
            return jsonify({'success': False, 'message': '用户名已存在'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'注册失败: {str(e)}'})
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
    
    return render_template('register.html')

# 用户登录
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'success': False, 'message': '请输入用户名和密码'})
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({'success': True, 'message': '登录成功'})
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'登录失败: {str(e)}'})
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# 用户退出
@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'success')
    return redirect(url_for('index'))

# 仪表盘/联系人列表
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    search = request.args.get('search', '').strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if search:
            cursor.execute('''
                SELECT * FROM contacts 
                WHERE user_id = %s AND (name LIKE %s OR phone LIKE %s)
                ORDER BY created_at DESC
            ''', (session['user_id'], f'%{search}%', f'%{search}%'))
        else:
            cursor.execute('''
                SELECT * FROM contacts 
                WHERE user_id = %s 
                ORDER BY created_at DESC
            ''', (session['user_id'],))
        
        contacts = cursor.fetchall()
        return render_template('dashboard.html', contacts=contacts, search=search)
    except Exception as e:
        flash(f'加载联系人失败: {str(e)}', 'error')
        return render_template('dashboard.html', contacts=[], search=search)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# 添加联系人
@app.route('/api/contacts', methods=['POST'])
def add_contact():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        # 验证输入
        if not name:
            return jsonify({'success': False, 'message': '姓名不能为空'})
        if len(name) > 100:
            return jsonify({'success': False, 'message': '姓名过长'})
        if not phone:
            return jsonify({'success': False, 'message': '电话不能为空'})
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return jsonify({'success': False, 'message': '请输入有效的手机号码'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已存在相同电话的联系人
        cursor.execute('SELECT id FROM contacts WHERE user_id = %s AND phone = %s', 
                      (session['user_id'], phone))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': '该电话已存在'})
        
        # 插入新联系人
        cursor.execute('''
            INSERT INTO contacts (user_id, name, phone, address) 
            VALUES (%s, %s, %s, %s)
        ''', (session['user_id'], name, phone, address))
        conn.commit()
        
        # 获取新创建的联系人信息
        contact_id = cursor.lastrowid
        cursor.execute('SELECT * FROM contacts WHERE id = %s', (contact_id,))
        new_contact = cursor.fetchone()
        
        return jsonify({
            'success': True, 
            'message': f'联系人 {name} 添加成功',
            'contact': new_contact
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# 删除联系人
@app.route('/api/contacts/<int:contact_id>', methods=['DELETE'])  
def delete_contact(contact_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查联系人是否存在且属于当前用户
        cursor.execute('SELECT id FROM contacts WHERE id = %s AND user_id = %s', 
                      (contact_id, session['user_id']))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': '联系人不存在或无权操作'})
        
        # 执行删除
        cursor.execute('DELETE FROM contacts WHERE id = %s', (contact_id,))
        conn.commit()
        
        return jsonify({'success': True, 'message': '联系人删除成功'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# 获取联系人统计
@app.route('/api/stats')
def get_stats():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM contacts WHERE user_id = %s', 
                      (session['user_id'],))
        result = cursor.fetchone()
        return jsonify({'success': True, 'count': result[0]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
@app.route('/api/contacts/<int:contact_id>', methods=['PUT'])
def update_contact(contact_id):
    """更新联系人信息"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        # 获取表单数据
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        # 验证必填字段
        if not name:
            return jsonify({'success': False, 'message': '姓名不能为空'})
        if not phone:
            return jsonify({'success': False, 'message': '电话不能为空'})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查联系人是否存在且属于当前用户
        cursor.execute('SELECT id FROM contacts WHERE id = %s AND user_id = %s', 
                      (contact_id, session['user_id']))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': '联系人不存在或无权操作'})
        
        # 检查电话是否重复（排除当前联系人）
        cursor.execute('SELECT id FROM contacts WHERE phone = %s AND id != %s AND user_id = %s', 
                      (phone, contact_id, session['user_id']))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': '该电话已存在'})
        
        # 更新联系人信息
        cursor.execute('''
            UPDATE contacts 
            SET name = %s, phone = %s, address = %s 
            WHERE id = %s AND user_id = %s
        ''', (name, phone, address, contact_id, session['user_id']))
        
        conn.commit()
        
        return jsonify({
            'success': True, 
            'message': f'联系人 {name} 更新成功'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)