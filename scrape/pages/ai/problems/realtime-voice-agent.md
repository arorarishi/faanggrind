# Real-time voice AI agent — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/realtime-voice-agent

[AI problems](/ai#problems)

GENAIGenAI systems#21Hard

# Real-time voice AI agent

voice agentspeech-to-texttext-to-speechstreamingturn detectionlatency budget

## Problem statement

Design a voice agent that answers an airline's customer phone line: 100,000 calls a day, about 3 minutes each, up to 833 at the same time. Callers speak naturally and can interrupt at any moment. The agent looks up and changes bookings through tools while the call is live. The gap between the caller finishing a sentence and hearing the first word of the reply must feel like a conversation, so every stage has a latency budget. The same agent also runs inside the mobile app.

## Requirements

### Functional

* Hold a spoken conversation over the phone network and in the app, in English and Hindi.
* Detect when the caller has finished a turn, and stop speaking quickly when the caller interrupts (barge-in).
* Call tools during the call: look up a booking, search flights, and change a booking after a spoken confirmation.
* Transfer to a human agent with a summary when the caller asks, after repeated misunderstanding, or when a request is out of scope.
* Accept keypad tones as a fallback for booking references.
* Store the recording (after a consent notice), the transcript and per-stage timestamps for every turn.

### Non-functional

* Voice-to-voice latency, from the end of the caller's speech to the first agent audio leaving the media gateway: target under 800 ms at p50 and 1,500 ms at p95.
* Barge-in: agent audio stops within 400 ms of the caller starting to speak.
* 100,000 calls a day: 208 live calls on average and 833 at peak.
* At least 80% of in-scope calls finished with no human, and wrong booking changes under 0.1%.
* No silence longer than 1.5 s without a spoken filler.
* Cost under 0.12 USD per call at the assumed prices below.

## Back-of-the-envelope estimates

**Traffic.** 100,000 calls x 180 s = 18 million call-seconds a day, or 5,000 call-hours. Average concurrency is 18,000,000 / 86,400 = 208 calls. Daytime peak at 4x: 833.

**One call.** 10 caller turns. A reply is about 20 words: 27 tokens, and 8 s to speak at 150 words per minute. So the agent speaks for 80 s, the caller for 60 s (6 s per turn), and 40 s is gaps and tool waits.

**Latency budget (p50 targets).** End-of-turn wait 250 ms + final transcript 50 ms + LLM first token 250 ms + first clause of 8 tokens at 100 tokens per second 80 ms + first TTS audio 100 ms + network and playout buffer 70 ms = 800 ms. The phone network adds its own delay on top, assumed 100 to 150 ms, so the caller hears the reply after about 900 to 950 ms.

**Tokens.** 10 turns + 3 extra model calls after tool results = 13 calls. Each sends about 2,500 tokens (system prompt 1,200, tools 500, history 800) and returns 30. Per call: 32,500 in and 390 out. At an assumed 1 and 5 USD per million: 0.0325 + 0.00195 = 0.0345 USD.

**Cost per call, all prices assumed.** Speech-to-text: 3 min x 0.006 USD = 0.018. Text-to-speech: 200 words x 6 characters = 1,200 characters at 15 USD per million = 0.018. Telephony: 3 min x 0.01 USD = 0.03. With the LLM: 0.10 USD per call, about 10,000 USD/day.

**Audio.** Phone audio is 8,000 samples per second at 8 bits: 64 kbps, or 160 bytes per 20 ms frame. 833 calls x 2 directions x 64 kbps = 107 Mbps. A recording of both sides is 180 s x 8,000 bytes x 2 = 2.88 MB per call, 288 GB/day before compression.

## API

```
Inbound call (phone network or app) -> media gateway opens a session

WS /v1/calls/{call_id}/media                 (two-way)
  in:  audio frame, 20 ms each | keypad digit
  out: audio frame | { event: "clear" }      (drop audio already queued)

Session events (each has call_id, turn_id, t_ms):
  vad.speech_start        vad.speech_end
  stt.partial { text }    stt.final { text, confidence }
  turn.end { reason: "silence" | "sentence_complete" | "timeout" }
  llm.token { text }      llm.tool_call { name, args }
  tts.audio { frame }     tts.mark { words_played }
  barge_in { words_played }

Tools:
  get_booking(reference)                               read
  search_flights(origin, destination, date)            read
  change_booking(reference, flight_id, idempotency_key)
                                    write, needs a spoken yes first
  transfer_to_human(summary)
```

## Data model

```
calls(call_id PK, channel: phone | app, caller_hash, language,
      started_at, ended_at, consent, recording_uri,
      outcome: completed | transferred | abandoned)

turns(call_id, turn_id, role: caller | agent,
      text_generated,        -- what the LLM wrote
      text_spoken,           -- what was actually played before any cut
      interrupted BOOL,
      t_speech_end, t_turn_end, t_llm_first_token,
      t_tts_first_audio, t_audio_out)
  voice-to-voice latency = t_audio_out - t_speech_end

tool_calls(call_id, turn_id, name, args, idempotency_key,
           confirmed_by_caller BOOL, status, latency_ms)

session state (in memory, checkpointed per turn):
  history[], slots { reference, date, destination },
  playing { utterance_id, words_sent, words_played },
  pending_tool, misunderstanding_count

audio frame: 160 bytes = 20 ms at 8 kHz, 8-bit (phone)
             wider band in the app
```

## High-level design

The design uses the cascaded pipeline: speech-to-text (STT), then an LLM, then text-to-speech (TTS). The first deep dive explains the choice.

**Offline path**

1. A test set of simulated and recorded calls is replayed through the pipeline on every change. Prompts, voices and turn-detection thresholds are versioned together.

**Online path**

2. A call arrives from the phone network or the app. The media gateway opens a session, plays the greeting and the recording notice, and starts passing 20 ms audio frames in both directions.
3. Voice activity detection (VAD) marks each frame as speech or silence. Echo cancellation removes the agent's own voice from the caller's channel.
4. Streaming STT receives every frame and emits partial transcripts while the caller is still speaking, then a final transcript.
5. The turn detector combines the silence length with the partial transcript and decides that the turn is over.
6. The orchestrator builds the prompt (rules, tools, history, known slots) and calls the LLM with streaming on.
7. A chunker cuts the token stream at clause boundaries. Each clause is normalised for speech (dates, amounts, flight codes) and sent to streaming TTS at once.
8. TTS audio flows through the gateway to the caller. The gateway reports how many words have been played.
9. On a tool call, the agent speaks a short filler, runs the tool, and feeds the result back to the LLM. A write tool runs only after a spoken yes.
10. If the caller speaks while the agent is speaking, the barge-in path stops playback, clears queued audio, cancels generation and cuts the history to the words that were heard.
11. Timestamps, transcripts and the outcome are stored. A transfer passes a summary to the human agent.

## Sequence diagram

Rendering diagram…

## Deep dives

### Cascade or speech-to-speech

A speech-to-speech model takes audio in and produces audio out with one model, with no transcript in the middle.

|  | Cascade: STT, LLM, TTS | Speech-to-speech |
| --- | --- | --- |
| Latency | Three stages plus turn detection | One model; one research system reports about 200 ms |
| Control | Text in the middle can be logged, filtered and tested | Needs a text side channel to inspect |
| Tools and rules | Any text LLM with its full tool calling | Whatever the one model supports |
| Tone | Emotion and overlapping speech are lost in the transcript | Hears tone and can handle overlap |

This design picks the cascade. An airline line needs dependable tool calls, a transcript for audit, and the freedom to replace one stage at a time. Keep the orchestrator's interface fixed (audio events in, audio out) so the middle can be swapped once a speech-to-speech model matches the cascade's tool accuracy on our own test calls.

### Streaming at every stage

The 800 ms budget works only if no stage waits for the one before it to finish. STT transcribes while the caller is still speaking, so only the 50 ms of finalising falls inside the gap. The LLM streams tokens, and the chunker sends the first clause to TTS as soon as its comma or full stop arrives, about 8 tokens in. TTS streams audio while it is still synthesising. Waiting for the whole 27-token reply would add 190 ms, and non-streaming TTS would add the time to synthesise all 8 s of audio.

Smaller gains: keep connections to every provider open, run all stages in one region near the phone entry point, and cache the 1,700-token prefix of rules and tools. A speculative start begins the LLM call on the partial transcript at 150 ms of silence and discards it if the caller continues. That buys about 100 ms and wastes some tokens.

### Turn detection and barge-in

The simplest rule ends the turn after a fixed silence. A short wait cuts callers off mid-thought ("my reference is", then a pause to find it). A long wait makes every reply slow. A better detector also reads the partial transcript and predicts whether the sentence is complete: wait 250 ms after "I want to change my flight", and up to 1,500 ms after "my reference is".

Barge-in needs four actions inside 400 ms: stop playback, clear audio already queued at the gateway and the carrier, cancel the LLM and TTS streams, and cut the stored agent turn to the words actually played, using word marks from TTS. Without the last step the LLM believes it said things the caller never heard. A cough, "mm-hm" or the agent's own echo must not trigger it, so require 200 ms of continuous speech or two recognised words, and resume the sentence after a false alarm.

### Tool calls in the middle of a call

A tool takes 0.5 to 3 s, and more than 1.5 s of silence on a phone makes people ask "hello?". So the agent speaks a filler the moment the tool call appears, and the tool runs while it plays. A barge-in cancels speech but never a write that has started. Writes carry an idempotency key built from the call id and turn id, so a retry cannot rebook twice.

STT confuses letters and digits (B, D and P sound alike), so before any write the agent reads the values back: "A B 1 2 C D to Mumbai on the 14th, correct?". Code checks the `confirmed_by_caller` flag before `change_booking` runs. Keypad entry is the fallback for references.

## Evaluation

**Per stage.** STT: word error rate (WER: wrong, missing and extra words divided by the words in the reference) on our own 8 kHz call audio, and separately the error rate on booking references, dates and city names. A transcript with 5% WER can still get the one reference wrong. Turn detection: cut-in rate (the agent started while the caller was mid-turn) and end-of-turn delay. Barge-in: time to stop and false-trigger rate. TTS: listening scores plus a list of hard strings such as flight codes, times and amounts.

**Latency.** From the per-turn timestamps: voice-to-voice p50 and p95 and each stage's share. Place test calls through the real phone network, because server timestamps miss the carrier delay.

**Task level.** Completion checked against the end state in the booking system, not the transcript. Share of calls with no human, transfer rate, wrong-change rate, call length and the post-call rating.

**Offline suite.** 500 scenarios with simulated callers: an LLM plays the caller, TTS gives it a voice, and noise, accents, pauses and interruptions are mixed in. 3 runs each is 1,500 calls. Recorded calls (with consent) are replayed through new STT and turn-detector versions.

**Judging.** An LLM judge scores transcripts for policy steps (did it confirm before changing?), calibrated against human labels. People also listen to 50 calls a week, because a transcript hides tone, overlap and awkward pauses.

**A/B.** Randomise by call and change one thing at a time. Wrong-change rate and transfer rate are guard metrics that stop the test.

## Bottlenecks & mitigations

* The end-of-turn wait: 250 of the 800 ms are spent making sure the caller has finished.
* LLM time to first token: it is the least predictable stage and sets the p95.
* 833 live streams for STT and for TTS, each held open for the whole call.
* The phone network: 8 kHz audio lowers STT accuracy, and the carrier delay of 100 to 150 ms cannot be removed.
* The booking system: at 2 s per lookup, most tool turns need a filler.

## Failure modes

* **The agent cuts the caller off.** A pause to find a number looks like the end of a turn. Mitigation: the transcript-aware turn detector, a longer wait after incomplete phrases, and an alert on the cut-in rate.
* **The agent keeps talking after an interruption.** Seconds of audio are already queued downstream. Mitigation: the clear command, and sending audio only slightly faster than real time.
* **History and reality disagree.** The LLM wrote four sentences and the caller heard one. Mitigation: store `text_spoken` from the word marks and use it in the prompt.
* **A misheard booking reference.** One wrong letter loads another booking or none. Mitigation: read-back, spelling alphabet, keypad entry, and a match on the caller's surname.
* **The agent hears itself.** Speakerphone echo triggers barge-in. Mitigation: echo cancellation, and ignore input that matches the text being spoken.
* **Dead air.** A slow tool or a failing provider leaves silence. Mitigation: a filler at once, a 5 s tool timeout with an apology, a second provider for each stage, then transfer to a human.
* **Symbols read aloud.** The LLM writes a bulleted list and TTS says "asterisk". Mitigation: a prompt written for speech (short sentences, no lists) and a normaliser before TTS.

## Follow-up questions interviewers ask

* The p95 voice-to-voice latency is 2.4 s. How do you find the stage that is responsible?
* When would you switch to a speech-to-speech model, and what would you have to rebuild?
* Callers mix Hindi and English in one sentence. What changes in STT, the prompt and TTS?
* How do you take a card payment by voice so that the card number never reaches the LLM or the recording?
* The caller says "hold on" and talks to someone else in the room. What should the agent do?
* How does the design change at 20,000 concurrent calls?

## Lessons that cover this

* [#21Computer use and multimodal agentsLater](/ai/learn/computer-use-multimodal-agents)

## Further reading

* [Moshi: a speech-text foundation model for real-time dialoguePaperarxiv.org](https://arxiv.org/abs/2410.00037)
* [Robust Speech Recognition via Large-Scale Weak Supervision (Whisper)Paperarxiv.org](https://arxiv.org/abs/2212.04356)
* [Turns overview (LiveKit Agents documentation)Guidedocs.livekit.io](https://docs.livekit.io/agents/build/turns/)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousDocument ingestion and indexing pipeline for LLM use](/ai/problems/document-ingestion-pipeline)[NextCut LLM cost by half: model routing and cascades](/ai/problems/llm-cost-router)

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
