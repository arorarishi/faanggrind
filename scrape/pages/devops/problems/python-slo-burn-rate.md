# Python: SLO error budget and burn-rate alert calculator — DevOps interview problem · FAANGrind

Source: https://faangrind.vercel.app/devops/problems/python-slo-burn-rate

[DevOps problems](/devops#problems)

CODEImplement it#42Easy

# Python: SLO error budget and burn-rate alert calculator

pythonsloerror budgetburn rateprometheusalerting

## Problem statement

Implement an SLO calculator in Python. Given an SLO target (for example 99.9 percent over 30 days) and a per-minute stream of `(good, total)` counts, compute the SLI, the error budget in events and in minutes, the budget consumed so far, the burn rate over sliding windows (5m, 30m, 1h, 2h, 6h, 1d, 3d), and evaluate the multi-window multi-burn-rate page and ticket rules from the SRE workbook. Also compute the time to exhaustion at the current burn rate, and print the Prometheus recording and alerting rules as YAML built from the same numbers. The script must generate its own 30-day test series with a fixed seed and assert its results.

## Requirements

### Functional

* `SLO(target, window_days)` and a `Series(good, total)` of per-minute counts, index 0 oldest.
* `sli`, `error_budget_events`, `error_budget_minutes` and `budget_consumed` as separate functions with one formula each.
* `burn_rate_series(slo, series, window)` returns the burn rate at every minute over a trailing window; `burn_rates_now` returns the value at the last minute for all seven windows.
* `evaluate_alerts` returns per-minute booleans for `page` and `ticket` using exactly the workbook pairs: page on 14.4x over 1h and 5m or 6x over 6h and 30m; ticket on 3x over 1d and 2h or 1x over 3d and 6h.
* `time_to_exhaustion_minutes` and `prometheus_rules` (a YAML string that `yaml.safe_load` parses, with one recording rule per window and the two alerts).
* Self-checks: a seeded 30-day series with a 20-minute incident at a known error rate; assert the page fires inside the incident and clears after it, the ticket never fires, and the budget arithmetic matches a hand-computed number.

### Non-functional

* Standard library plus numpy and yaml only; runs in under 1 s for a 43,200-minute series (7 windows, O(n) each via prefix sums, not O(n x window)).
* Every threshold is derived from `(1 - target)` and the rule table; no literal `0.001` outside the test assertions.
* Burn rates for the first minutes of the series use the partial window from the start, the way PromQL `rate()` does with a short range, and never divide by zero when `total` is 0.
* Output is deterministic: `numpy.random.default_rng(seed)` with a fixed seed, so the printed numbers can be quoted in a review.
* The YAML must match the workbook expression shape so that it can be dropped into a Prometheus rule file after renaming the metrics.

## API

```
Run: python3 slo_burn.py      (prints the report, the YAML and "all checks passed"; AssertionError otherwise)

SLO(target: float, window_days: int)               .window_minutes  .error_fraction = 1 - target
Series(good, total)                                 per-minute int arrays; .bad, .cum_bad, .cum_total

sli(series) -> float                                good / total over the whole series
error_budget_events(slo, series) -> float           total x (1 - target)
error_budget_minutes(slo) -> float                  window_minutes x (1 - target)      (43.2 for 99.9% / 30d)
budget_consumed(slo, series) -> float               bad / budget events               (1.0 = exhausted)
burn_rate_series(slo, series, window) -> ndarray    (bad / total in the trailing window) / (1 - target), per minute
burn_rates_now(slo, series) -> dict                 {"5m": 0.4, "30m": ..., "3d": ...} at the last minute
evaluate_alerts(slo, series) -> {"page": bool[], "ticket": bool[]}
time_to_exhaustion_minutes(slo, series, window="1h") -> float   inf when the burn rate is 0
prometheus_rules(slo, job="myjob", metric="slo") -> str          YAML with 7 recording rules and 2 alerts
report(slo, series) -> None                         prints the human-readable summary
```

## Data model

```
Input: one row per minute, oldest first
  good   int   requests that met the SLI condition (status < 500, latency under the threshold)
  total  int   all requests in that minute
Derived
  bad = total - good
  cum_bad[i], cum_total[i] = sums of the first i minutes, with a leading 0, so any window is 2 lookups

Windows (minutes): 5m=5, 30m=30, 1h=60, 2h=120, 6h=360, 1d=1440, 3d=4320

Rules (SRE workbook, Table 5-8 and the ticket expression, 99.9% SLO):
  long   short   burn   budget spent over the long window   severity
  1h     5m      14.4   2%                                   page
  6h     30m     6      5%                                   page
  1d     2h      3      10%                                  ticket
  3d     6h      1      10%                                  ticket
A rule fires when burn rate > threshold over BOTH windows; short = long / 12.

Test series: 43,200 minutes, 1,000 requests per minute, binomial baseline errors at 0.05%,
one incident of 20 minutes at exactly 5% errors starting at day 20, 10:00.
```

## Approach

1. Validate the series: same length, `good <= total`. Build `bad` and the two prefix-sum arrays with a leading zero.
2. Budget arithmetic: `error_budget_events = total x (1 - target)`; `error_budget_minutes = window_minutes x (1 - target)`; `budget_consumed = bad / error_budget_events`. For 99.9 percent over 30 days that is 43.2 minutes of full outage, or 43,200 bad events at 1,000 requests per minute.
3. Burn rate at minute `i` over window `w`: `start = max(i + 1 - w, 0)`, `bad_w = cum_bad[i + 1] - cum_bad[start]`, the same for total, then `(bad_w / total_w) / (1 - target)`. Do this for all `i` at once with numpy index arrays; it is O(n) per window.
4. Alerts: compute the seven burn-rate arrays once. For each rule, `fires = rate[long] > b and rate[short] > b`; `page` is the OR of its two rules, `ticket` the OR of its two.
5. Time to exhaustion: at burn rate `b` the whole budget lasts `window_minutes / b`; multiply by the fraction still unspent. Return infinity when `b` is 0.
6. Prometheus YAML: one recording rule per window in the workbook's naming, `job:slo_errors_per_request:ratio_rate<w>`, then two alerts whose `expr` is built by joining the rule pairs with `and` inside and `or` between, with thresholds printed as `(14.4*0.001)` so a reviewer sees the burn rate and the SLO, not a precomputed `0.0144`.
7. Self-checks in `main`: assert the four workbook budget fractions (2, 5, 10, 10 percent), generate the series, assert the incident contributed exactly 20 x 50 = 1,000 bad events and that `budget_consumed` equals `(baseline + 1000) / 43200`, assert the 5m burn at the end of the incident is exactly 50, that the page first fires inside the incident and is clear within 5 minutes after it, that the ticket never fires, and that a 14.4x hour on a fresh budget gives 50 hours to exhaustion from full. Parse the YAML back and check the thresholds.

## Architecture diagram

Rendering diagram…

## Deep dives

### The burn-rate math, with the worked example

Burn rate is how fast the service spends its error budget, relative to spending it exactly at the end of the window. For a 99.9 percent SLO the allowed error ratio is 0.001; an observed ratio of 0.0144 is burn rate 14.4. Budget consumed over a window is `burn x window / slo_window`. The workbook example: at 14.4x for 1 hour, `14.4 x 1 h / 720 h = 0.02`, so 2 percent of the 30-day budget is gone in an hour, and the whole budget would be gone in `720 / 14.4 = 50 hours`. Likewise 6x over 6 hours is `36 / 720 = 5 percent` and 1x over 3 days is `72 / 720 = 10 percent`. In the test series the incident runs at 5 percent errors, burn 50 inside it; over the 1-hour window it averages `(20 x 0.05 + 40 x 0.0005) / 60 / 0.001 = 17`, so the 1h and 5m pair fires, while the 3-day average stays near 0.75, below 1, so no ticket.

### Why two windows per rule

A single long window has a bad reset time: the 1-hour average stays above 14.4x for up to an hour after the errors stop, so the page keeps firing on a healthy service. A single short window is noisy: five bad minutes at 3 a.m. page someone for 0.1 percent of the budget. Requiring both fixes it: the long window proves the burn is significant, the short window proves it is still happening. In the script the page clears 3 minutes after the incident ends because the 5m burn drops to baseline, while the 1h burn stays above 14.4 for most of the next hour. The one-twelfth ratio (5m for 1h, 30m for 6h, 6h for 3d) is the chapter's guideline, not a law.

### Long-window reset and the slow burn

The ticket rules catch the error you would never page on: 0.3 percent errors after a Monday deploy is burn 3, which exhausts the budget in 10 days but never reaches 14.4x or 6x. After a day at 3x it has cost 10 percent, and the 2-hour window confirms it is still going, so a ticket opens for business hours and clears when the 2h window drops. Partial windows need care: right after a restart a 3-day rule sees minutes of data and can fire on one bad minute; the test ignores partial 3d windows when it reports the peak.

### When the budget is exhausted

`budget_consumed` above 1.0 means the SLO is missed for this window. The page rules keep running to protect users from the next incident; what changes is policy: freeze feature deploys, do reliability work first, write a postmortem for any incident that spent more than an agreed share. With a rolling window the budget returns as bad days fall out of it. An exhausted budget with no user complaints is evidence the SLO is too strict.

## Evaluation

**Correctness tests.** The `main` block is the test suite: workbook fractions (2, 5, 10, 10 percent), budget events exactly 43,200, incident bad events exactly 1,000, consumed budget equal to `(baseline + 1000) / 43200` to 12 decimal places, 5m burn exactly 50.0 at the end of the incident, page firing inside the incident and clear within 5 minutes after it, ticket never firing, time to exhaustion of 50 hours from a full budget at 14.4x, and the YAML round-tripping through `yaml.safe_load` with `(14.4*0.001)` in the page expression and `(1*0.001)` in the ticket expression.

**Edge cases.** A minute with `total = 0` (overnight batch service) must give burn 0, not a division error. `good > total` must raise. A series shorter than the longest window must still evaluate. A burn rate of 0 gives infinite time to exhaustion. An SLO of 100 percent gives a zero budget and must not divide by zero in `budget_consumed`.

**Complexity.** Prefix sums make every window O(n) regardless of window length, so the seven windows over 43,200 minutes cost about 300,000 array operations and run in about 0.1 s. The naive version, a Python loop with `sum(bad[i-w:i])`, is O(n x w) and takes minutes for the 3-day window.

**What a strong answer adds.** Deriving every threshold from the SLO instead of hard-coding 0.0144; the prefix-sum trick; printing the YAML with the burn rate visible in the expression; the observation that the page's first firing is 16 minutes into the incident (index 16, the 17th minute) because the 1h window needs more than 864 bad events (14.4 x 0.001 x 60,000), the baseline supplies about 20, and the incident adds 50 a minute, so 17 incident minutes are needed; and a clear statement of what the script does not model, which is that Prometheus `rate()` extrapolates at range boundaries and evaluates every 15 to 60 seconds, not per minute.

## Bottlenecks & mitigations

* The longest window (3 days) is the one that decides memory: a per-second series for 30 days is 2.6 million rows, still fine in numpy, but a per-request log is not; aggregate to minutes first.
* Seven windows times the number of services and SLIs: at 200 services with 2 SLIs each this is 2,800 recording rules in Prometheus, which is why rule generation from an SLO file is the common pattern.
* `rate()` over `3d` in Prometheus reads 3 days of samples per evaluation; recording rules exist precisely so that the alert expression reads one series instead.
* Low-traffic services: at 10 requests per minute one bad request in a 5-minute window is 2 percent errors, burn 20, so the short windows flap; the workbook's advice is to lengthen windows or combine services.

## Failure modes

* **Hard-coded 0.0144 in the rule.** The SLO changes to 99.95 and every threshold is silently wrong. Mitigation: compute `burn x (1 - target)` from one constant, as the script does, and print the two factors in the expression.
* **Single long window.** The page stays up for an hour after recovery. Mitigation: the short-window `and`.
* **Single short window.** Pages for noise worth 0.1 percent of budget. Mitigation: the long-window `and`.
* **Dividing by zero traffic.** Overnight minutes with `total = 0` crash the calculator or produce NaN burn rates that compare as false. Mitigation: `np.where(total > 0, ...)` and treat no traffic as burn 0.
* **Counting the budget over calendar months.** Budget resets on the first of the month, and a 29-day incident counts for nothing on day 30. Mitigation: a rolling window, which is what the 30-day series computes.
* **Partial windows at startup.** A 3-day rule fires on the first bad minute after a restart. Mitigation: ignore windows shorter than their length, or in Prometheus accept that `rate()` needs at least two samples and alert on `absent()` separately.
* **Treating `for:` as the fix.** A `for: 1h` clause delays every page by an hour. Mitigation: the chapter rejects durations for SLO alerts; use burn rates.

## Reference solution

Python · runs and prints its own checks

```
"""slo_burn.py: SLO error budget and multi-window multi-burn-rate alert calculator.

Input: an SLO (target, window in days) and a per-minute series of (good, total) counts.
Output: SLI, error budget in events and minutes, budget consumed, burn rate per sliding
window, the page and ticket alert state per minute (SRE workbook chapter 5 thresholds),
time to exhaustion, and the Prometheus rule YAML built from the same numbers.
Standard library plus numpy and yaml. Run: python3 slo_burn.py
"""

from dataclasses import dataclass

import numpy as np
import yaml

MINUTES = {"5m": 5, "30m": 30, "1h": 60, "2h": 120, "6h": 360, "1d": 1440, "3d": 4320}

# SRE workbook, chapter 5, "6: Multiwindow, Multi-Burn-Rate Alerts". Each rule fires when the
# burn rate is above the threshold over BOTH the long and the short window (short = long / 12).
# (long, short, burn rate, budget consumed over the long window, severity)
RULES = [
    ("1h", "5m", 14.4, "2%", "page"),
    ("6h", "30m", 6.0, "5%", "page"),
    ("1d", "2h", 3.0, "10%", "ticket"),
    ("3d", "6h", 1.0, "10%", "ticket"),
]

@dataclass(frozen=True)
class SLO:
    target: float  # 0.999 means 99.9 percent
    window_days: int  # 30

    @property
    def window_minutes(self) -> int:
        return self.window_days * 1440

    @property
    def error_fraction(self) -> float:
        return 1.0 - self.target  # 0.001 for 99.9 percent

class Series:
    """Per-minute (good, total) counts. Index 0 is the oldest minute."""

    def __init__(self, good, total):
        self.good = np.asarray(good, dtype=np.int64)
        self.total = np.asarray(total, dtype=np.int64)
        if self.good.shape != self.total.shape or (self.good > self.total).any():
            raise ValueError("good and total must align and good <= total")
        self.bad = self.total - self.good
        # Prefix sums with a leading zero so any window sum is two lookups: O(1) per window.
        self.cum_bad = np.concatenate([[0], np.cumsum(self.bad)])
        self.cum_total = np.concatenate([[0], np.cumsum(self.total)])

    def __len__(self):
        return len(self.total)

# ---------- budget arithmetic ----------

def sli(s: Series) -> float:
    """Fraction of good events over the whole series (the SLI)."""
    return float(s.good.sum() / s.total.sum()) if s.total.sum() else 1.0

def error_budget_events(slo: SLO, s: Series) -> float:
    """How many bad events the SLO allows over the series: total x (1 - target)."""
    return float(s.total.sum()) * slo.error_fraction

def error_budget_minutes(slo: SLO) -> float:
    """Minutes of total outage the SLO allows per window: 43.2 for 99.9 percent over 30 days."""
    return slo.window_minutes * slo.error_fraction

def budget_consumed(slo: SLO, s: Series) -> float:
    """Fraction of the error budget spent so far (1.0 means exhausted, above 1 means breached)."""
    budget = error_budget_events(slo, s)
    return float(s.bad.sum()) / budget if budget else 0.0

# ---------- burn rate ----------

def burn_rate_series(slo: SLO, s: Series, window: str) -> np.ndarray:
    """Burn rate at every minute over a trailing window: error ratio in the window / (1 - target).

    Burn rate 1 means the budget is spent exactly at the end of the SLO window.
    Minutes before a full window exists use the partial window from the start, like rate().
    """
    w = MINUTES[window]
    n = len(s)
    end = np.arange(1, n + 1)
    start = np.maximum(end - w, 0)
    bad = s.cum_bad[end] - s.cum_bad[start]
    total = s.cum_total[end] - s.cum_total[start]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(total > 0, bad / np.maximum(total, 1), 0.0)
    return ratio / slo.error_fraction

def burn_rates_now(slo: SLO, s: Series) -> dict:
    """Burn rate over every window at the last minute of the series."""
    return {w: float(burn_rate_series(slo, s, w)[-1]) for w in MINUTES}

def evaluate_alerts(slo: SLO, s: Series) -> dict:
    """Per-minute boolean arrays: page and ticket, each the OR of its two window pairs."""
    rates = {w: burn_rate_series(slo, s, w) for w in MINUTES}
    state = {"page": np.zeros(len(s), dtype=bool), "ticket": np.zeros(len(s), dtype=bool)}
    for long_w, short_w, rate, _, severity in RULES:
        state[severity] |= (rates[long_w] > rate) & (rates[short_w] > rate)
    return state

def time_to_exhaustion_minutes(slo: SLO, s: Series, window: str = "1h") -> float:
    """Minutes until the REMAINING budget is gone if the current burn rate (over `window`) holds.

    At burn rate b a full budget lasts window_minutes / b; only the unspent part is left.
    Returns inf when nothing is burning.
    """
    b = burn_rate_series(slo, s, window)[-1]
    remaining = max(0.0, 1.0 - budget_consumed(slo, s))
    return float("inf") if b <= 0 else slo.window_minutes * remaining / b

# ---------- Prometheus rules built from the same numbers ----------

def prometheus_rules(slo: SLO, job: str = "myjob", metric: str = "slo") -> str:
    """Recording rules per window plus the two multiwindow alerts, as a YAML string."""
    e = slo.error_fraction
    lines = ["groups:", "  - name: slo-burn-rate", "    rules:"]
    for w in MINUTES:
        lines += [
            f"      - record: job:{metric}_errors_per_request:ratio_rate{w}",
            "        expr: |",
            f"          sum(rate({metric}_errors[{w}])) by (job)",
            "          /",
            f"          sum(rate({metric}_requests[{w}])) by (job)",
        ]
    for severity in ("page", "ticket"):
        pairs = [r for r in RULES if r[4] == severity]
        clauses = []
        for long_w, short_w, rate, _, _ in pairs:
            clauses.append(
                f"          (\n"
                f"            job:{metric}_errors_per_request:ratio_rate{long_w}{{job=\"{job}\"}} > ({rate:g}*{e:g})\n"
                f"          and\n"
                f"            job:{metric}_errors_per_request:ratio_rate{short_w}{{job=\"{job}\"}} > ({rate:g}*{e:g})\n"
                f"          )"
            )
        lines += [
            f"      - alert: {'FastBurn' if severity == 'page' else 'SlowBurn'}ErrorBudget",
            "        expr: |",
            "\n          or\n".join(clauses),
            "        labels:",
            f"          severity: {severity}",
            "        annotations:",
            f"          summary: '{job} burns its {slo.target:.1%} / {slo.window_days}d error budget too fast'",
        ]
    return "\n".join(lines) + "\n"

# ---------- report ----------

def report(slo: SLO, s: Series) -> None:
    state = evaluate_alerts(slo, s)
    print(f"SLO {slo.target:.1%} over {slo.window_days} days ({slo.window_minutes} minutes)")
    print(f"  SLI so far            : {sli(s):.5%}")
    print(f"  error budget (events) : {error_budget_events(slo, s):,.0f}")
    print(f"  error budget (minutes): {error_budget_minutes(slo):.1f} minutes of full outage")
    print(f"  bad events so far     : {int(s.bad.sum()):,}")
    print(f"  budget consumed       : {budget_consumed(slo, s):.2%}")
    print("  burn rate now         : " + ", ".join(f"{w}={b:.2f}" for w, b in burn_rates_now(slo, s).items()))
    tte = time_to_exhaustion_minutes(slo, s)
    print(f"  time to exhaustion    : {'never at this rate' if tte == float('inf') else f'{tte / 60:.1f} hours'}")
    for sev in ("page", "ticket"):
        mins = int(state[sev].sum())
        print(f"  {sev:6s} alert          : {'FIRING' if state[sev][-1] else 'ok'} now, {mins} firing minutes in the series")

# ---------- self-checks ----------

def generate_series(slo: SLO, seed: int, per_minute: int, baseline_error: float,
                    incident_start: int, incident_minutes: int, incident_error: float) -> Series:
    """A full SLO window of traffic at `per_minute` requests, a small random baseline error
    rate, and one incident with an exact error rate (so the arithmetic is hand-checkable)."""
    rng = np.random.default_rng(seed)
    n = slo.window_minutes
    total = np.full(n, per_minute, dtype=np.int64)
    bad = rng.binomial(per_minute, baseline_error, size=n)
    bad[incident_start:incident_start + incident_minutes] = int(per_minute * incident_error)
    return Series(total - bad, total)

def main() -> None:
    slo = SLO(target=0.999, window_days=30)

    # Worked example from the workbook: burn 14.4 over 1 hour spends 14.4 * 60 / 43200 = 2 percent.
    assert abs(14.4 * 60 / slo.window_minutes - 0.02) < 1e-12
    assert abs(6 * 360 / slo.window_minutes - 0.05) < 1e-12
    assert abs(1 * 4320 / slo.window_minutes - 0.10) < 1e-12
    assert abs(3 * 1440 / slo.window_minutes - 0.10) < 1e-12
    assert abs(error_budget_minutes(slo) - 43.2) < 1e-9
    print("check ok: 14.4x for 1h = 2%, 6x for 6h = 5%, 3x for 1d = 10%, 1x for 3d = 10%; budget = 43.2 minutes")

    per_minute, baseline, inc_start, inc_len, inc_err = 1000, 0.0005, 20 * 1440 + 600, 20, 0.05
    s = generate_series(slo, seed=7, per_minute=per_minute, baseline_error=baseline,
                        incident_start=inc_start, incident_minutes=inc_len, incident_error=inc_err)
    report(slo, s)

    # Budget arithmetic against a hand-computed number: 43,200 minutes x 1,000 = 43.2 M events,
    # budget = 43,200 events; the incident alone is 20 x 50 = 1,000 bad events = 2.3148% of budget.
    assert abs(error_budget_events(slo, s) - 43_200) < 1e-6
    incident_bad = int(s.bad[inc_start:inc_start + inc_len].sum())
    assert incident_bad == 1000
    baseline_bad = int(s.bad.sum()) - incident_bad
    expected = (baseline_bad + 1000) / 43200
    assert abs(budget_consumed(slo, s) - expected) < 1e-12
    assert abs(1000 / 43200 - 0.023148) < 1e-6
    print(f"check ok: budget consumed {budget_consumed(slo, s):.4%} = ({baseline_bad} baseline + 1000 incident) / 43200")

    # Burn rate over a 5m window fully inside the incident is exactly 0.05 / 0.001 = 50.
    b5 = burn_rate_series(slo, s, "5m")
    assert abs(b5[inc_start + inc_len - 1] - 50.0) < 1e-9
    print("check ok: 5m burn rate at the end of the incident is exactly 50.0 (5% errors / 0.1% allowed)")

    # The fast-burn page fires during the incident and clears after it; the slow-burn ticket never fires.
    state = evaluate_alerts(slo, s)
    page, ticket = state["page"], state["ticket"]
    first = int(np.argmax(page))
    assert page.any() and inc_start <= first < inc_start + inc_len
    assert page[inc_start + inc_len - 1]
    cleared = inc_start + inc_len + int(np.argmin(page[inc_start + inc_len:]))
    assert not page[cleared] and cleared - (inc_start + inc_len) <= 5
    assert not page[cleared:].any() and not page[:inc_start].any()
    assert not ticket.any()
    print(f"check ok: page fired {first - inc_start} minutes into the incident, "
          f"cleared {cleared - (inc_start + inc_len)} minutes after it ended (short window reset)")
    full_3d = burn_rate_series(slo, s, "3d")[MINUTES["3d"]:]  # ignore partial windows at the start
    print(f"check ok: ticket (slow burn) never fired: 3d burn peaked at {full_3d.max():.2f}, below 1.0")

    # Time to exhaustion: 30 clean days then one hour at 1.44% errors is burn 14.4 over 1h.
    # A full budget lasts 720 h / 14.4 = 50 h; the hour already spent about 2%, so a bit less is left.
    n = slo.window_minutes
    hot = Series(good=[10000] * n + [10000 - 144] * 60, total=[10000] * (n + 60))
    assert abs(burn_rate_series(slo, hot, "1h")[-1] - 14.4) < 1e-9
    tte = time_to_exhaustion_minutes(slo, hot, "1h")
    left = 1 - budget_consumed(slo, hot)
    assert abs(tte / 60 - 720 * left / 14.4) < 1e-9 and 49.0 < tte / 60 < 50.0
    print(f"check ok: at 14.4x burn a full budget lasts 50.0 h; with {left:.2%} left it lasts {tte / 60:.1f} h")

    # The YAML parses, and the thresholds inside it are the rule numbers times (1 - target).
    text = prometheus_rules(slo)
    doc = yaml.safe_load(text)
    rules = doc["groups"][0]["rules"]
    records = [r for r in rules if "record" in r]
    alerts = [r for r in rules if "alert" in r]
    assert len(records) == len(MINUTES) and len(alerts) == 2
    assert "(14.4*0.001)" in alerts[0]["expr"] and "ratio_rate5m" in alerts[0]["expr"]
    assert "(1*0.001)" in alerts[1]["expr"] and "ratio_rate3d" in alerts[1]["expr"]
    assert alerts[0]["labels"]["severity"] == "page" and alerts[1]["labels"]["severity"] == "ticket"
    print(f"check ok: Prometheus YAML parses with {len(records)} recording rules and 2 alerts")
    print("\n--- prometheus rules ---")
    print(text)
    print("all checks passed")

if __name__ == "__main__":
    main()
```

## Follow-up questions interviewers ask

* Change the SLO to 99.95 percent over 28 days. Which numbers in the YAML change and which do not?
* A service has 5 requests per minute. Show with numbers why the 5m window flaps and what you would change.
* The SLI is latency, not errors. How do you get `good` and `total` from a Prometheus histogram, and what does `le="0.3"` have to do with it?
* Add `observed burn rate` and `budget remaining` to the alert annotations so the page says how long the on-call has.
* Two incidents of 10 minutes at 5 percent errors an hour apart: does the page fire once, twice or not at all?
* The budget is exhausted on day 12. Write the three lines of the error-budget policy you would propose.

## Lessons that cover this

* [#6Python and Go for automation and toolingFoundations](/devops/learn/python-and-go-for-devops)
* [#20Observability - Prometheus, Grafana, OpenTelemetry, logs and alertingOperate](/devops/learn/observability-prometheus-grafana-otel)
* [#21SRE practice - SLOs, error budgets, incidents and postmortemsOperate](/devops/learn/sre-slos-incidents-postmortems)

## Further reading

* [Google SRE Workbook: Chapter 5 - Alerting on SLOsArticlesre.google](https://sre.google/workbook/alerting-on-slos/)
* [Google SRE Book: Chapter 4 - Service Level ObjectivesArticlesre.google](https://sre.google/sre-book/service-level-objectives/)
* [Prometheus: alerting rulesGuideprometheus.io](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousGo: a Kubernetes-style reconcile loop for a custom resource](/devops/problems/go-reconcile-loop)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [API](#api)
4. [Data model](#data-model)
5. [Approach](#design)
6. [Diagram](#diagram)
7. [Deep dives](#deep-dives)
8. [Evaluation](#evaluation)
9. [Bottlenecks](#bottlenecks)
10. [Failure modes](#failures)
11. [Reference solution](#code)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
