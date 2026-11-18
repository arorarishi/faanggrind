# Vending Machine (State pattern) — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-vending-machine

[All system design questions](/system-design)

#50LLDEasyLow-level design

# Vending Machine (State pattern)

stateOOPinventory

## Problem statement

Design a vending machine that accepts coins/notes, lets the user select a product, dispenses it if enough money was inserted, returns change, and handles cancellation, sold-out and insufficient-change situations.

## Requirements

### Functional

* Insert money (multiple denominations); select product; dispense; return change.
* Cancel at any point before dispensing → refund.
* Inventory per slot; admin restock and cash collection.
* Reject selection if sold out or insufficient funds.

### Non-functional

* Illegal transitions impossible (e.g. dispense without payment).
* Easy to add states/products/payment types.
* Change-making handles limited coin inventory.

## API

```
void insertMoney(Denomination d)
void selectProduct(String code)
Product dispense()
List<Denomination> cancel()          // refund inserted money
void adminRestock(code, qty) ; Money adminCollectCash()
```

## Data model

* `VendingMachine`: current `State`, `Inventory`, `CashRegister`, `selectedProduct`, `insertedAmount`.
* `State` (interface): `insertMoney`, `selectProduct`, `dispense`, `cancel`, `refund` → `IdleState`, `HasMoneyState`, `ProductSelectedState`, `DispensingState`, `OutOfServiceState`.
* `Product(code, name, price)`, `Slot(product, quantity)`, `Inventory(Map<code, Slot>)`.
* `Coin`/`Note` enums with values; `CashRegister(Map<Denomination, count>)` with `makeChange(amount)`.

## Design

1. **State pattern**: `VendingMachine` delegates every action to its current `State`; each state implements only the valid actions and throws/ignores the rest, then transitions the machine (`machine.setState(...)`).
   * `Idle`: insertMoney → HasMoney. selectProduct → error.
   * `HasMoney`: insertMoney (accumulate); selectProduct → if sold out: error; if inserted ≥ price and change makeable → ProductSelected; cancel → refund → Idle.
   * `ProductSelected`: dispense → decrement inventory, compute change → Dispensing → Idle.
2. **Change making**: greedy over denominations works for canonical coin systems; back off to DP if the register lacks a denomination; if change can't be made, refuse the sale before dispensing.
3. **Inventory** and **CashRegister** are separate classes so the machine class stays thin.
4. **Events/Observer** for out-of-stock notifications to the operator (optional).

## Class diagram

Rendering diagram…

## Deep dives

**Why State over a big switch**: each state's rules live in one class; adding `MaintenanceState` doesn't touch the others (Open/Closed).

**Change before dispense**: verify `makeChange(inserted − price)` is possible before committing; otherwise you dispense and then can't refund.

**Money as integers** (paise); denominations as an enum with values.

**Transactional dispense**: decrement inventory and add cash together; if the motor fails, revert both.

## Bottlenecks & mitigations

* Greedy change fails for odd coin sets → DP change-making with available counts.
* State objects allocated per transition → use singletons/enums for stateless states.

## Failure modes

* **Insert money then power loss** → persist inserted amount; refund on restart.
* **Dispense motor jams** → revert inventory decrement, refund, go to OutOfService.
* **Concurrent buttons** (hardware) → serialise events in a queue.
* **Exact-change-only mode** when the register is low → disable products needing change.

## Code skeleton

```
class VMError(Exception): pass

class State:
    def insert(self, vm, amt): raise VMError("cannot insert now")
    def select(self, vm, code): raise VMError("cannot select now")
    def dispense(self, vm): raise VMError("nothing to dispense")
    def cancel(self, vm): raise VMError("nothing to cancel")

class Idle(State):
    def insert(self, vm, amt): vm.inserted += amt; vm.state = HasMoney()

class HasMoney(State):
    def insert(self, vm, amt): vm.inserted += amt
    def select(self, vm, code):
        slot = vm.inventory.get(code)
        if not slot or slot["qty"] == 0: raise VMError("sold out")
        if vm.inserted < slot["price"]: raise VMError(f"insert {slot['price'] - vm.inserted} more")
        if vm.register.change(vm.inserted - slot["price"]) is None: raise VMError("cannot make change")
        vm.selected = code; vm.state = ProductSelected()
    def cancel(self, vm):
        refund, vm.inserted = vm.inserted, 0; vm.state = Idle(); return refund

class ProductSelected(State):
    def dispense(self, vm):
        slot = vm.inventory[vm.selected]; slot["qty"] -= 1
        change = vm.register.change(vm.inserted - slot["price"])
        vm.register.deposit(vm.inserted, change)
        vm.inserted, vm.selected, vm.state = 0, None, Idle()
        return slot["name"], change
    def cancel(self, vm): return HasMoney().cancel(vm)

class CashRegister:
    DENOMS = [2000, 500, 200, 100, 50, 20, 10, 5, 1]
    def __init__(self): self.coins = {d: 10 for d in self.DENOMS}
    def change(self, amount):
        out, tmp = [], dict(self.coins)
        for d in self.DENOMS:
            while amount >= d and tmp[d] > 0: amount -= d; tmp[d] -= 1; out.append(d)
        return out if amount == 0 else None
    def deposit(self, inserted, change_given):
        # simplified: assume inserted arrives as largest denominations
        for d in change_given: self.coins[d] -= 1

class VendingMachine:
    def __init__(self, inventory):
        self.inventory, self.register = inventory, CashRegister()
        self.state, self.inserted, self.selected = Idle(), 0, None
    def insert(self, amt): self.state.insert(self, amt)
    def select(self, code): self.state.select(self, code)
    def dispense(self): return self.state.dispense(self)
    def cancel(self): return self.state.cancel(self)
```

## Follow-up questions interviewers ask

* Add card/UPI payments via a PaymentStrategy.
* Add a multi-item cart.
* Add telemetry for stock and sales.

[PreviousChess](/system-design/lld-chess)[NextATM](/system-design/lld-atm)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftSalesforceAdobePayPal

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
