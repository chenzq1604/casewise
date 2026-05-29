"""
CaseWise 法律AI工具 - 数据采集引擎模块

实现后台数据采集引擎，支持：
- 从内嵌法条数据或外部数据源获取法条JSON数据
- 解析法条数据，提取法条编号、标题、正文、生效日期
- 使用 doubao-embedding-vision 生成向量
- 存入 ChromaDB（laws_child 和 laws_parent 两个collection）
- 同时构建 BM25 索引
- 实时追踪采集进度
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import chromadb
from rank_bm25 import BM25Okapi

from app.config import settings
from app.core.chroma_client import get_chroma_client
from app.core.embedding import get_embedding_service

logger = logging.getLogger(__name__)


# ========== 法律类型配置 ==========

LAW_CATEGORIES = {
    "civil": {"name": "民法典", "description": "中华人民共和国民法典（合同编、物权编、侵权编等）"},
    "labor": {"name": "劳动法", "description": "劳动法+劳动合同法+劳动争议调解仲裁法"},
    "company": {"name": "公司法", "description": "中华人民共和国公司法"},
    "construction": {"name": "建工法规", "description": "建筑法+建设工程相关司法解释"},
    "finance": {"name": "金融法规", "description": "银行法+证券法+保险法"},
    "criminal": {"name": "刑法", "description": "中华人民共和国刑法"},
}


# ========== 内嵌法条数据（MVP阶段使用） ==========

EMBEDDED_LAWS = {
    "civil": [
        # ---- 第三编 合同 ----
        {"law_id": "civil_469", "title": "第四百六十九条", "content": "当事人订立合同，可以采用书面形式、口头形式或者其他形式。书面形式是合同书、信件、电报、电传、传真等可以有形地表现所载内容的形式。以电子数据交换、电子邮件等方式能够有形地表现所载内容，并可以随时调取查用的数据电文，视为书面形式。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_470", "title": "第四百七十条", "content": "合同的内容由当事人约定，一般包括下列条款：（一）当事人的姓名或者名称和住所；（二）标的；（三）数量；（四）质量；（五）价款或者报酬；（六）履行期限、地点和方式；（七）违约责任；（八）解决争议的方法。当事人可以参照各类合同的示范文本订立合同。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_471", "title": "第四百七十一条", "content": "当事人订立合同，可以采取要约、承诺方式或者其他方式。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_472", "title": "第四百七十二条", "content": "要约是希望与他人订立合同的意思表示，该意思表示应当符合下列条件：（一）内容具体确定；（二）表明经受要约人承诺，要约人即受该意思表示约束。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_473", "title": "第四百七十三条", "content": "要约邀请是希望他人向自己发出要约的表示。拍卖公告、招标公告、招股说明书、债券募集办法、基金招募说明书、商业广告和宣传、寄送的价目表等为要约邀请。商业广告和宣传的内容符合要约条件的，构成要约。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_474", "title": "第四百七十四条", "content": "要约生效的时间适用本法第一百三十七条的规定。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_475", "title": "第四百七十五条", "content": "要约可以撤回。要约的撤回适用本法第一百四十一条的规定。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_476", "title": "第四百七十六条", "content": "要约可以撤销，但是有下列情形之一的除外：（一）要约人以确定承诺期限或者其他形式明示要约不可撤销；（二）受要约人有理由认为要约是不可撤销的，并已经为履行合同做了合理准备工作。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_477", "title": "第四百七十七条", "content": "撤销要约的意思表示以对话方式作出的，该意思表示的内容应当在受要约人作出承诺之前为受要约人所知道；撤销要约的意思表示以非对话方式作出的，应当在受要约人作出承诺之前到达受要约人。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_478", "title": "第四百七十八条", "content": "有下列情形之一的，要约失效：（一）要约被拒绝；（二）要约被依法撤销；（三）承诺期限届满，受要约人未作出承诺；（四）受要约人对要约的内容作出实质性变更。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_479", "title": "第四百七十九条", "content": "承诺是受要约人同意要约的意思表示。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_480", "title": "第四百八十条", "content": "承诺应当以通知的方式作出；但是，根据交易习惯或者要约表明可以通过行为作出承诺的除外。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_481", "title": "第四百八十一条", "content": "承诺应当在要约确定的期限内到达要约人。要约没有确定承诺期限的，承诺应当依照下列规定到达：（一）要约以对话方式作出的，应当即时作出承诺；（二）要约以非对话方式作出的，承诺应当在合理期限内到达。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_483", "title": "第四百八十三条", "content": "承诺生效时合同成立，但是法律另有规定或者当事人另有约定的除外。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_484", "title": "第四百八十四条", "content": "以通知方式作出的承诺，生效的时间适用本法第一百三十七条的规定。承诺不需要通知的，根据交易习惯或者要约的要求作出承诺的行为时生效。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_485", "title": "第四百八十五条", "content": "承诺可以撤回。承诺的撤回适用本法第一百四十一条的规定。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_486", "title": "第四百八十六条", "content": "受要约人超过承诺期限发出承诺，或者在承诺期限内发出承诺，按照通常情形不能及时到达要约人的，为新要约；但是，要约人及时通知受要约人该承诺有效的除外。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_488", "title": "第四百八十八条", "content": "承诺的内容应当与要约的内容一致。受要约人对要约的内容作出实质性变更的，为新要约。有关合同标的、数量、质量、价款或者报酬、履行期限、履行地点和方式、违约责任和解决争议方法等的变更，是对要约内容的实质性变更。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_489", "title": "第四百八十九条", "content": "承诺对要约的内容作出非实质性变更的，除要约人及时表示反对或者要约表明承诺不得对要约的内容作出任何变更外，该承诺有效，合同的内容以承诺的内容为准。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_490", "title": "第四百九十条", "content": "当事人采用合同书形式订立合同的，自当事人均签名、盖章或者按指印时合同成立。在签名、盖章或者按指印之前，当事人一方已经履行主要义务，对方接受时，该合同成立。法律、行政法规规定或者当事人约定合同应当采用书面形式订立，当事人未采用书面形式但是一方已经履行主要义务，对方接受时，该合同成立。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_491", "title": "第四百九十一条", "content": "当事人采用信件、数据电文等形式订立合同要求签订确认书的，签订确认书时合同成立。当事人一方通过互联网等信息网络发布的商品或者服务信息符合要约条件的，对方选择该商品或者服务并提交订单成功时合同成立，但是当事人另有约定的除外。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_492", "title": "第四百九十二条", "content": "承诺生效的地点为合同成立的地点。采用数据电文形式订立合同的，收件人的主营业地为合同成立的地点；没有主营业地的，其住所地为合同成立的地点。当事人另有约定的，按照其约定。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_493", "title": "第四百九十三条", "content": "当事人采用合同书形式订立合同的，最后签名、盖章或者按指印的地点为合同成立的地点，但是当事人另有约定的除外。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_494", "title": "第四百九十四条", "content": "国家根据抢险救灾、疫情防控或者其他需要下达国家订货任务、指令性任务的，有关民事主体之间应当依照有关法律、行政法规规定的权利和义务订立合同。依照法律、行政法规的规定负有发出要约义务的当事人，应当及时发出合理的要约。依照法律、行政法规的规定负有作出承诺义务的当事人，不得拒绝对方合理的订立合同要求。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_495", "title": "第四百九十五条", "content": "当事人约定在将来一定期限内订立合同的认购书、订购书、预订书等，构成预约合同。当事人一方不履行预约合同约定的订立合同义务的，对方可以请求其承担预约合同的违约责任。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_496", "title": "第四百九十六条", "content": "格式条款是当事人为了重复使用而预先拟定，并在订立合同时未与对方协商的条款。采用格式条款订立合同的，提供格式条款的一方应当遵循公平原则确定当事人之间的权利和义务，并采取合理的方式提示对方注意免除或者减轻其责任等与对方有重大利害关系的条款，按照对方的要求，对该条款予以说明。提供格式条款的一方未履行提示或者说明义务，致使对方没有注意或者理解与其有重大利害关系的条款的，对方可以主张该条款不成为合同的内容。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_497", "title": "第四百九十七条", "content": "有下列情形之一的，该格式条款无效：（一）具有本法第一编第六章第三节和本法第五百零六条规定的无效情形；（二）提供格式条款一方不合理地免除或者减轻其责任、加重对方责任、限制对方主要权利；（三）提供格式条款一方排除对方主要权利。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_498", "title": "第四百九十八条", "content": "对格式条款的理解发生争议的，应当按照通常理解予以解释。对格式条款有两种以上解释的，应当作出不利于提供格式条款一方的解释。格式条款和非格式条款不一致的，应当采用非格式条款。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_499", "title": "第四百九十九条", "content": "悬赏人以公开方式声明对完成特定行为的人支付报酬的，完成该行为的人可以请求其支付。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_500", "title": "第五百条", "content": "当事人在订立合同过程中有下列情形之一，造成对方损失的，应当承担赔偿责任：（一）假借订立合同，恶意进行磋商；（二）故意隐瞒与订立合同有关的重要事实或者提供虚假情况；（三）有其他违背诚信原则的行为。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_501", "title": "第五百零一条", "content": "当事人在订立合同过程中知悉的商业秘密或者其他应当保密的信息，无论合同是否成立，不得泄露或者不正当地使用；泄露、不正当地使用该商业秘密或者信息，造成对方损失的，应当承担赔偿责任。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_502", "title": "第五百零二条", "content": "依法成立的合同，自成立时生效，但是法律另有规定或者当事人另有约定的除外。依照法律、行政法规的规定，合同应当办理批准等手续的，依照其规定。未办理批准等手续影响合同生效的，不影响合同中履行报批等义务条款以及相关条款的效力。应当办理申请批准等手续的当事人未履行义务的，对方可以请求其承担违反该义务的责任。依照法律、行政法规的规定，合同的变更、转让、解除等情形应当办理批准等手续的，适用前款规定。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_503", "title": "第五百零三条", "content": "无权代理人以被代理人的名义订立合同，被代理人已经开始履行合同义务或者接受相对人履行的，视为对合同的追认。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_504", "title": "第五百零四条", "content": "法人的法定代表人或者非法人组织的负责人超越权限订立的合同，除相对人知道或者应当知道其超越权限外，该代表行为有效，订立的合同对法人或者非法人组织发生效力。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_505", "title": "第五百零五条", "content": "当事人超越经营范围订立的合同的效力，应当依照本法第一编第六章第三节和本编的有关规定确定，不得仅以超越经营范围确认合同无效。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_506", "title": "第五百零六条", "content": "合同中的下列免责条款无效：（一）造成对方人身损害的；（二）因故意或者重大过失造成对方财产损失的。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_507", "title": "第五百零七条", "content": "合同不生效、无效、被撤销或者终止的，不影响合同中有关解决争议方法的条款的效力。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_508", "title": "第五百零八条", "content": "本编对合同的效力没有规定的，适用本法第一编第六章的有关规定。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_509", "title": "第五百零九条", "content": "当事人应当按照约定全面履行自己的义务。当事人应当遵循诚信原则，根据合同的性质、目的和交易习惯履行通知、协助、保密等义务。当事人在履行合同过程中，应当避免浪费资源、污染环境和破坏生态。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_510", "title": "第五百一十条", "content": "合同生效后，当事人就质量、价款或者报酬、履行地点等内容没有约定或者约定不明确的，可以协议补充；不能达成补充协议的，按照合同相关条款或者交易习惯确定。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_511", "title": "第五百一十一条", "content": "当事人就有关合同内容约定不明确，依据前条规定仍不能确定的，适用下列规定：（一）质量要求不明确的，按照强制性国家标准履行；没有强制性国家标准的，按照推荐性国家标准履行；没有推荐性国家标准的，按照行业标准履行；没有国家标准、行业标准的，按照通常标准或者符合合同目的的特定标准履行。（二）价款或者报酬不明确的，按照订立合同时履行地的市场价格履行；依法应当执行政府定价或者政府指导价的，依照规定履行。（三）履行地点不明确，给付货币的，在接受货币一方所在地履行；交付不动产的，在不动产所在地履行；其他标的，在履行义务一方所在地履行。（四）履行期限不明确的，债务人可以随时履行，债权人也可以随时请求履行，但是应当给对方必要的准备时间。（五）履行方式不明确的，按照有利于实现合同目的的方式履行。（六）履行费用的负担不明确的，由履行义务一方负担；因债权人原因增加的履行费用，由债权人负担。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_512", "title": "第五百一十二条", "content": "通过互联网等信息网络订立的电子合同的标的为交付商品并采用快递物流方式交付的，收货人的签收时间为交付时间。电子合同的标的为提供服务的，生成的电子凭证或者实物凭证中载明的时间为提供服务时间；前述凭证没有载明时间或者载明时间与实际提供服务时间不一致的，以实际提供服务的时间为准。电子合同的标的物为采用在线传输方式交付的，合同标的物进入对方当事人指定的特定系统并且能够检索识别的时间为交付时间。电子合同当事人对交付商品或者提供服务的方式、时间另有约定的，按照其约定。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_513", "title": "第五百一十三条", "content": "执行政府定价或者政府指导价的，在合同约定的交付期限内政府价格调整时，按照交付时的价格计价。逾期交付标的物的，遇价格上涨时，按照原价格执行；价格下降时，按照新价格执行。逾期提取标的物或者逾期付款的，遇价格上涨时，按照新价格执行；价格下降时，按照原价格执行。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_514", "title": "第五百一十四条", "content": "以支付金钱为内容的债，除法律另有规定或者当事人另有约定外，债权人可以请求债务人以实际履行地的法定货币履行。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_515", "title": "第五百一十五条", "content": "标的有多项而债务人只需履行其中一项的，债务人享有选择权；但是，法律另有规定、当事人另有约定或者另有交易习惯的除外。享有选择权的当事人在约定期限内或者履行期限届满未作选择，经催告后在合理期限内仍未选择，选择权转移至对方。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_516", "title": "第五百一十六条", "content": "当事人行使选择权应当及时通知对方，通知到达对方时，标的确定。标的确定后不得变更，但是经对方同意的除外。可选择的标的发生不能履行情形的，享有选择权的当事人不得选择不能履行的标的，但是该不能履行情形是由对方造成的除外。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_522", "title": "第五百二十二条", "content": "当事人约定由债务人向第三人履行债务，债务人未向第三人履行债务或者履行债务不符合约定的，应当向债权人承担违约责任。法律规定或者当事人约定第三人可以直接请求债务人向其履行债务，第三人未在合理期限内明确拒绝，债务人未向第三人履行债务或者履行债务不符合约定的，第三人可以请求债务人承担违约责任；债务人对债权人的抗辩，可以向第三人主张。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_523", "title": "第五百二十三条", "content": "当事人约定由第三人向债权人履行债务，第三人不履行债务或者履行债务不符合约定的，债务人应当向债权人承担违约责任。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_524", "title": "第五百二十四条", "content": "债务人不履行债务，第三人对履行该债务具有合法利益的，第三人有权向债权人代为履行；但是，根据债务性质、按照当事人约定或者依照法律规定只能由债务人履行的除外。债权人接受第三人履行后，其对债务人的债权转让给第三人，但是债务人和第三人另有约定的除外。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_525", "title": "第五百二十五条", "content": "当事人互负债务，没有约定履行顺序的，应当同时履行。一方在对方履行之前有权拒绝其履行请求。一方在对方履行债务不符合约定时，有权拒绝其相应的履行请求。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_526", "title": "第五百二十六条", "content": "当事人互负债务，有先后履行顺序，应当先履行债务一方未履行的，后履行一方有权拒绝其履行请求。先履行一方履行债务不符合约定的，后履行一方有权拒绝其相应的履行请求。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_527", "title": "第五百二十七条", "content": "应当先履行债务的当事人，有确切证据证明对方有下列情形之一的，可以中止履行：（一）经营状况严重恶化；（二）转移财产、抽逃资金，以逃避债务；（三）丧失商业信誉；（四）有丧失或者可能丧失履行债务能力的其他情形。当事人没有确切证据中止履行的，应当承担违约责任。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_528", "title": "第五百二十八条", "content": "当事人依据前条规定中止履行的，应当及时通知对方。对方提供适当担保的，应当恢复履行。中止履行后，对方在合理期限内未恢复履行能力且未提供适当担保的，视为以自己的行为表明不履行主要债务，中止履行的一方可以解除合同并可以请求对方承担违约责任。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_535", "title": "第五百三十五条", "content": "因债务人怠于行使其债权或者与该债权有关的从权利，影响债权人的到期债权实现的，债权人可以向人民法院请求以自己的名义代位行使债务人对相对人的权利，但是该权利专属于债务人自身的除外。代位权的行使范围以债权人的到期债权为限。债权人行使代位权的必要费用，由债务人负担。相对人对债务人的抗辩，可以向债权人主张。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_538", "title": "第五百三十八条", "content": "债务人以放弃其债权、放弃债权担保、无偿转让财产等方式无偿处分财产权益，或者恶意延长其到期债权的履行期限，影响债权人的债权实现的，债权人可以请求人民法院撤销债务人的行为。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_539", "title": "第五百三十九条", "content": "债务人以明显不合理的低价转让财产、以明显不合理的高价受让他人财产或者为他人的债务提供担保，影响债权人的债权实现，债务人的相对人知道或者应当知道该情形的，债权人可以请求人民法院撤销债务人的行为。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_551", "title": "第五百五十一条", "content": "债务人将债务的全部或者部分转移给第三人的，应当经债权人同意。债务人或者第三人可以催告债权人在合理期限内予以同意，债权人未作表示的，视为不同意。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_552", "title": "第五百五十二条", "content": "第三人与债务人约定加入债务并通知债权人或者第三人向债权人表示愿意加入债务，债权人未在合理期限内明确拒绝的，债权人可以请求第三人在其愿意承担的债务范围内和债务人承担连带债务。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_562", "title": "第五百六十二条", "content": "当事人协商一致，可以解除合同。当事人可以约定一方解除合同的事由。解除合同的事由发生时，解除权人可以解除合同。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_563", "title": "第五百六十三条", "content": "有下列情形之一的，当事人可以解除合同：（一）因不可抗力致使不能实现合同目的；（二）在履行期限届满前，当事人一方明确表示或者以自己的行为表明不履行主要债务；（三）当事人一方迟延履行主要债务，经催告后在合理期限内仍未履行；（四）当事人一方迟延履行债务或者有其他违约行为致使不能实现合同目的；（五）法律规定的其他情形。以持续履行的债务为内容的不定期合同，当事人可以随时解除合同，但是应当在合理期限之前通知对方。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_565", "title": "第五百六十五条", "content": "当事人一方依法主张解除合同的，应当通知对方。合同自通知到达对方时解除；通知载明债务人在一定期限内不履行债务则合同自动解除，债务人在该期限内未履行债务的，合同自通知载明的期限届满时解除。对方对解除合同有异议的，任何一方当事人均可以请求人民法院或者仲裁机构确认解除行为的效力。当事人一方未通知对方，直接以提起诉讼或者申请仲裁的方式依法主张解除合同，人民法院或者仲裁机构确认该主张的，合同自起诉状副本或者仲裁申请书副本送达对方时解除。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_566", "title": "第五百六十六条", "content": "合同解除后，尚未履行的，终止履行；已经履行的，根据履行情况和合同性质，当事人可以请求恢复原状或者采取其他补救措施，并有权请求赔偿损失。合同因违约解除的，解除权人可以请求违约方承担违约责任，但是当事人另有约定的除外。主合同解除后，担保人对债务人应当承担的民事责任仍应当承担担保责任，但是担保合同另有约定的除外。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_567", "title": "第五百六十七条", "content": "合同的权利义务关系终止，不影响合同中结算和清理条款的效力。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_568", "title": "第五百六十八条", "content": "当事人互负债务，该债务的标的物种类、品质相同的，任何一方可以将自己的债务与对方的到期债务抵销；但是，根据债务性质、按照当事人约定或者依照法律规定不得抵销的除外。当事人主张抵销的，应当通知对方。通知自到达对方时生效。抵销不得附条件或者附期限。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_577", "title": "第五百七十七条", "content": "当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_578", "title": "第五百七十八条", "content": "当事人一方明确表示或者以自己的行为表明不履行合同义务的，对方可以在履行期限届满前请求其承担违约责任。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_579", "title": "第五百七十九条", "content": "当事人一方未支付价款、报酬、租金、利息，或者不履行其他金钱债务的，对方可以请求其支付。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_580", "title": "第五百八十条", "content": "当事人一方不履行非金钱债务或者履行非金钱债务不符合约定的，对方可以请求履行，但是有下列情形之一的除外：（一）法律上或者事实上不能履行；（二）债务的标的不适于强制履行或者履行费用过高；（三）债权人在合理期限内未请求履行。有前款规定的除外情形之一，致使不能实现合同目的的，人民法院或者仲裁机构可以根据当事人的请求终止合同权利义务关系，但是不影响违约责任的承担。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_581", "title": "第五百八十一条", "content": "当事人一方不履行债务或者履行债务不符合约定，根据债务的性质不得强制履行的，对方可以请求其负担由第三人替代履行的费用。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_582", "title": "第五百八十二条", "content": "履行不符合约定的，应当按照当事人的约定承担违约责任。对违约责任没有约定或者约定不明确，依据本法第五百一十条的规定仍不能确定的，受损害方根据标的的性质以及损失的大小，可以合理选择请求对方承担修理、重作、更换、退货、减少价款或者报酬等违约责任。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_583", "title": "第五百八十三条", "content": "当事人一方不履行合同义务或者履行合同义务不符合约定的，在履行义务或者采取补救措施后，对方还有其他损失的，应当赔偿损失。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_584", "title": "第五百八十四条", "content": "当事人一方不履行合同义务或者履行合同义务不符合约定，造成对方损失的，损失赔偿额应当相当于因违约所造成的损失，包括合同履行后可以获得的利益；但是，不得超过违约一方订立合同时预见到或者应当预见到的因违约可能造成的损失。", "chapter": "第三编 合同", "section": "第一分编 通则"},
        {"law_id": "civil_585", "title": "第五百八十五条", "content": "当事人可以约定一方违约时应当根据违约情况向对方支付一定数额的违约金，也可以约定因违约产生的损失赔偿额的计算方法。约定的违约金低于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以增加；约定的违约金过分高于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以适当减少。当事人就迟延履行约定违约金的，违约方支付违约金后，还应当履行债务。", "chapter": "第三编 合同", "section": "第一分编 通则"},
    ],
    "labor": [
        {"law_id": "labor_1", "title": "第一条", "content": "为了保护劳动者的合法权益，调整劳动关系，建立和维护适应社会主义市场经济的劳动制度，促进经济发展和社会进步，根据宪法，制定本法。", "chapter": "总则", "section": "第一章 总则"},
        {"law_id": "labor_3", "title": "第三条", "content": "劳动者享有平等就业和选择职业的权利、取得劳动报酬的权利、休息休假的权利、获得劳动安全卫生保护的权利、接受职业技能培训的权利、享受社会保险和福利的权利、提请劳动争议处理的权利以及法律规定的其他劳动权利。", "chapter": "总则", "section": "第一章 总则"},
        {"law_id": "labor_16", "title": "第十六条", "content": "劳动合同是劳动者与用人单位确立劳动关系、明确双方权利和义务的协议。建立劳动关系应当订立劳动合同。", "chapter": "劳动合同", "section": "第三章 劳动合同和集体合同"},
        {"law_id": "labor_17", "title": "第十七条", "content": "订立和变更劳动合同，应当遵循平等自愿、协商一致的原则，不得违反法律、行政法规的规定。劳动合同依法订立即具有法律约束力，当事人必须履行劳动合同规定的义务。", "chapter": "劳动合同", "section": "第三章 劳动合同和集体合同"},
        {"law_id": "labor_19", "title": "第十九条", "content": "劳动合同应当以书面形式订立，并具备以下条款：（一）劳动合同期限；（二）工作内容；（三）劳动保护和劳动条件；（四）劳动报酬；（五）劳动纪律；（六）劳动合同终止的条件；（七）违反劳动合同的责任。劳动合同除前款规定的必备条款外，当事人可以协商约定其他内容。", "chapter": "劳动合同", "section": "第三章 劳动合同和集体合同"},
        {"law_id": "labor_26", "title": "第二十六条", "content": "下列劳动合同无效或者部分无效：（一）以欺诈、胁迫的手段或者乘人之危，使对方在违背真实意思的情况下订立或者变更劳动合同的；（二）用人单位免除自己的法定责任、排除劳动者权利的；（三）违反法律、行政法规强制性规定的。对劳动合同的无效或者部分无效有争议的，由劳动争议仲裁机构或者人民法院确认。", "chapter": "劳动合同", "section": "第三章 劳动合同和集体合同"},
        {"law_id": "labor_36", "title": "第三十六条", "content": "国家实行劳动者每日工作时间不超过八小时、平均每周工作时间不超过四十四小时的工时制度。", "chapter": "工作时间和休息休假", "section": "第四章 工作时间和休息休假"},
        {"law_id": "labor_44", "title": "第四十四条", "content": "有下列情形之一的，用人单位应当按照下列标准支付高于劳动者正常工作时间工资的工资报酬：（一）安排劳动者延长工作时间的，支付不低于工资的百分之一百五十的工资报酬；（二）休息日安排劳动者工作又不能安排补休的，支付不低于工资的百分之二百的工资报酬；（三）法定休假日安排劳动者工作的，支付不低于工资的百分之三百的工资报酬。", "chapter": "工作时间和休息休假", "section": "第四章 工作时间和休息休假"},
        {"law_id": "labor_46", "title": "第四十六条", "content": "工资分配应当遵循按劳分配原则，实行同工同酬。工资水平在经济发展的基础上逐步提高。国家对工资总量实行宏观调控。", "chapter": "工资", "section": "第五章 工资"},
        {"law_id": "labor_50", "title": "第五十条", "content": "工资应当以货币形式按月支付给劳动者本人。不得克扣或者无故拖欠劳动者的工资。", "chapter": "工资", "section": "第五章 工资"},
        {"law_id": "labor_77", "title": "第七十七条", "content": "用人单位与劳动者发生劳动争议，当事人可以依法申请调解、仲裁、提起诉讼，也可以协商解决。调解原则适用于仲裁和诉讼程序。", "chapter": "劳动争议", "section": "第十章 劳动争议"},
        {"law_id": "labor_79", "title": "第七十九条", "content": "劳动争议发生后，当事人可以向本单位劳动争议调解委员会申请调解；调解不成，当事人一方要求仲裁的，可以向劳动争议仲裁委员会申请仲裁。当事人一方也可以直接向劳动争议仲裁委员会申请仲裁。对仲裁裁决不服的，可以向人民法院提起诉讼。", "chapter": "劳动争议", "section": "第十章 劳动争议"},
    ],
    "company": [
        {"law_id": "company_1", "title": "第一条", "content": "为了规范公司的组织和行为，保护公司、股东和债权人的合法权益，维护社会经济秩序，促进社会主义市场经济的发展，制定本法。", "chapter": "总则", "section": "第一章 总则"},
        {"law_id": "company_3", "title": "第三条", "content": "公司是企业法人，有独立的法人财产，享有法人财产权。公司以其全部财产对公司的债务承担责任。有限责任公司的股东以其认缴的出资额为限对公司承担责任；股份有限公司的股东以其认购的股份为限对公司承担责任。", "chapter": "总则", "section": "第一章 总则"},
        {"law_id": "company_4", "title": "第四条", "content": "公司股东依法享有资产收益、参与重大决策和选择管理者等权利。", "chapter": "总则", "section": "第一章 总则"},
        {"law_id": "company_14", "title": "第十四条", "content": "公司可以设立分公司。设立分公司，应当向公司登记机关申请登记，领取营业执照。分公司不具有法人资格，其民事责任由公司承担。公司可以设立子公司，子公司具有法人资格，依法独立承担民事责任。", "chapter": "总则", "section": "第一章 总则"},
        {"law_id": "company_16", "title": "第十六条", "content": "公司应当为工会提供必要的活动条件。公司工会代表职工就职工的劳动报酬、工作时间、福利、保险和劳动安全卫生等事项依法与公司签订集体合同。公司依照宪法和有关法律的规定，通过职工代表大会或者其他形式，实行民主管理。", "chapter": "总则", "section": "第一章 总则"},
        {"law_id": "company_20", "title": "第二十条", "content": "公司股东应当遵守法律、行政法规和公司章程，依法行使股东权利，不得滥用股东权利损害公司或者其他股东的利益；不得滥用公司法人独立地位和股东有限责任损害公司债权人的利益。公司股东滥用股东权利给公司或者其他股东造成损失的，应当依法承担赔偿责任。公司股东滥用公司法人独立地位和股东有限责任，逃避债务，严重损害公司债权人利益的，应当对公司债务承担连带责任。", "chapter": "总则", "section": "第一章 总则"},
        {"law_id": "company_21", "title": "第二十一条", "content": "公司的控股股东、实际控制人、董事、监事、高级管理人员不得利用其关联关系损害公司利益。违反前款规定，给公司造成损失的，应当承担赔偿责任。", "chapter": "总则", "section": "第一章 总则"},
        {"law_id": "company_36", "title": "第三十六条", "content": "有限责任公司股东会由全体股东组成。股东会是公司的权力机构，依照本法行使职权。", "chapter": "有限责任公司的设立和组织机构", "section": "第二章 有限责任公司的设立和组织机构"},
        {"law_id": "company_37", "title": "第三十七条", "content": "股东会行使下列职权：（一）决定公司的经营方针和投资计划；（二）选举和更换非由职工代表担任的董事、监事，决定有关董事、监事的报酬事项；（三）审议批准董事会的报告；（四）审议批准监事会或者监事的报告；（五）审议批准公司的年度财务预算方案、决算方案；（六）审议批准公司的利润分配方案和弥补亏损方案；（七）对公司增加或者减少注册资本作出决议；（八）对发行公司债券作出决议；（九）对公司合并、分立、解散、清算或者变更公司形式作出决议；（十）修改公司章程；（十一）公司章程规定的其他职权。", "chapter": "有限责任公司的设立和组织机构", "section": "第二章 有限责任公司的设立和组织机构"},
        {"law_id": "company_71", "title": "第七十一条", "content": "有限责任公司的股东之间可以相互转让其全部或者部分股权。股东向股东以外的人转让股权，应当经其他股东过半数同意。股东应就其股权转让事项书面通知其他股东征求同意，其他股东自接到书面通知之日起满三十日未答复的，视为同意转让。其他股东半数以上不同意转让的，不同意的股东应当购买该转让的股权；不购买的，视为同意转让。经股东同意转让的股权，在同等条件下，其他股东有优先购买权。两个以上股东主张行使优先购买权的，协商确定各自的购买比例；协商不成的，按照转让时各自的出资比例行使优先购买权。", "chapter": "有限责任公司的股权转让", "section": "第三章 有限责任公司的股权转让"},
    ],
}


# ========== 进度追踪数据结构 ==========

@dataclass
class CollectionProgress:
    """采集任务进度追踪数据结构"""
    task_id: str
    status: str  # idle/running/completed/failed/cancelled
    total: int
    completed: int
    current_step: str  # "下载法条数据"/"解析法条"/"生成向量"/"写入ChromaDB"/"构建BM25索引"
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    selected_categories: list[str] = field(default_factory=list)


# ========== 数据采集引擎 ==========

class DataCollector:
    """
    数据采集引擎

    负责从内嵌法条数据或外部数据源获取法条，
    解析后生成向量并存入 ChromaDB，同时构建 BM25 索引。
    支持后台异步运行和实时进度追踪。
    """

    def __init__(self) -> None:
        """
        初始化数据采集引擎

        创建 ChromaDB 客户端，初始化进度追踪对象，
        准备 laws_child 和 laws_parent 两个 collection。
        """
        self.chroma_client = get_chroma_client()
        # 获取或创建 laws_parent 和 laws_child 两个 collection
        self.laws_parent = self.chroma_client.get_or_create_collection(
            name="laws_parent",
            metadata={"description": "法条父文档（完整法条）"},
        )
        self.laws_child = self.chroma_client.get_or_create_collection(
            name="laws_child",
            metadata={"description": "法条子文档（每款一段）"},
        )
        # BM25 索引数据
        self.bm25_corpus: list[str] = []
        self.bm25_metadata: list[dict] = []
        self.bm25_model: Optional[BM25Okapi] = None
        # 进度追踪（单例，同一时间只能运行一个采集任务）
        self.progress = CollectionProgress(
            task_id="",
            status="idle",
            total=0,
            completed=0,
            current_step="",
        )
        # 取消标志
        self._cancel_flag = False
        logger.info("数据采集引擎初始化完成")

    def _tokenize_chinese(self, text: str) -> list[str]:
        """
        中文文本分词（简易字符级分词）

        对中文文本按字符切分，同时保留英文单词的完整性。
        生产环境建议替换为 jieba 等专业分词工具。

        Args:
            text: 待分词的文本

        Returns:
            list[str]: 分词结果列表
        """
        tokens = []
        current_word = ""
        for char in text:
            if "\u4e00" <= char <= "\u9fff":
                if current_word:
                    tokens.append(current_word.lower())
                    current_word = ""
                tokens.append(char)
            elif char.isalnum():
                current_word += char
            else:
                if current_word:
                    tokens.append(current_word.lower())
                    current_word = ""
        if current_word:
            tokens.append(current_word.lower())
        return tokens

    def _split_into_paragraphs(self, content: str) -> list[str]:
        """
        将法条正文按款拆分为子段落

        根据中文分号或句号分隔法条各款，
        每款作为一个 child 文档。

        Args:
            content: 法条正文

        Returns:
            list[str]: 拆分后的子段落列表
        """
        # 按中文分号拆分各款
        paragraphs = content.split("；")
        # 过滤空段落并去除首尾空白
        result = [p.strip() for p in paragraphs if p.strip()]
        # 如果只有一段，尝试按句号拆分（适用于较长的单款法条）
        if len(result) == 1 and len(result[0]) > 200:
            sentences = result[0].split("。")
            result = [s.strip() + "。" for s in sentences if s.strip()]
        return result if result else [content]

    def _get_law_full_name(self, category: str) -> str:
        """
        根据法律类型获取完整法律名称

        Args:
            category: 法律类型标识

        Returns:
            str: 完整法律名称
        """
        names = {
            "civil": "中华人民共和国民法典",
            "labor": "中华人民共和国劳动法",
            "company": "中华人民共和国公司法",
            "construction": "中华人民共和国建筑法",
            "finance": "中华人民共和国金融法规",
            "criminal": "中华人民共和国刑法",
        }
        return names.get(category, LAW_CATEGORIES.get(category, {}).get("name", category))

    async def _fetch_law_data(self, category: str, limit: int = 0) -> list[dict]:
        """
        获取法条数据

        优先从内嵌数据获取，后续可扩展从外部URL下载。
        MVP阶段使用内嵌法条数据。

        Args:
            category: 法律类型标识
            limit: 限制获取条数，0表示不限制

        Returns:
            list[dict]: 法条数据列表
        """
        self.progress.current_step = "下载法条数据"

        # 优先使用内嵌数据
        if category in EMBEDDED_LAWS:
            data = EMBEDDED_LAWS[category]
            if limit > 0:
                data = data[:limit]
            logger.info("从内嵌数据获取 %s 法条 %d 条", category, len(data))
            return data

        # TODO: 后续可扩展从外部URL下载
        # url = os.environ.get(f"DATA_SOURCE_URL_{category.upper()}", "")
        # if url:
        #     async with httpx.AsyncClient() as client:
        #         response = await client.get(url)
        #         return response.json()

        logger.warning("法律类型 %s 暂无可用数据源", category)
        return []

    def _parse_law_items(self, raw_data: list[dict], category: str) -> tuple[list[dict], list[dict]]:
        """
        解析法条数据，拆分为 parent 和 child 文档

        每条法条生成一个 parent（完整法条）和若干 child（每款一段），
        child 通过 parent_id 关联到 parent。

        Args:
            raw_data: 原始法条数据列表
            category: 法律类型标识

        Returns:
            tuple[list[dict], list[dict]]: (parent文档列表, child文档列表)
        """
        self.progress.current_step = "解析法条"
        law_name = self._get_law_full_name(category)

        parents = []
        children = []

        for item in raw_data:
            law_id = item.get("law_id", f"{category}_{uuid.uuid4().hex[:8]}")
            title = item.get("title", "")
            content = item.get("content", "")
            chapter = item.get("chapter", "")
            section = item.get("section", "")

            # 构建 parent 文档
            parent_text = f"{law_name} {title}\n{content}"
            parent_meta = {
                "law_id": law_id,
                "law_name": law_name,
                "title": title,
                "chapter": chapter,
                "section": section,
                "category": category,
                "type": "parent",
            }
            parents.append({
                "id": f"parent_{law_id}",
                "text": parent_text,
                "metadata": parent_meta,
            })

            # 拆分为 child 文档（每款一段）
            paragraphs = self._split_into_paragraphs(content)
            for para_idx, para in enumerate(paragraphs):
                child_text = f"{law_name} {title} 第{para_idx + 1}款\n{para}"
                child_meta = {
                    "law_id": law_id,
                    "parent_id": f"parent_{law_id}",
                    "law_name": law_name,
                    "title": title,
                    "paragraph_index": para_idx + 1,
                    "chapter": chapter,
                    "section": section,
                    "category": category,
                    "type": "child",
                }
                children.append({
                    "id": f"child_{law_id}_{para_idx + 1}",
                    "text": child_text,
                    "metadata": child_meta,
                })

        logger.info(
            "解析法条完成，类别: %s，parent: %d，child: %d",
            category, len(parents), len(children),
        )
        return parents, children

    async def _generate_embeddings_batch(
        self, texts: list[str], batch_size: int = 0
    ) -> list[Optional[list[float]]]:
        """
        批量生成向量，支持分批和限流重试

        将文本按批次调用 Embedding API，
        遇到限流时自动重试，最多重试 EMBEDDING_RETRY_MAX 次。

        Args:
            texts: 待向量化的文本列表
            batch_size: 每批大小，0使用配置默认值

        Returns:
            list[Optional[list[float]]]: 向量列表，失败的项为 None
        """
        self.progress.current_step = "生成向量"
        if batch_size <= 0:
            batch_size = settings.DATA_BATCH_SIZE

        embedding_service = get_embedding_service()
        all_embeddings: list[Optional[list[float]]] = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            # 检查取消标志
            if self._cancel_flag:
                logger.info("采集任务已被取消，停止生成向量")
                return all_embeddings

            start = batch_idx * batch_size
            end = min(start + batch_size, len(texts))
            batch_texts = texts[start:end]

            # 限流重试
            retry_count = 0
            embeddings = None
            while retry_count < settings.EMBEDDING_RETRY_MAX:
                try:
                    embeddings = await embedding_service.get_embeddings(batch_texts)
                    if embeddings is not None:
                        break
                except Exception as e:
                    retry_count += 1
                    logger.warning(
                        "Embedding 批次 %d/%d 第 %d 次重试: %s",
                        batch_idx + 1, total_batches, retry_count, str(e),
                    )
                    await asyncio.sleep(2 ** retry_count)  # 指数退避

            if embeddings is not None:
                all_embeddings.extend(embeddings)
            else:
                # 该批次全部失败，填充 None
                all_embeddings.extend([None] * len(batch_texts))
                error_msg = f"Embedding 批次 {batch_idx + 1}/{total_batches} 生成失败"
                self.progress.errors.append(error_msg)
                logger.error(error_msg)

            # 更新进度
            self.progress.completed = min(
                self.progress.completed + len(batch_texts),
                self.progress.total,
            )
            logger.debug(
                "Embedding 进度: %d/%d (批次 %d/%d)",
                self.progress.completed, self.progress.total,
                batch_idx + 1, total_batches,
            )

        return all_embeddings

    async def _write_to_chromadb(
        self,
        documents: list[dict],
        collection_name: str,
    ) -> int:
        """
        将文档写入 ChromaDB

        将带有向量的文档写入指定的 ChromaDB collection，
        跳过向量为 None 的文档。

        Args:
            documents: 文档列表，每项包含 id、text、metadata、embedding
            collection_name: 目标 collection 名称（laws_parent 或 laws_child）

        Returns:
            int: 成功写入的文档数量
        """
        self.progress.current_step = "写入ChromaDB"
        collection = self.chroma_client.get_or_create_collection(name=collection_name)

        # 过滤掉 embedding 为 None 的文档
        valid_docs = [doc for doc in documents if doc.get("embedding") is not None]
        if not valid_docs:
            logger.warning("没有有效的文档可写入 %s", collection_name)
            return 0

        ids = [doc["id"] for doc in valid_docs]
        texts = [doc["text"] for doc in valid_docs]
        embeddings = [doc["embedding"] for doc in valid_docs]
        metadatas = [doc["metadata"] for doc in valid_docs]

        try:
            collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info("成功写入 %s %d 条文档", collection_name, len(valid_docs))
            return len(valid_docs)
        except Exception as e:
            error_msg = f"写入 {collection_name} 失败: {str(e)}"
            self.progress.errors.append(error_msg)
            logger.error(error_msg)
            return 0

    def _build_bm25_index(self, all_child_texts: list[str], all_child_metadata: list[dict]) -> None:
        """
        构建 BM25 索引

        将所有 child 文档加入 BM25 语料库并构建索引，
        索引保存到本地文件以便后续加载。

        Args:
            all_child_texts: 所有 child 文档文本列表
            all_child_metadata: 所有 child 文档元数据列表
        """
        self.progress.current_step = "构建BM25索引"

        # 合并已有语料
        self.bm25_corpus.extend(all_child_texts)
        self.bm25_metadata.extend(all_child_metadata)

        # 分词并构建 BM25 模型
        tokenized_corpus = [self._tokenize_chinese(text) for text in self.bm25_corpus]
        self.bm25_model = BM25Okapi(tokenized_corpus)

        # 保存索引到本地文件
        try:
            import pickle
            index_dir = Path(settings.CHROMA_PERSIST_DIR) / "bm25_index"
            index_dir.mkdir(parents=True, exist_ok=True)
            index_path = index_dir / "bm25_data.pkl"
            with open(index_path, "wb") as f:
                pickle.dump({
                    "corpus": self.bm25_corpus,
                    "metadata": self.bm25_metadata,
                }, f)
            logger.info("BM25 索引构建完成并保存，语料数: %d", len(self.bm25_corpus))
        except Exception as e:
            logger.warning("BM25 索引保存失败: %s", str(e))

    def load_bm25_index(self) -> bool:
        """
        从本地文件加载 BM25 索引

        Returns:
            bool: 是否成功加载
        """
        try:
            import pickle
            index_path = Path(settings.CHROMA_PERSIST_DIR) / "bm25_index" / "bm25_data.pkl"
            if not index_path.exists():
                logger.info("BM25 索引文件不存在，跳过加载")
                return False

            with open(index_path, "rb") as f:
                data = pickle.load(f)
            self.bm25_corpus = data.get("corpus", [])
            self.bm25_metadata = data.get("metadata", [])

            if self.bm25_corpus:
                tokenized_corpus = [self._tokenize_chinese(text) for text in self.bm25_corpus]
                self.bm25_model = BM25Okapi(tokenized_corpus)
                logger.info("BM25 索引加载完成，语料数: %d", len(self.bm25_corpus))
                return True
            return False
        except Exception as e:
            logger.warning("BM25 索引加载失败: %s", str(e))
            return False

    async def collect(
        self,
        categories: list[str],
        limit: int = 0,
    ) -> None:
        """
        执行数据采集任务

        完整流程：获取数据 -> 解析 -> 生成向量 -> 写入 ChromaDB -> 构建 BM25 索引。
        同一时间只能运行一个采集任务。

        Args:
            categories: 要采集的法律类型列表
            limit: 每类法条限制条数，0表示不限制
        """
        # 生成任务ID
        task_id = uuid.uuid4().hex[:12]
        self.progress = CollectionProgress(
            task_id=task_id,
            status="running",
            total=0,
            completed=0,
            current_step="初始化",
            started_at=datetime.now().isoformat(),
            selected_categories=categories,
        )
        self._cancel_flag = False

        logger.info("数据采集任务 %s 启动，类别: %s", task_id, categories)

        try:
            # ---- 第1步：获取法条数据 ----
            all_raw_data = []
            for category in categories:
                if self._cancel_flag:
                    break
                raw_data = await self._fetch_law_data(category, limit)
                all_raw_data.extend(raw_data)

            if not all_raw_data:
                self.progress.status = "failed"
                self.progress.errors.append("未获取到任何法条数据")
                self.progress.completed_at = datetime.now().isoformat()
                logger.error("数据采集任务 %s 失败：未获取到数据", task_id)
                return

            # ---- 第2步：解析法条 ----
            all_parents = []
            all_children = []
            for category in categories:
                if self._cancel_flag:
                    break
                category_data = [d for d in all_raw_data if d.get("law_id", "").startswith(category)]
                if not category_data:
                    continue
                parents, children = self._parse_law_items(category_data, category)
                all_parents.extend(parents)
                all_children.extend(children)

            # 计算总条数（parent + child 的向量生成数量）
            total_items = len(all_parents) + len(all_children)
            self.progress.total = total_items
            self.progress.completed = 0
            logger.info("解析完成，parent: %d, child: %d, 总计: %d", len(all_parents), len(all_children), total_items)

            # ---- 第3步：生成向量 ----
            # 为 parent 生成向量
            parent_texts = [p["text"] for p in all_parents]
            parent_embeddings = await self._generate_embeddings_batch(parent_texts)

            if self._cancel_flag:
                self.progress.status = "cancelled"
                self.progress.completed_at = datetime.now().isoformat()
                return

            # 为 child 生成向量
            child_texts = [c["text"] for c in all_children]
            child_embeddings = await self._generate_embeddings_batch(child_texts)

            if self._cancel_flag:
                self.progress.status = "cancelled"
                self.progress.completed_at = datetime.now().isoformat()
                return

            # ---- 第4步：写入 ChromaDB ----
            # 组装 parent 文档（含向量）
            parent_docs = []
            for idx, parent in enumerate(all_parents):
                parent_docs.append({
                    "id": parent["id"],
                    "text": parent["text"],
                    "metadata": parent["metadata"],
                    "embedding": parent_embeddings[idx] if idx < len(parent_embeddings) else None,
                })

            # 组装 child 文档（含向量）
            child_docs = []
            for idx, child in enumerate(all_children):
                child_docs.append({
                    "id": child["id"],
                    "text": child["text"],
                    "metadata": child["metadata"],
                    "embedding": child_embeddings[idx] if idx < len(child_embeddings) else None,
                })

            parent_count = await self._write_to_chromadb(parent_docs, "laws_parent")
            child_count = await self._write_to_chromadb(child_docs, "laws_child")

            # ---- 第5步：构建 BM25 索引 ----
            all_child_texts = [c["text"] for c in all_children]
            all_child_metadata = [c["metadata"] for c in all_children]
            self._build_bm25_index(all_child_texts, all_child_metadata)

            # 完成
            self.progress.status = "completed"
            self.progress.completed = self.progress.total
            self.progress.current_step = "完成"
            self.progress.completed_at = datetime.now().isoformat()
            logger.info(
                "数据采集任务 %s 完成，parent: %d, child: %d",
                task_id, parent_count, child_count,
            )

        except Exception as e:
            self.progress.status = "failed"
            self.progress.errors.append(f"采集任务异常: {str(e)}")
            self.progress.completed_at = datetime.now().isoformat()
            logger.error("数据采集任务 %s 异常: %s", task_id, str(e), exc_info=True)

    def cancel(self) -> bool:
        """
        取消正在运行的采集任务

        设置取消标志，采集循环会在下一个检查点停止。

        Returns:
            bool: 是否成功设置取消标志
        """
        if self.progress.status != "running":
            return False
        self._cancel_flag = True
        self.progress.status = "cancelled"
        self.progress.completed_at = datetime.now().isoformat()
        logger.info("数据采集任务 %s 已请求取消", self.progress.task_id)
        return True

    def get_progress(self) -> dict:
        """
        获取当前采集进度

        Returns:
            dict: 进度信息字典
        """
        return asdict(self.progress)

    def get_status(self) -> dict:
        """
        获取 ChromaDB 当前数据状态

        Returns:
            dict: 包含各 collection 文档数量和最后更新时间
        """
        try:
            laws_count = self.laws_parent.count() + self.laws_child.count()
            collections = []
            for name in ["laws_parent", "laws_child"]:
                try:
                    col = self.chroma_client.get_collection(name=name)
                    collections.append(name)
                except Exception:
                    pass

            # 获取最后更新时间
            import os
            chroma_dir = Path(settings.CHROMA_PERSIST_DIR)
            last_updated = ""
            if chroma_dir.exists():
                # 查找目录下最新修改的文件
                all_files = list(chroma_dir.rglob("*"))
                if all_files:
                    latest_file = max(all_files, key=lambda f: f.stat().st_mtime if f.is_file() else 0)
                    if latest_file.is_file():
                        mtime = latest_file.stat().st_mtime
                        last_updated = datetime.fromtimestamp(mtime).isoformat()

            return {
                "laws_count": laws_count,
                "cases_count": 0,
                "collections": collections,
                "last_updated": last_updated,
            }
        except Exception as e:
            logger.error("获取数据状态失败: %s", str(e))
            return {
                "laws_count": 0,
                "cases_count": 0,
                "collections": [],
                "last_updated": "",
            }


# ========== 全局数据采集引擎单例 ==========

_data_collector: Optional[DataCollector] = None


def get_data_collector() -> DataCollector:
    """
    获取数据采集引擎单例

    Returns:
        DataCollector: 数据采集引擎实例
    """
    global _data_collector
    if _data_collector is None:
        _data_collector = DataCollector()
        # 尝试加载已有的 BM25 索引
        _data_collector.load_bm25_index()
    return _data_collector
