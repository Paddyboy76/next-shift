# Next Shift — Operations Control Design System

**Source of truth:** extracted from `services/operations_ui/` (`static/app.css`,
`templates/index.html`, `static/app.js`) at branch
`claude/stitch-skills-plugin-setup-w9zc8j`.

**Stitch project:** `Next Shift Operations Control` — `projects/1774680268812896613`

This document describes the *current* visual system as implemented, plus the
constraints any redesign must respect. It is the baseline for Stitch generation
and the contract for anything carried back into the Flask/Jinja/vanilla-JS app.

> Next Shift does not summarize the handover. It finishes the operational work
> left behind by it.

---

## 1. Product character

Next Shift is an autonomous operations control system for 24/7 non-clinical
environments. It is **not** a SaaS analytics dashboard. The screen is read by an
operator mid-shift, often at a glance, often on a wall display.

Design intent, in priority order:

1. **Operational truth first.** The UI must never make an agent's *claim* look
   like verified state. Human claims and authoritative Firestore state are
   different things and must be visually different things.
2. **Calm, not flashy.** Colour is a semantic signal, not decoration. A screen
   with nothing wrong should look quiet.
3. **Density without clutter.** An operator would rather see 14 issues than 5
   large cards.
4. **Fast scanning.** Answer, without interaction: what changed, what needs
   attention, who owns it, what happens next, what is actually verified.
5. **Credible in a real control room.** Hospital facilities, EVS, transport.

---

## 2. Colour

### 2.1 Background / surface palette

Dark-only (`color-scheme: dark`). Surfaces step *up* in lightness as they step
forward in the z-order.

| Token | Value | Use |
|---|---|---|
| `--bg-base` | `#071019` | Page background |
| `--bg-wash` | `radial-gradient(circle at top left, #123044 0, transparent 35%)` | Single ambient wash over base. The only gradient in the system that is decorative — keep it subtle or drop it. |
| `--surface-panel` | `linear-gradient(180deg, rgba(17,35,46,.92), rgba(10,24,33,.95))` | Panels (intake, metrics, shift snapshots) |
| `--surface-lane` | `rgba(8,22,31,.80)` | Workflow lane container |
| `--surface-card` | `#0c1c26` | Issue card |
| `--surface-card-raised` | `linear-gradient(180deg, rgba(16,41,53,.98), rgba(10,27,37,.98))` | Priority / newest-work card (`.issue-card-compact`) |
| `--surface-inset` | `#091923` | Metric tiles, state pills |
| `--surface-input` | `#07141d` | Textarea |
| `--surface-drawer` | `#091822` | Issue drawer |
| `--surface-timeline` | `#0d202b` | Timeline / history entries |
| `--scrim` | `rgba(0,0,0,.62)` | Drawer backdrop |

### 2.2 Border palette

| Token | Value | Use |
|---|---|---|
| `--border-panel` | `#203440` | Panel outline |
| `--border-lane` | `#1e3441` | Lane outline |
| `--border-card` | `#203946` | Card outline |
| `--border-card-hover` | `#3e6b7d` | Card hover |
| `--border-strong` | `#29404c` | Drawer edge, topbar rule (`#21323e`) |
| `--border-pill` | `#294455` | Chips, state pills |
| `--border-dashed` | `#29414e` | Empty-state outline |

### 2.3 Text palette

| Token | Value | Contrast on `--bg-base` | Use |
|---|---|---|---|
| `--text-primary` | `#e8f2f7` | 15.4:1 | Headings, card titles, metric values |
| `--text-secondary` | `#a8c1cf` | 8.9:1 | Chip labels, lane titles (`#adc3ce`) |
| `--text-tertiary` | `#88a4b4` | 6.2:1 | Timestamps, sub-notes, next-action line (`#839fac`) |
| `--text-muted` | `#6f8a98` | 4.3:1 | Empty states only. **Do not** use below 12px. |
| `--text-on-accent` | `#041310` | — | Text on teal fills |

### 2.4 Accent

| Token | Value | Use |
|---|---|---|
| `--accent` | `#42cabb` | Primary action fill, focus ring, eyebrows (`#46cabb`), owner label, section headers |
| `--accent-brand` | `#36c2b4` | Brand mark only |
| `--accent-focus-ring` | `rgba(66,202,187,.12)` | `0 0 0 3px` focus halo |

One accent. Resist adding a second brand hue — the status palette needs the
remaining colour budget.

### 2.5 Status / state semantics

Current implementation collapses nine workflow states into four visual
treatments:

| Treatment | States | Border | Text |
|---|---|---|---|
| Active | `ACTION_PENDING`, `VERIFYING` | `#39746f` | `#7ce1d4` |
| Attention | `BLOCKED`, `HUMAN_REVIEW` | `#745c39` | `#e2bd7c` |
| Complete | `CLOSED` | `#315d49` | `#8bd6ad` |
| Neutral | `RECEIVED`, `TRIAGED`, `ASSIGNED`, `FAILED` | `#294655` | `#a9c3ce` |

**Known defects in this mapping — a redesign must fix these:**

- `ACTION_PENDING` (work an operator can act on now) and `VERIFYING` (work
  waiting on a machine) are indistinguishable. They demand different behaviour.
- `BLOCKED` (system-stuck) and `HUMAN_REVIEW` (a person must decide) are
  indistinguishable.
- `FAILED` renders as neutral — the same treatment as `RECEIVED`. A failure
  looks like a new arrival.

**Required semantics for any new palette:**

| Rank | State | Meaning | Signal |
|---|---|---|---|
| 1 | `HUMAN_REVIEW` | A person must decide, now | Amber, highest weight |
| 2 | `BLOCKED` | Progress stopped on a dependency | Amber, outlined |
| 3 | `FAILED` | Workflow error | Red — the only red in the system |
| 4 | `ACTION_PENDING` | Awaiting trusted evidence | Teal, filled |
| 5 | `VERIFYING` | Independent verifier running | Teal, outlined |
| 6 | `ASSIGNED` / `TRIAGED` / `RECEIVED` | In flight, no operator action | Neutral, descending weight |
| 7 | `CLOSED` | Verified complete | Green, low weight — recede |

**Never encode state by colour alone.** Every state carries its literal name as
text in the pill. Additionally each state must carry a non-colour differentiator
— a shape, a leading glyph, a fill-vs-outline distinction, or a position — so the
board survives greyscale, projector washout, and colour-vision deficiency.

### 2.6 The claim-vs-truth distinction

This is the product's defining idea and needs a dedicated visual device.

- **Authoritative state** (Firestore, via State Authority) — the state pill.
  Solid, unambiguous, always present.
- **Human claim** (`human_reach.delivery_status = COMPLETION_CLAIMED`) — a
  frontline worker says it is done. This is **not** truth.

Current implementation shows the claim warning *only inside the drawer*. On the
board a `COMPLETION_CLAIMED` issue is visually identical to any other
`ACTION_PENDING` issue. Any redesign must surface an **unverified-claim marker
at board level** — a hatched/striped edge or a distinct "claimed · unverified"
chip — so an operator never mistakes a claim for closure without opening the
drawer.

---

## 3. Typography

Family: `Inter, ui-sans-serif, system-ui, sans-serif`.

| Role | Size | Weight | Tracking | Colour |
|---|---|---|---|---|
| Page title (`h1`) | 21px | 600 | — | primary |
| Section title (`h2`) | 19px | 600 | — | primary |
| Subsection (`h3`) | 15px | 600 | — | primary |
| Card title | 13px | 600 | — | primary, `line-height: 1.32` |
| Body / timeline | 11–12px | 400 | — | secondary, `line-height: 1.45` |
| Eyebrow | 10px | 800 | `.11em`, uppercase | accent |
| Lane title | 11px | 800 | — | secondary |
| State pill | 9px | 800 | — | per state |
| Metadata / time | 10–12px | 400 | — | tertiary |
| Metric value | 27px | 400 | — | primary, `line-height: 1` |

**Constraints.** 9px is the floor and is used only for pills carrying a
redundant text label. Do not go below it. Numerals in metric tiles and any
timing column must be tabular (`font-variant-numeric: tabular-nums`) so digits
do not jitter on the 5-second refresh.

---

## 4. Spacing & density

Base scale: **7 · 8 · 9 · 10 · 11 · 12 · 14 · 16 · 18 · 20 · 24 · 28**

The system is deliberately tight. Notable values:

| Context | Padding |
|---|---|
| Topbar | `18px 28px` |
| Panel | `18px` |
| Lane | `11px` |
| Issue card | `11px` |
| Metric tile | `14px` |
| Drawer | `24px` |
| Timeline item | `10px` |

Gaps: `8px` between cards in a lane, `10px` between lanes and between
newest-work cards, `16px` between major regions, `20–22px` between sections.

**Density target:** an operator on a 1440×900 laptop should see the newest-work
strip plus at least two full rows of workflow lanes without scrolling.

---

## 5. Shape

| Token | Radius | Use |
|---|---|---|
| `--radius-panel` | 15px | Panels |
| `--radius-lane` | 13px | Lanes, primary-action block |
| `--radius-control` | 12px | Metric tiles, textarea, brand mark |
| `--radius-card` | 10px | Issue cards, buttons |
| `--radius-timeline` | `0 9px 9px 0` | Timeline items (flat left edge carries the 2px accent rule) |
| `--radius-pill` | 999px | Chips, state pills, lane counts |

Elevation is expressed by surface lightness and border, not by shadow. The one
shadow in the system is `0 14px 44px rgba(0,0,0,.16)` on panels. Keep shadows at
or below this. No glow, no neon, no glassmorphism.

---

## 6. Component hierarchy

```
topbar
  brand-row            NS mark · Next Shift · Autonomous Operations Control
  security-strip       Live Firestore · Agent Gateway · Model Armor · State Authority
main
  hero-grid            1.75fr / minmax(280px, .75fr)
    intake-panel       handover textarea + governed submit + status line
    metric-panel       2×2 tiles: Open · Verifying · Closed · Human review
  workspace            1fr / 290px
    board-area
      focus-section    "Needs attention now" — newest active work, max 8, auto-fit
      workflow-section 9 state lanes, auto-fit minmax(230px, 1fr)
    shift-panel        sticky continuity snapshots
drawer                 min(590px, 96vw), right, full height
  eyebrow (owner) · h2 (title)
  current state
  next governed action     <- must stay above the fold
  Human Reach
  trusted evidence
  operational history
  State Authority events
```

### 6.1 Cards

`.issue-card` — owner label + state pill on one topline, title, next-action
line, timestamp. `.issue-card-compact` raises the surface and border for the
newest-work strip.

**Required additions:** relative age ("14m"), time-in-current-state, and the
unverified-claim marker. The current absolute `toLocaleString()` timestamp is a
long, low-scannability string in a 10px tertiary colour — it fails the
"what changed?" test.

### 6.2 Buttons

Single primary style: `#42cabb` fill, `#041310` text, weight 800, radius 10,
padding `10px 14px`. Disabled at `.55` opacity with `cursor: wait`. There is no
secondary or destructive button style — add one only if a real second action
exists.

### 6.3 Drawer / panel

Right-hand overlay, `min(590px, 96vw)`, full viewport height, scrolls
internally, `#091822` on a `.62` scrim, `1px` left border. Close control is a
36px circle, sticky at top.

**Required additions:** `aria-label` on the close control, `Esc` to dismiss,
focus trap, and focus restoration to the originating card.

### 6.4 Empty states

`.empty` — 11px muted text. `.focus-empty` adds a dashed outline. Empty lanes
currently render at full width with "No work" inside — see §8.

---

## 7. Motion

`transition: .15s ease` on card hover, which lifts `1px` and brightens the
border. That is the entire motion system, and it is correct for the product.

Add only: a brief, non-looping highlight on a card whose state changed since the
last poll ("what changed?"). No looping animation, no pulsing, no shimmer — a
control room screen is watched for hours.

---

## 8. Layout defects to correct

Carried from real acceptance testing against the deployed product, verified
against current code:

1. **Empty lanes consume full columns.** `app.js` renders all nine states
   unconditionally into `repeat(auto-fit, minmax(230px, 1fr))`. On a typical
   shift, four to six lanes are empty and each still occupies a full grid track
   with a "No work" label. Empty lanes must collapse, or the board must abandon
   per-state columns entirely.

2. **"Needs attention now" is sorted by recency, not attention.** The
   focus strip filters out terminal states and sorts by `updated_at`. An
   `ASSIGNED` issue touched a minute ago outranks an `ACTION_PENDING` issue
   touched ten minutes ago. The heading promises triage; the code delivers a
   changelog. Rank by the §2.5 attention order first, recency second.

3. **`CLOSED` sits in the same grid as active work.** History competes visually
   with current work. `CLOSED` and `FAILED` belong in a separate, collapsed,
   lower-contrast region.

4. **Metric tiles are equal weight.** "Human review" (a person is needed *now*)
   renders identically to "Closed" (nothing to do). Weight the tiles by
   actionability, and make the actionable ones clickable filters.

5. **No time-in-state anywhere.** Nothing on the screen shows how long an issue
   has been waiting. For an operations product this is the single most
   important missing datum.

6. **Full `innerHTML` replacement every 5s.** `loadBoard()` rebuilds the board
   wholesale, discarding hover, scroll position and any selection, and making
   change-detection impossible. Diff and patch instead.

7. **Refresh failures are near-silent.** A failed poll only rewrites the
   `#last-refresh` string. On a wall display, stale data must be *loud* — a
   persistent banner and a visibly dimmed board.

8. **Cards are not keyboard reachable.** `.issue-card` is an `<article>` with a
   click listener: no `tabindex`, no `role`, no Enter/Space handling.

---

## 9. Responsive behaviour

Current breakpoints: `1050px` (workspace collapses to one column, shift panel
un-sticks) and `760px` (everything stacks, drawer goes full-bleed).

`main` is capped at `min(1540px, 100%)`.

### Required tiers

| Tier | Width | Behaviour |
|---|---|---|
| **Tablet** | 768–1024px | Two-column board. Shift panel moves below the board. Intake collapses to a single-line trigger that opens a sheet — the textarea should not occupy a third of a tablet viewport. Touch targets ≥44px. |
| **Laptop / desktop** | 1025–1919px | Current layout. Newest-work strip plus two lane rows above the fold at 1440×900. |
| **Wall display** | ≥1920px | **The 1540px cap must be lifted.** On a 4K control-room screen the current layout wastes roughly two-thirds of the width. Widen to `min(2400px, 100%)`, step type up ~15%, drop the intake panel entirely (nobody types on a wall display), and promote the attention queue to a persistent left region. Optimise for readability at 2–3m: minimum 14px body, heavier weights, higher-contrast borders. |

---

## 10. Accessibility

- All text ≥ 4.5:1 on its own surface. `--text-muted` (`#6f8a98`, 4.3:1) is
  borderline and is restricted to non-essential empty states.
- Status is never colour-only — every pill carries its state name as text, and
  §2.5 requires a second non-colour differentiator.
- Focus is visible: `2px` accent outline with `2px` offset on every interactive
  element. The existing textarea focus ring is the reference.
- Cards must be `role="button"`, `tabindex="0"`, with Enter/Space activation.
- The drawer must trap focus, close on `Esc`, and restore focus on close.
- Live regions: the board should announce count changes politely; a stale-data
  banner should be `role="status"`.
- Respect `prefers-reduced-motion` for the change-highlight.

---

## 11. Non-negotiable content semantics

Any generated design must use these exact names and this exact workflow.

**Canonical states:** `RECEIVED` → `TRIAGED` → `ASSIGNED` → `ACTION_PENDING` →
`VERIFYING` → `CLOSED`, plus `BLOCKED`, `HUMAN_REVIEW`, `FAILED`.

**Operational owners:** `Facilities`, `AssetLogistics`, `LanguageAccess`,
`DischargeDME`, `EVSThroughput`, `PatientTransport`.

**Next-action strings** (from `app.js`, must not be reworded):

| State | Next action |
|---|---|
| `RECEIVED` | Await specialist triage |
| `TRIAGED` | Await specialist assignment |
| `ASSIGNED` | Begin operational action |
| `ACTION_PENDING` | Await trusted evidence |
| `VERIFYING` | Await independent verification |
| `BLOCKED` | Resolve blocking dependency |
| `HUMAN_REVIEW` | Await authorized human decision |
| `CLOSED` | Verified complete |
| `FAILED` | Review failure |

**Human Reach statuses:** `PENDING`, `DELIVERED`, `ACKNOWLEDGED`, `BLOCKED`,
`COMPLETION_CLAIMED`.

**Governed actions** (the only two operator actions in the product):
"Record synthetic trusted evidence" on `ACTION_PENDING`, and "Run independent
verifier" on `VERIFYING`. Specialists never close their own work.

**Governance strip:** Live Firestore · Agent Gateway · Model Armor · State
Authority. Plus a persistent "Synthetic data only" badge.

Rules that the UI must never contradict:

- An agent's or human's claim of completion is not evidence.
- Only the independent verifier moves work to `CLOSED`.
- Firestore is authoritative; nothing else on screen outranks it.
