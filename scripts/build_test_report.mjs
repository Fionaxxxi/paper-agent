import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const inputPath = process.argv[2];
const outputPath = process.argv[3];
const previewDir = process.argv[4];

if (!inputPath || !outputPath) {
  throw new Error(
    "Usage: node scripts/build_test_report.mjs <input.json> <output.xlsx> [preview-dir]",
  );
}

const report = JSON.parse(await fs.readFile(inputPath, "utf8"));
const tests = report.tests ?? [];
const history = report.history ?? [];
const summary = report.summary ?? {};
const workbook = Workbook.create();

const COLORS = {
  navy: "#17365D",
  blue: "#D9EAF7",
  lightBlue: "#EEF5FB",
  green: "#E2F0D9",
  greenText: "#375623",
  red: "#FCE4D6",
  redText: "#9C0006",
  amber: "#FFF2CC",
  amberText: "#7F6000",
  gray: "#E7E6E6",
  darkGray: "#595959",
  white: "#FFFFFF",
  border: "#B4C6E7",
};

const statusText = {
  passed: "通过",
  failed: "失败",
  error: "错误",
  skipped: "跳过",
};

function titleBand(sheet, range, text) {
  sheet.getRange(range).merge();
  sheet.getRange(range.split(":")[0]).values = [[text]];
  sheet.getRange(range).format = {
    fill: COLORS.navy,
    font: { bold: true, color: COLORS.white, size: 16 },
    verticalAlignment: "center",
  };
  sheet.getRange(range).format.rowHeight = 30;
}

function styleHeader(range) {
  range.format = {
    fill: COLORS.navy,
    font: { bold: true, color: COLORS.white },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "inside", style: "thin", color: COLORS.border },
  };
}

function styleBody(range) {
  range.format = {
    verticalAlignment: "center",
    borders: {
      insideHorizontal: { style: "thin", color: "#D9E2F3" },
    },
  };
}

function addStatusFormatting(range) {
  range.conditionalFormats.add("containsText", {
    text: "通过",
    format: { fill: COLORS.green, font: { color: COLORS.greenText, bold: true } },
  });
  range.conditionalFormats.add("containsText", {
    text: "失败",
    format: { fill: COLORS.red, font: { color: COLORS.redText, bold: true } },
  });
  range.conditionalFormats.add("containsText", {
    text: "错误",
    format: { fill: COLORS.red, font: { color: COLORS.redText, bold: true } },
  });
  range.conditionalFormats.add("containsText", {
    text: "跳过",
    format: { fill: COLORS.amber, font: { color: COLORS.amberText, bold: true } },
  });
}

function excelSerialFromIsoWallClock(value) {
  const match = String(value).match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/,
  );
  if (!match) {
    return value;
  }
  const [, year, month, day, hour, minute, second] = match.map(Number);
  return (
    Date.UTC(year, month - 1, day, hour, minute, second) / 86_400_000 +
    25_569
  );
}

const overview = workbook.worksheets.add("测试总览");
const details = workbook.worksheets.add("测试明细");
const explanations = workbook.worksheets.add("用例说明");
const failures = workbook.worksheets.add("失败明细");
const trends = workbook.worksheets.add("历史趋势");

for (const sheet of [overview, details, explanations, failures, trends]) {
  sheet.showGridLines = false;
}

// 测试明细是其他工作表的唯一事实来源。
titleBand(details, "A1:H1", "PaperAgent 本地单元测试明细");
details.getRange("A2:H2").merge();
details.getRange("A2").values = [[
  `运行时间：${report.run_at}  |  Git：${report.git_commit}`,
]];
details.getRange("A2:H2").format = {
  fill: COLORS.lightBlue,
  font: { color: COLORS.darkGray },
};
details.getRange("A4:H4").values = [[
  "序号",
  "测试文件",
  "测试用例",
  "参数场景",
  "状态",
  "耗时（秒）",
  "测试作用",
  "消息",
]];
styleHeader(details.getRange("A4:H4"));

if (tests.length) {
  details.getRangeByIndexes(4, 0, tests.length, 8).values = tests.map((test, index) => [
    index + 1,
    test.test_file ?? "",
    test.test_name ?? "",
    test.scenario ?? "默认场景",
    statusText[test.status] ?? test.status,
    Number(test.duration_seconds ?? 0),
    test.purpose ?? "未登记测试作用",
    test.message ?? "",
  ]);
  const endRow = tests.length + 4;
  styleBody(details.getRange(`A5:H${endRow}`));
  details.getRange(`A5:A${endRow}`).format.horizontalAlignment = "center";
  details.getRange(`E5:E${endRow}`).format.horizontalAlignment = "center";
  details.getRange(`F5:F${endRow}`).format.numberFormat = "0.000";
  details.getRange(`F5:F${endRow}`).format.horizontalAlignment = "right";
  details.getRange(`B5:D${endRow}`).format.wrapText = true;
  details.getRange(`G5:H${endRow}`).format.wrapText = true;
  details.getRange(`A5:H${endRow}`).format.autofitRows();
  addStatusFormatting(details.getRange(`E5:E${endRow}`));
  details.tables.add(`A4:H${endRow}`, true, "TestDetailsTable").style = "TableStyleMedium2";
}
details.freezePanes.freezeRows(4);
details.getRange("A:A").format.columnWidth = 7;
details.getRange("B:B").format.columnWidth = 25;
details.getRange("C:C").format.columnWidth = 48;
details.getRange("D:D").format.columnWidth = 24;
details.getRange("E:E").format.columnWidth = 10;
details.getRange("F:F").format.columnWidth = 13;
details.getRange("G:G").format.columnWidth = 56;
details.getRange("H:H").format.columnWidth = 32;

// 用例说明逐条解释每个实际执行场景及结果含义。
titleBand(explanations, "A1:J1", "测试用例作用与结果含义");
explanations.getRange("A2:J2").merge();
explanations.getRange("A2").values = [[
  "新增测试必须先在 scripts/test_case_catalog.py 登记；缺少登记会导致测试失败。",
]];
explanations.getRange("A2:J2").format = {
  fill: COLORS.amber,
  font: { bold: true, color: COLORS.amberText },
};
explanations.getRange("A4:J4").values = [[
  "序号",
  "测试文件",
  "测试用例",
  "参数场景",
  "测试作用",
  "通过代表",
  "失败代表",
  "本次结果",
  "耗时（秒）",
  "说明登记",
]];
styleHeader(explanations.getRange("A4:J4"));
if (tests.length) {
  explanations.getRangeByIndexes(4, 0, tests.length, 10).values = tests.map(
    (test, index) => [
      index + 1,
      test.test_file ?? "",
      test.test_name ?? "",
      test.scenario ?? "默认场景",
      test.purpose ?? "未登记测试作用",
      test.passed_meaning ?? "未登记通过含义",
      test.failed_meaning ?? "未登记失败含义",
      statusText[test.status] ?? test.status,
      Number(test.duration_seconds ?? 0),
      test.description_registered ? "已登记" : "未登记",
    ],
  );
  const explanationEndRow = tests.length + 4;
  styleBody(explanations.getRange(`A5:J${explanationEndRow}`));
  explanations.getRange(`A5:A${explanationEndRow}`).format.horizontalAlignment =
    "center";
  explanations.getRange(`A5:J${explanationEndRow}`).format.borders = {
    insideHorizontal: { style: "thin", color: "#D9E2F3" },
    insideVertical: { style: "thin", color: "#EAF0F8" },
  };
  explanations.getRange(`B5:G${explanationEndRow}`).format.wrapText = true;
  explanations.getRange(`H5:H${explanationEndRow}`).format.horizontalAlignment =
    "center";
  explanations.getRange(`I5:I${explanationEndRow}`).format.numberFormat = "0.000";
  explanations.getRange(`J5:J${explanationEndRow}`).format.horizontalAlignment =
    "center";
  explanations.getRange(`A5:J${explanationEndRow}`).format.autofitRows();
  addStatusFormatting(explanations.getRange(`H5:H${explanationEndRow}`));
  explanations.getRange(`J5:J${explanationEndRow}`).conditionalFormats.add(
    "containsText",
    {
      text: "未登记",
      format: { fill: COLORS.red, font: { color: COLORS.redText, bold: true } },
    },
  );
  explanations.tables.add(
    `A4:J${explanationEndRow}`,
    true,
    "TestExplanationsTable",
  ).style = "TableStyleMedium2";
}
explanations.freezePanes.freezeRows(4);
explanations.getRange("A:A").format.columnWidth = 7;
explanations.getRange("B:B").format.columnWidth = 25;
explanations.getRange("C:C").format.columnWidth = 44;
explanations.getRange("D:D").format.columnWidth = 22;
explanations.getRange("E:G").format.columnWidth = 52;
explanations.getRange("H:H").format.columnWidth = 11;
explanations.getRange("I:I").format.columnWidth = 13;
explanations.getRange("J:J").format.columnWidth = 12;

// 总览通过公式引用明细，便于审计统计口径。
titleBand(overview, "A1:H1", "PaperAgent 本地单元测试报告");
overview.getRange("A2:H2").merge();
overview.getRange("A2").values = [[
  `运行时间：${report.run_at}  |  Git：${report.git_commit}`,
]];
overview.getRange("A2:H2").format = {
  fill: COLORS.lightBlue,
  font: { color: COLORS.darkGray },
};
overview.getRange("A4:H4").values = [[
  "测试总数", "", "通过", "", "失败/错误", "", "跳过", "",
]];
styleHeader(overview.getRange("A4:H4"));
overview.getRange("A4:B4").merge();
overview.getRange("C4:D4").merge();
overview.getRange("E4:F4").merge();
overview.getRange("G4:H4").merge();

const detailEndRow = Math.max(5, tests.length + 4);
overview.getRange("A5:B6").merge();
overview.getRange("C5:D6").merge();
overview.getRange("E5:F6").merge();
overview.getRange("G5:H6").merge();
overview.getRange("A5").formulas = [[
  `=COUNTA('测试明细'!$A$5:$A$${detailEndRow})`,
]];
overview.getRange("C5").formulas = [[
  `=COUNTIF('测试明细'!$E$5:$E$${detailEndRow},"通过")`,
]];
overview.getRange("E5").formulas = [[
  `=COUNTIF('测试明细'!$E$5:$E$${detailEndRow},"失败")+COUNTIF('测试明细'!$E$5:$E$${detailEndRow},"错误")`,
]];
overview.getRange("G5").formulas = [[
  `=COUNTIF('测试明细'!$E$5:$E$${detailEndRow},"跳过")`,
]];
overview.getRange("A5:H6").format = {
  fill: COLORS.white,
  font: { bold: true, size: 20, color: COLORS.navy },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: COLORS.border },
};

overview.getRange("A8:H8").values = [[
  "通过率", "", "用例总耗时（秒）", "", "pytest 退出码", "", "说明登记缺失", "",
]];
styleHeader(overview.getRange("A8:H8"));
overview.getRange("A8:B8").merge();
overview.getRange("C8:D8").merge();
overview.getRange("E8:F8").merge();
overview.getRange("G8:H8").merge();
overview.getRange("A9:B10").merge();
overview.getRange("C9:D10").merge();
overview.getRange("E9:F10").merge();
overview.getRange("G9:H10").merge();
overview.getRange("A9").formulas = [["=IF(A5=0,0,C5/A5)"]];
overview.getRange("C9").formulas = [[
  `=SUM('测试明细'!$F$5:$F$${detailEndRow})`,
]];
overview.getRange("E9").values = [[Number(summary.pytest_exit_code ?? 0)]];
const explanationEndRow = Math.max(5, tests.length + 4);
overview.getRange("G9").formulas = [[
  `=COUNTIF('用例说明'!$J$5:$J$${explanationEndRow},"未登记")`,
]];
overview.getRange("A9:B10").format.numberFormat = "0.0%";
overview.getRange("C9:D10").format.numberFormat = "0.000";
overview.getRange("A9:H10").format = {
  fill: COLORS.white,
  font: { bold: true, size: 16, color: COLORS.navy },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: COLORS.border },
};
overview.getRange("A9:B10").format.numberFormat = "0.0%";
overview.getRange("C9:D10").format.numberFormat = "0.000";

overview.getRange("A12:H12").merge();
overview.getRange("A12").values = [["指标计算口径"]];
overview.getRange("A12:H12").format = {
  fill: COLORS.blue,
  font: { bold: true, color: COLORS.navy },
};
overview.getRange("A13:H17").values = [
  ["测试总数", "JUnit XML 中 testcase 记录数", "", "", "", "", "", ""],
  ["通过/失败/错误/跳过", "按测试明细的状态列计数", "", "", "", "", "", ""],
  ["通过率", "通过数 ÷ 测试总数", "", "", "", "", "", ""],
  ["用例总耗时", "测试明细中所有用例耗时求和", "", "", "", "", "", ""],
  ["说明登记", "新增测试必须登记作用、通过含义和失败含义；缺失数必须为 0", "", "", "", "", "", ""],
];
for (let row = 13; row <= 17; row += 1) {
  overview.getRange(`B${row}:H${row}`).merge();
}
overview.getRange("A13:H17").format = {
  borders: { insideHorizontal: { style: "thin", color: "#D9E2F3" } },
  verticalAlignment: "center",
};
overview.getRange("A13:A17").format.font = { bold: true, color: COLORS.navy };
overview.getRange("B13:H17").format.wrapText = true;
overview.getRange("A:H").format.columnWidth = 14;
overview.getRange("B:B").format.columnWidth = 16;
overview.getRange("D:D").format.columnWidth = 16;
overview.getRange("F:F").format.columnWidth = 16;
overview.getRange("H:H").format.columnWidth = 16;

// 失败明细保留完整错误文本；无失败时显示明确状态。
titleBand(failures, "A1:F1", "失败与错误明细");
failures.getRange("A3:F3").values = [[
  "序号",
  "测试文件",
  "测试用例",
  "状态",
  "消息",
  "错误详情",
]];
styleHeader(failures.getRange("A3:F3"));
const failedTests = tests.filter((test) => ["failed", "error"].includes(test.status));
if (failedTests.length) {
  failures.getRangeByIndexes(3, 0, failedTests.length, 6).values = failedTests.map(
    (test, index) => [
      index + 1,
      test.test_file ?? "",
      test.test_name ?? "",
      statusText[test.status] ?? test.status,
      test.message ?? "",
      test.details ?? "",
    ],
  );
  const failureEndRow = failedTests.length + 3;
  styleBody(failures.getRange(`A4:F${failureEndRow}`));
  failures.getRange(`E4:F${failureEndRow}`).format.wrapText = true;
  addStatusFormatting(failures.getRange(`D4:D${failureEndRow}`));
} else {
  failures.getRange("A4:F5").merge();
  failures.getRange("A4").values = [["本次测试没有失败或错误。"]];
  failures.getRange("A4:F5").format = {
    fill: COLORS.green,
    font: { bold: true, color: COLORS.greenText },
    horizontalAlignment: "center",
    verticalAlignment: "center",
  };
}
failures.freezePanes.freezeRows(3);
failures.getRange("A:A").format.columnWidth = 7;
failures.getRange("B:B").format.columnWidth = 25;
failures.getRange("C:C").format.columnWidth = 42;
failures.getRange("D:D").format.columnWidth = 10;
failures.getRange("E:E").format.columnWidth = 32;
failures.getRange("F:F").format.columnWidth = 70;

// 历史趋势直接展示每次运行的数据，便于后续比较能力迭代的稳定性。
titleBand(trends, "A1:J1", "本地单元测试历史趋势");
trends.getRange("A3:J3").values = [[
  "运行时间",
  "Git Commit",
  "总数",
  "通过",
  "失败",
  "错误",
  "跳过",
  "通过率",
  "耗时（秒）",
  "退出码",
]];
styleHeader(trends.getRange("A3:J3"));
if (history.length) {
  trends.getRangeByIndexes(3, 0, history.length, 10).values = history.map((run) => [
    excelSerialFromIsoWallClock(run.run_at ?? ""),
    (run.git_commit ?? "").slice(0, 12),
    Number(run.total ?? 0),
    Number(run.passed ?? 0),
    Number(run.failed ?? 0),
    Number(run.errors ?? 0),
    Number(run.skipped ?? 0),
    Number(run.pass_rate_pct ?? 0) / 100,
    Number(run.duration_seconds ?? 0),
    Number(run.pytest_exit_code ?? 0),
  ]);
  const historyEndRow = history.length + 3;
  styleBody(trends.getRange(`A4:J${historyEndRow}`));
  trends.getRange(`A4:A${historyEndRow}`).format.numberFormat =
    "yyyy-mm-dd hh:mm:ss";
  trends.getRange(`H4:H${historyEndRow}`).format.numberFormat = "0.0%";
  trends.getRange(`I4:I${historyEndRow}`).format.numberFormat = "0.000";
  trends.tables.add(`A3:J${historyEndRow}`, true, "TestHistoryTable").style =
    "TableStyleMedium2";
}
trends.freezePanes.freezeRows(3);
trends.getRange("A:A").format.columnWidth = 27;
trends.getRange("B:B").format.columnWidth = 16;
trends.getRange("C:J").format.columnWidth = 12;

const keyInspection = await workbook.inspect({
  kind: "table",
  range: `测试总览!A1:H17`,
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 10,
  maxChars: 6000,
});
console.log(keyInspection.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(formulaErrors.ndjson);

if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const sheetName of [
    "测试总览",
    "测试明细",
    "用例说明",
    "失败明细",
    "历史趋势",
  ]) {
    const preview = await workbook.render({
      sheetName,
      autoCrop: "all",
      scale: 1,
      format: "png",
    });
    await fs.writeFile(
      path.join(previewDir, `${sheetName}.png`),
      new Uint8Array(await preview.arrayBuffer()),
    );
  }
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`Saved workbook: ${outputPath}`);
