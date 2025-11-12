"""
测试常用报表的summary保存和使用
验证快速执行时是否正确使用保存的summary
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from backend.services.report_service import ReportService
from backend.models.saved_report import SavedReport


@pytest.mark.asyncio
async def test_run_saved_report_uses_saved_summary():
    """测试快速执行常用报表时使用保存的summary"""
    
    # 模拟保存的报表数据
    saved_report = SavedReport(
        id="test-report-id",
        name="就业最好的专业",
        description="这是报表描述",
        query_plan=json.dumps({
            "no_data_source_match": False,
            "sql_queries": [{
                "db_config_id": "db-001",
                "sql": "SELECT major, employment_rate FROM majors ORDER BY employment_rate DESC LIMIT 1",
                "source_alias": "result"
            }],
            "mcp_calls": [],
            "needs_combination": False
        }),
        chart_config=json.dumps({
            "type": "text",
            "title": "就业最好的专业"
        }),
        summary="就业最好的专业是 {major}，就业率为 {employment_rate}%",  # 带占位符的summary
        original_query="就业最好的专业是哪个",
        data_source_ids=json.dumps(["db-001"])
    )
    
    # 模拟查询结果
    mock_data = [
        {"major": "预防医学", "employment_rate": 95.5}
    ]
    
    # 创建mock对象
    mock_db = Mock()
    mock_db_session = Mock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = saved_report
    mock_db.get_session.return_value.__enter__.return_value = mock_db_session
    mock_db.get_session.return_value.__exit__.return_value = None
    
    mock_data_source = Mock()
    mock_data_source.execute_query_plan = AsyncMock(return_value=Mock(
        data=mock_data,
        columns=["major", "employment_rate"]
    ))
    mock_data_source.get_combined_metadata = Mock(return_value=Mock(
        columns=["major", "employment_rate"],
        column_types={"major": "TEXT", "employment_rate": "FLOAT"},
        row_count=1
    ))
    
    mock_llm = Mock()
    mock_filter = Mock()
    mock_session_manager = Mock()
    
    # 创建ReportService实例
    report_service = ReportService(
        db=mock_db,
        llm=mock_llm,
        data_source=mock_data_source,
        filter_service=mock_filter,
        session_manager=mock_session_manager
    )
    
    # 模拟_apply_filters_to_combined_data方法
    async def mock_apply_filters(combined_data, data_source_ids):
        return combined_data.data
    
    report_service._apply_filters_to_combined_data = mock_apply_filters
    
    # 执行快速模式（with_analysis=False）
    result = await report_service.run_saved_report(
        report_id="test-report-id",
        with_analysis=False,
        session_id=None,
        model=None
    )
    
    # 验证结果
    assert result.summary == "就业最好的专业是 预防医学，就业率为 95.5%"
    assert result.summary != "这是报表描述"  # 不应该使用description
    assert "{major}" not in result.summary  # 占位符应该被替换
    assert "{employment_rate}" not in result.summary
    
    print("✓ 测试通过：快速执行时正确使用保存的summary并替换占位符")


@pytest.mark.asyncio
async def test_run_saved_report_fallback_to_description():
    """测试当没有保存summary时，使用description作为后备"""
    
    # 模拟没有summary的报表
    saved_report = SavedReport(
        id="test-report-id",
        name="测试报表",
        description="这是报表描述",
        query_plan=json.dumps({
            "no_data_source_match": False,
            "sql_queries": [{
                "db_config_id": "db-001",
                "sql": "SELECT * FROM test",
                "source_alias": "result"
            }],
            "mcp_calls": [],
            "needs_combination": False
        }),
        chart_config=json.dumps({"type": "text"}),
        summary=None,  # 没有保存summary
        original_query="测试查询",
        data_source_ids=json.dumps(["db-001"])
    )
    
    # 创建mock对象
    mock_db = Mock()
    mock_db_session = Mock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = saved_report
    mock_db.get_session.return_value.__enter__.return_value = mock_db_session
    mock_db.get_session.return_value.__exit__.return_value = None
    
    mock_data_source = Mock()
    mock_data_source.execute_query_plan = AsyncMock(return_value=Mock(
        data=[{"col": "value"}],
        columns=["col"]
    ))
    mock_data_source.get_combined_metadata = Mock(return_value=Mock(
        columns=["col"],
        column_types={"col": "TEXT"},
        row_count=1
    ))
    
    report_service = ReportService(
        db=mock_db,
        llm=Mock(),
        data_source=mock_data_source,
        filter_service=Mock(),
        session_manager=Mock()
    )
    
    async def mock_apply_filters(combined_data, data_source_ids):
        return combined_data.data
    
    report_service._apply_filters_to_combined_data = mock_apply_filters
    
    # 执行快速模式
    result = await report_service.run_saved_report(
        report_id="test-report-id",
        with_analysis=False,
        session_id=None,
        model=None
    )
    
    # 验证使用了description作为后备
    assert result.summary == "这是报表描述"
    
    print("✓ 测试通过：没有summary时正确使用description作为后备")


if __name__ == "__main__":
    import asyncio
    
    print("运行测试：常用报表summary功能")
    print("=" * 60)
    
    asyncio.run(test_run_saved_report_uses_saved_summary())
    asyncio.run(test_run_saved_report_fallback_to_description())
    
    print("=" * 60)
    print("所有测试通过！✓")
