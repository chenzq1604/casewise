/**
 * 费用计算页面
 * 提供诉讼费、劳动赔偿、律师费三个计算器
 * 所有计算纯前端完成，输入变化时实时计算
 */
import React, { useState, useMemo } from 'react';
import {
  Card,
  Tabs,
  Select,
  InputNumber,
  Statistic,
  Row,
  Col,
  Typography,
  Divider,
  Alert,
  Space,
  Descriptions,
} from 'antd';
import {
  CalculatorOutlined,
  DollarOutlined,
  AuditOutlined,
  SolutionOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

/** 案件类型选项：财产案件 / 非财产案件 */
const CASE_TYPE_OPTIONS = [
  { value: 'property', label: '财产案件' },
  { value: 'nonProperty', label: '非财产案件' },
];

/** 解除类型选项 */
const DISMISS_TYPE_OPTIONS = [
  { value: 'legal', label: '合法解除' },
  { value: 'illegal', label: '违法解除' },
  { value: 'negotiate', label: '协商解除' },
];

/** 律师费案件类型选项 */
const LAWYER_CASE_TYPE_OPTIONS = [
  { value: 'civil', label: '民事' },
  { value: 'criminal', label: '刑事' },
  { value: 'admin', label: '行政' },
];

/** 律师费地区选项 */
const REGION_OPTIONS = [
  { value: 'tier1', label: '一线城市' },
  { value: 'tier2', label: '二线城市' },
  { value: 'tier3', label: '三线及以下' },
];

/**
 * 根据诉讼标的额计算财产案件诉讼费
 * 依据《诉讼费用交纳办法》第十三条
 * @param amount - 诉讼标的额（元）
 * @returns 诉讼费金额（元）
 */
function calcPropertyCourtFee(amount: number): number {
  if (amount <= 10000) return 50;
  if (amount <= 100000) return amount * 0.025 - 200;
  if (amount <= 200000) return amount * 0.02 + 300;
  if (amount <= 500000) return amount * 0.015 + 1300;
  if (amount <= 1000000) return amount * 0.01 + 3800;
  if (amount <= 2000000) return amount * 0.009 + 4800;
  if (amount <= 5000000) return amount * 0.008 + 6800;
  if (amount <= 10000000) return amount * 0.007 + 11800;
  if (amount <= 20000000) return amount * 0.006 + 21800;
  return amount * 0.005 + 41800;
}

/**
 * 获取财产案件诉讼费计算公式文本
 * @param amount - 诉讼标的额（元）
 * @returns 计算公式字符串
 */
function getPropertyCourtFeeFormula(amount: number): string {
  if (amount <= 10000) return '不超过1万元：固定50元';
  if (amount <= 100000) return `标的额 × 2.5% - 200 = ${amount.toLocaleString()} × 2.5% - 200`;
  if (amount <= 200000) return `标的额 × 2% + 300 = ${amount.toLocaleString()} × 2% + 300`;
  if (amount <= 500000) return `标的额 × 1.5% + 1300 = ${amount.toLocaleString()} × 1.5% + 1300`;
  if (amount <= 1000000) return `标的额 × 1% + 3800 = ${amount.toLocaleString()} × 1% + 3800`;
  if (amount <= 2000000) return `标的额 × 0.9% + 4800 = ${amount.toLocaleString()} × 0.9% + 4800`;
  if (amount <= 5000000) return `标的额 × 0.8% + 6800 = ${amount.toLocaleString()} × 0.8% + 6800`;
  if (amount <= 10000000) return `标的额 × 0.7% + 11800 = ${amount.toLocaleString()} × 0.7% + 11800`;
  if (amount <= 20000000) return `标的额 × 0.6% + 21800 = ${amount.toLocaleString()} × 0.6% + 21800`;
  return `标的额 × 0.5% + 41800 = ${amount.toLocaleString()} × 0.5% + 41800`;
}

/**
 * 计算经济补偿金的工作年限折算
 * 每满1年支付1个月，6个月以上不满1年按1年算，不满6个月支付半个月
 * @param years - 工作年限
 * @returns 折算月数
 */
function calcCompensationMonths(years: number): number {
  const fullYears = Math.floor(years);
  const remainder = years - fullYears;
  if (remainder >= 0.5) {
    return fullYears + 1;
  } else if (remainder > 0) {
    return fullYears + 0.5;
  }
  return fullYears;
}

/**
 * 获取工作年限折算说明文本
 * @param years - 工作年限
 * @returns 折算说明字符串
 */
function getCompensationMonthsDesc(years: number): string {
  const fullYears = Math.floor(years);
  const remainder = years - fullYears;
  let detail = '';
  if (remainder === 0) {
    detail = `满${fullYears}年，折算${fullYears}个月`;
  } else if (remainder >= 0.5) {
    detail = `${fullYears}年余${remainder.toFixed(1)}年（6个月以上不满1年按1年算），折算${fullYears + 1}个月`;
  } else {
    detail = `${fullYears}年余${remainder.toFixed(1)}年（不满6个月支付半个月），折算${fullYears + 0.5}个月`;
  }
  return detail;
}

/**
 * 获取律师费基础估算范围（按标的额分段）
 * @param amount - 标的额（元）
 * @returns [最低费用, 最高费用]
 */
function getLawyerFeeBaseRange(amount: number): [number, number] {
  if (amount <= 100000) return [3000, 8000];
  if (amount <= 500000) return [8000, 25000];
  if (amount <= 1000000) return [25000, 50000];
  if (amount <= 5000000) return [50000, 150000];
  const extra = amount - 5000000;
  return [150000 + extra * 0.005, 150000 + extra * 0.02];
}

/**
 * 获取地区系数
 * @param region - 地区类型
 * @returns 地区系数
 */
function getRegionCoefficient(region: string): number {
  switch (region) {
    case 'tier1': return 1.3;
    case 'tier2': return 1.0;
    case 'tier3': return 0.7;
    default: return 1.0;
  }
}

/**
 * 格式化金额为人民币显示
 * @param value - 金额数值
 * @returns 格式化后的金额字符串
 */
function formatMoney(value: number): string {
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * 诉讼费计算器Tab组件
 * 支持财产案件和非财产案件的诉讼费计算
 */
const LitigationFeeCalculator: React.FC = () => {
  /** 案件类型 */
  const [caseType, setCaseType] = useState<string>('property');
  /** 诉讼标的额（元） */
  const [amount, setAmount] = useState<number | null>(null);

  /** 实时计算诉讼费结果 */
  const result = useMemo(() => {
    if (caseType === 'nonProperty') {
      return {
        fee: 75,
        halfFee: 37.5,
        formula: '非财产案件：50~100元（取中间值75元）',
        isProperty: false,
      };
    }
    if (amount === null || amount <= 0) {
      return null;
    }
    const fee = calcPropertyCourtFee(amount);
    return {
      fee,
      halfFee: fee / 2,
      formula: getPropertyCourtFeeFormula(amount),
      isProperty: true,
    };
  }, [caseType, amount]);

  return (
    <div>
      {/* 输入区域 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[24, 16]}>
          {/* 案件类型选择 */}
          <Col xs={24} sm={12}>
            <div style={{ marginBottom: 8 }}>
              <Text strong>案件类型</Text>
            </div>
            <Select
              value={caseType}
              onChange={setCaseType}
              options={CASE_TYPE_OPTIONS}
              style={{ width: '100%' }}
              size="large"
            />
          </Col>
          {/* 诉讼标的额输入 */}
          <Col xs={24} sm={12}>
            <div style={{ marginBottom: 8 }}>
              <Text strong>诉讼标的额（元）</Text>
            </div>
            <InputNumber
              value={amount}
              onChange={setAmount}
              min={0}
              step={10000}
              placeholder="请输入标的额"
              style={{ width: '100%' }}
              size="large"
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => Number(value?.replace(/,/g, '') || 0)}
              disabled={caseType === 'nonProperty'}
            />
          </Col>
        </Row>
      </Card>

      {/* 计算结果区域 */}
      {result && (
        <Card
          title={
            <Space>
              <DollarOutlined />
              <span>计算结果</span>
            </Space>
          }
        >
          <Row gutter={[24, 16]}>
            {/* 应交诉讼费 */}
            <Col xs={24} sm={12}>
              <Statistic
                title="应交诉讼费"
                value={result.fee}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#1890ff', fontSize: 28 }}
              />
            </Col>
            {/* 减半收取（简易程序） */}
            <Col xs={24} sm={12}>
              <Statistic
                title="减半收取（简易程序）"
                value={result.halfFee}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#52c41a', fontSize: 28 }}
              />
            </Col>
          </Row>

          <Divider />

          {/* 计算公式 */}
          <Descriptions column={1} size="small">
            <Descriptions.Item label="计算公式">
              <Text code>{result.formula}</Text>
            </Descriptions.Item>
          </Descriptions>

          {/* 法律依据 */}
          <div style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              依据：《诉讼费用交纳办法》第十三条
            </Text>
          </div>
        </Card>
      )}

      {/* 未输入时的提示 */}
      {!result && caseType === 'property' && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <CalculatorOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
          <Paragraph type="secondary">请输入诉讼标的额开始计算</Paragraph>
        </div>
      )}
    </div>
  );
};

/**
 * 劳动赔偿计算器Tab组件
 * 支持经济补偿金(N)、违法解除赔偿金(2N)、协商解除的计算
 */
const LaborCompensationCalculator: React.FC = () => {
  /** 月工资（元） */
  const [monthlySalary, setMonthlySalary] = useState<number | null>(null);
  /** 工作年限 */
  const [workingYears, setWorkingYears] = useState<number | null>(null);
  /** 解除类型 */
  const [dismissType, setDismissType] = useState<string>('legal');

  /** 实时计算劳动赔偿结果 */
  const result = useMemo(() => {
    if (monthlySalary === null || monthlySalary <= 0 || workingYears === null || workingYears <= 0) {
      return null;
    }

    /** 折算月数 */
    const months = calcCompensationMonths(workingYears);
    /** 经济补偿金(N) */
    const compensationN = monthlySalary * months;
    /** 违法解除赔偿金(2N) */
    const compensation2N = compensationN * 2;
    /** 折算说明 */
    const monthsDesc = getCompensationMonthsDesc(workingYears);

    /** 根据解除类型确定最终金额和说明 */
    let amount = 0;
    let typeLabel = '';
    let calculationDetail = '';

    switch (dismissType) {
      case 'legal':
        amount = compensationN;
        typeLabel = '经济补偿金(N)';
        calculationDetail = `${typeLabel} = 月工资 × 折算月数 = ${formatMoney(monthlySalary)} × ${months} = ¥${formatMoney(amount)}`;
        break;
      case 'illegal':
        amount = compensation2N;
        typeLabel = '违法解除赔偿金(2N)';
        calculationDetail = `${typeLabel} = 经济补偿金 × 2 = ¥${formatMoney(compensationN)} × 2 = ¥${formatMoney(amount)}`;
        break;
      case 'negotiate':
        amount = compensationN;
        typeLabel = '协商解除补偿金(N)';
        calculationDetail = `${typeLabel} = 月工资 × 折算月数 = ${formatMoney(monthlySalary)} × ${months} = ¥${formatMoney(amount)}`;
        break;
    }

    return {
      amount,
      typeLabel,
      compensationN,
      compensation2N,
      months,
      monthsDesc,
      calculationDetail,
    };
  }, [monthlySalary, workingYears, dismissType]);

  return (
    <div>
      {/* 输入区域 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[24, 16]}>
          {/* 月工资输入 */}
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 8 }}>
              <Text strong>月工资（元）</Text>
            </div>
            <InputNumber
              value={monthlySalary}
              onChange={setMonthlySalary}
              min={0}
              step={1000}
              placeholder="请输入月工资"
              style={{ width: '100%' }}
              size="large"
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => Number(value?.replace(/,/g, '') || 0)}
            />
          </Col>
          {/* 工作年限输入 */}
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 8 }}>
              <Text strong>工作年限</Text>
            </div>
            <InputNumber
              value={workingYears}
              onChange={setWorkingYears}
              min={0}
              max={50}
              step={0.5}
              placeholder="请输入工作年限"
              style={{ width: '100%' }}
              size="large"
              precision={1}
            />
          </Col>
          {/* 解除类型选择 */}
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 8 }}>
              <Text strong>解除类型</Text>
            </div>
            <Select
              value={dismissType}
              onChange={setDismissType}
              options={DISMISS_TYPE_OPTIONS}
              style={{ width: '100%' }}
              size="large"
            />
          </Col>
        </Row>
      </Card>

      {/* 计算结果区域 */}
      {result && (
        <Card
          title={
            <Space>
              <AuditOutlined />
              <span>计算结果</span>
            </Space>
          }
        >
          {/* 赔偿金额 */}
          <Row gutter={[24, 16]}>
            <Col xs={24} sm={12}>
              <Statistic
                title={result.typeLabel}
                value={result.amount}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#1890ff', fontSize: 28 }}
              />
            </Col>
            <Col xs={24} sm={12}>
              <Statistic
                title="经济补偿金(N)"
                value={result.compensationN}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#fa8c16', fontSize: 22 }}
              />
              <div style={{ marginTop: 12 }}>
                <Statistic
                  title="违法解除赔偿金(2N)"
                  value={result.compensation2N}
                  precision={2}
                  prefix="¥"
                  valueStyle={{ color: '#ff4d4f', fontSize: 22 }}
                />
              </div>
            </Col>
          </Row>

          <Divider />

          {/* 计算过程 */}
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="工作年限折算">
              {result.monthsDesc}，折算 {result.months} 个月
            </Descriptions.Item>
            <Descriptions.Item label="计算过程">
              <Text code>{result.calculationDetail}</Text>
            </Descriptions.Item>
          </Descriptions>

          {/* 法律依据 */}
          <div style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              依据：《中华人民共和国劳动合同法》第四十七条（经济补偿）、第四十八条（违法解除赔偿）、第三十六条（协商解除）
            </Text>
          </div>
        </Card>
      )}

      {/* 未输入时的提示 */}
      {!result && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <AuditOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
          <Paragraph type="secondary">请输入月工资和工作年限开始计算</Paragraph>
        </div>
      )}
    </div>
  );
};

/**
 * 律师费估算Tab组件
 * 根据案件类型、标的额、地区估算律师费范围
 */
const LawyerFeeCalculator: React.FC = () => {
  /** 案件类型 */
  const [caseType, setCaseType] = useState<string>('civil');
  /** 标的额（元） */
  const [amount, setAmount] = useState<number | null>(null);
  /** 地区 */
  const [region, setRegion] = useState<string>('tier2');

  /** 实时计算律师费估算结果 */
  const result = useMemo(() => {
    if (amount === null || amount <= 0) {
      return null;
    }

    /** 基础费用范围 */
    const [baseMin, baseMax] = getLawyerFeeBaseRange(amount);
    /** 地区系数 */
    const coefficient = getRegionCoefficient(region);
    /** 应用地区系数后的费用范围 */
    const minFee = Math.round(baseMin * coefficient);
    const maxFee = Math.round(baseMax * coefficient);

    /** 标的额分段说明 */
    let segmentDesc = '';
    if (amount <= 100000) {
      segmentDesc = '10万以下';
    } else if (amount <= 500000) {
      segmentDesc = '10万~50万';
    } else if (amount <= 1000000) {
      segmentDesc = '50万~100万';
    } else if (amount <= 5000000) {
      segmentDesc = '100万~500万';
    } else {
      segmentDesc = '500万以上（基础150000 + 超出部分0.5%~2%）';
    }

    /** 地区说明 */
    const regionLabel = REGION_OPTIONS.find((r) => r.value === region)?.label || '';

    return {
      minFee,
      maxFee,
      segmentDesc,
      coefficient,
      regionLabel,
    };
  }, [amount, region]);

  return (
    <div>
      {/* 输入区域 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[24, 16]}>
          {/* 案件类型选择 */}
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 8 }}>
              <Text strong>案件类型</Text>
            </div>
            <Select
              value={caseType}
              onChange={setCaseType}
              options={LAWYER_CASE_TYPE_OPTIONS}
              style={{ width: '100%' }}
              size="large"
            />
          </Col>
          {/* 标的额输入 */}
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 8 }}>
              <Text strong>标的额（元）</Text>
            </div>
            <InputNumber
              value={amount}
              onChange={setAmount}
              min={0}
              step={10000}
              placeholder="请输入标的额"
              style={{ width: '100%' }}
              size="large"
              formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(value) => Number(value?.replace(/,/g, '') || 0)}
            />
          </Col>
          {/* 地区选择 */}
          <Col xs={24} sm={8}>
            <div style={{ marginBottom: 8 }}>
              <Text strong>地区</Text>
            </div>
            <Select
              value={region}
              onChange={setRegion}
              options={REGION_OPTIONS}
              style={{ width: '100%' }}
              size="large"
            />
          </Col>
        </Row>
      </Card>

      {/* 计算结果区域 */}
      {result && (
        <Card
          title={
            <Space>
              <SolutionOutlined />
              <span>估算结果</span>
            </Space>
          }
        >
          {/* 费用范围展示 */}
          <Row gutter={[24, 16]}>
            <Col xs={24} sm={12}>
              <Statistic
                title="律师费估算（最低）"
                value={result.minFee}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#52c41a', fontSize: 28 }}
              />
            </Col>
            <Col xs={24} sm={12}>
              <Statistic
                title="律师费估算（最高）"
                value={result.maxFee}
                precision={2}
                prefix="¥"
                valueStyle={{ color: '#ff4d4f', fontSize: 28 }}
              />
            </Col>
          </Row>

          <Divider />

          {/* 估算依据 */}
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="标的额分段">
              {result.segmentDesc}
            </Descriptions.Item>
            <Descriptions.Item label="地区系数">
              {result.regionLabel} × {result.coefficient}
            </Descriptions.Item>
            <Descriptions.Item label="估算范围">
              ¥{formatMoney(result.minFee)} ~ ¥{formatMoney(result.maxFee)}
            </Descriptions.Item>
          </Descriptions>

          {/* 免责声明 */}
          <Alert
            style={{ marginTop: 16 }}
            type="warning"
            showIcon
            message="免责声明"
            description="此为估算，实际费用请咨询律师。律师费受案件复杂程度、律师资历、地区差异等多种因素影响，以上估算仅供参考。"
          />
        </Card>
      )}

      {/* 未输入时的提示 */}
      {!result && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <SolutionOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
          <Paragraph type="secondary">请输入标的额开始估算</Paragraph>
        </div>
      )}
    </div>
  );
};

/**
 * CalculatorPage 费用计算页面组件
 * 包含诉讼费、劳动赔偿、律师费三个计算器Tab
 */
const CalculatorPage: React.FC = () => {
  /** Tab项定义 */
  const tabItems = [
    {
      key: 'litigation',
      label: (
        <Space>
          <CalculatorOutlined />
          诉讼费计算器
        </Space>
      ),
      children: <LitigationFeeCalculator />,
    },
    {
      key: 'labor',
      label: (
        <Space>
          <AuditOutlined />
          劳动赔偿计算器
        </Space>
      ),
      children: <LaborCompensationCalculator />,
    },
    {
      key: 'lawyer',
      label: (
        <Space>
          <SolutionOutlined />
          律师费估算
        </Space>
      ),
      children: <LawyerFeeCalculator />,
    },
  ];

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      {/* 页面标题 */}
      <Title level={2} style={{ marginBottom: 24 }}>
        <DollarOutlined style={{ marginRight: 8, color: '#1890ff' }} />
        费用计算
      </Title>

      {/* 计算器Tabs */}
      <Tabs
        defaultActiveKey="litigation"
        items={tabItems}
        type="card"
        size="large"
      />
    </div>
  );
};

export default CalculatorPage;
