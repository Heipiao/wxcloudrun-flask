from datetime import datetime
from flask import render_template, request, Flask, request, jsonify, session
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response
from wxcloudrun.DeviceRoleManager import DeviceRoleManager
from wxcloudrun.role import RoleManager
import requests
import jwt
import os
import logging
from datetime import datetime, timezone, timedelta
from functools import wraps
# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from wxcloudrun.user import UserManager 
user_manager = UserManager()
device_manager = DeviceRoleManager()
role_manager = RoleManager()

JWT_SECRET = 'your-jwt-secret'  # 替换为实际的 JWT 密钥
JWT_EXPIRATION_HOURS = 24 * 7
# 微信小程序配置
APP_ID = os.getenv('APP_ID',"wx8446265bd2d968e9")
APP_SECRET =  os.getenv('APP_SECRET',"dfddc06c807106ae6d67b639dcd926a4")


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
            logging.warning('Token is missing in the request headers.')
            return jsonify({'message': 'Token is missing!'}), 403

        try:
            logging.info('Original token: %s', token)

            # 去除 "Bearer " 前缀
            token = token.replace("Bearer ", "").replace("\n", "")
            logging.info('Token prefix "Bearer" removed. %s',token)


            # 解码token
            decoded_token = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            logging.info('after decoded_token: %s', decoded_token)
            logging.info('Token decoded successfully.')

            # 获取openid
            openid = decoded_token.get('openid')

            if not openid:
                logging.error('Token does not contain openid.')
                return jsonify({'message': 'Token is invalid!'}), 403
            logging.info('Token verified successfully for openid: %s', openid)
            # 将 openid 传递给视图函数
            return f(openid=openid, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            logging.warning('Token has expired.')
            return jsonify({'message': 'Token has expired!'}), 403
        except jwt.InvalidTokenError:
            logging.error('Invalid token encountered.')
            return jsonify({'message': 'Invalid token!'}), 403
        except Exception as e:
            logging.error('An unexpected error occurred during token verification: %s', str(e))
            return jsonify({'message': 'An unexpected error occurred!'}), 500
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
        logging.error('缺少device_id参数')
        return jsonify({"message": "device_id 是必需的"}), 400

    logging.info(f'尝试绑定设备，用户openid：{openid}，设备ID：{device_id}')
    result = device_manager.bind_user_device(openid, device_id)
    if result:
        logging.info(f'设备绑定成功，用户openid：{openid}，设备ID：{device_id}')
        return jsonify({"message": "绑定成功", "data": result})
    else:
        logging.error(f'设备绑定失败，用户openid：{openid}，设备ID：{device_id}')
        return jsonify({"message": "绑定失败"}), 500
    
@app.route('/api/get_mac_addresses', methods=['GET'])
@token_required  # 验证 token
def get_mac_addresses(openid):
    logging.info(f'尝试查找用户openid：{openid} 绑定的所有 mac 地址')

    # 使用 device_manager 查找用户绑定的 mac 地址
    mac_addresses = device_manager.find_mac_address_by_openid(openid)

    if mac_addresses:
        logging.info(f'找到的 mac 地址: {mac_addresses}')
        return jsonify({"message": "成功获取 mac 地址", "data": mac_addresses})
    else:
        logging.error(f'未找到与 openid：{openid} 关联的 mac 地址')
        return jsonify({"message": "未找到 mac 地址"}), 404

@app.route('/api/bind_role', methods=['POST'])
@token_required  # 验证 token
def bind_role_endpoint(openid):
    data = request.json
    role_id = data.get('role_id')

    if not role_id:
        logging.error('缺少 role_id 参数')
        return jsonify({"message": "fail"}), 400  # 请求参数错误，返回 fail

    logging.info(f'尝试绑定角色，用户 openid: {openid}, 角色 ID: {role_id}')
    result = device_manager.bind_role(openid, role_id)
    return jsonify(result)  # 直接返回 bind_role 方法的结果

@app.route('/api/get_roles_top25', methods=['POST'])
@token_required  # 验证 token
def get_roles_top25_endpoint(openid):
    # 获取所有角色
    roles = role_manager.get_roles()  # 假设 get_roles 已经实现返回所有角色
    
    if not roles:
        logging.error(f'未找到任何角色信息')
        return jsonify({"message": "No roles found"}), 404

    # 取前 25 个角色
    top_roles = roles[:25]

    # 返回角色信息
    logging.info(f'成功获取前 25 个角色信息')
    return jsonify({"message": "success", "roles": top_roles}), 200

@app.route('/api/get_role_by_mac', methods=['POST'])
def get_role_by_mac_endpoint():
    # 获取请求中的 mac_address
    data = request.get_json()
    mac_address = data.get('mac_address')

    if not mac_address:
        logging.error('缺少 mac_address 参数')
        return jsonify({"message": "Missing mac_address parameter"}), 400

    # 通过 mac_address 获取角色 ID
    role_info = device_manager.get_user_role(mac_address)  # 使用 device_manager.get_user_role 获取角色信息

    if not role_info:
        logging.error(f'未找到 mac_address={mac_address} 的角色信息')
        return jsonify({"message": "Role not found"}), 404

    role_id = role_info.get('data').get('role_id')

    if not role_id:
        logging.error(f'mac_address={mac_address} 未绑定角色')
        return jsonify({"message": "Role ID not found"}), 404

    # 获取角色详细信息
    role_details = role_manager.get_roles_by_id(role_id)  # 使用 role_manager.get_roles_by_id 获取角色详细信息

    if not role_details:
        logging.error(f'未找到 role_id={role_id} 的详细信息')
        return jsonify({"message": "Role details not found"}), 404

    # 返回角色详细信息
    logging.info(f'成功获取 mac_address={mac_address} 的角色详细信息')
    return jsonify({"message": "success", "role_details": role_details}), 200

