from datetime import datetime
from flask import render_template, request, Flask, request, jsonify, session
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
from wxcloudrun.DeviceRoleManager import DeviceRoleManager
import requests
import jwt
import logging
from datetime import datetime, timezone, timedelta
from functools import wraps

from wxcloudrun.user import UserManager 
user_manager = UserManager()
device_manager = DeviceRoleManager()
JWT_SECRET = 'your-jwt-secret'  # 替换为实际的 JWT 密钥
JWT_EXPIRATION_HOURS = 24 * 7
# 微信小程序配置
APP_ID = "wx8446265bd2d968e9"
APP_SECRET = "dfddc06c807106ae6d67b639dcd926a4"


def generate_token(openid):
    """生成 JWT token"""
    payload = {
        'openid': openid,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)  # Token 有效期
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token
# JWT 装饰器，检查 token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 403

        try:
            token = token.replace("Bearer ", "")  # 去除 "Bearer " 前缀
            decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            openid = decoded_token.get('openid')
            if not openid:
                return jsonify({'message': 'Token is invalid!'}), 403
            # 将 openid 传递给视图函数
            return f(openid=openid, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 403
    return decorated


@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')

@app.route('/api/wechat_login', methods=['POST'])
def wechat_login():
    code = request.json.get('code')

    if not code:
        return jsonify({'success': False, 'msg': 'Missing code'}), 400

    # 调用微信API，获取 openid 和 session_key
    url = f"https://api.weixin.qq.com/sns/jscode2session?appid={APP_ID}&secret={APP_SECRET}&js_code={code}&grant_type=authorization_code"
    response = requests.get(url)
    data = response.json()

    if 'errcode' in data:
        return jsonify({'success': False, 'msg': 'WeChat login failed', 'details': data}), 400

    openid = data['openid']
    session_key = data['session_key']

    # 查找用户是否已经存在
    user = user_manager.find_user_by_openid(openid)
    if user:
        # 如果用户存在，则更新登录时间并设置 session
        user_manager.login_user(user)
        token = generate_token(openid)
        return jsonify({'success': True, 'msg': 'Login successful', 'token': token, 'nickname': user['nick_name']})
    else:
        nick_name = request.json.get('nickname', '默认昵称')

        new_user = user_manager.register_user(openid, nick_name)
        if new_user:
            user_manager.login_user(new_user)
            token = generate_token(openid)
            return jsonify({'success': True, 'msg': 'Registration and login successful', 'token': token, 'nickname': new_user['nick_name']})
        else:
            return jsonify({'success': False, 'msg': 'Registration failed'}), 500

@app.route('/api/bind_device', methods=['POST'])
@token_required  # 验证 token
def bind_device(openid):
    data = request.json
    device_id = data.get('device_id')

    if not device_id:
        return jsonify({"message": "device_id 是必需的"}), 400

    result = device_manager.bind_user_device(openid, device_id)
    if result:
        return jsonify({"message": "绑定成功", "data": result})
    else:
        return jsonify({"message": "绑定失败"}), 500
