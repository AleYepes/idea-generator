# Pain-Point Mining Procedure for LLM Agents

## Objective
Systematically identify and document user pain-points by searching targeted online communities using predefined sites and key phrases.

## High-level procedure
0. Prepare a canvas or file where to store findings.
For each of the provided queries:
1. Run the query with the agent's WebSearch/GoogleSearch tool.
2. Identify pain-points expressed by users in the search result pages.
3. If a result page unearths pain-points, record an entry in the canvas/file for each painpoint found on the page.
  - Use csv formatting.
  - Include `url`, `painpoint_quote`, `painpoint_summary`, and `post_date` features for every painpoint.
  - Make sure to always include the painpoint's corresponging url.

## Queries
site:reddit.com/r/Entrepreneur "is there a"
site:reddit.com/r/Entrepreneur "looking for a"
site:reddit.com/r/Entrepreneur "software that"
site:reddit.com/r/Entrepreneur "alternatives to"
site:reddit.com/r/Entrepreneur "can\t find"
site:reddit.com/r/Entrepreneur "how do you"
site:reddit.com/r/Entrepreneur "how to fix"
site:reddit.com/r/Entrepreneur "struggling"
site:reddit.com/r/Entrepreneur "not working"
site:reddit.com/r/Entrepreneur "problem"
site:reddit.com/r/Entrepreneur "hay algun"
site:reddit.com/r/Entrepreneur "estoy buscando"
site:reddit.com/r/Entrepreneur "alternativas a"
site:reddit.com/r/Entrepreneur "problema"
site:reddit.com/r/Entrepreneur "busco"
site:reddit.com/r/Entrepreneur "software que"
site:reddit.com/r/Entrepreneur "no encuentro"
site:reddit.com/r/Entrepreneur "no funciona"
site:reddit.com/r/Entrepreneur "como arreglar"

