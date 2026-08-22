# Next Shift — Operations Control: Stitch design review

**Stitch project:** `Next Shift Operations Control` — `projects/1774680268812896613`
**Design system asset:** `assets/237c5ee76f8d480b8bf7194337a4f9a3`
**Baseline analysed:** `services/operations_ui/` at `claude/stitch-skills-plugin-setup-w9zc8j`
(origin/main `cf2593b`)

Design-only exercise. No production application code was modified or deployed.

---

## 1. Screens

| # | Screen | Screen ID | Size |
|---|---|---|---|
| 1 | Operations Command Center | `872c01b1477b499ea1f9f01ca905d84f` | 2560×2048 |
| 2 | Google Enterprise | `3d9a07e39b7145f9907a2ca9e8a274d9` | 2560×2048 |
| 3 | 24/7 Control Room | `ecd0fc980fff4681949e60a99ab14c55` | 2560×2048 |
| 4 | Issue Detail — Governed Action | `6153ceeed980422a912a97752c28f542` | desktop |
| 5 | Responsive — Tablet and Wall Display | `1ab8e50ef62a4fee9523bab4b17e3556` | desktop |
| — | DESIGN.md (design-system source) | `6529151378873512914` | — |

Full resource path: `projects/1774680268812896613/screens/{screenId}`.

The design system Stitch derived from `.stitch/DESIGN.md` preserved the real
tokens — `#42cabb` accent, Inter, dark mode, `#071019` base, `#0c1c26` card,
`#091923` inset — and, importantly, adopted the *corrected* state palette this
review proposed rather than the current collapsed one:
`state-review-amber #e2bd7c`, `state-blocked-amber #745c39`,
`state-failed-red #ff4d4d`, `state-active-teal #42cabb`,
`state-complete-green #8bd6ad`, `state-neutral #a9c3ce`.

---

## 2. What all three variants share

Every variant was constrained to the same non-negotiables, and all three
implement them:

- **The kanban board is gone.** All three replace per-state columns with a
  ranked list or table. This is the single biggest change and it addresses
  acceptance findings 2, 3 and 4 at once — no horizontal hunting, no
  off-screen `ACTION_PENDING`, no empty columns eating a grid track.
- **Attention ranking replaces recency ranking.** The primary region is
  ordered by required action (`HUMAN_REVIEW` → `BLOCKED` → `FAILED` →
  `ACTION_PENDING` → `VERIFYING` → in-flight), not by `updated_at`.
- **`CLOSED` is demoted** to a collapsed, low-contrast strip so history stops
  competing with live work.
- **Time-in-state is on every row.** The baseline shows an absolute
  `toLocaleString()` string; all variants show elapsed time in tabular numerals.
- **A hatched "CLAIMED · UNVERIFIED" marker appears at board level** for
  `COMPLETION_CLAIMED`, not only inside the drawer. This is the product's core
  claim-vs-truth distinction, and in the baseline it is invisible until an
  operator opens an issue.
- **State is never colour alone** — literal text plus a fill-vs-outline
  differentiator.

---

## 3. Comparison

### Variant 1 — Operations Command Center (`872c01b1…`)

Three full-width horizontal bands: governance top bar, a full-width **attention
rail** of five priority cards, then a dense work table with a 300px right column
for collapsed intake and shift continuity.

- **Strengths.** Highest raw information density of the three. The attention
  rail is the clearest answer to "what needs attention *now*" — it is spatially
  fixed, so an operator's eye lands in the same place every time. Filter chips
  ("Human review 1", "Blocked 1", "Action pending 4") double as the metric row,
  which removes the baseline's four equal-weight tiles entirely.
- **Weaknesses.** The attention rail costs a fixed horizontal band even when
  only one issue needs attention, which is the common case on a calm shift.
  Least "designed" of the three — closest to an internal tool.
- **Best for.** A dedicated operator working the queue on a laptop.

### Variant 2 — Google Enterprise (`3d9a07e3…`)

220px persistent left rail (nav + owner filters with counts + governance block),
then header, urgency-weighted status tiles, and a refined data table with 52px
rows grouped under "Requires attention" and "In flight".

- **Strengths.** The most credible as a product rather than a dashboard —
  hairline dividers, clear column headers, real type hierarchy. The owner list
  in the rail is the only variant that makes "who owns it" a first-class
  navigation axis, which matters for a six-specialist fleet. Urgency-weighted
  tiles fix the baseline defect where "Human review" and "Closed" render
  identically. Grouping the table under two subheadings gives triage structure
  without giving up density.
- **Weaknesses.** The 220px rail is the largest fixed cost of the three, and
  most of it is navigation to views that do not exist yet in the Flask app.
  Slightly lower density than Variant 1 at the same width.
- **Best for.** Demo credibility and day-to-day desktop use.

### Variant 3 — 24/7 Control Room (`ecd0fc98…`)

Full-bleed 2560×1440 three-column wall layout. Slim header carrying a
`DAY SHIFT → NIGHT SHIFT · HANDOVER IN 38 MIN` banner and a live clock. Column 1
= two oversized human-attention cards; column 2 = active work at large type;
column 3 = shift continuity above a deliberately dim "verified complete" region.
No intake control at all.

- **Strengths.** The only variant that treats the handover countdown as a
  first-class object, which is exactly the product thesis. Correctly drops the
  intake textarea — nobody types at a wall display. Lifts the 1540px cap that
  currently wastes roughly two-thirds of a 4K control-room screen.
- **Weaknesses.** Not a general-purpose screen. At laptop width the three
  columns and the type scale are wrong, and with more than two attention items
  column 1 overflows. It is a display mode, not the default view.
- **Best for.** The wall screen, and for the hackathon demo's opening shot.

### At a glance

| | V1 Command Center | V2 Google Enterprise | V3 Control Room |
|---|---|---|---|
| Density | Highest | High | Moderate (by design) |
| Owner as navigation | No | **Yes** | No |
| Fixed chrome cost | Attention band | 220px rail | Header only |
| Laptop 1440×900 | Very good | **Very good** | Poor |
| Wall display ≥1920 | Good | Good | **Excellent** |
| Tablet | Good | Moderate (rail collapses) | Not applicable |
| Demo impact | Moderate | High | **Highest** |
| Distance from current Flask/CSS | Moderate | Moderate | Large |

---

## 4. Recommendation

**Adopt Variant 2 (Google Enterprise) as the primary Operations Control screen,
and Variant 3 as a dedicated `?display=wall` mode.**

Reasons:

1. **It fixes every acceptance finding without a rewrite.** The table, the
   attention grouping, the weighted tiles and the demoted `CLOSED` strip are all
   reachable from the current Jinja + vanilla-JS structure. No React, no
   Tailwind, no new build step.
2. **Owner is a navigation axis.** Next Shift's differentiator is a routed fleet
   of six least-privilege specialists. Variant 2 is the only layout that makes
   the fleet visible on the screen at rest, which is the thing judges need to
   see and operators need to filter by.
3. **It is the most defensible density trade.** Variant 1 is denser, but its
   attention rail is a fixed cost paid on every shift including calm ones.
   Variant 2's grouped table degrades gracefully: on a calm shift "Requires
   attention" is simply a short group.
4. **Variant 3 is not a competitor to it.** It is the same information at a
   different reading distance, and the two should ship together rather than one
   replacing the other — Variant 5 (`1ab8e50e…`) shows exactly that pairing.

Variant 1's **attention rail** is worth borrowing into Variant 2 as a
conditional region: render it only when `HUMAN_REVIEW` or `BLOCKED` work exists,
so the fixed cost is paid only when it is earned.

---

## 5. Carry-back into the existing Flask / HTML / CSS / JS

Ordered by operational value per unit of change. All are achievable inside
`templates/index.html`, `static/app.css` and `static/app.js` without touching
Flask routes, APIs, Firestore, State Authority, Human Reach, evidence,
verification, or security.

**High value, small change**

1. **Rank the focus strip by attention, not recency.** In `app.js`, `active` is
   sorted purely by `issueTime`. Introduce an attention rank
   (`HUMAN_REVIEW` 0, `BLOCKED` 1, `FAILED` 2, `ACTION_PENDING` 3, `VERIFYING`
   4, rest 5) and sort by `[rank, -updated_at]`. The heading already promises
   "Needs attention now"; this makes the code keep that promise.
2. **Replace the absolute timestamp with time-in-state.** `card-time` currently
   renders `toLocaleString()` — a long, low-scannability string. Show `18m` /
   `2h 04m` with `font-variant-numeric: tabular-nums`, and keep the absolute
   time in a `title` attribute.
3. **Collapse empty lanes.** `loadBoard()` renders all nine states
   unconditionally into `repeat(auto-fit, minmax(230px,1fr))`. Skip lanes with
   zero matching issues, and move `CLOSED`/`FAILED` into a separate collapsed
   strip below the board.
4. **Split the four collapsed state treatments into six.** `ACTION_PENDING` and
   `VERIFYING` currently share one CSS rule; so do `BLOCKED` and
   `HUMAN_REVIEW`; and `FAILED` renders as neutral, so a failure looks like a
   new arrival. Give each its own rule, add `FAILED` red, and add a
   fill-vs-outline distinction so the board survives greyscale and projector
   washout.
5. **Surface `COMPLETION_CLAIMED` on the card.** The `/api/issues` payload
   already drives the board; the claim warning exists only in
   `humanReachSection()` inside the drawer. Add a hatched "claimed · unverified"
   chip to the card so a human claim is never mistaken for verified progress at
   a glance. This is the highest-value single change on the list — it is the
   product thesis rendered visually.

**High value, moderate change**

6. **Weight the metric tiles by actionability** and make them filter the board.
   "Human review" and "Closed" currently render identically.
7. **Replace the state-column board with a grouped list** ("Requires attention"
   / "In flight" / collapsed "Closed today"). This is Variant 2's core move and
   it retires acceptance findings 2, 3, 4 and 5 together.
8. **Add a `?display=wall` mode** — reuse the same template, lift
   `main { width: min(1540px, 100%) }` to `min(2400px, 100%)`, step type up
   ~15%, hide the intake panel, and add the handover countdown header. Cheap,
   and it is the demo shot.
9. **Diff-and-patch instead of full `innerHTML` replacement.** `loadBoard()`
   rebuilds everything every 5 seconds, discarding hover and scroll position and
   making change-detection impossible. Patch by issue ID, then add a brief
   non-looping highlight on rows whose state changed — that is the "what
   changed?" answer, and it needs the diff to exist first.
10. **Make refresh failure loud.** A failed poll currently only rewrites the
    `#last-refresh` string. Add a persistent `role="status"` banner and dim the
    board when data is stale — on a wall display, silent staleness is dangerous.

**Accessibility and interaction (small, and currently missing)**

11. Cards are `<article>` elements with a click listener: no `tabindex`, no
    `role="button"`, no Enter/Space handling. Make them keyboard-reachable.
12. The drawer close control is a bare `×` with no `aria-label`, no `Esc`
    handler, no focus trap and no focus restoration. Fix all four.
13. `runIssueAction()` reports failures via `window.alert()`. Render the error
    inline in the drawer instead.
14. Add a visible focus ring to every interactive element; the existing textarea
    focus ring is the right reference.

**Issue drawer (screen `6153ceeed980…`)**

15. The current drawer order — state → action → Human Reach → evidence →
    history → State Authority — is already close to correct, and the recent
    revision fixed the worst of acceptance finding 6. Three refinements remain:
    make the header sticky so title and owner survive scrolling; put
    time-in-state beside the state pill; and give the unverified-claim callout a
    hatched treatment distinct from ordinary `timeline-item` blocks, since it
    currently uses the same styling as neutral history entries.

---

## 6. Stitch suggestions NOT recommended

Stitch's follow-up suggestions were largely sound. These should be declined:

1. **"Show the mobile version of the command center."** Out of scope and
   arguably harmful. Next Shift's operator surface is laptop, tablet and wall.
   A phone layout would force a density compromise into the shared CSS for a
   context nobody works in — frontline workers reach the system through Human
   Reach in Google Chat, not through this UI.
2. **"Make the headers even larger for 5-metre viewing."** Variant 3's scale is
   already tuned for 2–3m. Pushing to 5m costs roughly a third of the visible
   work rows. Distance should be a deployment choice, not a design default.
3. **"Adjust the 'Verified Complete' region to be more subtle."** It is already
   deliberately dim. Making it quieter risks hiding the one region that proves
   the verifier is doing its job — which is precisely what a judge looks for.
4. **"Simulate a 'refresh failed' alert state" as a separate screen.** The
   behaviour is worth building (carry-back 10), but as a state of the real
   board, not as an extra artboard to maintain.
5. **Auto-generated logo/brand imagery.** Stitch generated an "NS" brand mark
   image as part of the first generation. The existing CSS `.brand-mark` — a
   40px teal rounded square with the letters — is lighter, sharper at every
   scale, needs no asset pipeline, and is already consistent. Do not adopt a
   raster logo.
6. **The Material `namedColors` expansion.** Deriving the design system
   produced a full Material token set (`primary_fixed_dim`,
   `on_tertiary_container`, `inverse_on_surface`, and so on). Useful inside
   Stitch, but importing that vocabulary into `app.css` would replace a tight,
   readable 30-token palette with ~50 tokens the product does not use. Keep the
   hand-authored tokens in `.stitch/DESIGN.md` as the source of truth.
7. **`surface: #0b141d` as the background.** Stitch normalised the base surface
   slightly lighter than the real `#071019`. Keep `#071019` — it is tuned for
   continuous dark-room operation and the whole surface ladder is built on it.
