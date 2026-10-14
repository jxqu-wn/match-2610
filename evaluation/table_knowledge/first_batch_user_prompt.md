请严格按照系统提示词 table-knowledge-reference-v2，独立完成本批标注。

batch_id: batch-001
target_table_ids: ["MYSQL:common.administrative_division", "MYSQL:common.vehicle_type_dict", "MYSQL:common.vessel_type_dict", "MYSQL:common.employee_type_dict", "MYSQL:common.license_type_dict", "MYSQL:common.dict_registration_type"]

完整上下文如下。每张目标表都必须检查 context.knowledge_context 中的全部247条知识。
使用完整的72张表/索引目录消除引用歧义，主结果仅输出上述目标表，顺序与列表相同。
主结果必须保持 tables[].knowledge[]，每条 knowledge 只含 knowledge_id 和完整原文 knowledge_text。
知识排序、去重、空表、未决项及独立 audit 信息均遵守系统提示词。
不使用其他标注员的结果或程序当前的匹配结果。

<REFERENCE_INPUT_JSON>
{
  "context": {
    "source_manifest": {
      "rubric_version": "table-knowledge-reference-v2",
      "knowledge_file": "data/赛题8/knowledge.json",
      "knowledge_sha256": "92f310bc19420e8b374936c1eac0b35b58489c2764a892976fdfae3268b276c9",
      "knowledge_count": 247,
      "table_count": 72,
      "schema_sources": [
        {
          "source_file": "data/赛题8/Schema/commom_schema.txt",
          "encoding": "utf-8-sig",
          "sha256": "a6e0b1048576e4d55b66e496aff505047c2aca0a8f87ae0bde87329ca8ed8e94"
        },
        {
          "source_file": "data/赛题8/Schema/core_schema.txt",
          "encoding": "gb18030",
          "sha256": "936e4a96d43515d3570dc213dee83a836cc74d9584a9a1ce875c97dfb8248bad"
        }
      ],
      "contains_generated_descriptions": false,
      "contains_existing_associations": false
    },
    "table_catalog": [
      {
        "table_id": "MYSQL:common.administrative_division",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "administrative_division",
        "columns": [
          "id",
          "name",
          "full_name",
          "province_name",
          "city_name",
          "county_name",
          "level",
          "longitude",
          "latitude"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 6
      },
      {
        "table_id": "MYSQL:common.vehicle_type_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "vehicle_type_dict",
        "columns": [
          "type_code",
          "type_name",
          "category"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 31
      },
      {
        "table_id": "MYSQL:common.vessel_type_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "vessel_type_dict",
        "columns": [
          "type_code",
          "type_name",
          "category"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 38
      },
      {
        "table_id": "MYSQL:common.employee_type_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "employee_type_dict",
        "columns": [
          "type_code",
          "type_name"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 45
      },
      {
        "table_id": "MYSQL:common.license_type_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "license_type_dict",
        "columns": [
          "license_code",
          "license_name"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 51
      },
      {
        "table_id": "MYSQL:common.dict_registration_type",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_registration_type",
        "columns": [
          "type_code",
          "type_name",
          "description"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 126
      },
      {
        "table_id": "MYSQL:common.dict_size_category",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_size_category",
        "columns": [
          "size_code",
          "size_name"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 143
      },
      {
        "table_id": "MYSQL:common.dict_stock_type",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_stock_type",
        "columns": [
          "type_category",
          "type_code",
          "type_name"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 155
      },
      {
        "table_id": "MYSQL:common.dict_industry",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_industry",
        "columns": [
          "industry_code",
          "industry_name"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 175
      },
      {
        "table_id": "MYSQL:common.energy_type_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "energy_type_dict",
        "columns": [
          "type_code",
          "type_name",
          "category",
          "is_renewable"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 195
      },
      {
        "table_id": "MYSQL:common.voltage_level_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "voltage_level_dict",
        "columns": [
          "level_code",
          "level_name",
          "level_value",
          "category"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 215
      },
      {
        "table_id": "MYSQL:common.energy_position_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "energy_position_dict",
        "columns": [
          "position_code",
          "position_name",
          "category"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 234
      },
      {
        "table_id": "MYSQL:common.station_type_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "station_type_dict",
        "columns": [
          "type_code",
          "type_name",
          "category"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 258
      },
      {
        "table_id": "MYSQL:common.cert_type_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "cert_type_dict",
        "columns": [
          "cert_type_code",
          "cert_type_name",
          "category",
          "valid_years"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 276
      },
      {
        "table_id": "MYSQL:common.product_category",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "product_category",
        "columns": [
          "category_id",
          "category_name",
          "parent_category_id",
          "category_level",
          "sort_order"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 293
      },
      {
        "table_id": "MYSQL:common.customer_level_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "customer_level_dict",
        "columns": [
          "level_code",
          "level_name",
          "min_growth_value",
          "description",
          "sort_order"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 304
      },
      {
        "table_id": "MYSQL:common.customer_status_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "customer_status_dict",
        "columns": [
          "status_code",
          "status_name",
          "description"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 313
      },
      {
        "table_id": "MYSQL:common.product_status_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "product_status_dict",
        "columns": [
          "status_code",
          "status_name",
          "description"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 320
      },
      {
        "table_id": "MYSQL:common.order_status_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "order_status_dict",
        "columns": [
          "status_code",
          "status_name",
          "description"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 327
      },
      {
        "table_id": "MYSQL:common.payment_method_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "payment_method_dict",
        "columns": [
          "method_code",
          "method_name",
          "description"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 334
      },
      {
        "table_id": "MYSQL:common.payment_status_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "payment_status_dict",
        "columns": [
          "status_code",
          "status_name",
          "description"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 341
      },
      {
        "table_id": "MYSQL:common.refund_reason_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "refund_reason_dict",
        "columns": [
          "reason_code",
          "reason_name",
          "description"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 348
      },
      {
        "table_id": "MYSQL:common.order_channel_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "order_channel_dict",
        "columns": [
          "channel_code",
          "channel_name",
          "description"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 355
      },
      {
        "table_id": "MYSQL:common.platform_dict",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "platform_dict",
        "columns": [
          "platform_code",
          "platform_name",
          "description"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 362
      },
      {
        "table_id": "MYSQL:common.dict_gender",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_gender",
        "columns": [
          "gender_code",
          "gender_name"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 452
      },
      {
        "table_id": "MYSQL:common.dict_academic_level",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_academic_level",
        "columns": [
          "level_code",
          "level_name"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 459
      },
      {
        "table_id": "MYSQL:common.dict_student_status",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_student_status",
        "columns": [
          "status_code",
          "status_name"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 466
      },
      {
        "table_id": "MYSQL:common.dict_course_type",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_course_type",
        "columns": [
          "type_code",
          "type_name"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 473
      },
      {
        "table_id": "MYSQL:common.dict_exam_item",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_exam_item",
        "columns": [
          "item_code",
          "item_name",
          "default_weight"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 480
      },
      {
        "table_id": "MYSQL:common.dict_take_mode",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_take_mode",
        "columns": [
          "mode_code",
          "mode_name"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 488
      },
      {
        "table_id": "MYSQL:common.dict_semester_type",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_semester_type",
        "columns": [
          "semester_code",
          "semester_name",
          "season",
          "is_current"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 495
      },
      {
        "table_id": "MYSQL:common.dict_grade_level",
        "engine": "MYSQL",
        "database": "common",
        "schema": null,
        "object_type": "table",
        "name": "dict_grade_level",
        "columns": [
          "grade_level",
          "min_score",
          "max_score",
          "grade_point"
        ],
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "source_start_line": 504
      },
      {
        "table_id": "MYSQL:transportation.vehicle_company",
        "engine": "MYSQL",
        "database": "transportation",
        "schema": null,
        "object_type": "table",
        "name": "vehicle_company",
        "columns": [
          "company_id",
          "company_name",
          "business_type",
          "establish_date",
          "legal_person",
          "contact_phone",
          "address",
          "area_id",
          "status"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 6
      },
      {
        "table_id": "MYSQL:transportation.driver",
        "engine": "MYSQL",
        "database": "transportation",
        "schema": null,
        "object_type": "table",
        "name": "driver",
        "columns": [
          "driver_id",
          "name",
          "gender",
          "birth_date",
          "license_type",
          "issue_date",
          "valid_years",
          "phone",
          "address",
          "area_id",
          "status",
          "company_id"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 20
      },
      {
        "table_id": "MYSQL:transportation.vehicle",
        "engine": "MYSQL",
        "database": "transportation",
        "schema": null,
        "object_type": "table",
        "name": "vehicle",
        "columns": [
          "vehicle_id",
          "plate_number",
          "owner_id",
          "vehicle_type_code",
          "brand",
          "model",
          "manufacture_year",
          "load_capacity",
          "seat_count",
          "color",
          "register_date",
          "area_id",
          "insurance_expire",
          "company_id"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 41
      },
      {
        "table_id": "MYSQL:transportation.shipping_company",
        "engine": "MYSQL",
        "database": "transportation",
        "schema": null,
        "object_type": "table",
        "name": "shipping_company",
        "columns": [
          "company_id",
          "company_name",
          "business_type",
          "establish_date",
          "legal_person",
          "contact_phone",
          "address",
          "area_id",
          "status"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 66
      },
      {
        "table_id": "MYSQL:transportation.employee",
        "engine": "MYSQL",
        "database": "transportation",
        "schema": null,
        "object_type": "table",
        "name": "employee",
        "columns": [
          "employee_id",
          "name",
          "gender",
          "employee_type_code",
          "company_id",
          "hire_date",
          "phone",
          "status"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 80
      },
      {
        "table_id": "MYSQL:transportation.vessel",
        "engine": "MYSQL",
        "database": "transportation",
        "schema": null,
        "object_type": "table",
        "name": "vessel",
        "columns": [
          "mmsi",
          "company_id",
          "vessel_type",
          "max_load",
          "max_speed",
          "endurance",
          "captain_name",
          "area_id"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 94
      },
      {
        "table_id": "MYSQL:finance_tax.companies",
        "engine": "MYSQL",
        "database": "finance_tax",
        "schema": null,
        "object_type": "table",
        "name": "companies",
        "columns": [
          "company_id",
          "company_name",
          "stock_code",
          "established_year",
          "registered_capital",
          "industry_code",
          "registration_type_code",
          "is_private",
          "size_category_code",
          "is_key_high_tech",
          "is_tech_advanced_service"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 118
      },
      {
        "table_id": "MYSQL:finance_tax.stocks",
        "engine": "MYSQL",
        "database": "finance_tax",
        "schema": null,
        "object_type": "table",
        "name": "stocks",
        "columns": [
          "stock_id",
          "company_id",
          "stock_code",
          "stock_name",
          "stock_full_name",
          "share_right_type",
          "register_type",
          "par_value_type",
          "market_class",
          "listing_date",
          "total_shares",
          "current_price"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 137
      },
      {
        "table_id": "MYSQL:finance_tax.stock_daily_trades",
        "engine": "MYSQL",
        "database": "finance_tax",
        "schema": null,
        "object_type": "table",
        "name": "stock_daily_trades",
        "columns": [
          "trade_id",
          "stock_id",
          "trade_date",
          "volume",
          "avg_trade_size",
          "open_price",
          "close_price",
          "high_price",
          "low_price"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 155
      },
      {
        "table_id": "MYSQL:finance_tax.company_financials",
        "engine": "MYSQL",
        "database": "finance_tax",
        "schema": null,
        "object_type": "table",
        "name": "company_financials",
        "columns": [
          "financial_id",
          "company_id",
          "report_date",
          "dividend_cash",
          "dividend_stock",
          "total_assets",
          "total_liabilities"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 171
      },
      {
        "table_id": "MYSQL:finance_tax.corporate_income_tax_returns",
        "engine": "MYSQL",
        "database": "finance_tax",
        "schema": null,
        "object_type": "table",
        "name": "corporate_income_tax_returns",
        "columns": [
          "return_id",
          "company_id",
          "tax_year",
          "revenue",
          "non_taxable_income",
          "deductions",
          "prior_year_losses",
          "building_asset_value",
          "employee_count",
          "total_assets",
          "is_restricted_industry"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 185
      },
      {
        "table_id": "MYSQL:energy.energy_company",
        "engine": "MYSQL",
        "database": "energy",
        "schema": null,
        "object_type": "table",
        "name": "energy_company",
        "columns": [
          "company_id",
          "company_name",
          "business_type",
          "establish_date",
          "legal_person",
          "contact_phone",
          "area_id",
          "staff_count",
          "status"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 210
      },
      {
        "table_id": "MYSQL:energy.company_certification",
        "engine": "MYSQL",
        "database": "energy",
        "schema": null,
        "object_type": "table",
        "name": "company_certification",
        "columns": [
          "id",
          "company_id",
          "cert_type",
          "cert_no",
          "issue_date",
          "expire_date",
          "issue_authority"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 224
      },
      {
        "table_id": "MYSQL:energy.energy_station",
        "engine": "MYSQL",
        "database": "energy",
        "schema": null,
        "object_type": "table",
        "name": "energy_station",
        "columns": [
          "station_id",
          "station_name",
          "company_id",
          "station_type_code",
          "energy_type_code",
          "installed_capacity",
          "annual_generation",
          "grid_connect_date",
          "area_id",
          "status"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 236
      },
      {
        "table_id": "MYSQL:energy.supply_area",
        "engine": "MYSQL",
        "database": "energy",
        "schema": null,
        "object_type": "table",
        "name": "supply_area",
        "columns": [
          "id",
          "company_id",
          "area_id",
          "supply_level",
          "household_count",
          "annual_supply"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 254
      },
      {
        "table_id": "MYSQL:energy.employee",
        "engine": "MYSQL",
        "database": "energy",
        "schema": null,
        "object_type": "table",
        "name": "employee",
        "columns": [
          "employee_id",
          "name",
          "gender",
          "birth_date",
          "company_id",
          "station_id",
          "position_code",
          "hire_date",
          "phone",
          "education",
          "status"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 267
      },
      {
        "table_id": "MYSQL:education_2024.semester",
        "engine": "MYSQL",
        "database": "education_2024",
        "schema": null,
        "object_type": "table",
        "name": "semester",
        "columns": [
          "semester_id",
          "academic_year",
          "semester_code",
          "start_date_key",
          "end_date_key"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 290
      },
      {
        "table_id": "MYSQL:education_2024.department",
        "engine": "MYSQL",
        "database": "education_2024",
        "schema": null,
        "object_type": "table",
        "name": "department",
        "columns": [
          "department_id",
          "department_code",
          "department_name"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 299
      },
      {
        "table_id": "MYSQL:education_2024.teacher",
        "engine": "MYSQL",
        "database": "education_2024",
        "schema": null,
        "object_type": "table",
        "name": "teacher",
        "columns": [
          "teacher_id",
          "teacher_no",
          "teacher_name",
          "department_id",
          "gender_code",
          "phone",
          "region_id"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 306
      },
      {
        "table_id": "MYSQL:education_2024.class",
        "engine": "MYSQL",
        "database": "education_2024",
        "schema": null,
        "object_type": "table",
        "name": "class",
        "columns": [
          "class_id",
          "class_code",
          "class_name",
          "department_id",
          "grade_year"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 318
      },
      {
        "table_id": "MYSQL:education_2024.student",
        "engine": "MYSQL",
        "database": "education_2024",
        "schema": null,
        "object_type": "table",
        "name": "student",
        "columns": [
          "student_id",
          "student_no",
          "student_name",
          "gender_code",
          "academic_level_code",
          "department_id",
          "class_id",
          "home_region_id",
          "student_status_code",
          "admit_date_key"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 328
      },
      {
        "table_id": "MYSQL:education_2024.course",
        "engine": "MYSQL",
        "database": "education_2024",
        "schema": null,
        "object_type": "table",
        "name": "course",
        "columns": [
          "course_id",
          "course_code",
          "course_name",
          "department_id",
          "teacher_id",
          "credit",
          "course_type",
          "max_score"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 344
      },
      {
        "table_id": "MYSQL:education_2024.enrollment",
        "engine": "MYSQL",
        "database": "education_2024",
        "schema": null,
        "object_type": "table",
        "name": "enrollment",
        "columns": [
          "enrollment_id",
          "student_id",
          "course_id",
          "semester_id",
          "enroll_date_key",
          "take_mode",
          "is_withdraw"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 358
      },
      {
        "table_id": "MYSQL:education_2024.exam_score",
        "engine": "MYSQL",
        "database": "education_2024",
        "schema": null,
        "object_type": "table",
        "name": "exam_score",
        "columns": [
          "exam_score_id",
          "enrollment_id",
          "exam_item",
          "score",
          "score_date_key"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 372
      },
      {
        "table_id": "MYSQL:education_2025.semester",
        "engine": "MYSQL",
        "database": "education_2025",
        "schema": null,
        "object_type": "table",
        "name": "semester",
        "columns": [
          "semester_id",
          "academic_year",
          "semester_code",
          "start_date_key",
          "end_date_key"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 390
      },
      {
        "table_id": "MYSQL:education_2025.department",
        "engine": "MYSQL",
        "database": "education_2025",
        "schema": null,
        "object_type": "table",
        "name": "department",
        "columns": [
          "department_id",
          "department_code",
          "department_name"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 398
      },
      {
        "table_id": "MYSQL:education_2025.teacher",
        "engine": "MYSQL",
        "database": "education_2025",
        "schema": null,
        "object_type": "table",
        "name": "teacher",
        "columns": [
          "teacher_id",
          "teacher_no",
          "teacher_name",
          "department_id",
          "gender_code",
          "phone",
          "region_id"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 404
      },
      {
        "table_id": "MYSQL:education_2025.class",
        "engine": "MYSQL",
        "database": "education_2025",
        "schema": null,
        "object_type": "table",
        "name": "class",
        "columns": [
          "class_id",
          "class_code",
          "class_name",
          "department_id",
          "grade_year"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 415
      },
      {
        "table_id": "MYSQL:education_2025.student",
        "engine": "MYSQL",
        "database": "education_2025",
        "schema": null,
        "object_type": "table",
        "name": "student",
        "columns": [
          "student_id",
          "student_no",
          "student_name",
          "gender_code",
          "academic_level_code",
          "department_id",
          "class_id",
          "home_region_id",
          "student_status_code",
          "admit_date_key"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 424
      },
      {
        "table_id": "MYSQL:education_2025.course",
        "engine": "MYSQL",
        "database": "education_2025",
        "schema": null,
        "object_type": "table",
        "name": "course",
        "columns": [
          "course_id",
          "course_code",
          "course_name",
          "department_id",
          "teacher_id",
          "credit",
          "course_type",
          "max_score"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 439
      },
      {
        "table_id": "MYSQL:education_2025.enrollment",
        "engine": "MYSQL",
        "database": "education_2025",
        "schema": null,
        "object_type": "table",
        "name": "enrollment",
        "columns": [
          "enrollment_id",
          "student_id",
          "course_id",
          "semester_id",
          "enroll_date_key",
          "take_mode",
          "is_withdraw"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 452
      },
      {
        "table_id": "MYSQL:education_2025.exam_score",
        "engine": "MYSQL",
        "database": "education_2025",
        "schema": null,
        "object_type": "table",
        "name": "exam_score",
        "columns": [
          "exam_score_id",
          "enrollment_id",
          "exam_item",
          "score",
          "score_date_key"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 465
      },
      {
        "table_id": "MYSQL:ecommerce.customer",
        "engine": "MYSQL",
        "database": "ecommerce",
        "schema": null,
        "object_type": "table",
        "name": "customer",
        "columns": [
          "customer_id",
          "customer_name",
          "gender",
          "phone",
          "email",
          "level_code",
          "status_code",
          "province_code",
          "city_code",
          "register_time",
          "last_login_time",
          "growth_value"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 483
      },
      {
        "table_id": "MYSQL:ecommerce.product",
        "engine": "MYSQL",
        "database": "ecommerce",
        "schema": null,
        "object_type": "table",
        "name": "product",
        "columns": [
          "product_id",
          "product_name",
          "category_id",
          "brand_name",
          "status_code",
          "sale_price",
          "cost_price",
          "listed_time"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 504
      },
      {
        "table_id": "MYSQL:ecommerce.inventory",
        "engine": "MYSQL",
        "database": "ecommerce",
        "schema": null,
        "object_type": "table",
        "name": "inventory",
        "columns": [
          "inventory_id",
          "product_id",
          "warehouse_code",
          "warehouse_name",
          "province_code",
          "city_code",
          "stock_quantity",
          "locked_quantity",
          "safety_stock",
          "updated_time"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 520
      },
      {
        "table_id": "MYSQL:ecommerce.orders",
        "engine": "MYSQL",
        "database": "ecommerce",
        "schema": null,
        "object_type": "table",
        "name": "orders",
        "columns": [
          "order_id",
          "order_no",
          "customer_id",
          "order_status_code",
          "order_channel_code",
          "platform_code",
          "order_time",
          "pay_time",
          "finish_time",
          "total_amount",
          "discount_amount",
          "freight_amount",
          "payable_amount",
          "receiver_province_code",
          "receiver_city_code"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 538
      },
      {
        "table_id": "MYSQL:ecommerce.order_item",
        "engine": "MYSQL",
        "database": "ecommerce",
        "schema": null,
        "object_type": "table",
        "name": "order_item",
        "columns": [
          "order_item_id",
          "order_id",
          "product_id",
          "quantity",
          "unit_price",
          "discount_amount",
          "item_amount",
          "item_cost_amount",
          "refund_quantity",
          "refund_amount",
          "refund_reason_code"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 564
      },
      {
        "table_id": "MYSQL:ecommerce.payment",
        "engine": "MYSQL",
        "database": "ecommerce",
        "schema": null,
        "object_type": "table",
        "name": "payment",
        "columns": [
          "payment_id",
          "payment_no",
          "order_id",
          "payment_method_code",
          "payment_status_code",
          "payment_amount",
          "refund_amount",
          "paid_time",
          "created_time"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 584
      },
      {
        "table_id": "POSTGRESQL:public.vessel_ais_data",
        "engine": "POSTGRESQL",
        "database": null,
        "schema": "public",
        "object_type": "table",
        "name": "vessel_ais_data",
        "columns": [
          "id",
          "mmsi",
          "timestamp",
          "longitude",
          "latitude",
          "sog",
          "cog",
          "heading",
          "nav_status",
          "rot",
          "destination",
          "draught",
          "vessel_type",
          "imo",
          "call_sign",
          "eta",
          "last_update",
          "geom"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 633
      },
      {
        "table_id": "Elasticsearch:medical_institutions",
        "engine": "Elasticsearch",
        "database": null,
        "schema": null,
        "object_type": "index",
        "name": "medical_institutions",
        "columns": [
          "name",
          "name.keyword",
          "city",
          "district",
          "address",
          "location",
          "level",
          "bed_count",
          "doctor_count",
          "nurse_count",
          "ambulance_count",
          "department_count",
          "annual_outpatient",
          "has_icu",
          "is_teaching_hospital",
          "emergency_24h",
          "rating",
          "founded_year"
        ],
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "source_start_line": 606
      }
    ],
    "schema_sources": [
      {
        "source_file": "data/赛题8/Schema/commom_schema.txt",
        "encoding": "utf-8-sig",
        "sha256": "a6e0b1048576e4d55b66e496aff505047c2aca0a8f87ae0bde87329ca8ed8e94",
        "text": "-- 创建通用字典库\r\nCREATE DATABASE IF NOT EXISTS common;\r\nUSE common;\r\n\r\n-- 行政区划字典表\r\nCREATE TABLE IF NOT EXISTS administrative_division (\r\n    id CHAR(6) PRIMARY KEY COMMENT '行政区划代码',\r\n    name VARCHAR(50) NOT NULL COMMENT '行政区划名称',\r\n    full_name VARCHAR(100) NOT NULL COMMENT '行政区划全称',\r\n    province_name VARCHAR(20) NOT NULL COMMENT '省级名称',\r\n    city_name VARCHAR(20) NOT NULL COMMENT '市级名称',\r\n    county_name VARCHAR(20) NOT NULL COMMENT '县级名称',\r\n    level TINYINT NOT NULL COMMENT '级别(1:省/直辖市,2:市,3:区县)',\r\n    longitude DECIMAL(10, 6) COMMENT '经度',\r\n    latitude DECIMAL(10, 6) COMMENT '纬度'\r\n) ENGINE=InnoDB COMMENT='统一行政区划表';\r\n\r\n-- 行政区划示例数据\r\nINSERT INTO administrative_division (id, name, full_name, province_name, city_name, county_name, level, longitude, latitude)\r\nVALUES\r\n('310000', '上海市', '上海市', '', '', '', 1, NULL, NULL),\r\n('310101', '黄浦区', '上海市-黄浦区', '上海市', '黄浦区', '', 3, NULL, NULL),\r\n('310115', '浦东新区', '上海市-浦东新区', '上海市', '浦东新区', '', 3, NULL, NULL),\r\n('320500', '苏州市', '江苏省-苏州市', '江苏省', '苏州市', '', 2, NULL, NULL),\r\n('320100', '南京市', '江苏省-南京市', '江苏省', '南京市', '', 2, NULL, NULL),\r\n('320102', '玄武区', '江苏省-南京市-玄武区', '江苏省', '南京市', '玄武区', 3, NULL, NULL),\r\n('320115', '江宁区', '江苏省-南京市-江宁区', '江苏省', '南京市', '江宁区', 3, NULL, NULL);\r\n\r\n-- 交通库\r\n-- 车辆类型字典表\r\nCREATE TABLE vehicle_type_dict (\r\n    type_code VARCHAR(20) PRIMARY KEY COMMENT '类型代码',\r\n    type_name VARCHAR(50) NOT NULL COMMENT '类型名称（客车/货车/危化品车等）',\r\n    category VARCHAR(20) COMMENT '大类'\r\n) ENGINE=InnoDB COMMENT='车辆类型字典';\r\n\r\n-- 船舶类型字典表\r\nCREATE TABLE vessel_type_dict (\r\n    type_code SMALLINT PRIMARY KEY COMMENT 'AIS船舶类型代码',\r\n    type_name VARCHAR(50) NOT NULL COMMENT '类型名称',\r\n    category VARCHAR(20) COMMENT '大类'\r\n) ENGINE=InnoDB COMMENT='船舶类型字典';\r\n\r\n-- 人员类型字典表\r\nCREATE TABLE employee_type_dict (\r\n    type_code VARCHAR(20) PRIMARY KEY COMMENT '人员类型代码',\r\n    type_name VARCHAR(50) NOT NULL COMMENT '类型名称（船长/大副/轮机长/水手等）'\r\n) ENGINE=InnoDB COMMENT='人员类型字典';\r\n\r\n-- 驾照类型字典表\r\nCREATE TABLE license_type_dict (\r\n    license_code VARCHAR(5) PRIMARY KEY COMMENT '驾照代码',\r\n    license_name VARCHAR(50) NOT NULL COMMENT '驾照名称'\r\n) ENGINE=InnoDB COMMENT='驾照类型字典';\r\n\r\n-- 车辆类型字典\r\nINSERT INTO common.vehicle_type_dict (type_code, type_name, category) VALUES\r\n('BUS', '客车', '客运'),\r\n('TRUCK', '货车', '货运'),\r\n('HAZMAT', '危化品车', '特种'),\r\n('VAN', '面包车', '货运'),\r\n('MINIBUS', '小型客车', '客运'),\r\n('DUMP', '自卸车', '货运'),\r\n('TANKER', '罐式车', '特种'),\r\n('REFRIGERATED', '冷藏车', '特种');\r\n\r\n-- 船舶类型字典\r\nINSERT INTO common.vessel_type_dict (type_code, type_name, category) VALUES\r\n(20, '客船', '客运'),\r\n(21, '高速客船', '客运'),\r\n(30, '货船', '货运'),\r\n(31, '散货船', '货运'),\r\n(32, '集装箱船', '货运'),\r\n(33, '滚装船', '货运'),\r\n(34, '液化气船', '特种'),\r\n(35, '油轮', '货运'),\r\n(36, '化学品船', '特种'),\r\n(37, '冷藏船', '货运'),\r\n(40, '拖船', '作业'),\r\n(41, '挖泥船', '作业'),\r\n(42, '消防船', '公务'),\r\n(43, '医疗船', '公务'),\r\n(50, '引航船', '作业'),\r\n(51, '搜救船', '公务'),\r\n(52, '交通船', '作业'),\r\n(53, '公务船', '公务'),\r\n(60, '帆船', '娱乐'),\r\n(70, '渔船', '渔业'),\r\n(71, '拖网渔船', '渔业'),\r\n(80, '军事舰艇', '军事'),\r\n(90, '其他', '其他');\r\n\r\n-- 人员类型字典 (employee_type_dict) 用于船舶公司员工\r\nINSERT INTO common.employee_type_dict (type_code, type_name) VALUES\r\n('CAPTAIN', '船长'),\r\n('CHIEF_OFFICER', '大副'),\r\n('SECOND_OFFICER', '二副'),\r\n('THIRD_OFFICER', '三副'),\r\n('CHIEF_ENGINEER', '轮机长'),\r\n('SECOND_ENGINEER', '大管轮'),\r\n('THIRD_ENGINEER', '二管轮'),\r\n('ELECTRICIAN', '电机员'),\r\n('BOSUN', '水手长'),\r\n('ABLE_SEAMAN', '一级水手'),\r\n('ORDINARY_SEAMAN', '二级水手'),\r\n('OILER', '加油工'),\r\n('COOK', '厨师'),\r\n('STEWARD', '服务员'),\r\n('PURSER', '事务长'),\r\n('MEDICAL', '船医');\r\n\r\n-- 驾照类型字典\r\nINSERT INTO common.license_type_dict (license_code, license_name) VALUES\r\n('A1', '大型客车'),\r\n('A2', '牵引车'),\r\n('A3', '城市公交车'),\r\n('B1', '中型客车'),\r\n('B2', '大型货车'),\r\n('C1', '小型汽车'),\r\n('C2', '小型自动挡汽车'),\r\n('C3', '低速载货汽车'),\r\n('C4', '三轮汽车');\r\n\r\n-- 金融库\r\n-- 登记注册类型字典表\r\nCREATE TABLE dict_registration_type (\r\n    type_code VARCHAR(20) PRIMARY KEY COMMENT '注册类型代码',\r\n    type_name VARCHAR(100) NOT NULL COMMENT '注册类型名称',\r\n    description VARCHAR(200) COMMENT '说明'\r\n) COMMENT='企业登记注册类型字典';\r\n\r\nINSERT INTO dict_registration_type (type_code, type_name) VALUES\r\n('111', '国有独资公司'),\r\n('112', '有限责任公司'),\r\n('113', '股份有限公司'),\r\n('114', '私营有限责任公司'),\r\n('115', '私营股份有限公司'),\r\n('116', '外商投资企业'),\r\n('117', '港澳台商投资企业'),\r\n('118', '合伙企业');\r\n\r\n-- 企业规模划型字典表\r\nCREATE TABLE dict_size_category (\r\n    size_code VARCHAR(10) PRIMARY KEY COMMENT '规模代码',\r\n    size_name VARCHAR(20) NOT NULL COMMENT '规模名称'\r\n) COMMENT='企业规模划型字典';\r\n\r\nINSERT INTO dict_size_category (size_code, size_name) VALUES\r\n('L', '大型'),\r\n('M', '中型'),\r\n('S', '小型'),\r\n('XS', '微型');\r\n\r\n-- 股票分类字典表\r\nCREATE TABLE dict_stock_type (\r\n    type_category VARCHAR(30) COMMENT '分类维度',\r\n    type_code VARCHAR(20) COMMENT '类型代码',\r\n    type_name VARCHAR(50) NOT NULL COMMENT '类型名称',\r\n    PRIMARY KEY (type_category, type_code)\r\n) COMMENT='股票分类字典';\r\n\r\nINSERT INTO dict_stock_type (type_category, type_code, type_name) VALUES\r\n('SHARE_RIGHT', 'COMMON', '普通股'),\r\n('SHARE_RIGHT', 'PREFERRED', '优先股'),\r\n('REGISTER', 'REGISTERED', '记名股票'),\r\n('REGISTER', 'BEARER', '无记名股票'),\r\n('PAR_VALUE', 'PAR', '面额股票'),\r\n('PAR_VALUE', 'NO_PAR', '无面额股票'),\r\n('MARKET_CLASS', 'A', 'A股'),\r\n('MARKET_CLASS', 'B', 'B股'),\r\n('MARKET_CLASS', 'H', 'H股'),\r\n('MARKET_CLASS', 'N', 'N股');\r\n\r\n-- 行业分类字典表\r\nCREATE TABLE dict_industry (\r\n    industry_code VARCHAR(20) PRIMARY KEY COMMENT '行业代码（国标）',\r\n    industry_name VARCHAR(100) NOT NULL COMMENT '行业名称'\r\n) COMMENT='行业分类字典';\r\n\r\nINSERT INTO dict_industry (industry_code, industry_name) VALUES\r\n('I65', '软件和信息技术服务业'),\r\n('C39', '计算机、通信和其他电子设备制造业'),\r\n('L72', '商务服务业'),\r\n('C26', '化学原料和化学制品制造业'),\r\n('C27', '医药制造业'),\r\n('B06', '石油和天然气开采业'),\r\n('G60', '交通运输、仓储和邮政业'),\r\n('K70', '房地产业'),\r\n('J66', '金融业');\r\n\r\n\r\n\r\n-- 工业库\r\n-- 能源类型字典\r\nCREATE TABLE energy_type_dict (\r\n    type_code VARCHAR(10) PRIMARY KEY COMMENT '能源类型代码',\r\n    type_name VARCHAR(30) NOT NULL COMMENT '类型名称',\r\n    category VARCHAR(20) COMMENT '大类',\r\n    is_renewable TINYINT(1) DEFAULT 0 COMMENT '是否可再生'\r\n) ENGINE=InnoDB COMMENT='能源类型字典';\r\n\r\nINSERT INTO energy_type_dict (type_code, type_name, category, is_renewable) VALUES\r\n('THERMAL', '火电', '传统能源', 0),\r\n('HYDRO', '水电', '清洁能源', 1),\r\n('WIND', '风电', '新能源', 1),\r\n('SOLAR', '光伏', '新能源', 1),\r\n('NUCLEAR', '核电', '清洁能源', 0),\r\n('BIOMASS', '生物质发电', '新能源', 1),\r\n('GAS', '天然气发电', '清洁能源', 0),\r\n('PUMPED', '抽水蓄能', '清洁能源', 1),\r\n('GEOTHERMAL', '地热发电', '新能源', 1),\r\n('HYDROGEN', '氢能', '新能源', 1);\r\n\r\n-- 电压等级字典\r\nCREATE TABLE voltage_level_dict (\r\n    level_code VARCHAR(10) PRIMARY KEY COMMENT '电压等级代码',\r\n    level_name VARCHAR(20) NOT NULL COMMENT '等级名称',\r\n    level_value INT COMMENT '电压值(kV)',\r\n    category VARCHAR(20) COMMENT '类别'\r\n) ENGINE=InnoDB COMMENT='电压等级字典';\r\n\r\nINSERT INTO voltage_level_dict (level_code, level_name, level_value, category) VALUES\r\n('LV', '低压', 0, '低压'),\r\n('MV10', '10kV', 10, '中压'),\r\n('MV35', '35kV', 35, '中压'),\r\n('HV110', '110kV', 110, '高压'),\r\n('HV220', '220kV', 220, '高压'),\r\n('EHV330', '330kV', 330, '超高压'),\r\n('EHV500', '500kV', 500, '超高压'),\r\n('EHV750', '750kV', 750, '超高压'),\r\n('UHV1000', '1000kV', 1000, '特高压');\r\n\r\n-- 员工岗位字典\r\nCREATE TABLE energy_position_dict (\r\n    position_code VARCHAR(20) PRIMARY KEY COMMENT '岗位代码',\r\n    position_name VARCHAR(50) NOT NULL COMMENT '岗位名称',\r\n    category VARCHAR(30) COMMENT '类别'\r\n) ENGINE=InnoDB COMMENT='能源行业岗位字典';\r\n\r\nINSERT INTO energy_position_dict (position_code, position_name, category) VALUES\r\n('GM', '总经理', '管理'),\r\n('DM', '副总经理', '管理'),\r\n('CE', '总工程师', '技术'),\r\n('PM', '项目经理', '管理'),\r\n('OE', '运行工程师', '运行'),\r\n('ME', '检修工程师', '检修'),\r\n('SE', '安全工程师', '管理'),\r\n('EE', '电气工程师', '技术'),\r\n('TE', '热控工程师', '技术'),\r\n('CE2', '土建工程师', '技术'),\r\n('OP', '值班员', '运行'),\r\n('MT', '检修工', '检修'),\r\n('EL', '电工', '检修'),\r\n('AD', '行政专员', '管理'),\r\n('HR', '人事专员', '管理');\r\n\r\n-- 场站类型字典\r\nCREATE TABLE station_type_dict (\r\n    type_code VARCHAR(10) PRIMARY KEY COMMENT '场站类型代码',\r\n    type_name VARCHAR(50) NOT NULL COMMENT '类型名称',\r\n    category VARCHAR(30) COMMENT '大类'\r\n) ENGINE=InnoDB COMMENT='场站类型字典';\r\n\r\nINSERT INTO station_type_dict (type_code, type_name, category) VALUES\r\n('PP', '发电厂', '发电'),\r\n('SUB', '变电站', '变电'),\r\n('TL', '输电线路', '输电'),\r\n('DS', '配电站', '配电'),\r\n('WP', '风电场', '发电'),\r\n('SP', '光伏电站', '发电'),\r\n('HP', '水电站', '发电'),\r\n('NP', '核电站', '发电'),\r\n('ES', '储能站', '配电'),\r\n('CC', '集控中心', '变电');\r\n\r\nCREATE TABLE cert_type_dict (\r\n    cert_type_code VARCHAR(20) PRIMARY KEY COMMENT '资质类型代码',\r\n    cert_type_name VARCHAR(50) NOT NULL COMMENT '资质类型名称',\r\n    category VARCHAR(20) COMMENT '类别',\r\n    valid_years TINYINT COMMENT '有效期(年)'\r\n) ENGINE=InnoDB COMMENT='资质类型字典';\r\n\r\nINSERT INTO cert_type_dict (cert_type_code, cert_type_name, category, valid_years) VALUES\r\n('POWER_SUPPLY', '供电类电力业务许可证', '电力业务', 20),\r\n('POWER_GEN', '发电类电力业务许可证', '电力业务', 20),\r\n('POWER_NEW', '新能源类电力业务许可证', '电力业务', 20),\r\n('INSTALL_REPAIR', '承装修试许可证', '承装修试', 5),\r\n('SAFETY', '安全生产许可证', '安全', 3);\r\n\r\n\r\n\r\n-- 电商\r\nCREATE TABLE product_category (\r\n  category_id BIGINT NOT NULL COMMENT '商品分类ID',\r\n  category_name VARCHAR(100) NOT NULL COMMENT '商品分类名称',\r\n  parent_category_id BIGINT DEFAULT NULL COMMENT '父级商品分类ID',\r\n  category_level TINYINT NOT NULL COMMENT '分类层级',\r\n  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序号',\r\n  PRIMARY KEY (category_id),\r\n  KEY idx_category_parent (parent_category_id),\r\n  KEY idx_category_level (category_level)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表';\r\n\r\nCREATE TABLE customer_level_dict (\r\n  level_code VARCHAR(32) NOT NULL COMMENT '用户等级编码',\r\n  level_name VARCHAR(64) NOT NULL COMMENT '用户等级名称',\r\n  min_growth_value INT NOT NULL DEFAULT 0 COMMENT '最低成长值',\r\n  description VARCHAR(255) DEFAULT NULL COMMENT '说明',\r\n  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序号',\r\n  PRIMARY KEY (level_code)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户等级字典';\r\n\r\nCREATE TABLE customer_status_dict (\r\n  status_code VARCHAR(32) NOT NULL COMMENT '用户状态编码',\r\n  status_name VARCHAR(64) NOT NULL COMMENT '用户状态名称',\r\n  description VARCHAR(255) DEFAULT NULL COMMENT '说明',\r\n  PRIMARY KEY (status_code)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户状态字典';\r\n\r\nCREATE TABLE product_status_dict (\r\n  status_code VARCHAR(32) NOT NULL COMMENT '商品状态编码',\r\n  status_name VARCHAR(64) NOT NULL COMMENT '商品状态名称',\r\n  description VARCHAR(255) DEFAULT NULL COMMENT '说明',\r\n  PRIMARY KEY (status_code)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品状态字典';\r\n\r\nCREATE TABLE order_status_dict (\r\n  status_code VARCHAR(32) NOT NULL COMMENT '订单状态编码',\r\n  status_name VARCHAR(64) NOT NULL COMMENT '订单状态名称',\r\n  description VARCHAR(255) DEFAULT NULL COMMENT '说明',\r\n  PRIMARY KEY (status_code)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单状态字典';\r\n\r\nCREATE TABLE payment_method_dict (\r\n  method_code VARCHAR(32) NOT NULL COMMENT '支付方式编码',\r\n  method_name VARCHAR(64) NOT NULL COMMENT '支付方式名称',\r\n  description VARCHAR(255) DEFAULT NULL COMMENT '说明',\r\n  PRIMARY KEY (method_code)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付方式字典';\r\n\r\nCREATE TABLE payment_status_dict (\r\n  status_code VARCHAR(32) NOT NULL COMMENT '支付状态编码',\r\n  status_name VARCHAR(64) NOT NULL COMMENT '支付状态名称',\r\n  description VARCHAR(255) DEFAULT NULL COMMENT '说明',\r\n  PRIMARY KEY (status_code)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付状态字典';\r\n\r\nCREATE TABLE refund_reason_dict (\r\n  reason_code VARCHAR(32) NOT NULL COMMENT '退款原因编码',\r\n  reason_name VARCHAR(64) NOT NULL COMMENT '退款原因名称',\r\n  description VARCHAR(255) DEFAULT NULL COMMENT '说明',\r\n  PRIMARY KEY (reason_code)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='退款原因字典';\r\n\r\nCREATE TABLE order_channel_dict (\r\n  channel_code VARCHAR(32) NOT NULL COMMENT '下单渠道编码',\r\n  channel_name VARCHAR(64) NOT NULL COMMENT '下单渠道名称',\r\n  description VARCHAR(255) DEFAULT NULL COMMENT '说明',\r\n  PRIMARY KEY (channel_code)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='下单渠道字典';\r\n\r\nCREATE TABLE platform_dict (\r\n  platform_code VARCHAR(32) NOT NULL COMMENT '销售平台编码',\r\n  platform_name VARCHAR(64) NOT NULL COMMENT '销售平台名称',\r\n  description VARCHAR(255) DEFAULT NULL COMMENT '说明',\r\n  PRIMARY KEY (platform_code)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售平台字典';\r\n\r\nINSERT INTO product_category (category_id, category_name, parent_category_id, category_level, sort_order) VALUES\r\n  (1000, '数码家电', NULL, 1, 1),\r\n  (1100, '手机通讯', 1000, 2, 1),\r\n  (1200, '电脑办公', 1000, 2, 2),\r\n  (1300, '家用电器', 1000, 2, 3),\r\n  (2000, '服饰鞋包', NULL, 1, 2),\r\n  (2100, '男装', 2000, 2, 1),\r\n  (2200, '女装', 2000, 2, 2),\r\n  (2300, '鞋靴', 2000, 2, 3),\r\n  (3000, '食品生鲜', NULL, 1, 3),\r\n  (3100, '休闲零食', 3000, 2, 1),\r\n  (3200, '粮油调味', 3000, 2, 2),\r\n  (3300, '水果生鲜', 3000, 2, 3),\r\n  (4000, '美妆个护', NULL, 1, 4),\r\n  (4100, '护肤', 4000, 2, 1),\r\n  (4200, '彩妆', 4000, 2, 2),\r\n  (4300, '个人护理', 4000, 2, 3),\r\n  (5000, '母婴玩具', NULL, 1, 5),\r\n  (5100, '婴童用品', 5000, 2, 1),\r\n  (5200, '玩具乐器', 5000, 2, 2),\r\n  (6000, '运动户外', NULL, 1, 6),\r\n  (6100, '运动服饰', 6000, 2, 1),\r\n  (6200, '户外装备', 6000, 2, 2);\r\n\r\nINSERT INTO customer_level_dict (level_code, level_name, min_growth_value, description, sort_order) VALUES\r\n  ('NORMAL', '普通会员', 0, '默认会员等级', 1),\r\n  ('SILVER', '银卡会员', 1000, '中等活跃用户', 2),\r\n  ('GOLD', '金卡会员', 5000, '高价值用户', 3),\r\n  ('DIAMOND', '钻石会员', 20000, '核心高价值用户', 4);\r\n\r\nINSERT INTO customer_status_dict (status_code, status_name, description) VALUES\r\n  ('ACTIVE', '正常', '用户账号可正常下单'),\r\n  ('FROZEN', '冻结', '用户账号被限制操作'),\r\n  ('CANCELLED', '注销', '用户账号已注销');\r\n\r\nINSERT INTO product_status_dict (status_code, status_name, description) VALUES\r\n  ('ON_SALE', '上架', '商品正在销售'),\r\n  ('OFF_SALE', '下架', '商品已停止销售'),\r\n  ('SOLD_OUT', '缺货', '商品暂无可售库存');\r\n\r\nINSERT INTO order_status_dict (status_code, status_name, description) VALUES\r\n  ('PENDING_PAY', '待支付', '订单已创建但未支付'),\r\n  ('PAID', '已支付', '订单已完成支付'),\r\n  ('SHIPPED', '已发货', '订单已发货'),\r\n  ('COMPLETED', '已完成', '订单交易完成'),\r\n  ('CANCELLED', '已取消', '订单已取消'),\r\n  ('REFUNDED', '已退款', '订单已退款');\r\n\r\nINSERT INTO payment_method_dict (method_code, method_name, description) VALUES\r\n  ('ALIPAY', '支付宝', '使用支付宝支付'),\r\n  ('WECHAT', '微信支付', '使用微信支付'),\r\n  ('BANK_CARD', '银行卡', '使用银行卡支付'),\r\n  ('BALANCE', '账户余额', '使用平台账户余额支付');\r\n\r\nINSERT INTO payment_status_dict (status_code, status_name, description) VALUES\r\n  ('SUCCESS', '支付成功', '支付已成功入账'),\r\n  ('FAILED', '支付失败', '支付未成功'),\r\n  ('REFUNDING', '退款中', '退款流程处理中'),\r\n  ('REFUNDED', '已退款', '支付金额已退回');\r\n\r\nINSERT INTO refund_reason_dict (reason_code, reason_name, description) VALUES\r\n  ('QUALITY', '质量问题', '商品存在质量问题'),\r\n  ('WRONG_ITEM', '错发漏发', '商品错发或漏发'),\r\n  ('NO_REASON', '七天无理由', '用户无理由退货'),\r\n  ('OUT_OF_STOCK', '缺货退款', '商家缺货导致退款'),\r\n  ('OTHER', '其他原因', '其他退款原因');\r\n\r\nINSERT INTO order_channel_dict (channel_code, channel_name, description) VALUES\r\n  ('APP', '手机App', '用户通过手机App下单'),\r\n  ('MINI_PROGRAM', '小程序', '用户通过小程序下单'),\r\n  ('WEB', '网页端', '用户通过网页端下单'),\r\n  ('LIVE', '直播间', '用户通过直播间下单');\r\n\r\nINSERT INTO platform_dict (platform_code, platform_name, description) VALUES\r\n  ('TMALL', '天猫', '天猫销售平台'),\r\n  ('JD', '京东', '京东销售平台'),\r\n  ('PDD', '拼多多', '拼多多销售平台'),\r\n  ('SELF', '自营商城', '品牌自营商城');\r\n\r\n\r\n-- 教育\r\n-- 1. 性别字典\r\nDROP TABLE IF EXISTS dict_gender;\r\nCREATE TABLE dict_gender (\r\n    gender_code CHAR(1) PRIMARY KEY COMMENT '性别代码(M/F)',\r\n    gender_name VARCHAR(10) NOT NULL COMMENT '性别名称'\r\n);\r\n\r\n-- 2. 学历层次字典\r\nDROP TABLE IF EXISTS dict_academic_level;\r\nCREATE TABLE dict_academic_level (\r\n    level_code VARCHAR(20) PRIMARY KEY COMMENT '学历代码(UNDERGRAD/MASTER等)',\r\n    level_name VARCHAR(50) NOT NULL COMMENT '学历名称'\r\n);\r\n\r\n-- 3. 学生状态字典\r\nDROP TABLE IF EXISTS dict_student_status;\r\nCREATE TABLE dict_student_status (\r\n    status_code VARCHAR(20) PRIMARY KEY COMMENT '状态代码(ACTIVE/INACTIVE/GRADUATED等)',\r\n    status_name VARCHAR(50) NOT NULL COMMENT '状态名称'\r\n);\r\n\r\n-- 4. 课程类型字典\r\nDROP TABLE IF EXISTS dict_course_type;\r\nCREATE TABLE dict_course_type (\r\n    type_code VARCHAR(20) PRIMARY KEY COMMENT '课程类型代码',\r\n    type_name VARCHAR(50) NOT NULL COMMENT '课程类型名称'\r\n);\r\n\r\n-- 5. 考试项目字典\r\nDROP TABLE IF EXISTS dict_exam_item;\r\nCREATE TABLE dict_exam_item (\r\n    item_code VARCHAR(20) PRIMARY KEY COMMENT '考试项目代码',\r\n    item_name VARCHAR(50) NOT NULL COMMENT '考试项目名称',\r\n    default_weight DECIMAL(5,2) COMMENT '默认权重（如平时成绩占30%）'\r\n);\r\n\r\n-- 6. 选课方式字典\r\nDROP TABLE IF EXISTS dict_take_mode;\r\nCREATE TABLE dict_take_mode (\r\n    mode_code VARCHAR(20) PRIMARY KEY COMMENT '选课方式代码',\r\n    mode_name VARCHAR(50) NOT NULL COMMENT '选课方式名称'\r\n);\r\n\r\n-- 7. 学期字典（与业务库中的 semester 表互补，用于描述学期性质）\r\nDROP TABLE IF EXISTS dict_semester_type;\r\nCREATE TABLE dict_semester_type (\r\n    semester_code VARCHAR(20) PRIMARY KEY COMMENT '学期代码（如2024-FALL）',\r\n    semester_name VARCHAR(50) NOT NULL COMMENT '学期名称',\r\n    season VARCHAR(10) COMMENT '季节(SPRING/FALL/SUMMER)',\r\n    is_current TINYINT(1) COMMENT '是否为当前学期'\r\n);\r\n\r\n-- 8. 成绩等级参考表\r\nDROP TABLE IF EXISTS dict_grade_level;\r\nCREATE TABLE dict_grade_level (\r\n    grade_level CHAR(2) PRIMARY KEY COMMENT '等级(A/B/C/D/F)',\r\n    min_score INT COMMENT '最低分数',\r\n    max_score INT COMMENT '最高分数',\r\n    grade_point DECIMAL(3,2) COMMENT '绩点'\r\n);\r\n\r\n-- 1. 性别\r\nDELETE FROM dict_gender;\r\nINSERT INTO dict_gender (gender_code, gender_name) VALUES\r\n('M', '男'),\r\n('F', '女');\r\n\r\n-- 2. 学历层次\r\nDELETE FROM dict_academic_level;\r\nINSERT INTO dict_academic_level (level_code, level_name) VALUES\r\n('UNDERGRAD', '本科'),\r\n('MASTER', '硕士'),\r\n('DOCTOR', '博士');\r\n\r\n-- 3. 学生状态\r\nDELETE FROM dict_student_status;\r\nINSERT INTO dict_student_status (status_code, status_name) VALUES\r\n('ACTIVE', '在读'),\r\n('INACTIVE', '休学'),\r\n('GRADUATED', '已毕业'),\r\n('SUSPENDED', '退学'),\r\n('EXPIRED', '逾期未注册');\r\n\r\n-- 4. 课程类型\r\nDELETE FROM dict_course_type;\r\nINSERT INTO dict_course_type (type_code, type_name) VALUES\r\n('必修', '必修课'),\r\n('选修', '选修课'),\r\n('通识', '通识选修课'),\r\n('实践', '实践环节');\r\n\r\n-- 5. 考试项目\r\nDELETE FROM dict_exam_item;\r\nINSERT INTO dict_exam_item (item_code, item_name, default_weight) VALUES\r\n('平时', '平时成绩', 0.35),\r\n('期中', '期中考试', 0.45),\r\n('期末', '期末考试', 0.75);\r\n\r\n-- 6. 选课方式\r\nDELETE FROM dict_take_mode;\r\nINSERT INTO dict_take_mode (mode_code, mode_name) VALUES\r\n('线下', '线下课程'),\r\n('线上', '线上课程'),\r\n('混合', '线上线下混合');\r\n\r\n-- 7. 学期字典\r\nDELETE FROM dict_semester_type;\r\nINSERT INTO dict_semester_type (semester_code, semester_name, season, is_current) VALUES\r\n('2024-FALL', '2024年秋季学期', 'FALL', 0),\r\n('2025-SPRING', '2025年春季学期', 'SPRING', 1);\r\n\r\n-- 8. 成绩等级参考\r\nDELETE FROM dict_grade_level;\r\nINSERT INTO dict_grade_level (grade_level, min_score, max_score, grade_point) VALUES\r\n('A', 90, 100, 4.0),\r\n('B', 80, 89, 3.0),\r\n('C', 70, 79, 2.0),\r\n('D', 60, 69, 1.0),\r\n('F', 0, 59, 0.0);"
      },
      {
        "source_file": "data/赛题8/Schema/core_schema.txt",
        "encoding": "gb18030",
        "sha256": "936e4a96d43515d3570dc213dee83a836cc74d9584a9a1ce875c97dfb8248bad",
        "text": "-- =====================================================\r\n-- 交通库相关表\r\nCREATE DATABASE IF NOT EXISTS transportation;\r\nUSE transportation;\r\n-- 1. 车辆公司表\r\nCREATE TABLE vehicle_company (\r\n    company_id VARCHAR(20) PRIMARY KEY COMMENT '车辆公司编号',\r\n    company_name VARCHAR(100) NOT NULL COMMENT '公司名称',\r\n    business_type VARCHAR(50) NOT NULL COMMENT '经营类型（客运/货运/危化品运输）',\r\n    establish_date DATE COMMENT '成立日期',\r\n    legal_person VARCHAR(50) COMMENT '法人',\r\n    contact_phone VARCHAR(20) COMMENT '联系电话',\r\n    address VARCHAR(200) COMMENT '公司地址',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    status ENUM('运营','停业','注销') DEFAULT '运营' COMMENT '经营状态',\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id)\r\n) ENGINE=InnoDB COMMENT='车辆运输公司信息表';\r\n\r\n-- 2. 驾驶员表（车辆公司的员工）\r\nCREATE TABLE driver (\r\n    driver_id VARCHAR(18) PRIMARY KEY COMMENT '身份证号',\r\n    name VARCHAR(50) NOT NULL COMMENT '姓名',\r\n    gender ENUM('男','女') NOT NULL COMMENT '性别',\r\n    birth_date DATE NOT NULL COMMENT '出生日期',\r\n    license_type VARCHAR(5) NOT NULL COMMENT '驾照类型代码',\r\n    issue_date DATE NOT NULL COMMENT '发证日期',\r\n    valid_years TINYINT NOT NULL COMMENT '有效期(年)',\r\n    phone VARCHAR(20) COMMENT '联系电话',\r\n    address VARCHAR(200) COMMENT '联系地址',\r\n    area_id CHAR(6) NOT NULL COMMENT '行政区划代码',\r\n    status ENUM('正常','暂扣','吊销','过期') DEFAULT '正常' COMMENT '驾照状态',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属车辆公司ID',\r\n    INDEX idx_name (name),\r\n    INDEX idx_license (license_type),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    FOREIGN KEY (license_type) REFERENCES common.license_type_dict(license_code),\r\n    FOREIGN KEY (company_id) REFERENCES vehicle_company(company_id)\r\n) ENGINE=InnoDB COMMENT='驾驶员信息表（车辆公司员工）';\r\n\r\n-- 3. 车辆登记表\r\nCREATE TABLE vehicle (\r\n    vehicle_id VARCHAR(20) PRIMARY KEY COMMENT '车辆唯一编号',\r\n    plate_number VARCHAR(10) NOT NULL UNIQUE COMMENT '车牌号',\r\n    owner_id VARCHAR(18) NOT NULL COMMENT '车主（驾驶员）身份证号',\r\n    vehicle_type_code VARCHAR(20) NOT NULL COMMENT '车辆类型代码',\r\n    brand VARCHAR(30) NOT NULL COMMENT '品牌',\r\n    model VARCHAR(30) NOT NULL COMMENT '型号',\r\n    manufacture_year YEAR NOT NULL COMMENT '生产年份',\r\n    load_capacity DECIMAL(8,2) COMMENT '载重(吨)',\r\n    seat_count TINYINT UNSIGNED COMMENT '座位数（客车用）',\r\n    color VARCHAR(20) COMMENT '颜色',\r\n    register_date DATE NOT NULL COMMENT '注册日期',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    insurance_expire DATE COMMENT '保险到期日',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属车辆公司ID',\r\n    INDEX idx_plate (plate_number),\r\n    INDEX idx_owner (owner_id),\r\n    INDEX idx_type (vehicle_type_code),\r\n    FOREIGN KEY (owner_id) REFERENCES driver(driver_id),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    FOREIGN KEY (vehicle_type_code) REFERENCES common.vehicle_type_dict(type_code),\r\n    FOREIGN KEY (company_id) REFERENCES vehicle_company(company_id)\r\n) ENGINE=InnoDB COMMENT='车辆登记表';\r\n\r\n-- 4. 船舶公司表（独立）\r\nCREATE TABLE shipping_company (\r\n    company_id VARCHAR(20) PRIMARY KEY COMMENT '船舶公司编号',\r\n    company_name VARCHAR(100) NOT NULL COMMENT '公司名称',\r\n    business_type VARCHAR(50) NOT NULL COMMENT '经营类型（集装箱/散货/油轮/客运）',\r\n    establish_date DATE NOT NULL COMMENT '成立日期',\r\n    legal_person VARCHAR(50) NOT NULL COMMENT '法人',\r\n    contact_phone VARCHAR(20) COMMENT '联系电话',\r\n    address VARCHAR(200) COMMENT '公司地址',\r\n    area_id CHAR(6) NOT NULL COMMENT '行政区划代码',\r\n    status ENUM('运营','停业','注销') DEFAULT '运营' COMMENT '经营状态',\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id)\r\n) ENGINE=InnoDB COMMENT='船舶公司信息表';\r\n\r\n-- 5. 员工表（船舶公司的员工）\r\nCREATE TABLE employee (\r\n    employee_id VARCHAR(18) PRIMARY KEY COMMENT '身份证号',\r\n    name VARCHAR(50) NOT NULL COMMENT '姓名',\r\n    gender ENUM('男','女') NOT NULL COMMENT '性别',\r\n    employee_type_code VARCHAR(20) NOT NULL COMMENT '人员类型代码（船长/大副等）',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属船舶公司ID',\r\n    hire_date DATE COMMENT '入职日期',\r\n    phone VARCHAR(20) COMMENT '联系电话',\r\n    status ENUM('在职','离职','退休') DEFAULT '在职' COMMENT '状态',\r\n    FOREIGN KEY (employee_type_code) REFERENCES common.employee_type_dict(type_code),\r\n    FOREIGN KEY (company_id) REFERENCES shipping_company(company_id)\r\n) ENGINE=InnoDB COMMENT='船舶公司员工表';\r\n\r\n-- 6. 船舶基础信息表（船舶公司的子表）（通过mmsi关联Postgre中的ais数据）\r\nCREATE TABLE vessel (\r\n    mmsi INT UNSIGNED NOT NULL COMMENT '船舶MMSI，9位唯一标识',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属船舶公司ID',\r\n    vessel_type SMALLINT COMMENT '船舶类型代码（参照AIS标准）',\r\n    max_load DECIMAL(10,2) COMMENT '最大荷载量（吨）',\r\n    max_speed DECIMAL(4,1) COMMENT '最大航速（节）',\r\n    endurance VARCHAR(32) COMMENT '自持力（天/海里）',\r\n    captain_name VARCHAR(32) COMMENT '船长姓名',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    UNIQUE KEY uk_mmsi (mmsi),\r\n    FOREIGN KEY (company_id) REFERENCES shipping_company(company_id) ON DELETE RESTRICT ON UPDATE CASCADE,\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    FOREIGN KEY (vessel_type) REFERENCES common.vessel_type_dict(type_code)\r\n) ENGINE=InnoDB COMMENT='船舶基础信息表';\r\n\r\n\r\n\r\n\r\n-- =====================================================\r\n-- 金融库\r\nCREATE DATABASE IF NOT EXISTS finance_tax;\r\nUSE finance_tax;\r\n\r\n-- 公司主表\r\nCREATE TABLE companies (\r\n    company_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '公司唯一ID',\r\n    company_name VARCHAR(200) NOT NULL UNIQUE COMMENT '公司法定全称',\r\n    stock_code VARCHAR(20) UNIQUE COMMENT '股票代码（若上市）',\r\n    established_year YEAR COMMENT '注册/成立年份',\r\n    registered_capital DECIMAL(18,2) COMMENT '注册资本（万元）',\r\n    industry_code VARCHAR(20) COMMENT '所属行业代码',\r\n    registration_type_code VARCHAR(20) COMMENT '登记注册类型代码',\r\n    is_private BOOLEAN COMMENT '是否民营企业',\r\n    size_category_code VARCHAR(10) COMMENT '规模划型代码',\r\n    is_key_high_tech BOOLEAN DEFAULT FALSE COMMENT '是否重点扶持高新技术企业',\r\n    is_tech_advanced_service BOOLEAN DEFAULT FALSE COMMENT '是否技术先进型服务企业',\r\n\r\n    FOREIGN KEY (industry_code) REFERENCES common.dict_industry(industry_code),\r\n    FOREIGN KEY (registration_type_code) REFERENCES common.dict_registration_type(type_code),\r\n    FOREIGN KEY (size_category_code) REFERENCES common.dict_size_category(size_code)\r\n) COMMENT='公司基础信息主表';\r\n\r\n-- 股票信息表\r\nCREATE TABLE stocks (\r\n    stock_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '词条ID',\r\n    company_id BIGINT NOT NULL COMMENT '关联公司ID',\r\n    stock_code VARCHAR(20) NOT NULL UNIQUE COMMENT '股票代码',\r\n    stock_name VARCHAR(50) NOT NULL COMMENT '股票简称',\r\n    stock_full_name VARCHAR(200) COMMENT '公司全称（冗余）',\r\n    share_right_type VARCHAR(20) DEFAULT 'COMMON' COMMENT '股东权利类型（引用字典）',\r\n    register_type VARCHAR(20) DEFAULT 'REGISTERED' COMMENT '记名方式',\r\n    par_value_type VARCHAR(20) DEFAULT 'PAR' COMMENT '面额类型',\r\n    market_class VARCHAR(5) COMMENT '上市地点分类（A/B/H/N等）',\r\n    listing_date DATE COMMENT '上市时间',\r\n    total_shares BIGINT NOT NULL COMMENT '股本（股）',\r\n    current_price DECIMAL(10,2) COMMENT '最新股票价格（元）',\r\n\r\n    FOREIGN KEY (company_id) REFERENCES companies(company_id)\r\n) COMMENT='股票基本信息表';\r\n\r\n-- 股票日成交信息表\r\nCREATE TABLE stock_daily_trades (\r\n    trade_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '词条ID',\r\n    stock_id BIGINT NOT NULL COMMENT '关联股票ID',\r\n    trade_date DATE NOT NULL COMMENT '交易日期',\r\n    volume BIGINT NOT NULL COMMENT '成交量（股）',\r\n    avg_trade_size INT COMMENT '每笔成交股数',\r\n    open_price DECIMAL(10,2) NOT NULL COMMENT '开盘价',\r\n    close_price DECIMAL(10,2) NOT NULL COMMENT '收盘价',\r\n    high_price DECIMAL(10,2) NOT NULL COMMENT '最高价',\r\n    low_price DECIMAL(10,2) NOT NULL COMMENT '最低价',\r\n\r\n    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id),\r\n    UNIQUE KEY uk_stock_date (stock_id, trade_date)\r\n) COMMENT='股票每日成交汇总信息';\r\n\r\n-- 公司财务信息表\r\nCREATE TABLE company_financials (\r\n    financial_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '词条ID',\r\n    company_id BIGINT NOT NULL COMMENT '关联公司ID',\r\n    report_date DATE NOT NULL COMMENT '报表日期',\r\n    dividend_cash DECIMAL(18,2) DEFAULT 0 COMMENT '现金分红总额（万元）',\r\n    dividend_stock INT DEFAULT 0 COMMENT '每股股息（分/股）',\r\n    total_assets DECIMAL(18,2) NOT NULL COMMENT '总资产（万元）',\r\n    total_liabilities DECIMAL(18,2) NOT NULL COMMENT '总负债（万元）',\r\n\r\n    FOREIGN KEY (company_id) REFERENCES companies(company_id),\r\n    UNIQUE KEY uk_company_report (company_id, report_date)\r\n) COMMENT='公司定期财务摘要信息';\r\n\r\n-- 企业所得税申报信息表\r\nCREATE TABLE corporate_income_tax_returns (\r\n    return_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '申报ID',\r\n    company_id BIGINT NOT NULL COMMENT '关联公司ID',\r\n    tax_year YEAR NOT NULL COMMENT '纳税年度',\r\n    revenue DECIMAL(18,2) NOT NULL COMMENT '收入总额（万元）',\r\n    non_taxable_income DECIMAL(18,2) DEFAULT 0 COMMENT '不征税收入与免税收入（万元）',\r\n    deductions DECIMAL(18,2) NOT NULL COMMENT '扣除金额（万元）',\r\n    prior_year_losses DECIMAL(18,2) DEFAULT 0 COMMENT '允许弥补的以前年度亏损（万元）',\r\n    building_asset_value DECIMAL(18,2) COMMENT '房屋建筑物资产原值（万元）',\r\n    employee_count INT COMMENT '从业人数（全年季度平均值）',\r\n    total_assets DECIMAL(18,2) COMMENT '资产总额（万元，全年季度平均值）',\r\n    is_restricted_industry BOOLEAN DEFAULT FALSE COMMENT '是否从事国家限制或禁止行业',\r\n\r\n    FOREIGN KEY (company_id) REFERENCES companies(company_id),\r\n    UNIQUE KEY uk_company_year (company_id, tax_year)\r\n) COMMENT='企业所得税年度申报信息表';\r\n\r\n\r\n\r\n-- ============================================\r\n-- 工业库\r\nCREATE DATABASE IF NOT EXISTS energy;\r\nUSE energy;\r\n\r\n-- 能源企业表\r\nCREATE TABLE energy_company (\r\n    company_id VARCHAR(20) PRIMARY KEY COMMENT '企业编号',\r\n    company_name VARCHAR(100) NOT NULL COMMENT '企业名称',\r\n    business_type VARCHAR(50) NOT NULL COMMENT '经营类型',\r\n    establish_date DATE COMMENT '成立日期',\r\n    legal_person VARCHAR(50) COMMENT '法人代表',\r\n    contact_phone VARCHAR(20) COMMENT '联系电话',\r\n    area_id CHAR(6) NOT NULL COMMENT '注册地区划代码',\r\n    staff_count INT COMMENT '员工总数',\r\n    status ENUM('运营','停业','注销') DEFAULT '运营' COMMENT '经营状态',\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id)\r\n) ENGINE=InnoDB COMMENT='能源企业信息表';\r\n\r\n-- 企业资质表\r\nCREATE TABLE company_certification (\r\n    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '企业编号',\r\n    cert_type VARCHAR(50) NOT NULL COMMENT '资质类型',\r\n    cert_no VARCHAR(50) COMMENT '证书编号',\r\n    issue_date DATE COMMENT '发证日期',\r\n    expire_date DATE COMMENT '到期日期',\r\n    issue_authority VARCHAR(100) COMMENT '发证机关',\r\n    FOREIGN KEY (company_id) REFERENCES energy_company(company_id)\r\n) ENGINE=InnoDB COMMENT='企业资质表';\r\n\r\n-- 能源场站表\r\nCREATE TABLE energy_station (\r\n    station_id VARCHAR(20) PRIMARY KEY COMMENT '场站编号',\r\n    station_name VARCHAR(100) NOT NULL COMMENT '场站名称',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属企业编号',\r\n    station_type_code VARCHAR(10) NOT NULL COMMENT '场站类型代码',\r\n    energy_type_code VARCHAR(10) NOT NULL COMMENT '能源类型代码',\r\n    installed_capacity DECIMAL(12,2) COMMENT '装机容量(MW)',\r\n    annual_generation DECIMAL(12,2) COMMENT '年发电量(万kWh)',\r\n    grid_connect_date DATE COMMENT '并网日期',\r\n    area_id CHAR(6) NOT NULL COMMENT '所在地区划代码',\r\n    status ENUM('运行','在建','停机','退役') DEFAULT '运行' COMMENT '运行状态',\r\n    FOREIGN KEY (company_id) REFERENCES energy_company(company_id),\r\n    FOREIGN KEY (station_type_code) REFERENCES common.station_type_dict(type_code),\r\n    FOREIGN KEY (energy_type_code) REFERENCES common.energy_type_dict(type_code),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id)\r\n) ENGINE=InnoDB COMMENT='能源场站表';\r\n\r\n-- 供电区域表\r\nCREATE TABLE supply_area (\r\n    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '供电企业编号',\r\n    area_id CHAR(6) NOT NULL COMMENT '供电区域代码',\r\n    supply_level VARCHAR(10) COMMENT '供电等级',\r\n    household_count INT COMMENT '供电户数',\r\n    annual_supply DECIMAL(12,2) COMMENT '年供电量(万kWh)',\r\n    FOREIGN KEY (company_id) REFERENCES energy_company(company_id),\r\n    FOREIGN KEY (area_id) REFERENCES common.administrative_division(id),\r\n    UNIQUE KEY uk_company_area (company_id, area_id)\r\n) ENGINE=InnoDB COMMENT='供电区域表';\r\n\r\n-- 员工表\r\nCREATE TABLE employee (\r\n    employee_id VARCHAR(18) PRIMARY KEY COMMENT '身份证号',\r\n    name VARCHAR(50) NOT NULL COMMENT '姓名',\r\n    gender ENUM('男','女') NOT NULL COMMENT '性别',\r\n    birth_date DATE NOT NULL COMMENT '出生日期',\r\n    company_id VARCHAR(20) NOT NULL COMMENT '所属企业编号',\r\n    station_id VARCHAR(20) COMMENT '所属场站编号',\r\n    position_code VARCHAR(20) NOT NULL COMMENT '岗位代码',\r\n    hire_date DATE COMMENT '入职日期',\r\n    phone VARCHAR(20) COMMENT '联系电话',\r\n    education VARCHAR(20) COMMENT '学历',\r\n    status ENUM('在职','离职','退休','外派') DEFAULT '在职' COMMENT '状态',\r\n    FOREIGN KEY (company_id) REFERENCES energy_company(company_id),\r\n    FOREIGN KEY (station_id) REFERENCES energy_station(station_id),\r\n    FOREIGN KEY (position_code) REFERENCES common.energy_position_dict(position_code)\r\n) ENGINE=InnoDB COMMENT='能源企业员工表';\r\n\r\n\r\n-- =====================================================\r\n-- 2024教育库\r\nCREATE DATABASE IF NOT EXISTS education_2024;\r\nUSE education_2024;\r\n-- 学期表\r\nCREATE TABLE semester (\r\n    semester_id       INT AUTO_INCREMENT PRIMARY KEY,\r\n    academic_year     INT NOT NULL,\r\n    semester_code     VARCHAR(20) NOT NULL,\r\n    start_date_key    INT NOT NULL,\r\n    end_date_key      INT NOT NULL\r\n);\r\n\r\n-- 院系表（真实院系名称）\r\nCREATE TABLE department (\r\n    department_id     INT AUTO_INCREMENT PRIMARY KEY,\r\n    department_code   VARCHAR(20) NOT NULL,\r\n    department_name   VARCHAR(100) NOT NULL\r\n);\r\n\r\n-- 教师表\r\nCREATE TABLE teacher (\r\n    teacher_id        INT AUTO_INCREMENT PRIMARY KEY,\r\n    teacher_no        VARCHAR(20) NOT NULL,\r\n    teacher_name      VARCHAR(100) NOT NULL,\r\n    department_id     INT NOT NULL,\r\n    gender_code       CHAR(1),\r\n    phone             VARCHAR(20),\r\n    region_id         INT,\r\n    FOREIGN KEY (department_id) REFERENCES department(department_id)\r\n);\r\n\r\n-- 班级表\r\nCREATE TABLE class (\r\n    class_id          INT AUTO_INCREMENT PRIMARY KEY,\r\n    class_code        VARCHAR(20) NOT NULL,\r\n    class_name        VARCHAR(100) NOT NULL,\r\n    department_id     INT NOT NULL,\r\n    grade_year        INT,\r\n    FOREIGN KEY (department_id) REFERENCES department(department_id)\r\n);\r\n\r\n-- 学生表\r\nCREATE TABLE student (\r\n    student_id            INT AUTO_INCREMENT PRIMARY KEY,\r\n    student_no            VARCHAR(20) NOT NULL,\r\n    student_name          VARCHAR(100) NOT NULL,\r\n    gender_code           CHAR(1),\r\n    academic_level_code   VARCHAR(20),\r\n    department_id         INT NOT NULL,\r\n    class_id              INT NOT NULL,\r\n    home_region_id        INT,\r\n    student_status_code   VARCHAR(20),\r\n    admit_date_key        INT,\r\n    FOREIGN KEY (department_id) REFERENCES department(department_id),\r\n    FOREIGN KEY (class_id) REFERENCES class(class_id)\r\n);\r\n\r\n-- 课程表\r\nCREATE TABLE course (\r\n    course_id         INT AUTO_INCREMENT PRIMARY KEY,\r\n    course_code       VARCHAR(20) NOT NULL,\r\n    course_name       VARCHAR(200) NOT NULL,\r\n    department_id     INT NOT NULL,\r\n    teacher_id        INT NOT NULL,\r\n    credit            DECIMAL(3,1),\r\n    course_type       VARCHAR(20),\r\n    max_score         INT,\r\n    FOREIGN KEY (department_id) REFERENCES department(department_id),\r\n    FOREIGN KEY (teacher_id) REFERENCES teacher(teacher_id)\r\n);\r\n\r\n-- 选课表\r\nCREATE TABLE enrollment (\r\n    enrollment_id     INT AUTO_INCREMENT PRIMARY KEY,\r\n    student_id        INT NOT NULL,\r\n    course_id         INT NOT NULL,\r\n    semester_id       INT NOT NULL,\r\n    enroll_date_key   INT,\r\n    take_mode         VARCHAR(20),\r\n    is_withdraw       TINYINT(1),\r\n    FOREIGN KEY (student_id) REFERENCES student(student_id),\r\n    FOREIGN KEY (course_id) REFERENCES course(course_id),\r\n    FOREIGN KEY (semester_id) REFERENCES semester(semester_id)\r\n);\r\n\r\n-- 成绩表\r\nCREATE TABLE exam_score (\r\n    exam_score_id     INT AUTO_INCREMENT PRIMARY KEY,\r\n    enrollment_id     INT NOT NULL,\r\n    exam_item         VARCHAR(20),\r\n    score             DECIMAL(5,2),\r\n    score_date_key    INT,\r\n    FOREIGN KEY (enrollment_id) REFERENCES enrollment(enrollment_id)\r\n);\r\n\r\n\r\n\r\n\r\n\r\n\r\n-- =====================================================\r\n-- 2025教育库\r\nCREATE DATABASE IF NOT EXISTS education_2025;\r\nUSE education_2025;\r\nCREATE TABLE semester (\r\n    semester_id       INT AUTO_INCREMENT PRIMARY KEY,\r\n    academic_year     INT NOT NULL,\r\n    semester_code     VARCHAR(20) NOT NULL,\r\n    start_date_key    INT NOT NULL,\r\n    end_date_key      INT NOT NULL\r\n);\r\n\r\nCREATE TABLE department (\r\n    department_id     INT AUTO_INCREMENT PRIMARY KEY,\r\n    department_code   VARCHAR(20) NOT NULL,\r\n    department_name   VARCHAR(100) NOT NULL\r\n);\r\n\r\nCREATE TABLE teacher (\r\n    teacher_id        INT AUTO_INCREMENT PRIMARY KEY,\r\n    teacher_no        VARCHAR(20) NOT NULL,\r\n    teacher_name      VARCHAR(100) NOT NULL,\r\n    department_id     INT NOT NULL,\r\n    gender_code       CHAR(1),\r\n    phone             VARCHAR(20),\r\n    region_id         INT,\r\n    FOREIGN KEY (department_id) REFERENCES department(department_id)\r\n);\r\n\r\nCREATE TABLE class (\r\n    class_id          INT AUTO_INCREMENT PRIMARY KEY,\r\n    class_code        VARCHAR(20) NOT NULL,\r\n    class_name        VARCHAR(100) NOT NULL,\r\n    department_id     INT NOT NULL,\r\n    grade_year        INT,\r\n    FOREIGN KEY (department_id) REFERENCES department(department_id)\r\n);\r\n\r\nCREATE TABLE student (\r\n    student_id            INT AUTO_INCREMENT PRIMARY KEY,\r\n    student_no            VARCHAR(20) NOT NULL,\r\n    student_name          VARCHAR(100) NOT NULL,\r\n    gender_code           CHAR(1),\r\n    academic_level_code   VARCHAR(20),\r\n    department_id         INT NOT NULL,\r\n    class_id              INT NOT NULL,\r\n    home_region_id        INT,\r\n    student_status_code   VARCHAR(20),\r\n    admit_date_key        INT,\r\n    FOREIGN KEY (department_id) REFERENCES department(department_id),\r\n    FOREIGN KEY (class_id) REFERENCES class(class_id)\r\n);\r\n\r\nCREATE TABLE course (\r\n    course_id         INT AUTO_INCREMENT PRIMARY KEY,\r\n    course_code       VARCHAR(20) NOT NULL,\r\n    course_name       VARCHAR(200) NOT NULL,\r\n    department_id     INT NOT NULL,\r\n    teacher_id        INT NOT NULL,\r\n    credit            DECIMAL(3,1),\r\n    course_type       VARCHAR(20),\r\n    max_score         INT,\r\n    FOREIGN KEY (department_id) REFERENCES department(department_id),\r\n    FOREIGN KEY (teacher_id) REFERENCES teacher(teacher_id)\r\n);\r\n\r\nCREATE TABLE enrollment (\r\n    enrollment_id     INT AUTO_INCREMENT PRIMARY KEY,\r\n    student_id        INT NOT NULL,\r\n    course_id         INT NOT NULL,\r\n    semester_id       INT NOT NULL,\r\n    enroll_date_key   INT,\r\n    take_mode         VARCHAR(20),\r\n    is_withdraw       TINYINT(1),\r\n    FOREIGN KEY (student_id) REFERENCES student(student_id),\r\n    FOREIGN KEY (course_id) REFERENCES course(course_id),\r\n    FOREIGN KEY (semester_id) REFERENCES semester(semester_id)\r\n);\r\n\r\nCREATE TABLE exam_score (\r\n    exam_score_id     INT AUTO_INCREMENT PRIMARY KEY,\r\n    enrollment_id     INT NOT NULL,\r\n    exam_item         VARCHAR(20),\r\n    score             DECIMAL(5,2),\r\n    score_date_key    INT,\r\n    FOREIGN KEY (enrollment_id) REFERENCES enrollment(enrollment_id)\r\n);\r\n\r\n\r\n-- =====================================================\r\n-- 电商库\r\nCREATE DATABASE IF NOT EXISTS ecommerce\r\n  DEFAULT CHARACTER SET utf8mb4\r\n  DEFAULT COLLATE utf8mb4_unicode_ci;\r\n\r\nUSE ecommerce;\r\n\r\nCREATE TABLE customer (\r\n  customer_id BIGINT NOT NULL COMMENT '用户ID',\r\n  customer_name VARCHAR(100) NOT NULL COMMENT '用户姓名',\r\n  gender ENUM('M', 'F', 'U') NOT NULL DEFAULT 'U' COMMENT '性别：M男，F女，U未知',\r\n  phone VARCHAR(32) DEFAULT NULL COMMENT '手机号',\r\n  email VARCHAR(128) DEFAULT NULL COMMENT '邮箱',\r\n  level_code VARCHAR(32) NOT NULL COMMENT '用户等级编码，关联common.customer_level_dict.level_code',\r\n  status_code VARCHAR(32) NOT NULL COMMENT '用户状态编码，关联common.customer_status_dict.status_code',\r\n  province_code VARCHAR(12) NOT NULL COMMENT '省级行政区划编码，关联common.administrative_division.division_code',\r\n  city_code VARCHAR(12) NOT NULL COMMENT '城市行政区划编码，关联common.administrative_division.division_code',\r\n  register_time DATETIME NOT NULL COMMENT '注册时间',\r\n  last_login_time DATETIME DEFAULT NULL COMMENT '最近登录时间',\r\n  growth_value INT NOT NULL DEFAULT 0 COMMENT '成长值',\r\n  PRIMARY KEY (customer_id),\r\n  UNIQUE KEY uk_customer_phone (phone),\r\n  KEY idx_customer_level (level_code),\r\n  KEY idx_customer_status (status_code),\r\n  KEY idx_customer_region (province_code, city_code),\r\n  KEY idx_customer_register_time (register_time)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';\r\n\r\nCREATE TABLE product (\r\n  product_id BIGINT NOT NULL COMMENT '商品ID',\r\n  product_name VARCHAR(200) NOT NULL COMMENT '商品名称',\r\n  category_id BIGINT NOT NULL COMMENT '商品分类ID，关联common.product_category.category_id',\r\n  brand_name VARCHAR(100) NOT NULL COMMENT '品牌名称',\r\n  status_code VARCHAR(32) NOT NULL COMMENT '商品状态编码，关联common.product_status_dict.status_code',\r\n  sale_price DECIMAL(12,2) NOT NULL COMMENT '销售单价',\r\n  cost_price DECIMAL(12,2) NOT NULL COMMENT '成本单价',\r\n  listed_time DATETIME NOT NULL COMMENT '上架时间',\r\n  PRIMARY KEY (product_id),\r\n  KEY idx_product_category (category_id),\r\n  KEY idx_product_status (status_code),\r\n  KEY idx_product_brand (brand_name),\r\n  KEY idx_product_price (sale_price)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';\r\n\r\nCREATE TABLE inventory (\r\n  inventory_id BIGINT NOT NULL COMMENT '库存ID',\r\n  product_id BIGINT NOT NULL COMMENT '商品ID，关联ecommerce.product.product_id',\r\n  warehouse_code VARCHAR(32) NOT NULL COMMENT '仓库编码',\r\n  warehouse_name VARCHAR(100) NOT NULL COMMENT '仓库名称',\r\n  province_code VARCHAR(12) NOT NULL COMMENT '仓库所在省份编码，关联common.administrative_division.division_code',\r\n  city_code VARCHAR(12) NOT NULL COMMENT '仓库所在城市编码，关联common.administrative_division.division_code',\r\n  stock_quantity INT NOT NULL DEFAULT 0 COMMENT '当前库存数量',\r\n  locked_quantity INT NOT NULL DEFAULT 0 COMMENT '锁定库存数量',\r\n  safety_stock INT NOT NULL DEFAULT 0 COMMENT '安全库存数量',\r\n  updated_time DATETIME NOT NULL COMMENT '库存更新时间',\r\n  PRIMARY KEY (inventory_id),\r\n  UNIQUE KEY uk_inventory_product_warehouse (product_id, warehouse_code),\r\n  KEY idx_inventory_product (product_id),\r\n  KEY idx_inventory_region (province_code, city_code),\r\n  CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) REFERENCES product(product_id)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存表';\r\n\r\nCREATE TABLE orders (\r\n  order_id BIGINT NOT NULL COMMENT '订单ID',\r\n  order_no VARCHAR(64) NOT NULL COMMENT '订单编号',\r\n  customer_id BIGINT NOT NULL COMMENT '用户ID，关联ecommerce.customer.customer_id',\r\n  order_status_code VARCHAR(32) NOT NULL COMMENT '订单状态编码，关联common.order_status_dict.status_code',\r\n  order_channel_code VARCHAR(32) NOT NULL COMMENT '下单渠道编码，关联common.order_channel_dict.channel_code',\r\n  platform_code VARCHAR(32) NOT NULL COMMENT '销售平台编码，关联common.platform_dict.platform_code',\r\n  order_time DATETIME NOT NULL COMMENT '下单时间',\r\n  pay_time DATETIME DEFAULT NULL COMMENT '支付时间',\r\n  finish_time DATETIME DEFAULT NULL COMMENT '完成时间',\r\n  total_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT '订单商品总金额',\r\n  discount_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT '订单优惠金额',\r\n  freight_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT '运费金额',\r\n  payable_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT '订单应付金额',\r\n  receiver_province_code VARCHAR(12) NOT NULL COMMENT '收货省份编码，关联common.administrative_division.division_code',\r\n  receiver_city_code VARCHAR(12) NOT NULL COMMENT '收货城市编码，关联common.administrative_division.division_code',\r\n  PRIMARY KEY (order_id),\r\n  UNIQUE KEY uk_orders_order_no (order_no),\r\n  KEY idx_orders_customer (customer_id),\r\n  KEY idx_orders_status (order_status_code),\r\n  KEY idx_orders_time (order_time),\r\n  KEY idx_orders_channel_platform (order_channel_code, platform_code),\r\n  KEY idx_orders_receiver_region (receiver_province_code, receiver_city_code),\r\n  CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';\r\n\r\nCREATE TABLE order_item (\r\n  order_item_id BIGINT NOT NULL COMMENT '订单明细ID',\r\n  order_id BIGINT NOT NULL COMMENT '订单ID，关联ecommerce.orders.order_id',\r\n  product_id BIGINT NOT NULL COMMENT '商品ID，关联ecommerce.product.product_id',\r\n  quantity INT NOT NULL COMMENT '购买数量',\r\n  unit_price DECIMAL(12,2) NOT NULL COMMENT '成交单价',\r\n  discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00 COMMENT '明细优惠金额',\r\n  item_amount DECIMAL(14,2) NOT NULL COMMENT '明细应付金额',\r\n  item_cost_amount DECIMAL(14,2) NOT NULL COMMENT '明细成本金额',\r\n  refund_quantity INT NOT NULL DEFAULT 0 COMMENT '退款数量',\r\n  refund_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT '退款金额',\r\n  refund_reason_code VARCHAR(32) DEFAULT NULL COMMENT '退款原因编码，关联common.refund_reason_dict.reason_code',\r\n  PRIMARY KEY (order_item_id),\r\n  KEY idx_order_item_order (order_id),\r\n  KEY idx_order_item_product (product_id),\r\n  KEY idx_order_item_refund_reason (refund_reason_code),\r\n  CONSTRAINT fk_order_item_order FOREIGN KEY (order_id) REFERENCES orders(order_id),\r\n  CONSTRAINT fk_order_item_product FOREIGN KEY (product_id) REFERENCES product(product_id)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单明细表';\r\n\r\nCREATE TABLE payment (\r\n  payment_id BIGINT NOT NULL COMMENT '支付ID',\r\n  payment_no VARCHAR(64) NOT NULL COMMENT '支付流水号',\r\n  order_id BIGINT NOT NULL COMMENT '订单ID，关联ecommerce.orders.order_id',\r\n  payment_method_code VARCHAR(32) NOT NULL COMMENT '支付方式编码，关联common.payment_method_dict.method_code',\r\n  payment_status_code VARCHAR(32) NOT NULL COMMENT '支付状态编码，关联common.payment_status_dict.status_code',\r\n  payment_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT '支付金额',\r\n  refund_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00 COMMENT '退款金额',\r\n  paid_time DATETIME DEFAULT NULL COMMENT '支付成功时间',\r\n  created_time DATETIME NOT NULL COMMENT '支付记录创建时间',\r\n  PRIMARY KEY (payment_id),\r\n  UNIQUE KEY uk_payment_no (payment_no),\r\n  UNIQUE KEY uk_payment_order (order_id),\r\n  KEY idx_payment_method (payment_method_code),\r\n  KEY idx_payment_status (payment_status_code),\r\n  KEY idx_payment_paid_time (paid_time),\r\n  CONSTRAINT fk_payment_order FOREIGN KEY (order_id) REFERENCES orders(order_id)\r\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付表';\r\n\r\n\r\n-- =====================================================\r\n-- 医院库（ES）\r\nPUT /medical_institutions\r\n{\r\n  \"mappings\": {\r\n    \"properties\": {\r\n      \"name\": { \"type\": \"text\", \"fields\": { \"keyword\": { \"type\": \"keyword\" } } },\r\n      \"city\": { \"type\": \"keyword\" },\r\n      \"district\": { \"type\": \"keyword\" },\r\n      \"address\": { \"type\": \"text\" },\r\n      \"location\": { \"type\": \"geo_point\" },\r\n      \"level\": { \"type\": \"keyword\" },            // 三甲、三乙、二甲、二乙、一甲等\r\n      \"bed_count\": { \"type\": \"integer\" },\r\n      \"doctor_count\": { \"type\": \"integer\" },\r\n      \"nurse_count\": { \"type\": \"integer\" },\r\n      \"ambulance_count\": { \"type\": \"integer\" },   // 救护车数量\r\n      \"department_count\": { \"type\": \"integer\" },  // 科室数量\r\n      \"annual_outpatient\": { \"type\": \"long\" },    // 年门诊量（人次）\r\n      \"has_icu\": { \"type\": \"boolean\" },           // 是否有ICU\r\n      \"is_teaching_hospital\": { \"type\": \"boolean\" }, // 是否教学医院\r\n      \"emergency_24h\": { \"type\": \"boolean\" },\r\n      \"rating\": { \"type\": \"float\" },\r\n      \"founded_year\": { \"type\": \"integer\" }       // 成立年份\r\n    }\r\n  }\r\n}\r\n\r\n-- =====================================================\r\n-- 船舶实时库（PG）\r\nCREATE TABLE public.vessel_ais_data (\r\n    id bigint NOT NULL,\r\n    mmsi integer NOT NULL,\r\n    \"timestamp\" timestamp without time zone NOT NULL,\r\n    longitude numeric(9,6) NOT NULL,\r\n    latitude numeric(8,6) NOT NULL,\r\n    sog numeric(4,1) NOT NULL,\r\n    cog numeric(5,1) NOT NULL,\r\n    heading smallint,\r\n    nav_status smallint NOT NULL,\r\n    rot numeric(4,1),\r\n    destination character varying(32),\r\n    draught numeric(4,2),\r\n    vessel_type smallint,\r\n    imo bigint,\r\n    call_sign character varying(10),\r\n    eta timestamp without time zone,\r\n    last_update timestamp without time zone DEFAULT CURRENT_TIMESTAMP,\r\n    geom public.geometry(Point,4326) NOT NULL,\r\n    CONSTRAINT vessel_ais_data_heading_check CHECK (((heading >= 0) AND (heading <= 359))),\r\n    CONSTRAINT vessel_ais_data_mmsi_check CHECK (((mmsi >= 1) AND (mmsi <= 999999999))),\r\n    CONSTRAINT vessel_ais_data_nav_status_check CHECK (((nav_status >= 0) AND (nav_status <= 255)))\r\n);\r\nALTER TABLE public.vessel_ais_data OWNER TO postgres;\r\n\r\nCOMMENT ON TABLE public.vessel_ais_data IS '船舶AIS数据存储表';\r\nCOMMENT ON COLUMN public.vessel_ais_data.id IS '主键ID';\r\nCOMMENT ON COLUMN public.vessel_ais_data.mmsi IS '船舶MMSI码';\r\nCOMMENT ON COLUMN public.vessel_ais_data.\"timestamp\" IS '数据时间';\r\nCOMMENT ON COLUMN public.vessel_ais_data.longitude IS '经度';\r\nCOMMENT ON COLUMN public.vessel_ais_data.latitude IS '纬度';\r\nCOMMENT ON COLUMN public.vessel_ais_data.sog IS '航速';\r\nCOMMENT ON COLUMN public.vessel_ais_data.cog IS '航向';\r\nCOMMENT ON COLUMN public.vessel_ais_data.heading IS '船首向';\r\nCOMMENT ON COLUMN public.vessel_ais_data.nav_status IS '航行状态';\r\nCOMMENT ON COLUMN public.vessel_ais_data.geom IS '空间位置';"
      }
    ],
    "knowledge_context": [
      {
        "knowledge_id": 1554,
        "knowledge_text": "GMV（商品交易总额/订单总额/交易总额）指订单商品总交易额，通常按订单表 total_amount 汇总，不扣除优惠、退款或支付失败；若题目强调实付金额，应使用 payable_amount 或 payment_amount。SQL逻辑：SUM(ecommerce.orders.total_amount)。示例：SELECT ROUND(SUM(total_amount), 2) AS gmv FROM ecommerce.orders。注意：如果问题明确要求成交或实付，优先使用 payable_amount。"
      },
      {
        "knowledge_id": 1555,
        "knowledge_text": "客单价（AOV/平均订单金额/平均客单价）指平均每笔订单的应付金额，按订单应付金额总和除以订单数计算。SQL逻辑：SUM(ecommerce.orders.payable_amount) / COUNT(DISTINCT ecommerce.orders.order_id)。示例：SELECT ROUND(SUM(payable_amount) / COUNT(DISTINCT order_id), 2) AS avg_order_value FROM ecommerce.orders。"
      },
      {
        "knowledge_id": 1556,
        "knowledge_text": "实付销售额（成交额/实付金额/销售额）指订单应付金额或支付成功金额的汇总。若需要以支付事实为准，应关联 payment 并筛选 SUCCESS。SQL逻辑：SUM(ecommerce.orders.payable_amount)。示例：SELECT ROUND(SUM(o.payable_amount), 2) AS paid_sales FROM ecommerce.orders o JOIN ecommerce.payment p ON o.order_id = p.order_id WHERE p.payment_status_code = 'SUCCESS'。注意：若题目出现支付成功，必须关联 payment 并筛选 payment_status_code = 'SUCCESS'。"
      },
      {
        "knowledge_id": 1557,
        "knowledge_text": "支付成功率（支付转化率/付款成功率）指成功支付订单数占全部支付记录数的比例。SQL逻辑：SUM(CASE WHEN ecommerce.payment.payment_status_code = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*)。示例：SELECT ROUND(SUM(CASE WHEN payment_status_code = 'SUCCESS' THEN 1 ELSE 0 END) / COUNT(*), 4) AS payment_success_rate FROM ecommerce.payment。"
      },
      {
        "knowledge_id": 1558,
        "knowledge_text": "退款率（订单退款率/售后退款率）可按退款订单数占订单数计算。订单明细存在 refund_amount 大于 0 时，可认为发生退款。SQL逻辑：COUNT(DISTINCT CASE WHEN ecommerce.order_item.refund_amount > 0 THEN ecommerce.order_item.order_id END) / COUNT(DISTINCT ecommerce.orders.order_id)。示例：SELECT ROUND(COUNT(DISTINCT CASE WHEN oi.refund_amount > 0 THEN oi.order_id END) / COUNT(DISTINCT o.order_id), 4) AS refund_rate FROM ecommerce.orders o LEFT JOIN ecommerce.order_item oi ON o.order_id = oi.order_id。"
      },
      {
        "knowledge_id": 1559,
        "knowledge_text": "复购率（重复购买率/用户复购率）指下单次数大于 1 的用户数占下单用户数的比例。SQL逻辑：COUNT(CASE WHEN user_order_count > 1 THEN 1 END) / COUNT(*)。示例：SELECT ROUND(SUM(CASE WHEN t.order_count > 1 THEN 1 ELSE 0 END) / COUNT(*), 4) AS repurchase_rate FROM (SELECT customer_id, COUNT(DISTINCT order_id) AS order_count FROM ecommerce.orders GROUP BY customer_id) t。"
      },
      {
        "knowledge_id": 1560,
        "knowledge_text": "毛利额（利润额/商品毛利）指订单明细应付金额减去明细成本金额后的差额汇总。SQL逻辑：SUM(ecommerce.order_item.item_amount - ecommerce.order_item.item_cost_amount)。示例：SELECT ROUND(SUM(item_amount - item_cost_amount), 2) AS gross_profit FROM ecommerce.order_item。"
      },
      {
        "knowledge_id": 1561,
        "knowledge_text": "毛利率（销售毛利率/利润率）指毛利额占销售额的比例，按订单明细的 item_amount 和 item_cost_amount 计算。SQL逻辑：SUM(item_amount - item_cost_amount) / SUM(item_amount)。示例：SELECT ROUND(SUM(item_amount - item_cost_amount) / SUM(item_amount), 4) AS gross_margin_rate FROM ecommerce.order_item。"
      },
      {
        "knowledge_id": 1562,
        "knowledge_text": "销量（销售数量/售出件数）指订单明细里的购买数量汇总，一般使用 order_item.quantity。SQL逻辑：SUM(ecommerce.order_item.quantity)。示例：SELECT product_id, SUM(quantity) AS sales_quantity FROM ecommerce.order_item GROUP BY product_id。"
      },
      {
        "knowledge_id": 1563,
        "knowledge_text": "热销商品（TOP商品/畅销商品/销量最高商品）通常按销量从高到低排序；若问题强调销售额，则按 item_amount 汇总排序。SQL逻辑：ORDER BY SUM(ecommerce.order_item.quantity) DESC。示例：SELECT p.product_id, p.product_name, SUM(oi.quantity) AS sales_quantity FROM ecommerce.order_item oi JOIN ecommerce.product p ON oi.product_id = p.product_id GROUP BY p.product_id, p.product_name ORDER BY sales_quantity DESC LIMIT 10。"
      },
      {
        "knowledge_id": 1564,
        "knowledge_text": "高价值用户（核心用户/高消费用户/大客户）通常按用户累计应付金额或累计支付金额排序。SQL逻辑：ORDER BY SUM(ecommerce.orders.payable_amount) DESC。示例：SELECT c.customer_id, c.customer_name, ROUND(SUM(o.payable_amount), 2) AS total_payable FROM ecommerce.customer c JOIN ecommerce.orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.customer_name ORDER BY total_payable DESC LIMIT 10。"
      },
      {
        "knowledge_id": 1565,
        "knowledge_text": "库存告警（低库存/库存不足/安全库存预警）指当前库存数量低于或等于安全库存数量。SQL逻辑：ecommerce.inventory.stock_quantity <= ecommerce.inventory.safety_stock。示例：SELECT i.product_id, p.product_name, i.warehouse_name, i.stock_quantity, i.safety_stock FROM ecommerce.inventory i JOIN ecommerce.product p ON i.product_id = p.product_id WHERE i.stock_quantity <= i.safety_stock。"
      },
      {
        "knowledge_id": 1566,
        "knowledge_text": "月销售额（按月销售额/每月成交额）按订单时间 order_time 的年月维度汇总订单应付金额。SQL逻辑：GROUP BY DATE_FORMAT(ecommerce.orders.order_time, '%Y-%m')。示例：SELECT DATE_FORMAT(order_time, '%Y-%m') AS month, ROUND(SUM(payable_amount), 2) AS monthly_sales FROM ecommerce.orders GROUP BY DATE_FORMAT(order_time, '%Y-%m') ORDER BY month。"
      },
      {
        "knowledge_id": 1567,
        "knowledge_text": "下单用户数（购买用户数/成交用户数）指有订单记录的去重用户数。SQL逻辑：COUNT(DISTINCT ecommerce.orders.customer_id)。示例：SELECT COUNT(DISTINCT customer_id) AS order_user_count FROM ecommerce.orders。"
      },
      {
        "knowledge_id": 1568,
        "knowledge_text": "订单转化完成率（完成率/订单完成率）指已完成订单数占全部订单数的比例。SQL逻辑：SUM(CASE WHEN ecommerce.orders.order_status_code = 'COMPLETED' THEN 1 ELSE 0 END) / COUNT(*)。示例：SELECT ROUND(SUM(CASE WHEN order_status_code = 'COMPLETED' THEN 1 ELSE 0 END) / COUNT(*), 4) AS order_complete_rate FROM ecommerce.orders。"
      },
      {
        "knowledge_id": 1569,
        "knowledge_text": "用户最近订单（最近一次下单/最新订单）：需要按 customer_id 分组，并按 order_time 降序取第一条，可使用窗口函数或 MySQL 5.7 兼容的子查询。SQL模式：MAX(order_time) per customer_id。示例：SELECT o.* FROM ecommerce.orders o JOIN (SELECT customer_id, MAX(order_time) AS max_order_time FROM ecommerce.orders GROUP BY customer_id) t ON o.customer_id = t.customer_id AND o.order_time = t.max_order_time。注意：MySQL 5.7 不支持 ROW_NUMBER，可用聚合子查询实现。"
      },
      {
        "knowledge_id": 1570,
        "knowledge_text": "高于平均客单价用户（超过平均客单价/高客单用户）：先按用户聚合计算用户客单价，再与全局客单价比较。SQL模式：user_avg_order_value > global_avg_order_value。示例：SELECT t.customer_id, ROUND(t.user_aov, 2) AS user_aov FROM (SELECT customer_id, SUM(payable_amount) / COUNT(DISTINCT order_id) AS user_aov FROM ecommerce.orders GROUP BY customer_id) t WHERE t.user_aov > (SELECT SUM(payable_amount) / COUNT(DISTINCT order_id) FROM ecommerce.orders)。"
      },
      {
        "knowledge_id": 1571,
        "knowledge_text": "类目内商品销售排名（类目排名/分类商品排名）：统计每个商品的销售额或销量后，在商品分类内部排序。MySQL 5.7 可通过自连接或变量实现；若训练 SQL 允许 MySQL 8，可使用窗口函数。SQL模式：RANK within category by SUM(order_item.item_amount) or SUM(order_item.quantity)。示例：SELECT pc.category_name, p.product_id, p.product_name, SUM(oi.item_amount) AS sales_amount FROM ecommerce.order_item oi JOIN ecommerce.product p ON oi.product_id = p.product_id JOIN common.product_category pc ON p.category_id = pc.category_id GROUP BY pc.category_name, p.product_id, p.product_name ORDER BY pc.category_name, sales_amount DESC。"
      },
      {
        "knowledge_id": 1572,
        "knowledge_text": "成绩折算规则（教育教务常用口径示例）：总评 = 平时*0.30 + 期中*0.30 + 期末*0.40。总评四舍五入保留2位。"
      },
      {
        "knowledge_id": 1573,
        "knowledge_text": "挂科判定规则（示例）：当总评成绩 < 60.00 视为不合格（挂科）。"
      },
      {
        "knowledge_id": 1574,
        "knowledge_text": "学分绩（GPA/绩点）示例映射：总评>=90 为绩点 4.0；80-89 为 3.0；70-79 为 2.0；60-69 为 1.0；<60 为 0.0。"
      },
      {
        "knowledge_id": 1575,
        "knowledge_text": "选课退课规则（示例）：enrollment.is_withdraw=1 的记录视为已退课，不计入成绩统计与排名。"
      },
      {
        "knowledge_id": 1576,
        "knowledge_text": "退课率 = 退课去重学生/选课去重学生"
      },
      {
        "knowledge_id": 1577,
        "knowledge_text": "中位数：窗口函数按分值排序取中间行"
      },
      {
        "knowledge_id": 1578,
        "knowledge_text": "窗口函数：MySQL8+"
      },
      {
        "knowledge_id": 1579,
        "knowledge_text": "总评折算总分：同一学生跨多门课把总评相加"
      },
      {
        "knowledge_id": 1580,
        "knowledge_text": "统计能源企业的员工数量时，不用考虑场站的位置，就按照注册地进行统计"
      },
      {
        "knowledge_id": 1581,
        "knowledge_text": "能源类型分类：火电(THERMAL)、水电(HYDRO)、风电(WIND)、光伏(SOLAR)、核电(NUCLEAR)、生物质发电(BIOMASS)、天然气发电(GAS)、抽水蓄能(PUMPED)、地热发电(GEOTHERMAL)、氢能(HYDROGEN)。清洁能源包括水电、核电、天然气发电、抽水蓄能，新能源包括风电、光伏、生物质发电、地热发电、氢能。可再生能源包括水电、风电、光伏、生物质发电、地热发电。"
      },
      {
        "knowledge_id": 1582,
        "knowledge_text": "场站类型代码映射：PP=发电厂，SUB=变电站，TL=输电线路，DS=配电站，WP=风电场，SP=光伏电站，HP=水电站，NP=核电站，ES=储能站，CC=集控中心。发电类场站包括PP、WP、SP、HP、NP。"
      },
      {
        "knowledge_id": 1583,
        "knowledge_text": "装机容量单位MW（兆瓦），年发电量单位万kWh。大型火电厂装机容量≥3000MW，大型水电站装机容量≥1000MW，大型风电场装机容量≥500MW，大型光伏电站装机容量≥200MW。"
      },
      {
        "knowledge_id": 1584,
        "knowledge_text": "企业资质类型：电力业务许可证分为发电类、供电类、新能源类；承装修试许可证分为承装、承修、承试；安全生产许可证由应急管理部颁发。资质过期指 expire_date 小于当前日期。"
      },
      {
        "knowledge_id": 1585,
        "knowledge_text": "供电等级划分：一级供电区域为直辖市、省会城市、计划单列市市区；二级供电区域为地级市市区及经济发达县级市；三级供电区域为普通县级市及农村地区。"
      },
      {
        "knowledge_id": 1586,
        "knowledge_text": "员工状态“在职”表示当前在岗，“离职”表示已离开企业，“退休”表示已办理退休手续，“外派”表示借调至其他单位。"
      },
      {
        "knowledge_id": 1587,
        "knowledge_text": "“五大发电集团”指：华能国际(EC003)、大唐发电(EC004)、华电集团(EC005)、国家电投(EC006)、国家能源集团(EC009)。“两网”指：国家电网(EC001、EC020-EC022)、南方电网(EC002、EC023)。"
      },
      {
        "knowledge_id": 1588,
        "knowledge_text": "资质到期判断：expire_date < CURDATE() 表示已过期，expire_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 180 DAY) 表示未来半年内到期。"
      },
      {
        "knowledge_id": 1589,
        "knowledge_text": "员工学历与岗位对应：技术人员(CE、TE、EE、SE)通常为硕士或博士，值班员(OP)和检修工(MT、EL)通常为本科或大专，管理人员(GM、DM、PM)通常为硕士。"
      },
      {
        "knowledge_id": 1590,
        "knowledge_text": "“西电东送”指将西部地区的电力输送到东部地区。送端省份包括四川、云南、贵州、甘肃、青海、宁夏、陕西、新疆、西藏；受端省份包括上海、江苏、浙江、安徽、福建、山东、广东。"
      },
      {
        "knowledge_id": 1591,
        "knowledge_text": "场站运行状态：'运行'表示正常发电中，'在建'表示施工中尚未并网，'停机'表示临时停运可恢复，'退役'表示永久关停。"
      },
      {
        "knowledge_id": 1592,
        "knowledge_text": "企业注销与场站退役不同：企业 status='注销' 表示企业主体消亡，场站 status='退役' 表示该设施永久关停但所属企业可能仍在运营。"
      },
      {
        "knowledge_id": 1593,
        "knowledge_text": "新能源企业指 business_type='新能源' 的企业，其场站 energy_type_code 通常为 WIND、SOLAR、BIOMASS、GEOTHERMAL、HYDROGEN。"
      },
      {
        "knowledge_id": 1594,
        "knowledge_text": "抽水蓄能电站(PUMPED)的 annual_generation 为0，因为其功能是储能调峰而非发电。统计发电量时应排除 energy_type_code='PUMPED' 的场站。"
      },
      {
        "knowledge_id": 1595,
        "knowledge_text": "企业员工规模等级：大型企业 staff_count≥5000，中型企业 1000≤staff_count<5000，小型企业 staff_count<1000。"
      },
      {
        "knowledge_id": 1596,
        "knowledge_text": "县级市代码特征：前4位中第3-4位为数字（非00），如义乌市(330782)、昆山市(320583)。地级市代码特征：前4位以00结尾。省直管县包括：仙桃市(429004)、潜江市(429005)。"
      },
      {
        "knowledge_id": 1597,
        "knowledge_text": "“双碳”目标指2030年前实现碳达峰、2060年前实现碳中和。清洁能源和新能源是实现双碳目标的主力军。清洁能源装机占比 = 清洁能源装机容量 / 总装机容量 × 100%。"
      },
      {
        "knowledge_id": 1598,
        "knowledge_text": "“三北地区”指东北、华北、西北，是中国风电和光伏的主要集中区域。东北包括黑龙江省、吉林省、辽宁省，华北包括北京市、天津市、河北省、山西省、内蒙古自治区，西北包括陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。"
      },
      {
        "knowledge_id": 1599,
        "knowledge_text": "供电户数超过200万的为特大型供电区域，100万-200万为大型供电区域，50万-100万为中型，低于50万为小型。"
      },
      {
        "knowledge_id": 1600,
        "knowledge_text": "年发电量超过装机容量×5000小时的火电厂为超高效火电厂。火电年平均利用小时数约为4500小时。"
      },
      {
        "knowledge_id": 1601,
        "knowledge_text": "年利用小时数计算公式：年利用小时数 = 年发电量(万kWh) × 10000 ÷ 装机容量(MW) ÷ 1000，简化后为：年利用小时数 = 年发电量(万kWh) ÷ 装机容量(MW) × 10。"
      },
      {
        "knowledge_id": 1602,
        "knowledge_text": "年利用小时数用于衡量发电场站利用效率，通用高效判断阈值为年利用小时数大于3000小时。"
      },
      {
        "knowledge_id": 1603,
        "knowledge_text": "小型发电场站判断标准：装机容量低于100MW。"
      },
      {
        "knowledge_id": 1604,
        "knowledge_text": "stocks.total_shares 表示股本，即公司发行的所有股票数量，单位：股。"
      },
      {
        "knowledge_id": 1605,
        "knowledge_text": "stocks.current_price 表示最新股票价格，通常为最近交易日收盘价，单位：元。"
      },
      {
        "knowledge_id": 1606,
        "knowledge_text": "company_financials.dividend_cash 表示现金分红总额，单位：万元。"
      },
      {
        "knowledge_id": 1607,
        "knowledge_text": "company_financials.dividend_stock 表示每股股息，单位：分/股，计算时需除以100转换为元。"
      },
      {
        "knowledge_id": 1608,
        "knowledge_text": "company_financials.total_assets 表示总资产，单位：万元。"
      },
      {
        "knowledge_id": 1609,
        "knowledge_text": "company_financials.total_liabilities 表示总负债，单位：万元。"
      },
      {
        "knowledge_id": 1610,
        "knowledge_text": "corporate_income_tax_returns.revenue 表示收入总额，单位：万元。"
      },
      {
        "knowledge_id": 1611,
        "knowledge_text": "corporate_income_tax_returns.non_taxable_income 表示不征税收入与免税收入合计，单位：万元。"
      },
      {
        "knowledge_id": 1612,
        "knowledge_text": "corporate_income_tax_returns.deductions 表示扣除金额，单位：万元。"
      },
      {
        "knowledge_id": 1613,
        "knowledge_text": "corporate_income_tax_returns.prior_year_losses 表示允许弥补的以前年度亏损，单位：万元。"
      },
      {
        "knowledge_id": 1614,
        "knowledge_text": "corporate_income_tax_returns.employee_count 表示从业人数，为全年季度平均值，单位：人。"
      },
      {
        "knowledge_id": 1615,
        "knowledge_text": "corporate_income_tax_returns.total_assets 表示资产总额（用于小型微利企业判定），为全年季度平均值，单位：万元。"
      },
      {
        "knowledge_id": 1616,
        "knowledge_text": "companies.is_key_high_tech 表示是否为重点扶持高新技术企业，TRUE表示是，FALSE表示否。"
      },
      {
        "knowledge_id": 1617,
        "knowledge_text": "corporate_income_tax_returns.is_restricted_industry 表示是否从事国家限制或禁止行业，TRUE表示是，FALSE表示否。"
      },
      {
        "knowledge_id": 1618,
        "knowledge_text": "companies.is_tech_advanced_service 表示是否为技术先进型服务企业，TRUE表示是，FALSE表示否。"
      },
      {
        "knowledge_id": 1619,
        "knowledge_text": "companies.established_year 表示公司注册/成立年份，计算成立年限时可用当前年份减该字段。"
      },
      {
        "knowledge_id": 1620,
        "knowledge_text": "companies.registered_capital 表示注册资本，单位：万元。"
      },
      {
        "knowledge_id": 1621,
        "knowledge_text": "companies.is_private 表示是否民营企业，TRUE为民营，FALSE为非民营。"
      },
      {
        "knowledge_id": 1622,
        "knowledge_text": "日成交总价值近似计算公式：volume * close_price，单位：元。"
      },
      {
        "knowledge_id": 1623,
        "knowledge_text": "日平均成交价近似计算公式：日成交总价值 / 成交量，可近似使用收盘价代替。"
      },
      {
        "knowledge_id": 1624,
        "knowledge_text": "每股净资产(BPS)计算公式：(total_assets * 10000) / total_shares，其中总资产由万元转换为元。"
      },
      {
        "knowledge_id": 1625,
        "knowledge_text": "市净率(P/B)计算公式：股价 / 每股净资产，股价可使用最近收盘价。"
      },
      {
        "knowledge_id": 1626,
        "knowledge_text": "净利润近似计算公式：total_assets - total_liabilities（本库特殊定义，实际净利润≠资产-负债）。"
      },
      {
        "knowledge_id": 1627,
        "knowledge_text": "股息率(DYR)计算公式：(dividend_stock / 100.0) / 股价 * 100，其中股息需由分/股转换为元/股。"
      },
      {
        "knowledge_id": 1628,
        "knowledge_text": "应纳税所得额计算公式：revenue - non_taxable_income - deductions - prior_year_losses，单位：万元。"
      },
      {
        "knowledge_id": 1629,
        "knowledge_text": "小型微利企业判定条件：应纳税所得额≤100万元 且 从业人数≤300人 且 资产总额≤5000万元 且 未从事国家限制或禁止行业。"
      },
      {
        "knowledge_id": 1630,
        "knowledge_text": "企业所得税税率规则：高新技术企业适用15%，小型微利企业适用20%，其他企业适用25%。高新技术企业优先于小型微利判定。"
      },
      {
        "knowledge_id": 1631,
        "knowledge_text": "企业所得税额计算公式：应纳税所得额 × 适用税率，单位：万元。"
      },
      {
        "knowledge_id": 1632,
        "knowledge_text": "市盈率(PE)近似计算公式：股价 / (净利润 / 总股本) = current_price / ((total_assets - total_liabilities) * 10000 / total_shares)。"
      },
      {
        "knowledge_id": 1633,
        "knowledge_text": "换手率计算公式：(volume / total_shares) * 100%，反映股票交易活跃程度。"
      },
      {
        "knowledge_id": 1634,
        "knowledge_text": "资产负债率计算公式：(total_liabilities / total_assets) * 100%，单位：%。"
      },
      {
        "knowledge_id": 1635,
        "knowledge_text": "每股收益(EPS)近似计算公式：净利润 / 总股本 = (total_assets - total_liabilities) * 10000 / total_shares。"
      },
      {
        "knowledge_id": 1636,
        "knowledge_text": "日涨跌幅计算公式：(close_price - open_price) / open_price * 100%，单位：%。"
      },
      {
        "knowledge_id": 1637,
        "knowledge_text": "红利支付率计算公式：dividend_cash / (total_assets - total_liabilities) * 100%，单位：%。"
      },
      {
        "knowledge_id": 1638,
        "knowledge_text": "净资产收益率(ROE)计算公式：(净利润 / 净资产) × 100%。其中净利润 = total_assets - total_liabilities，净资产 = total_assets，本库中以每股收益/每股净资产替代计算。单位：%。"
      },
      {
        "knowledge_id": 1639,
        "knowledge_text": "实际税负率计算公式：(应纳税额 / 收入总额) × 100%。其中应纳税额 = 应纳税所得额 × 适用税率，单位：%。"
      },
      {
        "knowledge_id": 1640,
        "knowledge_text": "年化波动率计算公式：日涨跌幅的标准差 × SQRT(250)，其中日涨跌幅 = (close_price - open_price) / open_price。250为年交易日数近似值。单位：%。"
      },
      {
        "knowledge_id": 1641,
        "knowledge_text": "所得税贡献率计算公式：(应纳税额 / 资产总额) × 100%。其中应纳税额 = 应纳税所得额 × 适用税率，资产总额取自申报表中的全年季度平均值。单位：%。"
      },
      {
        "knowledge_id": 1642,
        "knowledge_text": "资产周转率计算公式：收入总额 / 资产总额，反映企业资产运营效率。单位：倍。"
      },
      {
        "knowledge_id": 1643,
        "knowledge_text": "股价波动幅度比例（价格波动率）计算公式：(年内最高价 - 年内最低价) / 年内均价，年内均价可用收盘价均值近似。反映股价年度波动程度。"
      },
      {
        "knowledge_id": 1644,
        "knowledge_text": "股票总市值计算公式：current_price × total_shares，单位：元。其中 current_price 为最新股价（元），total_shares 为总股本（股）。"
      },
      {
        "knowledge_id": 1645,
        "knowledge_text": "总资产收益率(ROA)计算公式：(净利润 / 总资产) × 100%。本库中净利润 = total_assets - total_liabilities，单位：%。"
      },
      {
        "knowledge_id": 1646,
        "knowledge_text": "每股现金分红(DPS)计算公式：dividend_cash × 10000 / total_shares。dividend_cash 单位为万元，需转换为元后除以总股本（股），结果单位：元/股。"
      },
      {
        "knowledge_id": 1647,
        "knowledge_text": "收入扣除后利润率计算公式：(revenue - deductions) / revenue × 100%，单位：%。反映扣除后的利润空间。"
      },
      {
        "knowledge_id": 1648,
        "knowledge_text": "股票按股东权利分类：普通股(COMMON)、优先股(PREFERRED)，字段stocks.share_right_type。"
      },
      {
        "knowledge_id": 1649,
        "knowledge_text": "股票按是否记名分类：记名股票(REGISTERED)、无记名股票(BEARER)，字段stocks.register_type。"
      },
      {
        "knowledge_id": 1650,
        "knowledge_text": "股票按面额标示分类：面额股(PAR)、无面额股(NO_PAR)，字段stocks.par_value_type。"
      },
      {
        "knowledge_id": 1651,
        "knowledge_text": "中国股票按上市地点和投资者分类：A股（境内上市，人民币交易）、B股（境内上市，外币交易）、H股（香港上市）、N股（纽约上市）等，字段stocks.market_class。"
      },
      {
        "knowledge_id": 1652,
        "knowledge_text": "高新技术企业认定资格由companies.is_key_high_tech字段标识，若为TRUE则适用15%优惠税率，相比普通税率25%可节省10%的应纳税额。"
      },
      {
        "knowledge_id": 1653,
        "knowledge_text": "小型微利企业判定基于年度申报数据，满足条件则适用20%优惠税率。判定条件见知识108。"
      },
      {
        "knowledge_id": 1654,
        "knowledge_text": "一般企业所得税税率为25%。"
      },
      {
        "knowledge_id": 1655,
        "knowledge_text": "若corporate_income_tax_returns.is_restricted_industry为TRUE，表示企业从事国家限制或禁止行业，不能享受小型微利企业优惠。"
      },
      {
        "knowledge_id": 1656,
        "knowledge_text": "技术先进型服务企业可享受企业所得税优惠税率15%，与高新技术企业待遇相同。"
      },
      {
        "knowledge_id": 1657,
        "knowledge_text": "符合条件的小型微利企业，年应纳税所得额不超过100万元的部分，减按25%计入应纳税所得额，按20%税率缴纳企业所得税（实际税负5%）。本库按简化规则直接使用20%税率。"
      },
      {
        "knowledge_id": 1658,
        "knowledge_text": "企业研究开发费用未形成无形资产计入当期损益的，在按照规定据实扣除的基础上，可按研究开发费用的100%在税前加计扣除（制造业企业），其他企业按75%。本库中加计扣除包含在deductions字段内。"
      },
      {
        "knowledge_id": 1659,
        "knowledge_text": "上市公司所属行业分类存储在companies.industry_code，对应的行业名称在common.dict_industry表中。"
      },
      {
        "knowledge_id": 1660,
        "knowledge_text": "企业规模划型分为大型、中型、小型、微型，存储在companies.size_category_code，可通过common.dict_size_category查看名称。"
      },
      {
        "knowledge_id": 1661,
        "knowledge_text": "企业成立年限 = 当前年份 - companies.established_year。"
      },
      {
        "knowledge_id": 1662,
        "knowledge_text": "某些税收优惠政策与行业有关，如高新技术企业主要集中在制造业、信息技术等行业，但数据库已有is_key_high_tech字段，无需依赖行业推断。"
      },
      {
        "knowledge_id": 1663,
        "knowledge_text": "登记注册类型通过companies.registration_type_code引用字典表common.dict_registration_type，常见的类型包括：有限责任公司、股份有限公司、国有独资公司等，国有独资公司也是国有企业。"
      },
      {
        "knowledge_id": 1664,
        "knowledge_text": "企业集中度指每个行业收入最高的n个企业占行业总收入的比例，CRn指数通过计算前n位企业数据总和与行业总数据的比值。"
      },
      {
        "knowledge_id": 1665,
        "knowledge_text": "上海静安寺的经纬度坐标为 (lat: 31.2235, lon: 121.4447)"
      },
      {
        "knowledge_id": 1666,
        "knowledge_text": "上海人民广场的经纬度坐标为 (lat: 31.2304, lon: 121.4737)"
      },
      {
        "knowledge_id": 1667,
        "knowledge_text": "上海外滩的经纬度坐标为 (lat: 31.2389, lon: 121.4885)"
      },
      {
        "knowledge_id": 1668,
        "knowledge_text": "上海东方明珠塔的经纬度坐标为 (lat: 31.2395, lon: 121.4990)"
      },
      {
        "knowledge_id": 1669,
        "knowledge_text": "上海迪士尼乐园的经纬度坐标为 (lat: 31.1440, lon: 121.6600)"
      },
      {
        "knowledge_id": 1670,
        "knowledge_text": "上海虹桥火车站的经纬度坐标为 (lat: 31.1950, lon: 121.3180)"
      },
      {
        "knowledge_id": 1671,
        "knowledge_text": "上海浦东国际机场的经纬度坐标为 (lat: 31.1450, lon: 121.8050)"
      },
      {
        "knowledge_id": 1672,
        "knowledge_text": "北京天安门广场的经纬度坐标为 (lat: 39.9087, lon: 116.3975)"
      },
      {
        "knowledge_id": 1673,
        "knowledge_text": "北京故宫博物院的经纬度坐标为 (lat: 39.9163, lon: 116.3972)"
      },
      {
        "knowledge_id": 1674,
        "knowledge_text": "北京颐和园的经纬度坐标为 (lat: 39.9991, lon: 116.2747)"
      },
      {
        "knowledge_id": 1675,
        "knowledge_text": "北京奥林匹克公园的经纬度坐标为 (lat: 40.0000, lon: 116.4000)"
      },
      {
        "knowledge_id": 1676,
        "knowledge_text": "北京南站的经纬度坐标为 (lat: 39.8630, lon: 116.3760)"
      },
      {
        "knowledge_id": 1677,
        "knowledge_text": "北京首都国际机场的经纬度坐标为 (lat: 40.0800, lon: 116.5850)"
      },
      {
        "knowledge_id": 1678,
        "knowledge_text": "广州塔的经纬度坐标为 (lat: 23.1090, lon: 113.3245)"
      },
      {
        "knowledge_id": 1679,
        "knowledge_text": "广州珠江新城的经纬度坐标为 (lat: 23.1250, lon: 113.3250)"
      },
      {
        "knowledge_id": 1680,
        "knowledge_text": "广州白云山的经纬度坐标为 (lat: 23.1870, lon: 113.2970)"
      },
      {
        "knowledge_id": 1681,
        "knowledge_text": "广州南站的经纬度坐标为 (lat: 22.9910, lon: 113.2670)"
      },
      {
        "knowledge_id": 1682,
        "knowledge_text": "深圳市民中心的经纬度坐标为 (lat: 22.5490, lon: 114.0562)"
      },
      {
        "knowledge_id": 1683,
        "knowledge_text": "深圳世界之窗的经纬度坐标为 (lat: 22.5340, lon: 113.9690)"
      },
      {
        "knowledge_id": 1684,
        "knowledge_text": "深圳欢乐谷的经纬度坐标为 (lat: 22.5350, lon: 113.9730)"
      },
      {
        "knowledge_id": 1685,
        "knowledge_text": "深圳宝安国际机场的经纬度坐标为 (lat: 22.6390, lon: 113.8100)"
      },
      {
        "knowledge_id": 1686,
        "knowledge_text": "杭州西湖的经纬度坐标为 (lat: 30.2470, lon: 120.1480)"
      },
      {
        "knowledge_id": 1687,
        "knowledge_text": "杭州雷峰塔的经纬度坐标为 (lat: 30.2360, lon: 120.1460)"
      },
      {
        "knowledge_id": 1688,
        "knowledge_text": "杭州东站的经纬度坐标为 (lat: 30.2930, lon: 120.2130)"
      },
      {
        "knowledge_id": 1689,
        "knowledge_text": "成都天府广场的经纬度坐标为 (lat: 30.6600, lon: 104.0630)"
      },
      {
        "knowledge_id": 1690,
        "knowledge_text": "成都宽窄巷子的经纬度坐标为 (lat: 30.6670, lon: 104.0580)"
      },
      {
        "knowledge_id": 1691,
        "knowledge_text": "成都双流国际机场的经纬度坐标为 (lat: 30.5780, lon: 103.9610)"
      },
      {
        "knowledge_id": 1692,
        "knowledge_text": "武汉黄鹤楼的经纬度坐标为 (lat: 30.5430, lon: 114.2970)"
      },
      {
        "knowledge_id": 1693,
        "knowledge_text": "武汉光谷广场的经纬度坐标为 (lat: 30.5020, lon: 114.3950)"
      },
      {
        "knowledge_id": 1694,
        "knowledge_text": "西安钟楼的经纬度坐标为 (lat: 34.2600, lon: 108.9400)"
      },
      {
        "knowledge_id": 1695,
        "knowledge_text": "西安大雁塔的经纬度坐标为 (lat: 34.2220, lon: 108.9690)"
      },
      {
        "knowledge_id": 1696,
        "knowledge_text": "复旦大学附属华山医院的经纬度坐标为 (lat: 31.2230, lon: 121.4428)"
      },
      {
        "knowledge_id": 1697,
        "knowledge_text": "上海交通大学医学院附属瑞金医院的经纬度坐标为 (lat: 31.2125, lon: 121.4682)"
      },
      {
        "knowledge_id": 1698,
        "knowledge_text": "北京协和医院的经纬度坐标为 (lat: 39.9087, lon: 116.4135)"
      },
      {
        "knowledge_id": 1699,
        "knowledge_text": "四川大学华西医院的经纬度坐标为 (lat: 30.6460, lon: 104.0610)"
      },
      {
        "knowledge_id": 1700,
        "knowledge_text": "中山大学附属第一医院的经纬度坐标为 (lat: 23.1310, lon: 113.2895)"
      },
      {
        "knowledge_id": 1701,
        "knowledge_text": "深圳市人民医院的经纬度坐标为 (lat: 22.5565, lon: 114.1158)"
      },
      {
        "knowledge_id": 1702,
        "knowledge_text": "浙江大学医学院附属第一医院的经纬度坐标为 (lat: 30.2630, lon: 120.1650)"
      },
      {
        "knowledge_id": 1703,
        "knowledge_text": "大型医院的定义：床位数(bed_count) >= 1500 且 医生数(doctor_count) >= 1500。"
      },
      {
        "knowledge_id": 1704,
        "knowledge_text": "顶尖三甲医院的标准：拥有ICU(has_icu=true) 且 救护车数量(ambulance_count) >= 20 且 患者评分(rating) >= 4.8。"
      },
      {
        "knowledge_id": 1705,
        "knowledge_text": "医师力量强的医院定义：医生数(doctor_count) >= 2000 或 年门诊量(annual_outpatient) >= 4000000。"
      },
      {
        "knowledge_id": 1706,
        "knowledge_text": "高负荷医院的定义：年门诊量(annual_outpatient) >= 5000000。"
      },
      {
        "knowledge_id": 1707,
        "knowledge_text": "急诊能力充足的医院定义：24小时急诊(emergency_24h=true) 且 救护车数量(ambulance_count) >= 10。"
      },
      {
        "knowledge_id": 1708,
        "knowledge_text": "教学医院的定义：is_teaching_hospital = true。"
      },
      {
        "knowledge_id": 1709,
        "knowledge_text": "超大规模医院的定义：床位数(bed_count) >= 2000 且 年门诊量(annual_outpatient) >= 6000000。"
      },
      {
        "knowledge_id": 1710,
        "knowledge_text": "优秀护理医院的判断标准：护士数(nurse_count) >= 2000 且 床位数/护士数比值 <= 1.2。"
      },
      {
        "knowledge_id": 1711,
        "knowledge_text": "现代化医院的定义：拥有ICU(has_icu=true) 且 科室数量(department_count) >= 40。"
      },
      {
        "knowledge_id": 1712,
        "knowledge_text": "老牌知名医院的定义：成立年份(founded_year) <= 1950 且 评分(rating) >= 4.6。"
      },
      {
        "knowledge_id": 1713,
        "knowledge_text": "上海青草沙水源地禁航区四边形水域，四个顶点坐标分别为：A(31°26′08.329″N,121°34′18.678″E)、B(31°26′42.713″N,121°33′39.136″E)、C(31°27′10.312″N,121°33′58.456″E)、D(31°26′36.982″N,121°34′35.287″E)，转换为十进制度约为A(121.5719,31.4356)、B(121.5609,31.4452)、C(121.5663,31.4529)、D(121.5765,31.4414)，按A-B-C-D-A顺序围成闭合多边形"
      },
      {
        "knowledge_id": 1714,
        "knowledge_text": "长江口禁捕管理区范围为东经122°15′（122.25°）以东至124.0°、北纬30°54′（30.90°）至31°41′36″（31.6933°）之间的矩形水域，向西以水陆交界线为界"
      },
      {
        "knowledge_id": 1715,
        "knowledge_text": "黄浦江核心管制区为川杨河口下游100米处（约31°10′12″N,121°29′00″E）至南浦大桥（约31°12′30″N,121°30′30″E）之间的水域"
      },
      {
        "knowledge_id": 1716,
        "knowledge_text": "珠江口水上交通安全特别监管区，东至114°30′08.8″E（114.5024°）经度线，南至21°45′00.0″N（21.75°）纬度线，西至112°59′30″E（112.9917°）经度线，北至广州港黄埔大桥附近（约23.5°以覆盖整个监管区）"
      },
      {
        "knowledge_id": 1717,
        "knowledge_text": "杭州湾水域某次实弹训练禁航区范围为北纬30°19′（30.317°）至30°35′（30.583°），东经121°02′（121.033°）至121°12′（121.20°）的矩形水域"
      },
      {
        "knowledge_id": 1718,
        "knowledge_text": "天津港地处渤海西部海岸海河入海口处，中心位置东经117°42′05″（117.7014°），北纬38°59′08″（38.9856°）。海河水域新港船闸维修禁航区：以38-59.5N 117-42.8E（38.9917°N,117.7133°E）为圆心，半径250米的水域。海河下游二道闸至轮驳公司码头段为通航管制区"
      },
      {
        "knowledge_id": 1719,
        "knowledge_text": "渤海海峡老铁山水道禁航区（军事任务）。禁航区范围为以下四点连线围成的水域：A(38°36.0′N,121°15.0′E)、B(38°36.0′N,121°30.0′E)、C(38°18.0′N,121°30.0′E)、D(38°18.0′N,121°15.0′E)。该区域为军事演习或武器试验临时禁航区，禁止所有船舶驶入。禁航时段通常由海事部门通过航行警告提前发布，船舶应保持VHF16频道守听，并重新规划航线绕行。"
      },
      {
        "knowledge_id": 1720,
        "knowledge_text": "青岛港主航道（第一分道通航制）。分道通航制位于大公岛和小公岛连线以西的青岛港主航道内侧，进港船舶通航分道和出港船舶通航分道之间由分隔带分隔。进港主交通流向282°（真航向），出港主交通流向103°。定线制水域范围约为：北纬35°59′30″至36°01′00″，东经120°27′00″至120°30′00″。该区域为进出青岛港的大型船舶主要通道，船舶应严格按分道通航制航行，禁止逆向行驶。"
      },
      {
        "knowledge_id": 1721,
        "knowledge_text": "烟台港西港区航道及警戒区。烟台港西港区航道坐标为：入口点A(37°46.5′N,121°11.8′E)至防波堤口B(37°44.0′N,121°12.0′E)，航道长度约2.5海里，宽度300米，水深-20米。航道入口处设警戒区，以点(37°46.5′N,121°11.8′E)为中心、半径0.5海里的圆形水域。船舶进入警戒区前应向烟台VTS中心报告，航道内限速12节，禁止追越和锚泊。"
      },
      {
        "knowledge_id": 1722,
        "knowledge_text": "舟山虾峙门深水航道（进港航道）。虾峙门航道是宁波舟山港核心港区最重要的深水进港航道，地理范围：自虾峙门东口（29°45.0′N,122°25.0′E）至螺头角（29°54.0′N,122°01.0′E），全长约24海里，航道宽度约0.3海里，水深22米以上，可满足30万吨级船舶通航。航道两侧设有分道通航制，中间由分隔带分隔。船舶在航道内应保持VHF08频道守听，按照潮汐时段单向通航，大型船舶需引航。"
      },
      {
        "knowledge_id": 1723,
        "knowledge_text": "珠江口桂山锚地。桂山锚地位于珠江口桂山岛附近，是进出广州港、深圳港、珠海港的大型船舶候泊、引航、联检锚地。锚地范围由以下四点围成：A(22°10.0′N,113°48.0′E)、B(22°10.0′N,113°52.0′E)、C(22°07.0′N,113°52.0′E)、D(22°07.0′N,113°48.0′E)。锚地水深12-18米，底质泥沙，可锚泊10万吨级以下船舶。锚地内船舶应按规定显示锚泊信号，保持VHF16频道守听，不得排放污染物。"
      },
      {
        "knowledge_id": 1724,
        "knowledge_text": "长江口南槽航道（A-N槽）。南槽航道是长江口主要辅助航道，供吃水较浅的船舶进出长江。航道范围：自南槽灯船（31°02.0′N,122°32.0′E）沿自然水深向上游至浏河口（31°30.0′N,121°17.0′E），全长约60海里，航道宽度250-500米，维护水深5.5-6.5米。航道两侧设有浮筒，船舶应沿浮筒标示的航槽行驶，禁止在航道内锚泊或捕捞。船舶须遵守《长江口船舶交通管理系统（VTS）安全监督管理办法》，向吴淞VTS中心报告。"
      },
      {
        "knowledge_id": 1725,
        "knowledge_text": "厦门港东渡港区航道及锚地。东渡港区航道自青屿水域（24°26.0′N,118°06.0′E）至东渡码头前沿，全长约8海里，航道宽度200米，水深-12米。港区锚地位于猴屿西侧，范围为：A(24°28.0′N,118°04.0′E)、B(24°28.0′N,118°06.0′E)、C(24°26.0′N,118°06.0′E)、D(24°26.0′N,118°04.0′E)，水深10-14米。该区域为船舶进出厦门港西航道的主要通道，船舶应遵守《厦门水域船舶定线制》和《厦门船舶交通管理系统（VTS）用户指南》。"
      },
      {
        "knowledge_id": 1726,
        "knowledge_text": "大连大窑湾港区航道及警戒区。大窑湾航道自大窑湾口（39°00.0′N,121°55.0′E）至集装箱码头（38°59.5′N,121°46.5′E），全长约7海里，宽度280米，水深-14米。大窑湾口设警戒区，以点(39°00.0′N,121°55.0′E)为中心、半径0.6海里。船舶进入警戒区前应向大窑湾VTS中心报告（VHF11频道），航道内限速10节，大型船舶需申请引航。该水域船舶交通密集，进出船应加强瞭望。"
      },
      {
        "knowledge_id": 1727,
        "knowledge_text": "北部湾涠洲岛警戒区。涠洲岛警戒区以涠洲岛西角码头西侧点为圆心、半径3海里的扇形水域，具体范围：以W点(21°02′02″N,109°06′43″E)为中心，半径3海里（5556米），方位240°至360°的扇形区域。该警戒区位于北部湾海上石油平台密集区和旅游航线交汇处，船舶交通流量大。船舶进入警戒区应减速谨慎驾驶，加强与过往船舶通信，避免碰撞。禁止在警戒区内抛锚或进行捕鱼作业。"
      },
      {
        "knowledge_id": 1728,
        "knowledge_text": "上海洋山深水港区航道。洋山港航道自黄泽洋灯船（30°31.0′N,122°15.0′E）至洋山港主航道口（30°35.0′N,122°03.0′E），全长约20海里，航道宽度400米，水深-16米。航道两侧设有大型灯浮，实行分道通航制：西行船舶（进港）走北侧分道，东行船舶（出港）走南侧分道。该航道可通航15万吨级集装箱船。船舶进入航道前应向洋山VTS中心（VHF13频道）报告，大型船舶须引航。"
      },
      {
        "knowledge_id": 1729,
        "knowledge_text": "渤海湾曹妃甸港区航道及锚地。曹妃甸港区主航道自20万吨级矿石码头（38°55.0′N,118°30.0′E）向外海延伸至38°51.0′N,118°35.0′E，全长约11海里，宽度350米，水深-21米。港区设有1#和2#锚地：1#锚地位于38°54.0′N-38°56.0′N,118°35.0′E-118°40.0′E，2#锚地位于38°51.0′N-38°53.0′N,118°35.0′E-118°40.0′E。锚地底质为泥沙，可锚泊15万吨级以下船舶。船舶进出港需遵守《曹妃甸船舶交通管理系统（VTS）安全管理规定》。"
      },
      {
        "knowledge_id": 1730,
        "knowledge_text": "渤海海峡长山水道（禁航区）。长山水道为渤海海峡三大水道之一，位于长山列岛之间，是大型船舶进出渤海的重要通道。禁航区范围为以下四点连线所围水域：A(38°20.0′N,120°45.0′E)、B(38°20.0′N,121°00.0′E)、C(38°10.0′N,121°00.0′E)、D(38°10.0′N,120°45.0′E)。该区域为军事训练禁航区，定期发布航行警告禁止船舶进入。船舶应通过VHF16频道获取最新禁航信息，并改用老铁山水道或登州水道绕行。"
      },
      {
        "knowledge_id": 1731,
        "knowledge_text": "香港水域东博寮海峡分道航行制。东博寮海峡是香港主要南向航道，分道通航制范围为：北起(22°15.0′N,114°15.0′E)，南至(22°10.0′N,114°13.0′E)。实行分隔制，进港船舶（向北）使用东侧分道，出港船舶（向南）使用西侧分道。两侧分道各宽0.2海里，中间分隔带宽0.05海里。船舶在该水域航行必须遵守《香港水域船舶交通管制条例》，使用VHF12频道与香港海事处交管中心联系，海峡内禁止锚泊和捕鱼。"
      },
      {
        "knowledge_id": 1732,
        "knowledge_text": "汕尾遮浪角海域军事禁航区。遮浪角位于汕尾红海湾东侧，军事禁航区范围为以下四点围成的水域：A(22°45.0′N,115°35.0′E)、B(22°45.0′N,115°45.0′E)、C(22°30.0′N,115°45.0′E)、D(22°30.0′N,115°35.0′E)。该区域经常进行实弹射击和军事演习，航行通告会提前发布禁航时段。禁航期间任何船舶不得驶入，否则将面临军事处罚。过往船舶应绕行外海，保持VHF16频道守听。"
      },
      {
        "knowledge_id": 1733,
        "knowledge_text": "温州港状元岙港区航道。状元岙港区航道自大门岛东侧（27°58.0′N,121°10.0′E）至状元岙码头前沿（27°55.0′N,121°07.0′E），全长约5海里，航道宽度180米，水深-10米。航道两侧设有灯浮标示，航道内设有2处转向点。船舶进出港需向温州VTS中心（VHF14频道）报告，航道内限速8节，禁止追越。该水域受潮汐影响较大，吃水超过9米的船舶应乘高潮通过。"
      },
      {
        "knowledge_id": 1734,
        "knowledge_text": "台州港头门港区航道及警戒区。头门港区航道自点(28°40.0′N,121°40.0′E)至点(28°38.0′N,121°36.0′E)，全长约8海里，航道宽度200米，水深-9米。港外警戒区位于航道口门处，以点(28°40.0′N,121°40.0′E)为中心、半径0.4海里。警戒区外东侧设有候潮锚地（28°40.5′N-28°42.0′N,121°42.0′E-121°44.0′E）。船舶进入警戒区前应向台州VTS中心（VHF16频道）报告，航道内禁止锚泊，大型船舶需引航。"
      },
      {
        "knowledge_id": 1735,
        "knowledge_text": "福建福清湾水域船舶定线制。福清湾船舶定线制范围为：北起(25°35.0′N,119°35.0′E)，南至(25°25.0′N,119°30.0′E)。实行分道通航，进港船舶（向北）使用东侧分道，出港船舶（向南）使用西侧分道，分隔带为虚拟线段。该定线制连接福清湾内各码头，船舶须遵守《福建船舶交通管理系统（VTS）服务指南》，使用VHF10频道与福州VTS中心报告。湾内航道水深变化较大，船舶应参照最新海图航行。"
      },
      {
        "knowledge_id": 1736,
        "knowledge_text": "汕头港广澳港区航道及锚地。广澳港区航道自广澳湾口（23°15.0′N,116°50.0′E）至广澳码头（23°13.0′N,116°46.0′E），全长约5.5海里，航道宽度150米，水深-11米。港区锚地位于航道西侧，范围为：A(23°14.0′N,116°48.0′E)、B(23°14.0′N,116°50.0′E)、C(23°12.0′N,116°50.0′E)、D(23°12.0′N,116°48.0′E)。锚地水深9-12米。船舶进出港需向汕头VTS中心报告（VHF08频道），航道内限速10节，禁止在航道内追越。"
      },
      {
        "knowledge_id": 1737,
        "knowledge_text": "海南清澜港航道及禁航区。清澜港航道自七洲列岛附近（19°45.0′N,111°10.0′E）至清澜港码头（19°35.0′N,110°50.0′E），全长约22海里，航道宽度150米，水深-7米。港区南侧设有军事禁航区，范围为以(19°30.0′N,111°00.0′E)为中心、半径5海里的圆形水域，为某部海军训练区，全年禁航。民用船舶应保持与禁航区边界至少2海里的安全距离，不得进入。清澜港航道内常有渔船作业，进出港船舶应加强瞭望。"
      },
      {
        "knowledge_id": 1738,
        "knowledge_text": "北部湾防城港东湾航道及锚地。东湾航道自东湾口（21°35.0′N,108°25.0′E）至防城港码头前沿（21°38.0′N,108°21.0′E），全长约8海里，航道宽度180米，水深-11米。港区锚地位于航道南侧，范围为：A(21°32.0′N,108°24.0′E)、B(21°32.0′N,108°27.0′E)、C(21°30.0′N,108°27.0′E)、D(21°30.0′N,108°24.0′E)，水深8-12米。船舶进出港需向防城港VTS中心（VHF11频道）报告，航道内限速8节，锚地内船舶应保持安全间距，避免锚泊碰撞。"
      },
      {
        "knowledge_id": 1739,
        "knowledge_text": "异常航行记录：指航行状态nav_status=1（航行中）sog15或sog0.5"
      },
      {
        "knowledge_id": 1740,
        "knowledge_text": "停泊：包括nav_status=1锚泊和nav_status=5系泊"
      },
      {
        "knowledge_id": 1741,
        "knowledge_text": "青岛朝连岛附近水域禁航区（军事任务）。朝连岛位于青岛东南海域，禁航区范围为以下四点连线围成的水域：A(35°50.0′N,121°10.0′E)、B(35°50.0′N,121°30.0′E)、C(35°35.0′N,121°30.0′E)、D(35°35.0′N,121°10.0′E)。该区域经常用于海军实弹射击和军事演习，航行警告会提前发布禁航时段。禁航期间任何船舶不得驶入，过往船舶应绕行外海，保持VHF16频道守听。"
      },
      {
        "knowledge_id": 1742,
        "knowledge_text": "日照港石臼港区航道及警戒区。石臼港区航道自航道入口（35°20.0′N,119°35.0′E）至煤炭码头前沿（35°18.5′N,119°32.0′E），全长约6海里，航道宽度250米，水深-18米。航道入口处设警戒区，以点(35°20.0′N,119°35.0′E)为中心、半径0.5海里的圆形水域。船舶进入警戒区前应向日照VTS中心报告（VHF14频道），航道内限速10节，大型船舶需引航。"
      },
      {
        "knowledge_id": 1743,
        "knowledge_text": "连云港港主航道及锚地。连云港主航道自外海引航点（34°45.0′N,119°50.0′E）至庙岭集装箱码头（34°45.0′N,119°20.0′E），全长约25海里，航道宽度220米，水深-14米。港区设有2号锚地，范围为：A(34°48.0′N,119°40.0′E)、B(34°48.0′N,119°45.0′E)、C(34°45.0′N,119°45.0′E)、D(34°45.0′N,119°40.0′E)，水深12-15米。船舶进出港需向连云港VTS中心报告，航道内禁止追越。"
      },
      {
        "knowledge_id": 1744,
        "knowledge_text": "南通港天生港区航道及警戒区。天生港区航道自通州沙西水道入口（32°02.0′N,120°45.0′E）至天生港码头（32°00.0′N,120°43.0′E），全长约4海里，航道宽度150米，水深-8米。航道口门处设警戒区，以点(32°02.0′N,120°45.0′E)为中心、半径0.3海里。该水道水流湍急，船舶应谨慎驾驶，禁止在航道内锚泊。"
      },
      {
        "knowledge_id": 1745,
        "knowledge_text": "镇江港大港港区航道及锚地。大港港区航道自和畅洲北汊入口（32°12.0′N,119°40.0′E）至大港码头前沿（32°11.0′N,119°37.0′E），全长约5海里，航道宽度200米，水深-10米。港区锚地位于和畅洲南侧，范围为：A(32°10.0′N,119°38.0′E)、B(32°10.0′N,119°42.0′E)、C(32°08.0′N,119°42.0′E)、D(32°08.0′N,119°38.0′E)。船舶进出港需遵守《长江江苏段船舶定线制规定》，向镇江VTS中心报告。"
      },
      {
        "knowledge_id": 1746,
        "knowledge_text": "江阴港夏港港区航道及警戒区。夏港港区航道自江阴长江大桥下游（31°57.0′N,120°15.0′E）至夏港码头（31°56.0′N,120°12.0′E），全长约4.5海里，航道宽度180米，水深-9米。航道入口处设警戒区，以点(31°57.0′N,120°15.0′E)为中心、半径0.4海里。该水域船舶交通密集，港内限速8节，禁止追越。"
      },
      {
        "knowledge_id": 1747,
        "knowledge_text": "张家港港务局码头前沿水域（通航密集区）。张家港港务局码头前沿水域范围为：自(31°56.0′N,120°28.0′E)至(31°53.0′N,120°24.0′E)沿江岸线外300米水域。该区域码头泊位密集，常有多艘船舶同时靠离泊作业。过往船舶应保持安全航速，加强与码头调度通信，避免进入靠离泊作业区。"
      },
      {
        "knowledge_id": 1748,
        "knowledge_text": "常熟港兴华港区航道。兴华港区航道自白茆沙北水道入口（31°45.0′N,121°00.0′E）至兴华码头（31°43.0′N,120°55.0′E），全长约8海里，航道宽度160米，水深-8.5米。航道两侧设有浮筒，船舶应沿浮筒标示航行。该航道受潮汐影响明显，吃水超过7米的船舶应乘高潮通过。"
      },
      {
        "knowledge_id": 1749,
        "knowledge_text": "太仓港集装箱港区航道及警戒区。太仓港航道自长江#10浮（31°38.0′N,121°15.0′E）至集装箱码头前沿（31°36.0′N,121°12.0′E），全长约5海里，航道宽度200米，水深-12米。港区警戒区位于航道入口，以点(31°38.0′N,121°15.0′E)为中心、半径0.5海里。船舶进入警戒区前应向太仓VTS中心报告，航道内限速10节。"
      },
      {
        "knowledge_id": 1750,
        "knowledge_text": "上海港外高桥港区航道（长江口段）。外高桥港区航道自长江口圆圆沙灯船（31°22.0′N,121°38.0′E）至外高桥码头（31°20.0′N,121°33.0′E），全长约7海里，航道宽度300米，水深-12.5米。该航道为进出上海港的主要通道之一，实行分道通航制，船舶应保持VHF14频道守听，遵守《长江口船舶交通管理系统（VTS）安全监督管理办法》。"
      },
      {
        "knowledge_id": 1751,
        "knowledge_text": "杭州湾嘉兴港区航道。嘉兴港区航道自杭州湾入口（30°33.0′N,121°05.0′E）至独山码头（30°35.0′N,121°00.0′E），全长约10海里，航道宽度200米，水深-9米。航道两侧设有灯浮，航道内设有2处转向点。该水域潮流强劲，船舶应选择高平潮时段进出港，禁止在航道内锚泊。"
      },
      {
        "knowledge_id": 1752,
        "knowledge_text": "宁波舟山港穿山港区航道及警戒区。穿山港区航道自虾峙门航道东口（29°52.0′N,122°10.0′E）至穿山码头前沿（29°55.0′N,122°00.0′E），全长约12海里，航道宽度350米，水深-18米。港区警戒区位于航道入口，以点(29°52.0′N,122°10.0′E)为中心、半径0.6海里。船舶进入警戒区前应向穿山VTS中心报告，大型船舶需引航。"
      },
      {
        "knowledge_id": 1753,
        "knowledge_text": "台州港大麦屿港区航道及锚地。大麦屿港区航道自乐清湾口（28°05.0′N,121°05.0′E）至大麦屿码头（28°08.0′N,121°00.0′E），全长约8海里，航道宽度180米，水深-11米。港区锚地位于航道东侧，范围为：A(28°06.0′N,121°06.0′E)、B(28°06.0′N,121°08.0′E)、C(28°04.0′N,121°08.0′E)、D(28°04.0′N,121°06.0′E)，水深10-13米。船舶进出港需向台州VTS中心报告，航道内限速8节。"
      },
      {
        "knowledge_id": 1754,
        "knowledge_text": "温州港乐清湾港区航道。乐清湾港区航道自大门岛东侧（27°58.0′N,121°12.0′E）至乐清湾码头（27°55.0′N,121°05.0′E），全长约12海里，航道宽度200米，水深-10米。航道两侧设有浮筒，航道内设有3处转向点。该水域渔船较多，进出港船舶应加强瞭望，保持安全航速。"
      },
      {
        "knowledge_id": 1755,
        "knowledge_text": "福州港江阴港区航道及警戒区。江阴港区航道自兴化湾口（25°20.0′N,119°40.0′E）至江阴码头（25°25.0′N,119°20.0′E），全长约15海里，航道宽度250米，水深-15米。港区警戒区位于航道入口，以点(25°20.0′N,119°40.0′E)为中心、半径0.5海里。船舶进入警戒区前应向福州VTS中心报告（VHF10频道），大型船舶需引航。"
      },
      {
        "knowledge_id": 1756,
        "knowledge_text": "泉州港石湖港区航道及锚地。石湖港区航道自泉州湾口（24°45.0′N,118°50.0′E）至石湖码头（24°48.0′N,118°42.0′E），全长约10海里，航道宽度200米，水深-12米。港区锚地位于航道东侧，范围为：A(24°46.0′N,118°52.0′E)、B(24°46.0′N,118°55.0′E)、C(24°44.0′N,118°55.0′E)、D(24°44.0′N,118°52.0′E)，水深11-14米。船舶进出港需向泉州VTS中心报告，航道内禁止追越。"
      },
      {
        "knowledge_id": 1757,
        "knowledge_text": "漳州港招银港区航道。招银港区航道自厦门湾南侧（24°25.0′N,118°05.0′E）至招银码头（24°28.0′N,118°02.0′E），全长约6海里，航道宽度180米，水深-12米。航道两侧设有浮灯，航道内设有2处转向点。该水域船舶交通密集，船舶应遵守《厦门水域船舶定线制》，向厦门VTS中心报告。"
      },
      {
        "knowledge_id": 1758,
        "knowledge_text": "汕头港珠池港区航道及警戒区。珠池港区航道自鹿屿附近（23°20.0′N,116°45.0′E）至珠池码头（23°22.0′N,116°43.0′E），全长约5海里，航道宽度150米，水深-10米。港区警戒区位于航道入口，以点(23°20.0′N,116°45.0′E)为中心、半径0.4海里。船舶进入警戒区前应向汕头VTS中心报告（VHF08频道），航道内限速8节。"
      },
      {
        "knowledge_id": 1759,
        "knowledge_text": "惠州港荃湾港区航道及锚地。荃湾港区航道自大亚湾口（22°38.0′N,114°38.0′E）至荃湾码头（22°42.0′N,114°35.0′E），全长约8海里，航道宽度200米，水深-14米。港区锚地位于航道南侧，范围为：A(22°40.0′N,114°36.0′E)、B(22°40.0′N,114°39.0′E)、C(22°38.0′N,114°39.0′E)、D(22°38.0′N,114°36.0′E)，水深12-15米。船舶进出港需向惠州VTS中心报告，大型船舶需引航。"
      },
      {
        "knowledge_id": 1760,
        "knowledge_text": "深圳港盐田港区航道及警戒区。盐田港区航道自大鹏湾口（22°32.0′N,114°25.0′E）至盐田码头（22°35.0′N,114°15.0′E），全长约12海里，航道宽度300米，水深-16米。港区警戒区位于航道入口，以点(22°32.0′N,114°25.0′E)为中心、半径0.5海里。船舶进入警戒区前应向盐田VTS中心报告（VHF14频道），航道内实行分道通航，禁止锚泊。"
      },
      {
        "knowledge_id": 1761,
        "knowledge_text": "行政区划代码（area_id）为6位数字编码。前2位代表省级行政区，前4位代表地市级行政区，6位全码代表区县级行政区。统计省份时使用 LEFT(area_id,2) 分组，统计城市时使用 LEFT(area_id,4) 分组，统计区县时使用 area_id 全码分组。省份名称可通过 administrative_division 表中 level=1 的记录获取，城市名称可通过 level=2 的记录获取。"
      },
      {
        "knowledge_id": 1762,
        "knowledge_text": "车辆载重分段规则（中国公路运输标准）：轻型车：载重 ≤ 5 吨；中型车：5 吨 < 载重 ≤ 15 吨；重型车：载重 > 15 吨。"
      },
      {
        "knowledge_id": 1763,
        "knowledge_text": "东北三省指：黑龙江省、吉林省、辽宁省。"
      },
      {
        "knowledge_id": 1764,
        "knowledge_text": "华东地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。"
      },
      {
        "knowledge_id": 1765,
        "knowledge_text": "货车同义词：卡车、载货汽车。危化品车同义词：危险品运输车、罐车（仅当运输危化品时）。客车同义词：巴士、大客车、小客车（座位数≥9）。"
      },
      {
        "knowledge_id": 1766,
        "knowledge_text": "计算某类别数量占总数的百分比公式：ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM 总表), 2)。"
      },
      {
        "knowledge_id": 1767,
        "knowledge_text": "“最近一年”指从当前日期往前推365天。MySQL中可用 DATE_SUB(CURDATE(), INTERVAL 1 YEAR)。"
      },
      {
        "knowledge_id": 1768,
        "knowledge_text": "A1驾照准驾大型客车；B2驾照准驾大型货车；A2准驾牵引车；C1驾照准驾小型汽车。货车包含A2和B2"
      },
      {
        "knowledge_id": 1769,
        "knowledge_text": "驾驶员状态“正常”表示驾照有效，可驾驶车辆；“暂扣”表示暂时失去驾驶资格；“吊销”表示永久取消资格；“过期”表示未及时换证。"
      },
      {
        "knowledge_id": 1770,
        "knowledge_text": "车辆注册年份提取函数：YEAR(register_date)。例如查询2023年注册的车辆：YEAR(register_date)=2023。"
      },
      {
        "knowledge_id": 1771,
        "knowledge_text": "危化品车辆必须配备押运员，且押运员需持有道路危险货物运输从业资格证。"
      },
      {
        "knowledge_id": 1772,
        "knowledge_text": "车辆保险到期日 insurance_expire 若小于当前日期，表示保险已过期。过保车辆不得上路。"
      },
      {
        "knowledge_id": 1773,
        "knowledge_text": "中国驾照有效期规则：初次领证有效期为6年，第二次换证为10年，第三次为长期。可通过 issue_date 和 valid_years 计算到期日。"
      },
      {
        "knowledge_id": 1774,
        "knowledge_text": "春运期间为农历腊月十六至正月廿五（约40天），查询时需转换为公历日期。例如2024年春运为1月26日至3月5日。"
      },
      {
        "knowledge_id": 1775,
        "knowledge_text": "黄牌车指载重≥4.5吨的货车，蓝牌车为载重＜4.5的货车。"
      },
      {
        "knowledge_id": 1776,
        "knowledge_text": "船舶最大载重 max_load 超过10000吨的称为“万吨轮”。"
      },
      {
        "knowledge_id": 1777,
        "knowledge_text": "船舶航速单位“节”等于海里/小时，1节≈1.852公里/小时。高速船舶通常指航速≥25节。"
      },
      {
        "knowledge_id": 1778,
        "knowledge_text": "长江三角洲地区（长三角）包括上海市、江苏省、浙江省、安徽省。"
      },
      {
        "knowledge_id": 1779,
        "knowledge_text": "珠江三角洲地区（珠三角）包括广东省广州、深圳、珠海、佛山、惠州、东莞、中山、江门、肇庆9市。"
      },
      {
        "knowledge_id": 1780,
        "knowledge_text": "京津冀地区包括北京市、天津市、河北省。"
      },
      {
        "knowledge_id": 1781,
        "knowledge_text": "新能源车辆指纯电动车、插电式混合动力车、燃料电池车。品牌名称中含有“电动”关键词时为新能源车辆。"
      },
      {
        "knowledge_id": 1782,
        "knowledge_text": "车辆使用年限超过15年的货车应当强制报废。当前年份减去 manufacture_year > 15。"
      },
      {
        "knowledge_id": 1783,
        "knowledge_text": "驾驶员年龄分组标准：30岁以下为青年驾驶员，30-45岁为中年驾驶员，45岁以上为老年驾驶员。。"
      },
      {
        "knowledge_id": 1784,
        "knowledge_text": "危险品运输车辆需每年进行一次罐体检测，检测合格标志存储在备注字段（若有）。"
      },
      {
        "knowledge_id": 1785,
        "knowledge_text": "“重型货车”通常指总质量≥12吨的货车，对应载重 load_capacity ≥ 12 吨。"
      },
      {
        "knowledge_id": 1786,
        "knowledge_text": "船舶自持力 endurance 表示船舶在不补充燃料、淡水、食物的情况下能够连续航行的天数或海里数。"
      },
      {
        "knowledge_id": 1787,
        "knowledge_text": "驾驶员从业资格类型：普通货运、危险品运输、旅客运输。不同类型对应不同的 license_type 和公司 business_type。"
      },
      {
        "knowledge_id": 1788,
        "knowledge_text": "节假日高速公路免费时段：春节、清明、劳动节、国庆节，共4个法定节假日，免费对象为7座及以下小型客车。"
      },
      {
        "knowledge_id": 1789,
        "knowledge_text": "“老旧车辆”指注册日期 register_date 超过10年的车辆（以当前日期计算）。"
      },
      {
        "knowledge_id": 1790,
        "knowledge_text": "船舶MMSI的前三位数字表示国家代码，中国为412、413、414。"
      },
      {
        "knowledge_id": 1791,
        "knowledge_text": "消防公司属于特种运输企业，其经营类型通常为'危化品运输'。在 vehicle_company 表中，消防公司通过 business_type='危化品运输' 进行筛选。"
      },
      {
        "knowledge_id": 1792,
        "knowledge_text": "驾驶员驾照领证年限分段标准：领证超过10年为长期驾龄，5至10年为中期驾龄，5年以下为新手驾龄。领证年限通过当前日期与issue_date的年份差计算。"
      },
      {
        "knowledge_id": 1793,
        "knowledge_text": "华南地区包括：广东省、广西壮族自治区、海南省。统计时使用 LEFT(area_id,2) IN ('44','45','46') 进行筛选。"
      },
      {
        "knowledge_id": 1794,
        "knowledge_text": "华北地区包括：北京市、天津市、河北省、山西省、内蒙古自治区。"
      },
      {
        "knowledge_id": 1795,
        "knowledge_text": "华中地区包括：河南省、湖北省、湖南省。"
      },
      {
        "knowledge_id": 1796,
        "knowledge_text": "西南地区包括：重庆市、四川省、贵州省、云南省、西藏自治区。"
      },
      {
        "knowledge_id": 1797,
        "knowledge_text": "西北地区包括：陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。"
      },
      {
        "knowledge_id": 1798,
        "knowledge_text": "低龄驾驶员一般指年龄<25岁的驾驶员。"
      },
      {
        "knowledge_id": 1799,
        "knowledge_text": "中国东部地区包括：上海市、江苏省、浙江省、安徽省、福建省、江西省、山东省。统计时使用 LEFT(area_id,2) IN ('31','32','33','34','35','36','37') 进行筛选。"
      },
      {
        "knowledge_id": 1800,
        "knowledge_text": "中国西部地区包括：重庆市、四川省、贵州省、云南省、西藏自治区、陕西省、甘肃省、青海省、宁夏回族自治区、新疆维吾尔自治区。统计时使用 LEFT(area_id,2) IN ('50','51','52','53','54','61','62','63','64','65') 进行筛选。"
      }
    ]
  }
}
</REFERENCE_INPUT_JSON>

END_OF_REFERENCE_INPUT_TABLE_KNOWLEDGE_V2
