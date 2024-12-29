import logging
import pymysql
from datetime import datetime, timezone

# 配置日志记录，包含行号
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)'
)
logger = logging.getLogger(__name__)

# 数据库连接配置
DB_USERNAME = 'aigc_teacher_dev'
DB_PASSWORD = 'AIGC@2024'
DB_HOST = 'rm-bp11gu573pod4b6hb8o.mysql.rds.aliyuncs.com'
DB_PORT = 3306
DB_NAME = 'aigc_teacher'

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

class RoleManager:
    def __init__(self):
        """初始化"""
        logger.info("RoleManager 实例已创建")

    def create_table_if_not_exists(self):
        """如果表不存在则创建"""
        connection = get_db_connection()
        if connection is None:
            return
        try:
            with connection.cursor() as cursor:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS wechat_miniprogram_role_info_details (
                    role_id INT AUTO_INCREMENT PRIMARY KEY,
                    role_title VARCHAR(100),
                    role_prompt TEXT,
                    role_name VARCHAR(100),
                    role_age INT,
                    role_character TEXT,
                    role_introduction TEXT,
                    role_picture VARCHAR(255),
                    role_voice VARCHAR(255),
                    role_voice_api VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                ''')
                connection.commit()
                logger.info("表 'wechat_miniprogram_role_info_details' 已存在或已成功创建")
        except Exception as e:
            logger.error(f"创建表失败: {str(e)}")
        finally:
            connection.close()

    def add_role(self, role_data):
        """添加新角色"""
        connection = get_db_connection()
        if connection is None:
            return None
        try:
            with connection.cursor() as cursor:
                sql = '''
                INSERT INTO wechat_miniprogram_role_info_details (role_title, role_prompt, role_name, role_age, role_character, role_introduction, role_picture, role_voice, role_voice_api)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
                cursor.execute(sql, (
                    role_data['role_title'], role_data['role_prompt'], role_data['role_name'],
                    role_data['role_age'], role_data['role_character'], role_data['role_introduction'],
                    role_data['role_picture'], role_data['role_voice'], role_data['role_voice_api']
                ))
                connection.commit()
                logger.info(f"角色添加成功: {role_data['role_name']}")
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"添加角色失败: {str(e)}")
            connection.rollback()
            return None
        finally:
            connection.close()

    def get_roles(self):
        """获取所有角色"""
        connection = get_db_connection()
        if connection is None:
            return []
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM wechat_miniprogram_role_info_details")
                roles = cursor.fetchall()
                logger.info(f"共找到 {len(roles)} 个角色")
                return roles
        except Exception as e:
            logger.error(f"获取角色失败: {str(e)}")
            return []
        finally:
            connection.close()

    def delete_role_by_id(self, role_id):
        """根据角色 ID 删除角色"""
        connection = get_db_connection()
        if connection is None:
            return False
        try:
            with connection.cursor() as cursor:
                sql = "DELETE FROM wechat_miniprogram_role_info_details WHERE role_id = %s"
                cursor.execute(sql, (role_id,))
                connection.commit()
                logger.info(f"角色已删除: ID {role_id}")
                return True
        except Exception as e:
            logger.error(f"删除角色失败: {str(e)}")
            connection.rollback()
            return False
        finally:
            connection.close()

if __name__ == "__main__":
    # 初始化 RoleManager
    role_manager = RoleManager()

    # 创建表
    role_manager.create_table_if_not_exists()

    # 查询现有角色
    existing_roles = role_manager.get_roles()
    if existing_roles:
        for role in existing_roles:
            logger.info(f"现有角色: {role['role_name']} - {role['role_title']}")
    else:
        logger.info("数据库中没有角色记录")

    # 添加角色
    new_role = {
        'role_title': 'Hero',
        'role_prompt': 'Protect the village.',
        'role_name': 'John',
        'role_age': 30,
        'role_character': 'Brave and kind.',
        'role_introduction': 'A hero who protects his people.',
        'role_picture': 'hero.jpg',
        'role_voice': 'hero_voice.mp3',
        'role_voice_api': 'http://example.com/api/hero-voice'
    }
    # role_id = role_manager.add_role(new_role)
    # if role_id:
    #     logger.info(f"新角色已添加，ID: {role_id}")

    # # 再次获取所有角色
    # roles = role_manager.get_roles()
    # for role in roles:
    #     logger.info(f"角色: {role['role_name']} - {role['role_title']}")

    # # 删除角色
    # if role_id:
    #     if role_manager.delete_role_by_id(role_id):
    #         logger.info(f"角色 ID {role_id} 已删除")
