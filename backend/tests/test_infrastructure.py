"""
测试后端核心基础设施
验证数据库、加密服务和日志功能
"""
import uuid
from backend.database import get_database
from backend.services.encryption_service import get_encryption_service
from backend.utils.logger import get_logger
from backend.models import DatabaseConfig

# 初始化
logger = get_logger("test_infrastructure")
db = get_database()
encryption = get_encryption_service()

logger.info("开始测试后端核心基础设施...")

# 测试1: 加密服务
logger.info("测试1: 加密服务")
test_password = "my_secret_password_123"
encrypted = encryption.encrypt(test_password)
decrypted = encryption.decrypt(encrypted)
assert test_password == decrypted, "加密解密测试失败"
logger.info(f"✓ 加密服务测试通过 (原文长度: {len(test_password)}, 密文长度: {len(encrypted)})")

# 测试2: 数据库操作
logger.info("测试2: 数据库操作")
with db.get_session() as session:
    # 创建测试数据库配置
    test_config = DatabaseConfig(
        id=str(uuid.uuid4()),
        name="测试数据库",
        type="sqlite",
        url="sqlite:///test.db",
        username="test_user",
        encrypted_password=encryption.encrypt("test_password")
    )
    
    session.add(test_config)
    session.commit()
    
    # 查询测试
    result = session.query(DatabaseConfig).filter_by(name="测试数据库").first()
    assert result is not None, "数据库查询失败"
    assert result.name == "测试数据库", "数据不匹配"
    
    # 解密密码测试
    decrypted_password = encryption.decrypt(result.encrypted_password)
    assert decrypted_password == "test_password", "密码解密失败"
    
    logger.info(f"✓ 数据库操作测试通过 (ID: {result.id})")
    
    # 清理测试数据
    session.delete(result)
    session.commit()
    logger.info("✓ 测试数据已清理")

# 测试3: 错误日志记录
logger.info("测试3: 错误日志记录")
try:
    raise ValueError("这是一个测试错误")
except Exception as e:
    from backend.utils.logger import log_error_with_context
    log_error_with_context(
        logger,
        "测试错误日志记录",
        e,
        {"test_context": "测试上下文信息"}
    )
    logger.info("✓ 错误日志记录测试通过")

logger.info("=" * 50)
logger.info("所有测试通过！后端核心基础设施工作正常。")
logger.info("=" * 50)

print("\n✅ 所有测试通过！")
print("📊 数据库: 正常")
print("🔐 加密服务: 正常")
print("📝 日志系统: 正常")
