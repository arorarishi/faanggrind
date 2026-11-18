# BPE tokenizer: train, encode, decode — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/bpe-tokenizer

[AI problems](/ai#problems)

MLCODEImplement it#32Medium

# BPE tokenizer: train, encode, decode

tokenizationbpeutf-8bytespython

## Problem statement

Implement a byte-pair encoding (BPE) tokenizer from scratch in plain Python. It starts from the 256 possible byte values, learns merges from a training text, and then encodes any string to token ids and decodes ids back to the string. No tokenizer library is allowed. The interviewer wants to see the training loop, an encoder that applies merges in the right order, and a round trip that is exact for any UTF-8 text, including text in scripts the tokenizer never saw.

## Requirements

### Functional

* `train(text, vocab_size)` learns `vocab_size - 256` merges: count adjacent pairs, merge the most frequent pair into a new id, repeat.
* `encode(text)` turns a string into a list of ids by applying the learned merges in the order they were learned.
* `decode(ids)` turns ids back into a string.
* Ties between equally frequent pairs are broken by a fixed rule, so training is repeatable.
* Includes self-checks that print what they verify.

### Non-functional

* Lossless: `decode(encode(s)) == s` for every valid UTF-8 string, with 0 "unknown" tokens.
* Ids 0 to 255 are always the raw bytes; merged tokens start at 256, so the vocabulary has exactly 256 + merges entries.
* Deterministic: training twice on the same text and size gives identical merges, and a vocabulary of 276 is a prefix of a vocabulary of 456.
* `encode` never returns more tokens than the text has bytes, and on the training text the count falls with every merge added.
* The naive trainer handles 200 merges on 1 KB of text in under 1 second.

## API

```
def pair_counts(ids: list[int]) -> dict[tuple[int, int], int]: ...
    # [1, 2, 2, 2] -> {(1, 2): 1, (2, 2): 2}

def merge(ids: list[int], pair: tuple[int, int], new_id: int) -> list[int]: ...
    # replace each non-overlapping occurrence of pair, left to right

class BPETokenizer:
    merges: dict[tuple[int, int], int]   # (left id, right id) -> new id, in learned order
    vocab: dict[int, bytes]              # id -> the bytes it stands for

    def train(self, text: str, vocab_size: int) -> list[int]: ...   # returns the compressed training ids
    def encode(self, text: str) -> list[int]: ...
    def decode(self, ids: list[int]) -> str: ...
```

## Data model

```
ids      list[int]                  the text as tokens; starts as its UTF-8 bytes (0..255)
counts   dict[(int, int), int]      how often each adjacent pair occurs in ids
merges   dict[(int, int), int]      pair -> new id; insertion order = rank (256 is rank 0)
vocab    dict[int, bytes]           vocab[new] = vocab[left] + vocab[right]

Training on "aaabdaaabac" (a = 97, b = 98, c = 99, d = 100) with vocab_size 259:

step  ids                        best pair      new id   vocab[new id]
0     a a a b d a a a b a c      (a, a)   x4    256      b"aa"
1     256 a b d 256 a b a c      (a, b)   x2    257      b"ab"     tie with (256, a)
2     256 257 d 256 257 a c      (256, 257) x2  258      b"aaab"
end   258 d 258 a c              11 bytes -> 5 tokens
```

## Approach

1. Turn the training text into UTF-8 bytes and treat each byte as an id from 0 to 255. This is the starting vocabulary. It already covers every possible string.
2. Write `pair_counts`: walk the list once and count each adjacent pair in a dict.
3. Write `merge`: walk the list with an index. When the pair starts at the index, append the new id and jump two places. Otherwise copy one id and move one place. The jump is what makes "aaa" become one merged token plus one `a`, not two overlapping ones.
4. Train: for each new id from 256 up to `vocab_size - 1`, count the pairs, pick the pair with the highest count, merge it everywhere, and record `merges[pair] = new_id` and `vocab[new_id] = vocab[left] + vocab[right]`. Stop early if the text has shrunk to one token.
5. Break ties with a fixed rule. Here the smallest pair wins, compared as a tuple of ints. Without a rule the result depends on dict order, and two tokenizers that disagree on one merge disagree on every later id.
6. Encode: start from the bytes again. Among the pairs present in the text, find the one with the lowest merge id, which is the one learned first. Merge it everywhere. Repeat until no pair in the text is in the merge table.
7. Decode: look up the bytes of every id, join them into one byte string, then decode UTF-8 once. Use `errors="replace"`, because a model can produce ids whose bytes are not valid UTF-8.
8. Test properties: the round trip on several scripts, a case small enough to check by hand, repeatability, and that the token count falls as the vocabulary grows.

## Architecture diagram

Rendering diagram…

## Deep dives

### Bytes or characters as the starting alphabet

A character-level start needs one base token for every character you might meet. Unicode has far more than 100,000 of them, so either the base vocabulary is huge or a rare character becomes an "unknown" token and the round trip breaks. A byte-level start has exactly 256 base tokens and can spell anything. The price is length: an ASCII letter is 1 byte, a Devanagari letter is 3 and most emoji are 4, so text in a script the training data lacked costs several tokens per character.

### Why encode applies merges in rank order

Later merges are built from earlier ones. In the hand case, token 258 is the pair (256, 257), which exists only after 256 and 257 have been formed. Applying the lowest-ranked pair first replays training on the new text, so encoding the training text gives exactly the ids training ended with. The self-check runs the merges in reverse: the output still decodes correctly but has more than twice as many tokens. A model trained on rank-order ids would see those as unfamiliar input.

### The cost of naive training

Each merge rescans the text, so training costs O(N x M) for N bytes and M merges. On a 1 GB corpus with 50,000 merges that is 5 x 10^13 byte visits. Real trainers do three things. They split the text into words first and count each distinct word once with its frequency. They keep the pair counts between merges and update only the neighbours of each merged pair. They keep the counts in a priority queue so that finding the best pair does not scan every pair.

### Special tokens

Markers such as end-of-text or the start of a chat turn get ids outside the merge table. They are never produced by merging bytes. The encoder splits the text on those marker strings first, and only for text you trust. If a user types the marker and it is encoded as the control id, the user can fake the end of a turn. User text must go through the byte path.

### What tokenization means for cost and context

Price, rate limits and the context window are all counted in tokens, not characters. English prose averages about 0.75 words per token, but code, numbers and other languages take more. In the self-check, a tokenizer trained only on English needs about 0.5 tokens per character for new English text and about 2.7 for Hindi. Always count with the tokenizer of the model you will call.

## Evaluation

**Correctness tests.**

* Hand case: "aaabdaaabac" with 3 merges gives merges (a, a), (a, b), (256, 257) and the ids `[258, 100, 258, 97, 99]`.
* Tie-break: after the first merge, (a, b) and (256, a) both occur twice. The smaller pair must win, and a second training run must give the same table.
* Round trip: the empty string, one character, the training text, unseen English, Tamil, Japanese, accented Latin, whitespace and a 4-byte code point all satisfy `decode(encode(s)) == s`.
* Replay: `encode(training_text)` equals the ids that `train` returned.
* Compression: token counts for vocabulary sizes 256, 276, 356 and 456 are strictly decreasing, and the first equals the byte count.
* Order: applying merges in reverse order gives more tokens.
* Bad ids: decoding a lone UTF-8 lead byte returns the replacement character and does not raise.

**Complexity.** Training is O(N x M) time and O(N) memory. Encoding a text of n bytes is O(n) per merge applied, so O(n^2) in the worst case; splitting into words first makes n small. Decoding is O(n).

**What a strong answer adds.** Saying aloud why ids below 256 are reserved, stating the tie-break rule before the interviewer asks, pointing out that decoding token by token breaks multi-byte characters, and sketching the incremental trainer with word counts and a priority queue.

## Bottlenecks & mitigations

* Training rescans the whole text for every merge: O(N x M), far too slow for a real corpus.
* `merge` builds a new list on every call, so memory churn grows with text length times merges.
* `encode` rebuilds the set of pairs after every merge, which is quadratic on long inputs.
* No word splitting, so merges can cross spaces and identical words are encoded again each time; real encoders cache the ids of each word.

## Failure modes

* **Decoding each token separately.** A 3-byte character split across two tokens becomes two broken pieces. Mitigation: join all bytes, then decode once; when streaming, hold bytes back until they form a complete character.
* **No tie-break rule.** The winner depends on dict insertion order, or on hash order in other languages, so two implementations pick different pairs and every later id shifts. Mitigation: a fixed rule and a hand case that contains a tie.
* **Encoding by frequency in the new text.** The merges applied differ from training, so the model sees unfamiliar ids. Mitigation: always pick the lowest merge rank; test that the training text replays exactly.
* **Overlapping merges.** Advancing the index by 1 after a merge turns "aaa" into two merged tokens, which decode to four letters. Mitigation: skip two positions; the round-trip test catches it.
* **Strict UTF-8 decoding of model output.** A model may stop in the middle of a character and `decode` raises. Mitigation: `errors="replace"`.
* **Special token strings inside user text.** The user's text is encoded as a control token. Mitigation: split on special strings only for trusted text.
* **Counting characters to estimate cost.** Non-English text can take several tokens per character. Mitigation: count with the real tokenizer before sending.

## Reference solution

Python · standard library and NumPy only · runs and prints its own checks

```
"""Byte-level BPE tokenizer: train, encode, decode. Standard library only."""
import time

N_BYTES = 256   # ids 0..255 are the raw bytes; merged tokens start at 256

def pair_counts(ids):
    """Count every adjacent pair. [1, 2, 2, 2] -> {(1, 2): 1, (2, 2): 2}."""
    counts = {}
    for pair in zip(ids, ids[1:]):
        counts[pair] = counts.get(pair, 0) + 1
    return counts

def merge(ids, pair, new_id):
    """Replace each non-overlapping occurrence of pair, scanning left to right."""
    out, i = [], 0
    while i < len(ids):
        if i + 1 < len(ids) and ids[i] == pair[0] and ids[i + 1] == pair[1]:
            out.append(new_id)
            i += 2                      # skip both halves of the pair
        else:
            out.append(ids[i])
            i += 1
    return out

class BPETokenizer:
    def __init__(self):
        self.merges = {}                                    # (left, right) -> new id
        self.vocab = {i: bytes([i]) for i in range(N_BYTES)}  # id -> bytes

    def train(self, text, vocab_size):
        """Learn up to vocab_size - 256 merges. Returns the compressed training ids."""
        assert vocab_size >= N_BYTES, "the 256 byte tokens are always in the vocabulary"
        self.merges = {}                                    # training starts from scratch
        self.vocab = {i: bytes([i]) for i in range(N_BYTES)}
        ids = list(text.encode("utf-8"))
        for new_id in range(N_BYTES, vocab_size):
            counts = pair_counts(ids)
            if not counts:                                  # fewer than 2 tokens left
                break
            # Highest count wins. Ties go to the smallest pair, so runs are repeatable.
            pair = min(counts, key=lambda p: (-counts[p], p))
            ids = merge(ids, pair, new_id)
            self.merges[pair] = new_id
            self.vocab[new_id] = self.vocab[pair[0]] + self.vocab[pair[1]]
        return ids

    def encode(self, text):
        """Text -> ids. Apply merges in the order they were learned (lowest id first)."""
        ids = list(text.encode("utf-8"))
        while len(ids) >= 2:
            # Of the pairs present, pick the one learned earliest.
            pair = min(set(zip(ids, ids[1:])), key=lambda p: self.merges.get(p, float("inf")))
            if pair not in self.merges:
                break                                       # nothing left to merge
            ids = merge(ids, pair, self.merges[pair])
        return ids

    def decode(self, ids):
        """Ids -> text. Join the bytes first, then decode once."""
        data = b"".join(self.vocab[i] for i in ids)
        return data.decode("utf-8", errors="replace")

ENGLISH = (
    "a tokenizer turns text into a list of numbers called tokens, and the model only ever "
    "sees those numbers. a common word becomes one token, while a rare word is split into "
    "smaller pieces that the tokenizer has seen before. the price of a request is counted in "
    "tokens, and so is the limit on how much text fits in the context window. the same "
    "sentence can take ten tokens with one tokenizer and twenty with another, so always "
    "count with the tokenizer of the model you will call. training is simple: count every "
    "pair of neighbours, merge the most frequent pair into a new token, and repeat until "
    "the vocabulary is as large as you want. "
)
HINDI = (
    "टोकनाइज़र पाठ को संख्याओं की सूची में बदलता है। मॉडल केवल इन संख्याओं को देखता है। "
    "एक आम शब्द एक टोकन बनता है और दुर्लभ शब्द छोटे टुकड़ों में बँट जाता है। "
)
HELD_OUT_ENGLISH = "the model reads the tokens and counts the price of the whole sentence."
HELD_OUT_HINDI = "यह वाक्य प्रशिक्षण पाठ में नहीं था।"
MIXED = ENGLISH + HINDI

def encode_in_reverse_order(tok, text):
    """A wrong encoder for the self-check: one pass per merge, newest merge first."""
    ids = list(text.encode("utf-8"))
    for pair, new_id in reversed(list(tok.merges.items())):
        ids = merge(ids, pair, new_id)
    return ids

if __name__ == "__main__":
    # 1. A case small enough to do by hand.
    tok = BPETokenizer()
    ids = tok.train("aaabdaaabac", vocab_size=259)
    a, b = ord("a"), ord("b")
    assert list(tok.merges.items()) == [((a, a), 256), ((a, b), 257), ((256, 257), 258)]
    assert ids == [258, ord("d"), 258, a, ord("c")]
    assert tok.vocab[258] == b"aaab"
    print("hand case ok: aaabdaaabac -> 3 merges, 11 bytes become", len(ids), "tokens")

    # 2. Ties. After merge 1, (a, b) and (256, a) both occur twice; the smaller pair wins.
    assert tok.merges[(a, b)] == 257 and (256, a) not in tok.merges
    again = BPETokenizer()
    again.train("aaabdaaabac", vocab_size=259)
    assert again.merges == tok.merges
    print("tie-break ok: equal counts go to the smallest pair, two runs give the same merges")

    # 3. Round trip on text the tokenizer has and has not seen, in several scripts.
    tok = BPETokenizer()
    t0 = time.perf_counter()
    train_ids = tok.train(MIXED, vocab_size=456)
    train_time = time.perf_counter() - t0
    samples = [
        "", "a", MIXED,
        "an unseen sentence with new words: zebra, quartz, xylophone!",
        "தமிழ் மொழி", "日本語のテキスト", "naïve café, 12 €", "tabs\tand\nnewlines  ",
        "four-byte code point: \U0001F680",
    ]
    for s in samples:
        assert tok.decode(tok.encode(s)) == s, s
    assert tok.encode(MIXED) == train_ids
    print(f"round trip ok: {len(samples)} strings, including Hindi, Tamil, Japanese and a 4-byte character")
    print(f"encode(training text) equals the ids training ended with ({len(train_ids)} tokens)")

    # 4. More merges, fewer tokens. A smaller vocabulary is a prefix of a larger one.
    n_bytes = len(MIXED.encode("utf-8"))
    lengths, prev = [], None
    for size in (256, 276, 356, 456):
        t = BPETokenizer()
        t.train(MIXED, vocab_size=size)
        if prev is not None:
            assert list(t.merges.items())[:len(prev.merges)] == list(prev.merges.items())
        lengths.append(len(t.encode(MIXED)))
        prev = t
    assert lengths[0] == n_bytes and all(x > y for x, y in zip(lengths, lengths[1:]))
    print("compression ok: vocab 256/276/356/456 ->", lengths, "tokens for", n_bytes, "bytes")

    # 5. Merge order matters: later merges are built from earlier ones.
    wrong = encode_in_reverse_order(tok, MIXED)
    assert tok.decode(wrong) == MIXED and len(wrong) > len(train_ids)
    print(f"order ok: rank order gives {len(train_ids)} tokens, reverse order gives {len(wrong)}")

    # 6. Decoding must not crash on ids that are not valid UTF-8 on their own.
    assert tok.decode([0xE0]) == "\ufffd"  # U+FFFD, the replacement character
    print("decode ok: a lone lead byte becomes the replacement character, no exception")

    # 7. What the training data covers decides the token count. len() counts code points.
    eng = BPETokenizer()
    eng.train(ENGLISH, vocab_size=456)
    e_ratio = len(eng.encode(HELD_OUT_ENGLISH)) / len(HELD_OUT_ENGLISH)
    h_ratio = len(eng.encode(HELD_OUT_HINDI)) / len(HELD_OUT_HINDI)
    assert h_ratio > 2.0 and e_ratio < 1.0
    print(f"cost: trained on English only, new text -> {e_ratio:.2f} tokens per English "
          f"character, {h_ratio:.2f} per Hindi character")
    print(f"speed: {len(tok.merges)} merges over {n_bytes} bytes in {train_time:.2f} s (naive loop)")
```

## Follow-up questions interviewers ask

* Make training incremental: update the pair counts after each merge without rescanning the text.
* Add special tokens such as end-of-text. How does `encode` treat them in trusted and untrusted text?
* Split the text into words before training. What changes in the merges, and what does a leading space become?
* Make `encode` fast for a 1 MB input.
* How would you save and load the tokenizer so another service gets identical ids?
* How do you choose the vocabulary size, and what does a larger one cost the model?

## Lessons that cover this

* [#4LLM fundamentals - tokens, embeddings, decodingFoundations](/ai/learn/llm-fundamentals)
* [#6Hugging Face end to endFoundations](/ai/learn/hugging-face-end-to-end)

## Further reading

* [Neural Machine Translation of Rare Words with Subword UnitsPaperarxiv.org](https://arxiv.org/abs/1508.07909)
* [Hugging Face Tokenizers documentationGuidehuggingface.co](https://huggingface.co/docs/tokenizers)
* [Hugging Face LLM courseGuidehuggingface.co](https://huggingface.co/learn/llm-course)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousSelf-attention from scratch](/ai/problems/attention-from-scratch)[NextDecoder with a KV cache](/ai/problems/kv-cache-decoding)

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
