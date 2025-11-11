"""
报表生成服务测试
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from backend.services.report_service import ReportService, ReportResult
from backend.services.llm_service import LLMService
from backend.services.data_source_manager import DataSourceManager, CombinedData
from backend.services.filter_service import FilterService
from backend.services.session_manager import SessionManager
from backend.services.dto import (
    QueryPlan,
    SQLQuery,
    MCPCall,
    ChartSuggestion,
    DataMetadata,
    ConversationMessage
)
from backend.database import Database


@pytest.fixture
def mock_llm_service():
    """创建模拟的LLM服务"""
    llm = Mock(spec=LLMService)
    llm.default_model = "gemini/gemini-2.0-flash-exp"
    
    # 模拟generate_query_plan
    llm.generate_query_plan = AsyncMock(return_value=QueryPlan(
        sql_queries=[
            SQLQuery(
                db_config_id="test_db",
                sql="SELECT * FROM students",
                source_alias="students"
            )
        ],
        mcp_calls=[],
        needs_combination=False
    ))
    
    # 模拟analyze_data_and_suggest_chart
    llm.analyze_data_and_suggest_chart = AsyncMock(return_value=ChartSuggestion(
        chart_type="bar",
        chart_config={
            "title": {"text": "测试图表"},
            "xAxis": {"type": "category"},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": "{{DATA_PLACEHOLDER}}"}]
        },
        summary="这是一个测试报表总结"
    ))
    
    # 模拟summarize_conversation
    llm.summarize_conversation = AsyncMock(return_value="会话摘要")
    
    return llm


@pytest.fixture
def mock_data_source_manager():
    """创建模拟的数据源管理器"""
    dsm = Mock(spec=DataSourceManager)
    dsm.temp_db_path = "./data/temp_data.db"
    
    # 模拟execute_query_plan
    test_data = [
        {"id": 1, "name": "张三", "score": 85},
        {"id": 2, "name": "李四", "score": 90}
    ]
    dsm.execute_query_plan = AsyncMock(return_value=CombinedData(
        data=test_data,
        columns=["id", "name", "score"]
    ))
    
    # 模拟get_combined_metadata
    dsm.get_combined_metadata = Mock(return_value=DataMetadata(
        columns=["id", "name", "score"],
        column_types={"id": "INTEGER", "name": "TEXT", "score": "INTEGER"},
        row_count=2
    ))
    
    # 模拟cleanup_temp_tables
    dsm.cleanup_temp_tables = Mock()
    
    # 模拟db和mcp连接器
    dsm.db = Mock()
    dsm.db.get_schema_info = AsyncMock(return_value=Mock(tables=[]))
    dsm.mcp = Mock()
    dsm.mcp.get_available_tools = AsyncMock(return_value=[])
    
    return dsm


@pytest.fixture
def mock_filter_service():
    """创建模拟的过滤服务"""
    fs = Mock(spec=FilterService)
    
    # 模拟apply_filters（直接返回原始数据）
    fs.apply_filters = AsyncMock(side_effect=lambda data, db_config_id: data)
    
    return fs


@pytest.fixture
def mock_session_manager():
    """创建模拟的会话管理器"""
    sm = Mock(spec=SessionManager)
    
    # 模拟get_context
    sm.get_context = AsyncMock(return_value=[
        ConversationMessage(role="user", content="之前的查询")
    ])
    
    # 模拟add_interaction
    sm.add_interaction = AsyncMock(return_value="interaction_123")
    
    # 模拟check_and_compress
    sm.check_and_compress = AsyncMock(return_value=False)
    
    return sm


@pytest.fixture
def mock_database():
    """创建模拟的数据库"""
    db = Mock(spec=Database)
    
    # 创建模拟的session
    mock_session = MagicMock()
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=False)
    
    # 模拟query方法
    mock_session.query = Mock(return_value=Mock(
        filter=Mock(return_value=Mock(
            first=Mock(return_value=None)
        ))
    ))
    
    db.get_session = Mock(return_value=mock_session)
    
    return db


@pytest.fixture
def report_service(
    mock_llm_service,
    mock_data_source_manager,
    mock_filter_service,
    mock_session_manager,
    mock_database
):
    """创建报表服务实例"""
    return ReportService(
        llm_service=mock_llm_service,
        data_source_manager=mock_data_source_manager,
        filter_service=mock_filter_service,
        session_manager=mock_session_manager,
        database=mock_database
    )


@pytest.mark.asyncio
async def test_report_service_initialization(report_service):
    """测试报表服务初始化"""
    assert report_service is not None
    assert report_service.llm is not None
    assert report_service.data_source is not None
    assert report_service.filter is not None
    assert report_service.session is not None
    assert report_service.db is not None


@pytest.mark.asyncio
async def test_generate_report_basic(report_service):
    """测试基本的报表生成流程"""
    result = await report_service.generate_report(
        query="显示所有学生的成绩",
        model="gemini/gemini-2.0-flash-exp",
        session_id="session_123",
        data_source_ids=["test_db"]
    )
    
    # 验证返回结果
    assert isinstance(result, ReportResult)
    assert result.session_id == "session_123"
    assert result.interaction_id == "interaction_123"
    assert result.chart_config is not None
    assert result.summary == "这是一个测试报表总结"
    assert len(result.data) == 2
    assert result.metadata.row_count == 2
    
    # 验证各个服务被正确调用
    report_service.session.get_context.assert_called_once()
    report_service.llm.generate_query_plan.assert_called_once()
    report_service.data_source.execute_query_plan.assert_called_once()
    report_service.llm.analyze_data_and_suggest_chart.assert_called_once()
    report_service.session.add_interaction.assert_called_once()


@pytest.mark.asyncio
async def test_generate_report_with_combination(
    report_service,
    mock_llm_service,
    mock_data_source_manager
):
    """测试需要数据组合的报表生成"""
    # 修改query_plan为需要组合
    mock_llm_service.generate_query_plan = AsyncMock(return_value=QueryPlan(
        sql_queries=[
            SQLQuery(db_config_id="db1", sql="SELECT * FROM t1", source_alias="t1")
        ],
        mcp_calls=[
            MCPCall(
                mcp_config_id="mcp1",
                tool_name="get_data",
                parameters={},
                source_alias="mcp_data"
            )
        ],
        needs_combination=True,
        combination_strategy="SELECT * FROM temp_t1 JOIN temp_mcp_data"
    ))
    
    # 模拟combine_data_with_sql
    combined_data = CombinedData(
        data=[{"id": 1, "name": "张三", "external_data": "test"}],
        columns=["id", "name", "external_data"]
    )
    mock_data_source_manager.combine_data_with_sql = AsyncMock(return_value=combined_data)
    
    # 模拟generate_combination_sql
    mock_llm_service.generate_combination_sql = AsyncMock(
        return_value="SELECT * FROM temp_t1 JOIN temp_mcp_data"
    )
    
    result = await report_service.generate_report(
        query="组合数据库和外部数据",
        model="gemini/gemini-2.0-flash-exp",
        session_id="session_123",
        data_source_ids=["db1", "mcp1"]
    )
    
    # 验证组合流程被调用
    mock_llm_service.generate_combination_sql.assert_called_once()
    mock_data_source_manager.combine_data_with_sql.assert_called_once()
    mock_data_source_manager.cleanup_temp_tables.assert_called_once()
    
    assert isinstance(result, ReportResult)


@pytest.mark.asyncio
async def test_run_saved_report_without_analysis(report_service, mock_database):
    """测试执行常用报表（不带分析）"""
    # 模拟数据库返回的saved_report
    mock_saved_report = Mock()
    mock_saved_report.id = "report_123"
    mock_saved_report.name = "测试报表"
    mock_saved_report.description = "测试描述"
    mock_saved_report.query_plan = json.dumps({
        "sql_queries": [{
            "db_config_id": "test_db",
            "sql": "SELECT * FROM students",
            "source_alias": "students"
        }],
        "mcp_calls": [],
        "needs_combination": False
    })
    mock_saved_report.chart_config = json.dumps({
        "title": {"text": "保存的图表"},
        "series": [{"type": "bar"}]
    })
    mock_saved_report.data_source_ids = json.dumps(["test_db"])
    mock_saved_report.original_query = "显示学生"
    
    # 配置mock_database返回saved_report
    mock_session = mock_database.get_session.return_value.__enter__.return_value
    mock_session.query.return_value.filter.return_value.first.return_value = mock_saved_report
    
    result = await report_service.run_saved_report(
        report_id="report_123",
        with_analysis=False
    )
    
    # 验证结果
    assert isinstance(result, ReportResult)
    assert result.chart_config["title"]["text"] == "保存的图表"
    assert result.summary == "测试描述"
    
    # 验证LLM的analyze方法没有被调用（因为with_analysis=False）
    report_service.llm.analyze_data_and_suggest_chart.assert_not_called()


@pytest.mark.asyncio
async def test_run_saved_report_with_analysis(
    report_service,
    mock_database,
    mock_llm_service
):
    """测试执行常用报表（带分析）"""
    # 模拟数据库返回的saved_report
    mock_saved_report = Mock()
    mock_saved_report.id = "report_123"
    mock_saved_report.name = "测试报表"
    mock_saved_report.description = "测试描述"
    mock_saved_report.query_plan = json.dumps({
        "sql_queries": [{
            "db_config_id": "test_db",
            "sql": "SELECT * FROM students",
            "source_alias": "students"
        }],
        "mcp_calls": [],
        "needs_combination": False
    })
    mock_saved_report.chart_config = json.dumps({
        "title": {"text": "保存的图表"}
    })
    mock_saved_report.data_source_ids = json.dumps(["test_db"])
    mock_saved_report.original_query = "显示学生"
    
    # 配置mock_database返回saved_report
    mock_session = mock_database.get_session.return_value.__enter__.return_value
    mock_session.query.return_value.filter.return_value.first.return_value = mock_saved_report
    
    result = await report_service.run_saved_report(
        report_id="report_123",
        with_analysis=True,
        model="gemini/gemini-2.0-flash-exp"
    )
    
    # 验证结果
    assert isinstance(result, ReportResult)
    # 应该使用LLM生成的新配置
    assert result.chart_config["title"]["text"] == "测试图表"
    assert result.summary == "这是一个测试报表总结"
    
    # 验证LLM的analyze方法被调用了
    mock_llm_service.analyze_data_and_suggest_chart.assert_called_once()


@pytest.mark.asyncio
async def test_build_sql_display(report_service):
    """测试SQL显示字符串构建"""
    query_plan = QueryPlan(
        sql_queries=[
            SQLQuery(
                db_config_id="db1",
                sql="SELECT * FROM table1",
                source_alias="t1"
            )
        ],
        mcp_calls=[
            MCPCall(
                mcp_config_id="mcp1",
                tool_name="get_external_data",
                parameters={"param1": "value1"},
                source_alias="ext"
            )
        ],
        needs_combination=False
    )
    
    sql_display = report_service._build_sql_display(query_plan)
    
    assert "-- 数据库查询 1 (t1)" in sql_display
    assert "SELECT * FROM table1" in sql_display
    assert "-- MCP工具调用 1 (ext)" in sql_display
    assert "get_external_data" in sql_display
    assert "param1" in sql_display


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
