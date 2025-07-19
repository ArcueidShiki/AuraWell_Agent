#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP智能工具管理器 v2.0 - 真实MCP集成版本
支持真实MCP工具和占位符工具的混合使用
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .mcp_tools_manager import MCPToolsManager, IntentAnalyzer, WorkflowResult
from .mcp_interface import MCPToolInterface
from .mcp_tools_enhanced import EnhancedMCPTools, ToolExecutionMode

logger = logging.getLogger(__name__)


class ToolMode(Enum):
    """工具模式"""
    REAL_MCP = "real_mcp"        # 使用真实MCP工具
    PLACEHOLDER = "placeholder"   # 使用占位符工具
    HYBRID = "hybrid"            # 混合模式：优先真实，降级到占位符


@dataclass
class ToolCallResult:
    """工具调用结果"""
    success: bool
    result: Any
    tool_name: str
    mode_used: ToolMode
    error: Optional[str] = None
    execution_time: float = 0.0


class MCPToolsManagerV2(MCPToolsManager):
    """
    MCP智能工具管理器 v2.0
    
    新特性：
    - 支持真实MCP工具连接
    - 混合模式：真实工具优先，占位符降级
    - 改进的错误处理和重试机制
    - 工具性能监控
    """
    
    def __init__(self, tool_mode: ToolMode = ToolMode.HYBRID):
        super().__init__()
        self.tool_mode = tool_mode

        # 映射工具模式
        enhanced_mode = ToolExecutionMode.HYBRID
        if tool_mode == ToolMode.REAL_MCP:
            enhanced_mode = ToolExecutionMode.REAL
        elif tool_mode == ToolMode.PLACEHOLDER:
            enhanced_mode = ToolExecutionMode.PLACEHOLDER

        # 使用增强工具实现
        self.enhanced_tools = EnhancedMCPTools(enhanced_mode)
        self.tool_performance_stats = {}

        logger.info(f"🚀 初始化MCP工具管理器v2.0，模式: {tool_mode.value}")
    
    async def initialize(self):
        """初始化工具管理器"""
        try:
            # 初始化增强工具
            await self.enhanced_tools.initialize_real_interface()
            logger.info("✅ 增强MCP工具初始化成功")
        except ImportError:
            logger.warning("⚠️ 真实MCP依赖未安装，请运行: pip install mcp")
            if self.tool_mode == ToolMode.REAL_MCP:
                raise RuntimeError("真实MCP模式需要安装MCP依赖")
        except Exception as e:
            logger.warning(f"⚠️ 增强MCP工具初始化失败: {e}")
            if self.tool_mode == ToolMode.REAL_MCP:
                raise

        logger.info(f"🎯 最终工具模式: {self.tool_mode.value}")
    
    async def call_tool_smart(self, tool_name: str, action: str, parameters: Dict[str, Any]) -> ToolCallResult:
        """
        智能工具调用
        使用增强工具实现智能降级
        """
        # 使用增强工具进行调用
        enhanced_result = await self.enhanced_tools.call_tool(tool_name, action, parameters)

        # 转换结果格式
        mode_mapping = {
            ToolExecutionMode.REAL: ToolMode.REAL_MCP,
            ToolExecutionMode.PLACEHOLDER: ToolMode.PLACEHOLDER,
            ToolExecutionMode.HYBRID: ToolMode.HYBRID
        }

        return ToolCallResult(
            success=enhanced_result.success,
            result=enhanced_result.data,
            tool_name=enhanced_result.tool_name,
            mode_used=mode_mapping.get(enhanced_result.mode_used, ToolMode.PLACEHOLDER),
            error=enhanced_result.error,
            execution_time=enhanced_result.execution_time
        )
    
    async def _call_real_mcp_tool(self, tool_name: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用真实MCP工具"""
        if not self.real_mcp_interface:
            raise RuntimeError("真实MCP接口未初始化")
        
        # 映射工具名称到真实MCP方法
        tool_mapping = {
            "database_sqlite": self._call_real_database,
            "calculator": self._call_real_calculator,
            "brave_search": self._call_real_search,
            "filesystem": self._call_real_filesystem,
            "time": self._call_real_time,
        }
        
        if tool_name in tool_mapping:
            return await tool_mapping[tool_name](action, parameters)
        else:
            # 尝试通用工具调用
            return await self.real_mcp_interface.call_tool(action, parameters)
    
    async def _call_placeholder_tool(self, tool_name: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用占位符工具"""
        result = await self.placeholder_interface.call_tool(tool_name, action, parameters, timeout=10.0)
        return result.data
    
    # 真实MCP工具映射方法
    
    async def _call_real_database(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用真实数据库工具"""
        if action == "query":
            return await self.real_mcp_interface.database_query(parameters.get("sql", ""))
        else:
            raise ValueError(f"不支持的数据库操作: {action}")
    
    async def _call_real_calculator(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用真实计算器工具"""
        if action == "calculate":
            return await self.real_mcp_interface.calculator_calculate(parameters.get("expression", ""))
        else:
            raise ValueError(f"不支持的计算器操作: {action}")
    
    async def _call_real_search(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用真实搜索工具"""
        if action == "search":
            return await self.real_mcp_interface.brave_search(
                parameters.get("query", ""),
                parameters.get("count", 5)
            )
        else:
            raise ValueError(f"不支持的搜索操作: {action}")
    
    async def _call_real_filesystem(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用真实文件系统工具"""
        if action == "read_file":
            return await self.real_mcp_interface.filesystem_read(parameters.get("path", ""))
        elif action == "write_file":
            return await self.real_mcp_interface.filesystem_write(
                parameters.get("path", ""),
                parameters.get("content", "")
            )
        else:
            raise ValueError(f"不支持的文件系统操作: {action}")
    
    async def _call_real_time(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用真实时间工具"""
        if action == "get_time":
            return await self.real_mcp_interface.get_current_time()
        else:
            raise ValueError(f"不支持的时间操作: {action}")
    
    def _update_performance_stats(self, tool_name: str, success: bool, execution_time: float):
        """更新工具性能统计"""
        if tool_name not in self.tool_performance_stats:
            self.tool_performance_stats[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_execution_time": 0.0,
                "average_execution_time": 0.0
            }
        
        stats = self.tool_performance_stats[tool_name]
        stats["total_calls"] += 1
        stats["total_execution_time"] += execution_time
        stats["average_execution_time"] = stats["total_execution_time"] / stats["total_calls"]
        
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
    
    async def execute_workflow_v2(self, workflow_name: str, user_input: str, context: Dict[str, Any]) -> WorkflowResult:
        """
        执行智能工作流 v2.0
        支持真实MCP工具和性能监控
        """
        logger.info(f"🔄 执行工作流 v2.0: {workflow_name}")
        
        # 获取工作流配置
        workflow_config = self.workflows.get(workflow_name)
        if not workflow_config:
            return WorkflowResult(
                success=False,
                workflow_name=workflow_name,
                results={},
                execution_summary="工作流配置不存在"
            )
        
        results = {}
        execution_summary = []
        
        # 执行工作流步骤
        for step in workflow_config["tools"]:
            tool_name = step["tool"]
            action = step["action"]
            parameters = step.get("parameters", {})
            
            # 参数化处理
            if "user_input" in parameters and parameters["user_input"] == "{{user_input}}":
                parameters["user_input"] = user_input
            
            try:
                # 使用智能工具调用
                result = await self.call_tool_smart(tool_name, action, parameters)
                
                results[f"{tool_name}_{action}"] = result.result
                execution_summary.append(
                    f"✅ {tool_name}.{action} ({result.mode_used.value}) - {result.execution_time:.2f}s"
                )
                
                if not result.success:
                    logger.warning(f"⚠️ 工具调用失败但继续执行: {result.error}")
                
            except Exception as e:
                error_msg = f"❌ {tool_name}.{action} 失败: {e}"
                execution_summary.append(error_msg)
                logger.error(error_msg)
        
        return WorkflowResult(
            success=True,
            workflow_name=workflow_name,
            results=results,
            execution_summary="\n".join(execution_summary),
            metadata={
                "tool_mode": self.tool_mode.value,
                "total_steps": len(workflow_config["tools"]),
                "completed_steps": len(results)
            }
        )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取工具性能报告"""
        enhanced_report = self.enhanced_tools.get_performance_report()

        return {
            "tool_mode": self.tool_mode.value,
            "enhanced_tools_report": enhanced_report,
            "legacy_stats": self.tool_performance_stats,
            "summary": enhanced_report.get("summary", {}),
            "recommendations": self._generate_performance_recommendations(enhanced_report)
        }

    def _generate_performance_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """生成性能优化建议"""
        recommendations = []

        success_rate = report.get("summary", {}).get("success_rate", 100)
        if success_rate < 90:
            recommendations.append("工具成功率较低，建议检查网络连接和API配置")

        total_calls = report.get("summary", {}).get("total_calls", 0)
        if total_calls == 0:
            recommendations.append("尚未有工具调用记录，建议进行功能测试")

        if self.tool_mode == ToolMode.HYBRID:
            recommendations.append("当前使用混合模式，可获得最佳的可靠性和性能平衡")

        return recommendations
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            "tool_mode": self.tool_mode.value,
            "placeholder_interface": "available",
            "real_mcp_interface": "not_available"
        }
        
        # 检查真实MCP接口
        if self.real_mcp_interface:
            try:
                tools = await self.real_mcp_interface.list_available_tools()
                health_status["real_mcp_interface"] = "available"
                health_status["real_mcp_tools_count"] = len(tools)
            except Exception as e:
                health_status["real_mcp_interface"] = f"error: {e}"
        
        return health_status
    
    async def cleanup(self):
        """清理资源"""
        if self.real_mcp_interface:
            await self.real_mcp_interface.cleanup()
        logger.info("🧹 MCP工具管理器v2.0资源清理完成")


# 全局实例
_mcp_tools_manager_v2 = None


async def get_mcp_tools_manager_v2(tool_mode: ToolMode = ToolMode.HYBRID) -> MCPToolsManagerV2:
    """获取全局MCP工具管理器v2.0实例"""
    global _mcp_tools_manager_v2
    if _mcp_tools_manager_v2 is None:
        _mcp_tools_manager_v2 = MCPToolsManagerV2(tool_mode)
        await _mcp_tools_manager_v2.initialize()
    return _mcp_tools_manager_v2 