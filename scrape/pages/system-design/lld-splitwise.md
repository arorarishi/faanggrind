# Splitwise (expense sharing) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-splitwise

[All system design questions](/system-design)

#46LLDMediumLow-level design

# Splitwise (expense sharing)

strategygraphdebt simplificationOOP

## Problem statement

Design an expense-sharing app: users create groups, add expenses paid by one or more people and split equally / by exact amounts / by percentages, view who owes whom, settle up, and optionally simplify debts to the minimum number of transactions.

## Requirements

### Functional

* Users, groups; add expense with payer(s), participants, split type.
* Balances per user pair and per group; activity history.
* Settle up (partial or full).
* Simplify debts within a group.

### Non-functional

* Amounts exact to the paisa/cent (no floating-point drift).
* Split validation (exact amounts sum to total; percentages sum to 100).
* Extensible split types.

## API

```
Expense addExpense(groupId, paidBy: Map<userId, amount>, participants, splitType, splitData)
Map<User, Money> getBalances(userId)             // who I owe / who owes me
List<Transaction> simplifyDebts(groupId)
void settle(fromUserId, toUserId, amount)
List<Expense> history(groupId | userId)
```

## Data model

* `User(id, name, email)`; `Group(id, name, members)`.
* `Expense(id, groupId?, amount:Money, paidBy: Map<User, Money>, splits: List<Split>, splitType, createdBy, ts)`.
* `Split(user, amount)` computed by a `SplitStrategy`: `EqualSplit`, `ExactSplit`, `PercentSplit`, `ShareSplit`.
* `BalanceSheet`: `Map<User, Map<User, Money>>` (net owed, one direction per pair) — maintained per group and globally.
* `Transaction(from, to, amount)` for settlements.
* `Money` value object (long minor units + currency).

## Design

1. **Strategy** for splitting: each `SplitStrategy.split(total, participants, data) → List<Split>` and `validate(...)`. Rounding: distribute remainder paise to the first k participants so the sum is exact.
2. **Balance update** on add expense: for each payer p and each split s, `balance[s.user][p] += s.amount × (p.paid / total)` (proportional when multiple payers). Store net per pair: if A owes B 300 and B owes A 100, store A→B 200.
3. **Debt simplification** (greedy): compute each member's net (paid − owed). Put creditors (net > 0) and debtors (net < 0) into two max-heaps; repeatedly match the largest debtor with the largest creditor, transfer `min(|d|, c)`, push back remainders. Produces ≤ n−1 transactions. (Minimising the count exactly is NP-hard; greedy is standard.)
4. **Settle**: create a `Transaction` and update balances like an expense paid by the debtor for the creditor.
5. **Observer/Notifier**: members notified on new expenses.

## Class diagram

Rendering diagram…

## Deep dives

**Money as integers**: `100.00` split 3 ways = 33.33 + 33.33 + 33.34; the strategy must assign the extra paisa deterministically.

**Pairwise vs net balances**: Splitwise shows pairwise by default (who exactly you owe); simplification converts to nets and re-derives minimal transfers — offer it as a group setting because some users prefer real pairwise debts.

**Multiple payers**: attribute each split proportionally to what each payer contributed.

**Immutability**: expenses are events; edits create a reversal + new expense so history stays auditable.

## Bottlenecks & mitigations

* Balance map growing O(users²) → store only non-zero pairs; per-group sheets.
* Recomputing nets from all expenses → maintain running nets per group, recompute only on edits.
* Concurrent expense adds in one group → serialise per group (lock or single writer).

## Failure modes

* **Split doesn't sum to total** → validation error before any balance change.
* **Expense edit/delete** → apply reversal, then re-add; never mutate balances directly.
* **Rounding drift** → integer money + deterministic remainder distribution; nightly check that group nets sum to zero.
* **Settlement over-pay** → cap at outstanding balance or record as reverse debt, per product decision.

## Code skeleton

```
from collections import defaultdict
import heapq

class EqualSplit:
    def split(self, total, users, data=None):
        n = len(users); base, rem = divmod(total, n)
        return [(u, base + (1 if i < rem else 0)) for i, u in enumerate(users)]
class ExactSplit:
    def split(self, total, users, amounts):
        assert sum(amounts) == total, "amounts must sum to total"
        return list(zip(users, amounts))
class PercentSplit:
    def split(self, total, users, pcts):
        assert abs(sum(pcts) - 100) < 1e-9
        amts = [total * p // 100 for p in pcts]
        for i in range(total - sum(amts)): amts[i] += 1
        return list(zip(users, amts))

class BalanceSheet:
    def __init__(self): self.owes = defaultdict(lambda: defaultdict(int))  # owes[a][b] = a owes b
    def add(self, debtor, creditor, amt):
        if debtor == creditor or amt == 0: return
        back = self.owes[creditor][debtor]
        if back >= amt: self.owes[creditor][debtor] -= amt
        else: self.owes[creditor][debtor] = 0; self.owes[debtor][creditor] += amt - back
    def net(self, users):
        n = {u: 0 for u in users}
        for a in users:
            for b, amt in self.owes[a].items(): n[a] -= amt; n[b] += amt
        return n

class ExpenseManager:
    def __init__(self): self.sheet = BalanceSheet(); self.strategies = {"EQUAL": EqualSplit(), "EXACT": ExactSplit(), "PERCENT": PercentSplit()}
    def add_expense(self, paid_by, participants, split_type, data=None):   # paid_by: {user: amount} in minor units
        total = sum(paid_by.values())
        for user, share in self.strategies[split_type].split(total, participants, data):
            for payer, paid in paid_by.items():
                self.sheet.add(user, payer, share * paid // total)
    def simplify(self, users):
        net = self.sheet.net(users)
        cred = [(-v, u) for u, v in net.items() if v > 0]; debt = [(v, u) for u, v in net.items() if v < 0]
        heapq.heapify(cred); heapq.heapify(debt); out = []
        while cred and debt:
            c, cu = heapq.heappop(cred); d, du = heapq.heappop(debt)
            x = min(-c, -d); out.append((du, cu, x))
            if -c - x: heapq.heappush(cred, (c + x, cu))
            if -d - x: heapq.heappush(debt, (d + x, du))
        return out
```

## Follow-up questions interviewers ask

* Support multi-currency expenses with conversion at expense time.
* Recurring expenses (rent).
* How would you persist this and handle concurrent edits across devices?

[PreviousLRU / LFU Cache](/system-design/lld-lru-cache)[NextMovie Ticket Booking (BookMyShow) — LLD](/system-design/lld-movie-ticket-booking)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonFlipkartSwiggyMicrosoftAtlassianUber

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [API](#api)
4. [Data model](#data-model)
5. [Design](#design)
6. [Diagram](#diagram)
7. [Deep dives](#deep-dives)
8. [Bottlenecks](#bottlenecks)
9. [Failure modes](#failures)
10. [Code skeleton](#code)
11. [Follow-ups](#follow-ups)

## Your notes

Saved

Autosaves to this browser.
