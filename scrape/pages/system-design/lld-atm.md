# ATM — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-atm

[All system design questions](/system-design)

#51LLDMediumLow-level design

# ATM

statetransactionssecurityOOP

## Problem statement

Design an ATM that authenticates a card + PIN, shows balance, withdraws cash (with denomination dispensing), deposits, transfers, prints receipts, and talks to a bank service — handling card retention, daily limits and hardware failures.

## Requirements

### Functional

* Insert card → PIN (3 attempts) → menu: balance, withdraw, deposit, transfer, PIN change.
* Withdraw with denomination selection from available cassettes; daily/per-transaction limits.
* Deposit cash/cheque; transfer between accounts.
* Receipt; eject card; retain card after failed attempts.

### Non-functional

* Transactions atomic between ATM cash dispense and bank ledger.
* Secure PIN handling (never stored in plaintext; encrypted to bank).
* State machine prevents invalid sequences.
* Hardware abstraction for testability.

## API

```
void insertCard(Card)
AuthResult enterPin(String pin)
Money checkBalance()
DispenseResult withdraw(Money amount)
void deposit(Money amount)
void transfer(String toAccount, Money amount)
void ejectCard()
```

## Data model

* `ATM(id, location,` State`,` CardReader`,` Keypad`,` Screen`,` CashDispenser`,` DepositSlot`,` Printer`,` BankService`client, current`Session`)`.
* `State` → `IdleState`, `CardInsertedState`, `AuthenticatedState`, `TransactionState`, `OutOfServiceState`.
* `Card(number, expiry, bankId)`, `Account(id, type, balance)`, `Session(card, account, attempts, startedAt)`.
* `Transaction` (abstract) → `Withdrawal`, `Deposit`, `Transfer`, `BalanceInquiry` with `execute()`; `TransactionStatus`.
* `CashDispenser(Map<Denomination, count>)` with `dispense(amount)` using a chain-of-responsibility of dispensers (2000 → 500 → 100).
* `BankService` (interface): `authenticate`, `getBalance`, `debit`, `credit`, `transfer` (remote calls with idempotency keys).

## Design

1. **State pattern**: `Idle → CardInserted → Authenticated → (Transaction) → Authenticated | Idle`; `OutOfService` on hardware/network faults. Each state exposes only its valid operations.
2. **Withdrawal flow**: validate limits → ask bank to **reserve/debit** (idempotency key = ATM id + session + seq) → `CashDispenser.dispense` → on hardware failure, **reverse** the debit → print receipt → return to Authenticated.
3. **Denomination dispensing**: chain of responsibility; each handler dispenses as many of its note as possible (bounded by cassette count) and passes the remainder; if remainder ≠ 0 at the end, refuse before touching the bank.
4. **Security**: PIN entered via keypad object → encrypted PIN block sent to the bank; attempts counted in the session; 3 failures → `CardReader.retain()`.
5. **Hardware abstraction**: interfaces for reader/dispenser/printer so the state machine is unit-testable with fakes.
6. **Session timeout**: inactivity timer ejects the card.

## Class diagram

Rendering diagram…

## Deep dives

**Debit before dispense, reverse on failure**: the bank must never show cash as withdrawn that the customer didn't get; idempotent reversal covers network failure between the two steps.

**Chain of responsibility** for notes makes adding a ₹200 cassette a one-line change.

**Why the ATM never holds account state**: balances come from the bank each time; the ATM caches nothing sensitive.

**Receipts** printed after commit; printer failure doesn't roll back the transaction.

## Bottlenecks & mitigations

* Bank latency → show 'processing'; timeouts with reversal logic.
* Cassette exhaustion → mark denominations empty; alert operator; exact-change limits.

## Failure modes

* **Network timeout after debit request** → unknown outcome; query by idempotency key before dispensing; if unknown, do not dispense and reverse when reachable.
* **Dispenser jam after partial dispense** → record partial amount, reverse the difference, flag for reconciliation.
* **Card left in reader** → retain after timeout; log.
* **Power loss mid-transaction** → journal every step to local storage; reconcile on boot.

## Code skeleton

```
class NoteDispenser:
    def __init__(self, denom, count, nxt=None): self.d, self.n, self.nxt = denom, count, nxt
    def plan(self, amount, out):
        use = min(amount // self.d, self.n); amount -= use * self.d
        if use: out[self.d] = use
        if amount == 0: return out
        if self.nxt: return self.nxt.plan(amount, out)
        return None
    def commit(self, plan):
        if self.d in plan: self.n -= plan[self.d]
        if self.nxt: self.nxt.commit(plan)

class BankService:            # fake for tests
    def __init__(self, accounts): self.acc, self.seen = accounts, {}
    def debit(self, acc, amt, key):
        if key in self.seen: return self.seen[key]
        if self.acc[acc] < amt: raise Exception("insufficient funds")
        self.acc[acc] -= amt; self.seen[key] = True; return True
    def reverse(self, acc, amt, key):
        if self.seen.pop(key, None): self.acc[acc] += amt

class ATM:
    DAILY_LIMIT = 40000
    def __init__(self, bank, dispenser):
        self.bank, self.disp, self.state, self.session, self.seq = bank, dispenser, "IDLE", None, 0
    def insert_card(self, card):
        assert self.state == "IDLE"; self.session = {"card": card, "attempts": 0, "withdrawn": 0}; self.state = "CARD"
    def enter_pin(self, pin):
        assert self.state == "CARD"
        if self.session["card"]["pin"] != pin:
            self.session["attempts"] += 1
            if self.session["attempts"] == 3: self.state = "IDLE"; return "CARD_RETAINED"
            return "WRONG_PIN"
        self.state = "AUTH"; return "OK"
    def withdraw(self, amount):
        assert self.state == "AUTH"
        if self.session["withdrawn"] + amount > self.DAILY_LIMIT: raise Exception("limit")
        plan = self.disp.plan(amount, {})
        if plan is None: raise Exception("cannot dispense this amount")
        self.seq += 1; key = f"{id(self)}-{self.seq}"
        self.bank.debit(self.session["card"]["acc"], amount, key)
        try: self.disp.commit(plan)
        except Exception: self.bank.reverse(self.session["card"]["acc"], amount, key); raise
        self.session["withdrawn"] += amount; return plan
    def eject(self): self.state, self.session = "IDLE", None
```

## Follow-up questions interviewers ask

* Add cardless withdrawal via OTP.
* Add cheque deposit with image capture.
* How would the bank side ensure exactly-once across thousands of ATMs?

[PreviousVending Machine (State pattern)](/system-design/lld-vending-machine)[NextLibrary Management System](/system-design/lld-library-management)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

Goldman SachsJPMorgan ChaseAmerican ExpressAmazonMicrosoft

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
