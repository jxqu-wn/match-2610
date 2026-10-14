# 双份标注待裁定工作表

重新校验两方12批响应及冻结文件通过；重新比对与 comparison-v1 的三份 JSON 完全一致。

Codex 为 left，Deepseek Flash 为 right。230 对关联一致，66 对关联分歧，依据分类分歧 0 对。另有71份候选报告和19份内容问题报告。

156份待审报告按表和知识合并为 108 个裁定单元；合并仅减少重复展示，不删除任何报告。

本文件未作语义裁定。未输出肯定关联不等于否定；一致项也尚未经人审。正式预处理及两方冻结标注均不修改。

填写 decisions.json 的 decision 和 reason；association_decision 可填 accept / reject / defer，accepted_basis 可填 explicit / schema_supported，内容问题请单独写入 content_decision。保持知识原文不变。

## R001 · MYSQL:common.administrative_division · 知识 1590

“西电东送”指将西部地区的电力输送到东部地区。送端省份包括四川、云南、贵州、甘肃、青海、宁夏、陕西、新疆、西藏；受端省份包括上海、江苏、浙江、安徽、福建、山东、广东。

### 原始报告 #1 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1590,
  "basis": "schema_supported",
  "fields": [
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1590,
      "quote": "送端省份包括四川、云南、贵州、甘肃、青海、宁夏、陕西、新疆、西藏；受端省份包括上海、江苏、浙江、安徽、福建、山东、广东。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条送端、受端省份枚举直接解释省级行政区名称的筛选集合，Schema明确存储省级名称；关联范围为省份枚举片段。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R002 · MYSQL:common.administrative_division · 知识 1598

“三北地区”指东北、华北、西北，是中国风电和光伏的主要集中区域。东北包括黑龙江省、吉林省、辽宁省，华北包括北京市、天津市、河北省、山西省、内蒙古自治区，西北包括陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。

### 原始报告 #2 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1598,
  "basis": "schema_supported",
  "fields": [
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1598,
      "quote": "东北包括黑龙江省、吉林省、辽宁省，华北包括北京市、天津市、河北省、山西省、内蒙古自治区，西北包括陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "东北、华北、西北的省级行政区枚举直接对应Schema的省级名称，可解释本表省份名称的分组集合。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R003 · MYSQL:common.administrative_division · 知识 1763

东北三省指：黑龙江省、吉林省、辽宁省。

### 原始报告 #3 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1763,
  "basis": "schema_supported",
  "fields": [
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1763,
      "quote": "东北三省指：黑龙江省、吉林省、辽宁省。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示由省级行政区名称组成的地区集合；本表明确存储省级名称，可直接解释这些名称的筛选或分组集合。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R004 · MYSQL:common.administrative_division · 知识 1764

华东地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。

### 原始报告 #4 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1764,
  "basis": "schema_supported",
  "fields": [
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1764,
      "quote": "华东地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示由省级行政区名称组成的地区集合；本表明确存储省级名称，可直接解释这些名称的筛选或分组集合。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R005 · MYSQL:common.administrative_division · 知识 1778

长江三角洲地区（长三角）包括上海市、江苏省、浙江省、安徽省。

### 原始报告 #5 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1778,
  "basis": "schema_supported",
  "fields": [
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1778,
      "quote": "长江三角洲地区（长三角）包括上海市、江苏省、浙江省、安徽省。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示由省级行政区名称组成的地区集合；本表明确存储省级名称，可直接解释这些名称的筛选或分组集合。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R006 · MYSQL:common.administrative_division · 知识 1779

珠江三角洲地区（珠三角）包括广东省广州、深圳、珠海、佛山、惠州、东莞、中山、江门、肇庆9市。

### 原始报告 #6 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1779,
  "basis": "schema_supported",
  "fields": [
    "province_name",
    "city_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1779,
      "quote": "珠江三角洲地区（珠三角）包括广东省广州、深圳、珠海、佛山、惠州、东莞、中山、江门、肇庆9市。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条列出广东省及珠三角九市，直接对应本表的省级、市级行政区名称，可解释城市名称的筛选集合。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R007 · MYSQL:common.administrative_division · 知识 1780

京津冀地区包括北京市、天津市、河北省。

### 原始报告 #7 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1780,
  "basis": "schema_supported",
  "fields": [
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1780,
      "quote": "京津冀地区包括北京市、天津市、河北省。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示由省级行政区名称组成的地区集合；本表明确存储省级名称，可直接解释这些名称的筛选或分组集合。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R008 · MYSQL:common.administrative_division · 知识 1793

华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。

### 原始报告 #8 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1793,
  "basis": "schema_supported",
  "fields": [
    "id",
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1793,
      "quote": "华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示省级行政区名称及行政区划代码前缀筛选，本表存储六位行政区划代码和省级名称，直接支持该筛选对象。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R009 · MYSQL:common.administrative_division · 知识 1794

华北地区包括：北京市、天津市、河北省、山西省、内蒙古自治区。

### 原始报告 #9 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1794,
  "basis": "schema_supported",
  "fields": [
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1794,
      "quote": "华北地区包括：北京市、天津市、河北省、山西省、内蒙古自治区。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示由省级行政区名称组成的地区集合；本表明确存储省级名称，可直接解释这些名称的筛选或分组集合。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R010 · MYSQL:common.administrative_division · 知识 1795

华中地区包括：河南省、湖北省、湖南省。

### 原始报告 #10 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1795,
  "basis": "schema_supported",
  "fields": [
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1795,
      "quote": "华中地区包括：河南省、湖北省、湖南省。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示由省级行政区名称组成的地区集合；本表明确存储省级名称，可直接解释这些名称的筛选或分组集合。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R011 · MYSQL:common.administrative_division · 知识 1796

西南地区包括：重庆市、四川省、贵州省、云南省、西藏自治区。

### 原始报告 #11 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1796,
  "basis": "schema_supported",
  "fields": [
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1796,
      "quote": "西南地区包括：重庆市、四川省、贵州省、云南省、西藏自治区。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示由省级行政区名称组成的地区集合；本表明确存储省级名称，可直接解释这些名称的筛选或分组集合。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R012 · MYSQL:common.administrative_division · 知识 1797

西北地区包括：陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。

### 原始报告 #12 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1797,
  "basis": "schema_supported",
  "fields": [
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1797,
      "quote": "西北地区包括：陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示由省级行政区名称组成的地区集合；本表明确存储省级名称，可直接解释这些名称的筛选或分组集合。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R013 · MYSQL:common.administrative_division · 知识 1799

中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。

### 原始报告 #13 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1799,
  "basis": "schema_supported",
  "fields": [
    "id",
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1799,
      "quote": "中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示省级行政区名称及行政区划代码前缀筛选，本表存储六位行政区划代码和省级名称，直接支持该筛选对象。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R014 · MYSQL:common.administrative_division · 知识 1800

中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。

### 原始报告 #14 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1800,
  "basis": "schema_supported",
  "fields": [
    "id",
    "province_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1800,
      "quote": "中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明示省级行政区名称及行政区划代码前缀筛选，本表存储六位行政区划代码和省级名称，直接支持该筛选对象。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex：相关字段在训练集中未出现，放宽关联以覆盖测试未见情况；字段含义支持该解释。

## R015 · MYSQL:common.administrative_division · 知识 1596

县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。

### 原始报告 #15 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1596,
  "kind": "conflicting_content",
  "knowledge_evidence": [
    {
      "knowledge_id": 1596,
      "quote": "地级市代码特征：前4位以00结尾。"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "知识称地级市代码前4位以00结尾，原始Schema却列苏州市320500和南京市320100为level=2；两例前4位分别为3205、3201，与该断言冲突，未修改任何代码规则。"
}
```

裁定状态：resolved；关联：未另作关联裁定；来源：user_explicit。

理由：用户指定 Schema 优先，否定知识中与 Schema 示例冲突的区划编码断言。

内容处理：采用原始 Schema；1596 中冲突的地级市编码规则不作为可执行依据。知识原文保留，不作改写。

## R016 · MYSQL:common.vehicle_type_dict · 知识 1768

A1驾照准驾大型客车；B2驾照准驾大型货车；A2准驾牵引车；C1驾照准驾小型汽车。货车包含A2和B2

### 原始报告 #16 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1768,
  "knowledge_evidence": [
    {
      "knowledge_id": 1768,
      "quote": "A1驾照准驾大型客车；B2驾照准驾大型货车；A2准驾牵引车；C1驾照准驾小型汽车。货车包含A2和B2"
    }
  ],
  "reason": "知识将驾照代码与大型客车/大型货车等车辆类别关联，但未指明 vehicle_type_dict，且其 type_name 为客车/货车等泛类别，缺少大型客车等与字典代码的直接映射，无法确认是否直接解释该表。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户指定按类别后缀对应：大型客车对应 type_name=客车，准驾牵引车对应牵引车。

内容处理：按用户指定的后缀口径解释类别，不新增字典代码。

## R017 · MYSQL:common.vessel_type_dict · 知识 1777

船舶航速单位“节”等于海里/小时，1节≈1.852公里/小时。高速船舶通常指航速≥25节。

### 原始报告 #17 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1777,
  "knowledge_evidence": [
    {
      "knowledge_id": 1777,
      "quote": "高速船舶通常指航速≥25节。"
    }
  ],
  "reason": "字典有高速客船名称，但本条定义的是高速船舶的一般航速阈值，未说明是否界定字典中的高速客船类型，字典也没有航速属性，不能确认直接适用范围。"
}
```

裁定状态：resolved；关联：reject；来源：user_explicit。

理由：用户指出训练集没有高速判定问题；类型名称中的高速不等于该知识中的航速阈值。

## R018 · MYSQL:common.license_type_dict · 知识 1787

驾驶员从业资格类型：普通货运、危险品运输、旅客运输。不同类型对应不同的 license_type 和公司 business_type。

### 原始报告 #18 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1787,
  "knowledge_evidence": [
    {
      "knowledge_id": 1787,
      "quote": "驾驶员从业资格类型：普通货运、危险品运输、旅客运输。不同类型对应不同的 license_type 和公司 business_type。"
    }
  ],
  "reason": "本条提及license_type并列出从业资格类型，但未给出这些资格与字典驾照代码的对应关系，无法确认它是否直接解释本字典取值。"
}
```

裁定状态：resolved；关联：reject；来源：user_explicit。

理由：用户认为无对应映射或关联信息支持。

## R019 · MYSQL:common.dict_size_category · 知识 1595

企业员工规模等级：大型企业 staff_count≥5000，中型企业 1000≤staff_count<5000，小型企业 staff_count<1000。

### 原始报告 #19 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1595,
  "basis": "schema_supported",
  "fields": [
    "size_name"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1595,
      "quote": "企业员工规模等级：大型企业 staff_count≥5000，中型企业 1000≤staff_count<5000，小型企业 staff_count<1000。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE dict_size_category (\r\n    size_code VARCHAR(10) PRIMARY KEY COMMENT '规模代码',\r\n    size_name VARCHAR(20) NOT NULL COMMENT '规模名称'\r\n) COMMENT='企业规模划型字典';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "INSERT INTO dict_size_category (size_code, size_name) VALUES\r\n('L', '大型'),\r\n('M', '中型'),\r\n('S', '小型'),\r\n('XS', '微型');"
    }
  ],
  "qualifiers": [],
  "reason": "知识直接按员工数解释大型、中型、小型企业规模等级，本表明确为企业规模划型字典并含这三个规模名称；关联范围为规模名称的定义。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户采纳 Codex 对企业规模名称定义的关联。

## R020 · MYSQL:common.energy_type_dict · 知识 1597

“双碳”目标指2030年前实现碳达峰、2060年前实现碳中和。清洁能源和新能源是实现双碳目标的主力军。清洁能源装机占比 = 清洁能源装机容量 / 总装机容量 × 100%。

### 原始报告 #20 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1597,
  "knowledge_evidence": [
    {
      "knowledge_id": 1597,
      "quote": "清洁能源和新能源是实现双碳目标的主力军。清洁能源装机占比 = 清洁能源装机容量 / 总装机容量 × 100%。"
    }
  ],
  "reason": "清洁能源、新能源与字典大类名称相符，但本条核心为双碳目标和装机占比，字典不含装机容量，也未明确指定字典作为分类来源，无法确认该计算对字典的直接适用范围。"
}
```

### 原始报告 #21 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1597,
  "knowledge_evidence": [
    {
      "knowledge_id": 1597,
      "quote": "“双碳”目标指2030年前实现碳达峰、2060年前实现碳中和。清洁能源和新能源是实现双碳目标的主力军。清洁能源装机占比 = 清洁能源装机容量 / 总装机容量 × 100%。"
    }
  ],
  "reason": "知识提到清洁能源、新能源，与 energy_type_dict.category 的取值文字相近，但未给出能源类型代码或表名，无法确认是对该字典的直接描述。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户指出训练问题语境涉及装机，清洁能源装机知识应关联能源类别字典。

## R021 · MYSQL:common.energy_position_dict · 知识 1589

员工学历与岗位对应：技术人员(CE、TE、EE、SE)通常为硕士或博士，值班员(OP)和检修工(MT、EL)通常为本科或大专，管理人员(GM、DM、PM)通常为硕士。

### 原始报告 #22 · content_issues

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1589,
  "kind": "conflicting_content",
  "knowledge_evidence": [
    {
      "knowledge_id": 1589,
      "quote": "员工学历与岗位对应：技术人员(CE、TE、EE、SE)通常为硕士或博士，值班员(OP)和检修工(MT、EL)通常为本科或大专，管理人员(GM、DM、PM)通常为硕士。"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "知识将 SE 列入“技术人员”，而 Schema 的 energy_position_dict 中 ('SE', '安全工程师', '管理') 将 SE 的 category 标为“管理”；此处代码分类不一致，按原文保留不修补。"
}
```

裁定状态：resolved；关联：未另作关联裁定；来源：user_explicit。

理由：用户指定 Schema 与知识冲突时以 Schema 为准。

内容处理：SE 的 category 采用 Schema 中的管理；不采用知识中将其归为技术人员的冲突分类。

## R022 · MYSQL:common.customer_level_dict · 知识 1564

高价值用户（核心用户/高消费用户/大客户）通常按用户累计应付金额或累计支付金额排序。SQL逻辑：ORDER BY SUM(ecommerce.orders.payable_amount) DESC。示例：SELECT c.customer_id, c.customer_name, ROUND(SUM(o.payable_amount), 2) AS total_payable FROM ecommerce.customer c JOIN ecommerce.orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.customer_name ORDER BY total_payable DESC LIMIT 10。

### 原始报告 #23 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1564,
  "knowledge_evidence": [
    {
      "knowledge_id": 1564,
      "quote": "高价值用户（核心用户/高消费用户/大客户）通常按用户累计应付金额或累计支付金额排序。"
    }
  ],
  "reason": "字典说明中有高价值用户和核心高价值用户，但字典等级依据最低成长值，本条依据累计应付或支付金额排序，未说明排序结果与会员等级的映射，不能确认同一口径。"
}
```

裁定状态：resolved；关联：reject；来源：user_explicit。

理由：用户指定以 Schema 为准；字典按成长值定义会员等级，知识按支付金额排序，不能当作同一映射。

## R023 · MYSQL:common.dict_academic_level · 知识 1589

员工学历与岗位对应：技术人员(CE、TE、EE、SE)通常为硕士或博士，值班员(OP)和检修工(MT、EL)通常为本科或大专，管理人员(GM、DM、PM)通常为硕士。

### 原始报告 #24 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1589,
  "knowledge_evidence": [
    {
      "knowledge_id": 1589,
      "quote": "技术人员(CE、TE、EE、SE)通常为硕士或博士，值班员(OP)和检修工(MT、EL)通常为本科或大专，管理人员(GM、DM、PM)通常为硕士。"
    }
  ],
  "reason": "知识提到学历层次名称（硕士/博士/本科），与 dict_academic_level.level_name 的取值有词语重合，但它描述的是能源企业员工岗位与学历对应关系，未引用 dict_academic_level，也未涉及 student.academic_level_code；缺少该字典表直接参与该规则的证据。"
}
```

裁定状态：resolved；关联：reject；来源：user_explicit。

理由：用户指出该知识属于工业能源员工学历语境，缺少教育字典的直接关联。

## R024 · MYSQL:common.dict_exam_item · 知识 1572

成绩折算规则（教育教务常用口径示例）：总评 = 平时*0.30 + 期中*0.30 + 期末*0.40。总评四舍五入保留2位。

### 原始报告 #25 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1572,
  "kind": "conflicting_content",
  "knowledge_evidence": [
    {
      "knowledge_id": 1572,
      "quote": "成绩折算规则（教育教务常用口径示例）：总评 = 平时*0.30 + 期中*0.30 + 期末*0.40。总评四舍五入保留2位。"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "知识示例权重为平时0.30、期中0.30、期末0.40；原始Schema的本表初始化默认权重分别为0.35、0.45、0.75，不能混为同一默认口径。"
}
```

### 原始报告 #26 · content_issues

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1572,
  "kind": "conflicting_content",
  "knowledge_evidence": [
    {
      "knowledge_id": 1572,
      "quote": "总评 = 平时*0.30 + 期中*0.30 + 期末*0.40"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "知识中的权重（平时0.30、期中0.30、期末0.40）与 dict_exam_item 数据中的 default_weight（平时0.35、期中0.45、期末0.75）不一致；Schema 注释又举例“平时成绩占30%”，无法在本输入内统一，按原文记录冲突。"
}
```

裁定状态：resolved；关联：未另作关联裁定；来源：user_explicit。

理由：用户指定 Schema 优先。

内容处理：默认权重采用原始 Schema；不使用知识1572的示例权重覆盖 Schema。

## R025 · MYSQL:common.dict_grade_level · 知识 1573

挂科判定规则（示例）：当总评成绩 < 60.00 视为不合格（挂科）。

### 原始报告 #27 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1573,
  "basis": "schema_supported",
  "fields": [
    "grade_level",
    "min_score",
    "max_score"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1573,
      "quote": "当总评成绩 < 60.00 视为不合格（挂科）"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "min_score INT COMMENT '最低分数'"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "max_score INT COMMENT '最高分数'"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "('F', 0, 59, 0.0);"
    }
  ],
  "qualifiers": [
    "（示例）"
  ],
  "reason": "知识给出 <60 不合格阈值；Schema 中 F 等级分数范围为 0-59，直接对应。"
}
```

### 原始报告 #28 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1573,
  "knowledge_evidence": [
    {
      "knowledge_id": 1573,
      "quote": "挂科判定规则（示例）：当总评成绩 < 60.00 视为不合格（挂科）。"
    }
  ],
  "reason": "本表有分数段、等级与绩点，但原始Schema未明示哪个等级代表不合格或挂科，且没有总评字段；仅凭F或低绩点不能确认此挂科规则适用于本表。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户确认 F 等级与挂科同义，接受分数段关联。

## R026 · MYSQL:transportation.vehicle_company · 知识 1596

县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。

### 原始报告 #29 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1596,
  "knowledge_evidence": [
    {
      "knowledge_id": 1596,
      "quote": "县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。"
    }
  ],
  "reason": "条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 7 条其他关联。

先前待审原因：用户标记为略，未给出接受或拒绝结论，保留待审。

## R027 · MYSQL:transportation.driver · 知识 1596

县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。

### 原始报告 #30 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1596,
  "knowledge_evidence": [
    {
      "knowledge_id": 1596,
      "quote": "县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。"
    }
  ],
  "reason": "条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 11 条其他关联。

先前待审原因：用户标记为略，未给出接受或拒绝结论，保留待审。

## R028 · MYSQL:transportation.driver · 知识 1773

中国驾照有效期规则：初次领证有效期为6年，第二次换证为10年，第三次为长期。可通过 issue_date 和 valid_years 计算到期日。

### 原始报告 #31 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1773,
  "kind": "incomplete_rule",
  "knowledge_evidence": [
    {
      "knowledge_id": 1773,
      "quote": "中国驾照有效期规则：初次领证有效期为6年，第二次换证为10年，第三次为长期。可通过 issue_date 和 valid_years 计算到期日。"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "本条提到第三次换证为长期，并称可用issue_date和valid_years计算到期日，但没有说明长期有效在valid_years中的表示及其到期处理。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户确认存在部分明确关联，接受已明示的领证日期、有效期片段。

内容处理：6年与10年规则可关联；长期有效在 valid_years 中的表示仍未指定，不补造编码。

## R029 · MYSQL:transportation.driver · 知识 1783

驾驶员年龄分组标准：30岁以下为青年驾驶员，30-45岁为中年驾驶员，45岁以上为老年驾驶员。。

### 原始报告 #32 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1783,
  "kind": "incomplete_rule",
  "knowledge_evidence": [
    {
      "knowledge_id": 1783,
      "quote": "驾驶员年龄分组标准：30岁以下为青年驾驶员，30-45岁为中年驾驶员，45岁以上为老年驾驶员。。"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "中年写作30-45岁，老年写作45岁以上；45岁处的区间边界未明确是否重叠，不能自行选择比较符。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户指定模糊区间默认左闭右开。

内容处理：按用户裁定：青年 age<30，中年 30<=age<45，老年 age>=45；此规则仅用于评测裁定，不改写原文。

## R030 · MYSQL:transportation.vehicle · 知识 1765

货车同义词：卡车、载货汽车。危化品车同义词：危险品运输车、罐车（仅当运输危化品时）。客车同义词：巴士、大客车、小客车（座位数≥9）。

### 原始报告 #33 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1765,
  "basis": "schema_supported",
  "fields": [
    "vehicle_type_code",
    "seat_count"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1765,
      "quote": "货车同义词：卡车、载货汽车。危化品车同义词：危险品运输车、罐车（仅当运输危化品时）。客车同义词：巴士、大客车、小客车（座位数≥9）。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE vehicle (\r\n    vehicle_id VARCHAR(20) PRIMARY KEY COMMENT '车辆唯一编号',\r\n    plate_number VARCHAR(10) NOT NULL UNIQUE COMMENT '车牌号',\r\n    owner_id VARCHAR(18) NOT NULL COMMENT '车主（驾驶员）身份证号',\r\n    vehicle_type_code VARCHAR(20) NOT NULL COMMENT '车辆类型代码',\r\n    brand VARCHAR(30) NOT NULL COMMENT '品牌',\r\n    model VARCHAR(30) NOT NULL COMMENT '型号',\r\n    manufacture_year YEAR NOT NULL COMMENT '生产年份',\r\n    load_capacity DECIMAL(8,2) COMMENT '载重(吨)',\r\n    seat_count TINYINT UNSIGNED COMMENT '座位数（客车用）',\r\n    color VARCHAR(20) COMMENT '颜色',\r\n    register_date DATE NOT NULL COMMENT '注册日期',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    insurance_expire DATE COMMENT '保险到期日',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属车辆公司ID',\r\n    INDEX idx_plate (plate_number),\r\n    INDEX idx_owner (owner_id),\r\n    INDEX idx_type (vehicle_type_code),\r\n    FOREIGN KEY (owner_id) REFERENCES driver(driver_id),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    FOREIGN KEY (vehicle_type_code) REFERENCES common.vehicle_type_dict(type_code),\r\n    FOREIGN KEY (company_id) REFERENCES vehicle_company(company_id)\r\n) ENGINE=InnoDB COMMENT='车辆登记表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "INSERT INTO common.vehicle_type_dict (type_code, type_name, category) VALUES\r\n('BUS', '客车', '客运'),\r\n('TRUCK', '货车', '货运'),\r\n('HAZMAT', '危化品车', '特种'),\r\n('VAN', '面包车', '货运'),\r\n('MINIBUS', '小型客车', '客运'),\r\n('DUMP', '自卸车', '货运'),\r\n('TANKER', '罐式车', '特种'),\r\n('REFRIGERATED', '冷藏车', '特种');"
    }
  ],
  "qualifiers": [
    "仅当运输危化品时",
    "座位数≥9"
  ],
  "reason": "本条解释货车、危化品车和客车称呼，并以座位数限制小客车；本表记录车辆类型代码和客车座位数，字典明确这些类型对象。"
}
```

### 原始报告 #38 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1765,
  "knowledge_evidence": [
    {
      "knowledge_id": 1765,
      "quote": "货车同义词：卡车、载货汽车。危化品车同义词：危险品运输车、罐车（仅当运输危化品时）。客车同义词：巴士、大客车、小客车（座位数≥9）。"
    }
  ],
  "reason": "知识定义货车/客车/危化品车同义词，可能用于解释 vehicle 的车辆类型或 vehicle_type_code，但未明确提及 vehicle 表或 vehicle_type_code，需额外映射，不能确认。"
}
```

裁定状态：resolved；关联：accept；来源：user_explicit。

理由：用户确认训练集含此问题，采纳 Codex；后续同类 Codex 肯定、Flash 未肯定时亦采纳 Codex。

## R031 · MYSQL:transportation.vehicle · 知识 1596

县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。

### 原始报告 #34 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1596,
  "knowledge_evidence": [
    {
      "knowledge_id": 1596,
      "quote": "县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。"
    }
  ],
  "reason": "条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 12 条其他关联。

先前待审原因：1596 的编码断言已由用户裁定与 Schema 冲突；该表是否仅关联未冲突片段仍未明确，且用户对同类26–27项选择略，保留待审。

内容处理：冲突规则服从 Schema；不传播被否定的编码断言。

## R032 · MYSQL:transportation.vehicle · 知识 1771

危化品车辆必须配备押运员，且押运员需持有道路危险货物运输从业资格证。

### 原始报告 #35 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1771,
  "knowledge_evidence": [
    {
      "knowledge_id": 1771,
      "quote": "危化品车辆必须配备押运员，且押运员需持有道路危险货物运输从业资格证。"
    }
  ],
  "reason": "车辆类型可涉及危化品车，但Schema没有押运员或从业资格证属性，无法核实本条要求的配备和持证约束。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：车辆表已有14条参考关联，采用较严格口径；缺少押运员及其资格属性，无法将配备与持证要求直接用于该表。

## R033 · MYSQL:transportation.vehicle · 知识 1784

危险品运输车辆需每年进行一次罐体检测，检测合格标志存储在备注字段（若有）。

### 原始报告 #36 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1784,
  "knowledge_evidence": [
    {
      "knowledge_id": 1784,
      "quote": "危险品运输车辆需每年进行一次罐体检测，检测合格标志存储在备注字段（若有）。"
    }
  ],
  "reason": "本表能表达危险品车辆类型，但无罐体检测、合格标志或备注字段；本条若有的存储说明不能确认对应本表。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：车辆表已有较多关联，采用较严格口径；Schema 无罐体检测、合格标志或备注字段，不能把若有的存储说明确认到此表。

## R034 · MYSQL:transportation.vehicle · 知识 1785

“重型货车”通常指总质量≥12吨的货车，对应载重 load_capacity ≥ 12 吨。

### 原始报告 #37 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1785,
  "kind": "conflicting_content",
  "knowledge_evidence": [
    {
      "knowledge_id": 1785,
      "quote": "“重型货车”通常指总质量≥12吨的货车，对应载重 load_capacity ≥ 12 吨。"
    },
    {
      "knowledge_id": 1762,
      "quote": "车辆载重分段规则（中国公路运输标准）：轻型车：载重 ≤ 5 吨；中型车：5 吨 < 载重 ≤ 15 吨；重型车：载重 > 15 吨。"
    }
  ],
  "related_knowledge_ids": [
    1762
  ],
  "reason": "知识1762把重型车阈值写为载重>15吨，本条通常把重型货车写为load_capacity≥12吨；货车在12至15吨区间的重型口径不同，需保留两条限定交由人审。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 12 条其他关联。

先前待审原因：1762与1785的重型载重阈值冲突，尚无 Schema 明确阈值可优先。

内容处理：用户裁定不关联本知识；原报告中的内容冲突、缺失或歧义继续保留，不代表这些内容已被修正或补全。

## R035 · MYSQL:transportation.vehicle · 知识 1762

车辆载重分段规则（中国公路运输标准）：轻型车：载重 ≤ 5 吨；中型车：5 吨 < 载重 ≤ 15 吨；重型车：载重 > 15 吨。

### 原始报告 #39 · content_issues

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1762,
  "kind": "conflicting_content",
  "knowledge_evidence": [
    {
      "knowledge_id": 1762,
      "quote": "重型车：载重 > 15 吨。"
    },
    {
      "knowledge_id": 1785,
      "quote": "“重型货车”通常指总质量≥12吨的货车，对应载重 load_capacity ≥ 12 吨。"
    }
  ],
  "related_knowledge_ids": [
    1785
  ],
  "reason": "两条知识均关联 vehicle.load_capacity，但对“重型”载重阈值给出不同限定（>15吨 与 ≥12吨），存在冲突。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 12 条其他关联。

先前待审原因：与R034同一载重阈值冲突，无法从现有依据选择12吨或15吨。

内容处理：用户裁定不关联本知识；原报告中的内容冲突、缺失或歧义继续保留，不代表这些内容已被修正或补全。

## R036 · MYSQL:transportation.shipping_company · 知识 1596

县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。

### 原始报告 #40 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1596,
  "knowledge_evidence": [
    {
      "knowledge_id": 1596,
      "quote": "县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。"
    }
  ],
  "reason": "条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 5 条其他关联。

先前待审原因：1596 的编码断言已由用户裁定与 Schema 冲突；该表是否仅关联未冲突片段仍未明确，且用户对同类26–27项选择略，保留待审。

内容处理：冲突规则服从 Schema；不传播被否定的编码断言。

## R037 · MYSQL:transportation.shipping_company · 知识 1787

驾驶员从业资格类型：普通货运、危险品运输、旅客运输。不同类型对应不同的 license_type 和公司 business_type。

### 原始报告 #41 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1787,
  "knowledge_evidence": [
    {
      "knowledge_id": 1787,
      "quote": "驾驶员从业资格类型：普通货运、危险品运输、旅客运输。不同类型对应不同的 license_type 和公司 business_type。"
    }
  ],
  "reason": "知识提到公司 business_type，但语境为驾驶员从业资格及 license_type；shipping_company 含 business_type 字段但无驾驶员关联，无法确认直接适用。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：驾驶员资格与道路运输业务语境不能仅因 business_type 同名传播到航运公司；缺少相应驾驶员关系。

## R038 · MYSQL:transportation.vessel · 知识 1793

华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。

### 原始报告 #42 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1793,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1793,
      "quote": "华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE vessel (\r\n    mmsi INT UNSIGNED NOT NULL COMMENT '船舶MMSI，9位唯一标识',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属船舶公司ID',\r\n    vessel_type SMALLINT COMMENT '船舶类型代码（参照AIS标准）',\r\n    max_load DECIMAL(10,2) COMMENT '最大荷载量（吨）',\r\n    max_speed DECIMAL(4,1) COMMENT '最大航速（节）',\r\n    endurance VARCHAR(32) COMMENT '自持力（天/海里）',\r\n    captain_name VARCHAR(32) COMMENT '船长姓名',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    UNIQUE KEY uk_mmsi (mmsi),\r\n    FOREIGN KEY (company_id) REFERENCES shipping_company(company_id) ON DELETE RESTRICT ON UPDATE CASCADE,\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    FOREIGN KEY (vessel_type) REFERENCES common.vessel_type_dict(type_code)\r\n) ENGINE=InnoDB COMMENT='船舶基础信息表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R039 · MYSQL:transportation.vessel · 知识 1799

中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。

### 原始报告 #43 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1799,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1799,
      "quote": "中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE vessel (\r\n    mmsi INT UNSIGNED NOT NULL COMMENT '船舶MMSI，9位唯一标识',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属船舶公司ID',\r\n    vessel_type SMALLINT COMMENT '船舶类型代码（参照AIS标准）',\r\n    max_load DECIMAL(10,2) COMMENT '最大荷载量（吨）',\r\n    max_speed DECIMAL(4,1) COMMENT '最大航速（节）',\r\n    endurance VARCHAR(32) COMMENT '自持力（天/海里）',\r\n    captain_name VARCHAR(32) COMMENT '船长姓名',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    UNIQUE KEY uk_mmsi (mmsi),\r\n    FOREIGN KEY (company_id) REFERENCES shipping_company(company_id) ON DELETE RESTRICT ON UPDATE CASCADE,\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    FOREIGN KEY (vessel_type) REFERENCES common.vessel_type_dict(type_code)\r\n) ENGINE=InnoDB COMMENT='船舶基础信息表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R040 · MYSQL:transportation.vessel · 知识 1800

中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。

### 原始报告 #44 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1800,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1800,
      "quote": "中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE vessel (\r\n    mmsi INT UNSIGNED NOT NULL COMMENT '船舶MMSI，9位唯一标识',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属船舶公司ID',\r\n    vessel_type SMALLINT COMMENT '船舶类型代码（参照AIS标准）',\r\n    max_load DECIMAL(10,2) COMMENT '最大荷载量（吨）',\r\n    max_speed DECIMAL(4,1) COMMENT '最大航速（节）',\r\n    endurance VARCHAR(32) COMMENT '自持力（天/海里）',\r\n    captain_name VARCHAR(32) COMMENT '船长姓名',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    UNIQUE KEY uk_mmsi (mmsi),\r\n    FOREIGN KEY (company_id) REFERENCES shipping_company(company_id) ON DELETE RESTRICT ON UPDATE CASCADE,\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    FOREIGN KEY (vessel_type) REFERENCES common.vessel_type_dict(type_code)\r\n) ENGINE=InnoDB COMMENT='船舶基础信息表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R041 · MYSQL:transportation.vessel · 知识 1596

县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。

### 原始报告 #45 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1596,
  "knowledge_evidence": [
    {
      "knowledge_id": 1596,
      "quote": "县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。"
    }
  ],
  "reason": "条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 8 条其他关联。

先前待审原因：1596 的编码断言已由用户裁定与 Schema 冲突；该表是否仅关联未冲突片段仍未明确，且用户对同类26–27项选择略，保留待审。

内容处理：冲突规则服从 Schema；不传播被否定的编码断言。

## R042 · MYSQL:finance_tax.companies · 知识 1630

企业所得税税率规则：高新技术企业适用15%，小型微利企业适用20%，其他企业适用25%。高新技术企业优先于小型微利判定。

### 原始报告 #46 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1630,
  "basis": "schema_supported",
  "fields": [
    "is_key_high_tech"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1630,
      "quote": "企业所得税税率规则：高新技术企业适用15%，小型微利企业适用20%，其他企业适用25%。高新技术企业优先于小型微利判定。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE companies (\r\n    company_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '公司唯一ID',\r\n    company_name VARCHAR(200) NOT NULL UNIQUE COMMENT '公司法定全称',\r\n    stock_code VARCHAR(20) UNIQUE COMMENT '股票代码（若上市）',\r\n    established_year YEAR COMMENT '注册/成立年份',\r\n    registered_capital DECIMAL(18,2) COMMENT '注册资本（万元）',\r\n    industry_code VARCHAR(20) COMMENT '所属行业代码',\r\n    registration_type_code VARCHAR(20) COMMENT '登记注册类型代码',\r\n    is_private BOOLEAN COMMENT '是否民营企业',\r\n    size_category_code VARCHAR(10) COMMENT '规模划型代码',\r\n    is_key_high_tech BOOLEAN DEFAULT FALSE COMMENT '是否重点扶持高新技术企业',\r\n    is_tech_advanced_service BOOLEAN DEFAULT FALSE COMMENT '是否技术先进型服务企业',\r\n\r\n    FOREIGN KEY (industry_code) REFERENCES common.dict_industry(industry_code),\r\n    FOREIGN KEY (registration_type_code) REFERENCES common.dict_registration_type(type_code),\r\n    FOREIGN KEY (size_category_code) REFERENCES common.dict_size_category(size_code)\r\n) COMMENT='公司基础信息主表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条高新技术企业的税率条件对应公司表的重点扶持高新技术企业标志；仅据该企业属性部分建立关联。"
}
```

### 原始报告 #48 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1630,
  "knowledge_evidence": [
    {
      "knowledge_id": 1630,
      "quote": "企业所得税税率规则：高新技术企业适用15%，小型微利企业适用20%，其他企业适用25%。"
    }
  ],
  "reason": "该条以“高新技术企业”等企业类型描述税率，未指名表或字段；companies.is_key_high_tech 可标识高新技术企业，但税率计算通常作用于企业所得税申报数据，无法仅凭本表确认归属。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条高新技术企业的税率条件对应公司表的重点扶持高新技术企业标志；仅据该企业属性部分建立关联。

## R043 · MYSQL:finance_tax.companies · 知识 1664

企业集中度指每个行业收入最高的n个企业占行业总收入的比例，CRn指数通过计算前n位企业数据总和与行业总数据的比值。

### 原始报告 #47 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1664,
  "basis": "schema_supported",
  "fields": [
    "company_id",
    "industry_code"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1664,
      "quote": "企业集中度指每个行业收入最高的n个企业占行业总收入的比例，CRn指数通过计算前n位企业数据总和与行业总数据的比值。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE companies (\r\n    company_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '公司唯一ID',\r\n    company_name VARCHAR(200) NOT NULL UNIQUE COMMENT '公司法定全称',\r\n    stock_code VARCHAR(20) UNIQUE COMMENT '股票代码（若上市）',\r\n    established_year YEAR COMMENT '注册/成立年份',\r\n    registered_capital DECIMAL(18,2) COMMENT '注册资本（万元）',\r\n    industry_code VARCHAR(20) COMMENT '所属行业代码',\r\n    registration_type_code VARCHAR(20) COMMENT '登记注册类型代码',\r\n    is_private BOOLEAN COMMENT '是否民营企业',\r\n    size_category_code VARCHAR(10) COMMENT '规模划型代码',\r\n    is_key_high_tech BOOLEAN DEFAULT FALSE COMMENT '是否重点扶持高新技术企业',\r\n    is_tech_advanced_service BOOLEAN DEFAULT FALSE COMMENT '是否技术先进型服务企业',\r\n\r\n    FOREIGN KEY (industry_code) REFERENCES common.dict_industry(industry_code),\r\n    FOREIGN KEY (registration_type_code) REFERENCES common.dict_registration_type(type_code),\r\n    FOREIGN KEY (size_category_code) REFERENCES common.dict_size_category(size_code)\r\n) COMMENT='公司基础信息主表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条按企业所属行业计算集中度，公司主表直接记录企业标识及所属行业；依据限于行业分组对象。"
}
```

### 原始报告 #49 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1664,
  "knowledge_evidence": [
    {
      "knowledge_id": 1664,
      "quote": "企业集中度指每个行业收入最高的n个企业占行业总收入的比例"
    }
  ],
  "reason": "该条涉及“行业”和“企业收入”，companies 仅有 industry_code 而无收入字段，需结合其他表才能确定口径，无法确认与本表的直接关联。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条按企业所属行业计算集中度，公司主表直接记录企业标识及所属行业；依据限于行业分组对象。

## R044 · MYSQL:finance_tax.stocks · 知识 1638

净资产收益率(ROE)计算公式：(净利润 / 净资产) × 100%。其中净利润 = total_assets - total_liabilities，净资产 = total_assets，本库中以每股收益/每股净资产替代计算。单位：%。

### 原始报告 #50 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1638,
  "knowledge_evidence": [
    {
      "knowledge_id": 1638,
      "quote": "净资产收益率(ROE)计算公式：(净利润 / 净资产) × 100%。其中净利润 = total_assets - total_liabilities，净资产 = total_assets，本库中以每股收益/每股净资产替代计算。单位：%。"
    }
  ],
  "reason": "本条提及以每股收益/每股净资产替代ROE，但股票表没有这两个指标；本条未给出从股票表股本、价格推导二者的规则，不能借用相邻知识补全。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：股票表已有14条关联；Schema 无每股收益与每股净资产，知识亦未提供由股票字段得到两指标的规则。

## R045 · MYSQL:finance_tax.company_financials · 知识 1625

市净率(P/B)计算公式：股价 / 每股净资产，股价可使用最近收盘价。

### 原始报告 #51 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1625,
  "knowledge_evidence": [
    {
      "knowledge_id": 1625,
      "quote": "市净率(P/B)计算公式：股价 / 每股净资产，股价可使用最近收盘价。"
    }
  ],
  "reason": "本条市净率需要每股净资产，但本表只有总资产且没有每股净资产或总股本；本条未给出换算规则，不能使用未被显式引用的知识1624补全。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：财务表已有14条关联；只有总资产，没有股价、每股净资产或股本，知识未指定本表为来源，不沿未明示关系传播。

## R046 · MYSQL:finance_tax.company_financials · 知识 1642

资产周转率计算公式：收入总额 / 资产总额，反映企业资产运营效率。单位：倍。

### 原始报告 #52 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1642,
  "knowledge_evidence": [
    {
      "knowledge_id": 1642,
      "quote": "资产周转率计算公式：收入总额 / 资产总额，反映企业资产运营效率。单位：倍。"
    }
  ],
  "reason": "本表有财务总资产，但没有收入总额；条目也未指定资产来源。另有年度申报表同时记录收入与季度平均资产，不能仅凭总资产词语把本表作为已确认来源。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：财务表已有14条关联；没有收入总额，知识未指定总资产来源，不仅凭单个总资产字段确认。

## R047 · MYSQL:finance_tax.corporate_income_tax_returns · 知识 1630

企业所得税税率规则：高新技术企业适用15%，小型微利企业适用20%，其他企业适用25%。高新技术企业优先于小型微利判定。

### 原始报告 #53 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1630,
  "basis": "schema_supported",
  "fields": [],
  "knowledge_evidence": [
    {
      "knowledge_id": 1630,
      "quote": "企业所得税税率规则：高新技术企业适用15%，小型微利企业适用20%，其他企业适用25%。高新技术企业优先于小型微利判定。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "COMMENT='企业所得税年度申报信息表'"
    }
  ],
  "qualifiers": [
    "高新技术企业优先于小型微利判定"
  ],
  "reason": "本表为企业所得税年度申报信息表，税率规则用于其企业所得税计算。"
}
```

### 原始报告 #59 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1630,
  "knowledge_evidence": [
    {
      "knowledge_id": 1630,
      "quote": "企业所得税税率规则：高新技术企业适用15%，小型微利企业适用20%，其他企业适用25%。高新技术企业优先于小型微利判定。"
    }
  ],
  "reason": "条目给出高新技术、小型微利和其他企业的税率；本表没有这些企业类别或税率字段，本条也未提供由本表现有字段判定小型微利的条件，需补充明确适用依据。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：申报表已有较多关联；无企业资格和税率字段，该知识未提供本表可直接判断资格的规则，采用严格口径。

## R048 · MYSQL:finance_tax.corporate_income_tax_returns · 知识 1631

企业所得税额计算公式：应纳税所得额 × 适用税率，单位：万元。

### 原始报告 #54 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1631,
  "basis": "schema_supported",
  "fields": [],
  "knowledge_evidence": [
    {
      "knowledge_id": 1631,
      "quote": "企业所得税额计算公式：应纳税所得额 × 适用税率，单位：万元。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "COMMENT='企业所得税年度申报信息表'"
    }
  ],
  "qualifiers": [],
  "reason": "本表为企业所得税年度申报信息表，税额计算规则直接适用于申报数据。"
}
```

### 原始报告 #60 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1631,
  "knowledge_evidence": [
    {
      "knowledge_id": 1631,
      "quote": "企业所得税额计算公式：应纳税所得额 × 适用税率，单位：万元。"
    }
  ],
  "reason": "条目公式的应纳税所得额与适用税率都不是本表字段，本条未解释如何由申报属性取得二者；不能借用邻近但未显式引用的知识补全。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：申报表已有较多关联；知识公式的应纳税所得额与税率均非直接字段，未给出换算步骤，不以所得税主题相同确认关联。

## R049 · MYSQL:finance_tax.corporate_income_tax_returns · 知识 1654

一般企业所得税税率为25%。

### 原始报告 #55 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1654,
  "basis": "schema_supported",
  "fields": [],
  "knowledge_evidence": [
    {
      "knowledge_id": 1654,
      "quote": "一般企业所得税税率为25%。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "COMMENT='企业所得税年度申报信息表'"
    }
  ],
  "qualifiers": [],
  "reason": "一般企业所得税税率用于本表企业所得税计算。"
}
```

### 原始报告 #62 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1654,
  "knowledge_evidence": [
    {
      "knowledge_id": 1654,
      "quote": "一般企业所得税税率为25%。"
    }
  ],
  "reason": "条目仅给出一般企业税率，没有指定申报表或可核对的税率字段；Schema也没有一般企业判定属性，保留其对本表计算适用性待核。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：申报表已有较多关联；没有一般企业类别及税率字段，知识仅给出通用税率，缺少直接适用依据。

## R050 · MYSQL:finance_tax.corporate_income_tax_returns · 知识 1657

符合条件的小型微利企业，年应纳税所得额不超过100万元的部分，减按25%计入应纳税所得额，按20%税率缴纳企业所得税（实际税负5%）。本库按简化规则直接使用20%税率。

### 原始报告 #56 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1657,
  "basis": "schema_supported",
  "fields": [],
  "knowledge_evidence": [
    {
      "knowledge_id": 1657,
      "quote": "符合条件的小型微利企业，年应纳税所得额不超过100万元的部分，减按25%计入应纳税所得额，按20%税率缴纳企业所得税（实际税负5%）。本库按简化规则直接使用20%税率。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "COMMENT='企业所得税年度申报信息表'"
    }
  ],
  "qualifiers": [
    "年应纳税所得额不超过100万元的部分",
    "本库按简化规则直接使用20%税率"
  ],
  "reason": "小型微利企业税率规则适用于本表年度申报数据。"
}
```

### 原始报告 #64 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1657,
  "knowledge_evidence": [
    {
      "knowledge_id": 1657,
      "quote": "符合条件的小型微利企业，年应纳税所得额不超过100万元的部分，减按25%计入应纳税所得额，按20%税率缴纳企业所得税（实际税负5%）。本库按简化规则直接使用20%税率。"
    }
  ],
  "reason": "条目描述小型微利企业应纳税所得额与税率，但未指明本表、未提供由本表字段判定资格或计算应纳税所得额的规则；本表无这些直接属性。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：申报表已有较多关联；知识涉及资格、应纳税所得额和税率，Schema 缺少直接字段或该条所需的判定步骤。

## R051 · MYSQL:finance_tax.corporate_income_tax_returns · 知识 1664

企业集中度指每个行业收入最高的n个企业占行业总收入的比例，CRn指数通过计算前n位企业数据总和与行业总数据的比值。

### 原始报告 #57 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1664,
  "basis": "schema_supported",
  "fields": [
    "company_id",
    "revenue"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1664,
      "quote": "企业集中度指每个行业收入最高的n个企业占行业总收入的比例，CRn指数通过计算前n位企业数据总和与行业总数据的比值。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE corporate_income_tax_returns (\r\n    return_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '申报ID',\r\n    company_id BIGINT NOT NULL COMMENT '关联公司ID',\r\n    tax_year YEAR NOT NULL COMMENT '纳税年度',\r\n    revenue DECIMAL(18,2) NOT NULL COMMENT '收入总额（万元）',\r\n    non_taxable_income DECIMAL(18,2) DEFAULT 0 COMMENT '不征税收入与免税收入（万元）',\r\n    deductions DECIMAL(18,2) NOT NULL COMMENT '扣除金额（万元）',\r\n    prior_year_losses DECIMAL(18,2) DEFAULT 0 COMMENT '允许弥补的以前年度亏损（万元）',\r\n    building_asset_value DECIMAL(18,2) COMMENT '房屋建筑物资产原值（万元）',\r\n    employee_count INT COMMENT '从业人数（全年季度平均值）',\r\n    total_assets DECIMAL(18,2) COMMENT '资产总额（万元，全年季度平均值）',\r\n    is_restricted_industry BOOLEAN DEFAULT FALSE COMMENT '是否从事国家限制或禁止行业',\r\n\r\n    FOREIGN KEY (company_id) REFERENCES companies(company_id),\r\n    UNIQUE KEY uk_company_year (company_id, tax_year)\r\n) COMMENT='企业所得税年度申报信息表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条企业行业集中度以企业收入排序及汇总，申报表直接记录公司标识与收入总额；关联依据为企业收入部分。"
}
```

### 原始报告 #68 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1664,
  "knowledge_evidence": [
    {
      "knowledge_id": 1664,
      "quote": "企业集中度指每个行业收入最高的n个企业占行业总收入的比例，CRn指数通过计算前n位企业数据总和与行业总数据的比值。"
    }
  ],
  "reason": "使用收入数据但还依赖行业字段，本表只有revenue，行业信息在companies表，无法仅凭本表确认直接适用。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条企业行业集中度以企业收入排序及汇总，申报表直接记录公司标识与收入总额；关联依据为企业收入部分。

## R052 · MYSQL:finance_tax.corporate_income_tax_returns · 知识 1624

每股净资产(BPS)计算公式：(total_assets * 10000) / total_shares，其中总资产由万元转换为元。

### 原始报告 #58 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1624,
  "knowledge_evidence": [
    {
      "knowledge_id": 1624,
      "quote": "每股净资产(BPS)计算公式：(total_assets * 10000) / total_shares，其中总资产由万元转换为元。"
    }
  ],
  "reason": "本表也有万元资产总额，但其口径为全年季度平均；每股净资产条目没有指定资产来源，另有财务总资产表，不能仅凭total_assets同名确认使用申报平均资产。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：申报表的资产是全年季度平均值，不能视为知识BPS公式所需资产来源；以 Schema 口径为准。

## R053 · MYSQL:finance_tax.corporate_income_tax_returns · 知识 1652

高新技术企业认定资格由companies.is_key_high_tech字段标识，若为TRUE则适用15%优惠税率，相比普通税率25%可节省10%的应纳税额。

### 原始报告 #61 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1652,
  "knowledge_evidence": [
    {
      "knowledge_id": 1652,
      "quote": "高新技术企业认定资格由companies.is_key_high_tech字段标识，若为TRUE则适用15%优惠税率，相比普通税率25%可节省10%的应纳税额。"
    }
  ],
  "reason": "本条明确引用companies.is_key_high_tech解释资格和税率，但本表没有该资格或税率属性；仅可通过公司外键连接不足以确认归属。"
}
```

### 原始报告 #66 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1652,
  "knowledge_evidence": [
    {
      "knowledge_id": 1652,
      "quote": "高新技术企业认定资格由companies.is_key_high_tech字段标识"
    }
  ],
  "reason": "涉及企业所得税税率判定所需的高新技术企业资格，但资格字段在companies表，本表没有该字段，无法确认直接适用。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：知识明确引用 companies.is_key_high_tech，归属公司表；申报表无该属性，不沿外键传播。

## R054 · MYSQL:finance_tax.corporate_income_tax_returns · 知识 1656

技术先进型服务企业可享受企业所得税优惠税率15%，与高新技术企业待遇相同。

### 原始报告 #63 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1656,
  "knowledge_evidence": [
    {
      "knowledge_id": 1656,
      "quote": "技术先进型服务企业可享受企业所得税优惠税率15%，与高新技术企业待遇相同。"
    }
  ],
  "reason": "本条优惠税率依赖技术先进型服务企业资格，本表没有该资格或税率属性，不能仅沿公司外键传播。"
}
```

### 原始报告 #67 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1656,
  "knowledge_evidence": [
    {
      "knowledge_id": 1656,
      "quote": "技术先进型服务企业可享受企业所得税优惠税率15%，与高新技术企业待遇相同。"
    }
  ],
  "reason": "涉及企业所得税优惠税率，但目标表没有技术先进型服务企业标识字段，需依赖其他表，无法确认直接适用。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：申报表没有技术先进型服务企业资格与税率属性，不能把行业税率知识直接传播到该表。

## R055 · MYSQL:finance_tax.corporate_income_tax_returns · 知识 1653

小型微利企业判定基于年度申报数据，满足条件则适用20%优惠税率。判定条件见知识108。

### 原始报告 #65 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1653,
  "kind": "missing_reference",
  "knowledge_evidence": [
    {
      "knowledge_id": 1653,
      "quote": "小型微利企业判定基于年度申报数据，满足条件则适用20%优惠税率。判定条件见知识108。"
    }
  ],
  "related_knowledge_ids": [
    108
  ],
  "reason": "本条指向知识108，但完整247条输入没有该ID，无法核对其所称判定条件；不能用内容相似的其他知识替换。"
}
```

### 原始报告 #69 · content_issues

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1653,
  "kind": "missing_reference",
  "knowledge_evidence": [
    {
      "knowledge_id": 1653,
      "quote": "判定条件见知识108。"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "引用的知识108不在本输入的知识ID范围内，无法核对具体判定条件。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 16 条其他关联。

先前待审原因：知识108缺失，Schema优先不能补足被引用的判定条件。

内容处理：用户裁定不关联本知识；原报告中的内容冲突、缺失或歧义继续保留，不代表这些内容已被修正或补全。

## R056 · MYSQL:energy.energy_company · 知识 1587

“五大发电集团”指：华能国际(EC003)、大唐发电(EC004)、华电集团(EC005)、国家电投(EC006)、国家能源集团(EC009)。“两网”指：国家电网(EC001、EC020-EC022)、南方电网(EC002、EC023)。

### 原始报告 #70 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1587,
  "basis": "schema_supported",
  "fields": [
    "company_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1587,
      "quote": "“五大发电集团”指：华能国际(EC003)、大唐发电(EC004)、华电集团(EC005)、国家电投(EC006)、国家能源集团(EC009)。“两网”指：国家电网(EC001、EC020-EC022)、南方电网(EC002、EC023)。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "company_id VARCHAR(20) PRIMARY KEY COMMENT '企业编号'"
    }
  ],
  "qualifiers": [],
  "reason": "知识用企业编号列举能源集团，本表 company_id 可对应这些编号。"
}
```

### 原始报告 #74 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1587,
  "knowledge_evidence": [
    {
      "knowledge_id": 1587,
      "quote": "“五大发电集团”指：华能国际(EC003)、大唐发电(EC004)、华电集团(EC005)、国家电投(EC006)、国家能源集团(EC009)。“两网”指：国家电网(EC001、EC020-EC022)、南方电网(EC002、EC023)。"
    }
  ],
  "reason": "本条列出发电集团和电网企业名称及EC代码，但未明确表或字段；原始Schema没有这些企业实例、代码约定或集团归属属性，不能仅以能源行业推定对应记录。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：能源公司表关联相对有限，采用较宽口径；知识明确列举能源企业名称和EC编号，对应公司名称与公司ID含义。仅认可名称及编号筛选，不声称 Schema 存在这些实例。

## R057 · MYSQL:energy.energy_company · 知识 1793

华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。

### 原始报告 #71 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1793,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1793,
      "quote": "华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE energy_company (\r\n    company_id VARCHAR(20) PRIMARY KEY COMMENT '企业编号',\r\n    company_name VARCHAR(100) NOT NULL COMMENT '企业名称',\r\n    business_type VARCHAR(50) NOT NULL COMMENT '经营类型',\r\n    establish_date DATE COMMENT '成立日期',\r\n    legal_person VARCHAR(50) COMMENT '法人代表',\r\n    contact_phone VARCHAR(20) COMMENT '联系电话',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    staff_count INT COMMENT '员工总数',\r\n    status ENUM('运营','停业','注销') DEFAULT '运营' COMMENT '经营状态',\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id)\r\n) ENGINE=InnoDB COMMENT='能源企业信息表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R058 · MYSQL:energy.energy_company · 知识 1799

中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。

### 原始报告 #72 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1799,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1799,
      "quote": "中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE energy_company (\r\n    company_id VARCHAR(20) PRIMARY KEY COMMENT '企业编号',\r\n    company_name VARCHAR(100) NOT NULL COMMENT '企业名称',\r\n    business_type VARCHAR(50) NOT NULL COMMENT '经营类型',\r\n    establish_date DATE COMMENT '成立日期',\r\n    legal_person VARCHAR(50) COMMENT '法人代表',\r\n    contact_phone VARCHAR(20) COMMENT '联系电话',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    staff_count INT COMMENT '员工总数',\r\n    status ENUM('运营','停业','注销') DEFAULT '运营' COMMENT '经营状态',\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id)\r\n) ENGINE=InnoDB COMMENT='能源企业信息表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R059 · MYSQL:energy.energy_company · 知识 1800

中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。

### 原始报告 #73 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1800,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1800,
      "quote": "中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE energy_company (\r\n    company_id VARCHAR(20) PRIMARY KEY COMMENT '企业编号',\r\n    company_name VARCHAR(100) NOT NULL COMMENT '企业名称',\r\n    business_type VARCHAR(50) NOT NULL COMMENT '经营类型',\r\n    establish_date DATE COMMENT '成立日期',\r\n    legal_person VARCHAR(50) COMMENT '法人代表',\r\n    contact_phone VARCHAR(20) COMMENT '联系电话',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    staff_count INT COMMENT '员工总数',\r\n    status ENUM('运营','停业','注销') DEFAULT '运营' COMMENT '经营状态',\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id)\r\n) ENGINE=InnoDB COMMENT='能源企业信息表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R060 · MYSQL:energy.energy_company · 知识 1596

县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。

### 原始报告 #75 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1596,
  "knowledge_evidence": [
    {
      "knowledge_id": 1596,
      "quote": "县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。"
    }
  ],
  "reason": "条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 9 条其他关联。

先前待审原因：1596 的编码断言已由用户裁定与 Schema 冲突；该表是否仅关联未冲突片段仍未明确，且用户对同类26–27项选择略，保留待审。

内容处理：冲突规则服从 Schema；不传播被否定的编码断言。

## R061 · MYSQL:energy.energy_station · 知识 1602

年利用小时数用于衡量发电场站利用效率，通用高效判断阈值为年利用小时数大于3000小时。

### 原始报告 #76 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1602,
  "basis": "schema_supported",
  "fields": [
    "annual_generation",
    "installed_capacity"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1602,
      "quote": "年利用小时数用于衡量发电场站利用效率，通用高效判断阈值为年利用小时数大于3000小时。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "annual_generation DECIMAL(12,2) COMMENT '年发电量(万kWh)'"
    },
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "installed_capacity DECIMAL(12,2) COMMENT '装机容量(MW)'"
    }
  ],
  "qualifiers": [
    "通用高效判断阈值为年利用小时数大于3000小时"
  ],
  "reason": "知识说明年利用小时数用于衡量发电场站效率，本表含计算字段。"
}
```

### 原始报告 #81 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1602,
  "knowledge_evidence": [
    {
      "knowledge_id": 1602,
      "quote": "年利用小时数用于衡量发电场站利用效率，通用高效判断阈值为年利用小时数大于3000小时。"
    }
  ],
  "reason": "本条以年利用小时数判定高效，但Schema没有该指标字段；本条未给出由年发电量和装机容量取得年利用小时数的公式，不能使用未显式引用的相邻条目补全。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：能源场站知识直接说明该类场站的效率指标；接受年利用小时数阈值的适用关系，不将年发电量当成年利用小时数，不补写换算公式。

## R062 · MYSQL:energy.energy_station · 知识 1793

华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。

### 原始报告 #77 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1793,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1793,
      "quote": "华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE energy_station (\r\n    station_id VARCHAR(20) PRIMARY KEY COMMENT '场站编号',\r\n    station_name VARCHAR(100) NOT NULL COMMENT '场站名称',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属企业编号',\r\n    station_type_code VARCHAR(10) NOT NULL COMMENT '场站类型代码',\r\n    energy_type_code VARCHAR(10) NOT NULL COMMENT '能源类型代码',\r\n    installed_capacity DECIMAL(12,2) COMMENT '装机容量(MW)',\r\n    annual_generation DECIMAL(12,2) COMMENT '年发电量(万kWh)',\r\n    grid_connect_date DATE COMMENT '并网日期',\r\n    area_id CHAR(6) NOT NULL COMMENT '所在地区划代码',\r\n    status ENUM('运行','在建','停机','退役') DEFAULT '运行' COMMENT '运行状态',\r\n    FOREIGN KEY (company_id) REFERENCES energy_company(company_id),\r\n    FOREIGN KEY (station_type_code) REFERENCES common.station_type_dict(type_code),\r\n    FOREIGN KEY (energy_type_code) REFERENCES common.energy_type_dict(type_code),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id)\r\n) ENGINE=InnoDB COMMENT='能源场站表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R063 · MYSQL:energy.energy_station · 知识 1799

中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。

### 原始报告 #78 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1799,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1799,
      "quote": "中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE energy_station (\r\n    station_id VARCHAR(20) PRIMARY KEY COMMENT '场站编号',\r\n    station_name VARCHAR(100) NOT NULL COMMENT '场站名称',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属企业编号',\r\n    station_type_code VARCHAR(10) NOT NULL COMMENT '场站类型代码',\r\n    energy_type_code VARCHAR(10) NOT NULL COMMENT '能源类型代码',\r\n    installed_capacity DECIMAL(12,2) COMMENT '装机容量(MW)',\r\n    annual_generation DECIMAL(12,2) COMMENT '年发电量(万kWh)',\r\n    grid_connect_date DATE COMMENT '并网日期',\r\n    area_id CHAR(6) NOT NULL COMMENT '所在地区划代码',\r\n    status ENUM('运行','在建','停机','退役') DEFAULT '运行' COMMENT '运行状态',\r\n    FOREIGN KEY (company_id) REFERENCES energy_company(company_id),\r\n    FOREIGN KEY (station_type_code) REFERENCES common.station_type_dict(type_code),\r\n    FOREIGN KEY (energy_type_code) REFERENCES common.energy_type_dict(type_code),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id)\r\n) ENGINE=InnoDB COMMENT='能源场站表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R064 · MYSQL:energy.energy_station · 知识 1800

中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。

### 原始报告 #79 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1800,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1800,
      "quote": "中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE energy_station (\r\n    station_id VARCHAR(20) PRIMARY KEY COMMENT '场站编号',\r\n    station_name VARCHAR(100) NOT NULL COMMENT '场站名称',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属企业编号',\r\n    station_type_code VARCHAR(10) NOT NULL COMMENT '场站类型代码',\r\n    energy_type_code VARCHAR(10) NOT NULL COMMENT '能源类型代码',\r\n    installed_capacity DECIMAL(12,2) COMMENT '装机容量(MW)',\r\n    annual_generation DECIMAL(12,2) COMMENT '年发电量(万kWh)',\r\n    grid_connect_date DATE COMMENT '并网日期',\r\n    area_id CHAR(6) NOT NULL COMMENT '所在地区划代码',\r\n    status ENUM('运行','在建','停机','退役') DEFAULT '运行' COMMENT '运行状态',\r\n    FOREIGN KEY (company_id) REFERENCES energy_company(company_id),\r\n    FOREIGN KEY (station_type_code) REFERENCES common.station_type_dict(type_code),\r\n    FOREIGN KEY (energy_type_code) REFERENCES common.energy_type_dict(type_code),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id)\r\n) ENGINE=InnoDB COMMENT='能源场站表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R065 · MYSQL:energy.energy_station · 知识 1596

县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。

### 原始报告 #80 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1596,
  "knowledge_evidence": [
    {
      "knowledge_id": 1596,
      "quote": "县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。"
    }
  ],
  "reason": "条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 16 条其他关联。

先前待审原因：1596 的编码断言已由用户裁定与 Schema 冲突；该表是否仅关联未冲突片段仍未明确，且用户对同类26–27项选择略，保留待审。

内容处理：冲突规则服从 Schema；不传播被否定的编码断言。

## R066 · MYSQL:energy.supply_area · 知识 1793

华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。

### 原始报告 #82 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1793,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1793,
      "quote": "华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE supply_area (\r\n    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '供电企业编号',\r\n    area_id CHAR(6) NOT NULL COMMENT '供电区域代码',\r\n    supply_level VARCHAR(10) COMMENT '供电等级',\r\n    household_count INT COMMENT '供电户数',\r\n    annual_supply DECIMAL(12,2) COMMENT '年供电量(万kWh)',\r\n    FOREIGN KEY (company_id) REFERENCES energy_company(company_id),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    UNIQUE KEY uk_company_area (company_id, area_id)\r\n) ENGINE=InnoDB COMMENT='供电区域表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R067 · MYSQL:energy.supply_area · 知识 1799

中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。

### 原始报告 #83 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1799,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1799,
      "quote": "中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE supply_area (\r\n    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '供电企业编号',\r\n    area_id CHAR(6) NOT NULL COMMENT '供电区域代码',\r\n    supply_level VARCHAR(10) COMMENT '供电等级',\r\n    household_count INT COMMENT '供电户数',\r\n    annual_supply DECIMAL(12,2) COMMENT '年供电量(万kWh)',\r\n    FOREIGN KEY (company_id) REFERENCES energy_company(company_id),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    UNIQUE KEY uk_company_area (company_id, area_id)\r\n) ENGINE=InnoDB COMMENT='供电区域表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R068 · MYSQL:energy.supply_area · 知识 1800

中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。

### 原始报告 #84 · association_disagreement

Codex：接受关联。

Deepseek Flash：未输出肯定关联（不等于明确拒绝）。

Codex 原始审计：

```json
{
  "knowledge_id": 1800,
  "basis": "schema_supported",
  "fields": [
    "area_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1800,
      "quote": "中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "CREATE TABLE supply_area (\r\n    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '供电企业编号',\r\n    area_id CHAR(6) NOT NULL COMMENT '供电区域代码',\r\n    supply_level VARCHAR(10) COMMENT '供电等级',\r\n    household_count INT COMMENT '供电户数',\r\n    annual_supply DECIMAL(12,2) COMMENT '年供电量(万kWh)',\r\n    FOREIGN KEY (company_id) REFERENCES energy_company(company_id),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    UNIQUE KEY uk_company_area (company_id, area_id)\r\n) ENGINE=InnoDB COMMENT='供电区域表';"
    },
    {
      "source_file": "data/赛题8/Schema/commom_schema.txt",
      "quote": "CREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';"
    }
  ],
  "qualifiers": [],
  "reason": "本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。"
}
```

裁定状态：resolved；关联：accept；来源：user_rule。

理由：按用户后续规则：Codex 接受而 Flash 未输出肯定关联，采纳 Codex。依据：本条明确给出行政区划area_id的省级过滤表达式；本表以area_id记录行政区划并引用统一行政区划表，支持该查询条件。

## R069 · MYSQL:energy.supply_area · 知识 1596

县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。

### 原始报告 #85 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1596,
  "knowledge_evidence": [
    {
      "knowledge_id": 1596,
      "quote": "县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。"
    }
  ],
  "reason": "条目描述县级市、地级市及省直管县的代码特征，但未明示使用本表area_id；Schema仅说明区划代码，没有县级市或地级市判别属性，保留代码口径适用范围待核。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 6 条其他关联。

先前待审原因：1596 的编码断言已由用户裁定与 Schema 冲突；该表是否仅关联未冲突片段仍未明确，且用户对同类26–27项选择略，保留待审。

内容处理：冲突规则服从 Schema；不传播被否定的编码断言。

## R070 · MYSQL:education_2024.student · 知识 1579

总评折算总分：同一学生跨多门课把总评相加

### 原始报告 #86 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1579,
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "总评折算总分：同一学生跨多门课把总评相加"
    }
  ],
  "reason": "条目涉及同一学生的跨课程总评，但学生表没有总评或成绩属性；不能仅沿选课、成绩关系把计算规则归入学生表。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：学生表虽无肯定关联，放宽仍需字段意义支持；跨课程总评求和不是学生属性，Schema 没有成绩，不仅凭学生二字关联。

## R071 · MYSQL:education_2024.course · 知识 1579

总评折算总分：同一学生跨多门课把总评相加

### 原始报告 #87 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1579,
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "总评折算总分：同一学生跨多门课把总评相加"
    }
  ],
  "reason": "条目涉及多门课程的总评求和，但课程表没有总评属性；尚缺该规则直接解释课程表字段或操作的证据。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：课程表虽无肯定关联，仍没有总评字段或该知识直接解释的课程属性，不仅凭课程二字传播。

## R072 · MYSQL:education_2024.enrollment · 知识 1579

总评折算总分：同一学生跨多门课把总评相加

### 原始报告 #88 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1579,
  "basis": "schema_supported",
  "fields": [
    "student_id",
    "course_id"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "同一学生跨多门课把总评相加"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "student_id        INT NOT NULL,"
    },
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "course_id         INT NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识按同一学生跨课程汇总总评；Schema 中该表含 student_id 和 course_id，可标识学生选课关系。"
}
```

### 原始报告 #89 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1579,
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "总评折算总分：同一学生跨多门课把总评相加"
    }
  ],
  "reason": "选课表提供学生与课程的粒度线索，但没有总评；本条未说明总评来源，也未显式引用其他总评计算知识。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：选课表关联较少，按宽口径接受 student_id、course_id 提供跨课程按学生汇总的粒度关系；不声称该表存储总评。

## R073 · MYSQL:education_2024.enrollment · 知识 1575

选课退课规则（示例）：enrollment.is_withdraw=1 的记录视为已退课，不计入成绩统计与排名。

### 原始报告 #90 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1575,
  "kind": "ambiguous_reference",
  "knowledge_evidence": [
    {
      "knowledge_id": 1575,
      "quote": "enrollment.is_withdraw=1 的记录视为已退课，不计入成绩统计与排名。"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "enrollment.is_withdraw 未注明数据库，完整目录中 education_2024、education_2025 均有该表字段；关联按各自结构支持记录，不能声称短引用唯一指定了当前库。"
}
```

### 原始报告 #91 · content_issues

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1575,
  "kind": "ambiguous_reference",
  "knowledge_evidence": [
    {
      "knowledge_id": 1575,
      "quote": "enrollment.is_withdraw=1 的记录视为已退课"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "知识仅写 enrollment.is_withdraw，完整目录中 education_2024 与 education_2025 均存在同结构 enrollment 表，原文无法唯一定位到本表；主结果按 Schema 支持记录。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 2 条其他关联。

先前待审原因：同名 enrollment 在两个教育库存在，Schema 无法确定原文唯一归属；是否双库适用仍需裁定。

内容处理：用户裁定不关联本知识；原报告中的内容冲突、缺失或歧义继续保留，不代表这些内容已被修正或补全。

## R074 · MYSQL:education_2024.exam_score · 知识 1573

挂科判定规则（示例）：当总评成绩 < 60.00 视为不合格（挂科）。

### 原始报告 #92 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1573,
  "basis": "schema_supported",
  "fields": [
    "score"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1573,
      "quote": "当总评成绩 < 60.00 视为不合格（挂科）"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "score             DECIMAL(5,2),"
    }
  ],
  "qualifiers": [
    "（示例）"
  ],
  "reason": "知识以总评成绩判定挂科；Schema 中该表含 score 字段。"
}
```

### 原始报告 #96 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1573,
  "knowledge_evidence": [
    {
      "knowledge_id": 1573,
      "quote": "挂科判定规则（示例）：当总评成绩 < 60.00 视为不合格（挂科）。"
    }
  ],
  "reason": "条目针对总评成绩判定挂科，而原始表保存 exam_item、score 明细，未注明 score 为总评；本条未明确引用总评折算规则。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：成绩表关联较少，按宽口径接受挂科阈值对成绩业务的适用关系；score 为考试项目明细，不能逐行直接等同总评。

## R075 · MYSQL:education_2024.exam_score · 知识 1574

学分绩（GPA/绩点）示例映射：总评>=90 为绩点 4.0；80-89 为 3.0；70-79 为 2.0；60-69 为 1.0；<60 为 0.0。

### 原始报告 #93 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1574,
  "basis": "schema_supported",
  "fields": [
    "score"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1574,
      "quote": "总评>=90 为绩点 4.0；80-89 为 3.0；70-79 为 2.0；60-69 为 1.0；<60 为 0.0。"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "score             DECIMAL(5,2),"
    }
  ],
  "qualifiers": [
    "示例映射"
  ],
  "reason": "知识按总评分数映射绩点；Schema 中该表含 score 字段。"
}
```

### 原始报告 #97 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1574,
  "knowledge_evidence": [
    {
      "knowledge_id": 1574,
      "quote": "学分绩（GPA/绩点）示例映射：总评>=90 为绩点 4.0；80-89 为 3.0；70-79 为 2.0；60-69 为 1.0；<60 为 0.0。"
    }
  ],
  "reason": "条目把总评映射为绩点，成绩表未存储总评或绩点，也未说明哪一考试项目代表总评；不能自行补入折算步骤。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：成绩表关联较少，接受绩点映射对成绩业务的适用关系；仅在取得总评后应用，不把明细score直接当总评。

## R076 · MYSQL:education_2024.exam_score · 知识 1575

选课退课规则（示例）：enrollment.is_withdraw=1 的记录视为已退课，不计入成绩统计与排名。

### 原始报告 #94 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1575,
  "basis": "schema_supported",
  "fields": [
    "enrollment_id",
    "score"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1575,
      "quote": "不计入成绩统计与排名"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "enrollment_id     INT NOT NULL,"
    },
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "score             DECIMAL(5,2),"
    }
  ],
  "qualifiers": [
    "（示例）"
  ],
  "reason": "知识规定退课记录不计入成绩统计与排名；Schema exam_score 通过 enrollment_id 关联选课并以 score 记录成绩。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：知识直接规定成绩统计排除退课记录；exam_score 通过 enrollment_id 关联选课，支持明确的统计过滤关系。

## R077 · MYSQL:education_2024.exam_score · 知识 1579

总评折算总分：同一学生跨多门课把总评相加

### 原始报告 #95 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1579,
  "basis": "schema_supported",
  "fields": [
    "enrollment_id",
    "score"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "同一学生跨多门课把总评相加"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "enrollment_id     INT NOT NULL,"
    },
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "score             DECIMAL(5,2),"
    }
  ],
  "qualifiers": [],
  "reason": "知识按学生跨课程汇总总评；Schema exam_score 含 score，并通过 enrollment_id 关联选课。"
}
```

### 原始报告 #98 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1579,
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "总评折算总分：同一学生跨多门课把总评相加"
    }
  ],
  "reason": "成绩明细具有分数及选课关联，但本条未定义总评来源和跨课程聚合的直接口径；不能从未显式引用的其他知识补齐。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：成绩表关联较少，接受跨课程总评求和与成绩来源的部分明确关联；总评口径不得自行补写，亦不直接对所有考试明细求和。

## R078 · MYSQL:education_2024.exam_score · 知识 1577

中位数：窗口函数按分值排序取中间行

### 原始报告 #99 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1577,
  "knowledge_evidence": [
    {
      "knowledge_id": 1577,
      "quote": "中位数：窗口函数按分值排序取中间行"
    }
  ],
  "reason": "知识仅描述通用中位数与窗口函数，未指明分值字段或教育表；无法确认是否直接对应本表 score。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：成绩表关联较少，知识按分值排序取中位数与 score 数值含义相符；接受可应用的统计方法，不声称该知识专属于此表。

## R079 · MYSQL:education_2025.student · 知识 1579

总评折算总分：同一学生跨多门课把总评相加

### 原始报告 #100 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1579,
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "总评折算总分：同一学生跨多门课把总评相加"
    }
  ],
  "reason": "条目涉及同一学生的跨课程总评，但学生表没有总评或成绩属性；不能仅沿选课、成绩关系把计算规则归入学生表。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：与2024学生表同口径：缺少总评或成绩属性，零关联不构成自动接受理由。

## R080 · MYSQL:education_2025.course · 知识 1579

总评折算总分：同一学生跨多门课把总评相加

### 原始报告 #101 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1579,
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "总评折算总分：同一学生跨多门课把总评相加"
    }
  ],
  "reason": "条目涉及多门课程的总评求和，但课程表没有总评属性；尚缺该规则直接解释课程表字段或操作的证据。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：与2024课程表同口径：缺少总评属性，零关联不构成自动接受理由。

## R081 · MYSQL:education_2025.enrollment · 知识 1579

总评折算总分：同一学生跨多门课把总评相加

### 原始报告 #102 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1579,
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "总评折算总分：同一学生跨多门课把总评相加"
    }
  ],
  "reason": "选课表提供学生与课程的粒度线索，但没有总评；本条未说明总评来源，也未显式引用其他总评计算知识。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：与2024选课表同口径：宽松接受学生与课程分组粒度的部分关联，不声称总评存在于选课表。

## R082 · MYSQL:education_2025.enrollment · 知识 1575

选课退课规则（示例）：enrollment.is_withdraw=1 的记录视为已退课，不计入成绩统计与排名。

### 原始报告 #103 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1575,
  "kind": "ambiguous_reference",
  "knowledge_evidence": [
    {
      "knowledge_id": 1575,
      "quote": "enrollment.is_withdraw=1 的记录视为已退课，不计入成绩统计与排名。"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "enrollment.is_withdraw 未注明数据库，完整目录中 education_2024、education_2025 均有该表字段；关联按各自结构支持记录，不能声称短引用唯一指定了当前库。"
}
```

### 原始报告 #104 · content_issues

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1575,
  "kind": "ambiguous_reference",
  "knowledge_evidence": [
    {
      "knowledge_id": 1575,
      "quote": "enrollment.is_withdraw=1 的记录视为已退课"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "知识以 enrollment.is_withdraw 指代表字段，未写库名；完整目录中 education_2024.enrollment 与 education_2025.enrollment 同名同结构，无法据此唯一确定表，只能作为 schema_supported 关联。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 2 条其他关联。

先前待审原因：与R073同理，不能把短引用声称为唯一表引用。

内容处理：用户裁定不关联本知识；原报告中的内容冲突、缺失或歧义继续保留，不代表这些内容已被修正或补全。

## R083 · MYSQL:education_2025.exam_score · 知识 1573

挂科判定规则（示例）：当总评成绩 < 60.00 视为不合格（挂科）。

### 原始报告 #105 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1573,
  "basis": "schema_supported",
  "fields": [
    "score"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1573,
      "quote": "当总评成绩 < 60.00 视为不合格（挂科）"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "score             DECIMAL(5,2),"
    }
  ],
  "qualifiers": [
    "（示例）"
  ],
  "reason": "挂科判定基于总评成绩的分数阈值，exam_score.score 为该成绩取数字段。"
}
```

### 原始报告 #108 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1573,
  "knowledge_evidence": [
    {
      "knowledge_id": 1573,
      "quote": "挂科判定规则（示例）：当总评成绩 < 60.00 视为不合格（挂科）。"
    }
  ],
  "reason": "条目针对总评成绩判定挂科，而原始表保存 exam_item、score 明细，未注明 score 为总评；本条未明确引用总评折算规则。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：与2024成绩表同口径：接受挂科规则适用关系，score 明细不能直接当作总评。

## R084 · MYSQL:education_2025.exam_score · 知识 1574

学分绩（GPA/绩点）示例映射：总评>=90 为绩点 4.0；80-89 为 3.0；70-79 为 2.0；60-69 为 1.0；<60 为 0.0。

### 原始报告 #106 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1574,
  "basis": "schema_supported",
  "fields": [
    "score"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1574,
      "quote": "总评>=90 为绩点 4.0；80-89 为 3.0；70-79 为 2.0；60-69 为 1.0；<60 为 0.0"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "score             DECIMAL(5,2),"
    }
  ],
  "qualifiers": [
    "示例映射"
  ],
  "reason": "绩点映射按总评分数区间划分，exam_score.score 提供该分数取值。"
}
```

### 原始报告 #109 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1574,
  "knowledge_evidence": [
    {
      "knowledge_id": 1574,
      "quote": "学分绩（GPA/绩点）示例映射：总评>=90 为绩点 4.0；80-89 为 3.0；70-79 为 2.0；60-69 为 1.0；<60 为 0.0。"
    }
  ],
  "reason": "条目把总评映射为绩点，成绩表未存储总评或绩点，也未说明哪一考试项目代表总评；不能自行补入折算步骤。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：与2024成绩表同口径：接受总评到绩点映射的适用关系，不补写总评计算步骤。

## R085 · MYSQL:education_2025.exam_score · 知识 1579

总评折算总分：同一学生跨多门课把总评相加

### 原始报告 #107 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1579,
  "basis": "schema_supported",
  "fields": [
    "score"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "总评折算总分：同一学生跨多门课把总评相加"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "score             DECIMAL(5,2),"
    }
  ],
  "qualifiers": [],
  "reason": "总评折算总分由课程总评（源自 exam_score.score）按学生汇总，exam_score 为该汇总的分数明细来源。"
}
```

### 原始报告 #110 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1579,
  "knowledge_evidence": [
    {
      "knowledge_id": 1579,
      "quote": "总评折算总分：同一学生跨多门课把总评相加"
    }
  ],
  "reason": "成绩明细具有分数及选课关联，但本条未定义总评来源和跨课程聚合的直接口径；不能从未显式引用的其他知识补齐。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：与2024成绩表同口径：接受跨课程总评求和的成绩来源关系，不直接对考试明细求和。

## R086 · MYSQL:education_2025.exam_score · 知识 1577

中位数：窗口函数按分值排序取中间行

### 原始报告 #111 · candidates

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1577,
  "knowledge_evidence": [
    {
      "knowledge_id": 1577,
      "quote": "中位数：窗口函数按分值排序取中间行"
    }
  ],
  "reason": "仅给出通用中位数取法，未指明表或字段；“分值”可能对应 exam_score.score，但也可指其他数值列，无法确认是否专用于本表。"
}
```

裁定状态：resolved；关联：accept；来源：agent_under_user_rules。

理由：与2024成绩表同口径：按宽口径接受中位数方法与分值字段的适用关系，不声称专属。

## R087 · POSTGRESQL:public.vessel_ais_data · 知识 1713

上海青草沙水源地禁航区四边形水域，四个顶点坐标分别为：A(31°26′08.329″N,121°34′18.678″E)、B(31°26′42.713″N,121°33′39.136″E)、C(31°27′10.312″N,121°33′58.456″E)、D(31°26′36.982″N,121°34′35.287″E)，转换为十进制度约为A(121.5719,31.4356)、B(121.5609,31.4452)、C(121.5663,31.4529)、D(121.5765,31.4414)，按A-B-C-D-A顺序围成闭合多边形

### 原始报告 #112 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1713,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1713,
      "quote": "上海青草沙水源地禁航区四边形水域"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出上海青草沙水源地禁航区坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #132 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1713,
  "knowledge_evidence": [
    {
      "knowledge_id": 1713,
      "quote": "上海青草沙水源地禁航区四边形水域，四个顶点坐标分别为：A(31°26′08.329″N,121°34′18.678″E)、B(31°26′42.713″N,121°33′39.136″E)、C(31°27′10.312″N,121°33′58.456″E)、D(31°26′36.982″N,121°34′35.287″E)，转换为十进制度约为A(121.5719,31.4356)、B(121.5609,31.4452)、C(121.5663,31.4529)、D(121.5765,31.4414)，按A-B-C-D-A顺序围成闭合多边形"
    }
  ],
  "reason": "条目仅定义禁航水域多边形，未明确船舶记录或本表查询条件；AIS表保存船舶点位置，不保存禁航区对象。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目仅定义禁航水域多边形，未明确船舶记录或本表查询条件；AIS表保存船舶点位置，不保存禁航区对象。 不把同表已有空间字段作为充分依据。

## R088 · POSTGRESQL:public.vessel_ais_data · 知识 1714

长江口禁捕管理区范围为东经122°15′（122.25°）以东至124.0°、北纬30°54′（30.90°）至31°41′36″（31.6933°）之间的矩形水域，向西以水陆交界线为界

### 原始报告 #113 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1714,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1714,
      "quote": "长江口禁捕管理区范围为东经122°15′（122.25°）以东至124.0°、北纬30°54′（30.90°）至31°41′36″（31.6933°）之间的矩形水域"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出长江口禁捕管理区矩形范围，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #133 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1714,
  "knowledge_evidence": [
    {
      "knowledge_id": 1714,
      "quote": "长江口禁捕管理区范围为东经122°15′（122.25°）以东至124.0°、北纬30°54′（30.90°）至31°41′36″（31.6933°）之间的矩形水域，向西以水陆交界线为界"
    }
  ],
  "reason": "条目仅定义禁捕管理区域，缺少该区域与AIS船舶记录查询或操作约束的直接说明，不能仅凭空间字段确认。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目仅定义禁捕管理区域，缺少该区域与AIS船舶记录查询或操作约束的直接说明，不能仅凭空间字段确认。 不把同表已有空间字段作为充分依据。

## R089 · POSTGRESQL:public.vessel_ais_data · 知识 1715

黄浦江核心管制区为川杨河口下游100米处（约31°10′12″N,121°29′00″E）至南浦大桥（约31°12′30″N,121°30′30″E）之间的水域

### 原始报告 #114 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1715,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1715,
      "quote": "黄浦江核心管制区为川杨河口下游100米处"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出黄浦江核心管制区坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #134 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1715,
  "knowledge_evidence": [
    {
      "knowledge_id": 1715,
      "quote": "黄浦江核心管制区为川杨河口下游100米处（约31°10′12″N,121°29′00″E）至南浦大桥（约31°12′30″N,121°30′30″E）之间的水域"
    }
  ],
  "reason": "条目仅描述管制区起止水域，未给出直接针对AIS记录属性的条件或明确表对象。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目仅描述管制区起止水域，未给出直接针对AIS记录属性的条件或明确表对象。 不把同表已有空间字段作为充分依据。

## R090 · POSTGRESQL:public.vessel_ais_data · 知识 1716

珠江口水上交通安全特别监管区，东至114°30′08.8″E（114.5024°）经度线，南至21°45′00.0″N（21.75°）纬度线，西至112°59′30″E（112.9917°）经度线，北至广州港黄埔大桥附近（约23.5°以覆盖整个监管区）

### 原始报告 #115 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1716,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1716,
      "quote": "珠江口水上交通安全特别监管区"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出珠江口水上交通安全特别监管区边界，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #135 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1716,
  "knowledge_evidence": [
    {
      "knowledge_id": 1716,
      "quote": "珠江口水上交通安全特别监管区，东至114°30′08.8″E（114.5024°）经度线，南至21°45′00.0″N（21.75°）纬度线，西至112°59′30″E（112.9917°）经度线，北至广州港黄埔大桥附近（约23.5°以覆盖整个监管区）"
    }
  ],
  "reason": "条目提供监管区地理边界，未说明船舶记录的具体条件；不能只因AIS含经纬度而确认关联。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目提供监管区地理边界，未说明船舶记录的具体条件；不能只因AIS含经纬度而确认关联。 不把同表已有空间字段作为充分依据。

## R091 · POSTGRESQL:public.vessel_ais_data · 知识 1717

杭州湾水域某次实弹训练禁航区范围为北纬30°19′（30.317°）至30°35′（30.583°），东经121°02′（121.033°）至121°12′（121.20°）的矩形水域

### 原始报告 #116 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1717,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1717,
      "quote": "杭州湾水域某次实弹训练禁航区范围"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出杭州湾实弹训练禁航区矩形范围，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #136 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1717,
  "knowledge_evidence": [
    {
      "knowledge_id": 1717,
      "quote": "杭州湾水域某次实弹训练禁航区范围为北纬30°19′（30.317°）至30°35′（30.583°），东经121°02′（121.033°）至121°12′（121.20°）的矩形水域"
    }
  ],
  "reason": "条目提供某次实弹训练禁航区边界，未说明船舶记录的具体适用时段或直接查询条件。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目提供某次实弹训练禁航区边界，未说明船舶记录的具体适用时段或直接查询条件。 不把同表已有空间字段作为充分依据。

## R092 · POSTGRESQL:public.vessel_ais_data · 知识 1718

天津港地处渤海西部海岸海河入海口处，中心位置东经117°42′05″（117.7014°），北纬38°59′08″（38.9856°）。海河水域新港船闸维修禁航区：以38-59.5N 117-42.8E（38.9917°N,117.7133°E）为圆心，半径250米的水域。海河下游二道闸至轮驳公司码头段为通航管制区

### 原始报告 #117 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1718,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1718,
      "quote": "天津港地处渤海西部海岸海河入海口处"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出天津港及海河禁航区坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #137 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1718,
  "knowledge_evidence": [
    {
      "knowledge_id": 1718,
      "quote": "天津港地处渤海西部海岸海河入海口处，中心位置东经117°42′05″（117.7014°），北纬38°59′08″（38.9856°）。海河水域新港船闸维修禁航区：以38-59.5N 117-42.8E（38.9917°N,117.7133°E）为圆心，半径250米的水域。海河下游二道闸至轮驳公司码头段为通航管制区"
    }
  ],
  "reason": "条目提供天津港及禁航、管制水域位置，未明确本表对象或对船舶记录属性的直接条件。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目提供天津港及禁航、管制水域位置，未明确本表对象或对船舶记录属性的直接条件。 不把同表已有空间字段作为充分依据。

## R093 · POSTGRESQL:public.vessel_ais_data · 知识 1722

舟山虾峙门深水航道（进港航道）。虾峙门航道是宁波舟山港核心港区最重要的深水进港航道，地理范围：自虾峙门东口（29°45.0′N,122°25.0′E）至螺头角（29°54.0′N,122°01.0′E），全长约24海里，航道宽度约0.3海里，水深22米以上，可满足30万吨级船舶通航。航道两侧设有分道通航制，中间由分隔带分隔。船舶在航道内应保持VHF08频道守听，按照潮汐时段单向通航，大型船舶需引航。

### 原始报告 #118 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1722,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1722,
      "quote": "舟山虾峙门深水航道（进港航道）"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出舟山虾峙门深水航道地理范围，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #138 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1722,
  "knowledge_evidence": [
    {
      "knowledge_id": 1722,
      "quote": "舟山虾峙门深水航道（进港航道）。虾峙门航道是宁波舟山港核心港区最重要的深水进港航道，地理范围：自虾峙门东口（29°45.0′N,122°25.0′E）至螺头角（29°54.0′N,122°01.0′E），全长约24海里，航道宽度约0.3海里，水深22米以上，可满足30万吨级船舶通航。航道两侧设有分道通航制，中间由分隔带分隔。船舶在航道内应保持VHF08频道守听，按照潮汐时段单向通航，大型船舶需引航。"
    }
  ],
  "reason": "条目主要定义航道并要求守听、按潮汐通航和引航；Schema没有通信、潮汐或引航属性，不能从区域坐标推定关联。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目主要定义航道并要求守听、按潮汐通航和引航；Schema没有通信、潮汐或引航属性，不能从区域坐标推定关联。 不把同表已有空间字段作为充分依据。

## R094 · POSTGRESQL:public.vessel_ais_data · 知识 1723

珠江口桂山锚地。桂山锚地位于珠江口桂山岛附近，是进出广州港、深圳港、珠海港的大型船舶候泊、引航、联检锚地。锚地范围由以下四点围成：A(22°10.0′N,113°48.0′E)、B(22°10.0′N,113°52.0′E)、C(22°07.0′N,113°52.0′E)、D(22°07.0′N,113°48.0′E)。锚地水深12-18米，底质泥沙，可锚泊10万吨级以下船舶。锚地内船舶应按规定显示锚泊信号，保持VHF16频道守听，不得排放污染物。

### 原始报告 #119 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1723,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1723,
      "quote": "珠江口桂山锚地"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出珠江口桂山锚地四点范围，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #139 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1723,
  "knowledge_evidence": [
    {
      "knowledge_id": 1723,
      "quote": "珠江口桂山锚地。桂山锚地位于珠江口桂山岛附近，是进出广州港、深圳港、珠海港的大型船舶候泊、引航、联检锚地。锚地范围由以下四点围成：A(22°10.0′N,113°48.0′E)、B(22°10.0′N,113°52.0′E)、C(22°07.0′N,113°52.0′E)、D(22°07.0′N,113°48.0′E)。锚地水深12-18米，底质泥沙，可锚泊10万吨级以下船舶。锚地内船舶应按规定显示锚泊信号，保持VHF16频道守听，不得排放污染物。"
    }
  ],
  "reason": "条目定义锚地并要求锚泊信号、守听及排污约束；AIS结构没有这些属性，也没有载重字段支持十万吨级条件。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目定义锚地并要求锚泊信号、守听及排污约束；AIS结构没有这些属性，也没有载重字段支持十万吨级条件。 不把同表已有空间字段作为充分依据。

## R095 · POSTGRESQL:public.vessel_ais_data · 知识 1725

厦门港东渡港区航道及锚地。东渡港区航道自青屿水域（24°26.0′N,118°06.0′E）至东渡码头前沿，全长约8海里，航道宽度200米，水深-12米。港区锚地位于猴屿西侧，范围为：A(24°28.0′N,118°04.0′E)、B(24°28.0′N,118°06.0′E)、C(24°26.0′N,118°06.0′E)、D(24°26.0′N,118°04.0′E)，水深10-14米。该区域为船舶进出厦门港西航道的主要通道，船舶应遵守《厦门水域船舶定线制》和《厦门船舶交通管理系统（VTS）用户指南》。

### 原始报告 #120 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1725,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1725,
      "quote": "厦门港东渡港区航道及锚地"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出厦门港东渡港区航道及锚地坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #140 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1725,
  "knowledge_evidence": [
    {
      "knowledge_id": 1725,
      "quote": "厦门港东渡港区航道及锚地。东渡港区航道自青屿水域（24°26.0′N,118°06.0′E）至东渡码头前沿，全长约8海里，航道宽度200米，水深-12米。港区锚地位于猴屿西侧，范围为：A(24°28.0′N,118°04.0′E)、B(24°28.0′N,118°06.0′E)、C(24°26.0′N,118°06.0′E)、D(24°26.0′N,118°04.0′E)，水深10-14米。该区域为船舶进出厦门港西航道的主要通道，船舶应遵守《厦门水域船舶定线制》和《厦门船舶交通管理系统（VTS）用户指南》。"
    }
  ],
  "reason": "条目提供航道、锚地坐标并要求遵守外部制度，未给出可直接对应AIS字段的船舶条件。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目提供航道、锚地坐标并要求遵守外部制度，未给出可直接对应AIS字段的船舶条件。 不把同表已有空间字段作为充分依据。

## R096 · POSTGRESQL:public.vessel_ais_data · 知识 1729

渤海湾曹妃甸港区航道及锚地。曹妃甸港区主航道自20万吨级矿石码头（38°55.0′N,118°30.0′E）向外海延伸至38°51.0′N,118°35.0′E，全长约11海里，宽度350米，水深-21米。港区设有1#和2#锚地：1#锚地位于38°54.0′N-38°56.0′N,118°35.0′E-118°40.0′E，2#锚地位于38°51.0′N-38°53.0′N,118°35.0′E-118°40.0′E。锚地底质为泥沙，可锚泊15万吨级以下船舶。船舶进出港需遵守《曹妃甸船舶交通管理系统（VTS）安全管理规定》。

### 原始报告 #121 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1729,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1729,
      "quote": "渤海湾曹妃甸港区航道及锚地"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出渤海湾曹妃甸港区航道及锚地坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #141 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1729,
  "knowledge_evidence": [
    {
      "knowledge_id": 1729,
      "quote": "渤海湾曹妃甸港区航道及锚地。曹妃甸港区主航道自20万吨级矿石码头（38°55.0′N,118°30.0′E）向外海延伸至38°51.0′N,118°35.0′E，全长约11海里，宽度350米，水深-21米。港区设有1#和2#锚地：1#锚地位于38°54.0′N-38°56.0′N,118°35.0′E-118°40.0′E，2#锚地位于38°51.0′N-38°53.0′N,118°35.0′E-118°40.0′E。锚地底质为泥沙，可锚泊15万吨级以下船舶。船舶进出港需遵守《曹妃甸船舶交通管理系统（VTS）安全管理规定》。"
    }
  ],
  "reason": "条目给出航道、锚地和载重适用范围及外部规定；AIS没有最大载重字段，地理边界本身不足以确认。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目给出航道、锚地和载重适用范围及外部规定；AIS没有最大载重字段，地理边界本身不足以确认。 不把同表已有空间字段作为充分依据。

## R097 · POSTGRESQL:public.vessel_ais_data · 知识 1743

连云港港主航道及锚地。连云港主航道自外海引航点（34°45.0′N,119°50.0′E）至庙岭集装箱码头（34°45.0′N,119°20.0′E），全长约25海里，航道宽度220米，水深-14米。港区设有2号锚地，范围为：A(34°48.0′N,119°40.0′E)、B(34°48.0′N,119°45.0′E)、C(34°45.0′N,119°45.0′E)、D(34°45.0′N,119°40.0′E)，水深12-15米。船舶进出港需向连云港VTS中心报告，航道内禁止追越。

### 原始报告 #122 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1743,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1743,
      "quote": "连云港港主航道及锚地"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出连云港港主航道及锚地坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #142 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1743,
  "knowledge_evidence": [
    {
      "knowledge_id": 1743,
      "quote": "连云港港主航道及锚地。连云港主航道自外海引航点（34°45.0′N,119°50.0′E）至庙岭集装箱码头（34°45.0′N,119°20.0′E），全长约25海里，航道宽度220米，水深-14米。港区设有2号锚地，范围为：A(34°48.0′N,119°40.0′E)、B(34°48.0′N,119°45.0′E)、C(34°45.0′N,119°45.0′E)、D(34°45.0′N,119°40.0′E)，水深12-15米。船舶进出港需向连云港VTS中心报告，航道内禁止追越。"
    }
  ],
  "reason": "航道内禁止追越有潜在线索，但原文未给出由AIS记录判定追越的规则；不能自行补充轨迹或相对运动算法。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：航道内禁止追越有潜在线索，但原文未给出由AIS记录判定追越的规则；不能自行补充轨迹或相对运动算法。 不把同表已有空间字段作为充分依据。

## R098 · POSTGRESQL:public.vessel_ais_data · 知识 1745

镇江港大港港区航道及锚地。大港港区航道自和畅洲北汊入口（32°12.0′N,119°40.0′E）至大港码头前沿（32°11.0′N,119°37.0′E），全长约5海里，航道宽度200米，水深-10米。港区锚地位于和畅洲南侧，范围为：A(32°10.0′N,119°38.0′E)、B(32°10.0′N,119°42.0′E)、C(32°08.0′N,119°42.0′E)、D(32°08.0′N,119°38.0′E)。船舶进出港需遵守《长江江苏段船舶定线制规定》，向镇江VTS中心报告。

### 原始报告 #123 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1745,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1745,
      "quote": "镇江港大港港区航道及锚地"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出镇江港大港港区航道及锚地坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #143 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1745,
  "knowledge_evidence": [
    {
      "knowledge_id": 1745,
      "quote": "镇江港大港港区航道及锚地。大港港区航道自和畅洲北汊入口（32°12.0′N,119°40.0′E）至大港码头前沿（32°11.0′N,119°37.0′E），全长约5海里，航道宽度200米，水深-10米。港区锚地位于和畅洲南侧，范围为：A(32°10.0′N,119°38.0′E)、B(32°10.0′N,119°42.0′E)、C(32°08.0′N,119°42.0′E)、D(32°08.0′N,119°38.0′E)。船舶进出港需遵守《长江江苏段船舶定线制规定》，向镇江VTS中心报告。"
    }
  ],
  "reason": "条目定义航道、锚地并要求遵守外部制度和报告，Schema未记录这些制度或报告属性。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目定义航道、锚地并要求遵守外部制度和报告，Schema未记录这些制度或报告属性。 不把同表已有空间字段作为充分依据。

## R099 · POSTGRESQL:public.vessel_ais_data · 知识 1747

张家港港务局码头前沿水域（通航密集区）。张家港港务局码头前沿水域范围为：自(31°56.0′N,120°28.0′E)至(31°53.0′N,120°24.0′E)沿江岸线外300米水域。该区域码头泊位密集，常有多艘船舶同时靠离泊作业。过往船舶应保持安全航速，加强与码头调度通信，避免进入靠离泊作业区。

### 原始报告 #124 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1747,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1747,
      "quote": "张家港港务局码头前沿水域（通航密集区）"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出张家港港务局码头前沿水域范围，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #144 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1747,
  "knowledge_evidence": [
    {
      "knowledge_id": 1747,
      "quote": "张家港港务局码头前沿水域（通航密集区）。张家港港务局码头前沿水域范围为：自(31°56.0′N,120°28.0′E)至(31°53.0′N,120°24.0′E)沿江岸线外300米水域。该区域码头泊位密集，常有多艘船舶同时靠离泊作业。过往船舶应保持安全航速，加强与码头调度通信，避免进入靠离泊作业区。"
    }
  ],
  "reason": "安全航速、靠离泊作业区等要求有船舶线索，但安全阈值、沿岸边界和作业区均未提供，不能补成AIS条件。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：安全航速、靠离泊作业区等要求有船舶线索，但安全阈值、沿岸边界和作业区均未提供，不能补成AIS条件。 不把同表已有空间字段作为充分依据。

## R100 · POSTGRESQL:public.vessel_ais_data · 知识 1750

上海港外高桥港区航道（长江口段）。外高桥港区航道自长江口圆圆沙灯船（31°22.0′N,121°38.0′E）至外高桥码头（31°20.0′N,121°33.0′E），全长约7海里，航道宽度300米，水深-12.5米。该航道为进出上海港的主要通道之一，实行分道通航制，船舶应保持VHF14频道守听，遵守《长江口船舶交通管理系统（VTS）安全监督管理办法》。

### 原始报告 #125 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1750,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1750,
      "quote": "上海港外高桥港区航道（长江口段）"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出上海港外高桥港区航道坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #145 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1750,
  "knowledge_evidence": [
    {
      "knowledge_id": 1750,
      "quote": "上海港外高桥港区航道（长江口段）。外高桥港区航道自长江口圆圆沙灯船（31°22.0′N,121°38.0′E）至外高桥码头（31°20.0′N,121°33.0′E），全长约7海里，航道宽度300米，水深-12.5米。该航道为进出上海港的主要通道之一，实行分道通航制，船舶应保持VHF14频道守听，遵守《长江口船舶交通管理系统（VTS）安全监督管理办法》。"
    }
  ],
  "reason": "条目描述航道及分道制、守听和法规要求，未给出分道方向或位置条件；Schema不记录通信和法规遵守情况。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目描述航道及分道制、守听和法规要求，未给出分道方向或位置条件；Schema不记录通信和法规遵守情况。 不把同表已有空间字段作为充分依据。

## R101 · POSTGRESQL:public.vessel_ais_data · 知识 1752

宁波舟山港穿山港区航道及警戒区。穿山港区航道自虾峙门航道东口（29°52.0′N,122°10.0′E）至穿山码头前沿（29°55.0′N,122°00.0′E），全长约12海里，航道宽度350米，水深-18米。港区警戒区位于航道入口，以点(29°52.0′N,122°10.0′E)为中心、半径0.6海里。船舶进入警戒区前应向穿山VTS中心报告，大型船舶需引航。

### 原始报告 #126 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1752,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1752,
      "quote": "宁波舟山港穿山港区航道及警戒区"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出宁波舟山港穿山港区航道及警戒区坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #146 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1752,
  "knowledge_evidence": [
    {
      "knowledge_id": 1752,
      "quote": "宁波舟山港穿山港区航道及警戒区。穿山港区航道自虾峙门航道东口（29°52.0′N,122°10.0′E）至穿山码头前沿（29°55.0′N,122°00.0′E），全长约12海里，航道宽度350米，水深-18米。港区警戒区位于航道入口，以点(29°52.0′N,122°10.0′E)为中心、半径0.6海里。船舶进入警戒区前应向穿山VTS中心报告，大型船舶需引航。"
    }
  ],
  "reason": "条目主要给出航道警戒区与VTS、引航要求；AIS没有引航属性，且大型船舶条件未定义。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目主要给出航道警戒区与VTS、引航要求；AIS没有引航属性，且大型船舶条件未定义。 不把同表已有空间字段作为充分依据。

## R102 · POSTGRESQL:public.vessel_ais_data · 知识 1754

温州港乐清湾港区航道。乐清湾港区航道自大门岛东侧（27°58.0′N,121°12.0′E）至乐清湾码头（27°55.0′N,121°05.0′E），全长约12海里，航道宽度200米，水深-10米。航道两侧设有浮筒，航道内设有3处转向点。该水域渔船较多，进出港船舶应加强瞭望，保持安全航速。

### 原始报告 #127 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1754,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1754,
      "quote": "温州港乐清湾港区航道"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出温州港乐清湾港区航道坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #147 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1754,
  "knowledge_evidence": [
    {
      "knowledge_id": 1754,
      "quote": "温州港乐清湾港区航道。乐清湾港区航道自大门岛东侧（27°58.0′N,121°12.0′E）至乐清湾码头（27°55.0′N,121°05.0′E），全长约12海里，航道宽度200米，水深-10米。航道两侧设有浮筒，航道内设有3处转向点。该水域渔船较多，进出港船舶应加强瞭望，保持安全航速。"
    }
  ],
  "reason": "条目提出安全航速和加强瞭望的一般要求，未定义安全阈值，Schema也没有瞭望属性，具体AIS条件无法确认。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目提出安全航速和加强瞭望的一般要求，未定义安全阈值，Schema也没有瞭望属性，具体AIS条件无法确认。 不把同表已有空间字段作为充分依据。

## R103 · POSTGRESQL:public.vessel_ais_data · 知识 1755

福州港江阴港区航道及警戒区。江阴港区航道自兴化湾口（25°20.0′N,119°40.0′E）至江阴码头（25°25.0′N,119°20.0′E），全长约15海里，航道宽度250米，水深-15米。港区警戒区位于航道入口，以点(25°20.0′N,119°40.0′E)为中心、半径0.5海里。船舶进入警戒区前应向福州VTS中心报告（VHF10频道），大型船舶需引航。

### 原始报告 #128 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1755,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1755,
      "quote": "福州港江阴港区航道及警戒区"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出福州港江阴港区航道及警戒区坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #148 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1755,
  "knowledge_evidence": [
    {
      "knowledge_id": 1755,
      "quote": "福州港江阴港区航道及警戒区。江阴港区航道自兴化湾口（25°20.0′N,119°40.0′E）至江阴码头（25°25.0′N,119°20.0′E），全长约15海里，航道宽度250米，水深-15米。港区警戒区位于航道入口，以点(25°20.0′N,119°40.0′E)为中心、半径0.5海里。船舶进入警戒区前应向福州VTS中心报告（VHF10频道），大型船舶需引航。"
    }
  ],
  "reason": "条目给出航道、报告和大型船舶引航要求，AIS没有报告或引航属性，大型条件也未定义。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目给出航道、报告和大型船舶引航要求，AIS没有报告或引航属性，大型条件也未定义。 不把同表已有空间字段作为充分依据。

## R104 · POSTGRESQL:public.vessel_ais_data · 知识 1756

泉州港石湖港区航道及锚地。石湖港区航道自泉州湾口（24°45.0′N,118°50.0′E）至石湖码头（24°48.0′N,118°42.0′E），全长约10海里，航道宽度200米，水深-12米。港区锚地位于航道东侧，范围为：A(24°46.0′N,118°52.0′E)、B(24°46.0′N,118°55.0′E)、C(24°44.0′N,118°55.0′E)、D(24°44.0′N,118°52.0′E)，水深11-14米。船舶进出港需向泉州VTS中心报告，航道内禁止追越。

### 原始报告 #129 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1756,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1756,
      "quote": "泉州港石湖港区航道及锚地"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出泉州港石湖港区航道及锚地坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #149 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1756,
  "knowledge_evidence": [
    {
      "knowledge_id": 1756,
      "quote": "泉州港石湖港区航道及锚地。石湖港区航道自泉州湾口（24°45.0′N,118°50.0′E）至石湖码头（24°48.0′N,118°42.0′E），全长约10海里，航道宽度200米，水深-12米。港区锚地位于航道东侧，范围为：A(24°46.0′N,118°52.0′E)、B(24°46.0′N,118°55.0′E)、C(24°44.0′N,118°55.0′E)、D(24°44.0′N,118°52.0′E)，水深11-14米。船舶进出港需向泉州VTS中心报告，航道内禁止追越。"
    }
  ],
  "reason": "条目禁止航道内追越，但未提供从AIS字段判断追越的口径；其余主要是区域坐标和报告要求。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目禁止航道内追越，但未提供从AIS字段判断追越的口径；其余主要是区域坐标和报告要求。 不把同表已有空间字段作为充分依据。

## R105 · POSTGRESQL:public.vessel_ais_data · 知识 1757

漳州港招银港区航道。招银港区航道自厦门湾南侧（24°25.0′N,118°05.0′E）至招银码头（24°28.0′N,118°02.0′E），全长约6海里，航道宽度180米，水深-12米。航道两侧设有浮灯，航道内设有2处转向点。该水域船舶交通密集，船舶应遵守《厦门水域船舶定线制》，向厦门VTS中心报告。

### 原始报告 #130 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1757,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1757,
      "quote": "漳州港招银港区航道"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出漳州港招银港区航道坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #150 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1757,
  "knowledge_evidence": [
    {
      "knowledge_id": 1757,
      "quote": "漳州港招银港区航道。招银港区航道自厦门湾南侧（24°25.0′N,118°05.0′E）至招银码头（24°28.0′N,118°02.0′E），全长约6海里，航道宽度180米，水深-12米。航道两侧设有浮灯，航道内设有2处转向点。该水域船舶交通密集，船舶应遵守《厦门水域船舶定线制》，向厦门VTS中心报告。"
    }
  ],
  "reason": "条目主要定义航道并要求遵守定线制与VTS报告，没有给出直接对应AIS字段的方向、速度或状态条件。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目主要定义航道并要求遵守定线制与VTS报告，没有给出直接对应AIS字段的方向、速度或状态条件。 不把同表已有空间字段作为充分依据。

## R106 · POSTGRESQL:public.vessel_ais_data · 知识 1759

惠州港荃湾港区航道及锚地。荃湾港区航道自大亚湾口（22°38.0′N,114°38.0′E）至荃湾码头（22°42.0′N,114°35.0′E），全长约8海里，航道宽度200米，水深-14米。港区锚地位于航道南侧，范围为：A(22°40.0′N,114°36.0′E)、B(22°40.0′N,114°39.0′E)、C(22°38.0′N,114°39.0′E)、D(22°38.0′N,114°36.0′E)，水深12-15米。船舶进出港需向惠州VTS中心报告，大型船舶需引航。

### 原始报告 #131 · association_disagreement

Codex：未输出肯定关联（不等于明确拒绝）。

Deepseek Flash：接受关联。

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1759,
  "basis": "schema_supported",
  "fields": [
    "longitude",
    "latitude",
    "geom"
  ],
  "knowledge_evidence": [
    {
      "knowledge_id": 1759,
      "quote": "惠州港荃湾港区航道及锚地"
    }
  ],
  "schema_evidence": [
    {
      "source_file": "data/赛题8/Schema/core_schema.txt",
      "quote": "geom public.geometry(Point,4326) NOT NULL,"
    }
  ],
  "qualifiers": [],
  "reason": "知识给出惠州港荃湾港区航道及锚地坐标，Schema 的 vessel_ais_data 含空间位置字段，可用于空间查询条件。"
}
```

### 原始报告 #151 · candidates

Codex 原始审计：

```json
{
  "knowledge_id": 1759,
  "knowledge_evidence": [
    {
      "knowledge_id": 1759,
      "quote": "惠州港荃湾港区航道及锚地。荃湾港区航道自大亚湾口（22°38.0′N,114°38.0′E）至荃湾码头（22°42.0′N,114°35.0′E），全长约8海里，航道宽度200米，水深-14米。港区锚地位于航道南侧，范围为：A(22°40.0′N,114°36.0′E)、B(22°40.0′N,114°39.0′E)、C(22°38.0′N,114°39.0′E)、D(22°38.0′N,114°36.0′E)，水深12-15米。船舶进出港需向惠州VTS中心报告，大型船舶需引航。"
    }
  ],
  "reason": "条目提供区域边界并要求大型船舶引航，AIS不含引航属性，且大型条件未定义，不能仅据空间字段确认。"
}
```

裁定状态：resolved；关联：reject；来源：agent_under_user_rules。

理由：AIS表已有30条Codex关联、50条Flash关联，采用严格口径；逐项核对意见：条目提供区域边界并要求大型船舶引航，AIS不含引航属性，且大型条件未定义，不能仅据空间字段确认。 不把同表已有空间字段作为充分依据。

## R107 · POSTGRESQL:public.vessel_ais_data · 知识 1739

异常航行记录：指航行状态nav_status=1（航行中）sog15或sog0.5

### 原始报告 #152 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1739,
  "kind": "incomplete_rule",
  "knowledge_evidence": [
    {
      "knowledge_id": 1739,
      "quote": "nav_status=1（航行中）sog15或sog0.5"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "sog15、sog0.5 缺失比较符，状态条件与航速条件的连接范围也未完整写出；不补写阈值方向。"
}
```

### 原始报告 #153 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1739,
  "kind": "conflicting_content",
  "knowledge_evidence": [
    {
      "knowledge_id": 1739,
      "quote": "nav_status=1（航行中）"
    },
    {
      "knowledge_id": 1740,
      "quote": "nav_status=1锚泊"
    }
  ],
  "related_knowledge_ids": [
    1740
  ],
  "reason": "同一 nav_status=1 在1739被标为航行中，在1740被标为锚泊；不选定其中一方。"
}
```

### 原始报告 #155 · content_issues

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1739,
  "kind": "incomplete_rule",
  "knowledge_evidence": [
    {
      "knowledge_id": 1739,
      "quote": "sog15或sog0.5"
    }
  ],
  "related_knowledge_ids": [],
  "reason": "原文用“sog15或sog0.5”描述异常航行条件，缺少比较运算符，无法直接判断阈值方向。"
}
```

### 原始报告 #156 · content_issues

Deepseek Flash 原始审计：

```json
{
  "knowledge_id": 1739,
  "kind": "conflicting_content",
  "knowledge_evidence": [
    {
      "knowledge_id": 1739,
      "quote": "nav_status=1（航行中）"
    },
    {
      "knowledge_id": 1740,
      "quote": "nav_status=1锚泊"
    }
  ],
  "related_knowledge_ids": [
    1740
  ],
  "reason": "同一条 nav_status=1 在 1739 被定义为航行中，在 1740 又被归入停泊（锚泊），两处定义冲突。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 28 条其他关联。

先前待审原因：Schema仅说明航行状态及数值范围，没有状态码语义；原文还缺少航速比较符，左闭右开规则不足以补全。

内容处理：用户裁定不关联本知识；原报告中的内容冲突、缺失或歧义继续保留，不代表这些内容已被修正或补全。

## R108 · POSTGRESQL:public.vessel_ais_data · 知识 1740

停泊：包括nav_status=1锚泊和nav_status=5系泊

### 原始报告 #154 · content_issues

Codex 原始审计：

```json
{
  "knowledge_id": 1740,
  "kind": "conflicting_content",
  "knowledge_evidence": [
    {
      "knowledge_id": 1740,
      "quote": "nav_status=1锚泊"
    },
    {
      "knowledge_id": 1739,
      "quote": "nav_status=1（航行中）"
    }
  ],
  "related_knowledge_ids": [
    1739
  ],
  "reason": "同一 nav_status=1 在1740被标为锚泊，在1739被标为航行中；不选定其中一方。"
}
```

裁定状态：resolved；关联：reject；来源：user_rule_remaining_coverage。

理由：按用户最终规则：该表已有其他关联知识，因此本待审项不关联。排除本轮全部待审项后仍有 28 条其他关联。

先前待审原因：知识1739与1740对nav_status=1含义冲突，Schema无明确映射，仍需用户指定。

内容处理：用户裁定不关联本知识；原报告中的内容冲突、缺失或歧义继续保留，不代表这些内容已被修正或补全。
