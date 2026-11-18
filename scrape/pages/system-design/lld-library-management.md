# Library Management System — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-library-management

[All system design questions](/system-design)

#52LLDEasyLow-level design

# Library Management System

OOPsearchstatenotifications

## Problem statement

Design a library system: catalogue of books with multiple copies, members who borrow/return/reserve, due dates and fines, search by title/author/ISBN, and notifications for due/overdue and reservation availability.

## Requirements

### Functional

* Add/remove books and copies; search by title, author, subject, ISBN.
* Member checkout (limit N books), return, renew; reserve a book with a queue.
* Fines for overdue returns; block members with unpaid fines.
* Notifications: due soon, overdue, reserved copy available.

### Non-functional

* Copy-level state tracked accurately (available/loaned/reserved/lost).
* Search efficient over 1M titles (indexes).
* Business rules configurable (limits, fine rate, loan period).

## API

```
List<Book> Catalog.search(query, SearchType)
Loan   Library.checkout(memberId, barcode)         // rules: limit, no unpaid fines, item available/reserved-for-you
void   Library.returnItem(barcode)                 // computes fine, notifies next reservation
Loan   Library.renew(loanId)                       // denied if reserved by someone else
void   Library.reserve(memberId, isbn)
Money  Library.payFine(memberId, amount)
```

## Data model

* `Book(isbn, title, authors, subjects, publisher)` — the title; `BookItem(barcode, book, status, location, dueDate, borrowedBy)` — a physical copy.
* `Member(id, name,` List<BookItem> `loans, fines)`, `Librarian`.
* `Reservation(book, member, createdAt, status)` with a FIFO queue per book.
* `Loan(item, member, issuedAt, dueAt, returnedAt)`.
* `Fine(member, amount, reason, paid)`.
* `Catalog` with indexes: `Map<title→books>`, `Map<author→books>`, `Map<isbn→book>`.
* `NotificationService` (observer) with `EmailNotifier`, `SmsNotifier`.

## Design

1. **Book vs BookItem** separation is the core modelling point: reservations are on the title; loans are on the copy.
2. **Checkout rules** in a `CheckoutPolicy` (strategy): max loans, fine block, reservation priority (if the title has a reservation queue, only the head member may take an available copy).
3. **Return**: mark item available, close loan, compute fine via `FinePolicy` (per-day rate, cap), then if a reservation exists → mark the item `RESERVED` for the head member and notify; else available.
4. **State** on `BookItem`: `AVAILABLE → LOANED → AVAILABLE`, `RESERVED`, `LOST`.
5. **Scheduler** runs daily: due-soon and overdue notifications; expire reservations not collected within 3 days.
6. **Search** via in-memory indexes (or a search engine) keyed by normalised strings; prefix search on title with a trie for autocomplete.

## Class diagram

Rendering diagram…

## Deep dives

**Reservation priority on return**: without it a walk-in member could take the copy the reserver has waited for.

**Renewals** denied when others are waiting — a common rule interviewers expect.

**Fines as ledger entries** (not a mutable number) so payments and waivers are auditable.

**Lost items**: state `LOST` + replacement fee; removed from availability counts.

## Bottlenecks & mitigations

* Search over titles/authors → indexes/trie; a search engine at scale.
* Daily overdue scan over all loans → index loans by due date.
* Hot titles with long reservation queues → cap queue length; expire uncollected reservations.

## Failure modes

* **Double checkout of a copy** → status check + single-threaded per item (lock).
* **Return of an item not loaned** → validation error.
* **Member deleted with active loans** → soft-delete; block until returns.
* **Fine calculation across leap days/holidays** → use date library; configurable calendar.

## Code skeleton

```
from collections import deque, defaultdict
from datetime import date, timedelta

class BookItem:
    def __init__(self, barcode, book): self.barcode, self.book, self.status, self.holder, self.due = barcode, book, "AVAILABLE", None, None
class Book:
    def __init__(self, isbn, title, authors):
        self.isbn, self.title, self.authors, self.items, self.reservations = isbn, title, authors, [], deque()
class Member:
    def __init__(self, mid): self.id, self.loans, self.fines = mid, {}, 0

class Library:
    MAX_LOANS, LOAN_DAYS, FINE_PER_DAY = 5, 14, 2
    def __init__(self): self.books, self.items, self.members = {}, {}, {}
    def add_copy(self, isbn, barcode):
        it = BookItem(barcode, self.books[isbn]); self.books[isbn].items.append(it); self.items[barcode] = it
    def checkout(self, mid, barcode):
        m, it = self.members[mid], self.items[barcode]
        if m.fines > 0: raise Exception("unpaid fines")
        if len(m.loans) >= self.MAX_LOANS: raise Exception("loan limit")
        q = it.book.reservations
        if it.status == "RESERVED" and (not q or q[0] != mid): raise Exception("reserved for another member")
        if it.status not in ("AVAILABLE", "RESERVED"): raise Exception("not available")
        if q and q[0] == mid: q.popleft()
        it.status, it.holder, it.due = "LOANED", mid, date.today() + timedelta(days=self.LOAN_DAYS)
        m.loans[barcode] = it
    def return_item(self, barcode):
        it = self.items[barcode]; m = self.members[it.holder]
        overdue = (date.today() - it.due).days
        if overdue > 0: m.fines += overdue * self.FINE_PER_DAY
        del m.loans[barcode]; it.holder = it.due = None
        if it.book.reservations:
            it.status = "RESERVED"; self.notify(it.book.reservations[0], f"{it.book.title} is available")
        else: it.status = "AVAILABLE"
    def reserve(self, mid, isbn):
        b = self.books[isbn]
        if any(i.status == "AVAILABLE" for i in b.items): raise Exception("copy available, just borrow it")
        if mid not in b.reservations: b.reservations.append(mid)
    def notify(self, mid, msg): print(f"notify {mid}: {msg}")
```

## Follow-up questions interviewers ask

* Add e-books with concurrent-license limits.
* Multi-branch library with inter-branch transfers.
* Recommendation of books based on borrowing history.

[PreviousATM](/system-design/lld-atm)[NextLogging Framework (like Log4j)](/system-design/lld-logging-framework)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonGoldman SachsMicrosoftAdobe

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
