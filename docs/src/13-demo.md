# Presenting VANTA {#ch-demo}

A script for showing VANTA to a professor or judges in about ten minutes, with the points to make
at each step and answers to the questions they are likely to ask.

## Before you start

- Run `./run_dev.sh`, open `http://127.0.0.1:5173`, and generate one world beforehand so the page
  is warm.
- Open a second browser (or a private window) to play a cohort member.
- Optionally, run `python3 -m pytest tests -q` beforehand and keep the "35 passed" result on
  screen.

## The script

1. **The pitch (30 seconds).** "Most challenge platforms hand you a stored problem with a stored
   answer. VANTA writes a broken system on demand, proves it is broken and fixable in more than
   one way, and grades you by running your C."
2. **Generate (1 minute).** Choose *Calibrated to you* and *Generate a world*. While it spins,
   explain that it is *evolving*: six candidates, each compiled and tested against its own hidden
   tests and against two reference fixes, until one is viable.
3. **Read (1 minute).** Show the story, the requirements and the starter. Point out that the names
   and numbers are unique to this seed, and that the code contains no hint comments.
4. **Witnesses (2 minutes).** Ask the long-job user *"What was the worst wait you had?"*, then open
   "show the record behind this". Then type *"How do I fix the code?"* to show the deflection.
   Make the key point: "Nobody holds facts. Everything they say came from running this exact
   code. There is nothing to argue with."
5. **Probe lab (2 minutes).** Write a small experiment: a stream of short jobs plus one long job.
   Run it against the original, and show the timeline, the never-started count or the refusal
   markers.
6. **Fix and replay (2 minutes).** Edit the code (for example, oldest-first among jobs that fit),
   run the same experiment against *my edited code*, and then tick "live through the same period
   under my code". Show that the long-job user is now happy and the short-job user waits longer.
   Make the point: "Two correct designs, different trade-offs."
7. **Submit (30 seconds).** Show *Accepted*, the checks with hidden ones unnamed, and the rating
   change. Then show that the landing page's calibrated difficulty has moved up.
8. **Cohort (2 minutes).** Host a cohort and join it from the second browser. Show the host
   console with different identifiers per member and, after two different fixes, *distinct
   approaches = 2*.

## Likely questions

| Question | Answer |
|---|---|
| "Is this using AI to grade?" | No. Grading is compile + run + read the hidden tests' output. No language model is involved anywhere in grading or in witness answers. |
| "Where are the problems stored?" | Nowhere. Archetypes are programs. A world exists only after it is generated from a seed, and it is proven by execution. |
| "Can students share answers?" | In a cohort, every member's struct and function names differ and the constants differ. Copied code doesn't compile, and the originality analysis groups similar solutions. |
| "How do you know a world is solvable?" | Evolution only serves worlds where at least two architecturally different reference fixes pass the hidden tests. |
| "How does it adapt to beginners and experts?" | An Elo-style rating per person. The next world's target difficulty is set just above that rating, and evolution searches for a world near that target. |
| "Why is this hard to copy?" | The value isn't in any one world. It is in the archetypes, the fitness function, the generate–test–select loop, and the execution-grounded investigation layer. |
| "What's unsafe about running student C?" | It's checked for dangerous calls and sanitized, but it isn't containerized yet (Chapter 11). For a public deployment, the sandbox would move into a container. |
| "What would you add next?" | More defect classes, a container sandbox, accounts, and a hackathon round structure. |
