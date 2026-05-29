"""
CaseWise 法律AI工具 - 合规声明生成模块

为每个 AI 输出自动附加合规声明，
确保用户明确知晓 AI 生成内容的局限性，
降低法律风险。
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    合规声明服务

    生成标准化的合规声明文本，附加到 AI 输出中，
    确保用户了解 AI 生成内容仅供参考，不构成法律意见。
    """

    # 默认合规声明
    DEFAULT_NOTICE = "本内容仅供参考，不构成法律意见"

    # 不同场景的合规声明模板
    COMPLIANCE_TEMPLATES = {
        "chat": (
            "【合规声明】{notice}。本回答由AI生成，"
            "可能存在不准确或遗漏之处。如需正式法律意见，请咨询专业律师。"
            "生成时间：{timestamp}"
        ),
        "contract": (
            "【合规声明】{notice}。本合同审查结果由AI生成，"
            "不构成法律意见或建议。重要合同请务必由专业律师审核。"
            "审查时间：{timestamp}"
        ),
        "review": (
            "【合规声明】{notice}。本复核反馈由AI辅助生成，"
            "最终结论需由专业法律人员确认。"
            "反馈时间：{timestamp}"
        ),
    }

    def __init__(self) -> None:
        """
        初始化合规声明服务
        """
        logger.info("ComplianceService 初始化完成")

    def generate_notice(self, scene: str = "chat", custom_notice: Optional[str] = None) -> str:
        """
        生成合规声明文本

        根据不同场景生成对应的合规声明，可自定义核心声明内容。

        Args:
            scene: 场景类型，可选值：chat/contract/review
            custom_notice: 自定义核心声明内容，为空则使用默认声明

        Returns:
            str: 格式化的合规声明文本
        """
        notice = custom_notice or self.DEFAULT_NOTICE
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        template = self.COMPLIANCE_TEMPLATES.get(scene, self.COMPLIANCE_TEMPLATES["chat"])
        compliance_text = template.format(notice=notice, timestamp=timestamp)

        logger.debug("生成合规声明，场景: %s", scene)
        return compliance_text

    def generate_short_notice(self) -> str:
        """
        生成简短合规声明

        适用于空间有限的展示场景。

        Returns:
            str: 简短的合规声明文本
        """
        return self.DEFAULT_NOTICE

    def generate_detailed_notice(
        self,
        scene: str = "chat",
        custom_notice: Optional[str] = None,
        additional_disclaimers: Optional[list[str]] = None,
    ) -> str:
        """
        生成详细合规声明

        包含核心声明、场景说明和额外免责条款。

        Args:
            scene: 场景类型
            custom_notice: 自定义核心声明
            additional_disclaimers: 额外的免责条款列表

        Returns:
            str: 详细的合规声明文本
        """
        base_notice = self.generate_notice(scene, custom_notice)

        if additional_disclaimers:
            disclaimer_text = "\n".join(
                f"  {i + 1}. {d}" for i, d in enumerate(additional_disclaimers)
            )
            detailed = f"{base_notice}\n\n额外免责声明：\n{disclaimer_text}"
        else:
            detailed = base_notice

        return detailed


# 全局合规服务单例
_compliance_service: Optional[ComplianceService] = None


def get_compliance_service() -> ComplianceService:
    """
    获取合规声明服务单例

    Returns:
        ComplianceService: 合规声明服务实例
    """
    global _compliance_service
    if _compliance_service is None:
        _compliance_service = ComplianceService()
    return _compliance_service
