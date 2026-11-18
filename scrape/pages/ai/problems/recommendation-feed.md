# Recommendation feed — AI interview problem · FAANGrind

Source: https://faangrind.vercel.app/ai/problems/recommendation-feed

[AI problems](/ai#problems)

MLSDML system design#28Hard

# Recommendation feed

recommender systemstwo-towermulti-task rankingfeature storecold starta/b testingReported at Meta, TikTok, Netflix, Pinterest

## Problem statement

Design the home feed of a short-video app with 100 million daily active users and 200 million videos that are eligible for recommendation. Each request returns the next 10 videos for one user, chosen for long-term satisfaction and not only for clicks. The system must answer in 200 ms, react to what the user did seconds ago, give new users and new videos a fair start, and let the team test every model change safely online.

## Requirements

### Functional

* Return a ranked page of 10 videos for a user, and never repeat a video the user has seen in the last 30 days.
* Gather candidates from several sources: embedding retrieval, followed creators, co-watched videos and regional trends.
* Predict several outcomes for each candidate (finish, like, share, follow, skip, report) and combine them into one score with adjustable weights.
* Apply rules after ranking: creator and topic caps for diversity, removal or down-ranking for policy, and reserved slots for new videos.
* Log every impression with the features and scores that produced it, and join later engagement events to it as training labels.
* Run A/B experiments per user on any stage, and fall back to a simpler feed when a stage fails.

### Non-functional

* p99 latency of 200 ms on the server at a peak of 35,000 requests per second (1 billion requests per day).
* Freshness: a like or a skip changes the same user's next request within 10 seconds. Item counters update within 1 minute.
* A new video can be retrieved within 5 minutes of passing moderation.
* The ranking model is retrained at least every hour and the retrieval model every day.
* 99.95% availability. If a stage misses its deadline, the feed still returns 10 videos from a cheaper path.
* Cost control: the heavy ranker scores at most 300 candidates per request.

## Back-of-the-envelope estimates

**Traffic.** 100M daily users x 10 feed requests = 1B requests/day = 11,574 QPS on average. Plan for 3 times that at peak: about 35,000 QPS. Each request shows 10 videos, so 10B impressions/day, or 115,741 per second.

**Funnel per request.** The sources return 1,000 + 300 + 400 + 300 = 2,000 candidates. About 1,500 remain after removing duplicates, seen videos and blocked videos. The light ranker keeps 300, the heavy ranker scores those, and the re-ranker returns 10.

**Scoring load at peak.** Light ranker: 35,000 x 1,500 = 52.5M scores per second, so each score must be almost free. Heavy ranker: 35,000 x 300 = 10.5M scores per second. At an assumed 50,000 scores per second per GPU that is 210 GPUs, or 273 with 30% headroom. Sending all 1,500 to the heavy ranker would need 5 times more. This is why the funnel exists.

**Retrieval index.** 200M videos x 64 dimensions x 4 bytes = 51.2 GB. HNSW graph links (64 neighbour ids x 4 bytes = 256 bytes per vector) add another 51.2 GB. Total 102.4 GB per replica, split into 4 shards of 25.6 GB.

**Features.** Item features: 200M x 400 bytes = 80 GB, small enough to keep in RAM on every ranking server. That matters, because 52.5M item lookups per second cannot be network calls. User features: 500M accounts x 2 KB = 1 TB in a key-value store, read 35,000 times per second.

**Training logs.** 10B impressions x 1 KB of logged features = 10 TB/day, 300 TB for 30 days.

**Latency budget (p99).** Retrieval 30 ms, filter and feature fetch 15 ms, light ranker 15 ms, heavy ranker 60 ms, re-rank 10 ms, network and overhead 20 ms. Total 150 ms, which leaves 50 ms spare.

## API

```
GET /v1/feed?user_id=&session_id=&count=10&cursor=
  200: { request_id,
         items: [{ video_id, position, source, score }],
         next_cursor, experiment_ids: [] }

POST /v1/events                       (batched by the client every few seconds)
  body: { user_id, session_id,
          events: [{ request_id, video_id, position,
                     type: impression | watch | like | share | follow
                           | skip | not_interested | report,
                     watch_ms, video_ms, ts }] }

Internal, each with its own deadline:
POST /retrieve    { user_vector[64], k, language, region }   -> [{ video_id, source }]
POST /rank/light  { user_features, video_ids[1500] }         -> [{ video_id, score }]
POST /rank/heavy  { user_features, video_ids[300] }
                  -> [{ video_id, p_finish, p_like, p_share, p_follow, p_skip, p_report }]
POST /items/{video_id}/embed          (called when a video passes moderation)
```

## Data model

```
videos(video_id PK, creator_id, upload_ts, duration_s, language, region,
       topics[], policy_state, content_embedding[256])

item_vectors(video_id, tower_version, vec float32[64])     -- HNSW index, 4 shards
item_features(video_id -> counters for 1 h, 24 h, 7 d: impressions, finishes,
              likes, shares, skips, reports; creator stats)  -- in RAM on rankers
user_features(user_id -> last_100_events[{video_id, type, watch_ms, ts}],
              topic_affinity{}, creator_affinity{}, country, language, device)
seen_filter(user_id, day -> Bloom filter of video ids)       -- 30 daily filters, oldest dropped
follows(user_id, creator_id)
co_watch(video_id -> top 50 videos watched by the same users)

impression_log(request_id, user_id, video_id, position, source, ts,
               tower_version, ranker_version, experiment_ids[],
               feature_snapshot, scores{})                 -- features as served
event_log(request_id, video_id, type, watch_ms, ts)
training_rows = impression_log JOIN event_log ON (request_id, video_id)
  labels: finish, like, share, follow, skip, report

models(name, version, trained_until_ts, offline_metrics{}, state)
experiments(experiment_id, stage, arms[], traffic_share, hash_salt)
```

## High-level design

**Offline and streaming path**

1. The client sends impressions and engagement events. A stream job joins them on `(request_id, video_id)` and waits 30 minutes for late labels before it writes a training row.
2. The same events update the feature store: the user's recent history in the key-value store within seconds, and the per-video counters on the ranking servers within a minute.
3. The two-tower retrieval model is retrained every day. Its item tower turns each video into a 64-dimension vector, and the vectors are loaded into an approximate nearest neighbour (ANN) index. A new video is embedded when it passes moderation.
4. The ranking model is trained every hour on the newest rows. A new version is published only if its log loss and calibration on held-out data are no worse than the current one.

**Online path**

5. The feed service loads the user's features and runs the user tower to get a user vector that includes actions from seconds ago.
6. Four sources run in parallel with a 30 ms deadline: ANN search (1,000), recent videos from followed creators (300), videos co-watched with the user's last few finishes (400), and trends for the user's region and language (300).
7. The lists are merged. Duplicates, videos in the user's seen filter, blocked creators and videos that fail policy are removed, which leaves about 1,500.
8. The light ranker scores 1,500 and keeps 300.
9. The heavy multi-task ranker predicts six outcomes for each of the 300, and a value formula turns them into one score.
10. The re-ranker builds the page of 10: it applies diversity caps and policy rules and fills the exploration slots.
11. The service returns the page and logs each impression with the exact features and scores used.

If the heavy ranker misses its deadline, the page is built from light-ranker scores. If retrieval fails, a cached list of regional trends is served.

## Architecture diagram

Rendering diagram…

## Deep dives

### Retrieval: two towers, plus sources that cover their blind spots

A two-tower model has a user network and an item network. Each outputs a 64-dimension vector and the score is their dot product. The item tower never sees the user, so all 200M item vectors are computed in advance and an ANN index finds the nearest 1,000 in about 10 ms. The price: no feature may combine user and item, such as "how often has this user watched this creator". Scores are coarse, which is acceptable: retrieval only has to get good videos into the 1,000, not order them. Measure it with recall.

Train on pairs of a user and a video they finished. The other videos in the batch act as negatives. Popular videos then appear as negatives too often and are pushed down unfairly, so subtract the log of each item's sampling probability from its score during training, and add negatives sampled uniformly from the corpus.

One source is never enough. The embedding misses a followed creator's upload from ten minutes ago and a trend that started this hour. The other three sources cover those, and the `source` tag shows what each contributes.

### Ranking: one model, six predictions, one value formula

The heavy ranker sees only 300 candidates, so it can afford what retrieval cannot: user-item cross features, attention over the user's last 100 actions with the candidate as the query, and hundreds of inputs. It is a multi-task model with shared lower layers and one output head per outcome. Sharing lets rare outcomes such as share and follow learn from the common one, finish.

The score is a weighted sum:

`score = w1 p(finish) + w2 p(like) + w3 p(share) + w4 p(follow) - w5 p(skip) - w6 p(report)`

The weights are product decisions, tuned in online experiments. The formula only works if every head is calibrated: of the videos given p(like) = 0.1, about 10% are liked. The light ranker is a small model trained to copy the heavy ranker's ordering, using vectors that can be cached.

### Training data comes from the system's own logs

* **Position and selection bias.** Logs hold only what the old model chose to show, and early slots get more attention whatever is in them. Pass the position as a feature in training and fix it to one value at serving. Keep about 1% of traffic where some slots are filled at random from the candidates, to get data that does not depend on the old model.
* **Delayed labels.** Watch time arrives in seconds, a share in minutes, a report later. The 30-minute join window trades freshness against false negatives. Labels that arrive later are sent as corrections.
* **Negative sampling.** For rare outcomes, keep every positive and a fraction w of the negatives, then correct each prediction: p = p' / (p' + (1 - p') / w). With w = 0.1, a raw 0.5 becomes 0.091. Skip this and the value formula is wrong.
* **Leakage.** Train on the features logged at request time. Counters recomputed later already include the outcome you are predicting.

### Cold start

A new user has no history. Use country, language, device and onboarding interests, serve regional trends, and rely on in-session signals: after 5 to 10 swipes the user tower has real input. This is why 10-second freshness is worth more than a larger model.

A new video has no counters. The item tower uses content features (video, audio and caption embeddings, creator statistics), so the video has a vector at upload. The ranker still under-scores it, so reserve impressions: an assumed 2M new videos per day x 300 impressions = 600M, or 6% of the 10B daily impressions. Show them to users whose vectors are close, and promote those that perform.

### Re-ranking builds a page, not a list of scores

The ranker scores each video alone, so the top 10 can be ten videos by one creator. Pick greedily: take the best video, multiply the scores of the remaining videos from the same creator or topic by a penalty, and repeat. Then apply hard rules: at most 2 videos per creator per page, policy removals, and the exploration slots.

## Evaluation

**Offline, retrieval.** Train on days 1 to 29. On day 30, check what share of the videos each user finished appear in the 1,000 retrieved for that user: Recall@1,000. Report it per source, and separately for new users and for videos under 24 hours old.

**Offline, ranking.** Split by time, never at random, because a random split lets the model see the future. For each head report AUC, log loss and the calibration ratio (sum of predictions / sum of labels, target 0.98 to 1.02). Add per-user AUC: the ranker orders videos for one user, so AUC over all users mixed together rewards knowing which users are active.

**Offline is a gate, not a verdict.** Logged data shows only what the old model served. A model that would serve different videos cannot be scored fully offline.

**Online A/B.** Randomise by a hash of the user id, so one user always gets one variant. Ramp from 1% to 5% to 50% and run for at least 2 weeks, to cover weekly cycles and let novelty effects fade. Change one stage at a time.

* Primary: time spent per daily user and day-7 retention.
* Secondary: finishes, likes, shares and follows per session.
* Guardrails: report rate, "not interested" rate, the share of impressions going to new videos and to small creators, p99 latency and error rate.

**Long-term holdout.** Keep 1% of users on last quarter's system. It measures the total effect of many small launches and catches the case where engagement rises while retention falls.

**Stage health.** For each source, track the share of final impressions it supplied. For each head, track predicted against actual rates every hour.

## Bottlenecks & mitigations

* Heavy-ranker GPUs: 10.5M scores per second at peak. The candidate count of 300 is the main cost control.
* Item feature lookups: 52.5M per second. They must be served from local RAM, and the 80 GB table limits how many features a video can carry.
* The slowest retrieval source: the merge waits for all four, so each has a 30 ms deadline and the merge continues without a late one.
* The label join: 115,741 impressions per second held for 30 minutes is 208M rows of state in the stream job.
* The daily retrieval refresh: a new tower version means 200M videos must be embedded again and the index rebuilt before the switch.

## Failure modes

* **Feedback loop narrows the feed.** The model trains on what it chose to show, so popular videos and one topic per user keep winning. Mitigation: the exploration budget, the random slice, diversity caps, and a metric for the share of the catalogue that gets impressions.
* **Training-serving skew.** A feature is computed one way in the training job and another way online. Mitigation: train only on features logged at serving time and compare feature distributions between the log and live traffic.
* **Tower version mismatch.** A new user tower searches item vectors from the old item tower, and the dot products mean nothing. Mitigation: version both together, build the new index beside the old one and switch both in one step.
* **Label leakage.** Counters that include the impression's own outcome give a high offline AUC and no online gain. Mitigation: snapshot features at request time and split by time.
* **Calibration drift.** A change in the negative sampling rate or in label delay shifts one head, and the value formula quietly re-weights the feed. Mitigation: hourly predicted-against-actual checks per head, with automatic rollback.
* **Clickbait wins.** A video with a strong first second scores well on short-term outcomes. Mitigation: negative terms for skip and report in the value formula, and retention as the primary experiment metric.
* **Feature store slow or down.** Mitigation: per-call timeouts with default feature values, then the light-ranker path, then the cached regional feed.
* **A bad hourly model ships.** A broken upstream log produces a model trained on wrong labels. Mitigation: publish gates on held-out log loss and calibration, a 1% canary, and one-step rollback to the last good version.

## Follow-up questions interviewers ask

* A user taps "not interested". How does that change the very next page?
* The new ranker has 1% higher AUC offline, but time spent is flat in the A/B test. What do you check?
* A user watched three cricket videos and now the whole feed is cricket. How do you fix it?
* How do you rank a brand-new video from a brand-new creator?
* Cut the heavy-ranker GPU bill by half. What are the options and what does each cost in quality?
* How would you choose the weights in the value formula?

## Further reading

* [Scaling the Instagram Explore recommendations systemArticleengineering.fb.com](https://engineering.fb.com/2023/08/09/ml-applications/scaling-instagram-explore-recommendations-system/)
* [Deep Interest Network for Click-Through Rate PredictionPaperarxiv.org](https://arxiv.org/abs/1706.06978)
* [Wide & Deep Learning for Recommender SystemsPaperarxiv.org](https://arxiv.org/abs/1606.07792)

## My notes

## Your notes

Saved

Autosaves to this browser.

[PreviousVector search at billion scale](/ai/problems/vector-search-at-scale)[NextContent moderation with classifiers and LLM review](/ai/problems/content-moderation)

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
13. [Further reading](#reading)
14. [My notes](#notes)
