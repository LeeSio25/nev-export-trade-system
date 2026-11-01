-- 数据库创建
CREATE DATABASE IF NOT EXISTS cnev_export_trade_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;
  
  
  USE cnev_export_trade_db;
 -- 建表 
 -- 表1汽车企业AutoEnterprise表
 CREATE TABLE IF NOT EXISTS AutoEnterprise (
  EntID        CHAR(10)    NOT NULL PRIMARY KEY COMMENT '企业编号',
  EntName      VARCHAR(50) NOT NULL             COMMENT '企业名称',
  CreditCode   VARCHAR(18)                      COMMENT '统一社会信用代码',
  Province     VARCHAR(30)                      COMMENT '所属省份',
  EntType      VARCHAR(20)                      COMMENT '企业类型：整车/零部件/贸易',
  Brand        VARCHAR(30)                      COMMENT '品牌',
  FoundYear    INT                              COMMENT '成立年份',
  ContactPhone VARCHAR(20)                      COMMENT '联系电话',
  UNIQUE KEY uk_auto_enterprise_credit_code (CreditCode)
) COMMENT='汽车企业表';


-- 表2生产基地ProductionBase表
CREATE TABLE IF NOT EXISTS ProductionBase (
  BaseID     CHAR(10)    NOT NULL PRIMARY KEY COMMENT '基地编号',
  EntID      CHAR(10)    NOT NULL             COMMENT '所属企业编号',
  BaseName   VARCHAR(50) NOT NULL             COMMENT '基地名称',
  Province   VARCHAR(30)                      COMMENT '省份',
  City       VARCHAR(30)                      COMMENT '城市',
  Capacity   INT                              COMMENT '设计产能',
  StartYear  INT                              COMMENT '投产年份',
  BaseType   VARCHAR(20)                      COMMENT '基地类型：整车/电池/零部件',
  KEY idx_production_base_ent_id (EntID),
  CONSTRAINT fk_production_base_enterprise FOREIGN KEY (EntID) REFERENCES AutoEnterprise (EntID) ON UPDATE CASCADE ON DELETE RESTRICT,
  -- CONSTRAINT chk_production_base_type CHECK (BaseType IS NULL OR BaseType IN ('整车','电池','零部件')),
  CONSTRAINT chk_production_base_capacity CHECK (Capacity IS NULL OR Capacity >= 0),
  CONSTRAINT chk_production_base_start_year CHECK (StartYear IS NULL OR StartYear BETWEEN 1800 AND 2100)
) COMMENT='生产基地表';


-- 表3出口车型ExportModel表
CREATE TABLE IF NOT EXISTS ExportModel (
  ModelID      CHAR(10)     NOT NULL PRIMARY KEY COMMENT '车型编号',
  EntID        CHAR(10)     NOT NULL             COMMENT '所属企业编号',
  ModelName    VARCHAR(50)  NOT NULL             COMMENT '车型名称',
  VehicleType  VARCHAR(10)                       COMMENT '车辆类型：纯电/插混',
  RangeKm      INT                               COMMENT '续航里程（km）',
  BatteryType  VARCHAR(20)                       COMMENT '电池类型',
  BatteryCap   DECIMAL(6,2)                      COMMENT '电池容量（kW·h）',
  SeatNum      INT                               COMMENT '座位数',
  LaunchYear   INT                               COMMENT '上市年份',
  GuidePrice   DECIMAL(12,2)                     COMMENT '指导价（元）',
  ModelStatus  VARCHAR(10)                       COMMENT '车型状态：在售/停产',
  KEY idx_export_model_ent_id (EntID),
  CONSTRAINT fk_export_model_enterprise FOREIGN KEY (EntID) REFERENCES AutoEnterprise (EntID) ON UPDATE CASCADE ON DELETE RESTRICT
) COMMENT='出口车型表';


-- 表4目的国Country表
CREATE TABLE IF NOT EXISTS Country(
  CountryCode  CHAR(3)     NOT NULL PRIMARY KEY COMMENT '国家代码',
  CountryName  VARCHAR(50) NOT NULL             COMMENT '国名',
  Continent    VARCHAR(20)                      COMMENT '大洲',
  Region       VARCHAR(30)                      COMMENT '区域',
  IsBeltRoad   CHAR(1)                          COMMENT '是否“一带一路”：Y/N',
  IsRCEP       CHAR(1)                          COMMENT '是否RCEP：Y/N',
  CurrencyCode CHAR(3)                          COMMENT '货币代码',
  MarketLevel  VARCHAR(10)                      COMMENT '市场准入等级',
  Language     VARCHAR(20)                      COMMENT '官方语言',
  CONSTRAINT chk_country_belt_road CHECK (IsBeltRoad IS NULL OR IsBeltRoad IN ('Y','N')),
  CONSTRAINT chk_country_rcep CHECK (IsRCEP IS NULL OR IsRCEP IN ('Y','N'))
) COMMENT='目的国表';


-- 表5海外经销商Dealer表
CREATE TABLE IF NOT EXISTS Dealer(
  DealerID      CHAR(10)    NOT NULL PRIMARY KEY COMMENT '经销商编号',
  DealerName    VARCHAR(50) NOT NULL             COMMENT '经销商名称',
  CountryCode   CHAR(3)     NOT NULL             COMMENT '所在国家',
  DealerType    VARCHAR(20)                      COMMENT '经销商/大客户',
  CooperateDate DATE                             COMMENT '合作起始日期',
  CreditLevel   CHAR(1)                          COMMENT '信用等级',
  ContactPhone  VARCHAR(20)                      COMMENT '联系电话',
  KEY idx_dealer_country_code (CountryCode),
  CONSTRAINT fk_dealer_country_code FOREIGN KEY (CountryCode) REFERENCES Country (CountryCode) ON UPDATE CASCADE ON DELETE RESTRICT
) COMMENT='海外经销商表';


-- 表6出口订单ExportOrder表
CREATE TABLE IF NOT EXISTS ExportOrder (
  OrderNo        CHAR(15)      NOT NULL PRIMARY KEY COMMENT '订单号',
  EntID          CHAR(10)      NOT NULL             COMMENT '出口企业编号',
  DealerID       CHAR(10)      NOT NULL             COMMENT '经销商编号',
  CountryCode    CHAR(3)       NOT NULL             COMMENT '目的国代码',
  OrderDate      DATE          NOT NULL             COMMENT '订单日期',
  ContractAmount DECIMAL(14,2)                      COMMENT '合同金额',
  CurrencyCode   CHAR(3)                            COMMENT '币种代码',
  TradeTerm      VARCHAR(10)                        COMMENT '贸易术语：FOB/CIF',
  PayMethod      VARCHAR(20)                        COMMENT '付款方式',
  OrderStatus    VARCHAR(20)                        COMMENT '订单状态：未发货/在途/到港/签收',
  Salesperson    VARCHAR(30)                        COMMENT '业务员',
  Remark         VARCHAR(200)                       COMMENT '备注',
  KEY idx_export_order_ent_id (EntID),
  KEY idx_export_order_dealer_id (DealerID),
  KEY idx_export_order_country_code (CountryCode),
  KEY idx_export_order_date (OrderDate),
  CONSTRAINT fk_export_order_enterprise FOREIGN KEY (EntID) REFERENCES AutoEnterprise (EntID) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_export_order_dealer FOREIGN KEY (DealerID) REFERENCES Dealer (DealerID) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_export_order_country FOREIGN KEY (CountryCode) REFERENCES Country (CountryCode) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_export_order_trade_term CHECK (TradeTerm IS NULL OR TradeTerm IN ('FOB','CIF')),
  CONSTRAINT chk_export_order_status CHECK (OrderStatus IS NULL OR OrderStatus IN ('未发货','在途','到港','签收')),
  CONSTRAINT chk_export_order_amount CHECK (ContractAmount IS NULL OR ContractAmount >= 0)
) COMMENT='出口订单表';
 -- 表7订单明细OrderDetail表
CREATE TABLE IF NOT EXISTS OrderDetail
(
 OrderNo        CHAR(15)             NOT NULL COMMENT '订单号',
 ModelID        CHAR(10)             NOT NULL COMMENT '车型编号',
 Quantity       INT                  NOT NULL COMMENT '数量',
 UnitPrice      DECIMAL(12,2)                 COMMENT '单价',
 Amount         DECIMAL(14,2)                 COMMENT '金额',
 ConfigVersion  VARCHAR(30)                   COMMENT '配置版本',
 PRIMARY KEY (OrderNo, ModelID),
 CONSTRAINT ck_od_qty   CHECK (Quantity > 0),
 CONSTRAINT ck_od_price CHECK (UnitPrice IS NULL OR UnitPrice >= 0),
 CONSTRAINT ck_od_amt   CHECK (Amount    IS NULL OR Amount    >= 0),
 CONSTRAINT fk_od_order FOREIGN KEY (OrderNo) REFERENCES ExportOrder(OrderNo)
      ON DELETE CASCADE ON UPDATE CASCADE,
 CONSTRAINT fk_od_model FOREIGN KEY (ModelID) REFERENCES ExportModel(ModelID)
      ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_od_model (ModelID)
)COMMENT '订单明细OrderDetail表';


-- 表8物流承运商Carrier表
CREATE TABLE IF NOT EXISTS Carrier
(
 CarrierID      CHAR(10) PRIMARY KEY NOT NULL COMMENT '承运商编号',
 CarrierName    VARCHAR(50)          NOT NULL COMMENT '承运商名称',
 TransportMode  VARCHAR(20)                   COMMENT '海运/铁路/公路',
 MainRoute      VARCHAR(100)                  COMMENT '主营航线',
 Contact        VARCHAR(30)                   COMMENT '联系人',
 CreditLevel    CHAR(1)                       COMMENT '信用等级',
 CONSTRAINT ck_car_mode  CHECK (TransportMode IS NULL OR TransportMode IN ('海运','铁路','公路','空运')),
 CONSTRAINT ck_car_level CHECK (CreditLevel   IS NULL OR CreditLevel   IN ('A','B','C','D')),
 CONSTRAINT ck_car_name  CHECK (CHAR_LENGTH(TRIM(CarrierName)) > 0)
)COMMENT '物流承运商Carrier表';


-- 表9物流运单Waybill表
CREATE TABLE IF NOT EXISTS Waybill
(
 WaybillNo        CHAR(15) PRIMARY KEY NOT NULL COMMENT '运单号',
 OrderNo          CHAR(15)             NOT NULL COMMENT '订单号',
 CarrierID        CHAR(10)             NOT NULL COMMENT '承运商',
 DepartPort       VARCHAR(30)                   COMMENT '起运港',
 ArrivePort       VARCHAR(30)                   COMMENT '目的港',
 VesselVoyage     VARCHAR(50)                   COMMENT '船名航次',
 ContainerNo      VARCHAR(20)                   COMMENT '集装箱号',
 ETD              DATE                          COMMENT '预计离港',
 ETA              DATE                          COMMENT '预计到港',
 ActualArriveDate DATE                          COMMENT '实际到港',
 Freight          DECIMAL(10,2)                 COMMENT '运费',
 Insurance        DECIMAL(10,2)                 COMMENT '保险金额',
 WaybillStatus    VARCHAR(20)                   COMMENT '在途/到港/签收',
 CONSTRAINT ck_wb_freight CHECK (Freight   IS NULL OR Freight   >= 0),
 CONSTRAINT ck_wb_ins     CHECK (Insurance IS NULL OR Insurance >= 0),
 CONSTRAINT ck_wb_eta     CHECK (ETA              IS NULL OR ETD IS NULL OR ETA              >= ETD),
 CONSTRAINT ck_wb_ata     CHECK (ActualArriveDate IS NULL OR ETD IS NULL OR ActualArriveDate >= ETD),
 CONSTRAINT ck_wb_status  CHECK (WaybillStatus    IS NULL OR WaybillStatus IN ('未发运','在途','到港','签收')),
-- CONSTRAINT ck_wb_container CHECK (ContainerNo IS NULL OR ContainerNo REGEXP '^[A-Za-z]{4}[0-9]{7}$'),
 CONSTRAINT fk_wb_order   FOREIGN KEY (OrderNo)   REFERENCES ExportOrder(OrderNo)
      ON DELETE CASCADE  ON UPDATE CASCADE,
 CONSTRAINT fk_wb_carrier FOREIGN KEY (CarrierID) REFERENCES Carrier(CarrierID)
      ON DELETE RESTRICT ON UPDATE CASCADE,
 INDEX idx_wb_order (OrderNo),
 INDEX idx_wb_carrier (CarrierID)
)COMMENT '物流运单Waybill表';


-- 表10贸易政策Policy表
CREATE TABLE IF NOT EXISTS Policy
(
 PolicyID        CHAR(10) PRIMARY KEY NOT NULL COMMENT '政策编号',
 PolicyName      VARCHAR(100)         NOT NULL COMMENT '政策名称',
 PolicyType      VARCHAR(20)                   COMMENT '关税/补贴/准入/认证',
 PublishCountry  CHAR(3)              NOT NULL COMMENT '发布国家',
 PublishOrg      VARCHAR(50)                   COMMENT '发布机构',
 EffectDate      DATE                 NOT NULL COMMENT '生效日期',
 ExpireDate      DATE                          COMMENT '失效日期',
 PolicyVersion   VARCHAR(10)          NOT NULL COMMENT '版本',
 Summary         VARCHAR(200)                  COMMENT '摘要',
 PolicyStatus    VARCHAR(10)                   COMMENT '有效/失效',
 CONSTRAINT uk_pol_name   UNIQUE (PolicyName, PublishCountry, PolicyVersion),
 CONSTRAINT ck_pol_expire CHECK (ExpireDate   IS NULL OR ExpireDate > EffectDate),
 CONSTRAINT ck_pol_type   CHECK (PolicyType   IS NULL OR PolicyType   IN ('关税','补贴','准入','认证')),
 CONSTRAINT ck_pol_status CHECK (PolicyStatus IS NULL OR PolicyStatus IN ('有效','失效')),
 CONSTRAINT ck_pol_ver    CHECK (CHAR_LENGTH(TRIM(PolicyVersion)) > 0),
 CONSTRAINT fk_pol_country FOREIGN KEY (PublishCountry) REFERENCES Country(CountryCode)
      ON DELETE RESTRICT ON UPDATE CASCADE
)COMMENT '贸易政策Policy表';


-- 表11认证法规Certification表
CREATE TABLE IF NOT EXISTS Certification
(
 CertID       CHAR(10) PRIMARY KEY NOT NULL COMMENT '认证编号',
 CountryCode  CHAR(3)              NOT NULL COMMENT '制定国家',
 CertName     VARCHAR(50)          NOT NULL COMMENT '认证名称',
 StandardNo   VARCHAR(30)                   COMMENT '标准号',
 VehicleType  VARCHAR(10)                   COMMENT '适用车型类别',
 ValidPeriod  INT                           COMMENT '有效期月数',
 CertStatus   VARCHAR(10)                   COMMENT '有效/废止',
 IssueOrg     VARCHAR(50)                   COMMENT '发布机构',
 CONSTRAINT ck_cert_period CHECK (ValidPeriod IS NULL OR ValidPeriod > 0),
 CONSTRAINT ck_cert_status CHECK (CertStatus IS NULL OR CertStatus IN ('有效','废止')),
 CONSTRAINT fk_cert_country FOREIGN KEY (CountryCode) REFERENCES Country(CountryCode)
      ON DELETE RESTRICT ON UPDATE CASCADE
)COMMENT '认证法规Certification表';


-- 报关单Customs表
CREATE TABLE IF NOT EXISTS Customs
(
 DeclNo         CHAR(15) PRIMARY KEY NOT NULL COMMENT '报关单号',
 OrderNo        CHAR(15)             NOT NULL COMMENT '订单号（唯一）',
 DeclDate       DATE                 NOT NULL COMMENT '申报日期',
 HSCode         VARCHAR(15)                   COMMENT 'HS编码',
 OriginCertNo   VARCHAR(30)                   COMMENT '原产地证号',
 TaxRefund      DECIMAL(12,2)                 COMMENT '出口退税金额',
 SuperviseMode  VARCHAR(20)                   COMMENT '监管方式',
 DeclPort       VARCHAR(30)                   COMMENT '申报口岸',
 CustomsStatus  VARCHAR(10)                   COMMENT '已放行/查验',
 CONSTRAINT uk_cus_order  UNIQUE (OrderNo),
 CONSTRAINT ck_cus_refund CHECK (TaxRefund IS NULL OR TaxRefund >= 0),
 -- CONSTRAINT ck_cus_hs     CHECK (HSCode IS NULL OR HSCode REGEXP '^[0-9]{10}$'),
 CONSTRAINT ck_cus_status CHECK (CustomsStatus IS NULL OR CustomsStatus IN ('已申报','查验','已放行')),
 CONSTRAINT fk_cus_order  FOREIGN KEY (OrderNo) REFERENCES ExportOrder(OrderNo)
      ON DELETE RESTRICT ON UPDATE CASCADE
)COMMENT '报关单Customs表';


-- 创建表3-13
CREATE TABLE  IF NOT EXISTS AfterSales (
    ASID CHAR(10) NOT NULL COMMENT '网点编号',
    EntID CHAR(10) NOT NULL COMMENT '所属企业',
    CountryCode CHAR(3) NOT NULL COMMENT '所在国家',
    City VARCHAR(30) COMMENT '城市',
    ASName VARCHAR(50) NOT NULL COMMENT '网点名称',
    ASType VARCHAR(20) COMMENT '销售/售后/充电',
    ServiceAbility VARCHAR(50) COMMENT '服务能力',
    OpenDate DATE COMMENT '开业日期',
    PRIMARY KEY (ASID),
    CONSTRAINT fk_aftersales_enterprise FOREIGN KEY (EntID) REFERENCES AutoEnterprise(EntID),
    CONSTRAINT fk_aftersales_country FOREIGN KEY (CountryCode) REFERENCES Country(CountryCode)
) COMMENT'售后网点表';
-- 创建表3-14
CREATE TABLE IF NOT EXISTS  QualityEvent(
    QEID CHAR(10) NOT NULL COMMENT '事件编号',
    ModelID CHAR(10) NOT NULL COMMENT '车型编号',
    CountryCode CHAR(3) NOT NULL COMMENT '发生国家',
    EventType VARCHAR(20) COMMENT '质量/召回/投诉',
    EventDate DATE COMMENT '发生日期',
    AffectQty INT COMMENT '影响数量',
    HandleStatus VARCHAR(20) COMMENT '处理状态',
    RecallFlag CHAR(1) NOT NULL CHECK (RecallFlag IN ('Y', 'N')) COMMENT '是否召回Y/N',
    PRIMARY KEY (QEID),
    CONSTRAINT fk_qualityevent_exportmodel FOREIGN KEY (ModelID) REFERENCES ExportModel(ModelID),
    CONSTRAINT fk_qualityevent_country FOREIGN KEY (CountryCode) REFERENCES Country(CountryCode)
)COMMENT '质量事件';
-- 创建表3-15
CREATE TABLE  IF NOT EXISTS Currency(
    CurrencyCode CHAR(3) NOT NULL COMMENT '币种代码',
    CurrencyName VARCHAR(20) COMMENT '币种名称',
    Symbol VARCHAR(5) COMMENT '符号',
    PRIMARY KEY (CurrencyCode)
)COMMENT '币种';
-- 创建表3-16
CREATE TABLE  IF NOT EXISTS ExchangeRate(
    CurrencyCode CHAR(3) NOT NULL COMMENT '币种',
    YearMonth CHAR(6) NOT NULL COMMENT 'YYYYMM',
    RateToCNY DECIMAL(10,4) NOT NULL COMMENT '对人民币汇率',
    Source VARCHAR(30) COMMENT '数据来源',
    PRIMARY KEY (CurrencyCode,YearMonth),
    CONSTRAINT fk_exchangerate_currency FOREIGN KEY (CurrencyCode) REFERENCES Currency(CurrencyCode)
)COMMENT '汇率';
-- 创建表3-17
CREATE TABLE  IF NOT EXISTS PolicyApply(
    PolicyID CHAR(30) NOT NULL COMMENT '政策编号',
    CountryCode CHAR(3) NOT NULL COMMENT '适用国家',
    ApplyStart DATE NOT NULL COMMENT '适用起始日期',
    ApplyEnd DATE COMMENT '适用结束日期',
    VehicleType VARCHAR(10) COMMENT '适用车型类别',
    EntType VARCHAR(20) COMMENT '适用企业类型',
    TaxRate DECIMAL(6,2) COMMENT '税率',
    SubsidyAmount DECIMAL(12,2) COMMENT '补贴金额',
    ApplyNote VARCHAR(100) COMMENT '说明',
    PRIMARY KEY (PolicyID,CountryCode,ApplyStart),
    CONSTRAINT fk_policyapply_policy FOREIGN KEY (PolicyID) REFERENCES Policy(PolicyID),
    CONSTRAINT fk_policyapply_country FOREIGN KEY (CountryCode) REFERENCES Country(CountryCode)
)COMMENT '政策适用';
-- 创建表3-18
CREATE TABLE IF NOT EXISTS  ModelCert(
    ModelID CHAR(10) NOT NULL COMMENT '车型编号',
    CertID CHAR(10) NOT NULL COMMENT '认证编号',
    CertDate DATE NOT NULL COMMENT '认证日期',
    ExpireDate DATE COMMENT '到期日期',
    CertResult VARCHAR(10) NOT NULL CHECK (CertResult IN ('通过', '不通过')) COMMENT'通过/不通过',
    CertNo VARCHAR(30) COMMENT '证书号',
    PRIMARY KEY(ModelID,CertID),
    CONSTRAINT fk_modelcert_exportmodel FOREIGN KEY (ModelID) REFERENCES ExportModel(ModelID),
    CONSTRAINT fk_modelcert_certification FOREIGN KEY (CertID) REFERENCES Certification(CertID)
)COMMENT ' 车型认证';
-- 1. 删除引用 PolicyApply.PolicyID 的外键
ALTER TABLE PolicyApply
  DROP FOREIGN KEY fk_policyapply_policy;

-- 2. 把 PolicyID 改成 CHAR(10)
ALTER TABLE PolicyApply
  MODIFY COLUMN PolicyID CHAR(10) NOT NULL COMMENT '政策编号';

-- 3. 重新加回外键
ALTER TABLE PolicyApply
  ADD CONSTRAINT fk_policyapply_policy
  FOREIGN KEY (PolicyID) REFERENCES Policy(PolicyID)
  ON UPDATE CASCADE ON DELETE RESTRICT;