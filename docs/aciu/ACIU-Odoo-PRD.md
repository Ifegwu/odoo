# Product Requirements Document (PRD)

## ACIU × Odoo 19 — Communal Union ERP

| Field | Value |
|-------|--------|
| **Product** | ACIU Odoo (Abiriba Communal Union / Improvement Union) |
| **Platform** | Odoo 19.0 Community Edition |
| **Primary market** | ACIU Germany (central e.V. + 11 branches), extensible worldwide |
| **Status** | Requirements locked from officer workshops (Sep 2026); ACL refined in implementation |
| **Related blueprint** | Cursor canvas: `ACIU-odoo-tailoring.canvas.tsx` |
| **Version** | 1.4 |

---

## 1. Executive summary

ACIU needs an ERP to **harmonize member records, dues, project contributions, and branch operations** across Germany, then worldwide.

Stock Odoo 19 CE is a strong foundation (Contacts, multi-company, Accounting, Portal, Events, Project) but is **not** a diaspora-union system out of the box. Delivery requires a **thin custom addon layer** (`aciu_base`, `aciu_membership`, `aciu_dues`, later governance/projects/portal) without forking Odoo core.

**Germany first:** one database, multi-company (central e.V. + 11 branch companies with own banks), soft debt tracking (never hard-block membership), annual €20 dues, monthly roll call (attendance + per-branch fee).

---

## 2. Goals and non-goals

### 2.1 Goals

1. Single source of truth for ACIU Germany members, branches, and money.
2. Each branch collects into its **own bank**; central has its **own** bank.
3. Harmonize contribution types: annual dues, roll-call fees, branch/central projects, burial levies.
4. Track **open debts** clearly and encourage clearance **without** blocking membership.
5. Support monthly **roll-call attendance** per branch.
6. Design so branches that later register as e.V. need **no data migration**.
7. Leave a clear path to ACIU Worldwide (UK, North America, Nigeria, etc.).

### 2.2 Non-goals (v1)

- Hard-blocking members for unpaid dues or levies.
- Fixed % remittance from branch → central.
- Replacing Abiriba National Secretariat politics/governance outside DE scope.
- Enterprise-only Odoo features as a dependency (CE is enough to start).
- Forking or patching Odoo core modules.

---

## 3. Users and roles

Privilege principle (locked):

- **Branch officers** (see ladder) and **central executives** get **elevated operational rights** in their scope.
- They are **not Settings / Admin** users (no install apps, no edit security groups, no technical settings, no create companies).
- **Members** get **read + limited write** on their own data and selected shared areas (not full backend admin).
- **Branch officers are restricted to their home branch** for Branch company records and Contacts (no sibling branches, no Central/Germany hierarchy read).
- **Central Executive** users remain branch members and **keep any branch title** (Treasurer, President, VP, etc.); they **perform both** central and branch functions. Combined groups apply; Germany-wide rights come from Central Executive.

### 3.1 Role ladder

| Role (Odoo group) | Typical people | Company / Contacts scope | Privilege level |
|------|----------------|--------------------------|-----------------|
| **Member** | Ordinary members | Own contact (+ limited) | Read + write on **allowed** personal / participation areas only |
| **Treasurer** | Branch treasurer | Own branch only | Elevated finance on own branch; not admin |
| **Financial Secretary** | Branch financial secretary | Own branch only | Read own branch; not admin |
| **Secretary** | Branch secretary | Own branch only | Read own branch; not admin |
| **Speaker** | Branch speaker | Own branch only | Read own branch; not admin |
| **Vice President** | Branch VP | Own branch only | Read own branch; not admin |
| **President** | Branch president (xml id still `group_aciu_branch_leader`) | Own branch only | **Read/write** own branch ops + own branch company; not admin |
| **Central Treasurer** | Central e.V. treasurer | All ACIU DE companies | Elevated finance Germany-wide; not admin |
| **Central Executive** | Central / national officers | All ACIU DE companies (+ retained branch title) | Elevated ops Germany-wide **and** branch title duties; not admin |
| **System Admin** | IT / technical custodian | All | Full Settings (rare; 1–2 people) |

### 3.2 Privilege matrix (what each role can do)

Legend: **R** = read · **W** = write/create/edit · **—** = no access · **Own** = only own record / own branch  
**Officers (R)** = Treasurer, Financial Secretary, Secretary, Speaker, Vice President (read own branch unless noted).

| Area | Member | Officers (R) | Treasurer | President | Central Treasurer | Central Executive | Admin |
|------|--------|--------------|-----------|-----------|-------------------|-------------------|-------|
| Own profile (contact, family) | R/W Own | R/W Own | R/W Own | R/W Own | R/W Own | R/W Own | R/W |
| Own open debts & payments | R/W Own (pay) | R | R | R | R | R | R/W |
| Own roll-call attendance history | R Own | R branch | R branch | R/W branch | R | R | R/W |
| Branch member directory / Contacts | R Own (limited) | R Own branch | R/W Own branch | R/W Own branch | R all DE | R/W all DE | R/W |
| Branch menu (own company) | — | R Own branch | R Own branch | R/W Own branch | R all ACIU | R/W all ACIU | R/W |
| Central / parent company (Germany) | — | — | — | — | R | R/W | R/W |
| Sibling branches | — | — | — | — | R | R/W | R/W |
| Annual dues / roll-call fees (post & reconcile) | Pay own | R Own branch | R/W Own branch | R Own branch (approve/view) | R/W central + DE view | R all DE | R/W |
| Burial levy / project campaigns | Pay own | R Own branch | R/W Own branch | R/W Own branch | R/W central + DE | R/W all DE | R/W |
| Branch bank journal / reconciliation | — | — / R | R/W Own branch | R Own branch | R/W central; R DE | R DE | R/W |
| Central bank / transfers | — | — | — | — | R/W | R | R/W |
| Monthly roll call (take attendance) | — (self check-in optional later) | R Own branch | R Own branch | R/W Own branch | R | R/W all DE | R/W |
| Branch projects | R Own branch | R Own branch | R/W Own branch | R/W Own branch | R | R/W | R/W |
| Central projects | R (contribute) | R | R | R | R/W | R/W | R/W |
| Reports (collections, attendance, debts) | R Own | R Own branch | R Own branch | R Own branch | R DE | R DE | R/W |
| Configure roll-call fee amount | — | — | — | R Own branch (propose) | — | W all branches | W |
| Users, groups, Settings, apps | — | — | — | — | — | — | **Only Admin** |
| Create companies / chart of accounts setup | — | — | — | — | — | — | **Only Admin** |

### 3.3 Member read/write scope (explicit)

Members **may** read/write:

- Their **own** contact details (address, phone, email — within validation rules)
- Their **own** payment actions (pay open debts via portal)
- Their **own** attendance history (read)
- Optional: register interest / contribution intent on open projects (write own lines only)

Members **may not**:

- Edit other members’ records
- Post accounting entries or reconcile banks
- Open/close burial levies or change fee schedules
- Access Settings, users, or other branches’ books
- Browse Central or sibling branch companies / contact trees

### 3.4 Branch officers, President & Central Executive (elevated, not admin)

**Branch officers** (Treasurer, Financial Secretary, Secretary, Speaker, Vice President) — **own branch only**:

- Open **Branch** (own company) without Access Error; UI must **not** require reading ACIU Germany / parent company
- **Contacts** / Members: only home-branch contact tree (`aciu_branch_id` in allowed companies, or nested under that branch’s company partner)
- **Cannot:** see Central, sibling branches, Settings, or other branches’ banks

**Treasurer** (additional): finance write on own-branch dues/bank (as in matrix).

**President** (own branch only):

- Read/write own branch members, roll call, branch projects; write own branch company record
- Work with Treasurer (president focuses on people/ops; treasurer on bank)
- **Cannot:** Settings, install modules, manage security groups, see other branches’ banks or Central company

**Central Executive** (Germany-wide ops + optional branch title):

- Remains a member of a home branch; **retains** Treasurer / President / VP / etc. when assigned
- Performs **both** central functions and the branch title functions
- View/manage members across branches, central projects, DE-wide reports; write all ACIU companies as needed for DE policy
- **Cannot:** Settings / technical admin (unless separately given Admin — discouraged)

**Central Treasurer:** central bank + consolidated DE finance view; read all ACIU companies; not Settings/Admin.

### 3.5 Implemented ACL notes (`aciu_base` / `aciu_membership`)

| Mechanism | Behaviour |
|-----------|-----------|
| `company rule employee` | Employees only see `res.company` in `company_ids` |
| Branch officers | No extra parent-company read — Germany is not readable unless Central role (or Germany in `company_ids`) |
| President | Model write + record rule write on own branch company (`id in company_ids`) |
| Central Executive / Treasurer | Read all `is_aciu_company`; Central Executive also write all ACIU companies |
| Branch officer Contacts rule | `aciu_branch_id in company_ids` **or** `id child_of` activated companies’ partners |
| Central Contacts rule | All ACIU members / branch-assigned contacts + company partner trees |
| ACIU → Branch menu | List/form avoids parent / child hierarchy widgets for non-central users |

### 3.6 Brand / theme (aciuworldwide.com)

Public site reference: https://www.aciuworldwide.com/

| Token | Hex | Use |
|-------|-----|-----|
| Primary | `#00B686` | Buttons, active nav, accents, email CTA background |
| Primary soft | `#E6F8F3` | Soft surfaces / nav hover / mint CTA fill |
| Header | `#EEEEEE` | ERP top bar (matches site header — not solid green) |
| Ink | `#313131` | Headings / brand text |
| Muted | `#737373` | Inactive nav / secondary text |
| Surface | `#F5F5F5` | Page background |

Implementation: `aciu_base/brand_colors.py` + `static/src/scss/primary_variables.scss` (override `$o-brand-primary`). Company `primary_color` / `secondary_color` / email button colors set on upgrade. **Editable later** by changing those two files and re-upgrading `aciu_base`.

Login page uses full-bleed `aciu_base/static/img/bg-login.jpeg` via CSS (`background-size: cover`, centered; mobile-safe position) with a frosted glass card (`aciu_login.scss`).

---

## 4. Organization and legal model

### 4.1 Hierarchy (Odoo multi-company)

```
ACIU Worldwide (root, later)
 └── ACIU Germany (central) — registered e.V., is_registered_ev = true
      ├── ACIU Bremen (DE-HB)
      ├── ACIU Hamburg (DE-HH)
      ├── ACIU Bayern (DE-BY)
      ├── ACIU Baden-Württemberg (DE-BW)
      ├── ACIU NRW (DE-NW)
      ├── ACIU Duisburg (DE-DU)     ← peer of NRW, not child of NRW
      ├── ACIU Halle/Saale (DE-HAL)
      ├── ACIU Osnabrück (DE-OS)
      ├── ACIU Berlin-Brandenburg (DE-BE)
      ├── ACIU Frankfurt-Mainz (DE-FFM)
      └── ACIU Hannover (DE-H)
```

Later siblings under Worldwide: ACIU UK, North America, Nigeria, etc.

### 4.2 Banking and legal status

| Entity | Legal status now | Bank account | Odoo representation |
|--------|------------------|--------------|---------------------|
| ACIU Germany (central) | Registered e.V. | Yes — central | Parent company; full accounting + `l10n_de` |
| 11 branches | Operational chapters (not yet e.V.) | Yes — each own | Child companies from day one; own bank journal |
| Branch after e.V. registration | Own e.V. | Same or new | Flip `is_registered_ev` (+ VR number); **no restructuring** |

**Decision (locked):** Create all 11 branches as `res.company` children immediately so each has its own bank journal and dues ledger.

### 4.3 Money flow

1. Member pays into **their branch** bank.
2. Branch treasurer reconciles the branch journal.
3. Optional transfer branch → central when needed (**no fixed remittance %**).
4. Central funds national / Abiriba projects from the central account.

---

## 5. Functional requirements

### 5.1 Membership (`aciu_membership`)

| ID | Requirement | Priority |
|----|-------------|----------|
| M-01 | One `res.partner` per person; home branch = one of the 11 DE companies | Must |
| M-02 | Member fields: branch, age grade, membership status, join date, officer roles, optional NIN/diaspora/ACIU ID | Must |
| M-03 | Family / spouse links | Should |
| M-04 | Branch transfer workflow | Should |
| M-05 | Soft open-debt balance visible on member (does not block membership) | Must |

### 5.2 Contributions and dues (`aciu_dues`)

| ID | Requirement | Priority |
|----|-------------|----------|
| D-01 | **Annual membership due = €20** (Germany-wide); invoice on member’s branch company | Must |
| D-02 | Unpaid annual due **does not block** membership; remains open debt until paid | Must |
| D-03 | **Monthly roll call fee** configurable **per branch**; invoice on branch company | Must |
| D-04 | Seed Berlin-Brandenburg roll-call fee = **€5**; other branches configurable (TBD) | Must |
| D-05 | Branch project contribution campaigns (analytic + branch company) | Must |
| D-06 | Central project contribution campaigns (central-owned; multi-branch payers; optional remit) | Must |
| D-07 | **Burial levy**: ad-hoc campaign (open → invoice eligible → close); no standing schedule | Must |
| D-08 | Unpaid burial levy / project debts **do not block** membership; tracked until cleared | Must |
| D-09 | Soft debt UX: portal + treasurer always show what is owed; encourage clearance | Must |
| D-10 | Event fees (optional, linked to Events) | Should |
| D-11 | No formal branch→central remittance percentage engine | Must (as non-feature) |

### 5.3 Roll call / governance (`aciu_governance` — Phase 2, core attendance can start earlier)

| ID | Requirement | Priority |
|----|-------------|----------|
| G-01 | Each branch runs **monthly roll call** | Must |
| G-02 | Attendance statuses: present / absent / excused | Must |
| G-03 | Roll call = **attendance + fee** (fee amount per branch) | Must |
| G-04 | Attendance reports per branch / member (participation history) | Must |
| G-05 | Elections, committees, by-law document links | Could (Phase 2) |

### 5.4 Projects (`aciu_projects` — Phase 2)

| ID | Requirement | Priority |
|----|-------------|----------|
| P-01 | Distinguish **branch project** vs **central project** | Must |
| P-02 | Analytic account per project (payer + sourcing branch) | Must |
| P-03 | Track contributions toward Abiriba / development projects | Should |

### 5.5 Portal / worldwide UX (`aciu_portal_ww` — Phase 3)

| ID | Requirement | Priority |
|----|-------------|----------|
| W-01 | Member portal: view open debts, pay, receipts | Must |
| W-02 | Join / branch selection flows | Should |
| W-03 | Optional NIN / ID verification hooks | Could |

### 5.6 Security and access (`aciu_base` / `aciu_membership`)

| ID | Requirement | Priority |
|----|-------------|----------|
| S-01 | Security groups: Member; branch officers Treasurer, Financial Secretary, Secretary, Speaker, Vice President, President; Central Treasurer; Central Executive; System Admin | Must |
| S-02 | President & Central Executive = **elevated ops, never Settings/Admin** by default | Must |
| S-03 | Members = **read + limited write** on own profile, own payments, own attendance; no other members’ edit | Must |
| S-04 | Branch officers limited to **own company** for Branch + Contacts; Treasurer also own bank | Must |
| S-05 | Central Treasurer: central bank + consolidated DE finance view; read all ACIU companies | Must |
| S-06 | Central Executive: all DE companies operational access; **retains branch title** and performs both roles; no technical Settings | Must |
| S-07 | Record rules enforce company/branch isolation for non-central roles (no Germany parent read for branch-only officers) | Must |
| S-08 | Only System Admin may manage users/groups, apps, and technical configuration | Must |
| S-09 | Branch menu / company forms must not force branch officers to read Central (no parent hierarchy widgets) | Must |
| S-10 | Contacts for branch officers: home-branch members and that branch’s partner tree only | Must |

---

## 6. Contribution catalog (Germany)

| Charge | Scope | Frequency | Mode | Blocks membership? |
|--------|--------|-----------|------|--------------------|
| Annual membership due (€20) | Germany-wide | Yearly | Recurring invoice | No — soft debt |
| Monthly roll-call fee | Per branch (BE = €5; others TBD) | Monthly | Recurring + attendance | No — soft debt |
| Branch project contribution | One branch project | Campaign | Campaign | No — soft debt |
| Central project contribution | Central project, multi-branch | Campaign | Campaign | No — soft debt |
| Burial levy | Case-driven | Ad-hoc | Levy campaign | No — soft debt |
| Event fee | Per event | One-off | Event-linked | No — soft debt |

---

## 7. Branch master data

| # | Branch | Code | Roll-call fee / month |
|---|--------|------|------------------------|
| 1 | Bremen | DE-HB | TBD |
| 2 | Hamburg | DE-HH | TBD |
| 3 | Bayern | DE-BY | TBD |
| 4 | Stuttgart / Baden-Württemberg | DE-BW | TBD |
| 5 | Nordrhein-Westfalen (NRW) | DE-NW | TBD |
| 6 | Duisburg | DE-DU | TBD |
| 7 | Halle / Saale | DE-HAL | TBD |
| 8 | Osnabrück | DE-OS | TBD |
| 9 | Berlin / Brandenburg | DE-BE | **€5** |
| 10 | Frankfurt / Mainz | DE-FFM | TBD |
| 11 | Hannover | DE-H | TBD |

---

## 8. Native Odoo apps to enable

| App | Fit | ACIU use |
|-----|-----|----------|
| Contacts | Core | Member & household registry |
| Accounting + Analytic | Core | Invoices, banks, project analytics |
| l10n_de | Core (DE) | SKR chart, GoBD-friendly audit trail |
| Sales / Invoicing | Core | Dues and levy products |
| Payment + Portal | High | Online pay; open debts & receipts |
| Events | High | Roll calls, festivals, AGMs |
| Project | High | Development / fundraising projects |
| Discuss / Mail | Medium | Announcements; payment reminders |
| CRM | Low–Med | Outreach (optional) |
| Partnership | Weak alone | Do not use as membership engine |
| Website | Later | Public join / transparency |

**Technical constraint:** Keep custom code under `custom_addons/aciu_*`. Never fork core.

---

## 9. Custom module stack

| Module | Phase | Scope |
|--------|-------|--------|
| `aciu_base` | 1 | Company hierarchy helpers, `is_registered_ev`, security groups, menus, branding (logo + aciuworldwide.com colors) |
| `aciu_membership` | 1 | Member profile on partner, age grade, status, family, transfers |
| `aciu_dues` | 1 | €20 annual, per-branch roll-call fee, project & burial campaigns, soft debt |
| `aciu_governance` | 2 | Roll-call attendance UX, elections, committees |
| `aciu_projects` | 2 | Branch vs central project wrappers + Abiriba remittance proofs |
| `aciu_portal_ww` | 3 | Member self-service; worldwide join/pay |

---

## 10. Reporting requirements

| Layer | Questions answered |
|-------|-------------------|
| Member | What do I still owe? (soft list) |
| Branch | Collections; attendance %; who still owes |
| Central project | Contributions by member / branch |
| Country (DE) | Branch banks; optional transfers to central |
| Auditor | Cross-company debt and collection overview |

---

## 11. Phased rollout

| Phase | Scope | Outcome |
|-------|--------|---------|
| **0 — Foundation** | Deploy Odoo 19; enable Contacts, Accounting, Analytic, Sales, Portal, Payment, Events, Project; `l10n_de` | Empty ERP with German books ready |
| **1 — Germany pilot** | Central + 2–3 branches (e.g. Hamburg, NRW, Berlin); import members; dues + roll-call fee; treasurer workflows | Pilot collects in one system |
| **2 — Harmonize DE** | All 11 branches; attendance; soft debt dashboards | National DE picture |
| **3 — Worldwide** | UK / NA / Nigeria companies; shared member ID; multi-currency | Diaspora single source of truth |
| **4 — Member experience** | Portal + website join/pay; reminders; project transparency | Self-service; less treasurer load |

---

## 12. Design decisions (locked)

| Decision | Resolution |
|----------|------------|
| Database topology | One DB, multi-company |
| German chapters | Child companies now (own banks); `is_registered_ev` flag |
| Banks | Central bank + each branch bank |
| Annual due | €20 Germany-wide; soft debt; never hard-block |
| Monthly roll call | Attendance **+** fee; fee **per branch**; Berlin-Brandenburg €5 |
| Burial levy | Ad-hoc campaign; soft debt; never hard-block |
| Branch → central remittance | No formal % rule; optional transfers only |
| Debt culture | Soft for all charges — track, display, encourage clearance |
| Edition | Odoo Community Edition to start |
| Custom code | `custom_addons/aciu_*` only |

### Still open

- [ ] Roll-call fee amounts for the other 10 branches (not Berlin-Brandenburg)
- [ ] Exact pilot branch set for Phase 1
- [ ] Worldwide HQ identity (Abiriba National Secretariat vs diaspora federation vs both)
- [ ] Member unique ID scheme (ACIU ID vs email vs optional NIN)

---

## 13. Success metrics

1. All 11 DE branches + central can record collections against the correct bank.
2. Every member has a visible **open debt** list; unpaid €20 / fees / levies never auto-expel or hard-block.
3. Berlin-Brandenburg monthly roll call records attendance and €5 fee.
4. Central and branch projects report contributions by member and branch.
5. Burial levy can be opened, collected, and closed without a yearly schedule.
6. Time for treasurers to produce monthly collection + attendance reports reduced vs spreadsheets.

---

## 14. Out-of-scope risks / assumptions

- **Assumption:** Officers will supply remaining roll-call fees and member import lists.
- **Assumption:** Bank statements can be imported/reconciled per branch journal in Odoo.
- **Risk:** Treating Duisburg as peer of NRW must stay aligned with governance; change only if officers decide nesting.
- **Risk:** Soft debt may require cultural/process reminders (mail, meetings) — product shows debt, does not enforce.

---

## 15. Acceptance criteria (Phase 1 pilot)

- [ ] ACIU Germany + ≥2 branch companies created with `l10n_de` and bank journals
- [ ] `is_registered_ev` true on central, false on pilot branches
- [ ] Members imported and linked to home branch
- [ ] Annual €20 product/schedule generates invoices on correct branch
- [ ] Berlin-Brandenburg roll-call fee €5 configurable; other pilot branches set or left TBD
- [ ] Member form / portal shows open debts without blocking access
- [ ] Branch treasurer cannot see another branch’s bank
- [ ] Branch treasurer can open Branch + Contacts for **own branch only** (no Central Access Error; no sibling contacts)
- [ ] Burial levy campaign can be created and closed for a pilot branch
- [ ] Custom security groups match §3 privilege matrix (officers/execs ≠ Admin; Central Executive may keep branch title)
- [ ] Custom code lives only under `custom_addons/`

---

## 16. Document history

| Version | Date | Notes |
|---------|------|--------|
| 1.4 | 2026-09-23 | Theme: aciuworldwide.com palette (primary `#00B686`) on Odoo UI + company colors |
| 1.3 | 2026-09-23 | ACL: named branch officers; President R/W own branch; branch-only Branch/Contacts; Central Executive keeps branch titles (dual role) |
| 1.2 | 2026-09-22 | Phase 0–1 scaffold: custom_addons/aciu_base, aciu_membership, aciu_dues |
| 1.1 | 2026-09-21 | Privilege model: Branch Leader & Central Executive elevated (not admin); Member R/W limited areas |
| 1.0 | 2026-09-21 | Initial PRD from ACIU Odoo Tailoring workshops (branches, banks, €20, roll call, soft debt, projects, burial levy) |

---

*Sources: Odoo 19.0 CE workspace; ACIU Germany officer inputs (organization, fees, soft debt, remittance policy); public ACIU worldwide context (UK, NA, aciuworldwide.com).*
