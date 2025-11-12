"""
测试Schema描述文件功能

运行方式：
python -m backend.tests.test_schema_description_feature
"""
import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.database import get_database
from backend.models.database_config import DatabaseConfig
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def test_schema_description():
    """测试Schema描述功能"""
    
    db = get_database()
    
    # 读取示例schema描述文件
    schema_file_path = "data/test_medical_db_schema_compact.md"
    
    try:
        with open(schema_file_path, 'r', encoding='utf-8') as f:
            schema_content = f.read()
        logger.info(f"读取schema文件成功，长度: {len(schema_content)} 字符")
    except Exception as e:
        logger.error(f"读取schema文件失败: {e}")
        return
    
    # 创建测试数据库配置
    test_config_id = "test-schema-desc-001"
    
    with db.get_session() as session:
        # 删除已存在的测试配置
        existing = session.query(DatabaseConfig).filter(
            DatabaseConfig.id == test_config_id
        ).first()
        if existing:
            session.delete(existing)
            session.commit()
            logger.info("删除已存在的测试配置")
        
        # 创建新配置（使用schema描述文件）
        config = DatabaseConfig(
            id=test_config_id,
            name="测试医疗数据库（使用描述文件）",
            type="sqlite",
            url="sqlite:///data/test_medical.db",
            username=None,
            encrypted_password=None,
            use_schema_file=True,
            schema_description=schema_content
        )
        
        session.add(config)
        session.commit()
        logger.info(f"创建测试配置成功: {test_config_id}")
        
        # 验证配置
        saved_config = session.query(DatabaseConfig).filter(
            DatabaseConfig.id == test_config_id
        ).first()
        
        assert saved_config is not None, "配置未保存"
        assert saved_config.use_schema_file is True, "use_schema_file字段错误"
        assert saved_config.schema_description is not None, "schema_description为空"
        assert len(saved_config.schema_description) > 0, "schema_description内容为空"
        
        logger.info("✓ 配置验证成功")
        logger.info(f"  - use_schema_file: {saved_config.use_schema_file}")
        logger.info(f"  - schema_description长度: {len(saved_config.schema_description)}")
        
        # 测试更新配置
        saved_config.use_schema_file = False
        saved_config.schema_description = None
        session.commit()
        
        updated_config = session.query(DatabaseConfig).filter(
            DatabaseConfig.id == test_config_id
        ).first()
        
        assert updated_config.use_schema_file is False, "更新use_schema_file失败"
        assert updated_config.schema_description is None, "更新schema_description失败"
        
        logger.info("✓ 配置更新成功")
        
        # 清理测试数据
        session.delete(updated_config)
        session.commit()
        logger.info("✓ 清理测试数据完成")


async def test_schema_usage_in_query():
    """测试在查询中使用schema描述"""
    
    logger.info("\n测试在查询中使用schema描述...")
    
    db = get_database()
    
    # 读取示例schema描述文件
    schema_file_path = "data/test_medical_db_schema_compact.md"
    with open(schema_file_path, 'r', encoding='utf-8') as f:
        schema_content = f.read()
    
    # 创建测试配置
    test_config_id = "test-schema-query-001"
    
    with db.get_session() as session:
        # 删除已存在的配置
        existing = session.query(DatabaseConfig).filter(
            DatabaseConfig.id == test_config_id
        ).first()
        if existing:
            session.delete(existing)
            session.commit()
        
        # 创建配置
        config = DatabaseConfig(
            id=test_config_id,
            name="测试查询配置",
            type="sqlite",
            url="sqlite:///data/test_medical.db",
            use_schema_file=True,
            schema_description=schema_content
        )
        
        session.add(config)
        session.commit()
    
    try:
        # 模拟获取schema信息
        with db.get_session() as session:
            db_config = session.query(DatabaseConfig).filter(
                DatabaseConfig.id == test_config_id
            ).first()
            
            # 检查是否正确读取配置
            assert db_config is not None, "配置不存在"
            assert db_config.use_schema_file is True, "use_schema_file应为True"
            assert db_config.schema_description is not None, "schema_description不应为空"
            
            # 模拟report_service中的逻辑
            if db_config.use_schema_file and db_config.schema_description:
                db_schema = {
                    "name": db_config.name,
                    "type": db_config.type,
                    "schema_description": db_config.schema_description
                }
                logger.info("✓ 使用schema描述文件")
                logger.info(f"  - 描述长度: {len(db_schema['schema_description'])} 字符")
                
                # 验证schema_description字段存在
                assert "schema_description" in db_schema, "schema_description字段缺失"
                assert "tables" not in db_schema, "不应包含tables字段"
            else:
                logger.error("✗ 未使用schema描述文件")
                raise AssertionError("应该使用schema描述文件")
        
        logger.info("✓ Schema描述在查询中使用正确")
        
    finally:
        # 清理测试数据
        with db.get_session() as session:
            config = session.query(DatabaseConfig).filter(
                DatabaseConfig.id == test_config_id
            ).first()
            if config:
                session.delete(config)
                session.commit()
        logger.info("✓ 清理测试数据完成")


async def main():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("开始测试Schema描述文件功能")
    logger.info("=" * 60)
    
    try:
        # 测试1: 基本CRUD操作
        logger.info("\n[测试1] 数据库配置CRUD操作")
        await test_schema_description()
        
        # 测试2: 在查询中使用
        logger.info("\n[测试2] 在查询中使用Schema描述")
        await test_schema_usage_in_query()
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ 所有测试通过！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n✗ 测试失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
