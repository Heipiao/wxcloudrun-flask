import logging
import pymysql
from datetime import datetime

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 阿里云 RDS MySQL 连接信息
DB_USERNAME = 'aigc_teacher_dev'
DB_PASSWORD = 'AIGC@2024'
DB_HOST = 'rm-bp11gu573pod4b6hb8o.mysql.rds.aliyuncs.com'
DB_PORT = 3306  # MySQL 默认端口
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

# 创建表函数
def create_device_role_table_if_not_exists():
    """如果表不存在则创建"""
    connection = get_db_connection()
    if connection is None:
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS wechat_miniprogram_user_binding_role (
                openid VARCHAR(100) NOT NULL,
                mac_address VARCHAR(100) NOT NULL,
                role_id INT NOT NULL,
                device_quota INT NOT NULL,
                PRIMARY KEY (openid, mac_address)
            );
            """)
            connection.commit()
            logger.info("表 'wechat_miniprogram_user_binding_role' 已存在或已成功创建")
    except Exception as e:
        logger.error(f"创建表失败: {str(e)}")
    finally:
        connection.close()

class DeviceRoleManager:
    def __init__(self):
        """初始化"""
        logger.info("DeviceRoleManager 实例已创建")
    
    def find_mac_address_by_openid(self, openid):
        """根据 openid 查找用户的 mac 地址"""
        connection = get_db_connection()
        if connection is None:
            return None
        try:
            with connection.cursor() as cursor:
                sql = "SELECT mac_address FROM wechat_miniprogram_user_binding_role WHERE openid = %s"
                cursor.execute(sql, (openid,))
                mac_addresses = cursor.fetchall()
                if mac_addresses:
                    logger.info(f"找到的 mac 地址: {mac_addresses}")
                    return [mac["mac_address"] for mac in mac_addresses]  # 返回一个列表形式的所有 mac 地址
                else:
                    logger.info(f"未找到与 openid 关联的 mac 地址: {openid}")
                    return []
        except Exception as e:
            logger.error(f"查找 mac 地址失败: {str(e)}")
            return []
        finally:
            connection.close()

    def find_user_role(self, openid):
        """根据 openid 查找用户绑定的角色信息"""
        connection = get_db_connection()
        if connection is None:
            return None
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM wechat_miniprogram_user_binding_role WHERE openid = %s"
                cursor.execute(sql, (openid,))
                user_role = cursor.fetchall()
                if user_role:
                    logger.info(f"找到用户角色: {user_role}")
                else:
                    logger.info(f"未找到用户角色: {openid}")
                return user_role
        except Exception as e:
            logger.error(f"查找用户角色失败: {str(e)}")
            return None
        finally:
            connection.close()

    def bind_role(self, openid, role_id):
        """根据 openid 绑定角色，更新 role_id，其他字段保持不变"""
        connection = get_db_connection()
        if connection is None:
            logger.error("数据库连接失败")
            return None
        try:
            with connection.cursor() as cursor:
                # 获取当前用户绑定的设备信息
                sql_get_current_values = """
                SELECT mac_address, device_quota
                FROM wechat_miniprogram_user_binding_role
                WHERE openid = %s
                """
                logger.info(f"执行 SQL: {sql_get_current_values} 参数: {openid}")
                cursor.execute(sql_get_current_values, (openid,))
                current_values = cursor.fetchone()
                logger.info(f"查询结果: {current_values}")

                if current_values:
                    mac_address, device_quota = current_values
                    if not mac_address:
                        logger.warning(f"mac_address 为空: openid={openid}")
                        return {"message": "fail"}
                    
                    # 更新角色 id
                    sql_update_role = """
                    UPDATE wechat_miniprogram_user_binding_role
                    SET role_id = %s
                    WHERE openid = %s AND mac_address = %s
                    """
                    cursor.execute(sql_update_role, (role_id, openid, mac_address))
                    connection.commit()
                    logger.info(f"角色绑定更新成功: openid={openid}, role_id={role_id}, mac_address={mac_address}")
                    return {
                        "message": "suc",
                        "data": {
                            "openid": openid,
                            "mac_address": mac_address,
                            "role_id": role_id,
                            "device_quota": device_quota
                        }
                    }
                else:
                    logger.warning(f"未找到用户绑定信息: openid={openid}")
                    return {"message": "fail"}
        except Exception as e:
            logger.error(f"绑定角色失败: {str(e)}")
            connection.rollback()
            return {"message": "fail"}
        finally:
            connection.close()


    def update_device_quota(self, openid, mac_address, new_quota):
        """更新用户设备配额"""
        connection = get_db_connection()
        if connection is None:
            return None
        try:
            with connection.cursor() as cursor:
                sql = "UPDATE wechat_miniprogram_user_binding_role SET device_quota = %s WHERE openid = %s AND mac_address = %s"
                cursor.execute(sql, (new_quota, openid, mac_address))
                connection.commit()
                logger.info(f"更新设备配额成功: openid={openid}, mac_address={mac_address}, new_quota={new_quota}")
                return {"openid": openid, "mac_address": mac_address, "device_quota": new_quota}
        except Exception as e:
            logger.error(f"更新设备配额失败: {str(e)}")
            connection.rollback()
            return None
        finally:
            connection.close()

    def decrement_device_quota(self, openid, mac_address):
        """减少用户的设备配额"""
        connection = get_db_connection()
        if connection is None:
            return None
        try:
            with connection.cursor() as cursor:
                sql_check = "SELECT device_quota FROM wechat_miniprogram_user_binding_role WHERE openid = %s AND mac_address = %s"
                cursor.execute(sql_check, (openid, mac_address))
                result = cursor.fetchone()

                if result and result['device_quota'] > 0:
                    sql_decrement = "UPDATE wechat_miniprogram_user_binding_role SET device_quota = device_quota - 1 WHERE openid = %s AND mac_address = %s"
                    cursor.execute(sql_decrement, (openid, mac_address))
                    connection.commit()
                    logger.info(f"设备配额已减少: openid={openid}, mac_address={mac_address}")
                    return True
                else:
                    logger.info(f"设备配额不足: openid={openid}, mac_address={mac_address}")
                    return False
        except Exception as e:
            logger.error(f"减少设备配额失败: {str(e)}")
            connection.rollback()
            return None
        finally:
            connection.close()

    def add_user_role(self, openid, mac_address, role_id, device_quota):
        """Add a new user binding role."""
        self.cursor.execute("""
            INSERT INTO wechat_miniprogram_user_binding_role (openid, mac_address, role_id, device_quota)
            VALUES (?, ?, ?, ?)
        """, (openid, mac_address, role_id, device_quota))
        self.conn.commit()

    def get_user_role(self, mac_address):
        """根据 mac_address 获取用户角色信息"""
        connection = get_db_connection()
        if connection is None:
            return None
        try:
            with connection.cursor() as cursor:
                # 查询绑定的角色信息
                sql_get_user_role = """
                SELECT * 
                FROM wechat_miniprogram_user_binding_role 
                WHERE mac_address = %s
                """
                cursor.execute(sql_get_user_role, (mac_address,))
                user_role = cursor.fetchone()

                if user_role:
                    logger.info(f"用户角色信息查询成功: mac_address={mac_address}")
                    return {
                        "message": "suc",  # 查询成功
                        "data": user_role
                    }
                else:
                    logger.warning(f"未找到用户角色信息: mac_address={mac_address}")
                    return {"message": "fail"}  # 未找到角色信息
        except Exception as e:
            logger.error(f"查询用户角色信息失败: {str(e)}")
            return {"message": "fail"}  # 出现异常，查询失败
        finally:
            connection.close()

    def delete_user_role(self, openid):
        """Delete a user role by openid."""
        self.cursor.execute("""
            DELETE FROM wechat_miniprogram_user_binding_role WHERE openid = ?
        """, (openid,))
        self.conn.commit()

    def check_quota(self, openid):
        """Check if the user has remaining device quota."""
        self.cursor.execute("""
            SELECT device_quota FROM wechat_miniprogram_user_binding_role WHERE openid = ?
        """, (openid,))
        result = self.cursor.fetchone()
        if result:
            return result[0] > 0
        return False

    def decrement_quota(self, openid):
        """Decrement the device quota by 1 if there is remaining quota."""
        if self.check_quota(openid):
            self.cursor.execute("""
                UPDATE wechat_miniprogram_user_binding_role
                SET device_quota = device_quota - 1
                WHERE openid = ?
            """, (openid,))
            self.conn.commit()
            return True
        return False
    
    def bind_user_device(self, openid, device_id):
        """绑定 openid 和 设备ID，默认 role_id 为 1，device_quota 为 1000"""
        connection = get_db_connection()
        if connection is None:
            return None
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO wechat_miniprogram_user_binding_role (openid, mac_address, role_id, device_quota)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE device_quota = device_quota;
                """
                cursor.execute(sql, (openid, device_id, 1, 1000))
                connection.commit()
                logger.info(f"绑定成功: openid={openid}, device_id={device_id}, role_id=1, device_quota=1000")
                return {"openid": openid, "device_id": device_id, "role_id": 1, "device_quota": 1000}
        except Exception as e:
            logger.error(f"绑定失败: {str(e)}")
            connection.rollback()
            return None
        finally:
            connection.close()   


if __name__ == "__main__":
    # 创建表如果不存在
    #create_device_role_table_if_not_exists()
    mgr = DeviceRoleManager()
    connection = get_db_connection()
    if connection is None:
        pass

    with connection.cursor() as cursor:
            cursor.execute("""
            SELECT * FROM wechat_miniprogram_user_binding_role 
        """)
            out = cursor.fetchone()
    print(out)

    # # 初始化 DeviceRoleManager 实例
    # device_role_manager = DeviceRoleManager()
    # output = device_role_manager.get_user_role("A01625469232")
    # print(output)

    # # 测试绑定角色功能
    # device_role_manager.bind_role("test_openid", "test_mac_address", 1, 5)

    # # 查找用户角色
    # user_role = device_role_manager.find_user_role("test_openid")
    # if user_role:
    #     logger.info(f"找到用户角色: {user_role}")

    # # 更新设备配额
    # device_role_manager.update_device_quota("test_openid", "test_mac_address", 10)

    # # 减少设备配额
    # device_role_manager.decrement_device_quota("test_openid", "test_mac_address")

    # # 删除用户角色
    # device_role_manager.delete_user_role("test_openid", "test_mac_address")
