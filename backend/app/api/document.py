"""
CaseWise 法律AI工具 - 法律文书生成API路由

提供法律文书生成相关的HTTP接口：
- POST /api/document/generate: 生成法律文书
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.models.user import UserInfo
from app.api.auth import get_current_user
from app.core.llm import get_llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/document", tags=["法律文书"])


# ============================================================
# 文书类型常量
# ============================================================

DOC_TYPE_DEMAND_LETTER = "demand_letter"
DOC_TYPE_LABOR_ARBITRATION = "labor_arbitration"
DOC_TYPE_CIVIL_COMPLAINT = "civil_complaint"
DOC_TYPE_TERMINATION_NOTICE = "termination_notice"
DOC_TYPE_POWER_OF_ATTORNEY = "power_of_attorney"

# 所有合法文书类型
VALID_DOC_TYPES = {
    DOC_TYPE_DEMAND_LETTER,
    DOC_TYPE_LABOR_ARBITRATION,
    DOC_TYPE_CIVIL_COMPLAINT,
    DOC_TYPE_TERMINATION_NOTICE,
    DOC_TYPE_POWER_OF_ATTORNEY,
}

# 文书类型中文名称映射
DOC_TYPE_NAMES: dict[str, str] = {
    DOC_TYPE_DEMAND_LETTER: "催收函/催告函",
    DOC_TYPE_LABOR_ARBITRATION: "劳动仲裁申请书",
    DOC_TYPE_CIVIL_COMPLAINT: "民事起诉状",
    DOC_TYPE_TERMINATION_NOTICE: "解除劳动合同通知书",
    DOC_TYPE_POWER_OF_ATTORNEY: "授权委托书",
}


# ============================================================
# 请求/响应模型
# ============================================================

class DocumentGenerateRequest(BaseModel):
    """
    法律文书生成请求模型

    Attributes:
        doc_type: 文书类型
        scenario: 场景描述，用户用自然语言描述情况
        details: 可选的补充信息，如当事人姓名、金额等
    """
    doc_type: str = Field(
        ...,
        description="文书类型：demand_letter/labor_arbitration/civil_complaint/termination_notice/power_of_attorney",
    )
    scenario: str = Field(
        ...,
        min_length=10,
        description="场景描述，用户用自然语言描述情况",
    )
    details: Optional[dict] = Field(
        default=None,
        description="可选的补充信息，如当事人姓名、金额等",
    )


class DocumentGenerateResponse(BaseModel):
    """
    法律文书生成响应模型

    Attributes:
        doc_type: 文书类型
        title: 文书标题
        content: 文书正文，Markdown格式
        legal_basis: 法律依据列表
        tips: 使用提示
        disclaimer: 免责声明
    """
    doc_type: str = Field(..., description="文书类型")
    title: str = Field(..., description="文书标题")
    content: str = Field(..., description="文书正文，Markdown格式")
    legal_basis: list[str] = Field(default_factory=list, description="法律依据列表")
    tips: list[str] = Field(default_factory=list, description="使用提示")
    disclaimer: str = Field(..., description="免责声明")


# ============================================================
# 各文书类型的系统提示词
# ============================================================

SYSTEM_PROMPTS: dict[str, str] = {
    DOC_TYPE_DEMAND_LETTER: (
        "你是一名专业的中国法律文书撰写专家，擅长起草催收函/催告函。\n"
        "请根据用户描述的场景，生成一份正式的催收函/催告函。\n\n"
        "要求：\n"
        "1. 文书格式规范，包含标题、致函对象、正文、落款等完整结构\n"
        "2. 明确债务金额、欠款事由、催告期限\n"
        "3. 引用相关法律条文作为催告依据\n"
        "4. 语气正式、严肃，但不得含有威胁性语言\n"
        "5. 注明逾期不履行的法律后果\n"
        "6. 如用户提供了当事人姓名、金额等细节，请准确填入文书\n\n"
        "请以JSON格式输出，包含以下字段：\n"
        "- title: 文书标题\n"
        "- content: 文书正文（Markdown格式）\n"
        "- legal_basis: 法律依据列表（如[\"《中华人民共和国民法典》第五百七十七条\", ...]）\n"
        "- tips: 使用提示列表（如[\"建议通过挂号信或EMS寄送并保留凭证\", ...]）\n"
        "- disclaimer: 免责声明"
    ),

    DOC_TYPE_LABOR_ARBITRATION: (
        "你是一名专业的中国法律文书撰写专家，擅长起草劳动仲裁申请书。\n"
        "请根据用户描述的场景，生成一份正式的劳动仲裁申请书。\n\n"
        "要求：\n"
        "1. 文书格式规范，包含标题、申请人信息、被申请人信息、仲裁请求、事实与理由、证据清单、落款等\n"
        "2. 仲裁请求应明确具体，具有可执行性\n"
        "3. 事实与理由部分应逻辑清晰、条理分明\n"
        "4. 引用相关劳动法律法规作为依据\n"
        "5. 如用户提供了当事人姓名、入职时间、工资标准等细节，请准确填入文书\n"
        "6. 证据清单应列出常见可收集的证据类型\n\n"
        "请以JSON格式输出，包含以下字段：\n"
        "- title: 文书标题\n"
        "- content: 文书正文（Markdown格式）\n"
        "- legal_basis: 法律依据列表（如[\"《中华人民共和国劳动合同法》第四十七条\", ...]）\n"
        "- tips: 使用提示列表（如[\"劳动仲裁申请应在劳动争议发生之日起一年内提出\", ...]）\n"
        "- disclaimer: 免责声明"
    ),

    DOC_TYPE_CIVIL_COMPLAINT: (
        "你是一名专业的中国法律文书撰写专家，擅长起草民事起诉状。\n"
        "请根据用户描述的场景，生成一份正式的民事起诉状。\n\n"
        "要求：\n"
        "1. 文书格式规范，包含标题、原告信息、被告信息、诉讼请求、事实与理由、证据清单、落款等\n"
        "2. 诉讼请求应明确具体，包含具体的金额或行为请求\n"
        "3. 事实与理由部分应按时间顺序叙述，逻辑清晰\n"
        "4. 引用相关民事法律法规作为依据\n"
        "5. 如用户提供了当事人姓名、争议金额、事件经过等细节，请准确填入文书\n"
        "6. 证据清单应列出常见可收集的证据类型\n\n"
        "请以JSON格式输出，包含以下字段：\n"
        "- title: 文书标题\n"
        "- content: 文书正文（Markdown格式）\n"
        "- legal_basis: 法律依据列表（如[\"《中华人民共和国民法典》第一千一百六十五条\", ...]）\n"
        "- tips: 使用提示列表（如[\"起诉前建议先尝试协商或调解\", ...]）\n"
        "- disclaimer: 免责声明"
    ),

    DOC_TYPE_TERMINATION_NOTICE: (
        "你是一名专业的中国法律文书撰写专家，擅长起草解除劳动合同通知书。\n"
        "请根据用户描述的场景，生成一份正式的解除劳动合同通知书。\n\n"
        "要求：\n"
        "1. 文书格式规范，包含标题、致员工、解除原因、法律依据、经济补偿说明、交接要求、落款等\n"
        "2. 解除原因应明确具体，符合法定情形\n"
        "3. 引用相关劳动法律法规作为依据\n"
        "4. 如涉及经济补偿，应明确计算方式和金额\n"
        "5. 如用户提供了员工姓名、入职时间、解除原因等细节，请准确填入文书\n"
        "6. 注明工作交接要求和期限\n\n"
        "请以JSON格式输出，包含以下字段：\n"
        "- title: 文书标题\n"
        "- content: 文书正文（Markdown格式）\n"
        "- legal_basis: 法律依据列表（如[\"《中华人民共和国劳动合同法》第三十六条\", ...]）\n"
        "- tips: 使用提示列表（如[\"建议保留送达凭证，如签收回执或EMS邮寄凭证\", ...]）\n"
        "- disclaimer: 免责声明"
    ),

    DOC_TYPE_POWER_OF_ATTORNEY: (
        "你是一名专业的中国法律文书撰写专家，擅长起草授权委托书。\n"
        "请根据用户描述的场景，生成一份正式的授权委托书。\n\n"
        "要求：\n"
        "1. 文书格式规范，包含标题、委托人信息、受托人信息、委托事项、授权范围、委托期限、落款等\n"
        "2. 委托事项和授权范围应明确具体，避免模糊表述\n"
        "3. 区分一般授权和特别授权\n"
        "4. 如用户提供了委托人姓名、受托人姓名、委托事项等细节，请准确填入文书\n"
        "5. 注明委托期限的起止时间\n"
        "6. 如涉及诉讼代理，应注明是一审、二审还是执行阶段\n\n"
        "请以JSON格式输出，包含以下字段：\n"
        "- title: 文书标题\n"
        "- content: 文书正文（Markdown格式）\n"
        "- legal_basis: 法律依据列表（如[\"《中华人民共和国民法典》第一百六十二条\", ...]）\n"
        "- tips: 使用提示列表（如[\"授权委托书应由委托人本人签字或盖章\", ...]）\n"
        "- disclaimer: 免责声明"
    ),
}


# ============================================================
# 工具函数
# ============================================================

def _build_user_message(request: DocumentGenerateRequest) -> str:
    """
    根据用户请求构建发送给LLM的用户消息

    将场景描述和补充信息整合为结构化的用户消息文本。

    Args:
        request: 文书生成请求

    Returns:
        str: 格式化后的用户消息
    """
    doc_name = DOC_TYPE_NAMES.get(request.doc_type, request.doc_type)
    parts = [
        f"请帮我生成一份【{doc_name}】。",
        f"\n场景描述：{request.scenario}",
    ]
    if request.details:
        parts.append(f"\n补充信息：{json.dumps(request.details, ensure_ascii=False, indent=2)}")
    return "\n".join(parts)


def _parse_llm_response(raw: str, doc_type: str) -> DocumentGenerateResponse:
    """
    解析LLM返回的JSON文本为文书生成响应

    LLM应返回JSON格式的文书内容，此函数负责解析并校验。
    如果JSON解析失败，将原始文本作为content返回。

    Args:
        raw: LLM返回的原始文本
        doc_type: 文书类型

    Returns:
        DocumentGenerateResponse: 解析后的文书生成响应
    """
    # 尝试从返回文本中提取JSON（可能被markdown代码块包裹）
    json_text = raw.strip()
    if json_text.startswith("```"):
        # 去除markdown代码块标记
        first_newline = json_text.index("\n") if "\n" in json_text else -1
        if first_newline >= 0:
            json_text = json_text[first_newline + 1:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]
        json_text = json_text.strip()

    try:
        data = json.loads(json_text)
        return DocumentGenerateResponse(
            doc_type=doc_type,
            title=data.get("title", DOC_TYPE_NAMES.get(doc_type, "法律文书")),
            content=data.get("content", ""),
            legal_basis=data.get("legal_basis", []),
            tips=data.get("tips", []),
            disclaimer=data.get(
                "disclaimer",
                "本文书由AI辅助生成，仅供参考，不构成法律意见。"
                "建议在使用前咨询专业律师，以确保文书的合法性和适用性。",
            ),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("LLM返回内容JSON解析失败，使用原始文本作为content: %s", str(e))
        return DocumentGenerateResponse(
            doc_type=doc_type,
            title=DOC_TYPE_NAMES.get(doc_type, "法律文书"),
            content=raw,
            legal_basis=[],
            tips=["AI返回格式异常，建议重新生成以获取结构化结果"],
            disclaimer=(
                "本文书由AI辅助生成，仅供参考，不构成法律意见。"
                "建议在使用前咨询专业律师，以确保文书的合法性和适用性。"
            ),
        )


# ============================================================
# API路由
# ============================================================

@router.post("/generate", response_model=DocumentGenerateResponse, summary="生成法律文书")
async def generate_document(
    request: DocumentGenerateRequest,
    current_user: UserInfo = Depends(get_current_user),
) -> DocumentGenerateResponse:
    """
    法律文书生成接口

    根据用户提供的文书类型和场景描述，调用LLM生成专业法律文书。
    支持催收函、劳动仲裁申请书、民事起诉状、解除劳动合同通知书、授权委托书等类型。

    Args:
        request: 文书生成请求，包含 doc_type、scenario、details
        current_user: 当前登录用户

    Returns:
        DocumentGenerateResponse: 包含文书标题、正文、法律依据、使用提示、免责声明

    Raises:
        HTTPException: 文书类型无效或LLM调用失败时返回错误
    """
    # 校验文书类型
    if request.doc_type not in VALID_DOC_TYPES:
        valid_types = ", ".join(sorted(VALID_DOC_TYPES))
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文书类型: {request.doc_type}，有效类型为: {valid_types}",
        )

    # 获取对应文书类型的系统提示词
    system_prompt = SYSTEM_PROMPTS.get(request.doc_type)
    if not system_prompt:
        raise HTTPException(status_code=400, detail="缺少该文书类型的系统提示词配置")

    # 构建用户消息
    user_message = _build_user_message(request)

    # 调用LLM生成文书
    try:
        llm_service = get_llm_service()
        raw_response = await llm_service.chat_with_system(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.3,  # 法律文书需要较低的随机性，确保输出稳定专业
            max_tokens=8192,  # 法律文书可能较长，给予充足的生成空间
        )
    except Exception as e:
        logger.error("LLM调用失败，用户: %s, 文书类型: %s, 错误: %s", current_user.username, request.doc_type, str(e))
        raise HTTPException(status_code=500, detail="法律文书生成服务异常，请稍后重试")

    if not raw_response:
        logger.warning("LLM返回空内容，用户: %s, 文书类型: %s", current_user.username, request.doc_type)
        raise HTTPException(status_code=500, detail="法律文书生成失败，AI未返回有效内容，请重试")

    # 解析LLM响应
    result = _parse_llm_response(raw_response, request.doc_type)

    logger.info(
        "法律文书生成完成，用户: %s, 文书类型: %s, 标题: %s",
        current_user.username,
        request.doc_type,
        result.title,
    )

    return result
