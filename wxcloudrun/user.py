import logging
import pymysql
from flask import Flask, session
from datetime import datetime, timezone

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 阿里云 RDS MySQL 连接信息
DB_USERNAME = 'aigc_teacher_dev'
DB_PASSWORD = 'AIGC@2024'
DB_HOST = 'rm-bp11gu573pod4b6hb8o.mysql.rds.aliyuncs.com'
DB_PORT = 3306  # MySQL 默认端口
DB_NAME = 'aigc_teacher'

# 配置 Flask 密钥
app.config['SECRET_KEY'] = 'your-secret-key'  # session 所需的密钥

# 定义连接函数
def get_db_connection():
    """获取数据库连接"""
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            db=DB_NAME,
            port=DB_PORT,
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return None

# 创建表函数
def create_table_if_not_exists():
    """如果表不存在则创建"""
    connection = get_db_connection()
    if connection is None:
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS aigc_teacher_user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                openid VARCHAR(100) UNIQUE NOT NULL,
                nickname VARCHAR(100) NOT NULL,
                avatar VARCHAR(200),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            );
            """)
            connection.commit()
            logger.info("表 'aigc_teacher_user' 已存在或已成功创建")
    except Exception as e:
        logger.error(f"创建表失败: {str(e)}")
    finally:
        connection.close()

class UserManager:
    def __init__(self):
        """初始化"""
        logger.info("UserManager 实例已创建")

    def find_user_by_openid(self, openid):
        """根据 openid 查找用户"""
        connection = get_db_connection()
        if connection is None:
            return None
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM aigc_teacher_user WHERE openid = %s"
                cursor.execute(sql, (openid,))
                user = cursor.fetchone()
                if user:
                    logger.info(f"找到用户: {user['nickname']}")
                else:
                    logger.info(f"未找到用户: {openid}")
                return user
        except Exception as e:
            logger.error(f"查找用户失败: {str(e)}")
            return None
        finally:
            connection.close()

    def register_user(self, openid, nickname, avatar):
        """注册新用户"""
        connection = get_db_connection()
        if connection is None:
            return None
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO aigc_teacher_user (openid, nickname, avatar, created_at) VALUES (%s, %s, %s, %s)"
                now_utc = datetime.now(timezone.utc)
                cursor.execute(sql, (openid, nickname, avatar, now_utc))
                connection.commit()
                logger.info(f"注册用户成功: {nickname}")
                return {"openid": openid, "nickname": nickname, "avatar": avatar}
        except Exception as e:
            logger.error(f"注册用户失败: {str(e)}")
            connection.rollback()
            return None
        finally:
            connection.close()

    def login_user(self, user):
        """登录用户，保存 session 并更新 last_login"""
        connection = get_db_connection()
        if connection is None:
            return
        try:
            session['user_id'] = user['id']
            session['nickname'] = user['nickname']

            with connection.cursor() as cursor:
                sql = "UPDATE aigc_teacher_user SET last_login = %s WHERE id = %s"
                now_utc = datetime.now(timezone.utc)
                cursor.execute(sql, (now_utc, user['id']))
                connection.commit()
                logger.info(f"登录成功: {user['nickname']}")
        except Exception as e:
            logger.error(f"登录用户失败: {str(e)}")
            connection.rollback()
        finally:
            connection.close()

    def logout_user(self):
        """退出登录，清除 session"""
        try:
            session.clear()
            logger.info("用户已退出登录")
        except Exception as e:
            logger.error(f"退出登录失败: {str(e)}")


if __name__ == "__main__":
    # 创建表如果不存在
    create_table_if_not_exists()

    # 初始化 UserManager 实例
    user_manager = UserManager()

    # 测试数据库连接和用户注册、登录功能
    user = user_manager.register_user("test_openid", "test_nickname", "test_avatar")
    if user:
        logger.info(f"注册用户: {user['nickname']}")

    # 查找并登录用户
    found_user = user_manager.find_user_by_openid("test_openid")
    if found_user:
        user_manager.login_user(found_user)
        logger.info(f"登录成功: {found_user['nickname']}")

    # 用户退出登录
    user_manager.logout_user()
    logger.info("已退出登录")
