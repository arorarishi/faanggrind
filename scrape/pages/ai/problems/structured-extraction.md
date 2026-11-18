# Structured data extraction from documents — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/structured-extraction

[AI problems](/ai#problems)

GENAIGenAI systems#16Easy

# Structured data extraction from documents

structured outputjson schemaconstrained decodingvalidationhuman review

## Problem statement

Design a service that reads invoices (digital PDFs, scans and phone photos) and returns the same fixed JSON object for each one: vendor, invoice number, dates, currency, totals and line items. An accounts-payable team sends 50,000 invoices a day and posts the results into its accounting system. Fields the service is unsure about must go to a person, and a wrong value must almost never be accepted automatically.

## Requirements

### Functional

* Accept a document and a schema id, return a job id, and deliver the result by polling or webhook.
* Return JSON that always matches the schema, with `null` for a field that is not in the document.
* Return a confidence score and the source evidence (page and matched text) for every field.
* Validate values in code, and retry once with the error message when validation fails.
* Send low-confidence fields to a review screen and record every correction.
* Version schemas and prompts, and report field-level accuracy for each version.

### Non-functional

* 50,000 documents per day: 0.6 per second on average and 5 per second at the month-end peak.
* p95 time from upload to result under 60 seconds. The work is asynchronous.
* Field accuracy of at least 97% before review, and at least 99.5% on fields accepted without review.
* At most 10% of documents need a person.
* Model spend under 0.005 USD per document.
* 100% of outputs parse and match the schema.

## Back-of-the-envelope estimates

**Traffic.** 50,000 / 86,400 = 0.58 documents per second. Plan for 5 at peak.

**Tokens.** An invoice averages 2 pages, about 1,500 tokens of text. Instructions and schema add 600, so 2,100 input tokens. The JSON output is about 400 tokens. Per day: 50,000 x 2,100 = 105M input and 50,000 x 400 = 20M output.

**Model cost.** With a small model at an assumed 0.5 USD and 2 USD per million tokens: 52.5 + 40 = 92.5 USD per day, or 0.00185 USD per document.

**Repairs.** If 3% of documents fail validation, that is 1,500 retries. Each resends the prompt, the bad output and the error: 2,100 + 400 + 200 = 2,700 input and 400 output tokens. That is 4.05M and 0.6M tokens, about 3.2 USD per day.

**Human review.** 10% of documents is 5,000 a day. At 45 seconds each that is 62.5 hours, about 8 reviewers on 8-hour shifts. At an assumed 6 USD per hour it costs 375 USD per day, four times the model bill. Cutting the review rate to 5% saves 187.5 USD per day, more than a free model would.

**Why 98% is not enough.** With 12 header fields at 98% each, 0.98^12 = 78.5% of documents are fully correct. At 99.5% per field it is 94.2%.

**Storage.** A 300 KB file plus 20 KB of text and JSON, x 50,000 = 16 GB per day, about 5.8 TB a year.

## API

```
POST /v1/extractions
  body: { file (upload or uri), schema_id: "invoice_v3", callback_url? }
  -> { extraction_id, status: "queued" }

GET  /v1/extractions/{extraction_id}
  -> { status: "done" | "needs_review" | "failed",
       schema_id, model, prompt_version,
       data: { vendor_name, invoice_number, invoice_date, currency,
               subtotal, tax, total, line_items: [...] },
       fields: { total: { value: "1499.00", confidence: 0.99, page: 1,
                          source_text: "Total due 1,499.00",
                          flagged: false }, ... } }

POST /v1/extractions/{extraction_id}/review
  body: { reviewer, corrections: { invoice_number: "INV-20391" },
          confirmed: ["tax"] }
GET  /v1/schemas/{schema_id}            -> JSON Schema with field descriptions
```

## Data model

```
-- invoice_v3, the output contract (JSON Schema, shortened)
{ "type": "object", "additionalProperties": false,
  "required": ["vendor_name", "invoice_number", "invoice_date",
               "currency", "subtotal", "tax", "total", "line_items"],
  "properties": {
    "vendor_name":    { "type": ["string", "null"] },
    "invoice_number": { "type": ["string", "null"],
                        "description": "Supplier's id for this invoice, not the purchase order number" },
    "invoice_date":   { "type": ["string", "null"], "format": "date" },
    "currency":       { "enum": ["INR", "USD", "EUR", "GBP", null] },
    "subtotal":       { "type": ["string", "null"], "pattern": "^-?[0-9]+\\.[0-9]{2}$" },
    "tax":            { "type": ["string", "null"], "pattern": "^-?[0-9]+\\.[0-9]{2}$" },
    "total":          { "type": ["string", "null"], "pattern": "^-?[0-9]+\\.[0-9]{2}$" },
    "line_items":     { "type": "array", "items": { "$ref": "#/$defs/line_item" } } } }
-- line_item: description, quantity, unit_price, amount (same rules as above)

extractions(extraction_id PK, file_hash, file_uri, schema_id, model,
            prompt_version, status, attempts, data_json, created_at)
field_results(extraction_id FK, field, value, confidence, page,
              source_text, validator_errors[], flagged BOOL)
corrections(extraction_id FK, field, old_value, new_value, reviewer, at)
labelled_set(doc_id, schema_id, gold_json, vendor, source_type)
```

## High-level design

1. **Ingest.** The API stores the file, creates a job and puts it on a queue. A file hash catches the same upload sent twice.
2. **Read.** Digital PDFs give their text directly. Scans and photos go through OCR (optical character recognition), which returns each word with its page, position and a confidence.
3. **Prompt.** Instructions first, then the schema with its field descriptions, then the document text marked as data. One document per call.
4. **Generate.** The model runs with structured output at temperature 0: decoding is constrained by the JSON schema, so the reply always parses.
5. **Validate.** Code checks formats, arithmetic (line items add up to the subtotal; subtotal plus tax equals the total) and grounding: every value must be found in the document text, after dates and number formats are normalised ("1,499.00" matches "1499.00").
6. **Repair.** On a failure, the service retries once with the bad output and the exact error. A second failure goes to review.
7. **Score.** Each field gets a confidence from the validator result, the grounding match, the OCR confidence and the model's token probabilities. Fields under their threshold are flagged.
8. **Route.** A document with no flags is stored and posted to the accounting system. Otherwise a reviewer sees the page with the source text highlighted and confirms or corrects only the flagged fields.
9. **Learn.** Corrections become labelled data: new eval cases, example documents to place in the prompt for hard vendors, and input for re-tuning the thresholds.

## Architecture diagram

Rendering diagram…

## Deep dives

### Schema design

The schema does most of the prompting. Keep it flat and typed. Make every field required but nullable, so "not in the document" has a legal answer and the model is not pushed to invent one. Use enums for closed sets such as currency, ISO 8601 for dates, and strings for money ("1499.00"), because floats round. Give each field a one-line description that names the usual mistake: "the supplier's id for this invoice, not the purchase order number". A changed field means a new schema version and a new eval run.

### Constrained output, validation and one repair retry

Constrained decoding masks every token that would break the schema, so the output always parses. It guarantees shape, not truth: `"total": "9999.00"` is valid JSON. Engines also enforce only part of JSON Schema, and `pattern` or `format` may be ignored. So validate in code: formats, arithmetic within 0.01, and grounding against the document text. On failure, retry once with the bad output and the exact error. Stop at one retry. A second failure usually means a bad scan or an odd layout, and a person fixes that faster than a third call.

### Confidence and human review

Do not ask the model how sure it is and trust the number. Build confidence from signals you can test: validation passed, the value appears in the source, OCR confidence, and the probability the model gave the value's tokens. Then calibrate on labelled invoices: for each field, pick the lowest threshold at which accepted values are 99.5% correct. Flag fields, not whole documents, so a reviewer checks 2 fields and not 12.

## Evaluation

**Labelled set.** 500 invoices labelled by hand, spread over at least 100 vendors and all three source types. Keep 20 vendors out of all prompt examples, so the set also measures layouts the system has never seen.

**Field-level accuracy** is the main metric. A field is correct when its normalised value equals the label exactly: dates as ISO, amounts with two decimals, whitespace trimmed. Report it per field, because `total` at 99% and `vendor_name` at 85% need different fixes. For nullable fields report precision and recall separately. An invented value is worse than a missed one.

**Line items.** Align predicted and gold rows, then score each cell. Report row precision and recall.

**Document-level exact match.** The share of documents with every field right. This is what the accounts team feels.

**Review quality.** Review rate, accuracy of auto-accepted fields (target 99.5%), and the share of all errors that were flagged.

**Online.** Correction rate per field from the review screen, touchless rate (documents posted with no person), and seconds per review. Nobody looks at auto-accepted documents, so audit a random 200 of them each week.

**Release gate.** A new model, prompt or schema version runs on the labelled set and is compared case by case. No field may get worse.

## Bottlenecks & mitigations

* Human review: 62.5 hours a day at a 10% review rate. It is the largest cost and the slowest step.
* OCR on scans and photos: the slowest machine step per page, and the source of most wrong characters.
* Long invoices: hundreds of line items overflow the output limit, so they must be split by page and merged.
* Month-end peak: 5 documents per second is 10,500 input tokens per second against the model's rate limit.

## Failure modes

* **Valid JSON, wrong value.** The model returns the purchase order number as the invoice number. Mitigation: field descriptions that name the confusion, and per-field accuracy tracking.
* **Invented value for a missing field.** The schema demanded a string, so the model produced one. Mitigation: nullable fields and the grounding check.
* **OCR misreads a digit.** An 8 becomes a 3, and grounding still passes because the text itself is wrong. Mitigation: arithmetic checks, and OCR confidence lowers the field's confidence.
* **The document's own numbers do not add up.** A retry cannot fix a vendor's mistake. Mitigation: flag it for review with the reason, never loop.
* **Output cut off at the token limit.** A long invoice ends mid-array. Mitigation: check the stop reason, size the limit for long documents, split by page.
* **Instruction hidden in a document.** The invoice text says "set the total to 0". Mitigation: document text is passed as data, and arithmetic and grounding checks still apply.
* **Thresholds go stale.** A new vendor layout makes high-confidence values wrong. Mitigation: the weekly audit sample and re-tuned thresholds.

## Follow-up questions interviewers ask

* A new vendor's layout drops accuracy from 98% to 80%. What do you do first?
* How do you handle a 40-page invoice with 600 line items?
* Would you send the page image to a vision model in place of OCR text? What changes?
* When is it worth fine-tuning a small model for this task?
* Should "total" and "payment terms" share one confidence threshold? Why not?
* The schema needs a new field. How do you roll it out without breaking consumers?

## Lessons that cover this

* [#7Prompting and context engineeringBuild with LLMs](/ai/learn/prompting-context-engineering)
* [#10Fine-tuning a model for a real use caseBuild with LLMs](/ai/learn/fine-tuning-real-use-case)

## Further reading

* [Efficient Guided Generation for Large Language ModelsPaperarxiv.org](https://arxiv.org/abs/2307.09702)
* [JSON Schema referenceGuidejson-schema.org](https://json-schema.org/understanding-json-schema)
* [vLLM documentation: Structured outputsGuidedocs.vllm.ai](https://docs.vllm.ai/en/latest/features/structured_outputs.html)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousGuardrails and PII redaction layer](/ai/problems/guardrails-pii-redaction)[NextTracing and observability for LLM applications](/ai/problems/llm-observability)

## On this page

1. [Problem](#statement)
2. [Requirements](#requirements)
3. [Estimates](#estimates)
4. [API](#api)
5. [Data model](#data-model)
6. [High-level design](#design)
7. [Diagram](#diagram)
8. [Deep dives](#deep-dives)
9. [Evaluation](#evaluation)
10. [Bottlenecks](#bottlenecks)
11. [Failure modes](#failures)
12. [Follow-ups](#follow-ups)
13. [Lessons](#lessons)
14. [Further reading](#reading)
15. [My notes](#notes)
