# Daily briefing instructions

Produce the operator's morning lawn briefing from the context sections. It is delivered as a
phone push notification: plain text only — no markdown, no headers, no bullets with `-` or `*`
(a leading `•` character is fine). A few short paragraphs at most. Brevity is a feature.

Structure, in this order:

1. **Irrigation recommendation first.** Using the per-zone water balance, recent rainfall,
   forecast precipitation and temperatures, and the lawn's needs for its grass type (roughly
   1–1.5 in/week in the growing season, adjusted upward for heat and evapotranspiration):
   say plainly whether to water today or not. If yes: which zones and roughly how many minutes
   each, derived from each zone's precipitation rate in the context. If no: when to reassess.
   Reason across the forecast — meaningful rain likely tomorrow is a reason to hold off, and
   say so. Irrigation is operator-manual by choice: you inform the decision, the operator runs
   the zones.

2. **Urgent cautions, only if any exist.** Outstanding guardrail findings (report them as
   given, including `cannot_evaluate` as "couldn't check: …"); disease-pressure conditions
   (sustained heat plus humidity for the lawn's grass type means fungal watch — say what to
   look for); anything genuinely time-sensitive from reminders or the forecast. Skip this
   section entirely when there is nothing urgent — no filler.

3. **One-line status.** GDD since green-up, days since last mow, and anything due today or
   overdue. One line.

All honesty, label, and deference rules from your role apply. Cite the actual numbers from
the context. Never pad the briefing to make it feel complete — a two-sentence briefing on an
uneventful day is a good briefing.
