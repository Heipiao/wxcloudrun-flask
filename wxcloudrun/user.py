import logging
import pymysql
from flask import Flask, session
from datetime import datetime, timezone

# 配置日志记录，包含行号
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)'
)
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
            CREATE TABLE IF NOT EXISTS wechat_miniprogram_user_info (
                openid VARCHAR(100) PRIMARY KEY,
                nick_name VARCHAR(100) NOT NULL,
                user_register_time DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            connection.commit()
            logger.info("表 'wechat_miniprogram_user_info' 已存在或已成功创建")
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
                sql = "SELECT * FROM wechat_miniprogram_user_info WHERE openid = %s"
                cursor.execute(sql, (openid,))
                user = cursor.fetchone()
                if user:
                    logger.info(f"找到用户: {user['nick_name']}")
                else:
                    logger.info(f"未找到用户: {openid}")
                return user
        except Exception as e:
            logger.error(f"查找用户失败: {str(e)}")
            return None
        finally:
            connection.close()

    def register_user(self, openid, nick_name):
        """注册新用户"""
        connection = get_db_connection()
        if connection is None:
            return None
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO wechat_miniprogram_user_info (openid, nick_name, user_register_time) VALUES (%s, %s, %s)"
                now_utc = datetime.now(timezone.utc)
                cursor.execute(sql, (openid, nick_name, now_utc))
                connection.commit()
                logger.info(f"注册用户成功: {nick_name}")
                return {"openid": openid, "nick_name": nick_name}
        except Exception as e:
            logger.error(f"注册用户失败: {str(e)}")
            connection.rollback()
            return None
        finally:
            connection.close()

    def login_user(self, user):
        """登录用户，保存 session"""
        try:
            session['openid'] = user['openid']
            session['nick_name'] = user['nick_name']
            logger.info(f"登录成功: {user['nick_name']}")
        except Exception as e:
            logger.error(f"登录用户失败: {str(e)}")

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
    user = user_manager.register_user("test_openid", "test_nick_name")
    if user:
        logger.info(f"注册用户: {user['nick_name']}")

    # 查找并登录用户
    found_user = user_manager.find_user_by_openid("test_openid")
    if found_user:
        user_manager.login_user(found_user)
        logger.info(f"登录成功: {found_user['nick_name']}")

    # 用户退出登录
    user_manager.logout_user()
    logger.info("已退出登录")
