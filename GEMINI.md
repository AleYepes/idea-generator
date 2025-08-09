# Pain-Point Mining Runbook for LLM Agents
Includes translation, counting recurrences, freshness & authority scoring, and a clear programmatic + human output format.

# Pain-Point Mining Procedure for LLM Agents

## Objective
Systematically identify and document user pain-points by searching targeted online communities using predefined sites and key phrases.

## High-level procedure

### 0. Read `inputs.json`

### 1. Translate `KEY_PHRASES` for all languages listed in `SEARCH_LANGUAGES`

### 2. Build search query templates

* Combine one `PLACE` + one `KEY_PHRASE` + one `TOPIC_PHRASE` into queries.
* Template (literal examples):

```
{PLACE} "{KEY_PHRASE} {TOPIC_PHRASE}"
{PLACE} "{TOPIC_PHRASE}" "can't find" OR "need" OR "any recommendations"
{PLACE} intitle:"{TOPIC_PHRASE}" "help" OR "problem"
```

* Examples:

```
site:reddit.com/r/railroading "is there a tool to maintenance tracking software for rail operators"
site:practicalmachinist.com "how do you buy small quantities molybdenum alloy"
```

* Rule: Don’t combine multiple KEY\_PHRASES in the same query.

### 3. Execute searches

* Run each query with the agent's WebSearch/GoogleSearch tool.
* Fetch top `RESULTS_PER_QUERY` results.
* For each result capture: `url`, `title`, `snippet`, `publication/post date` (if available), `domain`, `type` (thread, blog, Q\&A, news), `meta` (upvotes/comments if Reddit/forum).
* Respect rate limits and stop when `MAX_UNIQUE_SOURCES` reached.

### 4. Filter & de-duplicate

* Remove exact duplicate URLs.
* De-duplicate content by similarity (use fuzzy text similarity on snippet/title/body hash) — merge duplicates but keep all source URLs.
* Prefer primary threads/posts over aggregator pages.

### 5. Extract candidate pain-points

For *each* fetched page:

* Scan for explicit pain sentences (look for keywords: “can’t”, “need”, “wish”, “no tool”, “problem”, “hard to”, “struggle”, “workarounds”, “costly”, “time-consuming”).
* Extract up to 3 verbatim quotes (max 2–3 sentences each) that clearly express a pain or workaround. Record the exact quote, author, date, and URL.
* If a single page mentions multiple pain-points, split into separate candidate pain-points with distinct quotes.

### 6. Normalize & group into broad pain-point categories

* Use semantic clustering (embedding similarity or LLM) to group candidate pain-points into broad categories (e.g., “Spare parts sourcing delays”, “Regulatory paperwork complexity”).
* For each category produce:

  * Category title (short).
  * 1–2 sentence summary synthesizing the pain.
  * List of evidence items (quotes + metadata + url).
  * Recurrence count = number of unique sources mentioning this category.
  * Source list (deduped URLs).

### 7. Score signal strength

Compute a simple composite SignalScore for prioritization:

* RecurrenceNormalized (0–1) = min(1, RecurrenceCount / 10)
* RecencyScore (0–1) = clamp(1 - median\_age\_years/3, 0, 1)  (recent = higher)
* AuthorityScore (0–1) = weighted average of domain/engagement quality:

  * Reddit thread with upvotes ≥ 20 → 0.8; forum post with replies ≥ 5 → 0.6; niche blog → 0.4; general blog/news → 0.3.
  * Normalize to 0–1.

Final:

```
SignalScore = 0.6 * RecurrenceNormalized + 0.25 * RecencyScore + 0.15 * AuthorityScore
```

(Weights configurable.)

### 8. Output & deliverables

Produce both machine-readable JSON and human markdown report (templates below). Include `top N` prioritized pain-points with counts, score, and evidence.

### 9. Follow-ups (automatic suggestions)

For each top pain-point (configurable N, default 5), include:

* Hypothesis statement for validation (1 line).
* Suggested 6 interview questions to confirm/quantify the pain.
* Quick validation experiments (e.g., 5-minute survey template, a landing page copy test, a micro-SaaS MVP checklist).

---

## Required output formats

### A. JSON schema (for automation)

```json
{
  "topic": "<TOPIC_PHRASE>",
  "search_language": "<LANG>",
  "total_sources_analyzed": 123,
  "categories": [
    {
      "id": "cat_01",
      "title": "Spare Parts Sourcing Delays",
      "summary": "Small operators can't find spare parts lead times exceed repair windows...",
      "recurrence_count": 28,
      "median_age_days": 210,
      "authority_score": 0.62,
      "signal_score": 0.81,
      "evidence": [
        {
          "quote": "I had to wait 6 weeks for a relay that should have been a 2-day order...",
          "author": "user123",
          "date": "2024-09-10",
          "url": "https://reddit.com/...",
          "source_type": "reddit",
          "upvotes": 45
        }
      ],
      "source_urls": ["https://reddit.com/...", "https://railforum..."]
    }
  ],
  "recommendations": {
    "top_categories": ["cat_01", "cat_04"],
    "interview_questions_template": ["..."]
  }
}
```

### B. Human Markdown report (copy-paste ready)

```markdown
# Pain-Point Mining — <TOPIC_PHRASE> (English)

Sources analyzed: 123

## Spare Parts Sourcing Delays
Summary: Small/medium operators routinely experience long lead times and brittle supply channels for legacy parts, forcing long downtime or expensive aftermarket fixes.

Signal: 28 sources — SignalScore: 0.81 — Median source date: 2024-09-10

Findings:
> "I had to wait 6 weeks for a relay that should have been a 2-day order..."  
> — u/user123, Reddit — https://reddit.com/...

> "Local yard refuses to keep stock of obsolete couplers; we cannibalize spares."  
> — forum poster, railforums.co.uk — https://railforums.co.uk/...

All sources:  
- https://reddit.com/..., https://railforums.co.uk/...

---

## [Next Category] ...
```

---

## Useful search operator patterns & key-phrase templates

* `site:reddit.com/r/<subreddit> "<KEY_PHRASE> <TOPIC_PHRASE>"`
* `site:*.forum OR site:*.com intitle:"<TOPIC_PHRASE>" "help" OR "problem"`
* `site:linkedin.com "how do you" "<TOPIC_PHRASE>"` (LinkedIn results often need auth; prefer public posts)
* Key phrase patterns to insert topic:

  * `"is there a tool to {TOPIC}"`
  * `"how do you {TOPIC}"`
  * `"{TOPIC}" "can't find" OR "no tool" OR "any recommendations"`
  * `"problems with {TOPIC}"`
* Use quotes to force phrase match, add OR for synonyms.

---

## Data quality & QA checkpoints

* Quote limits: 2–3 sentences per quote; include exact punctuation and preserve context.
* Date capture: always record post/publication date; if missing, mark `unknown` and prefer other sources.
* Deduplication: if a quote appears on >1 URL (mirror), count once for recurrence but keep all URLs.
* Language: if translated content used for evidence, include original text and translated version.
* Source diversity: cap one domain from dominating the top signals; if >40% of recurrence from single domain, mark as `potential bias`.
* Staleness filter: flag categories where >80% of evidence is older than 5 years.

---

## Prioritization & decision rules (suggested)

* High priority: SignalScore ≥ 0.7 AND RecurrenceCount ≥ 5
* Medium priority: SignalScore 0.4–0.7 AND RecurrenceCount ≥ 3
* Low priority: SignalScore < 0.4 OR RecurrenceCount < 3

Use priority buckets to decide which pains to validate with interviews.

---

## Validation pack (auto-generated for top N)

For each top category produce:

* Hypothesis: e.g. *“Operators of rolling stock <500 units lose an average of 8 hours/week due to spare part lead time >2 weeks.”*
* 6 interview questions focusing on frequency, workaround, cost, current toolset, ideal solution, willingness to pay.
* Micro-MVP ideas: landing page copy + 3 feature bullets for an email signup test; simple spreadsheet tool; Chrome extension prototype idea.

---

## Limitations & ethics

* Don’t scrape private groups or paywalled content. Respect robots.txt and site terms.
* When quoting users, redact personally identifying info unless public and consented. Keep quotes brief.
* Consider sampling bias: online forums attract certain user types; combine with at least 5 interviews before productizing.

---

## Quick checklist before handing to an LLM agent

* [ ] Populate `PLACES_TO_INVESTIGATE`, `TOPIC_PHRASES`, `KEY_PHRASES`, `SEARCH_LANGUAGE`.
* [ ] Set `RESULTS_PER_QUERY` and `MAX_UNIQUE_SOURCES`.
* [ ] Confirm translation method if non-English.
* [ ] Decide `TOP_N` categories for follow-up validation.
* [ ] Toggle scoring weights if you want recency/authority emphasized.

---

If you want, I’ll:

* produce a ready-to-run prompt that wraps this runbook for your agent (compact, with variables), or
* generate a spreadsheet template and a scriptable JSON config to plug into an automated agent pipeline. Which would you prefer?
