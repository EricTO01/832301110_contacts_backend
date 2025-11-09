项目代码规范
来源声明

JavaScript: Airbnb JavaScript Style Guide
HTML/CSS: Google HTML/CSS Style Guide
Python: PEP 8
Flask: Flask官方最佳实践
MySQL: MySQL官方文档


前端规范
JavaScript
javascriptjavascript复制javascript复制// 使用const/let，箭头函数
const getUser = async (id) => {
  const response = await fetch(`/api/users/${id}`);
  return response.json();
};

// 模板字符串和解构
const { name, email } = user;
const greeting = `Hello, ${name}!`;
HTML
htmlhtml运行复制html运行复制<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>页面标题</title>
</head>
<body>
    <main>
        <h1>主要内容</h1>
    </main>
</body>
</html>
CSS (BEM命名)
csscss复制css复制.user-card { /* Block */ }
.user-card__name { /* Element */ }
.user-card--active { /* Modifier */ }

后端规范
Python/Flask
pythonpython复制python复制from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    """获取用户信息"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify(user.to_dict())

# 模型类
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)

MySQL规范
表设计
sqlCREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB CHARSET=utf8mb4;
安全查询
python 正确：参数化查询
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# 错误：字符串拼接
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
