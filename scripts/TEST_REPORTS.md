# 本地测试报告

使用项目指定的 Conda 环境运行完整单元测试：

```powershell
D:\miniconda3\envs\paper_agent\python.exe scripts\run_tests_with_report.py
```

可以直接附加 pytest 参数，也支持使用 `--` 分隔：

```powershell
D:\miniconda3\envs\paper_agent\python.exe scripts\run_tests_with_report.py -k query_plan -q
```

每次运行都会在 `outputs/test_reports/` 下生成以下文件。这些运行产物已被 Git 忽略：

- `latest_test_results.json`：生成 Excel 报告所使用的标准化数据源。
- `latest_test_details.csv`：可以直接使用 Excel 打开的测试明细表。
- `latest_junit.xml`：供 CI 系统使用的标准 JUnit 报告。
- `test_history.csv`：每次本地运行占一行，用于分析测试趋势。
- 带时间戳的 JSON、CSV 和 JUnit 快照：用于保留可审计的历史结果。

## 测试用例说明

每个测试函数都必须在 `scripts/test_case_catalog.py` 中登记以下内容：

- `purpose`：该测试验证什么能力或行为。
- `passed_meaning`：测试通过代表什么。
- `failed_meaning`：测试失败意味着什么风险或功能回归。

参数化测试共享函数级说明，但报告会分别列出每一个实际参数场景。

`tests/test_test_catalog.py` 会对比测试源码与说明目录。以下情况都会导致单元测试失败：

- 新增测试后没有登记说明；
- 删除测试后仍保留失效说明；
- 任意说明字段为空。

报告运行器还会检查本次实际执行的每个测试用例。只要存在未登记说明的用例，就会返回非零退出码。

## 报告指标定义

- `total`：pytest 输出的 `<testcase>` 记录数量。
- `passed`、`failed`、`error`、`skipped`：各标准化测试状态的数量。
- `pass_rate_pct`：`passed / total * 100`。
- `duration_seconds`：JUnit XML 中全部用例耗时之和。
- `pytest_exit_code`：pytest 进程的原始退出码。
- `description_missing_count`：缺少说明目录记录的已执行用例数量，该值必须保持为 0。

报告命令会保留 pytest 的原始退出码。因此即使成功保存了报告文件，只要存在失败测试，CI 仍会正确判定为失败。
