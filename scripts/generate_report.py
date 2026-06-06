"""Generate interview-ready SA-CCR portfolio reports."""

from __future__ import annotations

import argparse
from datetime import date
from html import escape
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SA-CCR portfolio reports.")
    parser.add_argument("--trades", default=ROOT / "data" / "sample_trades.csv")
    parser.add_argument("--outputs", default=ROOT / "outputs")
    parser.add_argument("--counterparties", default=ROOT / "data" / "counterparty_reference.csv")
    parser.add_argument("--report", default=ROOT / "docs" / "sa_ccr_portfolio_report.md")
    parser.add_argument("--html-report", default=ROOT / "docs" / "sa_ccr_portfolio_report.html")
    parser.add_argument("--title", default="SA-CCR Industry-Style Portfolio Capital Report")
    parser.add_argument("--data-date", default="2025-02-14")
    parser.add_argument("--data-source", default="Public-safe anonymized industry-style derivative portfolio")
    parser.add_argument(
        "--portfolio-description",
        default=(
            "The portfolio is a public-safe anonymized sample generated in this GitHub project from "
            "bank SA-CCR implementation field conventions and Basel-style product coverage. It preserves "
            "realistic product scope, margin fields, netting-set structure, and notional ranges, but does "
            "not copy client/project trade rows or original counterparty names."
        ),
    )
    parser.add_argument("--trade-note", default="Generated industry-style trades")
    parser.add_argument("--workflow", choices=["industry-style", "dtcc"], default="industry-style")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    context = build_context(args)

    markdown_path = Path(args.report)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(build_markdown_report(context), encoding="utf-8")
    print(f"Wrote Markdown report to {markdown_path}")

    html_path = Path(args.html_report)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(build_html_report(context), encoding="utf-8")
    print(f"Wrote HTML report to {html_path}")


def build_context(args: argparse.Namespace) -> dict[str, object]:
    trades = pd.read_csv(args.trades)
    outputs = Path(args.outputs)
    exposure = pd.read_csv(outputs / "netting_set_exposure.csv")
    asset_summary = pd.read_csv(outputs / "asset_class_summary.csv")
    counterparty_summary = pd.read_csv(outputs / "counterparty_summary.csv")
    data_quality = pd.read_csv(outputs / "data_quality_issues.csv")
    counterparties = pd.read_csv(args.counterparties)

    totals = exposure[["AddOn Aggregate", "PFE", "RC", "EAD", "RWA"]].sum()
    ead_before_cap = exposure.get("EAD Before Cap", exposure["EAD"]).sum()
    ead_cap_reduction = ead_before_cap - exposure["EAD"].sum()
    cap_applied = int(exposure["EAD Cap Applied"].sum()) if "EAD Cap Applied" in exposure else 0
    margin_counts = trades["Margined/ Unmargined"].value_counts().to_dict()
    product_summary = build_product_summary(trades)
    asset_result = build_asset_result(asset_summary)
    counterparty_result = build_counterparty_result(counterparty_summary, counterparties)
    top_netting_sets = build_top_netting_sets(exposure)
    asset_cards = build_asset_cards(trades)

    return {
        "generated_on": date.today().isoformat(),
        "title": args.title,
        "data_date": args.data_date,
        "data_source": args.data_source,
        "portfolio_description": args.portfolio_description,
        "trade_note": args.trade_note,
        "workflow": args.workflow,
        "trades": trades,
        "exposure": exposure,
        "product_summary": product_summary,
        "asset_cards": asset_cards,
        "asset_result": asset_result,
        "counterparty_result": counterparty_result,
        "top_netting_sets": top_netting_sets,
        "totals": totals,
        "total_notional": trades["Base Notional"].sum(),
        "trade_count": len(trades),
        "counterparty_count": trades["Counterparty ID"].nunique(),
        "netting_set_count": exposure[["Counterparty ID", "Netting Set ID"]].drop_duplicates().shape[0],
        "margined_trades": int(margin_counts.get("M", 0)),
        "unmargined_trades": int(margin_counts.get("U", 0)),
        "cap_applied": cap_applied,
        "ead_before_cap": ead_before_cap,
        "ead_cap_reduction": ead_cap_reduction,
        "data_quality_count": len(data_quality),
    }


def build_markdown_report(context: dict[str, object]) -> str:
    totals = context["totals"]
    lines = [
        f"# {context['title']}",
        "",
        f"Generated on: {context['generated_on']}",
        "",
        "## 1. Executive Summary",
        "",
        "This report summarizes a Python-based SA-CCR portfolio capital engine built for counterparty credit risk analysis. "
        f"{context['portfolio_description']}",
        "",
        md_table(
            [
                ["Trade count", f"{context['trade_count']:,}"],
                ["Counterparties", f"{context['counterparty_count']:,}"],
                ["Netting sets", f"{context['netting_set_count']:,}"],
                ["Base notional", money(context["total_notional"])],
                ["Margined trades", f"{context['margined_trades']:,}"],
                ["Unmargined trades", f"{context['unmargined_trades']:,}"],
                ["Total EAD", money(totals["EAD"])],
                ["Total RWA", money(totals["RWA"])],
                ["Margined EAD caps applied", f"{context['cap_applied']:,} netting sets"],
                ["EAD reduction from cap", money(context["ead_cap_reduction"])],
                ["Data quality issues", f"{context['data_quality_count']:,}"],
            ],
            ["Metric", "Value"],
        ),
        "",
        "## 2. Product Coverage",
        "",
        md_table(context["product_summary"], ["Asset Class", "Product", "Trades", "Base Notional", "Margined", "Unmargined"]),
        "",
        "## 3. Calculation Methodology",
        "",
        "```text",
        "EAD = alpha * (RC + PFE)",
        "alpha = 1.4",
        "PFE = multiplier * AddOn_aggregate",
        "",
        "Unmargined RC = max(V - C, 0)",
        "Margined RC = max(V - C, TH + MTA - NICA, 0)",
        "```",
        "",
        "The engine enriches trades with hedging sets, supervisory factors, supervisory duration, option delta, maturity factor, effective notional, add-on aggregation, PFE multiplier, RC, EAD, RWA, and margined EAD cap logic.",
        "",
        "## 4. Final Results",
        "",
        md_table(
            [
                ["AddOn Aggregate", money(totals["AddOn Aggregate"])],
                ["PFE", money(totals["PFE"])],
                ["RC", money(totals["RC"])],
                ["EAD", money(totals["EAD"])],
                ["RWA", money(totals["RWA"])],
                ["EAD before margined cap", money(context["ead_before_cap"])],
                ["EAD reduction from cap", money(context["ead_cap_reduction"])],
            ],
            ["Measure", "Amount"],
        ),
        "",
        "### Add-On by Asset Class",
        "",
        md_table(context["asset_result"], ["Asset Class", "AddOn Exposure", "Share of AddOn"]),
        "",
        "### Counterparty Summary",
        "",
        md_table(context["counterparty_result"], ["Counterparty", "Type", "Rating", "AddOn", "PFE", "RC", "EAD", "RWA"]),
        "",
        "### Largest Netting Sets by EAD",
        "",
        md_table(context["top_netting_sets"], ["Counterparty", "Netting Set", "Margin", "AddOn", "PFE", "RC", "EAD", "RWA", "Cap Applied"]),
        "",
        "## 5. References",
        "",
        *reference_markdown_lines(context["workflow"]),
        "",
        "## 6. Reproducibility",
        "",
        "```bash",
        *workflow_commands(context["workflow"]),
        "```",
        "",
    ]
    return "\n".join(lines)


def reference_markdown_lines(workflow: object) -> list[str]:
    lines = [
        "- Basel Committee on Banking Supervision, [The standardised approach for measuring counterparty credit risk exposures](https://www.bis.org/publ/bcbs279.pdf).",
        "- BIS Basel Framework, [CRE52 - Standardised approach to counterparty credit risk](https://www.bis.org/basel_framework/chapter/CRE/52.htm).",
        "- China State Council / NFRA, [Commercial Bank Capital Management Measures](https://www.gov.cn/zhengce/202311/content_6913410.htm).",
    ]
    if workflow == "dtcc":
        lines.append("- DTCC, [Public Price Dissemination Dashboard](https://pddata.dtcc.com/ppd/info-center).")
    return lines


def build_html_report(context: dict[str, object]) -> str:
    totals = context["totals"]
    asset_rows = context["asset_result"]
    counterparty_rows = context["counterparty_result"]
    top_rows = context["top_netting_sets"]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(str(context['title']))}</title>
  <style>
    :root {{
      --ink: #162033;
      --muted: #5d6678;
      --line: #d9dee8;
      --paper: #ffffff;
      --soft: #f5f7fb;
      --blue: #2867b2;
      --teal: #0f8b8d;
      --green: #2d7d46;
      --amber: #b66b00;
      --red: #b33a3a;
      --purple: #6f4eb8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #eef2f7;
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }}
    .page {{
      max-width: 1180px;
      margin: 0 auto;
      background: var(--paper);
      min-height: 100vh;
    }}
    header {{
      padding: 34px 42px 24px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #ffffff 0%, #f7f9fd 100%);
    }}
    .eyebrow {{
      color: var(--teal);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    h1 {{
      margin: 0;
      font-size: 34px;
      line-height: 1.16;
      letter-spacing: 0;
    }}
    .subtitle {{
      margin: 12px 0 0;
      max-width: 900px;
      color: var(--muted);
      font-size: 15px;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 18px;
      color: var(--muted);
      font-size: 13px;
    }}
    main {{ padding: 28px 42px 42px; }}
    section {{ margin-top: 34px; }}
    section:first-child {{ margin-top: 0; }}
    h2 {{
      margin: 0 0 14px;
      font-size: 22px;
      letter-spacing: 0;
    }}
    h3 {{
      margin: 24px 0 10px;
      font-size: 16px;
      letter-spacing: 0;
    }}
    p {{ margin: 0 0 12px; color: var(--muted); }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 20px;
    }}
    .kpi {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 15px 16px;
      background: #fff;
      min-height: 96px;
    }}
    .kpi span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 7px;
    }}
    .kpi strong {{
      display: block;
      font-size: 23px;
      line-height: 1.2;
    }}
    .kpi small {{
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      background: #fff;
      margin-top: 14px;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 16px;
    }}
    .asset-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }}
    .asset-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: var(--soft);
    }}
    .asset-card strong {{ display: block; font-size: 15px; }}
    .asset-card span {{ display: block; color: var(--muted); font-size: 12px; margin-top: 4px; }}
    .formula {{
      background: #101828;
      color: #f2f4f7;
      border-radius: 8px;
      padding: 16px;
      font-family: Consolas, Monaco, monospace;
      font-size: 13px;
      overflow-x: auto;
      white-space: pre;
    }}
    .flow {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .step {{
      border-left: 4px solid var(--blue);
      background: var(--soft);
      padding: 12px;
      border-radius: 6px;
      min-height: 94px;
    }}
    .step strong {{ display: block; font-size: 13px; margin-bottom: 5px; }}
    .step span {{ color: var(--muted); font-size: 12px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      margin-top: 12px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--soft);
      color: #344054;
      font-size: 12px;
    }}
    .table-wrap {{ overflow-x: auto; }}
    .chart {{
      display: grid;
      gap: 11px;
      margin-top: 14px;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: 190px minmax(180px, 1fr) 100px;
      gap: 12px;
      align-items: center;
      font-size: 13px;
    }}
    .bar-label {{ font-weight: 700; }}
    .bar-track {{
      height: 12px;
      background: #e7ebf2;
      border-radius: 999px;
      overflow: hidden;
    }}
    .bar {{
      height: 100%;
      border-radius: 999px;
    }}
    .bar-0 {{ background: var(--teal); }}
    .bar-1 {{ background: var(--blue); }}
    .bar-2 {{ background: var(--amber); }}
    .bar-3 {{ background: var(--green); }}
    .bar-4 {{ background: var(--purple); }}
    .badge {{
      display: inline-block;
      min-width: 42px;
      text-align: center;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 700;
    }}
    .badge-yes {{ background: #fde8e8; color: var(--red); }}
    .badge-no {{ background: #e7f5ec; color: var(--green); }}
    .callout {{
      border: 1px solid #cfe6e7;
      background: #f0fbfb;
      border-radius: 8px;
      padding: 16px;
      margin-top: 14px;
    }}
    ul {{ margin: 8px 0 0; padding-left: 20px; color: var(--muted); }}
    li {{ margin-bottom: 7px; }}
    a {{ color: var(--blue); }}
    footer {{
      border-top: 1px solid var(--line);
      padding: 20px 42px 34px;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 900px) {{
      header, main, footer {{ padding-left: 22px; padding-right: 22px; }}
      .kpi-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .two-col, .flow {{ grid-template-columns: 1fr; }}
      .asset-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .bar-row {{ grid-template-columns: 1fr; gap: 5px; }}
    }}
    @media print {{
      body {{ background: #fff; }}
      .page {{ max-width: none; }}
      section {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header>
      <div class="eyebrow">Counterparty Credit Risk Portfolio Deliverable</div>
      <h1>{escape(str(context['title']))}</h1>
      <p class="subtitle">A concentrated delivery report covering product scope, calculation methodology, final EAD/RWA results, key drivers, assumptions, and reproducibility for the Python SA-CCR engine.</p>
      <div class="meta">
        <span>Generated: {escape(str(context['generated_on']))}</span>
        <span>Data date: {escape(str(context['data_date']))}</span>
        <span>Dataset: {escape(str(context['data_source']))}</span>
      </div>
    </header>

    <main>
      <section>
        <h2>Executive Snapshot</h2>
        <p>{escape(str(context['portfolio_description']))}</p>
        <div class="kpi-grid">
          {kpi_card("Trades", f"{context['trade_count']:,}", str(context["trade_note"]))}
          {kpi_card("Base Notional", money(context["total_notional"]), "USD converted reproducibility basis")}
          {kpi_card("Netting Sets", f"{context['netting_set_count']:,}", f"{context['counterparty_count']:,} counterparties")}
          {kpi_card("Total EAD", money(totals["EAD"]), f"Before cap: {money(context['ead_before_cap'])}")}
          {kpi_card("Total RWA", money(totals["RWA"]), "Illustrative risk weights")}
          {kpi_card("AddOn Aggregate", money(totals["AddOn Aggregate"]), "Sum across netting sets")}
          {kpi_card("RC / PFE", f"{money(totals['RC'])} / {money(totals['PFE'])}", "Replacement cost and potential future exposure")}
          {kpi_card("Caps Applied", f"{context['cap_applied']:,}", f"EAD reduction: {money(context['ead_cap_reduction'])}")}
        </div>
      </section>

      <section>
        <h2>Product Coverage</h2>
        <p>The sample is designed to demonstrate the five SA-CCR asset classes and several distinct product treatments, including maturity-bucket aggregation, FX currency-pair aggregation, credit/equity entity correlation, and commodity group/type aggregation.</p>
        <div class="asset-grid">
          {asset_cards_html(context["asset_cards"])}
        </div>
        <div class="table-wrap">
          {html_table(context["product_summary"], ["Asset Class", "Product", "Trades", "Base Notional", "Margined", "Unmargined"])}
        </div>
      </section>

      <section>
        <h2>Calculation Methodology</h2>
        <div class="two-col">
          <div class="panel">
            <h3>Core SA-CCR Formula</h3>
            <div class="formula">EAD = alpha * (RC + PFE)
alpha = 1.4
PFE = multiplier * AddOn_aggregate

Unmargined RC = max(V - C, 0)
Margined RC = max(V - C, TH + MTA - NICA, 0)</div>
          </div>
          <div class="panel">
            <h3>Data Separation</h3>
            <p>The sample generator creates product economics such as asset class, notional, currency, dates, cleared flag, product identifiers, underlier information, and option terms.</p>
            <p>Internal bank concepts are synthetic and reproducible: counterparty, legal netting set, CSA terms, collateral, MtM, direction, and risk weight.</p>
          </div>
        </div>
        <div class="flow">
          {step_card("1", "Data validation", "Check required fields, parse dates, and remove expired trades.")}
          {step_card("2", "Trade enrichment", "Assign asset class, product type, hedging set, supervisory factor, option volatility, and maturity bucket.")}
          {step_card("3", "Adjusted notional", "Use supervisory duration for interest rate and credit trades; use converted notional or base notional for other products.")}
          {step_card("4", "Delta and maturity factor", "Apply option delta where option fields exist; use MPOR for margined trades and remaining maturity for unmargined trades.")}
          {step_card("5", "Add-on aggregation", "Aggregate by IR maturity bucket, FX pair, credit/equity entity, and commodity group/type.")}
          {step_card("6", "Exposure and capital", "Calculate multiplier, PFE, RC, EAD, illustrative RWA, and margined netting-set EAD cap.")}
        </div>
      </section>

      <section>
        <h2>Final Results</h2>
        <div class="two-col">
          <div class="panel">
            <h3>Portfolio Totals</h3>
            {html_table([
                ["AddOn Aggregate", money(totals["AddOn Aggregate"])],
                ["PFE", money(totals["PFE"])],
                ["RC", money(totals["RC"])],
                ["EAD", money(totals["EAD"])],
                ["RWA", money(totals["RWA"])],
                ["EAD before margined cap", money(context["ead_before_cap"])],
                ["EAD reduction from cap", money(context["ead_cap_reduction"])],
            ], ["Measure", "Amount"])}
          </div>
          <div class="panel">
            <h3>What Drives the Result</h3>
            <ul>
              <li>Commodity, interest rate, and FX are the largest add-on drivers in this portfolio.</li>
              <li>RC is concentrated in counterparties with positive net MtM after collateral and margin mechanics.</li>
              <li>The margined EAD cap reduces total EAD by {money(context["ead_cap_reduction"])} across {context["cap_applied"]:,} netting sets.</li>
              <li>RWA depends on illustrative counterparty risk weights and is not a jurisdiction-specific capital filing.</li>
            </ul>
          </div>
        </div>

        <h3>Add-On by Asset Class</h3>
        {bar_chart(asset_rows, amount_index=1, pct_index=2)}

        <h3>Counterparty RWA Ranking</h3>
        {bar_chart(counterparty_rows, label_index=0, amount_index=7)}

        <h3>Counterparty Summary</h3>
        <div class="table-wrap">
          {html_table(counterparty_rows, ["Counterparty", "Type", "Rating", "AddOn", "PFE", "RC", "EAD", "RWA"])}
        </div>

        <h3>Largest Netting Sets by EAD</h3>
        <div class="table-wrap">
          {html_table_with_cap_badges(top_rows, ["Counterparty", "Netting Set", "Margin", "AddOn", "PFE", "RC", "EAD", "RWA", "Cap Applied"])}
        </div>
      </section>

      <section>
        <h2>Assumptions, Controls, and Limitations</h2>
        <div class="two-col">
          <div class="panel">
            <h3>Implemented Controls</h3>
            <ul>
              <li>Data-quality check file is generated for every run.</li>
              <li>Trade-level enrichment is exported for review and audit tracing.</li>
              <li>Netting-set exposure output includes RC formula, EAD before cap, unmargined EAD cap, and cap-applied flag.</li>
              <li>Unit tests cover RC floor, margined RC formula, PFE multiplier floor, basis factor adjustment, and pipeline execution.</li>
            </ul>
          </div>
          <div class="panel">
            <h3>Remaining Production Gaps</h3>
            <ul>
              <li>Legal netting enforceability and CSA eligibility are not modeled.</li>
              <li>Collateral haircuts and full initial/variation margin operations are simplified.</li>
              <li>Risk weights are illustrative rather than generated from a regulatory credit risk engine.</li>
              <li>Market data conversion uses a static table for reproducibility.</li>
            </ul>
          </div>
        </div>
        <div class="callout">
          <strong>Interview positioning:</strong> this is best described as a Basel-aligned educational SA-CCR capital engine using a generated public-safe industry-style portfolio. It demonstrates product classification, trade enrichment, exposure aggregation, capital logic, controls, and limitations.
        </div>
      </section>

      <section>
        <h2>References and Reproducibility</h2>
        <p>Primary regulatory references and reproducibility commands:</p>
        {references_html(context["workflow"])}
        <div class="formula">{escape(chr(10).join(workflow_commands(context["workflow"])))}</div>
      </section>
    </main>
    <footer>
      SA-CCR portfolio report generated from repository outputs. Educational/interview portfolio implementation, not a production regulatory capital engine.
    </footer>
  </div>
</body>
</html>"""


def references_html(workflow: object) -> str:
    references = [
        ("https://www.bis.org/publ/bcbs279.pdf", "Basel Committee: The standardised approach for measuring counterparty credit risk exposures"),
        ("https://www.bis.org/basel_framework/chapter/CRE/52.htm", "BIS Basel Framework CRE52: Standardised approach to counterparty credit risk"),
        ("https://www.gov.cn/zhengce/202311/content_6913410.htm", "China State Council / NFRA: Commercial Bank Capital Management Measures"),
    ]
    if workflow == "dtcc":
        references.append(("https://pddata.dtcc.com/ppd/info-center", "DTCC Public Price Dissemination Dashboard"))
    items = "".join(
        f'<li><a href="{escape(url)}">{escape(label)}</a></li>' for url, label in references
    )
    return f"<ul>{items}</ul>"


def build_product_summary(trades: pd.DataFrame) -> list[list[str]]:
    grouped = (
        trades.groupby(["Asset Class", "Trade Type"], as_index=False)
        .agg(
            Trades=("Ticket Number", "count"),
            Base_Notional=("Base Notional", "sum"),
            Margined=("Margined/ Unmargined", lambda values: int((values == "M").sum())),
            Unmargined=("Margined/ Unmargined", lambda values: int((values == "U").sum())),
        )
        .sort_values(["Asset Class", "Trade Type"])
    )
    return [
        [
            row["Asset Class"],
            row["Trade Type"],
            f"{int(row['Trades']):,}",
            money(row["Base_Notional"]),
            f"{int(row['Margined']):,}",
            f"{int(row['Unmargined']):,}",
        ]
        for _, row in grouped.iterrows()
    ]


def build_asset_cards(trades: pd.DataFrame) -> list[list[str]]:
    grouped = (
        trades.groupby("Asset Class", as_index=False)
        .agg(
            Trades=("Ticket Number", "count"),
            Products=("Trade Type", "nunique"),
            Base_Notional=("Base Notional", "sum"),
        )
        .sort_values("Asset Class")
    )
    return [
        [
            row["Asset Class"],
            f"{int(row['Trades']):,} trades",
            f"{int(row['Products']):,} products",
            money(row["Base_Notional"]),
        ]
        for _, row in grouped.iterrows()
    ]


def build_asset_result(asset_summary: pd.DataFrame) -> list[list[str]]:
    total = asset_summary["AddOn Exposure"].sum()
    rows = asset_summary.sort_values("AddOn Exposure", ascending=False)
    return [
        [
            row["Asset Class"],
            money(row["AddOn Exposure"]),
            pct(row["AddOn Exposure"] / total if total else 0.0),
        ]
        for _, row in rows.iterrows()
    ]


def build_counterparty_result(
    counterparty_summary: pd.DataFrame, counterparties: pd.DataFrame
) -> list[list[str]]:
    rows = counterparty_summary.merge(counterparties, on="Counterparty ID", how="left")
    rows = rows.sort_values("RWA", ascending=False)
    return [
        [
            row["Counterparty ID"],
            safe_text(row.get("Counterparty Type")),
            safe_text(row.get("Credit Rating")),
            money(row["AddOn Aggregate"]),
            money(row["PFE"]),
            money(row["RC"]),
            money(row["EAD"]),
            money(row["RWA"]),
        ]
        for _, row in rows.iterrows()
    ]


def build_top_netting_sets(exposure: pd.DataFrame, limit: int = 10) -> list[list[str]]:
    rows = exposure.sort_values("EAD", ascending=False).head(limit)
    return [
        [
            row["Counterparty ID"],
            str(int(row["Netting Set ID"])),
            safe_text(row.get("Margin Agreement")),
            money(row["AddOn Aggregate"]),
            money(row["PFE"]),
            money(row["RC"]),
            money(row["EAD"]),
            money(row["RWA"]),
            "Yes" if bool(row.get("EAD Cap Applied", False)) else "No",
        ]
        for _, row in rows.iterrows()
    ]


def kpi_card(label: str, value: str, note: str) -> str:
    return f'<article class="kpi"><span>{escape(label)}</span><strong>{escape(value)}</strong><small>{escape(note)}</small></article>'


def step_card(number: str, title: str, body: str) -> str:
    return f'<div class="step"><strong>{escape(number)}. {escape(title)}</strong><span>{escape(body)}</span></div>'


def asset_cards_html(rows: list[list[str]]) -> str:
    cards = []
    for row in rows:
        cards.append(
            '<div class="asset-card">'
            f'<strong>{escape(row[0])}</strong>'
            f'<span>{escape(row[1])}</span>'
            f'<span>{escape(row[2])}</span>'
            f'<span>{escape(row[3])}</span>'
            '</div>'
        )
    return "\n".join(cards)


def bar_chart(
    rows: list[list[str]],
    label_index: int = 0,
    amount_index: int = 1,
    pct_index: int | None = None,
) -> str:
    values = [money_to_float(row[amount_index]) for row in rows]
    max_value = max(values) if values else 1.0
    chart_rows = []
    for index, row in enumerate(rows):
        value = values[index]
        width = 0.0 if max_value == 0 else max((value / max_value) * 100, 2.0)
        amount = row[amount_index]
        extra = f" ({row[pct_index]})" if pct_index is not None else ""
        chart_rows.append(
            '<div class="bar-row">'
            f'<div class="bar-label">{escape(row[label_index])}</div>'
            f'<div class="bar-track"><div class="bar bar-{index % 5}" style="width: {width:.1f}%"></div></div>'
            f'<div>{escape(amount + extra)}</div>'
            '</div>'
        )
    return f'<div class="chart">{"".join(chart_rows)}</div>'


def html_table(rows: list[list[str]], headers: list[str]) -> str:
    thead = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{escape(str(cell))}</td>" for cell in row)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def html_table_with_cap_badges(rows: list[list[str]], headers: list[str]) -> str:
    thead = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = []
        for index, cell in enumerate(row):
            if index == len(row) - 1:
                css = "badge-yes" if cell == "Yes" else "badge-no"
                cells.append(f'<td><span class="badge {css}">{escape(cell)}</span></td>')
            else:
                cells.append(f"<td>{escape(str(cell))}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def workflow_commands(workflow: object) -> list[str]:
    if workflow == "industry-style":
        return [
            "python scripts/build_industry_style_sample.py",
            "python scripts/run_saccr.py",
            "python scripts/generate_report.py",
            "pytest",
        ]
    return [
        "python scripts/download_dtcc_sdr.py --date 2025-02-14",
        "python scripts/build_saccr_sample_from_sdr.py",
        "python scripts/run_saccr.py",
        "python scripts/generate_report.py",
        "pytest",
    ]


def md_table(rows: list[list[str]], headers: list[str]) -> str:
    clean_rows = [[str(cell) for cell in row] for row in rows]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in clean_rows))
        for index in range(len(headers))
    ]
    header = "| " + " | ".join(headers[index].ljust(widths[index]) for index in range(len(headers))) + " |"
    separator = "| " + " | ".join("-" * widths[index] for index in range(len(headers))) + " |"
    body = [
        "| " + " | ".join(row[index].ljust(widths[index]) for index in range(len(headers))) + " |"
        for row in clean_rows
    ]
    return "\n".join([header, separator, *body])


def money(value: float) -> str:
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}bn"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}mm"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.2f}k"
    return f"${value:,.2f}"


def money_to_float(value: str) -> float:
    cleaned = value.replace("$", "").replace(",", "")
    if cleaned.endswith("bn"):
        return float(cleaned[:-2]) * 1_000_000_000
    if cleaned.endswith("mm"):
        return float(cleaned[:-2]) * 1_000_000
    if cleaned.endswith("k"):
        return float(cleaned[:-1]) * 1_000
    return float(cleaned)


def pct(value: float) -> str:
    return f"{value * 100:,.1f}%"


def safe_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


if __name__ == "__main__":
    main()
