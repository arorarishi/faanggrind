# Stack Overflow (Q&A platform) — LLD — system design · FAANGrind

Source: https://faangrind.vercel.app/system-design/lld-stack-overflow

[All system design questions](/system-design)

#60LLDMediumLow-level design

# Stack Overflow (Q&A platform) — LLD

OOPreputationobserversearch

## Problem statement

Design the domain model for a Q&A site: users ask questions with tags, others answer, comment, vote; the asker accepts an answer; reputation and badges are awarded by rules; questions can be closed/reopened by privileged users; search by tag/keyword.

## Requirements

### Functional

* Post question (title, body, tags), answers, comments on both.
* Upvote/downvote questions and answers (one vote per user per post, changeable).
* Accept an answer; edit history; close/reopen/delete with privileges.
* Reputation rules and badges; notifications on activity.
* Search by keywords and tags; sort by votes/recency.

### Non-functional

* Vote counts consistent (no double voting).
* Reputation rules extensible (strategy); privileges derived from reputation.
* Clean inheritance: Question and Answer share Post behaviour.

## API

```
Question ask(userId, title, body, tags)
Answer   answer(userId, questionId, body)
Comment  comment(userId, postId, text)
void     vote(userId, postId, VoteType)         // idempotent per (user, post); flips if changed
void     accept(askerId, answerId)
void     close(userId, questionId, reason)      // requires privilege
List<Question> search(query, tags, sort)
```

## Data model

* `User(id, name, reputation, badges,` Privileges `derived)`.
* `Post` (abstract: id, author, body, createdAt, `List<Comment>`, `Map<userId, VoteType>` votes, score, `EditHistory`) → `Question(title, tags,` List<Answer>`, acceptedAnswer, status: OPEN|CLOSED|DELETED, views)`, `Answer(question, isAccepted)`.
* `Comment(author, text, createdAt)`, `Tag(name, description)`.
* `Vote(user, post, type)`; `ReputationRule` (strategy): `onUpvote`, `onDownvote`, `onAccept`; `Badge`, `BadgeRule`.
* `SearchIndex` (tag → questions, keyword inverted index).
* `NotificationService` (observer on post events).

## Design

1. **Post hierarchy**: shared voting/commenting/editing in `Post`; `Question` and `Answer` add specifics — classic inheritance question.
2. **Voting**: `votes` map keyed by user; `vote()` removes the previous vote's effect and applies the new one, so score = upvotes − downvotes stays consistent; a user cannot vote on their own post.
3. **Reputation engine**: post events (`Upvoted`, `Downvoted`, `Accepted`) go to `ReputationService`, which applies `ReputationRule`s (+10 upvote on answer, +5 on question, +15 accepted, −2 downvote received, −1 for downvoting) and `BadgeRule`s; reputation floor 1; daily cap.
4. **Privileges** computed from reputation thresholds (`canClose ≥ 3000`, `canEditOthers ≥ 2000`); checked in service methods.
5. **Search**: tag index + simple inverted index over title/body; sort strategies (votes, newest, active).
6. **Observer**: subscribers (question author, answerers) notified on new answers/comments/accepts.

## Class diagram

Rendering diagram…

## Deep dives

**Vote change semantics**: upvote → downvote must undo +1 and apply −1 (net −2) and adjust reputation both ways.

**Accepting**: only the asker; accepting a new answer un-accepts the old one; reputation moves accordingly.

**Edit history** as immutable versions (memento-like) enables rollback and 'edited by' attribution.

**Closing** keeps the question readable, blocks new answers; deletion soft-deletes.

## Bottlenecks & mitigations

* Linear search over questions → inverted index / search engine (see e-commerce search HLD).
* Vote storms on a hot post → per-post lock or DB row; counts cached.
* Reputation recalculation on vote reversal → event-sourced reputation ledger for auditability.

## Failure modes

* **Double vote** → map keyed by user makes it idempotent.
* **Accept after question closed** → allowed (SO allows); document the rule.
* **User deleted** → posts remain, attributed to 'deleted user'.
* **Reputation below 1** → floor.

## Code skeleton

```
import time
from collections import defaultdict

class User:
    def __init__(self, uid): self.id, self.rep, self.badges = uid, 1, set()
    def can(self, action):
        return {"close": 3000, "edit_others": 2000, "vote": 15}.get(action, 0) <= self.rep

class Post:
    def __init__(self, author, body): self.author, self.body, self.votes, self.comments, self.ts = author, body, {}, [], time.time()
    def score(self): return sum(self.votes.values())
    def vote(self, user, v, rep):
        if user is self.author: raise Exception("cannot vote on own post")
        if not user.can("vote"): raise Exception("need 15 reputation to vote")
        old = self.votes.get(user.id, 0)
        if old == v: return
        self.votes[user.id] = v
        rep.on_vote(self, old, v, user)

class Question(Post):
    def __init__(self, author, title, body, tags):
        super().__init__(author, body); self.title, self.tags, self.answers, self.accepted, self.status = title, set(tags), [], None, "OPEN"
    def accept(self, asker, ans, rep):
        if asker is not self.author: raise Exception("only asker can accept")
        if self.accepted: rep.on_accept(self.accepted, -1)
        self.accepted = ans; rep.on_accept(ans, +1)

class Answer(Post):
    def __init__(self, author, question, body): super().__init__(author, body); self.question = question

class ReputationService:
    UP = {"Question": 5, "Answer": 10}
    def on_vote(self, post, old, new, voter):
        kind = type(post).__name__
        def effect(v): return self.UP[kind] if v == 1 else (-2 if v == -1 else 0)
        post.author.rep = max(1, post.author.rep - effect(old) + effect(new))
        voter.rep += (-1 if new == -1 else 0) - (-1 if old == -1 else 0)
    def on_accept(self, ans, sign): ans.author.rep = max(1, ans.author.rep + 15 * sign)

class StackOverflow:
    def __init__(self): self.questions, self.by_tag, self.rep = [], defaultdict(list), ReputationService()
    def ask(self, user, title, body, tags):
        q = Question(user, title, body, tags); self.questions.append(q)
        for t in q.tags: self.by_tag[t].append(q)
        return q
    def answer(self, user, q, body):
        if q.status != "OPEN": raise Exception("question closed")
        a = Answer(user, q, body); q.answers.append(a); return a
    def search(self, text=None, tag=None, sort="votes"):
        pool = self.by_tag[tag] if tag else self.questions
        res = [q for q in pool if not text or text.lower() in (q.title + q.body).lower()]
        key = {"votes": lambda q: -q.score(), "newest": lambda q: -q.ts}[sort]
        return sorted(res, key=key)
```

## Follow-up questions interviewers ask

* Add bounties with expiry.
* Add duplicate-question detection.
* How would you scale reads (feed of newest questions) — see news feed HLD.

[PreviousAmazon Locker (package pickup)](/system-design/lld-amazon-locker)

Saved in this browser. No account needed.

## Commonly asked at

From public interview reports.

AmazonMicrosoftAtlassianAdobeLinkedIn

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
