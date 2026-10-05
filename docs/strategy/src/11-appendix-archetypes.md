# Appendix A: Proposed archetype catalogue {#s-appA}

Twenty proposed defect classes, beyond the two that exist today. The "Kind" column refers to
Chapter 4: **A** broken data structure or logic, **B** too slow, **C** optimization, **D**
adversarial game, **M** a multi-subsystem hackathon world. Every row needs at least two distinct
reference fixes before it can be served.

## Catalogue

| System (story) | Kind | Topic | Planted variants (examples) | Distinct correct fixes | Track |
|---|---|---|---|---|---|
| 1. Seat finder for exam halls | A | Binary search | `lo <= hi` loop that never ends; returns any match instead of the first; mid-point overflow | Closed-interval lower bound; half-open interval | DSA in the Wild |
| 2. Hospital triage queue | A | Binary heap | Sift-down compares with the wrong child; size not decremented on pop; parent index off by one | Array heap; bucket queue for small priority ranges | DSA in the Wild |
| 3. Username registry | A | Hash table | Deletion breaks probe chains; no resize at high load; negative hash with `%` | Tombstones; backward-shift deletion; separate chaining | DSA in the Wild |
| 4. Course prerequisite checker | A | Graphs, topological sort | Visited marked on pop; cycle check only from node 0; in-degree not decremented | Kahn's algorithm; DFS with three colours | DSA in the Wild |
| 5. Network outage regions | A | Union-find | Union attaches the wrong root; `find` drops the compressed root | Union by rank; union by size with path halving | DSA in the Wild |
| 6. Session cache | A | LRU (hash + linked list) | Eviction removes the most recent item; stale pointer after a move-to-front; capacity check off by one | Hash + doubly linked list; hash + timestamps with lazy eviction | DSA in the Wild |
| 7. Message relay buffer | A | Ring buffer | Full/empty confusion; wrap-around index bug; overwrite without advancing the tail | Count field; one-empty-slot convention | C Foundations |
| 8. Exam marks aggregator | A | Integers, overflow | Integer-division average; `int` overflow on totals; rounding toward zero for negatives | 64-bit accumulation; scaled integer arithmetic | C Foundations |
| 9. Log line parser | A | Strings, memory | Missing terminator; off-by-one buffer copy; reading past the line end | Length-bounded parsing; tokenizer with explicit lengths | C Foundations |
| 10. Duplicate session finder | B | Hashing, sorting | O(n²) pair comparison | Hash set; sort and scan | Performance |
| 11. Top-k trending tags | B | Heaps, selection | Full re-sort for every query | Size-k min-heap; counting with bucket selection | Performance |
| 12. Room booking conflict checker | B | Intervals, sweep | Scan every booking per query | Sort + sweep; difference array for bounded times | Performance |
| 13. Campus route planner | B | Shortest paths | BFS on weighted edges; Dijkstra with a linear-scan minimum | Dijkstra with a binary heap; 0-1 BFS where weights allow | Performance |
| 14. Sensor rolling average | B | Prefix sums, windows | Recompute the window sum every tick | Running sum; prefix sums | Performance |
| 15. Friend-group counter | B | Incremental connectivity | Flood fill after each new friendship | Union-find; merge-smaller-into-larger sets | Performance |
| 16. Course search autocomplete | B | Tries, sorted search | Linear scan of all names per keystroke | Trie; sorted array + binary search for the prefix range | Performance |
| 17. Exam hall scheduler | C | Scheduling, local search | Baseline: first-fit in input order | Greedy by constraint degree + local search; simulated annealing | Systems & Trade-offs |
| 18. Delivery batching | C | Bin packing, routing | Baseline: one delivery per trip | First-fit decreasing; savings-style route merging | Systems & Trade-offs |
| 19. "Contention" arena game | D | Pathfinding, scheduling, budgets | Baseline bot with planted bugs (Appendix C) | Many strategies by design | Arena |
| 20. Campus facilities platform | M | Integration of several of the above | 4–8 planted defects across booking, laundry and lockers, plus conflicting feature requests | Per subsystem, as above | Hackathon |

## What each archetype must include

Taken from the technical documentation's extension checklist (Chapter 12 there):

- 3 or more story settings, wide identifier pools, and 3 or more variants;
- a harness whose hidden tests really trigger each variant, and check *all* requirements in every
  test;
- 2 or more architecturally distinct reference fixes;
- `params` for the probe lab and witnesses, plus a probe kit and a witness kit;
- tests: viable for every pinned variant; starter rejected and fix accepted under sanitizers; no
  hints in the starter;
- for kind B: measured time limits, with the starter timing out and both fixes passing with
  margin.
