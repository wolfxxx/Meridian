# FIS Prophet (FIS Insurance Risk Suite): Analysis and Specification for a Competing Platform

**Version:** 3.2. v3.1 passed three rounds of independent review (verdict: SATISFIED). v3.2 adds ADR-001 (Rust engine core, §25.1) and the prototype results.
**Date:** 2 November 2026
**Purpose:** (1) Describe, as completely as public information allows, the abilities, architecture, features, commercial model, market position and competitive environment of FIS Prophet, the dominant actuarial modelling platform in life insurance. (2) Use that analysis to write a product specification for a competing platform that improves on it.

**How to read this document**
- **Part I (sections 1–14)** is descriptive: what Prophet is and does.
- **Part II (sections 15–34)** is prescriptive: what the competitor must do and how it beats Prophet.
- Claims about Prophet are sourced, and the references are listed in Appendix C.
- **[UNVERIFIED]** marks claims based on inference, a single weak source, or search-engine snippets of pages that could not be read directly. Vendor performance figures are vendor claims.

> Not to be confused with Meta's open-source "Prophet" time-series forecasting library, Prophet 21 ERP, or Prophet CRM.

---

## Table of contents

**Part I: Prophet as it is**
1. Executive summary
2. History, ownership and corporate status
3. Product suite and component map
4. The modelling paradigm and language
5. Tables, assumptions and data inputs
6. Run types, calculation engine and performance
7. Actuarial content: libraries and product coverage
8. Accounting, regulatory and management applications
9. Results, reporting and integration
10. Governance, controls and security
11. Deployment, cloud and AI
12. Commercial model, pricing and total cost of ownership
13. Market, customers and ecosystem
14. Competitive landscape

**Part II: Specification for the competing platform**
15. Prophet strengths and weaknesses (the gap analysis that drives the spec)
16. Product vision, positioning and design principles
17. Target users and personas
18. Functional requirements: modelling language and model structure
19. Functional requirements: engine, run types and performance
20. Functional requirements: actuarial content and regulatory libraries
21. Functional requirements: data, assumptions, results and reporting
22. Functional requirements: governance, collaboration and DevOps
23. Functional requirements: AI capabilities
24. Non-functional requirements
25. Reference architecture
26. Migration strategy from Prophet (including legal constraints)
27. Commercial model, go-to-market, roadmap and risks
28. Strategic options: build, buy, partner, open-core
29. Team, build cost and business case
30. Success metrics, release acceptance criteria and benchmarks
31. Validation and assurance strategy
32. Licensing, IP, data-use and support terms
33. Competitive response scenarios
34. Requirements traceability

**Appendices**
- A: Glossary
- B: Open questions and research gaps
- C: Sources

---

# PART I: PROPHET AS IT IS

## 1. Executive summary

- **What it is.** Prophet is a proprietary actuarial projection platform. Actuaries write cash-flow models of insurance liabilities, and optionally assets, in a C-like formula language organised into vendor-supplied "libraries". Prophet generates C/C++ code from them, compiles it and runs it over policy-level "model points". The runs are deterministic, stochastic, nested-stochastic and dynamic ALM, and they serve pricing, valuation, IFRS 17, US GAAP LDTI, US statutory PBR, Solvency II, embedded value, business planning, ALM and capital.
- **Who owns it.** Bacon & Woodrow (UK) created it in 1987–89. It passed to Deloitte (2001), then SunGard (2005, as "iWorks Prophet"), then FIS (Nov 2015). It is now marketed as **"FIS Insurance Risk Suite – Prophet"**.
- **Market position.**
  - FIS claims about **80% of the world's top 50 insurers**, **10,000+ users** and **850–1,000 customer sites** in **65–90+ countries**. The figures vary by date and source.
  - It is the incumbent in the UK, Europe, Asia-Pacific, India, Africa and much of Latin America.
  - In North America it is weaker. There Moody's AXIS and Milliman MG-ALFA are the most-used packages, though Prophet has major US users such as New York Life, Pacific Life and MetLife.
- **Current product state (2026).**
  - Version **2026 Q1 SP2** is current, and 2027 Q2 is planned.
  - Components were renamed: Prophet Professional became **Model Developer** and Prophet Enterprise became **Enterprise Manager**.
  - New: a SaaS burst-compute tier, **Production Manager**, on AWS (2024), and Model Developer as SaaS (from late 2025).
  - Engine: Linux calculation workers (2024–26) and GPU/AVX "looped modules" (preview from 2024).
  - An embedded GenAI **AI Assistant** launched on 23 Feb 2026.
- **Strengths.**
  - The deepest library catalogue in the market: 20+ libraries spanning life, health, pensions, VA, ALM, proxy, IFRS 17 and GI.
  - A huge installed base and talent pool, plus a regulator user (IRDAI, India).
  - Nested structures, dynamic ALM and an end-to-end chain from data, through assumption governance, runs and results database, to the IFRS 17 subledger.
- **Weaknesses that a competitor can exploit.** A 1989-era desktop/Windows heritage. A proprietary language with arbitrary limits and hard debugging. Weak native version control and DevOps. Many separately versioned bolt-on components. Proprietary file formats and terabyte output volumes. Paid add-ons for basic needs such as flexible result grouping. Opaque, quote-only pricing. Cloud offered as re-hosting, not cloud-native. GPU that requires re-writing models. Lock-in, made concrete by FIS's 2024 trade-secret lawsuit against Montoux. Montoux was a NZ pricing and decision-science platform whose "Model Replication Module" helped clients replicate Prophet models elsewhere. A thin, expensive talent pool.
- **Counterweight.** Prophet keeps winning industry awards: InsuranceERM "Actuarial Modelling Solution of the Year" in 2021 (UK & Europe), 2022 (Americas), 2024 (UK & Europe) and 2025 (Americas). The market sees it as a living product, not a legacy one.
- **Strategic opening (2026).** Competitors are moving fast: WTW (GPU, agentic AI), Moody's (AXIS Cloud, Navigator), Aon (GPU-native PathWise winning ICICI Prudential), and Akur8's purchase of Slope. FIS is reviewing "select products" in its Capital Markets segment (Aug 2026), and Prophet sits in that segment. A modern, open, cloud-native, Python-interoperable platform with credible libraries and a safe migration path has a real window.

---

## 2. History, ownership and corporate status

### 2.1 Timeline

| Year | Event |
|---|---|
| 1987 / 1989 | Bacon & Woodrow (UK actuarial consultancy) creates Prophet. SunGard says it was "originally launched in 1987"; FIS dates **Prophet 1.0 to 1989** [R1, R2] |
| 1991 | Prophet 3.0 runs on "transputers", processing 20 policies simultaneously [R1] |
| 1994 | Prophet 4.3 introduces "Parallel PC mode", which FIS claims was the first distributed actuarial processing on the market [R1] |
| 1998 | Prophet 6.0: first Windows version. **DCS** (Data Conversion System) introduced [R1] |
| 1999 | **Glean** experience-analysis tool [R1] |
| 2001 | Bacon & Woodrow demerges. Its insurance practice, which owns Prophet, joins **Deloitte** ("B&W Deloitte"); employee benefits joins Hewitt. Prophet 7.0 [R1, R3] |
| 2004 | Prophet Enterprise development starts |
| Sep/Oct 2005 | **SunGard** buys Prophet from Deloitte & Touche LLP (UK). Sarbanes-Oxley auditor-independence rules are cited as the driver [R2, R4] |
| 2006 | Brand "SunGard iWORKS Prophet". **ALS (Asset Liability Strategy)** library [R1, R5] |
| Jul 2007 | **Prophet Enterprise** launched as a client-server controlled production environment [R6] |
| 2008–09 | Prophet Enterprise tested on more than 1,000 cores in an Intel lab. Hosted grid with Sun, Intel and Microsoft. Replicating Portfolio library [R1, R7] |
| 2010 | Prophet 8.0: Managed Hosted Services and a Data Management Platform (results database lineage) [R1] |
| 2012 | Table Manager; curve fitting / LSMC library [R1] |
| 2013 | Prophet Analytics; Prophet GI; ALS extended to MBS/CDOs and US RMORSA [R1, R8] |
| 2014 | **Prophet Managed Cloud Services (PMCS)** [R1] |
| 2015 | Prophet 9.0 with **Nested Structures**. **FIS acquires SunGard** (closed 30 Nov 2015; headline about US$9.1bn including debt) [R1, R9] |
| 2016 | Assumptions Manager [R1] |
| 2017 | IFRS 17 solution about one month after the standard was published. 9.0.4 (Aug 2017) is the last numbered release found [inferred: R10, R11, R24] |
| 2018 | Calendar versioning begins: the archived supported-versions page lists 2018 Q3, 2019 Q2, 2020 Q2 and 2021 Q2 before 2022 Q1. LDTI support about one month after the ASU. **Conning GEMS** ESG partnership (signed Jun 2018, announced Nov 2018) [R12, R13, R15] |
| ~2020–21 | Rebrand to **"FIS Insurance Risk Suite (formerly Prophet)"** [R14] |
| 2022–24 | 2022 Q1, 2023 Q2 (adds GCC/MinGW compiler), 2024 Q4 (adds enumeration type, GPU preview, Linux workers) [R15] |
| 2024 | First **SaaS** offering: **Production Manager** (burst compute on AWS) [R16] |
| H2 2025 | **Model Developer** delivered as SaaS [R16, R17] |
| 23 Feb 2026 | **Insurance Risk Suite AI Assistant** launched [R18] |
| 12 Mar 2026 | **2026 Q1** released (SP1: Linux workers for Enterprise, PostgreSQL in Process Orchestrator; SP2: orchestration features) [R15] |
| Jul 2026 | InsuranceERM 2026 Americas "Best Use of AI in Risk Management" [R19] |
| 4 Aug 2026 | FIS says it is "evaluating strategic alternatives" for "select products" in the Capital Markets segment, which includes Prophet. No product was named [R20] |
| Jun 2027 (planned) | 2027 Q2 release [R15] |

**Source inconsistencies to note.**
- Prophet 7.0 is dated 2001 in the FIS timeline but appears as 2004 in one note.
- Prophet GI is dated 2013 or 2014.
- The Replicating Portfolio library is dated 2008 or 2009.

None of these changes the analysis.

### 2.2 Corporate status and implications
- Prophet sits in FIS's **Capital Markets** segment, under "Treasury and Risk" / "Office of the CFO". FIS does not disclose Prophet revenue [R9, R20].
- Neither the Worldpay sales (2024–26) nor the TSYS Issuer Solutions swap touched the insurance software. No sale, spin-off or rebrand of Prophet was found to 2 Nov 2026 [R20].
- **Ownership risk.** The Aug 2026 review of "select products" is ambiguous. Customers could see a possible sale as a reason to re-evaluate platforms. This is a sales opening for a competitor and should be monitored.
- **Organisation.**
  - The business is historically run from **London**.
  - Development and product roles in 2026 are in London, Warsaw, Serbia and Hong Kong.
  - Named teams: Actuarial Systems, Library Development (InsuranceERM 2020 Modelling Team of the Year), GI Development and Consultancy.
  - Team size is not published [R21].

### 2.3 Release and support policy
- **Naming and cadence.** Releases are named "YYYY Qn", with a major release every 12–18 months plus service packs (SPn).
- **Support window.** The standard licence supports the **current version and the two preceding ones**, about three years each.

| Version | Released | End of support |
|---|---|---|
| 2022 Q1 | 31 Mar 2022 | 31 Oct 2025 |
| 2023 Q2 | 7 Jun 2023 | 12 Dec 2026 |
| 2024 Q4 | 12 Dec 2024 | 12 Mar 2028 |
| 2026 Q1 | 12 Mar 2026 | 2029 |

  Source: [R15]
- **Library versioning.** Libraries are versioned separately from the system and are "sub-divided into books" to ease upgrades [R22].
- **Upgrade cost.** Large customers fork the FIS libraries and must "manage merges of new FIS library releases into existing versions". This is a recurring cost [R23].

---

## 3. Product suite and component map

"Insurance Risk Suite – Prophet" is a family of separately versioned components.

| Current name | Former name / abbrev. | Role |
|---|---|---|
| **FIS Model Developer** | Prophet Professional (PP) | Windows desktop (and now SaaS) model design, coding, compilation, testing and single-machine or small-cluster runs. A Firebird DB is listed for the 9.0.x era [R24]; the current back end is unconfirmed |
| **FIS Enterprise Manager** | Prophet Enterprise (PE) | Multi-user, server-based, permissioned production environment. Job scheduler, multithreaded Windows/Linux workers, locked-down inputs/outputs, backup and version control |
| **FIS Production Manager** | (new, 2024) | Cloud-native SaaS "burst" execution on AWS, which removes the need for on-prem grids [R16, R17] |
| **Managed Cloud Services** | PMCS (2014) | FIS-hosted PP/PE on AWS or Azure. Private ring-fenced networks, SOC 2 Type 2, encryption, pen tests [R25] |
| **FIS Assumptions Manager** | Prophet Assumption Manager (2016), descended from Table Manager (2012) [UNVERIFIED lineage] | Governed store for tables and assumptions, with entry/approval roles, audit trail and Excel integration |
| **DCS** | Data Conversion (and Grouping) System (1998) | ETL from admin-system extracts (fixed-width, CSV, tab, Access) to model-point files. Grouping/compression, validation reports |
| **Glean** | (1999) | Experience analysis (mortality, lapse studies) and credibility-based assumptions, e.g. for VM-20 |
| **FIS Flexible Results** (+ API) | FR | Add-on that writes results to a distributed database with flexible aggregation (e.g. IFRS 17 unit of account). **Extra subscription** [R26] |
| **SQL Connector** | Prophet Results Database (PRD) | Loads results into a SQL Server staging database |
| **FIS Data Repository** | Insurance Data Repository (IDR) | SQL Server/Oracle dimensional results store. XML mapping of variables to business dimensions and chart of accounts. Percentiles from simulations. Audit trail |
| **FIS Process Manager** | Prophet Control Centre (PCC) | BPM workflow automation (built on Infinity Process Platform). Electronic approvals and process history |
| **FIS Process Orchestrator** | PO (2022) | Newer orchestration with task templates (submit Enterprise Manager / Assumptions Manager jobs), REST integration, SFTP, PostgreSQL (2026) |
| **Prophet Quality Assurance** | PQA | Test-case management and regression testing for models |
| **Excel Reporting** | — | Excel add-in/templates for results |
| **PP & PE API** | — | Versioned automation API (technology not publicly confirmed: COM/.NET [UNVERIFIED]) |
| **Libraries** | — | 20+ actuarial libraries, licensed individually (section 7) |
| **Insurance Accounting Suite** | Enterprise Accounting System | IFRS 17 subledger. With Prophet it is sold as the "FIS Insurance Risk and Accounting Suite" |
| **GI Edition** | Prophet GI (2013) | P&C reserving and capital modelling, with "Prophet Forms" UI |
| **AI Assistant** | (2026) | Embedded GenAI documentation Q&A. Code writing and explanation are on the roadmap |

Sources for unlabelled rows: [R14, R15, R24, R26, R27].

**Observation.** The suite has grown by accretion over 35 years. The supported-versions page tracks separate version lines for PP/PE (which bundle Glean, DCS, PRD, API, PQA and Excel Reporting), IDR, PCC and PO. Integration between components is configured by the customer, and much of it is XML, batch-file or SQL-based.

---

## 4. The modelling paradigm and language

### 4.1 Core objects

| Object | Description |
|---|---|
| **Workspace** | Container for libraries, products, run structures, run settings, tables and model-point files. Supports backup/restore, maintenance and workspace objects such as enumerations |
| **Library** | Collection of **variables** and their **definitions** (formulas), organised into variable groups (e.g. Conventional library groups A–M are core, N–Z are input). Vendor-supplied, customer-modified |
| **Indicator** | A Boolean feature flag with no formula, e.g. `ORD_PAR`, `SING_PREM`, `INVST_LINK`, `ALWAYS`. Indicators carry "must not be selected if" exclusivity rules |
| **Variable definition** | A variable can have several definitions, each keyed to an indicator expression (`ORD_PAR AND SING_PREM`). The definition **type** is Formula, Constant, Global, Parameter, Extended Formula, or t-dependent Extended Formula |
| **Product** | Built by selecting indicators, often via a wizard. Only variables whose indicator conditions match are compiled. Variants: master, **"same as"** (reuses code) and summary products |
| **Module** | Reusable code called repeatedly with different inputs. Suited to repeated stress bases, e.g. the Solvency II shocks |
| **Run structure** | Defines which products run, the new-business SPCODE threshold and nesting |
| **Run setting** | Parameters of a run: projection start, term, what to output |
| **Run number** | Indexes an assumption set. Global tables vary by run number, which is used for sensitivities and scenarios |
| **SPCODE** | Mandatory sub-product code in the first column of every model-point file. One practitioner source says the maximum is 9999 [R30], but a public example file shows a six-digit SPCODE (101000) [R38], so the limit is **[UNVERIFIED]**. Results are output per SPCODE plus a total (SPCODE 0). SPCODEs above a run-structure threshold are new business. Without Flexible Results, SPCODE is effectively the **only built-in grouping dimension** of output |
| **Accumulation** | A "summary product" that sums the results of chosen products and SPCODEs, used to build company or line-of-business totals. Accumulations can themselves feed later calculations, e.g. Summary library aggregation or ALS company-level logic |
| **Global variable / Global definition** | A definition type whose value is constant across all model points and products for a run number. It is read from global tables and used for run-wide parameters such as valuation date, sensitivity multipliers and expense inflation |
| **Variable properties** | Each variable has a data type, an **Accounting Type** (revenue account, i.e. a flow, vs balance sheet, i.e. a stock), a **Cumulative** flag (whether it is summed across model points), a **Variable Code**, and dimensions if it is an array. These properties drive aggregation and reporting semantics [R28] |
| **Variable group** | A named subset of variables selected for output. It is the main way to control output volume [R28] |

Sources: [R26, R28, R29, R30].

### 4.1a Workspace, run settings and production mechanics
- **Workspace on disk.** A folder tree holds the library and product definitions, `TABLES\` and `MPFILES\` folders, generated and compiled code, diagnostic files (compile errors are read from `compile.txt` in the generated-code folder), and results folders per run [R32, R38] [folder names UNVERIFIED as a standard].
- **Run settings.**
  - Settings specify the projection start (valuation) date, projection term, time step, products and structure to run, run numbers, the number of simulations (stochastic), output variable groups, and the output types: projection (PRJ), individual model-point (IMP/RPT) and stochastic summaries (STO).
  - Stochastic and dynamic runs need their own run structures and settings, separate from deterministic ones [R26, R5].
- **Model Developer run types.** Single-machine runs, multi-run batches over run numbers, and "parallel processing" across networked PCs under a master PC. Multithreading is reserved for Enterprise [R26].
- **Enterprise mechanics.** Models built and signed off in Model Developer are exported or imported into Enterprise Manager, where jobs are defined, approved and executed. Inputs and outputs are locked. Roles are Modelling Actuary, Approver and Execution [R6, R27]. Workspace check-in, locking and "backup and version control" are provided [UNVERIFIED in detail].
- **Rundowns.** A training-syllabus topic, taken to be step-by-step reruns or analysis-of-change sequences [UNVERIFIED meaning] (AARC Prophet training syllabus [R69]).

### 4.1b Dynamic loop and in-memory mechanics
- **Why the dynamic loop exists.** In a "dynamic" run, liability products and an ALS company-level product are projected **in lockstep, one time step at a time**.
  - At each step the liability products pass their period cash flows and balances up to the ALS product. Prophet automatically outputs "the values which need to be passed from one dynamic loop to the next".
  - ALS then performs the asset projection, investment returns, rebalancing, defaults and management actions such as bonus rates, crediting rates and equity backing ratio.
  - The resulting company-level decisions feed back down as inputs to the liability products for the next step. Any liability assumption can be redefined to read from "a variable calculated in a higher level or ALM product in the previous dynamic loop" [R46].
- **Liability approaches** [R5, R23]:
  - **Flexing**: scale pre-computed liability results by projected in-force.
  - **External**: read liability results produced by earlier runs (`READ_RESULTS`).
  - **Internal**: liability code runs inside the ALS dynamic loop.
- **IMD / IMS.** In-Memory Dynamic and In-Memory Stochastic methodologies keep all model points' state in memory so that the step-synchronous loop does not re-read files each period. "Dynamic model point processing" refers to this [R5].
- **Implication for any competitor.** Cross-policy feedback (company-level actions, fund smoothing, aggregate reinsurance, group IFRS 17 measures) forces **time-synchronous execution**. It cannot be expressed as independent per-policy projections. (See §19.4.)

### 4.1c Stochastic simulation handling
- **Indexing.** Simulations are numbered, and scenario data comes from stochastic tables or ESG files indexed by simulation and time, e.g. `STOCHRET`.
- **Outputs.** Per-simulation results can be written out, and "stochastic summaries" (STO) are produced.
- **Statistics downstream.** Percentiles, CTEs and distribution statistics are typically computed downstream, in IDR ("compute percentiles from simulation data") or in Excel, rather than natively in the projection. The IDR mapping file decides whether simulation-level data is kept or discarded [R27].

### 4.1d Time step and timing conventions
- **Time step.** Monthly is the default, with annual possible. Liability libraries such as Cardif's French library use mid-month timing, and ALS models often run annually (Cardif thesis [R70]).
- **Conventions.** Libraries embed conventions such as the following, which a migration must map exactly:
  - when within the period premiums, claims, expenses and decrements occur (start, mid or end)
  - decrement ordering (death before lapse, for example)
  - whether decrements are independent or dependent
  - policy-month vs calendar-month alignment
  - interest timing
- **Why it matters.** These conventions are the **largest source of reconciliation differences** when re-implementing a Prophet model elsewhere [inference from practitioner experience].

### 4.1e Multi-currency and multi-entity
- **Not found.** No public source describes Prophet's multi-currency mechanics.
- **Likely practice [UNVERIFIED].**
  - Products are modelled in their own currency, with FX rates and FX scenarios supplied as tables to ALS or Summary products for conversion and asset-currency matching.
  - Group consolidation is usually performed downstream (IDR, Excel, consolidation systems).
- **Significance.** Multi-currency books matter in Hong Kong (HKD/USD), Singapore, the Middle East and multinationals. The competitor spec treats them as explicit requirements (§20.7).

### 4.2 Language
- **Style.** An expression language "that looks like simplified C++". The formula body *is* the value [R31].
- **Example syntax:**
  ```
  IF t = 0 THEN 0
  ELSE IF mult(t-1,12) AND POLICY_YEAR <= MAX_INVRATE_YR THEN
     READ_GENERIC_TABLE("Inv_rate","Y","PROD_NAME",POLICY_YEAR)
  ELSE UFII_PC(t-1)
  ```
- **Time.** `t` is the projection-period index. Monthly projection is the default, and annual is possible, e.g. ALS models. Recursion is via `X(t-1)` [R28].
- **Data types.**
  - Number and text. Text cannot depend on `t`.
  - **Enumeration** types added only in 2024 Q4.
  - Array variables, with at most **4 dimensions** in user-defined functions [R32].
- **User-defined functions.** Limited to **9 input parameters and 250 lines of code** [R32].
- **Extended formulas.** Procedural blocks for logic beyond an expression, such as rebasing or paid-up isolation. Their internal variables are **not visible in Diagram View**, which hampers debugging [R26].
- **Calculation loops.** `NUM_CLCLOOPS`, `CALC_LOOP` and `NO_CALC` repeat the full calculation within one run, e.g. for reserves on multiple bases or RBC stress cases [R33].
- **Built-ins.** Table readers (`READ_GENERIC_TABLE`), `READ_RESULTS` (ALS reading liability results), divisibility tests, enumeration conversions, and a **Maths Plugin** (matrix operations, statistical distributions including copulas, random sampling, curve fitting, solvers) [R34].
- **Compilation.**
  - Prophet generates code that needs a **C++ compiler**: MSVC 2017/2019, MinGW GCC 11.2 on Windows (from 2023 Q2), or GCC 11.5 on Linux (from 2024 Q4). Output has been 64-bit since 2018 Q3. VS2022 was not supported through 2026 Q1 [R35].
  - Prophet handles dependency ordering automatically. Users compile with "compilation, auto scan and regeneration".

### 4.3 Developer and results tooling
- **Diagram View.** Traces the precedents and dependents of a variable, inspects tables and model points, and shows computed values after a run. It has filters, plus an **auditor version** [R26].
- **Schedule view.** A grid of variables × products, used for model merges.
- **Comparison logs.** Compare libraries and workspaces to support merges.
- **Actuarial Documentation.** Generates documentation from descriptions attached to objects.
- **Diagnostic files and run logs.** Compile errors are read from `compile.txt` and the run log [R32].
- **Result View and results viewer.** Projection results can be browsed by variable × time × SPCODE/accumulation inside Model Developer, and Diagram View shows the values beside the formulas. Excel Reporting templates and an Excel plug-in extract results for analysis [R31, R26].
- **Excel side-models.** Practitioners commonly validate results by replicating single policies in Excel, because "checking spreadsheet was easier than checking coding" [R36].

### 4.4 New business modelling
- **Inputs.** New business is a profile per unit premium multiplied by a sales file, with monthly volumes per product. NB model points have `DUR_M=0`, and SPCODEs above a threshold denote new business [R37].
- **Methods.**
  - Cross-multiplication: one profile.
  - Project method: one profile per start month. This is about **36× slower** over 3 years.

---

## 5. Tables, assumptions and data inputs

### 5.1 Table types
| Type | Purpose |
|---|---|
| Parameter tables | One row per product; values constant across a product's model points |
| Generic tables | Values indexed by 2–10 keys |
| Global tables | Constant across products for a given run number (sensitivities, inflation) |
| Mortality tables | Standard and custom rates |
| Stochastic tables / ESG tables | Values by simulation (e.g. `STOCHRET`, `DET_RETS`) |
| ALS configuration tables | Many tables drive ALS without code changes, e.g. `COMPANY_ASS`, `ASSET_POOL_RULES`, `CFLOW_DEPEND`, `RESERVING_BASES` and `MAT_SMOOTHING` |

- **Performance guidance.** Large tables (more than 5,000 rows with 5 keys) hurt runtime, and reads cost more than arithmetic. Common practice is to keep tables in Excel and generate Prophet tables with VBA [R28].

### 5.2 File formats
- **Model-point files (`.PRO`).** One file per product. Layout:
  - header lines (`Output_Format`, `NUMLINES`)
  - a `VARIABLE_TYPES` row (`T8` text width 8, `N` number, `I` integer, `S` short, `Dmm/dd/yyyy` date)
  - `!` header row, then `*` data rows
  - optional DCS footers, which break plain-CSV parsing [R38]
- **Tables (`.fac`, `.prn`).** A title line, then `!n,keys...` and `*` rows.
- **Results.** `.rpt` (individual model-point output, IMP), projection (PRJ) and stochastic (STO) outputs. Volumes can reach **terabytes** [R39].
- **Third-party parsers.** Open-source tools fill the gap: `mpfi` (Python/pandas) and `mpduck` (a DuckDB extension).

### 5.3 Data preparation (DCS)
- **Function.** Converts and summarises admin extracts into asset and liability model points. It enriches data with reference tables and multiple input files, outputs seriatim or grouped MPFs, and produces validation reports that can fail the conversion [R40].
- **Other uses.** DCS also builds asset and ESG data for ALS.
- **Grouping (model-point compression).**
  - DCS "grouping runs" compress seriatim data into grouped model points. The user specifies **key fields** (e.g. product, sex, smoker, issue-age band, duration band, term band) and banding rules.
  - Within each group, additive fields such as sum assured, premium and fund are **summed**, and attributes such as age and duration are **averaged**, typically weighted by sum assured or reserve.
  - Grouped MPFs feed "calculation runs".
  - Accuracy is checked by comparing grouped results with seriatim results (reserves and cash flows within a tolerance) [R26, R40] [specific error metrics UNVERIFIED].
  - VM-20/21 on-the-fly grouping is a separate in-run mechanism (§6).
- **Trend.** Customers are replacing DCS with Alteryx and Python [R40].

### 5.3a Experience analysis (Glean)
- **What it does.** Glean (1999) performs experience investigations: exposure calculation, actual-vs-expected for mortality, morbidity and lapse, and credibility. It feeds assumption setting, including the VM-20 credibility-based prudent estimate assumptions [R42].
- **Successor.** A newer "Experience and Rating Manager" page exists on prophet-web; whether it replaces Glean is [UNVERIFIED]. Glean is still versioned with PP/PE in 2024 Q4 SP6 [R15].
- **Scope limits.** Glean is not known to offer modern GLM or ML-based assumption fitting [UNVERIFIED].

### 5.4 Assumptions governance (Assumptions Manager)
- Actuaries, not modellers, enter assumptions. Entry and approval roles ensure only confirmed inputs are used.
- It integrates with assumption-setting spreadsheets, works for both Developer and Enterprise runs, and supports automated sensitivity runs and analysis of change [R41].

---

## 6. Run types, calculation engine and performance

| Run type | Prophet mechanism |
|---|---|
| Deterministic | Single run over model points; multiple runs by run number |
| Stochastic | Multiple simulations driven by stochastic/ESG tables; "stochastic summaries" (STO) |
| Dynamic (ALM) | Assets and liabilities interact each period through the ALS library. Liability approaches are "flexing", "external" (`READ_RESULTS`) and "internal". "Any input assumption can be changed to make it calculate dynamically" from a higher-level/ALM product in the previous loop |
| In-memory dynamic / stochastic | IMD and IMS methodologies, plus dynamic model-point processing in ALS [R5] |
| Nested stochastic | **Nested Structures** (2015) put runs within runs: stochastic-on-stochastic, future VM-20/21 reserves, projected SCR for risk margin, IFRS 17 forecasting, GAAP unlocking projections, projected Greeks |
| Calculation loops | Repeat the calculation on alternative bases within one run |
| Goal seeking | Premium rates for target profitability; self-supporting bonus rates; market spreads; rebasing |
| On-the-fly grouping | Seriatim outer run with grouped inner runs (VM-20 DR/SR, VM-21 CTE) [R42] |
| Sensitivities / analysis of change | Run numbers, global tables, Assumptions Manager automation |

### 6.1 Distribution and hardware
- **Evolution of distribution.** Transputers (1991), then Parallel PC mode (1994), then a master PC plus networked machines (Professional), then multithreaded Enterprise workers on Windows or Linux (2024–26), then AWS burst through Production Manager.
- **GPU / AVX "looped modules".** Data is restructured into vectors with simulation or scenario as the loop dimension. FIS claims (vendor case study [R43]):

| Model | Hardware | Claimed result |
|---|---|---|
| Critical illness | AVX CPU | About 85% faster |
| Annuity Solvency II | A100 GPU | About 60–75% faster/cheaper |
| Unit-linked with guarantees | GPU | About 97% runtime/cost reduction |

- **GPU caveat.** FIS itself says GPU is not "a flick of a switch". Models must be vectorised with less branching, "normally not topics that actuaries need to consider". T4 GPUs hit memory limits [R44].
- **Run-time pressure in the industry.** A 2021 SOA/Oliver Wyman survey found US insurers **cut scenario counts by 88% on average** to manage run time. More than half spend more time running processes than analysing results [R45].

### 6.2 Run-time baselines and the close process
- **Baselines.** Prophet run times are not published, and none appear in independent benchmarks. The best public proxies:
  - **SOA Modeling Platform PBR survey (Nov 2020).** Full quarter-end production valuation runs took **"a few hours to an entire day"**. No participant ran the full 10,000 scenarios in valuation, and most cut to about 1,000 with scenario-picking tools. The most common way to cut run time was fewer stochastic scenarios. About 50% had considered changing systems because of PBR [R64; run-time details taken from a search summary of R64 and to be re-checked against the full text].
  - **FIS UK PMCS case.** About 1,000 cores were needed on-prem, and up to about 5,000 cores were available elastically on AWS. Average on-prem utilisation was **below 15%**, with year-end peaks [R53].
  - **Vendor GPU case studies.** These imply the CPU baselines for VA, unit-linked-with-guarantees and annuity SII runs are many hours (§6.1).
  - **Benchmarking restrictions.** Licences commonly restrict publishing benchmarks [UNVERIFIED for Prophet]. Any Meridian-vs-Prophet comparison must therefore be customer-run (§30.3).
- **Typical close calendar** (industry practice, not Prophet-specific):
  - **Quarter-end.** Data cut at working day (WD) 0–2. Model runs WD 2–8. Analysis of change, review and sign-off WD 6–12. Group consolidation WD 10–15.
  - **US filings.** 10-Q within 40 or 45 days and 10-K within 60–90 days of period end. US statutory annual statement due **1 March**. The PBR Actuarial Report (VM-31) and the actuarial opinion are filed with it, and the asset adequacy memorandum is generally due **1 April**.
  - **Solvency II QRTs.** Solo quarterly QRTs within 5 weeks and solo annual QRTs/SFCR within 14 weeks, with groups allowed 6 weeks more.
  - **IFRS 17.** Interim and annual reporting runs the full chain: cash flows, discounting/RA, CSM roll-forward, AoC and journals.
  - **Compute peak.** Runs are chained across bases (best estimate, IFRS 17, SII, local stat, tax, GAAP). Compute demand peaks 5–20× above steady state for a few days per quarter, which is why burst cloud is attractive.

---

## 7. Actuarial content: libraries and product coverage

Libraries are Prophet's moat. FIS says they are maintained by "a large team of actuaries", use an "open code architecture and tabular inputs", and allow products to be built "quickly using a wizard". Each library is **licensed individually** [R22, R46].

### 7.1 Library catalogue (prophet-web.com, Jan 2022) [R22]

| Group | Library | Key content |
|---|---|---|
| Life & annuity | **Conventional** | Non-linked business in the UK, SA and Asia (details below) |
| Life & annuity | **Unit Linked** | Unit and sterling reserves; hosts the VA modules |
| Life & annuity | **International** | Generic life for other markets; hosts the VA modules |
| Life & annuity | **Variable Annuity Modules** | Guarantees, Greeks and inner loops (details below) |
| Life & annuity | **German (Deutsche)** | RfB policyholder participation, Finanzierbarkeitsnachweis, German statutory P&L |
| Life & annuity | **French** | French market (details not retrieved) |
| Life & annuity | **Group Pensions** | DB/DC schemes, multi-state members, funding methods (details below) |
| Life & annuity | **Summary** | Aggregation. With ALS it computes the Solvency II SCR, MCR and Risk Margin |
| Life & annuity | **US Library** | US life and annuity products and guarantees (details below) |
| Life & annuity | **US 360 Life & Annuity** | Modern US library used for LDTI and PBR [UNVERIFIED detailed scope] |
| Life & annuity | **Financial Services** | Banking products: mutual funds, mortgages (with prepayment), credit cards, deposits |
| Health | **US Health** | DI, LTC, CI, Life-LTC combos; multi-state incidence and termination; Monte Carlo decrements; stat net level/FPT/2-yr FPT; PDR; GAAP |
| Health | **Permanent Health Insurance** | UK-style income protection |
| Health | **BUZ** | German disability rider using DAV tables |
| Risk management | **ALS** | Stochastic ALM, assets, management actions, dynamic policyholder behaviour. "Licensed by over 270 customer sites" |
| Risk management | **Proxy Fitting** | Replicating portfolios with non-linear and custom constraints. LSMC/curve fitting with stepwise regression |
| Accounting | **IFRS 17 Group Calculations** | CSM, GMM/VFA/PAA, loss component, OCI, transition. "Adopted at over 100 sites" [UNVERIFIED] |
| GI | **GI Capital Modelling** | Monte Carlo and Latin Hypercube, copulas; UK, SII, SAM and US capital |
| GI | **GI Reserving** | Development factors, Mack, Merz-Wüthrich, stochastic reserving |

- **Example models** include an "Example IFRS 17 and Solvency Capital Model" and a Deutsche Library Solvency II prototype.
- **No separate libraries were found** for with-profits, takaful, reinsurance, group risk, or Asia-specific markets. These are handled by customising other libraries [UNVERIFIED that none exist].

**Product details by library**
- **Conventional:**
  - Products: whole life, endowment, term, LCE, annuities, income bonds, with-profit and non-profit, GAOs, CI, joint lives, increasing benefits.
  - Experience: AIDS mortality, skewed withdrawals, stochastic decrements, five-component investment return, tax.
  - Valuation: market-consistent, multiple bases, GPV, bonus reserve, DAC, resilience basis.
  - Reinsurance: co-insurance, YRT, financing.
  - Other: asset shares, rebasing, US GAAP module (FAS 60/97/120, Purchase GAAP, SOP 03-1), analysis of movement.
- **US Library:**
  - Products: traditional life, UL (flexible/fixed premium), IUL, ISWL, VUL, EIA/FIA, fixed/variable deferred and immediate annuities.
  - Guarantees: GMDB/GMAB/GMIB/GMWB/GLWB.
  - Participating: dividend options.
  - Reserves: stat, deficiency and tax.
  - GAAP: FAS 60/97/120/133.
  - Reinsurance: YRT, co, modco.
  - Designed for "fully dynamic" runs with ALS.
- **VA modules:**
  - Guarantees: GMDB (6 types), GMWB (including lifetime), GMAB, GMIB.
  - Multi-fund with transfers.
  - Guarantee reserves as % of fund, discounted cost less charges, or CTE.
  - **Delta and Gamma** Greeks, current and projected through Nested Structures.
  - Inner stochastic loops.
- **Group Pensions:**
  - Members: active, deferred, pensioner, spouse, ill-health, disabled.
  - Funding methods: 65-minus-X, projected unit, current unit, and others.
  - Supports Dutch AOP/WAO-gap and bulk-annuity scheme transfers.

**With-profits detail (UK/Asian/Indian par)** [R46, R5] [ALS internals partly UNVERIFIED]
- **Liability libraries** provide:
  - historic and future **asset shares**
  - bonus reserve valuation
  - goal-seeking of "self-supporting" reversionary/terminal bonus rates
  - GAOs
  - cash bonuses
- **ALS** provides the dynamic, scenario-dependent management actions:
  - bonus declaration rules
  - **equity backing ratio** changes
  - **smoothing** of payouts (`MAT_SMOOTHING` table)
  - charges for guarantees (the ALS mechanics in this list are inferred from ALS configuration-table names and are not documented behaviour)
  - resilience/reserving bases (`RESILIENCE`, `RESERVING_BASES` tables)
  - surrender penalties (`SURR_PEN`)
- **Market-consistent TVOG.** Valued stochastically over risk-neutral scenarios.
- **India.** Indian insurers use Prophet for policy-level asset shares on par business.

**Reinsurance.** Each liability library includes treaty mechanics:
- original terms or co-insurance
- risk premium/YRT
- modified coinsurance (US)
- financing treaties

IFRS 17 reinsurance held is supported in the Group Calcs library. **Aggregate treaties** (stop-loss, surplus by retention across policies) need accumulation- or ALS-level logic. No dedicated reinsurance library was found.

**GI line.** The Insurance Risk Suite GI Edition covers P&C:
- reserving: chain-ladder/development factors, Mack, Merz-Wüthrich, stochastic
- capital modelling: Monte Carlo, Latin Hypercube, copulas; UK, SII, SAM and US
- IFRS 17 BBA/PAA for short-term business
- the "Prophet Forms" UI

Composite insurers value having life and GI on one vendor. The Meridian spec sets GI **out of scope** at launch (§20.1).

### 7.2 Library mechanics that matter for a competitor
- **Indicator-driven conditional compilation** keeps one library serving many products.
- **"Dynamic features"** in every liability library let any assumption be fed from an ALM product's previous loop. This is the hook for full ALM.
- **Common outputs:**
  - discounted profits at three rates
  - IRR and breakeven month
  - discounted revenue accounts
  - analysis of surplus
- **Library upgrades are painful.** Customers fork libraries, create global variants such as MetLife's, and merge each FIS release [R23].

---

## 8. Accounting, regulatory and management applications

| Framework | Prophet support (evidence) |
|---|---|
| **IFRS 17** | Liability libraries produce cash flows, discounting and RA. The **Group Calculations library** does CSM (GMM, VFA), PAA, loss component and reinstatement, insurance revenue/expense, finance income/expense with OCI disaggregation, analysis-of-change disclosures, initial recognition, and full/modified retrospective transition. CSM state is carried via IMP output. IFRS 17 forecasting uses nested structures. Data flows through IDR to the Insurance Accounting Subledger. There is reinsurance-held support, and GI covers BBA/PAA. **The Group Calcs library can run standalone on externally produced cash flows.** FIS can therefore keep the IFRS 17 layer even if a customer moves its projection engine elsewhere, and the reverse also holds. The **IFRS 17 Toolkit** is a template end-to-end model and process: data sourcing, calculations, ledger population and IFRS 17 projection for planning. Awards: Asia Risk IFRS 17 Solution of the Year 2021 and 2022 [R10, R11, R47]. *Not found:* coverage-unit options and RA method detail |
| **US GAAP pre-LDTI** | FAS 60 (seriatim), FAS 97 (cohort), FAS 120, FAS 133 embedded derivatives, SOP 03-1, DAC/UREV unlocking projections via nested structures [R48] |
| **US GAAP LDTI** | Cohort LFPB, DPL, DAC/SIA/URR at cohort and seriatim level, MRBs. Delivered in the US 360 and US Health libraries. InsuranceERM LDTI Solution of the Year 2020 and 2022 (Moody's won 2024–26) [R48]. *Not found:* NPR cap, discount-rate OCI mechanics, MRB own-credit split detail |
| **US Statutory / PBR** | VM-20 NPR, DR and SR in one run; on-the-fly grouping; allocation of excess reserves to policies; projected VM-20 reserves. VM-21 via ALS with seriatim and grouped CTE. VM-22 claimed [UNVERIFIED]. VA RBC (C-3 Phase II) [inferred]. CFT and dynamic solvency testing. Glean for credibility assumptions [R42]. *Not confirmed:* AG38, AG49-A, AG53, C-3 Phase I, NAIC GOES integration |
| **Solvency II / Solvency UK** | BEL deterministic or stochastic. SCR stresses on multiple bases or modules. **ALS + Summary libraries compute SCR, MCR and Risk Margin via nested structures.** Projected SII balance sheet with management actions (ORSA/FLAOR). Proxy Fitting for internal models [R49]. *Not confirmed:* Matching Adjustment / fundamental spread, Solvency UK reforms |
| **Bermuda** | EBS/BSCR projections at reinsurers such as Martello Re, using ALS. No packaged SBA library found |
| **Asia** | K-ICS (Korea, top life insurer), HK RBC, Singapore RBC2 and China C-ROSS (Guomin Pension) appear in job ads and cases. India: asset shares and with-profits. IRDAI uses Prophet for product vetting [R50] |
| **Other** | SAM (South Africa). AASB 17 (TAL, Australia). *Not found:* LICAT, J-ICS/ESR, IAIS ICS, LAGIC |
| **Embedded value** | Traditional EV, EEV and MCEV; VNB; analysis of EV movement; appraisal value |
| **Pricing and profit testing** | Profit signatures, IRR, breakeven, goal-seeking premiums, NB profiles |
| **Planning / ORSA** | Business projections, projected balance sheets under stress |
| **Hedging** | "Single-model hedging": current and projected Greeks from the same VA model |
| **Economic capital / proxy** | Replicating portfolios, LSMC, curve fitting; Maths Plugin copulas for aggregation |
| **ESG** | **No in-house ESG.** Reads external scenario files. Formal **Conning GEMS** integration (2018). Moody's ESG consumed by file. NAIC GOES (Conning-built) consumed as tables [UNVERIFIED] |
| **Tax** | US tax reserves are in the US library. Tax "on several bases" (e.g. UK I-E) is in Conventional. Deferred tax for SII/IFRS balance sheets sits typically in ALS/Summary or downstream [UNVERIFIED detail] |
| **Climate / ORSA scenarios** | No packaged climate library found. Climate stresses are run as deterministic or stochastic scenario sets through the standard machinery |

**US regulatory dates (for urgency).**
- **VM-22** (non-variable annuities) was adopted with an effective date of **1 Jan 2026**. It is optional during a three-year transition and mandatory for new business from **1 Jan 2029**.
- **NAIC GOES** replaces the AAA/Academy generator. Sources conflict on timing: Moody's says it is required from 1 Jan 2026, while NAIC LATF and C-3 materials (2026) point to a **2027 Valuation Manual** effective date and year-end 2027 for VM-20/21 and C-3. GOES was out for comment until 28 Aug 2026 [R65]. **Treat the GOES effective date as 2027 (to be confirmed).**

---

## 9. Results, reporting and integration

- **Output granularity.** Base output is per SPCODE plus total. Cumulative variables are summed within an SPCODE. **Flexible Results**, a paid add-on, allows arbitrary grouping and writes to a distributed database [R26].
- **Results pipeline.** Results flow from Enterprise Manager through SQL Connector (PRD, SQL Server staging) to Data Repository (IDR). IDR has dimension and variable mappings in XML, percentiles, a strategy-name mapping, and an Excel pivot or ledger feed. IDR supports SQL Server and Oracle.
- **Excel.** Excel Reporting add-in and templates (income statement, balance sheet, disclosures). Practitioners extract results to Excel via a plug-in.
- **Automation.**
  - **PP & PE API** (the "Automating Prophet" training course covers DCS, multiple runs, the API and reporting).
  - Batch files.
  - **Process Orchestrator REST** (2022+).
  - PCC/Process Manager workflows: timers, file detection, launching jobs, downloading results, starting ETL, publishing reports, requesting re-runs.
- **Gaps.**
  - No public evidence of a native Python API or Python model authoring.
  - No Snowflake or Databricks connectors.
  - No published Moody's ESG integration.
  - Users bolt on Alteryx, Python (`mpfi`, `mpduck`), Git and SQL [R39, R51].

---

## 10. Governance, controls and security

- **FIS's governance principles:**
  - separate data from calculation
  - review and approve inputs
  - generate results only from verified inputs
  - keep a versioned, secured, auditable repository
  - automate traceability
  - log, review, reject and approve each step [R27]
- **Mechanisms:**
  - Enterprise Manager roles: Modelling Actuary, Modelling Approver, Modelling Execution
  - locked-down production
  - Assumptions Manager entry/approval
  - Process Manager electronic approvals and history
  - IDR audit trail and change control
  - auditor Diagram View
  - PQA regression testing
  - "backup and version control"
- **Customer practice.** Customers layer their own governance on top: coding standards, change logs per release, separate test and production environments, owner/developer segregation, model merges, staging, UAT and regression [R26, R23].
- **Gaps.**
  - No evidence of native **Git** integration [UNVERIFIED, inferred from absence].
  - Job ads increasingly pair Prophet with Git, Azure DevOps, Python and Snowflake.
  - The SOA (2026) argues for Git-based actuarial version control to replace "shared drives, file names, and Excel changelog tabs" [R52].
- **Standards context.**
  - **ASOP 56** (Modeling, effective 2020) and Section 3.4 reliance on models developed by others raise the bar on understanding vendor code.
  - SOX controls apply to US filers and IFRS 17 reporting.
- **Vendor support model (comparator for §32.3).** The FIS Prophet Helpdesk is reached through a client portal, email (Prophet.CX.Support@fisglobal.com) and phone. Training courses are offered (e.g. "Automating Prophet", PRD/IDR, ALS modular). Standard support covers the current version and the two before it. FIS consultancy offers model builds and reviews. No regional support-centre list or published severity/response SLAs were found [R21, R15].
- **Cloud security (PMCS):**
  - AWS/Azure private networks
  - leased line, VPN or firewall-controlled internet access
  - encryption at rest and in transit
  - annual pen tests and **SOC 2 Type 2**
  - multiple snapshots per day plus daily backups
  - 90-day access recertification [R25]

---

## 11. Deployment, cloud and AI

### 11.1 Deployment options (2026)
1. On-premise desktop (Model Developer) plus on-premise grid (Enterprise Manager, Windows or Linux workers).
2. **Managed Cloud Services** (FIS-hosted on AWS or Azure). There were 25 sites by 2017, including AIA on Azure. A large UK insurer moved from about 1,000 to about 5,000 cores, and FIS claims **40–50% savings** [R53].
3. **SaaS**: Production Manager (2024) and Model Developer (2025) on AWS. An FIS DevOps job ad describes the architecture as a single web interface over microservices in Docker containers [R54, UNVERIFIED by an official source]. A "One Cloud" bundle combines SaaS and managed cloud [R16].

**Critique.** Practitioners note that most actuarial platforms are "effectively just re-hosted from on-premise data centres to cloud data centres", which has been "one massive cost increase" for some insurers [R55].

### 11.2 AI
- **Insurance Risk Suite AI Assistant** (23 Feb 2026) [R18]:
  - Answers questions about building, operating and maintaining models, "in any language", 24/7.
  - Planned capabilities: code writing and improvement, automated documentation, run descriptions, and explanations of calculations and errors.
  - The LLM provider and hosting are not disclosed.
  - It won InsuranceERM 2026 Americas "Best Use of AI in Risk Management" [R19].
- **Competitor comparison.** Moody's AXIS Navigator (2025) is included in maintenance. WTW launched an **agentic** assistant (Oct 2026) that plans migrations, builds models, runs regression tests and drafts review evidence [R56].

---

## 12. Commercial model, pricing and total cost of ownership

- **No public price list.** Prophet is quote-only, and no public tender with a contract value was found [R57].
- **Licence components (inferred from product structure):**
  - Model Developer seats
  - Enterprise Manager production environment (cores or workers)
  - individually licensed libraries
  - add-ons (Flexible Results, IDR, Process Manager/Orchestrator, Assumptions Manager, Glean, PQA)
  - annual maintenance and support
- **Managed cloud.** A monthly **per-user fee** including one upgrade a year, plus **pay-per-use compute**. Enterprise Manager is marketed with "pay-for-use pricing" [R58].
- **Consultancy licences.** Consultancies license Prophet and are accredited by FIS.
- **Estimated spend** [UNVERIFIED, industry hearsay, to be validated through interviews]:
  - Desktop seats in the low tens of thousands of USD/GBP per seat per year.
  - A mid-to-large life insurer spends from mid six figures to low seven figures USD a year on licences, libraries, grid and maintenance.
  - Tier-1 multinationals spend more.
- **TCO structure, by FIS's own account** (InsuranceERM 2025 special report [R55]). The source chart's labels were scrambled in PDF extraction, so the label-to-value mapping below is **partly UNVERIFIED**. The "people ≥60%" and "compute 5–10%" figures are stated in the text and are firm:

| Cost element | Share of TCO |
|---|---|
| People (actuaries, IT) | ~60% |
| Vendor subscription | ~20% |
| Compute | ~5–10% |
| Data/results management | ~5% |
| Consulting/training | ~5% |

  **Implication:** the economic prize is people productivity, not licence price.
- **Implementation timescales.** Full implementation takes 6–18 months, and migration 12–24 months [UNVERIFIED buyer guides]. Rebuilding a single model takes about 3–12 actuary-months (Montoux/AWS) [R59].
- **Contractor market.** UK Prophet contractors charge **£700–900/day**, and Irish contractors €650–800/day [R60].
- **Procurement patterns.**
  - Large public-sector or state-owned insurers procure through formal RFPs. LIC of India issued a "Global RFP for Integrated Suite of Actuarial Software for Life Insurance with Managed Cloud Services" (Nov 2020), and India Post issued an "Procurement of Actuarial Software" EOI (Dec 2025).
  - Private insurers typically run 6–12-month selection processes with proofs of concept.
  - Contracts usually run multi-year (3–5 years) with renewal windows. These windows are the realistic switching points [R57] [contract terms UNVERIFIED].

---

## 13. Market, customers and ecosystem

### 13.1 Scale claims over time

| Date | Claim |
|---|---|
| 2005 | >5,000 users, 500 companies, >50 countries |
| 2015 | 9,000+ users, 730+ sites, 65+ countries |
| 2017 | 9,000–10,000+ users, ~1,000 sites (one slide says 1,500+), >70 countries; >50% share in Indonesia |
| 2024–26 | 10,000+ users, 850+ sites, 65+ countries (prophet-web); "~80% of top 50 insurers, >90 countries" (product sheet); "used by over 1,000 insurers" (2026 job ad) |

Sources: [R1, R21, R57]. The user count has plateaued at about 10,000 since 2017, and site counts appear to have fallen. The decline may be a definitional change [UNVERIFIED].

### 13.2 Geography
- **Strongholds.** UK, Europe (including DACH via German/BUZ libraries), South Africa, Australia/NZ ("the default choice"), Hong Kong ("the largest Prophet user group globally"), Korea, Taiwan, SE Asia (Indonesia, Malaysia, Thailand, Philippines), India and China.
- **Weaker in the US/Canada.** AXIS and MG-ALFA lead there (SOA/Oliver Wyman 2021, 40+ US companies) [R45].
- **2026 user group meetings** give a footprint signal: Cologne, Warsaw, Jacksonville, Mumbai, Hong Kong, Jakarta, Seoul, Johannesburg, Taipei, Netherlands, London [R21].

### 13.3 Named users (public)
- **UK/Europe:** Zurich; Vienna Insurance Group; Legal & General; Vitality UK; Generali Hellas; a large UK life insurer (PMCS case).
- **Australia:** TAL/Asteron.
- **Asia:** AIA (cloud, on Azure via PMCS); KB Insurance; Shinhan Life; a top Korean life insurer; Thai Life; Ocean Life; AmMetLife and AmMetLife Takaful; Takaful IKHLAS; Insular Life; Avrist; Guomin Pension; Prudential plc (Malaysia); FWD; AXA Asia; China Taiping; Aviva India; Kotak Life.
- **Middle East:** SAICO.
- **Americas:** New York Life (PBR, 2014); Pacific Life; MetLife (global Prophet coding standards); Martello Re (Bermuda); Porto Seguro (Brazil).
- **Lower-confidence users** (based on job-mention counts that may be inflated by Meta's "Prophet"): RGA and SCOR (French reinsurer, global). Brighthouse is cited only via a job-ad snippet.
- **Regulator use:** IRDAI (India) licensed Prophet for product vetting around 2011. Its current status is unknown.

Sources: [R50, R57].

### 13.4 Ecosystem
- **Training.**
  - FIS courses, e.g. "Automating Prophet", PRD/IDR and ALS modular.
  - University modules at Kent (MACT7820/7821), SMU, Thai universities, and EY + Nankai.
  - FIS graduate programs.
  - **No individual user certification.** FIS accredits consultancies instead [R57].
- **Consultancies.** Oliver Wyman ("Profiting from Prophet" newsletter), Milliman, Deloitte (modelling centres in Poland and Romania), PwC, EY, KPMG, Finalyse, ARKA, ActBuilder, ARC, WNS, Birlasoft, Brockhaus.
- **Offshore hubs.** India (Noida, Bengaluru, Gurugram, Pune), Malaysia (KL), Slovakia, Poland.
- **Talent market.**
  - Ads ask for 4–10+ years of experience, and Martello Re calls Prophet expertise "non-negotiable".
  - US Pacific Life Prophet developer bands are about $105–199k.
  - Skills do not transfer outside Prophet, while graduates arrive knowing Python [R60].
  - **Talent-pool sizing.** About **4,700 actuarial job ads (about 7.4% of actuary job ads)** in one technographic dataset mention Prophet. The same dataset counts *organisations* mentioning each tool, which is a different measure: Prophet about 6,900 (inflated by Meta's "Prophet"), MoSes about 2,500, AXIS about 2,500 and MG-ALFA about 400. These figures are noisy but directional [R68].
- **Awards and analyst standing** (a counterweight to the "legacy" narrative):
  - Risk.net actuarial modelling software awards in 2011, 2013 and 2015.
  - InsuranceERM best actuarial modelling in 2016, 2017, 2018/19, 2021, 2022, 2024 and 2025, LDTI solution in 2020 and 2022, and Best Use of AI in 2026.
  - Asia Risk IFRS 17 Solution of the Year in 2021 and 2022.
  - Chartis RiskTech100 #1 overall for seven years to 2021, and Chartis IFRS 17/LDTI category leader in 2020 [R19, R66].

### 13.5 Market size
- **Estimates.** Third-party figures for "actuarial modelling software" range from **US$1.9bn to US$2.7bn (2025)**, with 6.9–12.5% CAGR. These are low-quality, mutually inconsistent reports [R61].
- **Drivers:**
  - IFRS 17 (Asia wave)
  - LDTI and PBR (US), with VM-22 effective 1 Jan 2026 (optional three-year transition, mandatory for new business 2029) and NAIC GOES expected in 2027
  - Ind AS 117 and Indian RBC
  - cloud migration
  - GPU
  - AI
  - climate stress testing
  - model risk regulation

---

## 14. Competitive landscape

| Product | Owner (2026) | Authoring model | Deployment | GPU | AI | Core markets | Notes |
|---|---|---|---|---|---|---|---|
| **FIS Prophet** | FIS | Proprietary C-like DSL + open-code libraries | Desktop/grid, managed cloud, SaaS (AWS) | Preview/looped modules | AI Assistant (2026) | UK, Europe, APAC, India, Africa, LatAm | Largest installed base |
| **Moody's AXIS** | Moody's (not sold) | Vendor-maintained "core model chassis" configured by formula tables + custom code | Installed or **AXIS Cloud** (GridLink, REST, SOC1/2) | Not advertised | **AXIS Navigator** (2025); agentic planned | North America, Bermuda; growing in Asia (Funde Sino Life) | 200+ insurers; strong PBR/reinsurance; Moody's ESG integrated; RiskIntegrity IFRS 17/LDTI |
| **WTW RiskAgility FM** | WTW (not sold) | Open modelling language (.NET-based [UNVERIFIED]) + templates; successor to MoSes | Self-managed, vGrid burst (Azure), hosted vPlace | **Yes (Jun 2026)**, "up to 100× cost savings" | **Agentic AI assistant (Oct 2026)** | UK, Europe, Asia (60+ clients), US | VM-22 US library 2026; Unify workflow; consulting-backed |
| **Milliman MG-ALFA / Integrate** | Milliman | Vendor code visible/modifiable | **Integrate** SaaS on Azure (first actuarial cloud, ~2011) | Consulting builds | — | US, Japan, Korea, LatAm, UK | Phoenix, Royal London, BrasilPrev; strong ALM |
| **Milliman Mind** | Milliman | No-code Excel to cloud | SaaS (Azure) | — | — | UK, Europe, APAC | Spreadsheet industrialisation |
| **Aon PathWise** | Aon | Spreadsheet-like Modelling Studio + Python Analytics Studio | Cloud GPU | **Native since 2011** | — | US/UK PRT, VA hedging, Korea, India, Canada | Vendor claims "1000× faster, 100× cheaper"; ICICI Prudential (Feb 2026), Kyobo |
| **Akur8 Life (ex-Slope)** | Akur8 (Mar 2026) | Browser low-code | Pure SaaS | — | Akur8 ML | US mid-market L&A | Modern UX; small |
| **Mo.net** | Software Alliance (UK) | .NET studio; Git/Azure DevOps CI; auto-docs | On-prem / Azure | — | "Codepilot" | UK, Malaysia (Takaful), US | Best DevOps practices; "one calc engine" for valuation, illustrations and admin |
| **RNA R³S** | RNA Analytics (UK/Korea) | ex-IBM Algo Financial Modeler | — | — | — | Korea, UK | 100+ customers claimed |
| **SAS Dynamic Actuarial Modeling** | SAS | — | — | — | — | — | Chartis 2022 leader |
| **lifelib/modelx, Heavylight** | Open source (MIT) | Python, formula-per-variable | Anywhere | DIY (NumPy/JAX/Numba) | DIY | Global individuals | Git-native; no support/libraries/governance |
| **Coherent Spark** | Coherent | Excel to API | SaaS (AWS) | — | — | Asia, US | Pricing/illustration deployment, not valuation |
| **In-house Python/C++/GPU** | Insurers | Code | Any | Yes | DIY | Large insurers/reinsurers | The real top-end competitor |

**Competitor-by-competitor: better or worse than Prophet**

| Competitor | Better than Prophet | Worse than Prophet | Pricing model (known) |
|---|---|---|---|
| Moody's AXIS | Less build effort (vendor-maintained chassis); one model across bases; US PBR and reinsurance pedigree; ESG, credit and RiskIntegrity from one vendor; Navigator included in maintenance | Less freedom for non-standard products; enhancements wait on the vendor release cycle; smaller presence outside North America | Licence + maintenance; AXIS Cloud managed service |
| WTW RAFM | CPU/GPU choice; burst pay-as-you-go cloud (vGrid); most advanced agentic AI; open language and code-analysis tools | Smaller installed base; MoSes migration overhang; vendor is also a consultancy (possible conflict) | Licence + pay-as-you-go cloud compute |
| Milliman MG-ALFA / Integrate | Most mature fully managed SaaS operating model; transparent, modifiable vendor code; strong US ALM | Smaller outside the US, Japan, Korea and LatAm; vendor also a consultancy | SaaS bundle (infrastructure + software + operations) [UNVERIFIED] |
| Aon PathWise | Order-of-magnitude speed (GPU-native); low run cost; Python analytics | GPU-efficient modelling needs specialist skill; GPU memory limits; smaller base | [UNVERIFIED] |
| Akur8 Life (Slope) | Modern browser UX; no infrastructure | Young; limited libraries outside the US; new P&C-led owner | SaaS |
| Mo.net | Git/CI/DevOps tooling; deploy the same calc engine to illustrations and admin | Small vendor; limited libraries and talent | Licence |
| PolySystems (Chicago, est. 1970) | Long-standing US valuation, projection and experience-study niche | Legacy; US-only | Licence |
| Addactis (France) | SaaS Solvency II / IFRS 17 for mid-size European insurers | Not a deep life projection engine | SaaS |
| In-house Python/GPU | Total control; no licence; modern talent | Must build libraries, governance and support; key-person risk | Internal cost |

- **Adjacent products.**
  - **IFRS 17/LDTI subledgers and engines:** FIS Insurance Accounting Suite, Moody's RiskIntegrity, SAP FPSL, Aptitude, Wolters Kluwer OneSumX, SAS, Oracle, Legerity.
  - **ESGs:** Conning GEMS (basis of **NAIC GOES**), Moody's ESG (ex-B&H), Ortec.
  - **P&C:** WTW ResQ/Igloo/Radar, Milliman Arius.
- **Market share.** No independent source quantifies it. The best summary: *Prophet has the largest global installed base and dominates the UK, Europe, Asia and India. AXIS and MG-ALFA lead in the US and Canada. RAFM is a strong number two in the UK, Europe and Asia. GPU-native PathWise and SaaS entrants are the disruptors* [R45, R56, R62].
- **Battlegrounds in 2026:**
  1. GPU performance
  2. agentic AI
  3. managed SaaS with burst compute
  4. migration tooling ("bring your models without re-engineering")
  5. software-engineering practice (Git, CI)
  6. new regimes: VM-22, Ind AS 117/IRBCF, K-ICS, NAIC GOES

---

# PART II: SPECIFICATION FOR THE COMPETING PLATFORM

Working name: **"Meridian"** (placeholder).

## 15. Prophet strengths and weaknesses (gap analysis)

| # | Prophet strength (must match) | Meridian response |
|---|---|---|
| S1 | Deep, regulator-current libraries (IFRS 17, LDTI, PBR, SII, ALS, VA) | Ship credible open-source-style reference libraries; prioritise by target market (section 20) |
| S2 | Indicator-driven product configuration; "same as" products | Feature-flag/trait system with composable product definitions |
| S3 | Nested structures, dynamic ALM, calculation loops | First-class nested and dynamic execution graph |
| S4 | Model-point paradigm (seriatim or grouped), SPCODE grouping | Seriatim-first with arbitrary dimensional aggregation built in at no extra cost |
| S5 | End-to-end chain (data, assumptions, runs, results, subledger) | Integrated platform with open interfaces at every stage |
| S6 | Massive talent pool, training, consultancy ecosystem | Python-based skills, university program, certification, partner program, Prophet-to-Meridian training |
| S7 | Proven at scale in 65+ countries; regulator acceptance | Validation packs, independent benchmarks, reference customers |

| # | Prophet weakness (evidence) | Meridian improvement |
|---|---|---|
| W1 | Proprietary DSL; UDF limits (9 params, 250 lines, 4-D arrays) [R32] | Python-embedded DSL with no arbitrary limits; standard tooling |
| W2 | Hard debugging; extended-formula internals hidden; Excel side-models for validation [R26, R36] | Full-fidelity trace of every value incl. inside functions; single-policy "explain" view; time-travel debugger |
| W3 | No native Git; governance by manual process [R52] | Git-native plain-text models, PR review, CI, semantic model diff |
| W4 | C++ compiler dependency; Windows desktop heritage | Self-contained JIT/AOT engine; browser IDE plus local VS Code extension; Linux/containers |
| W5 | Many separately versioned bolt-on components | One platform, one version, modular licensing |
| W6 | Flexible result grouping is a paid add-on (Flexible Results); base output groups only by SPCODE | Arbitrary dimensions/tags on every result, included |
| W7 | Proprietary file formats; TB output volumes [R38, R39] | Parquet/Arrow columnar outputs; output-on-demand; lineage-aware storage |
| W8 | GPU requires restructuring models into "looped modules" [R44] | One source compiles to vectorised CPU and GPU. Documented GPU constraints (branch divergence, memory per policy-scenario, path-dependent loops), a GPU-suitability linter, and automatic CPU fallback for non-conforming variables. Not a "no-effort" promise |
| W9 | Cloud = re-hosting, surprise bills [R55] | Cloud-native elastic compute, cost estimation before run, budgets/caps |
| W10 | Opaque pricing; per-library licensing; paid add-ons | Transparent published pricing tiers |
| W11 | Lock-in, code ownership dispute (FIS v. Montoux) [R63] | Contractual customer ownership of models, open format, free export, no training on customer code |
| W12 | Library upgrade merges are costly [R23] | Libraries as versioned packages with semantic versioning, override layers and automated merge/impact reports |
| W13 | Thin, expensive talent pool | Python skills; AI pair-programmer; built-in learning |
| W14 | Only now adding AI; documentation Q&A first | Agentic AI across build, test, explain, migrate and review, with governance |
| W15 | Data plumbing via DCS; customers replace with Alteryx/Python | Native data pipelines with SQL/Python, connectors (Snowflake, Databricks, S3, ADLS) |
| W16 | Ownership uncertainty (FIS Aug 2026 review) | Stability message: escrow, open formats, long-term support commitments |
| W17 | Models cannot readily be deployed as live calculation services (quotes, illustrations, admin) | "Model-as-API": the same governed model is published as a low-latency service (§21, D-11) |
| W18 | Multi-currency/multi-entity handling undocumented and done downstream | First-class currency and entity dimensions, FX scenarios and consolidation (§20.7) |
| W19 | Percentiles/CTEs computed downstream (IDR/Excel) | Native stochastic statistics in the engine and results store |

---

## 16. Product vision, positioning and design principles

**Vision.** Meridian is the open, cloud-native actuarial modelling platform. Actuaries write transparent models in a modern language, run them at any scale on CPU or GPU, explain every number, and govern everything like professional software, all without vendor lock-in.

**Positioning statement.** Meridian is for life, annuity, health and pensions insurers and reinsurers frustrated by legacy proprietary platforms. It brings software-engineering-grade transparency and governance, plus the actuarial depth each target market needs (US first, then UK/EU, then Asia; see §27.3). Targets are **≥3× faster CPU runs and ≥20× faster GPU stochastic/nested runs** at equal hardware cost, and a **30–40% lower total cost of ownership** (50% stretch), driven mainly by actuary productivity (§27.1). Unlike Prophet, models are customer-owned open code, debugging is first-class, and the cloud is native rather than re-hosted. Full Prophet-breadth parity across all regions is a 3-year goal, not a launch claim.

**Design principles**
1. **Transparency by default.** Every number is traceable to its inputs and formula, at any time step, for any policy and scenario.
2. **Open and owned.** Models are plain text in a documented language, and data is in open formats (Parquet, Arrow, CSV, JSON). Customers own their code. Free export is guaranteed.
3. **One model, many engines.** A model definition compiles to CPU, vectorised CPU and GPU, local or cloud, from one source. Documented GPU constraints apply, and non-conforming logic falls back to CPU automatically.
4. **Governance as code.** Version control, review, approval, lineage and reproducibility are built in and cannot be bypassed in production.
5. **Actuary-first ergonomics.** It is as approachable as a spreadsheet for simple models and as powerful as code for complex ones.
6. **Composable content.** Libraries are packages that customers extend through override layers, never by forking.
7. **Cost-aware cloud.** Estimate the cost before running, and pay for what you use with caps.
8. **AI as a governed teammate.** AI drafts, explains, tests and migrates; humans approve; everything is logged.

---

## 17. Target users and personas

| Persona | Needs | Prophet pain |
|---|---|---|
| **Model developer actuary** | Write/modify product logic fast, debug, test | DSL limits, opaque extended formulas, compile cycle |
| **Valuation/reporting actuary** | Reliable quarterly close, analysis of change, explainability | Long runs, manual handoffs, Excel reconciliations |
| **Pricing actuary** | Fast iteration, profit testing, goal seek, many sensitivities | Run time limits scenario counts; slow cycle |
| **ALM/risk/capital actuary** | Stochastic & nested runs, proxy models, management actions | Runtime, ALS complexity |
| **Model governance / validation** | Lineage, change control, independent review. Evidence for ASOP 56, NAIC Model Audit Rule/SOX, Solvency II internal-model validation and model-change policy, and UK FRC TAS 100/200 | Process-based controls, no diff/review tooling |
| **Non-programmer actuary (Excel-centric)** | Build or adjust simple models without coding; trust outputs | Prophet's DSL is itself a barrier; a Python DSL could be worse. This persona needs the low-code layer (L-9) |
| **IT/platform engineer** | Deployability, security, integration, cost control | Windows/C++ dependencies, separate components |
| **Finance/accounting** | IFRS 17/LDTI numbers into GL, disclosures | Multi-hop pipeline (IDR, subledger) |
| **CRO/CFO/Chief Actuary** | Speed of insight, cost, risk of vendor | Opaque pricing, key-person risk |
| **Auditor/regulator** | Read-only explainability, reproducibility | Requires vendor tools and specialist knowledge |

---

## 18. Functional requirements: modelling language and model structure

**Priority key**
- **M** = required for **GA 1.0 (US)**.
- **M (region)** = required for that region's GA release: **GA-UK/EU** at M30, **GA-Asia** at M36.
- **S** = 1.x enhancement.
- **C** = later or optional.

The **MVP (design-partner release, M15)** is a strict subset of M, listed by ID in §27.3. A requirement's tag means "must be in this release", not "nice to have". Every M item is scheduled at or before GA in §27.3.

### 18.1 Language
| ID | Requirement | Pri |
|---|---|---|
| L-1 | Models are written in an **embedded Python DSL**: variables declared as functions of time and context (e.g. `@var def death_outgo(t): ...`). Recursion over `t`, and references to other variables at any lag | M |
| L-2 | Automatic dependency-graph resolution and cycle detection, with clear errors that name the cycle path | M |
| L-3 | The DSL compiles (via tracing/IR) to a vectorised kernel over **policies × scenarios × time**. Users write scalar-looking code, and the engine vectorises it | M |
| L-4 | Rich types: float64 (default and required for production/reconciliation), float32 (opt-in for exploratory GPU runs only, flagged in run manifests), int, bool, date, enum, string (non-time-varying), categorical; N-dimensional arrays with named axes (fund, benefit, state, duration) | M |
| L-5 | User-defined functions with **no arbitrary limits** on parameters, lines or array dimensions | M |
| L-6 | Procedural blocks (loops, conditionals) inside variables for complex logic such as rebasing or guarantee ratchets. Their internal state **remains traceable** (fixes Prophet's extended-formula opacity) | M |
| L-7 | Time granularity: monthly, quarterly and annual, with mixed granularity (monthly for first N years, then annual), plus fractional/mid-period timing conventions and day-count support | M |
| L-8 | Calendar and policy-time alignment: valuation date, policy anniversaries, and premium/benefit frequency handling | M |
| L-9 | Low-code layer: a spreadsheet-like grid/formula editor and a product-configuration wizard that generate the same DSL, round-trip safe. Serves non-programmer actuaries, who are a large share of today's roughly 10,000 Prophet users. Assumption-only changes must never need code | M |
| L-10 | Escape hatches: call vetted Python libraries (NumPy, SciPy) and compiled extensions, within sandbox rules | S |
| L-11 | Deterministic numerics: reproducible results bit-for-bit across runs on the same engine target. Documented tolerance across CPU and GPU | M |

### 18.2 Model structure
| ID | Requirement | Pri |
|---|---|---|
| MS-1 | **Traits/features** (the indicator equivalent): products are composed of traits. Variable definitions are selected by trait expressions, with mutual-exclusivity constraints validated at build time | M |
| MS-2 | Product inheritance and "same-as" variants, with explicit overrides that show in diffs | M |
| MS-3 | **Libraries as packages**: semantic versioning, dependency manifests, **override layers** (customer changes stored separately from vendor code), and an automated upgrade impact report listing changed variables, affected products and result deltas on test data. This addresses Prophet's merge pain | M |
| MS-4 | Modules/sub-models callable with parameters (e.g. reserve calculation on multiple bases, SCR shocks) | M |
| MS-5 | **Nested models**: an outer projection can invoke an inner model (deterministic or stochastic) at any projection time, with configurable inner scenario sets, grouping and caching | M |
| MS-6 | **Dynamic linkage**: any assumption can be bound to a value computed by a higher-level (ALM/company) model in the previous step | M |
| MS-7 | Multi-basis calculation in one run (best estimate, stat, GAAP, tax, IFRS 17, SII) without full recomputation (the calc-loop equivalent, but incremental) | M |
| MS-8 | Model documentation generated from docstrings, types and the dependency graph (HTML/PDF), always in sync with code | M |
| MS-9 | Model templates and wizards for common product types | S |
| MS-10 | **Semantic variable kinds** (the successor to Prophet's Accounting Type and Cumulative flag): *flow* (summed over time and policies), *stock/balance* (summed over policies, point-in-time over time), *rate/ratio* (never summed; recomputed from numerator and denominator on aggregation), *state* (per-policy, non-additive). Aggregation, AoC and reporting use these kinds automatically and reject invalid aggregation | M |
| MS-11 | **Units and currency typing**: monetary variables carry a currency. Mixing currencies without explicit conversion is a build error (see §20.7) | M |
| MS-12 | Global/run-level parameters (the Prophet "Global" successor) and run-number-like assumption sets, as named, versioned **assumption scenarios** | M |

### 18.3 Developer experience
| ID | Requirement | Pri |
|---|---|---|
| DX-1 | Browser IDE plus a **VS Code extension**, with syntax highlighting, autocomplete, go-to-definition, find-usages, refactoring and inline errors | M |
| DX-2 | **Interactive dependency graph** (Diagram View successor), including inside functions, with precedent/dependent filters and computed values overlaid | M |
| DX-3 | **Single-policy explain/trace**: pick a policy, scenario and time, and see every variable's value, its formula and the inputs used. Export to Excel for reconciliation | M |
| DX-4 | Time-travel debugger: breakpoints on variable/time/policy conditions, and step through procedural blocks | S |
| DX-5 | Sub-second incremental rebuild; run a single policy instantly during development (REPL/notebook) | M |
| DX-6 | Jupyter notebook integration: load a model, run, inspect and plot | M |
| DX-7 | Semantic model diff: compare two versions by variables, formulas, tables and results (on a test dataset) | M |
| DX-8 | Linting and model-quality rules (unused variables, shadowing, hard-coded constants, performance anti-patterns such as expensive table reads in hot loops) | S |

---

## 19. Functional requirements: engine, run types and performance

### 19.1 Run types
| ID | Requirement | Pri |
|---|---|---|
| R-1 | Deterministic projection, seriatim or grouped | M |
| R-2 | Stochastic projection over N scenarios (risk-neutral or real-world), with scenario-level and summary outputs (mean, percentiles, CTE-x) | M |
| R-3 | Nested stochastic (stochastic-on-stochastic), with inner-loop acceleration options (caching, grouping, proxy substitution) | M |
| R-4 | Dynamic ALM: period-by-period asset-liability interaction, management actions, dynamic policyholder behaviour | M |
| R-5 | Sensitivity and stress batches: declare a grid of assumption shocks, run in parallel, auto-produce comparison reports | M |
| R-6 | **Analysis of change / movement / attribution**, specified in §19.5 | M |
| R-7 | Goal seek / solve (premium for target IRR/profit margin, bonus rates, spreads, VM-20 DR/SR iterations), using vectorised root-finding | M |
| R-8 | On-the-fly grouping (seriatim outer, compressed inner) with configurable compression algorithms (clustering, k-means/representative policies), plus error reporting | S |
| R-9 | Rolling forward / roll-forward runs (prior period state, e.g. CSM, LDTI cohort balances), with persisted state stores | M |
| R-10 | Replicating portfolio and LSMC/curve fitting (proxy) workflows, with validation statistics | S |
| R-11 | Greeks by bump-and-revalue, and adjoint/automatic differentiation for sensitivities where supported (a GPU AD advantage) | C |
| R-12 | Experience studies (the Glean equivalent): A/E by dimension, credibility, GLM fitting, feeding the assumption store | S |

### 19.2 Engine and performance
| ID | Requirement | Pri |
|---|---|---|
| E-1 | One model source compiles to three targets: (a) scalar debug mode, (b) SIMD-vectorised multi-core CPU, (c) GPU (CUDA first, then ROCm). The GPU target has **documented constraints** (branch divergence, per-lane memory, unbounded procedural loops, large random-access table lookups). A **GPU-suitability linter** reports non-conforming variables, which fall back to CPU automatically in a hybrid plan. No separate model is maintained per target | M (a,b); M (c) at GA |
| E-2 | Distributed execution on Kubernetes, with elastic burst to thousands of cores or hundreds of GPUs. The partitioning strategy depends on the model's dependency class (§19.4): independent work is partitioned freely by policy or scenario, and time-synchronous models are partitioned by scenario with all policies co-resident | M |
| E-3 | **Performance targets**, on the §19.3 reference suite at equal hardware cost against a customer-run legacy baseline (§30.3): ≥3× on CPU at GA and ≥20× on GPU for stochastic/nested. The basis for the CPU gain is SIMD vectorisation across policies × scenarios, cache-friendly columnar state, elimination of file I/O between steps and lazy output materialisation, not raw scalar speed. Per-workload targets are in §30.2 | M |
| E-4 | Memory-efficient streaming: only requested outputs materialised; intermediate variables computed on demand for trace | M |
| E-5 | Checkpoint/restart of long runs; partial re-run of failed partitions | M |
| E-6 | Deterministic seeding and scenario-file versioning for reproducibility | M |
| E-7 | **Cost estimator**: before a run, estimate runtime and cloud cost; enforce budgets/caps per team/project | M |
| E-8 | Priority queues and SLAs for close-period production vs. ad-hoc dev runs | S |
| E-9 | Run on customer cloud (BYOC: AWS, Azure, GCP), vendor SaaS, or on-prem Kubernetes/Linux | M |

### 19.3 Reference benchmark suite
Meridian's own absolute timings are published. Comparisons with legacy platforms are customer-run only (§30.3).
- **B1:** term life seriatim, 5m policies, monthly over 60 years, deterministic, three bases.
- **B2:** ULSG/IUL, VM-20 NPR + DR + SR, 1,000 stochastic scenarios, 500k policies.
- **B3:** VA (GMWB/GMDB), 200k policies.
  - VM-21 CTE70 over 1,000 outer scenarios.
  - Projected hedge Greeks: delta and rho by central-difference bumps, i.e. 4 bumped inner valuations plus a base valuation. These run on **each of the 1,000 outer scenarios** at 12 annual nodes, with 100 risk-neutral inner paths per valuation.
- **B4:** bulk annuity book, 1m lives, SII BEL, standard-formula SCR shocks (about 15 stress runs) and MA fundamental-spread calculation.
- **B5:** UK with-profits, dynamic bonus/EBR/smoothing in time-synchronous mode, 2,000 risk-neutral scenarios, 300k policies.
- **B6:** IFRS 17 CSM roll-forward, 10k groups of contracts over 40 quarters, including AoC.
- **B7:** US fixed annuity asset adequacy (CFT), seven NY7 deterministic scenarios plus 1,000 GOES scenarios, with an asset portfolio of 5,000 CUSIPs.

### 19.4 Execution model: dependency classes and time-synchronous runs
Prophet's dynamic loop and IMD/IMS exist because many calculations couple policies together (§4.1b). The Meridian engine classifies each model, and each variable, automatically from the dependency graph into one of three classes:

| Class | Definition | Examples | Execution strategy |
|---|---|---|---|
| **C1: Policy-independent** | A policy's projection depends only on its own data, assumptions and scenario | Term/WL cash flows, NPR, seriatim GAAP | Fully parallel over policy × scenario; whole time path per lane; best GPU fit |
| **C2: Aggregate-feedback (time-synchronous)** | At time *t*, policy calculations need a company-, fund- or treaty-level value computed from **all** policies at *t* or *t−1* | ALM crediting/bonus rates, EBR, smoothing, management actions, aggregate stop-loss/surplus reinsurance, dynamic hedging, fund-level charges, group IFRS 17 coverage-unit allocation | **Lockstep time stepping**: compute all policies for step *t* (vectorised), then a **global reduction/barrier** (sums by fund, treaty or company), then company-level logic (asset projection, actions), then broadcast the results to policies for *t+1*. Partition by scenario across nodes; within a scenario, all policies are co-resident on one node or, for large books, sharded across nodes with a per-step allreduce |
| **C3: Nested** | At outer time *t*, an inner model (deterministic or stochastic) is run from the projected state | Future VM-20/21 reserves, projected SCR/risk margin, projected Greeks, IFRS 17 forecasting | The nested scheduler spawns inner batches from outer-state snapshots. Options: inner-path caching, inner grouping of policies, proxy (LSMC) substitution, adaptive inner path counts. Inner runs are themselves C1 or C2 |

- **Memory model.**
  - **C2 sizing.** C2 runs hold the per-policy state for every policy in a scenario partition: state variables × policies × float64. Example: 1m policies × 200 state variables × 8 bytes ≈ 1.6 GB per scenario lane.
  - **Scenario packing.** The scheduler packs scenarios per node (or GPU) to fit memory, and policies are streamed in blocks when the reduction is associative (sums, maxima).
  - **Large C2 books (cross-node partitioning within a scenario).** When one scenario's state exceeds a node or GPU, e.g. 10–50m policies × 200 state variables ≈ 16–80 GB, policies in that scenario are **sharded across nodes**. At each time step every shard computes partial reductions (sums by fund, treaty or company), and an **allreduce** (MPI/NCCL-style collective) combines them. The company-level logic runs once on the result, which is broadcast back before step *t+1*. The cost is one collective per time step per scenario (e.g. 720 monthly steps). Fallbacks if network latency dominates: an annual time step for the feedback loop, or a compressed feedback proxy (see below).
  - **Non-associative reductions** require full residency. Examples are sorting for CTE inside a step, and solving a fund-level crediting rate that needs all policies.
  - **Compression.** Policy compression (D-3) can be applied *only* to the C2 company feedback loop while keeping seriatim liability outputs. This mirrors Prophet's "flexing" and on-the-fly grouping.
- **Determinism.** Reductions use fixed-order (pairwise or Kahan) summation so that results are reproducible regardless of partitioning (supports L-11 and the §24 numerical NFR).
- **Liability approaches** (compatibility with Prophet ALS concepts): (a) *internal*, meaning liabilities run inside the C2 loop; (b) *external*, meaning pre-computed liability cash flows read from a prior run; (c) *flexed*, meaning pre-computed unit cash flows scaled by dynamically projected in-force. All three are required (M for GA), because (b) and (c) are major run-time optimisations.
- **Developer visibility.** The IDE shows each variable's class and explains why a variable became C2, e.g. "depends on `fund_bonus_rate`, which sums over policies". Developers can see how a model change moves it between performance classes.

### 19.5 Analysis of change (AoC) specification
| ID | Requirement | Pri |
|---|---|---|
| AOC-1 | Configurable, ordered step list, e.g.: opening position, then model/methodology changes, opening adjustments, data corrections, expected roll-forward (unwind), new business, experience variances (deaths, lapses, expenses, investment), non-economic assumption changes, economic assumption changes, FX, and closing. Steps are stored as versioned configuration | M |
| AOC-2 | Each step is an incremental run reusing cached results where unaffected (dependency-aware), so a 12-step AoC costs far less than 12 full runs | M |
| AOC-3 | **Cross-effect handling**: sequential (order-dependent) attribution by default, with optional symmetric/Shapley-style attribution and explicit "interaction" residual reporting | S |
| AOC-4 | **IFRS 17-specific AoC**: separate changes that adjust the CSM (future service: non-financial assumption changes measured at locked-in rates) from those that go to P&L (current/past service, experience adjustments) and to insurance finance income/expense (P&L vs OCI under the disaggregation option). Show the **locked-in vs current discount rate** effects. Track the loss component. Produce the LRC/LIC reconciliations and the measurement-component reconciliation (PV future cash flows, RA, CSM) **VFA branch:** changes in the entity's share of the fair value of underlying items, including financial changes, and changes in fulfilment cash flows not varying with underlying items, also adjust the CSM. Support the **risk-mitigation option** (paras B115–B118) that lets qualifying hedge effects go to P&L instead of the CSM. PAA groups show LRC/LIC movements only | M (EU/UK), M (Asia) |
| AOC-5 | **LDTI rollforward**: LFPB rollforward with the effect of updated cash-flow assumptions (retrospective NPR unlocking, with the NPR cap at 100%), actual-vs-expected variances, discount-rate remeasurement to OCI; MRB rollforward separating instrument-specific credit-risk changes to OCI; DAC rollforward | M |
| AOC-6 | **Solvency II / EV movement**: own funds/BEL/risk margin/SCR movement analysis; EV and VNB analysis of movement (unwind, NB, experience, assumption changes, economic variances) | M (EU/UK) |
| AOC-7 | Drill-down from any AoC bar to products, cohorts or groups, then to policies, then to a single-policy trace (DX-3) | M |
| AOC-8 | Auto-generated AoC commentary draft (AI-4) with the numbers linked to the trace | S |

### 19.6 Close-process SLAs
| ID | Requirement | Pri |
|---|---|---|
| CL-1 | Orchestrated quarter-close chain (data load and validation, BE cash flows, IFRS 17, local stat/GAAP, AoC, review, sign-off, publish) as a reusable DAG template | M |
| CL-2 | **SLA target**: for a reference mid-size insurer (5m policies, 20 products, IFRS 17 + US stat + LDTI, 12-step AoC), the full quarterly production chain completes in **≤ 8 wall-clock hours** at P95 on burst capacity. Today the survey baseline is "a few hours to an entire day" for the valuation run alone, before AoC | M |
| CL-3 | Capacity reservation for close windows (pre-booked burst quota with guaranteed start times); priority pre-emption of dev runs | M |
| CL-4 | Close dashboard: step status, critical path, ETA, cost to date vs budget, failures with AI diagnosis | M |
| CL-5 | Re-run of a single failed step or partition without invalidating sign-offs on unaffected outputs (lineage-aware) | M |

---

## 20. Functional requirements: actuarial content and regulatory libraries

### 20.1 Library strategy
- **Licensing.** Libraries ship as **source-visible packages**. Customers can read every line, override through layers, and contribute back (community edition plus a certified commercial edition).
- **Certification packs.** Each library has a **regulatory certification pack**: methodology document, test cases with independent expected values, a change log mapped to regulatory amendments, and a validation report for auditors.
- **Update SLA (LIB-1, M).** A beta implementation of a regulatory change ships within **3 months** of the final rule or adopted text (e.g. NAIC Valuation Manual adoption, IASB/FASB amendment, PRA policy statement). A certified release ships **no later than 3 months before the effective date** or within 6 months of final text, whichever is later. Errata get a 30-day patch SLA.
- **Library packaging (LIB-2, M).** Libraries are packages with semantic versions and dependency manifests, and customer override layers sit outside the vendor package. On every library upgrade, an automated **upgrade-impact report** lists changed variables, affected customer overrides (with three-way merge proposals) and result deltas on the customer's regression dataset.
- **Out of scope at launch (LIB-3).** P&C/GI reserving and capital (Prophet GI Edition), and banking products (Prophet Financial Services library).
  - Composite insurers keep GI where it is. Meridian provides IFRS 17 PAA/GMM ingestion of GI cash flows so the accounting layer can still be unified (S).
  - GI modelling is reconsidered after year 3.

### 20.2 Product coverage (liability)
| ID | Area | Products | Pri |
|---|---|---|---|
| PC-1 | Protection | Term (level/decreasing), whole life, endowment, riders, waiver | M |
| PC-2 | Protection (other) | CI (standalone/accelerated), DI/IP, funeral | M (EU/UK), M (Asia) |
| PC-3 | US participating | Par whole life with dividend scales and options (cash, premium reduction, accumulation, PUA) | M |
| PC-4 | UK/European with-profits | Reversionary/terminal bonus, asset shares, smoothing, EBR, guarantees/GAOs, PPFM-style management actions, inherited-estate/fund-level modelling (C2 class), German RfB-style participation | M (EU/UK) |
| PC-5 | Asian/Indian par | Cash dividends, reversionary bonus, policy-level asset shares, Indian 90/10 surplus distribution, HK/SG par with smoothing and dividend fulfilment ratios | M (Asia) |
| PC-6 | Unit-linked | Unit funds, unit and non-unit (sterling) reserves, charges, fund switches | M (EU/UK), M (Asia) |
| PC-7 | Variable annuity | GMxB (GMDB/GMAB/GMIB/GMWB/GLWB) with ratchets/roll-ups, multi-fund, dynamic utilisation | M |
| PC-8 | US interest-sensitive | UL, ULSG, IUL (index crediting, caps/floors/participation, AG49-A illustration support), VUL, ISWL | M |
| PC-9 | Annuities | SPIA, DIA, FDA (MYGA), FIA/RILA, structured settlements | M |
| PC-10 | Bulk annuities / PRT | Deferred and in-payment members, spouse benefits, longevity improvements, buy-in/buy-out, MA portfolio linkage | M (EU/UK); S (US PRT) |
| PC-11 | Health | LTC (multi-state), Life-LTC combo, medical, hospital cash, multi-state CI | S |
| PC-12 | Group | Group life, group IP/LTD, group pensions DB/DC | S |
| PC-13 | Islamic | Family takaful (participant risk fund, participant investment fund, wakalah/mudharabah fees, surplus sharing) | M (Asia) for Malaysia/Indonesia go-to-market; else S |
| PC-14 | Reinsurance (policy-level) | YRT, coinsurance, modco, funds withheld, quota share, surplus by retention; reinsurance held for IFRS 17 | M |
| PC-15 | Reinsurance (aggregate) | Stop-loss, catastrophe, aggregate XL, experience refunds (C2 class) | S |
| PC-16 | Banking/other | Credit life, mortgage protection | C |

### 20.3 Assumption and experience modelling
- **Mortality.** Tables (select/ultimate, 1-D/2-D, including VM-20 prescribed tables such as 2017 CSO and VBT); improvement scales (CMI_2024/latest CMI model, SOA MP-2021 and MIM-2021, plus custom 2-D scales); stochastic mortality (Lee-Carter, CBD) for longevity risk.
- **Lapse and behaviour.** Dynamic lapse and utilisation (ITM-based functions for VA/FIA), partial withdrawals, premium persistency, option exercise (GAO, annuitisation).
- **Morbidity.** Multi-state incidence/termination; claim-cost methods.
- **Expenses.** Per-policy, per-premium and per-claim; inflation; allocation; overhead and acquisition splits.
- **Economic.** Yield curves (Smith-Wilson, Nelson-Siegel), volatility adjustment, matching adjustment, ultimate forward rate, credit spreads, inflation.

### 20.4 Accounting and regulatory frameworks
| ID | Framework | Required capabilities | Pri |
|---|---|---|---|
| RG-1 | **IFRS 17** | GMM/VFA/PAA; units of account (portfolio × profitability × cohort); CSM initial recognition, accretion (locked-in), adjustments, coverage-unit release (configurable CU definitions); loss component systematic allocation; RA (CoC, VaR/CTE, margin) with diversification and confidence-level disclosure; OCI option; reinsurance held (loss-recovery component); transition (FRA/MRA/FVA); full disclosure tables (LRC/LIC reconciliations, CSM by transition method, analysis by measurement component); journal generation to subledger/GL | M (EU/UK), M (Asia); GMM/PAA core S at GA-US (for US multinationals reporting IFRS) |
| RG-2 | **US GAAP LDTI** | Cohort LFPB with net premium ratio, NPR capping and retrospective unlocking; locked-in vs current upper-medium-grade discount rate with OCI; DAC constant-level amortisation; MRB fair value with own-credit (instrument-specific credit risk) in OCI; DPL; disaggregated rollforward disclosures | M (US) |
| RG-3 | **US Statutory PBR** | VM-20 (NPR, DR, SR, exclusion tests, credibility/margins, **starting-asset and reinvestment modelling for DR/SR**); VM-21 (SR, CTE70, additional standard projection amount, hedge modelling); **VM-22** (effective 1 Jan 2026, optional three-year transition, mandatory for new business 2029). SPIA/FDA/FIA/structured settlements at GA-US; PRT with PC-10 in 1.x, before the 2029 mandatory date; VM-31 report support; NAIC **GOES** scenarios natively, plus the legacy AAA generator for the transition (GOES effective date expected 2027, to be confirmed) | M |
| RG-4 | **US Asset Adequacy Analysis / CFT** | Annual AAT: NY7 deterministic scenarios, stochastic (GOES), asset/liability cash-flow testing with reinvestment/disinvestment strategies, AAT memorandum support. Required of essentially every US life insurer, so it is core to Beachhead A | M |
| RG-5 | **US Stat other** | CRVM/CARVM, AG38 (ULSG), AG49-A (IUL illustrations), AG53 (complex assets in AAT), AG55 (reinsurance AAT), C-1/C-3 RBC (C-3 Phase I/II), US tax reserves (federal tax reserve basis); product tax-qualification tests (IRC 7702/7702A definition of life insurance, TAMRA MEC testing, which are separate from reserves); IMR/AVR | M (CRVM/CARVM, AG53, AG55, tax reserves, IMR/AVR); S (others, incl. 7702/MEC testing) |
| RG-6 | **Solvency II / Solvency UK** | BEL (det/stoch), standard-formula SCR (all life, market, counterparty, operational modules with correlation matrices), MCR, risk margin (projected SCR, simplifications), VA/MA (fundamental spread, eligibility), TMTP, Solvency UK reforms; internal-model/proxy support; QRT feeds | M (EU/UK) |
| RG-7 | **Bermuda** | EBS, BSCR, Scenario-Based Approach (SBA) with prescribed scenarios and liquidity tests. Important for US-linked reinsurers and sidecars | S (promote to M if a Bermuda design partner signs) |
| RG-8 | **Asia** | India IRBCF + Ind AS 117, Korea K-ICS, HK RBC, Singapore RBC2, Malaysia RBC + MFRS 17, Indonesia RBC + PSAK 117, China C-ROSS II, Japan ESR (2025+), Taiwan TW-ICS | M (Asia) for India, HK, SG, MY, ID; S for others |
| RG-9 | **Other** | Canada LICAT + IFRS 17 (Canadian specifics), Australia LAGIC/AASB 17, South Africa SAM, IAIS ICS | S/C |
| RG-10 | **Management** | Pricing/profit testing (IRR, PVFP, margins, break-even), EV/EEV/MCEV/VNB/AoM, business planning, ORSA, economic capital, ALM/SAA, hedging (Greeks, hedge effectiveness), reinsurance optimisation, M&A appraisal | M (pricing, planning, ALM); S (others) |
| RG-11 | **Tax** | US tax reserves and DAC tax; deferred tax on IFRS 17/SII/GAAP balance sheets; UK I-E/BLAGAB; local tax bases as configurable tax modules | M (US); M (EU/UK) |
| RG-12 | **Climate & emerging-risk scenarios** | Scenario packs for NGFS-style climate pathways (transition and physical risk to assets; mortality/morbidity overlays), BoE CBES/PRA-style, NAIC climate scenario analysis; long-horizon (50+ year) projections; reporting templates | S |

### 20.5 Assets and ALM
- **Asset classes:**
  - Govt/corporate bonds (fixed, floating, inflation-linked, callable)
  - MBS/ABS/CMBS (with prepayment models)
  - CLO/CDO
  - Private credit
  - Commercial mortgages
  - Equities, property, cash
  - Derivatives: swaps, swaptions, options, futures, FX forwards, total return swaps
  - Index options for IUL/FIA hedging
- **Asset behaviour:**
  - Credit migration and defaults (rating-transition matrices)
  - Spread modelling
  - Book and market values; amortised cost
  - Statutory, GAAP and IFRS 9 accounting (AFS/HTM/FVTPL)
- **Strategies:**
  - Reinvestment and disinvestment rules
  - Target SAA and rebalancing
  - Liquidity waterfall
  - Hedging programmes
  - Management actions (crediting rates, bonuses, EBR, dividend scales)
- **Portfolio data.** Load holdings from custodian or investment systems, with pricing and calibration checks (market-consistency tests).

Asset requirements are tagged **AS-1** (asset classes), **AS-2** (asset behaviour and accounting), **AS-3** (strategies and management actions) and **AS-4** (portfolio data).
- **AS-1 to AS-3 basic** (bonds, cash, equities; defaults; reinvestment/disinvestment) is **M for the MVP**, because VM-20 DR/SR and CFT need it.
- **Full AS-1 to AS-4** is M at GA.

### 20.6 Economic scenarios
- **ESG-1 (M). Native readers** for Moody's ESG, Conning GEMS/**NAIC GOES**, Ortec and CSV/Parquet scenario files, with scenario-set versioning and validation (martingale tests, calibration fit).
- **ESG-2 (S). Built-in light ESG.** Hull-White/G2++, LMM-lite, equity (lognormal, SVJD), inflation and credit, for pricing and testing. Partnerships remain the default for production.

### 20.7 Multi-currency, multi-entity and consolidation
| ID | Requirement | Pri |
|---|---|---|
| FX-1 | Every monetary variable carries a currency (MS-11). Products can be denominated in any ISO currency, and multi-currency products (e.g. USD policies sold in HK) are supported | M |
| FX-2 | FX rate tables (spot and forward) and **stochastic FX scenarios** correlated with ESG output; conversion at configurable rates (closing, average, historical) for reporting | M |
| FX-3 | Asset-currency matching and currency hedges (FX forwards, cross-currency swaps) in ALM; currency mismatch reporting; SII currency SCR | M (EU/UK, Asia) |
| FX-4 | IFRS 17 currency treatment. Under **IFRS 17 paragraph 30**, a group of insurance contracts that generates foreign-currency cash flows, **including the CSM**, is treated as a **monetary item** under IAS 21 and retranslated at the closing rate. This is required, not a policy choice. Remaining real choices to support: (a) presentation of the FX difference within the IFRS 17 line items vs separately; (b) how groups with multi-currency cash flows are handled, i.e. the currency in which a multi-currency group is measured (an entity judgement); (c) translation from functional to presentation currency for consolidation | M (EU/UK), M (Asia) |
| FX-5 | **Multi-entity**: entity dimension on all results; legal-entity and group hierarchies; intra-group reinsurance flagged and **eliminated** on consolidation; group-level SII/ICS aggregation | S (M for multinational design partners) |
| FX-6 | Consolidation outputs feed group reporting systems (OneSumX, SAP, Tagetik) | S |

---

## 21. Functional requirements: data, assumptions, results and reporting

| ID | Requirement | Pri |
|---|---|---|
| D-1 | **Data pipelines** (the DCS replacement): declarative transforms in SQL/Python from admin extracts to model points; reusable mappings; validation rules with severity; reconciliation to admin totals (counts, sums assured, reserves) | M |
| D-2 | Connectors: files (CSV, fixed-width, Excel, Parquet), databases (SQL Server, Oracle, Postgres), Snowflake, Databricks/Delta, S3/ADLS/GCS, SFTP | M |
| D-3 | Model-point compression/grouping tools with error metrics vs. seriatim | S |
| D-4 | **Assumption store**: versioned, typed tables with effective dates, owners, approval workflow (entry vs approval roles), lineage to source studies; Excel round-trip add-in; change impact preview | M |
| D-5 | Results store: columnar (Parquet/Delta/Iceberg) with arbitrary dimensions (product, cohort, IFRS 17 group, channel, any MP attribute). **No paid add-on** and no single-code grouping constraint | M |
| D-6 | Output control: choose variables/granularity; aggregate on the fly; avoid TB dumps; retain trace-capability via re-execution rather than storage | M |
| D-7 | Results APIs (REST/GraphQL, Arrow Flight), SQL access, Python/R clients, Excel add-in, Power BI/Tableau connectors | M |
| D-8 | Built-in reporting: run comparison, AoC waterfalls, sensitivity heatmaps, stochastic distributions, IFRS 17 disclosure tables, LDTI rollforwards, SII QRT-ready extracts | M |
| D-9 | Ledger integration: journal generation/export to SAP FPSL, Oracle, Aptitude, OneSumX, Workday, or native lightweight subledger (C) | S |
| D-10 | Data quality dashboard per run (inputs, MPs, assumption versions, scenario set hashes) | S |
| D-11 | **Model-as-API**: publish a governed model version as a low-latency calculation service (REST/gRPC) for quotes, illustrations (e.g. AG49-A IUL illustrations), policy-admin values and pricing engines. Single-policy latency < 50 ms at P95; the same code and assumptions as valuation; version-pinned. This is Mo.net's "one calc engine" differentiator, which Prophet lacks | S |
| D-12 | **Roll-forward state store**: persisted, versioned per-period state, including IFRS 17 CSM, loss component, locked-in discount curves and coverage units by group of contracts; LDTI cohort histories (actual and expected cash flows since cohort inception, NPR history, locked-in rates); VM-20/21 prior results; DAC balances. Plus **import of opening state from legacy systems** with reconciliation (see §26.3) | M |
| D-13 | Native stochastic statistics (mean, SD, percentiles, CTE-x, VaR) computed in-engine and stored with scenario-level drill-down (fixes W19) | M |
| D-14 | Record retention: results, manifests and inputs retained per policy (default 10 years, configurable to regulatory requirements), with legal hold and immutable (WORM) storage options | M |

---

## 22. Functional requirements: governance, collaboration and DevOps

| ID | Requirement | Pri |
|---|---|---|
| G-1 | **Git-native**: models, libraries, run configs, assumption metadata stored as text in Git (hosted or customer GitHub/GitLab/Azure DevOps/Bitbucket) | M |
| G-2 | Pull-request workflow with semantic diffs (code + result impact on regression dataset), required reviewers, sign-off | M |
| G-3 | **CI for models**: automatic build, unit tests (per-variable expected values), regression tests (result tolerance vs. baseline), performance tests on every change | M |
| G-4 | Environments: dev/test/UAT/prod with promotion gates; production runs only from approved, tagged versions; immutable run manifests (code hash + data hash + assumption versions + scenario hash + engine version) | M |
| G-5 | Reproducibility: any historical production run can be exactly re-executed from its manifest | M |
| G-6 | Role-based access control (model developer, approver, executor, viewer, auditor), SSO (SAML/OIDC), SCIM, fine-grained data permissions | M |
| G-7 | Full audit trail of all actions (who/what/when), tamper-evident | M |
| G-8 | Model inventory and model risk management: register of models, owners, tiering, validation status and limitations. Evidence packs for ASOP 56 (US), the NAIC Model Audit Rule and SOX ITGC/ITAC controls, Solvency II internal-model validation, model-change policy and documentation standards (UK/EU), UK FRC TAS 100/200, and local equivalents. Note that PRA SS1/23 applies to banks, not insurers, but is a useful good-practice reference | M |
| G-9 | Workflow orchestration for close: DAG of steps (data load → validation → runs → AoC → review → sign-off → publish), with timers, triggers, approvals, notifications; REST/webhooks | M |
| G-10 | Collaboration: comments on code/results, @mentions, task assignment | S |
| G-11 | Auditor/regulator read-only workspace with trace explorer and documentation | S |

---

## 23. Functional requirements: AI capabilities

All AI features are optional and configurable per tenant. They support customer-chosen or private model hosting, never train on customer data/code without explicit opt-in, and log every action for audit.

| ID | Requirement | Pri |
|---|---|---|
| AI-1 | Documentation and methodology Q&A with citations (parity with FIS AI Assistant/AXIS Navigator) | M |
| AI-2 | **Explain this number**: natural-language explanation of any result using the trace graph (e.g. "why did BEL rise 3% vs last quarter?") | M |
| AI-3 | Code assistant: write/modify variables from a spec, generate unit tests, propose refactors, flag performance issues | M |
| AI-4 | **Agentic workflows** (human-approved): implement a product change end-to-end (code + tests + docs + PR); diagnose failed runs/regressions; draft validation and change-control evidence; draft AoC commentary | S |
| AI-5 | **Reconciliation-driven rebuild agent**. Inputs are limited to (a) **customer-owned specifications** (product terms, policy documents, the customer's own methodology documents and assumption tables), (b) **customer data** (model points, assumptions) and (c) **legacy outputs** (per-policy, per-period cash flows, reserves and intermediate values the customer exports). The agent proposes Meridian code, runs it, and iterates until policy-level results reconcile within tolerance, reporting the first divergent variable. **The agent is never given legacy vendor code or library source** (§26.1). An exception is possible only where counsel confirms, per customer contract, that specific customer-authored code is outside vendor IP; it must then be processed in the customer tenancy, logged and attested | S |
| AI-6 | Product-spec to model: draft a model from a product filing/brochure | C |
| AI-7 | Data-mapping assistant for admin extract → model point pipelines | S |

### 23.1 AI governance and regulatory compliance
| ID | Requirement | Pri |
|---|---|---|
| AIG-1 | **No autonomous changes to production numbers.** Every AI-generated code, assumption or configuration change goes through the normal PR, CI and approval path (G-2/G-3). AI output is labelled in lineage and the audit trail | M |
| AIG-2 | **EU AI Act.** Annex III lists AI systems used for **risk assessment and pricing in relation to natural persons in life and health insurance** as high-risk. Meridian's AI assistants are developer tools, not pricing decision systems, but customers may use Meridian models (including ML-based assumptions) in pricing. Provide: intended-purpose documentation, technical documentation, logging, human-oversight features, accuracy/robustness metrics and data-governance records so customers can meet deployer obligations. Track the application dates, including the 2025–26 "Digital Omnibus" proposals to defer high-risk obligations [verify current status] | M (EU) |
| AIG-3 | **US.** Support customer compliance with the NAIC Model Bulletin on the Use of AI Systems by Insurers (Dec 2023, adopted in many states), Colorado SB21-169 and the Colorado life-insurance governance regulation (external consumer data and algorithms; quantitative testing for unfair discrimination), and NY DFS Circular Letter 7 (2024). Provide model-inventory hooks, testing reports and documentation exports | S |
| AIG-4 | **AI evaluation.** A maintained benchmark of actuarial coding and explanation tasks, with published accuracy metrics per release: test-pass rate of generated code, reconciliation success rate, explanation factuality (claims verified against the trace), and hallucination rate on documentation Q&A. Gate releases on regression thresholds | M |
| AIG-5 | **Data boundary.** Choose per tenant: vendor-hosted models with zero data retention, customer-hosted models (e.g. in the customer's Azure OpenAI or AWS Bedrock tenancy), or AI disabled. No customer code or data is used to train shared models without written opt-in | M |
| AIG-6 | Explainability guarantees: "explain this number" (AI-2) answers must cite trace nodes, and any figure quoted is computed by the engine, never generated by the LLM | M |

---

## 24. Non-functional requirements

All NFRs are testable. The measurement method is in brackets.

| ID | Area | Requirement |
|---|---|---|
| NF-1 | Throughput | Workload-specific targets in §30.2 [timed on the §19.3 suite on published hardware specs] |
| NF-2 | Interactive dev loop | On a reference model (2,000 variables, 20 products): incremental rebuild after a single-variable edit **< 1 s** at P95. Single-policy, single-scenario, 60-year monthly projection **< 1 s** at P95. Full rebuild **< 60 s** [automated timing in CI] |
| NF-3 | IDE responsiveness | Autocomplete, go-to-definition and hover **< 200 ms** at P95 on the same reference model, browser and VS Code [synthetic user-journey tests] |
| NF-4 | Scale | (a) **50m policies seriatim**, deterministic, 3 bases, monthly to 60 years: ≤ 2 h on ≤ 2,000 vCPU. (b) Nested: **1,000 outer scenarios × 1,000 inner paths at 10 annual outer nodes** for 100k VA policies: ≤ 4 h on ≤ 64 GPUs. (c) Burst to ≥ 10,000 vCPU or 500 GPUs within 15 minutes of submission (subject to cloud quota) [load tests per release] |
| NF-5 | Availability | SaaS control plane **99.9%** monthly. During customer-declared close windows, 99.95% with a P1 response in 15 minutes. Compute-plane jobs survive control-plane outages (workers continue and results buffer) [status-page SLO reporting] |
| NF-6 | DR / BCP | Control plane RPO ≤ 15 min, RTO ≤ 4 h. Results store RPO ≤ 1 h (object-storage replication). Annual DR test with report shared with customers. Multi-AZ by default; multi-region optional |
| NF-7 | Security certifications | SOC 2 Type II by GA, ISO 27001 by GA+12 months, CSA STAR. Annual independent pen test, shared under NDA. Bug-bounty programme |
| NF-8 | Data protection | Encryption at rest (AES-256) and in transit (TLS 1.2+). **Customer-managed keys** (BYOK/HYOK). Private networking (PrivateLink/Private Endpoints). Tenant isolation verified by pen test. Field-level **pseudonymisation** of PII in model points (names and IDs tokenised, dates of birth optional). Health and medical data treated as **GDPR Art. 9 special-category data**, with default minimisation (model points need age, sex and underwriting class, not diagnoses) |
| NF-9 | Data residency and localisation | Regional deployments in US, EU, UK, Singapore, India and Australia. Support India **DPDP Act 2023** and IRDAI requirements on records and outsourcing, plus **China PIPL** (an in-country deployment via a local cloud partner if China is targeted). In BYOC, **only metadata leaves the customer tenancy**: job status, resource metrics, code hashes, and optionally code. Policy data, assumptions and results never do. The exact metadata schema is published |
| NF-10 | Software supply chain | SBOM for every release (SPDX/CycloneDX). Signed artefacts (Sigstore). Production use of third-party Python packages (L-10) only from a **curated, pinned, vulnerability-scanned allow-list** mirrored per tenant. Reproducible builds |
| NF-11 | Compliance and outsourcing | GDPR; **DORA** (EU) ICT third-party register data, exit strategies, audit and access rights, incident reporting timelines; EIOPA cloud outsourcing guidelines; PRA SS2/21; MAS Outsourcing/TRM; APRA CPS 230/234; contract clauses supporting these |
| NF-12 | Reproducibility | Bit-identical re-execution of any production run from its manifest on the same engine version. Engine versions retained and runnable for ≥ 10 years (containerised) [quarterly automated re-execution tests of archived runs] |
| NF-13 | Numerical accuracy | float64 for production. CPU–GPU relative difference **< 1e-9** on the reference suite with deterministic reductions (§19.4) [CI comparison]. float32 GPU runs are exempt and flagged |
| NF-14 | Portability | Kubernetes-based. Runs on AWS, Azure, GCP and on-prem (OpenShift/Rancher). No Windows or C++ toolchain needed by users |
| NF-15 | API stability | Public APIs versioned (semver). Breaking changes only in major versions, with a ≥ 12-month deprecation period. OpenAPI specs published. Python SDK compatibility matrix |
| NF-16 | Usability and accessibility | WCAG 2.1 AA. Localisation: English at GA; then Chinese (Simplified/Traditional), Korean, Japanese, Bahasa (Indonesia/Malaysia), Thai, German and French in line with go-to-market. Task-completion usability tests with actuaries before each GA |
| NF-17 | Support | See §32.3 for severity levels and response times |
| NF-18 | Longevity | Long-term-support releases (3 years). Source-code escrow with release triggers (§32.1). Open-format guarantee |

---

## 25. Reference architecture

```
┌──────────────────────────── Clients ────────────────────────────┐
│ Browser IDE │ VS Code ext │ Jupyter │ Excel add-in │ BI tools │ API │
└──────────────┬──────────────────────────────────────────────────┘
               │ HTTPS / gRPC (SSO, RBAC)
┌──────────────▼─────────── Control plane (SaaS or BYOC) ─────────┐
│ Model registry (Git) │ Build service (DSL→IR→kernels) │ Assumption│
│ store │ Scenario store │ Orchestrator (DAG/workflows) │ Run manager│
│ & cost estimator │ Governance/audit │ AI services │ Results catalog│
└──────────────┬──────────────────────────────────────────────────┘
               │ job specs (manifest hashes)
┌──────────────▼─────────── Compute plane (customer cloud/on-prem) ─┐
│ Kubernetes cluster: CPU worker pools (SIMD) │ GPU pools (CUDA)   │
│ Class-aware planner: C1 policy×scenario │ C2 lockstep + allreduce│
│ C3 nested scheduler │ Checkpoint/restart │ Cost estimator       │
└──────────────┬──────────────────────────────────────────────────┘
               │ Arrow/Parquet
┌──────────────▼─────────── Data plane ────────────────────────────┐
│ Object storage (S3/ADLS/GCS) │ Lakehouse tables (Delta/Iceberg) │  │
│ Connectors: Snowflake, Databricks, SQL DBs, SFTP │ Ledger exports │
└──────────────────────────────────────────────────────────────────┘
```

**Key technology choices** (the language and engine decision is recorded in ADR-001, §25.1):
- **Actuary-facing language: Python.** Models are written in a Python-hosted modelling language (plus the L-9 low-code layer) and traced to an intermediate representation (IR). Actuaries never write Rust.
- **Engine core: Rust.** The compiler back end, interpreter or code generator, the C1/C2/C3 scheduler, deterministic reductions, checkpointing and the results I/O are written in Rust. They are exposed to Python through PyO3/maturin, the same pattern as Polars, Ruff and pydantic-core.
- **GPU: generated kernels, Rust host.** GPU kernels are generated as CUDA C++/PTX or Triton (a JAX/XLA back end is an option) and launched from Rust (e.g. via `cudarc`). Kernels are not written in Rust, because Rust's GPU ecosystem is still immature.
- Columnar data via Apache Arrow end to end, with Parquet/Iceberg at rest (`arrow-rs`, DataFusion for results queries).
- Kubernetes plus a job framework (e.g. Ray or Argo) for distribution. Spot/preemptible capacity is supported, with checkpointing.
- Git (customer-provided or embedded Gitea) as the model source of truth.
- The control plane is multi-tenant SaaS. The compute and data planes can be deployed in the customer's own cloud (BYOC), so data never leaves the customer tenancy.

**Data boundaries (BYOC mode).**
- **Stays in the customer tenancy:** model points, assumptions, scenarios, results, logs containing values, and the AI context assembled from those.
- **Crosses to the vendor control plane:** job metadata, code hashes (and code only if the customer opts in to the hosted Git), resource metrics, and licence/usage telemetry.
- **AI services** run either in the customer tenancy (customer-hosted LLM endpoint) or in vendor regions under zero-retention terms (AIG-5).
- **Fully self-hosted.** For regulated or air-gapped customers, the control plane can also be self-hosted (C).

### 25.1 ADR-001: Python modelling language over a Rust engine core
**Status:** Accepted (2 Nov 2026). Validated by the Foundation-phase prototype in `meridian/` (see below).

**Context**
- The engine must be fast (E-3) and deterministic (L-11, NF-12, NF-13).
- It must be memory-safe, because it produces governed regulatory numbers and processes policyholder data (NF-8, NF-10).
- It must be portable across Linux, Windows and macOS and run in containers (NF-14).
- It must embed in Python (L-1, DX-6), compile to WebAssembly for in-browser single-policy traces (DX-3), and drive GPU kernels (E-1).

**Options considered**

| Option | Strengths | Weaknesses | Verdict |
|---|---|---|---|
| **Rust core + Python surface** | Memory and thread safety enforced at compile time; predictable performance with no GC pauses; first-class Arrow/Parquet (`arrow-rs`, DataFusion); PyO3/maturin bindings and packaging; Cranelift (fast JIT) and LLVM (`inkwell`) for code generation; WebAssembly target; `cargo-audit`/`cargo-deny`/SBOM tooling; attractive to strong systems engineers | Immature native GPU ecosystem; thinner numerical libraries than NumPy/SciPy or Eigen/BLAS (`ndarray`, `faer`, `nalgebra` exist); MLIR bindings immature; fewer Rust engineers in the India and Poland hubs; slower compile times and a steeper learning curve | **Chosen** |
| C++ core + Python surface | Most mature GPU, HPC and MLIR ecosystem; largest talent pool | Memory-safety risk in a regulated product; weaker build and packaging; slower safe iteration | Rejected (kept as the fallback if a GPU-first strategy dominates) |
| Pure Python (NumPy/JAX/Numba) | Fastest start; actuary-familiar | Hard to control C2 lockstep execution, memory and determinism; packaging and IP protection for the commercial engine | Prototype and reference use only; JAX remains a candidate GPU back end |
| Julia | Excellent numerics | Deployment, start-up latency and enterprise acceptance | Rejected |

**Decision: layering**
```
Actuary layer   Python modelling language + low-code editor            (Python)
Front end       Tracer -> IR (JSON today; binary/Arrow schema later)   (Python; hot paths in Rust via PyO3)
Core            Validation, dependency ordering, C1/C2/C3 and          (Rust: meridian-core)
                lane-uniform analysis, vectorised interpreter ->
                fused kernels -> Cranelift/LLVM code generation,
                scheduler, deterministic reductions, checkpointing
GPU             Generated CUDA/Triton kernels, launched from Rust       (generated code)
Data            Arrow/Parquet, DataFusion results queries               (Rust)
Services & IDE  Control-plane services, language server (LSP),          (Rust; TypeScript for the UI)
                WebAssembly trace engine for the browser
```

**Execution strategy**
- **Start with a vectorised interpreter, not a compiler.** Each IR node is applied to a chunk of thousands of policy × scenario lanes, so dispatch overhead is amortised. That captures much of the speed with far less risk than a JIT.
- **Optimisations in order:**
  1. ~~C1 whole-time-path-per-chunk execution (no global barriers)~~: **done** in the prototype. C1 models run per chunk; C2 models run lockstep.
  2. ~~Barrier-free segments inside C2 models~~: **done**. Lockstep breaks only where a `sum_policies` total needs every lane finished, and reductions are computed block-wise without full-width buffers.
  3. ~~Scenario-partitioned C2 execution~~: **done**. Each scenario group runs its own segmented lockstep (the §19.4 design).
  4. Operator fusion and shared-subexpression memoisation.
  5. Cranelift JIT for the development loop and LLVM AOT for production.
  6. GPU kernels.

**Consequences**
- **Hiring:** 2–3 senior Rust engineers from day 1 (engine, compiler); the others train in Rust (§29.1).
- **GPU:** GPU work needs CUDA/Triton expertise alongside Rust.
- **Bindings:** the Python/Rust boundary is a stable, versioned IR schema, and the language and engine can evolve independently behind it.
- **Community edition:** the Apache-2.0 community edition (§28) ships the Rust single-node engine as a Python wheel.

**Prototype evidence (Foundation spike, `meridian/` in this repository)**
- **What it is:**
  - a Python modelling language (traced decorators, `where`, `lag`, `sum_policies`)
  - a Rust engine crate with compile-time dependency ordering and cycle reporting, C1/C2 classification, lane-uniform folding, a chunked parallel interpreter and pairwise deterministic reductions
  - PyO3 bindings
  - an independent NumPy reference engine
  - two reference models: term life (C1) and a stochastic with-profits model with company-level bonus feedback (C2)
- **Test results** (2 Nov 2026):
  - 16 Rust tests and 13 Python tests pass.
  - Rust reconciles with the NumPy reference to ≤ 1e-11 relative; the observed worst case is 3e-13.
  - Results are bit-identical across all three execution strategies (per-chunk, scenario-partitioned lockstep, global lockstep), chunk sizes and thread counts. This works because per-scenario totals are defined over fixed 1,024-policy reduction blocks.
- **Throughput** (i7-14700K, 28 logical CPUs; term life, 100k policies × 360 months; best of 3):

| Engine | Time |
|---|---|
| NumPy, 1 thread | 12.8 s |
| Rust lockstep, 28 threads | 0.55 s (23×) |
| **Rust per-chunk, 28 threads** | **0.13 s (97×; about 273m policy-months/s)** |

- **Scale:** at 1m policies × 360 months, per-chunk takes 1.37 s against 10.6 s for lockstep.
- **Thread scaling:** per-chunk 11.8× from 1 to 28 threads; lockstep 3.3×.
- **C2 stochastic** (with-profits, scenario-partitioned segmented lockstep, 28 threads):
  - 2k policies × 50 scenarios × 240 months: 0.07 s, **81× NumPy**.
  - 20k × 200 × 240 (960m lane-months): **6–7.5 s**, against 12.1 s for global lockstep and 26.8 s for the first prototype.
  - Results are unchanged throughout: PV of guarantees mean 34,087,164 and CTE70 71,043,727 in every version.
  - The remaining limit for large scenarios is cache footprint (about 4 MB of state per 20k-policy scenario × 28 threads exceeds L3). Operator fusion (item 4) reduces it.
- **External reconciliation (lifelib BasicTerm, MIT-licensed, 10,000 policies):** lifelib's term-assurance model was rebuilt in the Python modelling language using the new multi-dimensional select-and-ultimate tables and text categories.
  - Every premium is identical to the cent, and per-policy PVs agree within 2e-15 relative.
  - The portfolio PV of net cash flow is identical (14,489,630.534602).
  - Meridian runs both passes in 0.03 s, against 0.38 s for lifelib's NumPy-vectorised model, and 1m policies in 1.6 s.
- **External stochastic reconciliation (lifelib CashValue_ME savings/UL model):** account value with intra-month timing, COI on net amount at risk, surrender charges, single and level premiums, whole life, new and in-force business, 10 stochastic scenarios.
  - Gross PVs agree per policy and scenario within 2e-14 for new business (10,000 policies) and 4e-13 for in-force (1,000 policies).
  - Portfolio PV by scenario is identical to 4 decimals.
  - Meridian runs all 10 scenarios in one 1.0 s pass, against 172 s for lifelib (one scenario per run).
  - Reconciliation surfaced an out-of-table lookup convention (lifelib returns 0 beyond the mortality table), now an explicit table `fill=` setting rather than an implicit rule.
- **South African family funeral on a SAM-style basis (illustrative assumptions):** up to 8 lives per policy, using the new lives-within-a-policy feature (`Model(lives=8)`, `sum_lives`), which plays the role of Prophet's array variables.
  - The valuation covers BEL, six SAM-style stresses, SCR with the life correlation matrix, and a 6% cost-of-capital risk margin.
  - BEL per policy matches an independent loop implementation within 2e-13 under all 7 bases.
  - 20,000 policies (70,000 lives) × 600 months × 7 runs take about 8–11 s.
- **These are prototype numbers, not the §30.2 GA targets.**

---

## 26. Migration strategy from Prophet (including legal constraints)

### 26.1 Legal guardrails
FIS v. Montoux (Delaware, Nov 2024) alleged trade-secret misappropriation and inducement to breach licence agreements through a "Model Replication Module". Montoux went into liquidation [R63]. Meridian must therefore:
1. Never use, ingest or redistribute FIS library code, documentation or tools without explicit legal clearance.
2. Make migration **customer-performed and customer-controlled**. Customers export their own model artefacts under their own licence rights, and conversion runs in the customer's tenancy.
3. Use **clean-room** methods: equivalence is demonstrated by reconciling *outputs* (cash flows and reserves per policy) rather than by translating vendor code.
4. Get specialist IP counsel review in each jurisdiction before releasing any import tooling, and have customers confirm their licence terms.
5. Never use customer-provided legacy code to train shared AI models.
6. **AI and tooling never see legacy vendor code.** A customer's Prophet workspace consists largely of FIS library code or derivative works of it. Only customer-owned specifications, customer data and legacy *outputs* may be used as migration inputs (AI-5).
7. **Benchmarks against legacy platforms are customer-run.** They are performed by the customer under its own licence and published only if the customer's contract allows (§30.3).

### 26.2 Migration toolkit
- **Data readers.** Readers for customer model-point and assumption-table files, which are customer data. The formats are plain-text and publicly documented through open-source parsers. This is a data-interchange function, subject to legal review.
- **Parallel-run harness.** Load legacy outputs and Meridian results, then reconcile policy by policy, variable by variable and time step by time step. Tolerance rules (§31.3) and drill-down highlight the first divergent variable.
- **Rebuild agent (AI-5).** Proposes Meridian code from specifications and reconciles iteratively against outputs. A human approves each change.
- **Convention mapper (§26.4).** Declares the legacy timing and decrement conventions, so that reconciliation differences are classified as *convention*, *bug* or *intended change*.
- **Prophet concept guide.** Maps indicators to traits, products to product definitions, run numbers to assumption scenarios, accumulations to aggregation views, SPCODE to dimensions, nested structures to C3 models, and the dynamic loop to the C2 class. It is written from public knowledge only.

### 26.3 Roll-forward state and history migration
| Item | What must be migrated | Approach |
|---|---|---|
| IFRS 17 | Opening CSM, loss component, locked-in discount curves (by cohort), cumulative coverage units, OCI balances, and transition method per group of contracts | Import the customer's last closed-period balances from its subledger or results store into D-12. Reconcile the first Meridian roll-forward against the legacy roll-forward for ≥2 periods |
| US GAAP LDTI | Cohort-level history: actual and expected cash flows since cohort inception (needed for retrospective NPR unlocking), locked-in discount rates, NPR history, DAC balances, MRB attributed fees and inception values | Import cohort history tables. Where history is unavailable, rebuild it from admin history plus legacy outputs, with documented approximations agreed with auditors |
| US Stat / PBR | Prior-period VM-20/21 reserves, deferred items, IMR/AVR, prior AAT conclusions | Import as opening balances. Reconcile the first-period movement |
| EV / SII | Prior-period BEL, RA, SCR and own funds for AoC openings | Import as AoC opening positions |
| Historical results | Prior N periods of results needed for trend analysis and AoC | Bulk import into the results store with lineage flagged "legacy" |

### 26.4 Convention mapping
Typical reconciliation drivers to capture explicitly before a parallel run:
- timing of premiums, claims, expenses and decrements within the period
- decrement ordering and dependency
- monthly vs annual rate conversion (e.g. 1−(1−q)^(1/12) vs q/12)
- policy-month vs calendar-month alignment
- interest timing and discount conventions
- treatment of the valuation month (part-period)
- rounding
- interpolation of tables
- grouping methodology

Meridian libraries are configurable for these conventions (as library parameters). Matching legacy conventions during parallel runs is therefore possible, and moving to preferred conventions becomes a separate, documented change.

### 26.5 Regulatory, audit and governance approval of the platform change
- **Solvency II / Solvency UK internal-model firms.** A change of modelling platform is likely a **major model change** under the firm's model-change policy and requires supervisory approval (e.g. PRA). Plan 12–18 months, with parallel runs and validation evidence. Standard-formula firms need no approval, but must evidence BEL/SCR equivalence to their auditors and to the board.
- **US.**
  - Document the change in the **VM-31 PBR Actuarial Report** and the AAT memorandum.
  - Satisfy **ASOP 56** (model reliance and validation) and the NAIC **Model Audit Rule**/SOX controls, including change-management and ITGC testing.
  - Inform the appointed actuary and external auditors early.
- **IFRS 17 / LDTI.** External auditors review the system change, roll-forward continuity and control environment. Plan for an audited parallel period.
- **Meridian support.** A regulatory change pack: validation report, parallel-run evidence, methodology mapping, control descriptions (SOC 1 Type II report for user-entity controls reliance, target GA+12 months), and auditor workspace access (G-11).

### 26.6 Migration effort and cost (planning estimates [to be calibrated with design partners])
| Scope | Typical legacy footprint | Meridian effort (with toolkit) | Comparator |
|---|---|---|---|
| Single product family (e.g. term + riders) | 1 library variant, 5–20 products | 1–3 actuary-months + reconciliation | 3–12 actuary-months per model by hand (Montoux/AWS [R59]) |
| Mid-size insurer (US) | 5–10 model families, PBR + LDTI + CFT | **12–18 months elapsed** from signature to cut-over (§26.7 phases: discovery about 1.5 months, pilot about 3 months, block migration 3–6 months, ≥2 parallel quarterly cycles about 6 months), **4–6 FTE** (customer + partner) | 12–24 months via buyer guides |
| Large multinational | 30+ models, multiple regimes and entities | Phased over 2–3 years | — |

- **Commercial offer.** Fixed-price migration packages with partners. A **dual-running credit** of **50% of the Meridian subscription for up to 12 months** of overlap (pilot fees are also credited). Design partners on early-access terms already pay discounted fees and receive no further credit.

**Worked example: mid-size US insurer** (this single cost basis is used throughout the document)

| Item | Assumption | Amount |
|---|---|---|
| Incumbent vendor spend | §12 range midpoint | US$1.0m a year |
| Total modelling TCO | Vendor ≈ 20% of TCO (§12) | US$5.0m a year |
| Internal migration effort | 5 FTE × 15 months × US$200k loaded | US$1.25m |
| Partner fixed-price migration | Pilot + block migration support | US$0.8m |
| Validation, audit and legal | Independent review of parallel-run evidence; auditor time | US$0.25m |
| Dual running | Meridian subscription at about US$0.75m ACV (about 25% below incumbent). 12 months at the 50% credit (US$0.375m) plus about 3 further months of overlap at full rate (US$0.19m). The incumbent licence continues as already budgeted | US$0.56m |
| **One-off switching cost** | | **≈ US$2.85m (≈ 0.57× annual TCO, ≈ 2.9× annual vendor spend)** |
| Steady-state annual saving | 33% of TCO (§27.1, 30% productivity case) | US$1.65m a year |
| Savings ramp | 50% in the first 12 months after cut-over, then 100% | — |
| **Payback from contract signature** | Cut-over at month 15; savings of US$0.83m by month 27; then US$1.65m a year, reaching cumulative US$2.85m at about month 42 | **≈ 3.5 years** (range about 2.7–4.5 years across the §27.1 productivity cases and the §26.6 effort range) |

- **TCO treatment.** The 30–40% TCO target is a steady-state figure. Every business case presented to buyers must show the switching cost, the ramp and payback measured **from signature**.
- **Consistency with KPI P3.** P3 (−30% actuary hours "by the second production quarter") is the productivity measure that drives the ramp.

### 26.7 Phased methodology
1. **Discovery (4–6 weeks).** Inventory models, conventions and controls, and pick a pilot.
2. **Pilot (10–12 weeks).** One product block, parallel run against legacy outputs, pre-agreed success criteria (§30.4).
3. **Block migration.** One reporting basis at a time (e.g. stat, then GAAP, then IFRS 17).
4. **Parallel production for ≥2 reporting cycles**, plus an auditor sign-off pack.
5. **Cut-over and decommission**, with legacy outputs archived for history.

---

## 27. Commercial model, go-to-market, roadmap and risks

### 27.1 Pricing (transparent, published)
Price points are **hypotheses to validate with design partners**. They are set against an estimated Prophet spend of about US$0.5–1.5m a year for a mid-size insurer (§12, UNVERIFIED).

| Tier | Target customer | Included | List price (annual, hypothesis) |
|---|---|---|---|
| **Community** | Students, researchers, individuals | Open-source DSL + single-node engine (Apache 2.0); no production governance or certified libraries | Free |
| **Starter** | Small insurers / fraternals (≤ 500k policies, ≤ 5 developers) | Full platform, 1 certified regulatory pack, SaaS compute allowance | US$120–180k |
| **Professional** | Mid-size (≤ 5m policies, ≤ 25 developers) | Full platform, 2 regulatory packs, BYOC option, model-as-API (S) | US$350–550k |
| **Enterprise** | Large / multinational | Unlimited developers, all packs in licensed regions, multi-entity, premium support, dedicated CSM | From US$1.0m |
| Add-on regulatory packs | Any | Each additional framework (e.g. VM-21/22, SII, Ind AS 117) | US$40–120k each |
| Compute | SaaS | Pass-through at cloud cost + 15% published margin; budgets and caps | Usage |
| Compute | BYOC | The customer pays its own cloud; no Meridian compute margin | — |

- **No per-library sprawl, and no paid add-ons for core capability.** Results store, flexible aggregation, orchestration, assumption store, experience studies and governance are all included.
- **TCO model and target.** Baseline TCO is 100: people 60, vendor 20, compute 10, data management 5, consulting 5 (the §12 split).
  - **At a 30% people-productivity gain:** people 42, vendor 15 (25% lower), compute 5 (50% lower), data management 2 (included), consulting 3. Total 67, a **33% reduction**.
  - **At a 40% people-productivity gain:** total about 61, a 39% reduction.
  - **Target:** 30–40% steady-state TCO reduction, with 50% as a stretch goal for customers with heavy run-time pain.
  - **Why productivity is the dominant lever:** licence price is only about 20% of TCO, so it is a secondary lever. Measured as KPI P3 (§30.1).

### 27.2 Go-to-market
**Beachheads and the capabilities each needs**

| Beachhead | Why | Must-have capabilities | Release |
|---|---|---|---|
| **A: US mid-market life & annuity** (about 250 companies with $1–50bn of assets) | Prophet is weak in the US. VM-22 (2026–29) and GOES (expected 2027) force model work. Slope is now P&C-owned (Akur8) | PC-1/3/7/8/9/14; RG-2/3/4/5 (M parts)/11; AS-1–4; ESG-1 (GOES); AOC-5; CL-1–5; D-12 | MVP (design partners) at M15; **GA-US at M24** |
| **C: UK/EU bulk annuity, with-profits, mid-size life** | Run-time pain (MA, SII), Solvency UK reforms, Prophet re-hosting costs | PC-2/4/6/10; RG-1/6/10/11; FX-3/4; AOC-4/6 | **GA-UK/EU at M30** |
| **B: India and SE Asia** | Ind AS 117 + IRBCF (India); MFRS 17/PSAK 117; HK/SG RBC; ICICI Prudential's move to PathWise shows switching happens | PC-2/5/6/13; RG-1/8; FX-1–4; localisation | **GA-Asia at M36** |

**Sales motion**
- **Sales cycle.** 12–24 months, typically RFP-driven, with a paid proof of concept.
- **Decision-making unit.** Chief/Appointed Actuary (economic buyer with the CFO), CRO, CIO/CTO, head of model risk and validation, internal audit, procurement and legal (IP, outsourcing, DORA). External auditors are informal influencers.
- **Typical RFP criteria (to design for).**
  - regulatory coverage and certification
  - proof of accuracy (parallel runs)
  - performance at close
  - governance and auditability
  - vendor viability and escrow
  - TCO
  - talent availability
  - references in the region
  - security and outsourcing compliance
  - migration plan and risk
- **Pilot design.** 10–12 weeks on one product block. Success criteria are agreed before the pilot (§30.4). Pilots are priced at US$75–150k and credited against the first-year subscription.
- **Renewal-window targeting.** Track known contract-renewal timing and FIS ownership events (§2.2) to time outreach.

**Partner programme**
- **Tiers.** Registered, Certified and Elite. Elite requires at least 10 certified practitioners and two delivered migrations. Benefits are lead sharing, a sandbox, early library access and co-marketing.
- **Big 4 conflict.** Several large consultancies have FIS alliances; Deloitte, for example, has a global alliance with FIS [UNVERIFIED date], and Prophet originated at Deloitte's predecessor. Recruit in a deliberate order:
  1. independent actuarial consultancies and offshore delivery firms (India, Malaysia, Poland) first
  2. Big 4 on a non-exclusive basis, once reference customers exist
- **Co-development.** Regulatory libraries for Asia are co-developed with regional consultancies under revenue-share agreements.

**Training and certification**
| Track | Audience | Format | Credential |
|---|---|---|---|
| Meridian Foundations | All actuaries, students | 2 days self-paced + labs; free with Community edition | Associate (online exam) |
| Model Developer | Modelling actuaries | 5 days + project | Professional (proctored exam + graded model) |
| Advanced: ALM, nested & performance | Senior modellers | 3 days | Expert |
| Governance & validation | Model risk, audit | 2 days | Validator |
| **Prophet → Meridian conversion** | Experienced Prophet users | 2 days: concept mapping (§26.2), convention mapping, migration toolkit | Professional (fast-track) |
| University programme | Actuarial science departments (including those currently teaching Prophet) | Free academic licences, course materials, student competitions | — |

**Proof and marketing**
- Publish Meridian's own reference benchmarks (§19.3).
- Publish customer-authorised parallel-run case studies.
- Provide validation packs and an open-source community edition.
- Engage at SOA ValAct, IFoA and Asian actuarial society events.

### 27.3 Roadmap (re-sequenced so each beachhead goes live at its GA)
| Phase | Timing | Scope (requirement IDs) |
|---|---|---|
| **Foundation** | M0–6 | L-1–8, L-11; MS-1–4, MS-10–12; DX-1–3, DX-5; E-1(a,b); single-node C1 engine (Rust, per ADR-001; the spike is done, see §25.1); Git (G-1); term/WL reference model |
| **MVP: design-partner release** | M6–15 | **MVP cut-list:** L-9 (basic grid editor); MS-6–8; DX-6–7; R-1, R-2, R-4 (C2 time-synchronous engine), R-5, R-7, R-9; AOC-1, AOC-2, AOC-7; E-2, E-4–7, E-9 (SaaS only); D-1, D-2, D-4–D-7, D-8 (core reports), D-12, D-13; G-2–G-7, G-9; AI-1–3; AIG-1, AIG-5, AIG-6; PC-1, PC-3, PC-8 (UL/ULSG), PC-9 (SPIA/FDA), PC-14; **AS-1–AS-3 basic** (bonds/cash/equity, defaults, reinvestment); ESG-1; RG-3 (VM-20), **RG-4 (CFT)**, RG-2 (LFPB/DAC), RG-11 (US tax reserves); NF-2, NF-3, NF-8, NF-12, NF-13; SOC 2 Type I. 3–5 US design partners on **early-access production contracts** |
| **GA-US (1.0)** | M15–24 | Rest of the US M items: MS-5 and R-3 (nested, C3); RG-2 (MRB); RG-3 (VM-21; VM-22 for SPIA/FDA/FIA/structured settlements; GOES); RG-5 (M parts); RG-10 (pricing, planning, ALM); PC-7 (VA); PC-8 (IUL/VUL); PC-9 (FIA/RILA, structured settlements); full AS-1–4; R-8; D-3 (compression, needed by §19.4); D-8 (full); D-14; E-1(c) GPU; E-3; E-9 (BYOC); AOC-5; CL-1–5; G-8, G-11; FX-1, FX-2; LIB-1, LIB-2 (library packaging = MS-3 implementation + update SLA); migration toolkit (§26); AIG-4; **S items pulled forward:** RG-1 core GMM/PAA for US multinationals. **All NFRs except those tied to later regions or dates:** NF-7 ISO 27001 (GA+12 months, i.e. GA-UK/EU), NF-9 non-US regions, NF-16 non-English localisation. **SOC 2 Type II** |
| **GA-UK/EU** | M24–30 | RG-1 (IFRS 17 full incl. VFA), RG-6 (SII/Solvency UK incl. MA/TMTP), RG-10 (EV), RG-11 (UK tax); PC-2, PC-4 (with-profits, C2), PC-6, PC-10 (BPA); FX-3, FX-4; AOC-4, AOC-6; **AIG-2 (EU AI Act support)**; NF-7 ISO 27001; NF-9 EU/UK regions; NF-11 DORA pack; NF-16 German and French |
| **GA-Asia** | M30–36 | RG-8 (M parts: India, HK, SG, MY, ID); PC-5 (Asian/Indian par), PC-13 (takaful); NF-16 Asian localisation; NF-9 India and Singapore regions |
| **1.x** | M24–42 (parallel stream) | AI-4 (agentic), AI-5 (rebuild agent GA), AI-7; AIG-3; D-9, D-10, D-11 (model-as-API); E-8; G-10; ESG-2; L-10; PC-10 (US PRT incl. VM-22 PRT), PC-11, PC-12, PC-15; R-10 (proxy), R-11, R-12 (experience studies); RG-5 (S parts), RG-7 (Bermuda), RG-8 (S parts), RG-9, RG-12 (climate); FX-5, FX-6; AOC-3, AOC-8; DX-4, DX-8; MS-9 |

**Reconciliation of priority tags against phases.**
- Every M item appears at or before its GA.
- Every S item appears in a phase. Some are pulled forward because of dependencies: D-3 and the RG-1 core.
- C items (AI-6, PC-16, self-hosted control plane) are unscheduled by definition.
- **VM-22 PRT** is scheduled with PC-10 in 1.x, which is within the VM-22 optional transition period that ends in 2029. RG-3's M tag therefore covers VM-22 for individual annuities only.

**MVP descope ladder** (if the schedule slips, items move to GA-US in this order, keeping the design-partner value proposition intact):
1. D-8 core reports, replaced by API/Excel extracts.
2. AI-2 and AI-3, keeping AI-1.
3. L-9 grid editor, keeping the wizard for assumption changes.
4. PC-3 US par.
5. R-7 vectorised solve, replaced by a scalar solve.
6. RG-2 LDTI DAC (keep LFPB).

**Never descoped from the MVP:** the C2 engine, VM-20 with assets, CFT, governance (G-2–G-7), D-12 and the reconciliation harness.

### 27.4 Key risks
Likelihood (L) and impact (I) are rated H, M or L.

| # | Risk | L | I | Mitigation | Owner |
|---|---|---|---|---|---|
| K1 | Library depth and regulatory correctness take longer than planned | H | H | Beachhead sequencing; library actuaries hired early; co-development with consultancies; independent validation (§31) | Head of Actuarial Content |
| K2 | Incumbent legal action (trade secret, tortious interference) | M | H | §26.1 guardrails; clean-room process; counsel review; insurance; never touch FIS materials | General Counsel |
| K3 | Switching inertia: regulator, auditor and board conservatism | H | H | Parallel-run tooling, validation packs, auditor workspace, SOC 1 report, design partners as references | CEO / Head of Sales |
| K4 | Funding shortfall before GA-US | M | H | Staged raise (§29.4); paid pilots; services revenue; capital-efficient offshore hiring | CEO / CFO |
| K5 | Numerical errors in governed numbers | M | H | Golden tests, dual implementation, independent validation, CI tolerance gates (§31) | CTO / Head of QA |
| K6 | AI hallucination contaminates governed outputs or commentary | M | H | AIG-1 and AIG-6 (numbers only from the engine; human approval); AI evaluation gates (AIG-4) | Head of AI |
| K7 | Incumbents close the gap (FIS adds Python/Git; WTW and Moody's agentic AI; GPU everywhere) | H | M | Compete on openness, explainability, DevOps, transparent pricing and customer-owned code, which are structurally hard for incumbents to copy (§33) | CPO |
| K8 | Talent: actuaries resist a code-first tool | M | M | L-9 low-code; conversion track; AI pair-programmer; university programme | CPO |
| K9 | Compute cost pass-through erodes margin or causes "surprise bills" | M | M | E-7 cost estimator and caps; BYOC; spot/preemptible capacity with checkpoints | VP Platform |
| K10 | GPU supply and pricing volatility | M | L | CPU-first performance; multi-cloud GPU sourcing; reservation contracts for close windows | VP Platform |
| K11 | Design partners churn before GA | M | H | Contractual pilot terms; executive sponsors; fast iteration; credits | Head of Customer Success |
| K12 | Security incident involving policyholder data | L | H | NF-7–NF-10; BYOC default for large customers; minimisation and pseudonymisation | CISO |
| K13 | Open-core cannibalisation: the Apache-licensed single-node C1/C2 engine is "good enough" for consultancies or small insurers | M | M | Community edition excludes distributed, GPU and C3 execution, governance (environments, approvals, manifests), certified libraries and support. Licence terms are unaffected, but value for production use sits in the commercial layer. Track community-to-paid conversion as KPI E3 | CPO / CRO (revenue) |
| K14 | Rust talent scarcity in delivery hubs, and an immature Rust GPU ecosystem (ADR-001) | M | M | Senior Rust hires in the US/UK/Poland, with structured Rust training for others; actuaries never need Rust; GPU kernels generated as CUDA/Triton rather than written in Rust; a stable IR boundary keeps a C++ back end possible | CTO |

---

## 28. Strategic options: build, buy, partner, open-core

| Option | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **O1: Build from scratch** | New DSL, compiler, engine and platform | Full control of architecture (C1/C2/C3 engine, GPU, governance); no legacy | Longest time to market; library depth must be built | **Core of the recommendation** |
| **O2: Build on open source** | Fork or extend lifelib/modelx or Heavylight for the DSL; JAX/XLA for GPU | Faster start; community goodwill; Python-native | modelx is a single-maintainer project, and its object model is not designed for C2/C3 distributed execution or governance; JAX imposes functional constraints | **Partial:** use JAX/XLA (or Triton) as one GPU backend, offer lifelib-compatible import as an on-ramp, and contribute upstream. The engine IR stays our own |
| **O3: Acquire a small vendor** | E.g. a niche actuarial software house with customers and libraries (candidates such as Mo.net/Software Alliance or RNA R³S; availability UNVERIFIED) | Instant customers, libraries, regulatory credibility | Legacy architecture to integrate or retire; high cost; culture | **Opportunistic:** consider after Series B for library content or Asian distribution (e.g. a takaful/Asia library house) |
| **O4: Partner for adjacent layers** | ESG (Conning GEMS/GOES, Moody's ESG), subledger (SAP FPSL, Aptitude, OneSumX), data (Snowflake, Databricks), cloud marketplaces | Avoids building commodity or specialist layers; credibility | Dependency on partners | **Yes:** ESG and subledger via partnership and connectors; a lightweight native subledger only later (C) |
| **O5: Pure low-code (Slope/Mind-style)** | Browser low-code only | Fast adoption by non-programmers | Ceiling on complexity; weak for ALM/nested; Git-unfriendly | **No** as the primary model; **yes** as layer L-9 over the code-first DSL |

**Open-core decision**
- **Community edition.** Licensed under **Apache 2.0**: the DSL, compiler front end and single-node C1/C2 engine. This builds talent and trust and answers the lock-in objection.
- **Commercial moats (not open source).**
  - the distributed, GPU and nested scheduler (C3) and cost-aware cloud runtime
  - certified regulatory libraries with validation packs and update SLAs
  - the governance platform (environments, manifests, approvals, audit), results store, orchestration and close tooling
  - AI services
  - SaaS operations, support and SLAs
- **Library source.** Visible to licensees under a commercial source-available licence. Customers may modify via overlays; redistribution is not allowed.

---

## 29. Team, build cost and business case

All figures are planning estimates for funding discussions.

### 29.1 Staffing plan (FTE, end of phase)
| Function | Foundation + MVP (M0–15) | GA-US (M24) | GA-UK/EU & Asia (M36) |
|---|---|---|---|
| Compiler/DSL & IR (Python front end, Rust back end) | 5 | 6 | 7 |
| Engine runtime (Rust: CPU, C2/C3 scheduler); includes 2–3 senior Rust engineers from M0 | 5 | 7 | 8 |
| GPU backend (CUDA/Triton kernel generation, Rust host) | 1 | 4 | 5 |
| Platform/SRE/cloud (control plane, BYOC) | 5 | 8 | 10 |
| Security & compliance | 1 | 3 | 4 |
| IDE/front end/UX | 5 | 7 | 8 |
| Data, results store, orchestration | 4 | 6 | 7 |
| AI engineering & evaluation | 2 | 4 | 6 |
| Library actuaries: US | 7 | 9 | 9 |
| Library actuaries: UK/EU | 1 | 4 | 7 |
| Library actuaries: Asia | 0 | 2 | 6 |
| QA & independent validation | 4 | 7 | 9 |
| Product management & design | 3 | 4 | 6 |
| Docs, training & certification | 1 | 3 | 5 |
| Customer success & implementation | 2 | 8 | 15 |
| Sales, partnerships & marketing | 3 | 8 | 14 |
| G&A (finance, legal, people) | 3 | 5 | 7 |
| **Total** | **≈52** | **≈95** | **≈134** |

### 29.2 Cost estimate
- **Assumptions.** Blended fully loaded cost about **US$170k/FTE/year** (hub mix: US/UK about 45%, Poland/Serbia about 30%, India about 25%). Cloud for development, CI and benchmarks is US$1–2m a year. Legal, IP, certifications and insurance are about US$1m a year. Marketing programmes rise from US$0.5m to US$3m a year.
- **Cash need:**

- **Independent validation** of certified regulatory packs (§31.1 point 6) is budgeted separately. Assume about 12–15 packs over Y1–Y3 at US$0.2–0.5m each, i.e. US$3–6m in total and about US$0.5–2m a year.
- The staffing table reflects the strengthened library and QA lines (US library actuaries 7 at MVP and 9 at GA-US; QA 4 and 7).

| Year | Payroll | Cloud | Legal/certs | Marketing | Validation | **Total spend (US$m)** |
|---|---|---|---|---|---|---|
| Y1 | ≈ 6.5 | 1.0 | 1.0 | 0.5 | 0.5 | **≈ 9.5** |
| Y2 | ≈ 12.5 | 1.5 | 1.0 | 1.5 | 1.5 | **≈ 18** |
| Y3 | ≈ 19.5 | 2.0 | 1.0 | 2.5 | 2.0 | **≈ 27** |
| Y4 | ≈ 23.5 | 2.0 | 1.0 | 3.0 | 1.5 | **≈ 31** |
| Y5 | ≈ 25.5 | 2.0 | 1.0 | 3.0 | 1.0 | **≈ 32.5** |

  Payroll is based on average headcount over the year (about 38, 74, 115, 138 and 150 FTE) × US$170k. This assumes a **founding team of about 20–25 FTE at M0**, e.g. a seed-funded team or an acqui-hired engineering team, ramping to 52 by M15. **Cumulative spend to GA-Asia (end of Y3): about US$54m. Through Y5: about US$118m. Y6: about US$34m.**

### 29.3 Market sizing (estimates)
- **TAM.** The global spend on life/annuity/health actuarial projection platforms (licences + vendor cloud) is estimated at **US$1.5–2.5bn a year**, consistent with third-party reports of US$1.9–2.7bn for "actuarial modelling software" (§13.5). It covers about 2,500–3,500 insurer and reinsurer entities; Prophet alone reports about 850–1,000 sites.
- **SAM (beachhead segments):**

Average annual spend is incumbent vendor spend (licence + maintenance + vendor cloud), consistent with the §12 and §27.1 range of US$0.5–1.5m for mid-size insurers, with smaller firms below that range.

| Segment | Companies | Average annual incumbent spend | SAM |
|---|---|---|---|
| US mid-market L&A (mix of small and mid-size) | ~250 | ~US$0.6m | ~US$150m |
| UK/EU mid-size life, BPA and with-profits | ~120 | ~US$0.9m | ~US$108m |
| India + SE Asia + HK/SG | ~150 | ~US$0.45m | ~US$68m |
| **Total** | **~520** | **~US$0.63m weighted** | **≈ US$325m** |

- **Meridian ACV assumption.** About 25% below incumbent spend (the §27.1 TCO model's "vendor 20 → 15"). New-logo ACV is therefore about **US$0.47m** on average, and design partners on early-access terms pay about US$0.3m.
- **SOM.** About 33 customers by year 5, giving **≈ US$16m ARR (about 5% of SAM)**. About 49 customers by year 6, giving **≈ US$25m ARR (about 8% of SAM)**. Services and partner-delivered migration add about US$4–6m a year.

### 29.4 Revenue plan, unit economics and funding
The logo curve respects the 12–24-month sales cycle and the regional GA dates. UK/EU starts with **2 design partners on early-access terms from about M20–24** (needed for the GA-UK/EU exit criterion, §30.4; supported by the 4 UK/EU library actuaries in place by M24). Full-price UK/EU logos follow GA-UK/EU (M30), and Asian logos follow GA-Asia (M36), both of which fall in Y3. **Contracted ARR** (year-end) and **recognised subscription revenue** are shown separately. Recognised revenue = the average of opening and closing ARR minus the 50% dual-running credit on new logos' first year (§26.6).

| Year | New logos | Cumulative logos | Contracted ARR (US$m, year-end) | Dual-running credit (US$m) | Recognised subscription revenue (US$m) | Services / pilots (US$m) | Notes |
|---|---|---|---|---|---|---|---|
| Y1 | 0 | 0 | 0 | 0 | 0 | 0.35 (3 paid pilots; one-off) | Pilots credited against first-year subscriptions |
| Y2 | 3 (US design partners, early access) | 3 | 0.9 | 0 | 0.45 | 0.5 | GA-US at M24; 2 UK/EU design partners signed late Y2 (counted in Y3) |
| Y3 | 8 (US 6; UK/EU 2 design partners at ~US$0.3m) | 11 | 4.4 | 1.4 | 1.25 | 1.5 | GA-UK/EU at M30; GA-Asia at M36. Y3 ARR = 0.9 × 1.1 + 6 × 0.47 + 2 × 0.3 ≈ 4.4 |
| Y4 | 9 (US 5, UK/EU 3, Asia 1) | 20 | 9.1 | 2.1 | 4.65 | 3.0 | Y4 ARR = 4.4 × 1.1 + 9 × 0.47 ≈ 9.1 |
| Y5 | 13 (US 6, UK/EU 4, Asia 3) | 33 | 16.1 | 3.05 | 9.55 | 4.0 | |
| Y6 | 16 | 49 | 25.2 | 3.75 | 16.9 | 5.5 | |

ARR is built up as the prior ARR × NRR plus new logos × ACV, e.g. Y5 = 9.1 × 1.10 + 13 × 0.47 ≈ 16.1. The plan deliberately uses an **NRR of 110%**, below the ≥115% unit-economics target, as conservatism. Recognised revenue through Y6 totals about US$33m of subscriptions plus about US$15m of services and pilots, **≈ US$48m**, against cumulative spend of about US$152m: a **net burn of ≈ US$104m**.

- **Unit economics (targets).**
  - Gross margin ≥75% on subscription (excluding pass-through compute).
  - CAC payback ≤24 months. Check for Y5: sales and marketing of about US$5.4m over 13 logos gives a CAC of about US$0.41m. Gross profit per logo is about US$0.35m a year (0.47 ACV × 75% margin), halved in year 1 by the credit, so payback comes at about **20 months**.
  - NRR ≥115%, driven by added regulatory packs, entities and compute.
  - Logo churn <5% a year once in production. Switching costs then work in Meridian's favour, which is why open formats and fair exit terms are a deliberate trust commitment rather than a weakness.
- **Break-even:** in Y6, recognised revenue is about US$22m against spend of about US$34m. In Y7, about US$26–27m of recognised subscription revenue (ARR about 36m) plus about US$7m of services gives about US$33–34m against spend of about US$35m. Operating break-even is therefore expected in **late Y7 to Y8**.
- **Funding:**
  - **Series A** of about US$25m covers Y1–Y2 (spend about 27.5, revenue about 1.75).
  - **Series B** of about US$55–60m at GA-US (M24) covers Y3–Y4 (spend about 58, recognised revenue about 10).
  - **Series C, growth equity or venture debt** of about US$30–35m in Y5 bridges to break-even (Y5–Y7 net burn about US$30m).
  - **Total raised: about US$110–120m** against a modelled net burn of about US$104m to Y6 plus the Y7 residual, leaving a contingency of about 5–10%.
- **Alternative:** a strategic investor, e.g. a reinsurer, consultancy or cloud provider, in exchange for distribution.

---

## 30. Success metrics, release acceptance criteria and benchmarks

### 30.1 KPIs
| Type | KPI | Target |
|---|---|---|
| Product | P1: time to first working model (new user, term product, from template) | ≤ 1 day |
| Product | P2: quarterly close-chain duration (CL-2 reference) | ≤ 8 h at P95 |
| Product | P3: actuary hours per quarterly close cycle vs the customer's legacy baseline | −30% by the second production quarter |
| Product | P4: cost per million policy-scenario-years (published per workload) | Down ≥ 20% a year |
| Product | P5: parallel-run reconciliation pass rate (policies within tolerance, §31.3) | ≥ 99.5% at cut-over |
| Product | P6: defect escape rate (defects found in production per release) | < 1 Sev-1/2 actuarial-calculation defect per release |
| Product | P7: AI suggestion acceptance rate; AI-generated code test-pass rate | ≥ 40%; ≥ 90% |
| Product | P8: regulatory update SLA adherence (LIB-1) | 100% |
| Business | B1: design-partner conversion to paid subscription | ≥ 2 of 3–5 |
| Business | B2: ARR, NRR, gross margin | Per §29.4 |
| Business | B3: logos per beachhead | US 9 by Y3 and 20 by Y5; UK/EU 2 (design partners) by Y3, 5 by Y4 and 9 by Y5; Asia 1 by Y4 and 4 by Y5 (per §29.4) |
| Business | B4: models migrated into production | ≥ 25 by Y3 |
| Ecosystem | E1: certified practitioners | 500 by Y3; 3,000 by Y5 |
| Ecosystem | E2: certified partners (Elite) | 3 by Y3 |
| Ecosystem | E3: Community-edition monthly active users | 2,000 by Y3 |

### 30.2 Per-workload performance targets (GA, §19.3 suite)
| Benchmark | Target wall-clock | Target hardware / cost envelope |
|---|---|---|
| B1 term 5m seriatim, 3 bases | ≤ 15 min | ≤ 512 vCPU; ≤ US$25 compute |
| B2 VM-20 DR/SR, 1,000 scenarios, 500k policies | ≤ 45 min | ≤ 1,024 vCPU or ≤ 16 GPUs |
| B3 VM-21 CTE70 + nested Greeks, 200k VA | ≤ 2 h | ≤ 32 GPUs |
| B4 bulk annuity SII BEL + SCR + MA, 1m lives | ≤ 30 min | ≤ 1,024 vCPU |
| B5 with-profits C2 dynamic, 2,000 RN scenarios, 300k policies | ≤ 1 h | ≤ 1,024 vCPU |
| B6 IFRS 17 CSM roll-forward, 10k groups × 40 quarters + AoC | ≤ 10 min | ≤ 64 vCPU |
| B7 CFT: NY7 + 1,000 GOES, 5,000 CUSIPs | ≤ 1 h | ≤ 1,024 vCPU |

These targets are revised after the Foundation phase, using profiling results. The relative targets (E-3) are verified by customer-run comparisons.

### 30.3 Benchmarking method and legal constraints
- **Meridian's own benchmarks.** Meridian publishes its absolute benchmark results with full specifications: model code (open), synthetic data generator, hardware and cost.
- **Comparisons with Prophet or other platforms** are run by customers (or by consultancies engaged by them) on their own licences, with identical data, assumptions and conventions. Results are published only with customer consent and where the vendor licence permits. Many software licences restrict publishing benchmarks [Prophet terms UNVERIFIED]. No Meridian employee operates a competitor's software.
- **Comparison measures:** wall-clock time, compute cost at list cloud prices, and actuary hours for a defined change task (e.g. adding a rider).

### 30.4 Release acceptance criteria
| Release | Exit criteria |
|---|---|
| **Pilot (per customer)** | Pre-agreed product block reconciles: policy-level reserves/cash flows within §31.3 tolerances for ≥99% of policies; all others explained (convention or legacy bug); total-level within 0.05% after convention mapping, with any systematic residual above 0.01% explained (§31.3); run time and actuary-effort measured; customer sign-off |
| **MVP** | All MVP cut-list IDs (§27.3) pass their acceptance tests; NF-2, NF-3 and NF-13 met; ≥ 3 design partners have each run ≥ 1 production-shaped model in parallel for ≥ 1 quarter; SOC 2 Type I issued; no open Sev-1 defects |
| **GA-US** | All M items pass acceptance tests; §30.2 B1–B3 and B7 targets met; VM-20/21/22, LDTI, CFT certification packs independently validated (§31.2); ≥ 2 design partners have completed ≥ 1 full quarterly reporting cycle **in parallel** (Meridian vs legacy) within §31.3 tolerances, with an **auditor walkthrough** of controls and reconciliation, and ≥ 1 has committed to Meridian as the system of record for its next statutory or GAAP filing. A filed cycle on Meridian is a GA+6-month milestone; SOC 2 Type II; DR test passed; documentation and training (Foundations, Model Developer) live |
| **GA-UK/EU** | M (EU/UK) items pass; B4–B6 targets met; SII/IFRS 17 packs independently validated; ≥ 1 UK/EU design partner (early-access, signed about M20–24) through a year-end close in parallel; ISO 27001; DORA contractual pack |
| **GA-Asia** | M (Asia) items pass; Ind AS 117/IRBCF and ≥ 2 other Asian regime packs validated; localisation for ≥ 3 languages; in-country data residency for India |

Each requirement ID carries **acceptance tests in the requirement repository**: Given/When/Then plus a reference dataset. The traceability matrix (§34) links IDs to tests.

---

## 31. Validation and assurance strategy

### 31.1 Layers of assurance
1. **Unit tests per variable.** Expected values for hand-checkable cases are generated independently (spreadsheet or a second implementation).
2. **Golden test cases per library.**
   - Policy-level cases with expected outputs produced by an **independent implementation**: a separate team, a separate language (e.g. a reference implementation in a different stack) or independent consultancy calculations.
   - Published regulatory examples are included where they exist: NAIC/AAA practice-note examples and IASB/TRG illustrative examples.
3. **Property-based and metamorphic tests.**
   - Zero mortality gives zero death claims.
   - Doubling sum assured doubles benefits.
   - Grouped results converge to seriatim results as the groups become finer.
   - Risk-neutral martingale tests on scenarios.
   - Reserve monotonicity tests.
4. **Cross-target equivalence.** CPU, GPU and distributed results are compared on every build (NF-13).
5. **Regression gates in CI.** Any change to results on the regression datasets needs an explicit, reviewed "expected change" approval.
6. **Independent third-party validation.** An external actuarial firm validates each certified regulatory pack before release (methodology review + replication of a sample). Its validation report goes into the customer evidence pack.
7. **Customer acceptance.** Parallel runs (§26.7) with customer-defined tolerances.

### 31.2 Certification pack contents (per regulatory library)
- Methodology document mapped clause by clause to the regulation
- Assumptions and limitations
- Test inventory and results
- Independent validation report
- Change log mapped to regulatory amendments
- Known issues
- Model-risk tiering guidance

### 31.3 Numerical reconciliation tolerances (defaults, configurable)
| Comparison | Variable type | Default tolerance |
|---|---|---|
| Engine vs engine (CPU/GPU/distributed) | All float64 | Relative 1e-9 or absolute 1e-6 currency units |
| Migration parallel run, policy level | Balances (reserves, account values, CSM) | max(0.1% relative, 1 currency unit) |
| Migration parallel run, policy level | Flows per period | max(0.5% relative, 1 currency unit) for each of the first 10 years; aggregated PV within 0.1% |
| Migration parallel run, total level | Reserves, BEL, CSM, SCR | **0.05% relative after convention mapping** (§26.4). Any systematic difference above 0.01% must be explained and attributed to a documented cause in the reconciliation report. Policy-level and total-level tests are applied together; a policy-level pass does not excuse an unexplained aggregate bias |
| Stochastic results | Mean/CTE over identical scenario sets | 0.05% relative |
| Rates/ratios | e.g. NPR, IRR | Absolute 1e-6 |

**Breach handling.** Breaches are classified as *convention difference*, *legacy defect*, *Meridian defect* or *data difference*. All must be explained before cut-over.

### 31.4 Regulator and auditor acceptance pathway
- **Early engagement.** Engage design-partner auditors early, using the SOC 1 Type II report and the auditor workspace.
- **Regulator briefings.** Brief regulators (PRA, NAIC/state regulators, IRDAI, MAS) on Meridian's methodology and controls, without seeking any formal "approval" of the software. Regulators approve firms' models, not vendors.
- **Validation partners.** Publish a list of independent validation partners.

---

## 32. Licensing, IP, data-use and support terms

### 32.1 IP and licence principles (customer contract)
- **Customer-owned models.** The customer owns all models, code, overrides, configurations, assumptions and outputs it creates, including extensions of Meridian libraries. Meridian makes **no derivative-work claim** on customer code.
- **Library licence.** Certified libraries are licensed (source-visible) for the subscription term. Customers have a **perpetual right to keep using the last library version received** for reproducing historical results after termination. This right comes with a **perpetual, non-production "reproduction licence"** to the archived *commercial* engine container of the versions used, including distributed and C3 nested execution. Historical VM-21, projected-SCR and nested runs can therefore be re-executed after exit for audit, regulatory or litigation purposes (supports NF-12). The Community engine alone would not suffice for those runs.
- **Open format guarantee.** The model language specification is published. Results and data are always exportable in open formats at no charge. An export tool is maintained for every release.
- **Exit assistance.** Up to 12 months of transition assistance at published rates, and full data and model export within 30 days of request. The exit plan meets DORA, EIOPA and PRA outsourcing requirements.
- **Escrow.** Source code (commercial components) is held in third-party escrow. Release triggers: insolvency, cessation of support for a major version without a replacement, or a change of control followed by material breach of support SLAs.
- **IP indemnity.** Meridian indemnifies customers against third-party IP infringement claims arising from Meridian software.
- **No benchmark ban.** Customers may benchmark Meridian and publish results with reasonable methodology disclosure.
- **AI and data use.** Customer data and code are never used to train shared models without written opt-in. Telemetry is limited to the published metadata schema (NF-9).
- **Audit and access rights** for customers and their regulators, as outsourcing rules require.
- **Price protection.** Renewal uplift capped at CPI + 3% for multi-year terms.

### 32.2 Community edition licence
- Apache 2.0 with a patent grant. Contributor licence agreement for contributions.

### 32.3 Support model
| Severity | Definition | Response | Update cadence | Coverage |
|---|---|---|---|---|
| Sev 1 | Production close blocked or wrong results in governed production | 30 min | Hourly | 24×7 |
| Sev 2 | Major function degraded, workaround exists | 2 h | 4-hourly | 24×5 (24×7 in close windows) |
| Sev 3 | Minor defect / question | 1 business day | Daily | Business hours, follow-the-sun |
| Sev 4 | Enhancement request | 3 business days | — | Business hours |

- **Two desks.** A technical desk (platform/engine) and an **actuarial desk** staffed by qualified actuaries (FSA, FIA or equivalent) for methodology and library questions.
- **Named roles.** Customer success manager for Professional and Enterprise tiers; technical account manager for Enterprise.
- **Close-window concierge.** Customers pre-register their close calendar, and Meridian monitors their runs proactively.
- **Implementation services.** Offered directly or through certified partners, with fixed-price migration packages (§26.6).
- **Public status page and RCAs.** Root-cause analyses for Sev 1 incidents are delivered within 5 business days.

---

## 33. Competitive response scenarios

| Scenario | Likelihood | Expected incumbent move | Meridian response |
|---|---|---|---|
| FIS discounts or bundles (multi-year renewal with steep discount, free Production Manager compute) | High | Lock customers in through renewal windows | TCO evidence centred on people productivity; dual-running credits; target renewal windows 18 months ahead; Community edition builds internal champions |
| FIS sells Prophet to private equity (Aug 2026 review) | Medium | (a) Under-investment and price rises, or (b) aggressive lock-in and litigation | (a) "Stability" campaign: escrow, open formats, roadmap; (b) strengthen legal guardrails; emphasise customer code ownership |
| FIS adds Python authoring and Git integration | Medium | Neutralises the openness message partly | Openness is structural for Meridian (Apache core, open format, export rights). Lead on the C2/C3 engine, trace explainability and close-time SLAs |
| Moody's, WTW or FIS ship mature agentic AI | High | AI parity claims | Compete on *governed* AI (AIG-1–6), the reconciliation-driven rebuild agent and AI evaluation transparency |
| Aon PathWise wins on GPU speed | Medium | Speed narrative | Match on GPU for C1/C3; win on breadth, low-code, governance and CPU efficiency for branch-heavy models |
| Incumbent litigation against Meridian | Low–Medium | Injunction attempts, trade-secret claims | §26.1 guardrails, clean-room records, IP counsel, insurance; no ex-FIS code or documents; hiring policy forbids bringing confidential materials |
| Akur8 Life (Slope) scales in US mid-market | Medium | Competes in Beachhead A | Depth in PBR/CFT/ALM and the C2 engine; open core; partner channel |

---

## 34. Requirements traceability

### 34.1 Prophet weaknesses → requirements
| Weakness | Requirement IDs |
|---|---|
| W1 Proprietary DSL & limits | L-1, L-4, L-5, L-9, L-10 |
| W2 Debugging opacity | L-6, DX-2, DX-3, DX-4, AI-2 |
| W3 No native Git | G-1, G-2, G-3, DX-7 |
| W4 C++/Windows dependency | E-1, NF-14 |
| W5 Many bolt-on components | §25 architecture, §27.1 (all core included) |
| W6 Paid flexible grouping | D-5, D-6 |
| W7 Proprietary formats / TB outputs | D-5, D-6, E-4, §32.1 open-format guarantee |
| W8 GPU rewrite | E-1, §19.4 |
| W9 Re-hosted cloud / surprise bills | E-2, E-7, E-9, CL-3 |
| W10 Opaque pricing | §27.1 |
| W11 Lock-in / code ownership | §32.1, §28 open core, §26 |
| W12 Library merge pain | MS-3, LIB-2 |
| W13 Talent scarcity | L-9, AI-3, §27.2 training |
| W14 Late AI | AI-1–AI-7, AIG-1–AIG-6 |
| W15 DCS data plumbing | D-1, D-2, D-3, AI-7 |
| W16 Ownership uncertainty | §32.1 escrow, §33 |
| W17 No model-as-API | D-11 |
| W18 Multi-currency/entity | MS-11, FX-1–FX-6 |
| W19 Downstream stochastic stats | D-13, R-2 |

### 34.2 Personas → key requirements
| Persona | Key IDs |
|---|---|
| Model developer | L-*, MS-*, DX-*, AI-3, G-2/3 |
| Valuation/reporting actuary | R-6, AOC-*, CL-*, D-8, D-12, RG-* |
| Pricing actuary | R-5, R-7, L-9, D-11, RG-10 |
| ALM/risk/capital | R-3, R-4, §19.4, AS-*, ESG-*, R-10, FX-3 |
| Model governance/validation | G-4, G-5, G-7, G-8, G-11, §31, AIG-* |
| IT/platform | E-2, E-9, NF-5–NF-15, §25 |
| Finance/accounting | RG-1, RG-2, AOC-4, AOC-5, D-9, FX-4–6 |
| Exec | §27.1 TCO, CL-2, KPIs §30.1 |
| Auditor/regulator | G-11, §31.4, §26.5 |
| Non-programmer actuary | L-9, AI-1, AI-3, DX-3 |

### 34.3 Feature parity matrix: Meridian (target at regional GA) vs incumbents
Ratings: ● strong, ◐ partial, ○ weak or absent. Incumbent ratings are based on the public evidence in Part I.

| Capability | Prophet | AXIS | RAFM | PathWise | Meridian target |
|---|---|---|---|---|---|
| Library breadth (global) | ● | ◐ (NA-centric) | ◐ | ○ | ◐ at GA-US → ● by M36 in target regions |
| US PBR/LDTI/CFT | ● | ● | ● | ◐ | ● |
| SII/IFRS 17 | ● | ● | ● | ◐ | ● (GA-UK/EU) |
| Dynamic ALM / with-profits | ● | ◐ | ● | ◐ | ● (C2 engine) |
| Nested stochastic performance | ◐ | ◐ | ● (GPU 2026) | ● | ● |
| GPU from same source | ◐ (looped modules) | ○ | ● | ● (GPU-native) | ● (with documented constraints) |
| Transparency / trace explain | ◐ | ◐ | ◐ | ◐ | ● |
| Git-native / CI | ○ | ○ | ◐ | ◐ | ● |
| Python interoperability | ○ | ○ | ◐ | ● | ● |
| Low-code for non-programmers | ◐ (wizards) | ● (chassis) | ◐ | ● (spreadsheet studio) | ● (L-9) |
| Cloud-native elastic | ◐ (SaaS from 2024) | ● (AXIS Cloud) | ● (vGrid) | ● | ● |
| Agentic AI | ◐ (Q&A 2026) | ◐ | ● (Oct 2026) | ○ | ● (governed) |
| Open format / exit | ○ | ○ | ○ | ○ | ● |
| Transparent pricing | ○ | ○ | ◐ (PAYG compute) | ○ | ● |
| Talent pool | ● | ◐ | ◐ | ○ | ○ → ◐ (Python skills, conversion track) |

---

# APPENDICES

## Appendix A: Glossary

| Term | Meaning |
|---|---|
| AoC | Analysis of change / movement |
| ALS | Prophet Asset Liability Strategy library |
| BEL | Best Estimate Liability (Solvency II) |
| CSM | Contractual Service Margin (IFRS 17) |
| CTE | Conditional Tail Expectation |
| DCS | Prophet Data Conversion System |
| ESG | Economic Scenario Generator |
| GOES | NAIC Generator of Economic Scenarios (Conning-built), replacing the AAA generator for VM-20/21/22 and C-3; effective date expected 2027 (to be confirmed) |
| IDR | Insurance Data Repository (Prophet results database) |
| LDTI | Long-Duration Targeted Improvements (US GAAP ASU 2018-12) |
| LSMC | Least Squares Monte Carlo |
| MP / MPF | Model point / model-point file |
| MRB | Market Risk Benefit (LDTI) |
| PBR | Principle-Based Reserving (VM-20/21/22) |
| RA | Risk Adjustment (IFRS 17) |
| SCR / MCR | Solvency/Minimum Capital Requirement |
| SPCODE | Prophet sub-product code |

## Appendix B: Open questions and research gaps
1. Actual Prophet price points: validate through customer interviews and procurement contacts.
2. Prophet API technology (COM, .NET or REST) and the Python support roadmap.
3. Full content of the US 360, Unit Linked, International, French and ALS 2019 datasheets.
4. Whether Prophet falls within FIS's Aug 2026 strategic review.
5. Verbatim user sentiment from r/actuary and the Actuarial Discussion Forum, which could not be fetched. Run a manual pass and conduct interviews.
6. Prophet coverage of AG38, AG49-A, AG53, LICAT, J-ICS, ICS, LAGIC and MA.
7. Prophet contract terms: benchmark-publication restrictions, termination notice, audit rights, renewal uplifts and typical term length.
8. How Prophet handles multiple currencies and entities (§4.1e).
9. Prophet Professional run types and run-parameter details beyond those described in §4.1a.
10. Typical Prophet run-time baselines by workload. Collect them from design partners as a customer-run baseline (§30.3).
11. The actual SPCODE limit: one source says 9999, but a public example file shows a six-digit code.
12. Exact GOES effective dates for VM-20/21 and C-3. Track NAIC LATF adoption of the 2027 Valuation Manual.
13. Current status of the EU AI Act high-risk application dates (Digital Omnibus proposals).
14. Whether the "Experience and Rating Manager" succeeds Glean, and what modern assumption-fitting it offers.
15. Calibrate the planning estimates in §26.6 (migration effort), §27.1 (price points) and §29 (team, cost, market sizing) through design-partner discovery and buyer interviews.

## Appendix C: Sources

(The URLs below were gathered during the research of 2 Nov 2026. Many fisglobal.com and insuranceerm.com pages were read via search snippets because direct fetches were blocked.)

- R1. FIS, "History of Prophet", Indonesian Actuaries Summit deck, 2017: https://www.aktuaris.or.id/download/ID%20CARD%20P.A.I%202nd%20summit.pdf
- R2. Finextra, SunGard buys actuarial system from Deloitte (2005): https://www.finextra.com/pressarticle/6523/sungard-buys-actuarial-system-from-deloitte-acquires-getpaid-corporation
- R3. Insurance Times, Bacon & Woodrow split: https://insurancetimes.co.uk/bacon-and-woodrow-to-merge-divisions/1355467.article
- R4. Risk.net, Deloitte sells Prophet: https://www.risk.net/1515203/deloitte-sells-prophet
- R5. FIS ALS Modular Training Brochure: https://www.prophet-web.com/assets/Datasheets/Training/Prophet-ALS-Modular-Training-Brochure.pdf
- R6. Insurance-Canada, SunGard launches iWorks Prophet Enterprise (2007): https://insurance-canada.ca/2007/07/12/sungard-launches-iworks-prophet-enterprise-new-generation-actuarial-modelling/
- R7. InsuranceNewsNet, SunGard adds grid computing to hosted iWorks Prophet (2009): https://insurancenewsnet.com/oarticle/SunGard-Adds-Grid-Computing-Capacity-to-its-Hosted-iWorks-Prophet-Actuarial-Solu-a-127664
- R8. Actuarial Post, SunGard ALS update (2013): https://actuarialpost.co.uk/article/sungard-launches-insurance-asset-liability-modeling-solution-5133.htm
- R9. FIS 10-K FY2015 and FY2025: https://www.sec.gov/Archives/edgar/data/0001136893/000113689316000061/a10-k2015.htm ; https://www.sec.gov/Archives/edgar/data/1136893/000113689326000013/fis-20251231.htm
- R10. Risk.net, IFRS 17 solution provider of the year FIS: https://risk.net/awards/6972131/ifrs-17-solution-provider-of-the-year-fis
- R11. FIS IFRS 17 Group Calculations Library datasheet: https://www.prophet-web.com/assets/Datasheets/New-Brand-Datasheets/Q2-2018/IFRS-17-Group-Calculations-Library.pdf
- R12. InsuranceERM, LDTI solution of the year 2020 (FIS Prophet): https://www.insuranceerm.com/content/awards/insuranceerm-annual-awards-2020-americas/winners/ldti-solution-of-the-year-fis-prophet.html
- R13. Conning–FIS collaboration (2018): https://www.conning.com/about-us/news/conning-and-fis-collaborate-to-integrate-economic-scenario-generation-and-actuarial-modeling
- R14. FIS Insurance Risk Suite product sheet 2021: https://www.fisglobal.com/-/media/fisglobal/files/PDF/product-sheet/Insurance-Insurance-Risk-Suite-Product-Sheet-2021.pdf
- R15. Prophet supported versions: https://www.prophet-web.com/support/supported-versions/
- R16. InsuranceERM, "The power of SaaS for actuarial modelling": https://www.insuranceerm.com/content/partnered-content/market-insight/the-power-of-saas-for-actuarial-modelling.html
- R17. The Register / AWS vendor voice on FIS: https://vendorvoice.theregister.com/aws_fis_capital_markets
- R18. FIS launches AI Assistant (Feb 2026): https://www.stocktitan.net/news/FIS/fis-launches-24-7-ai-assistant-to-ease-risk-models-lz1ahh7jfkpx.html ; https://insurance-canada.ca/2026/03/18/fis-launch-ai-assistant-risk-models-management/
- R19. FIS awards release (Jul 2026): https://financialit.net/node/71645 ; https://www.businesswire.com/news/home/20260714378409/en/
- R20. Payments Dive, FIS seeks to sell parts of Capital Markets unit (Aug 2026): https://www.paymentsdive.com/news/fis-seeks-to-sell-parts-of-capital-markets-unit/826952/
- R21. Prophet "About us" and events: https://www.prophet-web.com/about-us/ ; https://www.prophet-web.com/events/
- R22. Prophet libraries page (archived Jan 2022): https://web.archive.org/web/20220128231838/https://www.prophet-web.com/prophet-products/libraries/
- R23. MetLife ALS library job ad: https://builtinottawa.com/job/actuarial-lead/6215439
- R24. US VA Technical Reference Model, Prophet: https://www.oit.va.gov/Services/TRM/ToolPage.aspx?tid=13173
- R25. PMCS security product sheet: https://www.prophet-web.com/assets/Datasheets/New-Brand-Datasheets/0066INSPMCS-Security-Product-SheetWEB.pdf
- R26. Finalyse, Actuarial modelling using FIS Prophet: https://www.finalyse.com/blog/insurance/actuarial-modelling-using-fisr-prophet
- R27. FIS product page: https://www.fisglobal.com/en/products/fis-insurance-risk-suite
- R28. Vincent Chen, Prophet best practice: https://insurance.vincent-chen.com/en/prophet/best-practice/
- R29. Actuarial Working Life, Prophet indicators: https://actuarialworkinglife.blogspot.com/2020/12/setup-Prophet-indicator.html
- R30. Actuarial Working Life, SPCODE: https://actuarialworkinglife.blogspot.com/2025/05/prophet-techq-04-spcode.html
- R31. SOA CompAct 2013, "Reminiscences of a Prophet operator": https://www.soa.org/news-and-publications/newsletters/compact/2013/october/com-2013-iss49/reminiscences-of-a-prophet-operator/
- R32. Oliver Wyman, "Profiting from Prophet: Model Housekeeping": https://www.readkong.com/page/profiting-from-prophet-model-housekeeping-oliver-wyman-3600227
- R33. Actuarial Working Life, calculation loop: https://actuarialworkinglife.blogspot.com/2025/05/prophet-techq-03-calc-loop.html
- R34. Prophet Advanced Modelling (archived): https://web.archive.org/web/2022/https://www.prophet-web.com/prophet-solutions/Advanced-Modelling/
- R35. Prophet supported compilers: https://www.prophet-web.com/support/supported-compilers/
- R36. Actuarial Working Life, Prophet modelling 3: http://actuarialworkinglife.blogspot.com/2011/07/prophet-modeling-3-something-about.html
- R37. Actuarial Working Life, NB processing: https://actuarialworkinglife.blogspot.com/2025/05/prophet-techq-02-nb-processing.html
- R38. mpfi (Python Prophet file reader): https://pypi.org/project/mpfi/ ; https://github.com/bensonby/mpfi
- R39. Alteryx Community, Prophet connection: https://community.alteryx.com/t5/Alteryx-Designer-Desktop-Discussions/ACTUARIAL-Prophet-Connection-to-Alteryx/td-p/1178292 ; mpduck: https://github.com/MatthewMooreZA/mpduck
- R40. Finalyse (R26); FIS DCS sheet (via Scribd snippet)
- R41. Prophet Assumptions Manager (prophet-web snippets)
- R42. Prophet PBR page (archived): https://web.archive.org/web/2022/https://www.prophet-web.com/prophet-solutions/principles-based-reserving/
- R43. FIS GPU/CPU looped modules case study: https://www.fisglobal.com/-/media/fisglobal/files/pdf/case-study/insurance-risk-suite-prophet--gpu-cpu-looped-modules-case-study.pdf
- R44. InsuranceERM Actuarial Modelling Special Report 2025: https://www.graemegroup.org/wp-content/uploads/2025/06/InsuranceERMs-Actuarial-Modelling-Special-Report-2025.pdf
- R45. SOA Emerging Topics 2021 (Jeorgensen/Strother, Oliver Wyman survey): https://www.soa.org/digital-publishing-platform/emerging-topics/et-2021-11-jeorgensen-strother/
- R46. Prophet Conventional Library datasheet: https://web.archive.org/web/20220128231838/https://www.prophet-web.com/assets/Datasheets/New-Brand-Datasheets/Q2-2018/Prophet-Conventional-Library.pdf
- R47. Prophet IFRS page (archived): https://web.archive.org/web/2022/https://www.prophet-web.com/prophet-solutions/ifrs/
- R48. Prophet US GAAP page (archived): https://web.archive.org/web/2022/https://www.prophet-web.com/prophet-solutions/us-gaap/
- R49. Prophet Solvency II page (archived 2016): https://web.archive.org/web/2016/http://www.prophet-web.com/prophet-solutions/solvency-ii/
- R50. Risk.net, Indian regulator adopts Prophet: https://www.risk.net/regulation/solvency-ii/2079762/indian-insurance-regulator-adopts-industry-software-product-vetting ; Korean case: https://web.archive.org/web/2022/https://www.prophet-web.com/successes/top-korean-life-insurer/
- R51. Pacific Life Prophet developer job ad: https://builtin.com/job/actuary-prophet-developer/7084461
- R52. SOA Emerging Topics Feb 2026 (Git for actuaries): https://www.soa.org/communities/emerging-topics/newsletter-articles/2026/february/2026-02-et-cody/
- R53. FIS UK PMCS case study: https://www.prophet-web.com/successes/UK-PMCS/
- R54. FIS DevOps job ad (microservices/Docker): https://poslovi.infostud.com/posao/DevOps-Engineer/FIS/324718
- R55. InsuranceERM Special Report 2025 (R44)
- R56. WTW RAFM agentic AI (Oct 2026): https://www.wtwco.com/en-us/news/2026/10/wtw-launches-raiskagility-financial-modeller-with-expanded-agentic-capabilities ; GPU: https://iireporter.com/wtw-adds-gpu-support-to-riskagility-fm/ ; Moody's AXIS Cloud: https://www.moodys.com/web/en/us/solutions/capital-management/actuarial-modeling/axis-cloud.html
- R57. Coverager, Montoux liquidates amid FIS lawsuit: https://coverager.com/montoux-liquidates-amid-fis-lawsuit-allegations/ ; G2: https://g2.com/products/prophet-2024-04-02/pricing
- R58. FIS Managed Cloud brochure: https://www.fisglobal.com/-/media/fisglobal/files/pdf/brochure/managed-cloud-services-for-actuaries-and-risk-managers.pdf
- R59. AWS APN blog, Montoux model replication: https://aws.amazon.com/blogs/apn/montoux-ai-driven-decision-science-platform-transforms-actuarial-model-replication
- R60. Contractor ads: https://www.theactuaryjobs.com/job/120268/prophet-als-contractor/ ; https://www.oliverjames.com/job/senior-prophet-developer
- R61. Market-size reports: https://www.wiseguyreports.com/reports/actuarial-modeling-software-market ; https://pmarketresearch.com/it/actuarial-modeling-software-market/
- R62. Aon PathWise / IAA GPU presentation (2025): https://actuaries.org/app/uploads/2025/08/July_2025_IAALS_GPU_Presentation.pdf ; ICICI Pru: https://www.reinsurancene.ws/leading-indian-life-insurer-to-implement-aons-modelling-platform-pathwise/ ; Akur8–Slope: https://fintech.global/2026/03/17/akur8-buys-slope-software-to-broaden-actuarial-platform/
- R63. Global Restructuring Review, Montoux Chapter 15: https://globalrestructuringreview.com/article/new-zealand-software-company-files-ch15-amid-trade-secret-litigation ; remotely-actuarial blog: https://www.remotely-actuarial.com/blog/the-key-ingredient/
- R68. Sumble technographic data on Prophet (job-mention counts, noisy): https://sumble.com/tech/prophet
- R64. SOA, The Modeling Platform, Nov 2020 (PBR survey, run times, scenario reduction, ~50% considering a system change): https://www.soa.org/globalassets/assets/library/newsletters/the-modeling-platform/2020/november/mp-2020-11.pdf
- R65. NAIC GOES and VM-22 timing: NAIC LATF materials, 22 Oct 2026: https://content.naic.org/sites/default/files/call_materials/latf-10-22-26-materials.pdf ; NAIC PBR page: https://content.naic.org/index.php/pbr_data.htm ; Moody's on GOES: https://www.moodys.com/web/en/us/insights/insurance/moodys-axis-support-for-naic-goes.html ; Milliman VM-22/GOES readiness survey 2025: https://www.milliman.com/en/insight/milliman-vm-22-goes-readiness-survey-2025
- R66. Chartis RiskTech100 / IFRS 17 quadrant releases: https://www.businesswire.com/news/home/20211122005218/en/ ; https://www.businesswire.com/news/home/20200724005008/en/
- R67. PRA SS1/23 applies to banks, not insurers: https://www.prarulebook.co.uk/guidance/supervisory-statements/ss01-23--model-risk-management-principles-for-banks
- R69. AARC Prophet training syllabus (Rundowns, Result View, etc.): http://aarconsultants.in/pdf/AARC_training.pdf
- R70. Cardif / Institut des Actuaires thesis on a Prophet ALS model (mid-month timing, annual ALS): https://www.institutdesactuaires.com/docs/mem/3210a1837f763b3a902ba17b12f8f5cc.pdf
