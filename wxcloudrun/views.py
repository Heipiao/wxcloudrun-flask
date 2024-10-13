from datetime import datetime
from flask import render_template, request
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
import requests
import jwt
from flask import Flask, request, jsonify, session
import logging
from datetime import datetime, timezone, timedelta
from wxcloudrun.user import UserManager 
user_manager = UserManager()
JWT_SECRET = 'your-jwt-secret'  # 替换为实际的 JWT 密钥
JWT_EXPIRATION_HOURS = 24 * 7

def generate_token(openid):
    """生成 JWT token"""
    payload = {
        'openid': openid,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)  # Token 有效期
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token

@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/wechat_login', methods=['POST'])
def wechat_login():
    APP_ID = "wx8446265bd2d968e9"
    APP_SECRET = "dfddc06c807106ae6d67b639dcd926a4"
         
    code = request.json.get('code')

    if not code:
        return jsonify({'error': 'Missing code'}), 400

        # 调用微信API，获取 openid 和 session_key
    url = f"https://api.weixin.qq.com/sns/jscode2session?appid={APP_ID}&secret={APP_SECRET}&js_code={code}&grant_type=authorization_code"
            
    response = requests.get(url)
    data = response.json()

    if 'errcode' in data:
        return jsonify({'error': 'WeChat login failed', 'details': data}), 400

    openid = data['openid']
    session_key = data['session_key']

            # 查找用户是否已经存在
    user = user_manager.find_user_by_openid(openid)
    if user:
                # 如果用户存在，则更新登录时间并设置 session
        user_manager.login_user(user)
        token = generate_token(openid)
        return jsonify({'message': 'Login successful', 'nickname': user['nickname'], 'avatar': user['avatar'],'token':token})
    else:       
        nickname = request.json.get('nickname', '默认昵称')
        avatar = request.json.get('avatar', '')

        new_user = user_manager.register_user(openid, nickname, avatar)
        if new_user:
            user_manager.login_user(new_user)
            return jsonify({'message': 'Registration and login successful', 'nickname': new_user['nickname'], 'avatar': new_user['avatar']})
        else:
            return jsonify({'error': 'Registration failed'}), 500