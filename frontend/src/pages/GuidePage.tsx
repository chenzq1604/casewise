/**
 * 法律指引页
 * 场景化法律指引，包含5大场景卡片
 * 点击卡片弹出Modal展示详细指引内容
 * 包含维权步骤、法律依据、证据清单、常见问题等模块
 */
import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Button,
  Modal,
  Steps,
  Collapse,
  Checkbox,
  Tag,
  Divider,
  Space,
} from 'antd';
import {
  TeamOutlined,
  ShoppingOutlined,
  HeartOutlined,
  HomeOutlined,
  DollarOutlined,
  RobotOutlined,
  BookOutlined,
  FileProtectOutlined,
  QuestionCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;

/**
 * 场景数据类型定义
 */
interface SceneData {
  /** 场景唯一标识 */
  key: string;
  /** 场景图标 */
  icon: React.ReactNode;
  /** 场景名称 */
  title: string;
  /** 场景简短描述 */
  description: string;
  /** 主题色 */
  color: string;
  /** 场景概述 */
  overview: string;
  /** 维权步骤列表 */
  steps: { title: string; description: string }[];
  /** 证据清单 */
  evidence: string[];
  /** 法律依据列表 */
  legalBasis: { law: string; article: string; description: string }[];
  /** 常见问题FAQ */
  faq: { question: string; answer: string }[];
  /** 咨询AI助手的预填问题 */
  aiQuestion: string;
}

/**
 * 5大场景硬编码数据
 */
const SCENES: SceneData[] = [
  {
    key: 'labor',
    icon: <TeamOutlined />,
    title: '劳动纠纷维权',
    description: '劳动合同、欠薪追讨、违法解除赔偿等劳动争议维权指引',
    color: '#1890ff',
    overview:
      '劳动纠纷是劳动者与用人单位之间因劳动权利和义务发生争议的情形。常见类型包括：拖欠工资、违法解除劳动合同、未签订书面劳动合同、工伤赔偿等。劳动者可通过协商、调解、仲裁、诉讼等途径维护自身合法权益。',
    steps: [
      { title: '收集证据', description: '整理劳动合同、工资流水、考勤记录等关键证据材料' },
      { title: '协商沟通', description: '与用人单位进行沟通协商，争取和解解决' },
      { title: '劳动仲裁', description: '向劳动争议仲裁委员会申请仲裁，仲裁为诉讼前置程序' },
      { title: '法院诉讼', description: '对仲裁结果不服的，可在收到裁决书15日内向法院起诉' },
    ],
    evidence: ['劳动合同', '工资流水', '考勤记录', '辞退通知书', '社保缴纳记录'],
    legalBasis: [
      { law: '劳动合同法', article: '第47条', description: '经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付' },
      { law: '劳动合同法', article: '第87条', description: '用人单位违反本法规定解除或者终止劳动合同的，应当依照本法第47条规定的经济补偿标准的二倍向劳动者支付赔偿金' },
      { law: '劳动合同法', article: '第82条', description: '用人单位自用工之日起超过一个月不满一年未与劳动者订立书面劳动合同的，应当向劳动者每月支付二倍的工资' },
    ],
    faq: [
      {
        question: '试用期被辞退有赔偿吗？',
        answer: '试用期被辞退是否有赔偿取决于辞退原因。如果用人单位能证明劳动者不符合录用条件，可以合法解除且无需支付经济补偿；但如果用人单位无法证明或属于违法解除，劳动者有权要求继续履行合同或支付赔偿金（经济补偿的二倍）。',
      },
      {
        question: '欠薪怎么追讨？',
        answer: '追讨欠薪的途径包括：1）与用人单位协商；2）向劳动监察部门投诉举报；3）申请劳动仲裁；4）对仲裁结果不服可向法院起诉。劳动仲裁是追讨欠薪的主要途径，仲裁时效为一年。注意保留工资条、银行流水等证据。',
      },
      {
        question: '没签劳动合同怎么办？',
        answer: '根据《劳动合同法》第82条，用人单位自用工之日起超过一个月不满一年未与劳动者订立书面劳动合同的，应当向劳动者每月支付二倍的工资。超过一年未签的，视为已订立无固定期限劳动合同。劳动者需收集工作证、工资记录等证明劳动关系的证据。',
      },
    ],
    aiQuestion: '我遇到了劳动纠纷，请问应该如何维权？',
  },
  {
    key: 'consumer',
    icon: <ShoppingOutlined />,
    title: '消费者维权',
    description: '网购假货、预付卡退款、商品质量等消费者权益保护指引',
    color: '#fa8c16',
    overview:
      '消费者维权是指消费者在购买、使用商品或接受服务时，其合法权益受到侵害后依法寻求救济的过程。常见情形包括：商品质量缺陷、虚假宣传、价格欺诈、售后服务不到位等。消费者可通过协商、投诉、诉讼等方式维护自身权益。',
    steps: [
      { title: '保存证据', description: '保留购物凭证、商品照片、聊天记录等证据' },
      { title: '与商家协商', description: '联系商家沟通退换货或赔偿事宜' },
      { title: '平台投诉', description: '通过电商平台投诉渠道发起维权' },
      { title: '12315投诉', description: '向消费者协会或市场监管部门投诉举报' },
      { title: '提起诉讼', description: '向人民法院提起民事诉讼，维护合法权益' },
    ],
    evidence: ['购物凭证', '商品照片', '聊天记录', '宣传页面截图', '物流记录'],
    legalBasis: [
      { law: '消费者权益保护法', article: '第55条', description: '经营者提供商品或者服务有欺诈行为的，应当按照消费者的要求增加赔偿其受到的损失，增加赔偿的金额为消费者购买商品的价款或者接受服务的费用的三倍' },
      { law: '消费者权益保护法', article: '第24条', description: '经营者提供的商品或者服务不符合质量要求的，消费者可以依照国家规定、当事人约定退货，或者要求经营者履行更换、修理等义务' },
    ],
    faq: [
      {
        question: '网购假货怎么索赔？',
        answer: '根据《消费者权益保护法》第55条，网购到假货属于欺诈行为，消费者可要求"退一赔三"，即退还购物款项并增加赔偿三倍价款。赔偿金额不足500元的，为500元。建议先保存商品照片、购买记录等证据，与商家协商，协商不成可向平台投诉或拨打12315。',
      },
      {
        question: '预付卡退款怎么维权？',
        answer: '商家停业或拒绝退还预付卡余额的，消费者可：1）与商家协商退款；2）向消费者协会投诉；3）向市场监管部门举报；4）向法院起诉。根据《消费者权益保护法》第53条，经营者以预收款方式提供商品或服务的，应当按照约定提供，未按照约定提供的，应当按照消费者的要求履行约定或者退回预付款。',
      },
      {
        question: '美容院充值能退吗？',
        answer: '美容院充值属于预付消费，消费者有权要求退还未消费的余额。如果美容院存在虚假宣传、强制消费等行为，消费者还可主张赔偿。建议先与美容院协商，协商不成可向12315投诉或向法院起诉。注意保留充值凭证、消费记录等证据。',
      },
    ],
    aiQuestion: '我购买到了假货/劣质商品，请问如何维权？',
  },
  {
    key: 'marriage',
    icon: <HeartOutlined />,
    title: '婚姻家庭纠纷',
    description: '离婚财产分割、抚养权争议、家暴取证等婚姻家庭法律指引',
    color: '#eb2f96',
    overview:
      '婚姻家庭纠纷涉及离婚、财产分割、子女抚养、家庭暴力等问题。处理婚姻家庭纠纷应优先考虑调解，保护未成年人及无过错方权益。离婚方式包括协议离婚和诉讼离婚，涉及财产分割和子女抚养的需依法处理。',
    steps: [
      { title: '咨询律师', description: '了解自身权益，评估纠纷处理方案' },
      { title: '调解协商', description: '通过调解或协商方式尝试解决纠纷' },
      { title: '协议离婚/诉讼离婚', description: '双方达成一致的协议离婚，否则向法院提起离婚诉讼' },
      { title: '财产分割/抚养权', description: '依法进行夫妻共同财产分割和子女抚养权判定' },
    ],
    evidence: ['结婚证', '财产证明', '收入证明', '家暴证据', '子女抚养情况'],
    legalBasis: [
      { law: '民法典', article: '第1076条', description: '夫妻双方自愿离婚的，应当签订书面离婚协议，并亲自到婚姻登记机关申请离婚登记' },
      { law: '民法典', article: '第1087条', description: '离婚时，夫妻的共同财产由双方协议处理；协议不成的，由人民法院根据财产的具体情况，按照照顾子女、女方和无过错方权益的原则判决' },
      { law: '民法典', article: '第1084条', description: '离婚后，不满两周岁的子女，以由母亲直接抚养为原则。已满两周岁的子女，父母双方对抚养问题协议不成的，由人民法院根据双方的具体情况，按照最有利于未成年子女的原则判决' },
    ],
    faq: [
      {
        question: '离婚财产怎么分？',
        answer: '离婚时夫妻共同财产原则上平均分割，但法院会根据照顾子女、女方和无过错方权益的原则进行判决。婚前个人财产归各自所有。注意：隐藏、转移夫妻共同财产的一方，可以少分或不分。建议提前收集财产线索和证据。',
      },
      {
        question: '抚养权怎么判？',
        answer: '根据《民法典》第1084条，不满2周岁的子女原则上由母亲抚养；已满2周岁的子女，由法院根据最有利于未成年子女的原则判决；已满8周岁的子女，应尊重其真实意愿。法院综合考虑双方的经济条件、生活环境、教育能力等因素。',
      },
      {
        question: '家暴怎么取证？',
        answer: '家暴取证方式包括：1）及时报警，获取报警记录和告诫书；2）到医院就诊，保留伤情诊断证明和照片；3）保存威胁短信、聊天记录等电子证据；4）申请居委会、村委会出具证明；5）有目击证人的可请证人作证；6）可向法院申请人生安全保护令。',
      },
    ],
    aiQuestion: '我遇到了婚姻家庭纠纷，请问应该如何处理？',
  },
  {
    key: 'property',
    icon: <HomeOutlined />,
    title: '房产/物业纠纷',
    description: '租房押金、二手房违约、物业侵权等房产物业纠纷指引',
    color: '#52c41a',
    overview:
      '房产物业纠纷涵盖房屋租赁、买卖合同、物业管理等方面的争议。常见问题包括：租房押金不退、二手房交易违约、物业服务不到位、房屋质量缺陷等。维权时应首先查阅合同条款，通过协商、投诉、仲裁或诉讼等方式解决。',
    steps: [
      { title: '查阅合同', description: '仔细阅读租赁或买卖合同条款，明确双方权利义务' },
      { title: '协商沟通', description: '与对方进行沟通协商，争取和解解决' },
      { title: '住建部门投诉', description: '向住建部门或房屋管理机构投诉举报' },
      { title: '仲裁/诉讼', description: '根据合同约定申请仲裁或向法院提起诉讼' },
    ],
    evidence: ['租赁/买卖合同', '付款凭证', '房屋照片', '物业沟通记录'],
    legalBasis: [
      { law: '民法典', article: '第714条', description: '承租人应当妥善保管租赁物，因保管不善造成租赁物毁损、灭失的，应当承担赔偿责任' },
      { law: '民法典', article: '第722条', description: '承租人无正当理由未支付或者迟延支付租金的，出租人可以请求承租人在合理期限内支付；承租人逾期不支付的，出租人可以解除合同' },
    ],
    faq: [
      {
        question: '租房押金不退怎么办？',
        answer: '房东不退押金的维权方式：1）查看租赁合同中关于押金退还的约定；2）与房东协商，保留沟通记录；3）向居委会或街道办申请调解；4）向住建部门投诉；5）向法院起诉。注意退房时做好房屋交接，拍照留存房屋状况证据。',
      },
      {
        question: '二手房违约怎么追责？',
        answer: '二手房交易中一方违约的，守约方可以：1）要求继续履行合同；2）要求支付违约金（按合同约定）；3）要求赔偿实际损失。如果违约金不足以弥补损失，可请求法院增加。建议在签订合同时明确违约责任条款，交易过程中保留全部书面证据。',
      },
      {
        question: '物业侵权怎么维权？',
        answer: '物业服务不到位的维权方式：1）与物业公司沟通协商；2）向业主委员会反映；3）向住建部门或房管局投诉；4）通过业主大会决定更换物业公司；5）向法院起诉。业主有权要求物业公司按照合同约定提供服务，服务质量不达标的可以拒交或减免物业费。',
      },
    ],
    aiQuestion: '我遇到了房产/物业纠纷，请问应该如何维权？',
  },
  {
    key: 'debt',
    icon: <DollarOutlined />,
    title: '债务追讨',
    description: '借条效力、诉讼时效、担保责任等债务追讨法律指引',
    color: '#722ed1',
    overview:
      '债务追讨是指债权人通过合法途径要求债务人履行还款义务的过程。常见情形包括：民间借贷纠纷、合同欠款追讨、担保责任追究等。追讨债务应注意诉讼时效，及时收集和保全证据，可通过协商、调解、支付令、诉讼等方式实现债权。',
    steps: [
      { title: '确认债权', description: '核实借条、合同等债权凭证的效力和金额' },
      { title: '催收函', description: '向债务人发送正式催收函，明确还款要求和期限' },
      { title: '调解', description: '通过人民调解委员会或法院诉前调解方式协商解决' },
      { title: '支付令', description: '向法院申请支付令，债务人异议的转入诉讼程序' },
      { title: '民事诉讼', description: '向法院提起民事诉讼，通过判决强制执行实现债权' },
    ],
    evidence: ['借条/合同', '转账记录', '聊天记录', '催收记录'],
    legalBasis: [
      { law: '民法典', article: '第667条', description: '借款合同是借款人向贷款人借款，到期返还借款并支付利息的合同' },
      { law: '民法典', article: '第676条', description: '借款人未按照约定的期限返还借款的，应当按照约定或者国家有关规定支付逾期利息' },
    ],
    faq: [
      {
        question: '没有借条能追债吗？',
        answer: '没有借条也可以追债，但需要其他证据证明借贷关系的存在，如：银行转账记录、微信/支付宝转账记录、聊天记录中对方承认借款的内容、通话录音、证人证言等。建议通过微信等方式与对方确认借款事实和金额，形成书面证据。',
      },
      {
        question: '诉讼时效多久？',
        answer: '根据《民法典》第188条，向人民法院请求保护民事权利的诉讼时效期间为三年，自权利人知道或者应当知道权利受到损害以及义务人之日起计算。诉讼时效可因催讨、起诉等行为中断并重新计算。建议在时效内及时主张权利。',
      },
      {
        question: '担保人要承担什么责任？',
        answer: '担保人分为一般保证和连带责任保证。一般保证的担保人在主合同纠纷未经审判或仲裁，并就债务人财产依法强制执行仍不能履行债务前，有权拒绝承担保证责任。连带责任保证的担保人，在债务人不履行债务时，债权人可以直接要求担保人承担保证责任。建议在签订担保合同时明确保证方式和范围。',
      },
    ],
    aiQuestion: '我需要追讨债务，请问有哪些合法途径？',
  },
];

/**
 * GuidePage 法律指引页组件
 * 展示5大场景卡片，点击后弹出详细指引Modal
 */
const GuidePage: React.FC = () => {
  const navigate = useNavigate();
  /** 当前展开的场景，null表示Modal关闭 */
  const [activeScene, setActiveScene] = useState<SceneData | null>(null);
  /** 证据清单勾选状态 */
  const [checkedEvidence, setCheckedEvidence] = useState<Record<string, string[]>>({});

  /**
   * 打开场景详情Modal
   * @param scene - 选中的场景数据
   */
  const handleOpenDetail = (scene: SceneData) => {
    setActiveScene(scene);
  };

  /**
   * 关闭场景详情Modal
   */
  const handleCloseDetail = () => {
    setActiveScene(null);
  };

  /**
   * 切换证据清单勾选状态
   * @param sceneKey - 场景标识
   * @param item - 证据项名称
   */
  const handleEvidenceChange = (sceneKey: string, item: string) => {
    setCheckedEvidence((prev) => {
      const current = prev[sceneKey] || [];
      const next = current.includes(item)
        ? current.filter((i) => i !== item)
        : [...current, item];
      return { ...prev, [sceneKey]: next };
    });
  };

  /**
   * 跳转到AI助手对话页并预填问题
   * @param question - 预填的问题内容
   */
  const handleConsultAI = (question: string) => {
    navigate('/chat', { state: { initialQuestion: question } });
  };

  /**
   * 渲染场景卡片
   * @param scene - 场景数据
   * @param index - 卡片索引
   */
  const renderSceneCard = (scene: SceneData) => (
    <Col xs={24} sm={12} lg={8} key={scene.key}>
      <Card
        hoverable
        style={{
          height: '100%',
          borderRadius: 12,
          overflow: 'hidden',
          border: `1px solid ${scene.color}20`,
        }}
        styles={{
          body: { padding: 24 },
        }}
      >
        {/* 图标与标题区域 */}
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: '50%',
              background: `${scene.color}15`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 12px',
            }}
          >
            {React.cloneElement(scene.icon as React.ReactElement, {
              style: { fontSize: 28, color: scene.color },
            })}
          </div>
          <Title level={4} style={{ margin: 0, color: scene.color }}>
            {scene.title}
          </Title>
        </div>

        {/* 场景描述 */}
        <Paragraph
          style={{
            color: '#595959',
            fontSize: 14,
            textAlign: 'center',
            marginBottom: 20,
            minHeight: 44,
          }}
        >
          {scene.description}
        </Paragraph>

        {/* 步骤预览标签 */}
        <div style={{ marginBottom: 16 }}>
          {scene.steps.map((step, i) => (
            <Tag
              key={i}
              color={scene.color}
              style={{ marginBottom: 4, fontSize: 12 }}
            >
              {i + 1}. {step.title}
            </Tag>
          ))}
        </div>

        {/* 查看指引按钮 */}
        <Button
          type="primary"
          block
          onClick={() => handleOpenDetail(scene)}
          style={{
            background: scene.color,
            borderColor: scene.color,
            borderRadius: 8,
            height: 40,
          }}
        >
          查看指引
        </Button>
      </Card>
    </Col>
  );

  /**
   * 渲染场景详情Modal内容
   * @param scene - 当前展开的场景数据
   */
  const renderModalContent = (scene: SceneData) => {
    const currentChecked = checkedEvidence[scene.key] || [];

    return (
      <div>
        {/* 场景概述 */}
        <div style={{ marginBottom: 24 }}>
          <Space style={{ marginBottom: 8 }}>
            <BookOutlined style={{ color: scene.color, fontSize: 18 }} />
            <Text strong style={{ fontSize: 16 }}>
              场景概述
            </Text>
          </Space>
          <Paragraph style={{ color: '#595959', lineHeight: 1.8, margin: 0 }}>
            {scene.overview}
          </Paragraph>
        </div>

        <Divider style={{ margin: '16px 0' }} />

        {/* 维权步骤 */}
        <div style={{ marginBottom: 24 }}>
          <Space style={{ marginBottom: 12 }}>
            <FileProtectOutlined style={{ color: scene.color, fontSize: 18 }} />
            <Text strong style={{ fontSize: 16 }}>
              维权步骤
            </Text>
          </Space>
          <Steps
            direction="vertical"
            size="small"
            current={-1}
            items={scene.steps.map((step, i) => ({
              title: (
                <Text strong>
                  步骤{i + 1}：{step.title}
                </Text>
              ),
              description: (
                <Text type="secondary" style={{ fontSize: 13 }}>
                  {step.description}
                </Text>
              ),
            }))}
          />
        </div>

        <Divider style={{ margin: '16px 0' }} />

        {/* 关键法律依据 */}
        <div style={{ marginBottom: 24 }}>
          <Space style={{ marginBottom: 12 }}>
            <CheckCircleOutlined style={{ color: scene.color, fontSize: 18 }} />
            <Text strong style={{ fontSize: 16 }}>
              关键法律依据
            </Text>
          </Space>
          <div>
            {scene.legalBasis.map((basis, i) => (
              <div
                key={i}
                style={{
                  background: '#fafafa',
                  borderRadius: 8,
                  padding: '12px 16px',
                  marginBottom: 8,
                  borderLeft: `3px solid ${scene.color}`,
                }}
              >
                <div style={{ marginBottom: 4 }}>
                  <Tag color={scene.color} style={{ marginRight: 8 }}>
                    {basis.article}
                  </Tag>
                  <Text strong>{basis.law}</Text>
                </div>
                <Paragraph
                  style={{
                    margin: 0,
                    color: '#595959',
                    fontSize: 13,
                    lineHeight: 1.6,
                  }}
                >
                  {basis.description}
                </Paragraph>
              </div>
            ))}
          </div>
        </div>

        <Divider style={{ margin: '16px 0' }} />

        {/* 证据清单 */}
        <div style={{ marginBottom: 24 }}>
          <Space style={{ marginBottom: 12 }}>
            <FileProtectOutlined style={{ color: scene.color, fontSize: 18 }} />
            <Text strong style={{ fontSize: 16 }}>
              证据清单
            </Text>
            <Tag color="default" style={{ marginLeft: 4 }}>
              已准备 {currentChecked.length}/{scene.evidence.length}
            </Tag>
          </Space>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
              gap: 8,
            }}
          >
            {scene.evidence.map((item) => (
              <Checkbox
                key={item}
                checked={currentChecked.includes(item)}
                onChange={() => handleEvidenceChange(scene.key, item)}
                style={{ fontSize: 14 }}
              >
                {item}
              </Checkbox>
            ))}
          </div>
        </div>

        <Divider style={{ margin: '16px 0' }} />

        {/* 常见问题FAQ */}
        <div style={{ marginBottom: 24 }}>
          <Space style={{ marginBottom: 12 }}>
            <QuestionCircleOutlined style={{ color: scene.color, fontSize: 18 }} />
            <Text strong style={{ fontSize: 16 }}>
              常见问题
            </Text>
          </Space>
          <Collapse
            accordion
            style={{ background: 'transparent' }}
            items={scene.faq.map((item, i) => ({
              key: String(i),
              label: (
                <Text strong style={{ fontSize: 14 }}>
                  {item.question}
                </Text>
              ),
              children: (
                <Paragraph
                  style={{
                    color: '#595959',
                    fontSize: 13,
                    lineHeight: 1.8,
                    margin: 0,
                  }}
                >
                  {item.answer}
                </Paragraph>
              ),
            }))}
          />
        </div>

        <Divider style={{ margin: '16px 0' }} />

        {/* 咨询AI助手按钮 */}
        <div style={{ textAlign: 'center' }}>
          <Button
            type="primary"
            size="large"
            icon={<RobotOutlined />}
            onClick={() => handleConsultAI(scene.aiQuestion)}
            style={{
              background: scene.color,
              borderColor: scene.color,
              borderRadius: 8,
              height: 48,
              paddingInline: 32,
              fontSize: 16,
            }}
          >
            咨询AI助手
          </Button>
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              跳转到法律问答页面，AI助手将为您解答相关问题
            </Text>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      {/* 页面标题区域 */}
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <Title level={2} style={{ color: '#262626', marginBottom: 8 }}>
          法律指引
        </Title>
        <Paragraph style={{ fontSize: 16, color: '#8c8c8c' }}>
          选择您遇到的法律场景，获取专业维权指引和法律依据
        </Paragraph>
      </div>

      {/* 场景卡片网格 */}
      <Row gutter={[24, 24]}>{SCENES.map((scene) => renderSceneCard(scene))}</Row>

      {/* 底部合规声明 */}
      <div
        style={{
          marginTop: 40,
          textAlign: 'center',
          padding: '16px 24px',
          background: '#fafafa',
          borderRadius: 8,
        }}
      >
        <Text type="secondary" style={{ fontSize: 12 }}>
          以上法律指引仅供参考，不构成法律意见。具体案件请咨询专业律师，以获取针对性的法律建议。
        </Text>
      </div>

      {/* 场景详情Modal */}
      <Modal
        title={null}
        open={!!activeScene}
        onCancel={handleCloseDetail}
        footer={null}
        width={720}
        style={{ top: 20 }}
        styles={{
          body: { maxHeight: 'calc(100vh - 120px)', overflowY: 'auto', padding: '24px 24px 16px' },
        }}
        destroyOnClose
      >
        {activeScene && (
          <>
            {/* Modal标题区域 */}
            <div
              style={{
                textAlign: 'center',
                marginBottom: 24,
                paddingBottom: 16,
                borderBottom: `2px solid ${activeScene.color}20`,
              }}
            >
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: '50%',
                  background: `${activeScene.color}15`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 12px',
                }}
              >
                {React.cloneElement(activeScene.icon as React.ReactElement, {
                  style: { fontSize: 24, color: activeScene.color },
                })}
              </div>
              <Title level={3} style={{ margin: 0, color: activeScene.color }}>
                {activeScene.title}
              </Title>
            </div>

            {/* Modal详细内容 */}
            {renderModalContent(activeScene)}
          </>
        )}
      </Modal>
    </div>
  );
};

export default GuidePage;
