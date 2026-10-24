# 🪙 GoldTrader: Production Quantitative EA Development Harness (MT4 & MT5)

[![MQL4](https://img.shields.io/badge/Platform-MetaTrader_4_(MQL4)-blue.svg)](https://www.mql4.com)
[![MQL5](https://img.shields.io/badge/Platform-MetaTrader_5_(MQL5)-green.svg)](https://www.mql5.com)
[![Harness](https://img.shields.io/badge/Harness-Deterministic_State_Machine-purple.svg)](docs/architecture/deterministic-harness.md)
[![Benchmark](https://img.shields.io/badge/Benchmark-12%2F12_Passed_(120%2F120)-brightgreen.svg)](#-การทดสอบ-ground-truth-benchmark-12-ข้อ)
[![Zero-Test](https://img.shields.io/badge/Policy-Zero--Test_by_Default-orange.svg)](docs/policies/unittest-policy.md)

ระบบ **Deterministic Multi-Agent Algorithmic Trading Harness** สำหรับการออกแบบ, พัฒนา, ตรวจสอบ (Audit), และเพิ่มประสิทธิภาพ Expert Advisors (EAs) บนคู่เงิน/สินทรัพย์ **XAUUSD (Gold)** รองรับทั้งแพลตฟอร์ม **MetaTrader 4 (MQL4)** และ **MetaTrader 5 (MQL5)** อย่างเต็มรูปแบบ

โปรเจกต์นี้ผสานรวม **Control Plane** แบบ Deterministic State Machine พร้อมคัดเลือกและปรับแต่งทักษะเชิงลึก (Skills) เฉพาะทางด้าน Quant Finance และปฏิบัติตาม **Production Harness Master Standards (8 Golden Pillars)** อย่างเคร่งครัด

---

## 🏛️ Production Harness Master Standards (8 เสาหลัก)

```mermaid
flowchart TD
    subgraph MasterStandards ["🏛️ Production Harness Master Standards (8 Golden Pillars)"]
        direction TB
        P1["<b>1. Visual & Diagram Protocol</b><br/>Strict ASCII Ban (+----+, |--|, ├──, └──, ---&gt;)<br/>Mermaid Unicode Guardian (flowchart TD/LR)<br/>Node ID = ASCII only, Labels = [#quot;...#quot;]"]
        P2["<b>2. Documentation & Export Protocol</b><br/>Native UTF-8 Markdown in ./output/<br/>LaTeX math preservation ($inline$, $$display$$)<br/>Local Path Ban: No C:, D:, or file://<br/>Clean File Gate: Never save PDF advice in files"]
        P3["<b>3. Grounding Oracle & Anti-Hallucination</b><br/>Zero tolerance for fake MQL functions or fake APIs<br/>Whitelist verification from Grounding Oracle"]
        P4["<b>4. Anti-Sycophancy & Objectivity Gate</b><br/>Never validate retail illusions or guarantee 100% win<br/>Reject dangerous naked Martingale without hard stops"]
        P5["<b>5. Emergency & Red Flag Interceptor</b><br/>Instant escalation on Margin Call &lt; 150% / &lt; 100%<br/>Daily Drawdown ≥ 5% circuit breaker"]
        P6["<b>6. Tier-0 Dual-Layer Cache & Resilience</b><br/>L1 LRU (&lt;0.2ms) + L2 SQLite WAL with zlib (&lt;2.0ms)<br/>Auto-init on first run in ./cache/"]
        P7["<b>7. Adaptive 3-Tier Persona Routing</b><br/>Tier 1: Quant / Senior Algo Trader (IRAC, Math)<br/>Tier 2: EA Developer (MQL4/MQL5 code patterns)<br/>Tier 3: Retail Trader (Plain language & risk warnings)"]
        P8["<b>8. Strict Token Optimization & Test Control</b><br/>Strict Zero-Test by Default (Opt-In Only)<br/>Traceback suppression flags (-q --tb=short)<br/>Hard auto-fix limit (Max 2 Attempts)"]
    end
```

---

## 📌 จุดเด่นสำคัญ (Key Capabilities)

- **Dual-Engine MQL4 & MQL5 Architecture**:
  - **MT4 (MQL4)**: รองรับ Order pool, Backwards order loops (`OrdersTotal() - 1 down to 0`), Slippage handling, Error 130/138/146 retry loops พร้อม `RefreshRates()`, Legacy indicator shifts, และการคำนวณ Pip บนราคาทอง 2/3 ทศนิยม
  - **MT5 (MQL5)**: รองรับ Modern Object-Oriented Programming (OOP) ผ่าน `<Trade\Trade.mqh>`, `CTrade`, `CPositionInfo`, `CSymbolInfo`, การจัดการบัฟเฟอร์ด้วย `CopyBuffer()` และ `ArraySetAsSeries()`, ตลอดจนการปล่อยหน่วยความจำใน `OnDeinit()` ด้วย `IndicatorRelease()`
- **⚙️ Deterministic State Machine (Control Plane)**:
  - แยก Control Plane ออกจาก Data Plane ควบคุม Flow การทำงานระหว่างทีมอย่างแม่นยำ ไม่พึ่งพาการเดาของ LLM
  - บันทึก Task Call-Stack ลง `stack.json` ด้วยระบบ Atomic File Writing
- **📊 MT5 Backtest Report Quantitative Analyzer & Visual Dashboard**:
  - ถอดรหัส Strategy Tester HTML Reports (UTF-16 LE) สกัดค่าสถิติ 25+ ค่า, รายละเอียดตาราง Deals, Initial Deposit, และค่าคอมมิชชัน
  - ตรวจจับความลำเอียงของทิศทาง (Directional Asymmetry: 100% Short vs 0% Long) และสัญญาณ Overfitting (Sharpe สูงผิดปกติ)
  - สร้าง **Interactive Visual HTML Dashboard** แบบ Standalone พล็อตเส้น Cumulative Equity Curve, Underwater Drawdown Area Chart, และ Hourly PnL Heatmap
- **📐 Walk-Forward Optimization (WFO) Matrix Calculator**:
  - ประเมินความทนทานต่อการ Overfitting ในระดับสถาบัน ด้วย **Walk-Forward Efficiency ($WFE \ge 60\%$)**, **Parameter Stability Robustness ($PSR \ge 0.70$)**, และ **Drawdown Consistency Ratio ($DCR$)**
- **⚡ Prompt on Demand Builder (JIT Context)**:
  - ประกอบ Prompt แบบ Just-In-Time โดยดึงเฉพาะ Persona + Top of Stack + Unified Git Diff + Allowed Files ป้องกันปัญหา Context Rot และ Token Bloat
- **🛡️ Built-in MQL Code Linter & Verification Gate**:
  - ตรวจสอบไวยากรณ์ (Syntax), การจับคู่ปีกกา `{}` / วงเล็บ `()`, และ **กฎเหล็กการใส่วงเล็บสำหรับตัวดำเนินการตรรกะ `((a && b) || c)`** อัตโนมัติ
  - ป้องกันการใช้ฟังก์ชันข้ามแพลตฟอร์ม (ห้ามใช้ `CTrade` ใน MT4, ห้ามใช้ `OrderSend` เก่าใน MT5)
- **⚡ Strict Token Optimization & Test Control (Zero-Test by Default)**:
  - ค่าเริ่มต้นทำงานในโหมด **Implementation-Only Mode** 100% มุ่งเน้นการสร้างโค้ดและสัญญา (Contract)
  - เข้าสู่ Testing Mode เฉพาะเมื่อผู้ใช้สั่งการอย่างชัดเจน (Opt-In Trigger) พร้อมจำกัดลูปแก้โค้ดสูงสุดไม่เกิน 2 ครั้ง (Max 2 Attempts)
- **🚀 Tier-0 Dual-Layer Caching Engine**:
  - L1 In-Memory LRU (`<0.2ms`) + L2 SQLite WAL with zlib compression (`<2.0ms`)
  - Auto-initialization อัตโนมัติใน `./cache/` ตั้งแต่การรันครั้งแรก
- **🚨 Emergency & Red Flag Interceptors**:
  - ตรวจจับความเสี่ยงวิกฤต: Margin Level $< 150\%$ / $< 100\%$, Daily Drawdown $\ge 5\%$, และ Spread Widening $> 40$ points บน XAUUSD
- **🚫 Strict Machine-Local Path Ban (Portability Protocol)**:
  - ห้ามอ้างอิงไดรฟ์เครื่องโลคัล (เช่น `C:`, `D:`) หรือ URI schemes (`file://`) ในการบันทึกเอกสารและรายงานลงใน `./output/` หรือ `docs/` โดยเด็ดขาด บังคับใช้ Repository-relative path (`./output/...`) หรือ Basename เท่านั้น เพื่อความยืดหยุ่นและรองรับ CI/CD & Docker ข้ามแพลตฟอร์ม

---

## 🔄 แผนภาพการทำงานร่วมกันของทีมพัฒนา (SDLC Flow)

```mermaid
flowchart TD
    User["👤 ผู้ใช้งาน / คำขอสร้าง EA"] --> PM["📋 strategy_pm<br/>Quantitative Strategy PRD & Rules"]
    PM --> Quant["📐 quant_architect<br/>Market Microstructure & Math Models"]
    Quant --> Branch{"เลือกแพลตฟอร์ม"}
    Branch -- "MetaTrader 4" --> MQL4["⚙️ mql4_developer<br/>OrderSend & Backwards Loops"]
    Branch -- "MetaTrader 5" --> MQL5["⚙️ mql5_developer<br/>CTrade & CopyBuffer OOP"]
    MQL4 --> Risk["🧪 risk_gatekeeper<br/>Deterministic Linter & Margin Gate"]
    MQL5 --> Risk
    Risk -- "❌ ส่งกลับแก้ไข" --> Branch
    Risk -- "✅ ผ่านเกณฑ์ (Exit Code 0)" --> Out["🚀 ส่งมอบ Production EA ใน ./experts/"]
```

---

## 👥 บทบาทและหน้าที่ภายในทีม (Team Roles)

| บทบาท (Role) | รหัส Agent | หน้าที่หลัก | ทักษะที่เกี่ยวข้อง (Skills) |
| :--- | :--- | :--- | :--- |
| **📋 Strategy Product Manager** | `strategy_pm` | แปลงโจทย์การเทรดเป็น Quantitative Strategy PRD, กำหนดเงื่อนไข Entry/Exit, ตัวกรองเวลา (Session Filter) | [trading-spec-driven](.agents/skills/trading-spec-driven/SKILL.md) |
| **📐 Quantitative Architect** | `quant_architect` | วิเคราะห์ Market Microstructure บน XAUUSD, คำนวณ Sharpe, Sortino, VaR, และ Expectancy ด้วยสูตร $\LaTeX$, วางผัง Walk-Forward Analysis | [quant-analyst](.agents/skills/quant-analyst/SKILL.md), [mt5-backtest-analyzer](.agents/skills/mt5-backtest-analyzer/SKILL.md), [backtest-architect](.agents/skills/backtest-architect/SKILL.md) |
| **⚙️ Senior MQL4 Developer** | `mql4_developer` | พัฒนา EA บน MT4, วนลูป Order ถอยหลัง, จัดการ Slippage, Requote, และ Error 130/138 Retry Loops | [mql4-ea-development](.agents/skills/mql4-ea-development/SKILL.md), [mql-clean-code-guard](.agents/skills/mql-clean-code-guard/SKILL.md) |
| **⚙️ Senior MQL5 Developer** | `mql5_developer` | พัฒนา EA บน MT5 แบบ OOP ด้วย `CTrade`, `CPositionInfo`, ดึงข้อมูลผ่าน `CopyBuffer`, จัดการทรัพยากรใน `OnDeinit()` | [mql5-ea-development](.agents/skills/mql5-ea-development/SKILL.md), [mql-clean-code-guard](.agents/skills/mql-clean-code-guard/SKILL.md) |
| **🧪 Risk Gatekeeper & QA** | `risk_gatekeeper` | ตรวจสอบโค้ดด้วย MQL Static Linter (Exit Code 0), บังคับใช้ Stop Loss, Dynamic Spread Check, คุมกฎ Zero-Test, ตรวจสอบรายงานผล Backtest | [risk-manager](.agents/skills/risk-manager/SKILL.md), [anti-hallucination](.agents/skills/anti-hallucination-guardian/SKILL.md), [mt5-backtest-analyzer](.agents/skills/mt5-backtest-analyzer/SKILL.md) |

---

## 💻 การใช้งาน Harness CLI (`harness/cli.py`)

คำสั่งสำหรับควบคุมและสั่งการระบบ Harness ครบวงจร:

```bash
# 1. เริ่มต้น Task พัฒนา EA บน MT4 / MT5 ลงใน stack.json
python -m harness.cli init --task-id GOLD-001 --title "Build XAUUSD Scalper EA" --agent strategy_pm --allowed-files docs/strategies/xauusd-scalper.md

# 2. ตรวจสอบสถานะและงานบน Top of Stack
python -m harness.cli status

# 3. สร้าง Clean JIT Prompt on Demand สำหรับ Agent
python -m harness.cli build-prompt

# 4. ส่งผลงานแบบ Structured Output เพื่อเปลี่ยน State
python -m harness.cli transition --input '{"action": "pop_task", "status": "completed", "summary": "Done"}'

# 5. ตรวจสอบไวยากรณ์และกฎความปลอดภัยของโค้ด MQL4 / MQL5 ด้วย Linter
python -m harness.cli check-mql experts/mt4/GoldScalper_MT4.mq4 experts/mt5/GoldScalper_MT5.mq5

# 6. ตรวจสอบและซ่อมแซมแผนภาพ Mermaid ในเอกสาร Markdown
python -m harness.cli check-mermaid docs/architecture/deterministic-harness.md --fix

# 7. คอมไพล์โค้ด MQL4 / MQL5 แบบ Headless ผ่าน MetaEditor จริง (0 Errors, 0 Warnings)
python -m harness.cli compile-mql experts/mt4/GoldScalper_MT4.mq4 experts/mt5/GoldScalper_MT5.mq5

# 8. รันชุดทดสอบ Ground-Truth Benchmark 12 ข้อ (ครอบคลุม MQL, Risk, Backtest และ Portability)
python -m harness.cli eval-benchmark

# 9. ตรวจสอบหน้าต่าง Blackout ข่าวเศรษฐกิจสหรัฐฯ ระดับสูง (NFP, CPI, FOMC)
python -m harness.cli check-news --symbol XAUUSD

# 10. วิเคราะห์ Backtest Report จาก MT5 (.html) พร้อมสร้าง Interactive HTML Dashboard
python -m harness.cli analyze-backtest sample-backtest/09w1m1.html --html

# 11. เปรียบเทียบผลลัพธ์ Backtest หลายไฟล์พร้อมกัน (Side-by-side Matrix)
python -m harness.cli analyze-backtest sample-backtest/ --compare

# 12. คำนวณ Walk-Forward Optimization (WFO) Matrix และวัดค่า Walk-Forward Efficiency (WFE)
python -m harness.cli analyze-wfo sample-backtest/ --split-ratio 0.3
```

---

## 🧪 การทดสอบ Ground-Truth Benchmark 12 ข้อ

ระบบผสานชุดทดสอบเชิงประจักษ์ (Empirical Ground-Truth Evaluation) จำนวน 12 ข้อ (รวม 120 คะแนนเต็ม) ตรวจสอบความถูกต้องและป้องกันข้อผิดพลาดอัตโนมัติ:

| Case ID | Benchmark Test Case | หมวดหมู่ (Category) | คะแนน | วัตถุประสงค์ในการตรวจสอบ |
| :---: | :--- | :--- | :---: | :--- |
| **TC-01** | MQL4 Backwards Loop Order Iteration | `MQL4_STANDARDS` | 10 | วนลูป OrdersTotal()-1 ถอยหลัง ป้องกันการข้ามตั๋ว |
| **TC-02** | MQL4 Order Identification & Slippage Guard | `MQL4_STANDARDS` | 10 | คัดกรอง MagicNumber และตรวจ MaxSlippage ก่อนส่งคำสั่ง |
| **TC-03** | MQL5 Modern OOP Trading Engine | `MQL5_STANDARDS` | 10 | ใช้งาน CTrade, CPositionInfo ปราศจากฟังก์ชันเก่าของ MT4 |
| **TC-04** | Dynamic ATR Trailing Stop & StopLevel Check | `RISK_MANAGEMENT` | 10 | คำนวณ Trailing Stop ตาม ATR ไม่ฝ่าฝืน StopLevel ของโบรกเกอร์ |
| **TC-05** | Breakeven Threshold Activation | `RISK_MANAGEMENT` | 10 | เลื่อน Stop Loss บังทุนพร้อมบวกกำไรเมื่อถึงเกณฑ์ Trigger |
| **TC-06** | Emergency Margin Call & Drawdown Circuit Breakers | `RISK_MANAGEMENT` | 10 | ตัดการทำงานทันทีเมื่อ Margin Level < 150% หรือ Daily Loss ≥ 5% |
| **TC-07** | Microstructure Spread Spike Interceptor | `MACRO_MICROSTRUCTURE` | 10 | บล็อกการเปิดออร์เดอร์เมื่อสเปรดทองคำถ่างเกิน 40 จุด |
| **TC-08** | High-Impact Macroeconomic News Blackout | `MACRO_MICROSTRUCTURE` | 10 | หยุดเทรดช่วงประกาศข่าว NFP, CPI, FOMC (หน้าต่าง $\pm 30$ นาที) |
| **TC-09** | Strict Zero-Test FinOps Token Invariant | `TOKEN_FINOPS` | 10 | บังคับนโยบายไม่สร้าง/รันเทสต์ที่ไม่จำเป็นโดยอัตโนมัติ |
| **TC-10** | Headless MetaEditor Compiler 0-Error 0-Warning | `HEADLESS_COMPILER` | 10 | คอมไพล์ผ่าน MetaEditor จริงบนเครื่อง ได้ไฟล์ .ex4 / .ex5 |
| **TC-11** | MT5 Strategy Tester Report Quantitative Audit Engine | `QUANT_AUDIT` | 10 | ตรวจสอบการ Parse สถิติ Backtest, Directional Asymmetry, และคะแนน Quant Score |
| **TC-12** | Strict Machine-Local Path Ban & Auto-Sanitization | `PORTABILITY_SECURITY` | 10 | ดักจับและทำความสะอาด Path เครื่องโลคัล (C:, D:, file://) ในเอกสารทั้งหมด |

---

## 📁 โครงสร้างโปรเจกต์ (Project Blueprint)

```text
GoldTrader/
├── AGENTS.md                          # กฎการกำกับดูแลเอเจนต์, 8 เสาหลัก และนโยบาย Zero-Test
├── README.md                          # ภาพรวมสถาปัตยกรรมและการใช้งาน
├── .gitignore                         # กำหนดไฟล์ยกเว้นชั่วคราว แคช ไบนารี และโฟลเดอร์ output/ experts/
│
├── harness/                           # 🛡️ เครื่องยนต์ Deterministic Harness
│   ├── __init__.py
│   ├── cli.py                         # เครื่องมือ CLI สำหรับควบคุมระบบ (รวม compile, eval, backtest, wfo)
│   ├── schemas.py                     # Data Schemas และ Structured Output Contracts
│   ├── state_machine.py               # Deterministic State Machine & Agent Routing
│   ├── task_stack.py                  # ระบบ Atomic Stack Management (stack.json)
│   ├── prompt_builder.py              # Prompt on Demand Builder (JIT Context Assembler)
│   ├── verifier.py                    # Deterministic Verifier & Headless MetaEditor Runner
│   ├── evaluator.py                   # 12-Case Ground Truth Benchmark Evaluator
│   ├── benchmark_cases.json           # สเปกชุดทดสอบเกณฑ์มาตรฐาน 12 ข้อ (TC-01 ถึง TC-12)
│   ├── backtest_analyzer.py           # ตัววิเคราะห์ผลทดสอบ MT5, แยก Deals, สเปรด, และสร้าง Dashboard
│   ├── wfo_calculator.py              # ตัวคำนวณ Walk-Forward Efficiency (WFE) และ Parameter Stability
│   ├── news_filter.py                 # Macroeconomic High-Impact News Blackout Gate
│   ├── sanitizer.py                   # ตัวถอดรหัสและซ่อมแซม JSON ในเครื่อง (Zero Token Repair)
│   ├── git_diff.py                    # Git Unified Diff Extractor
│   ├── cache.py                       # Tier-0 Dual-Layer Cache (L1 LRU + L2 SQLite WAL)
│   ├── mermaid_guardian.py            # Mermaid Unicode Guardian & Auto-Healer (Quote & XML Entity safe)
│   ├── document.py                    # Markdown-Native Clean Exporter (Local Path Ban & Auto-Sanitizer)
│   ├── interceptor.py                 # Emergency & Red Flag Risk Interceptor
│   ├── oracle.py                      # Grounding Whitelist Oracle (MQL APIs & Gold Specs)
│   └── test_guardian.py               # Strict Token Optimization & Test Policy Guardian
│
├── .agents/skills/                    # 🧠 ทักษะเฉพาะทางที่คัดเลือกและปรับแต่งแล้ว
│   ├── mql4-ea-development/           # สถาปัตยกรรม MT4, Order loops, Error 130/138, Slippage
│   ├── mql5-ea-development/           # สถาปัตยกรรม MT5 OOP, CTrade, CopyBuffer, OnTradeTransaction
│   ├── quant-analyst/                 # โมเดลคณิตศาสตร์, Sharpe, Sortino, VaR, Walk-Forward
│   ├── mt5-backtest-analyzer/         # ถอดรหัสและตรวจสอบ MT5 HTML Reports, วิเคราะห์สเปรดและค่าคอมมิชชัน
│   ├── backtest-architect/            # สถาปัตยกรรม Walk-Forward, Cornish-Fisher VaR, CVaR, Ulcer Index
│   ├── risk-manager/                  # Fixed Fractional, Half-Kelly, Margin & Drawdown Breakers
│   ├── mql-clean-code-guard/          # Clean Code, วงเล็บตรรกะ ((a && b) || c), Memory Safety
│   ├── trading-spec-driven/           # Quantitative Strategy PRD ก่อนเริ่มเขียนโค้ด
│   └── anti-hallucination-guardian/   # กฎเหล็กความจริงเชิงประจักษ์, Portability Invariant และการประหยัด Token
│
├── docs/                              # 📚 เอกสารสถาปัตยกรรมและนโยบาย
│   ├── architecture/
│   │   └── deterministic-harness.md   # สเปก Deterministic Harness เต็มรูปแบบ
│   ├── policies/
│   │   ├── unittest-policy.md         # นโยบายประหยัด Token (Zero-Test by Default)
│   │   └── mql-coding-standards.md    # มาตรฐานการเขียนโค้ด MQL4 และ MQL5
│   └── strategies/
│       └── xauusd-microstructure-spec.md # สเปก Market Microstructure สำหรับทองคำ (XAUUSD)
│
├── experts/                           # 🤖 ซอร์สโค้ด Expert Advisors (Ignored in Git)
│   ├── mt4/
│   │   └── GoldScalper_MT4.mq4        # MT4 Scalper EA พร้อม Backwards Loop, Trailing, Breakeven
│   └── mt5/
│       └── GoldScalper_MT5.mq5        # MT5 Scalper EA แบบ OOP พร้อม CTrade, CopyBuffer, Trailing
│
├── include/                           # 📦 ไลบรารีส่วนขยาย
│   ├── mt4/
│   │   ├── TradeHelper_MT4.mqh        # ตัวคำนวณ Lot, Spread, Trailing Stop, Breakeven สำหรับ MT4
│   │   └── NewsFilter.mqh             # ตัวกรองข่าวเศรษฐกิจสหรัฐฯ สำหรับ MT4
│   └── mt5/
│       ├── TradeHelper_MT5.mqh        # คลาสคำนวณ Lot, Spread, Trailing Stop, Breakeven สำหรับ MT5
│       └── NewsFilter.mqh             # ตัวกรองข่าวเศรษฐกิจสหรัฐฯ สำหรับ MT5
│
├── output/                            # 📤 โฟลเดอร์ส่งออกรายงาน Clean Markdown (.md) และ HTML Dashboards (Ignored in Git)
└── cache/                             # 🗄️ ฐานข้อมูล SQLite Compressed Disk Cache
```

---

## 🛡️ กฎเหล็กการเขียนโค้ด MQL บน GoldTrader

1. **การใส่วงเล็บสำหรับตัวดำเนินการตรรกะ (Operator Precedence)**:
   - บังคับใส่วงเล็บ `()` ครอบคู่เงื่อนไขเสมอเมื่อใช้ `&&` ร่วมกับ `||`:
     `if(((isTrendBullish && rsiOversold)) || ((breakoutBuy && volumeSurge)))`
2. **การวนลูปออเดอร์ใน MT4 (Backwards Loop Invariant)**:
   - ต้องวนลูปถอยหลัง `for(int i = OrdersTotal() - 1; i >= 0; i--)` เพื่อป้องกันการข้าม Order Index เมื่อมีการปิดออเดอร์
3. **การคืนหน่วยความจำอินดิเคเตอร์ใน MT5 (Resource Cleanup Invariant)**:
   - ต้องเรียกใช้ `IndicatorRelease(handle)` ใน `OnDeinit()` สำหรับทุก Indicator Handle
4. **การคำนวณขนาด Lot ตามความเสี่ยง (Risk-Based Lot Sizing)**:
   - ห้ามใช้ Fixed Lot โดยไม่มีการคำนวณ Stop Loss distance และมูลค่า Tick Value ต่อบัญชี
5. **การป้องกัน Path โลคัลในเอกสารที่สร้างขึ้น (Machine-Local Path Ban)**:
   - เอกสารและรายงานทั้งหมดที่บันทึกลงใน `./output/` หรือ `docs/` ต้องใช้ Repository-relative path (`./...`) หรือ Basename เท่านั้น ห้ามใส่ไดรฟ์เครื่องส่วนบุคคล
