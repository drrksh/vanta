import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Chip, Label, Panel } from '../components/ui'

/*
  The in-app guide for people who have never used VANTA. It explains the
  workflow in the order a newcomer meets it, with copyable example
  experiments, and stays in the same blueprint visual language as the app.
*/

const SECTIONS: [string, string][] = [
  ['what', 'What VANTA is'],
  ['first', 'Your first world'],
  ['reading', 'Reading a world'],
  ['witnesses', 'Witnesses'],
  ['probe', 'Probe lab'],
  ['submit', 'Submitting & checks'],
  ['rating', 'Rating & difficulty'],
  ['cohorts', 'Cohorts'],
  ['discord', 'Discord'],
  ['tips', 'Investigation tips'],
  ['faq', 'FAQ'],
  ['glossary', 'Glossary'],
]

const JOB_EXAMPLE = `{
  "days": 4,
  "jobs": [
    { "minutes": 8, "at": 0,
      "repeat": 200, "every": 5 },
    { "minutes": 300, "at": 30 }
  ]
}`

const POOL_EXAMPLE = `{
  "ops": [
    { "op": "checkout", "holder": 5 },
    { "op": "release", "holder": 5 },
    { "op": "release", "holder": 5 },
    { "op": "cycle", "holder": 100,
      "repeat": 40, "step": 7 }
  ]
}`

export default function GuidePage() {
  return (
    <div className="grid gap-10 lg:grid-cols-[190px_1fr]">
      <nav className="hidden lg:block" aria-label="Guide sections">
        <div className="sticky top-6 space-y-1">
          <Label>On this page</Label>
          {SECTIONS.map(([id, title]) => (
            <a key={id} href={`#${id}`} className="block rounded px-2 py-1 text-[13px] transition-colors hover:bg-[var(--panel)]"
              style={{ color: 'var(--ink-dim)' }}>{title}</a>
          ))}
        </div>
      </nav>

      <article className="min-w-0 space-y-14">
        <header>
          <div className="mb-3 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: 'var(--structure)' }} />
            <span className="mono text-[11px] uppercase" style={{ color: 'var(--structure)', letterSpacing: '0.14em' }}>
              guide · about 5 minutes
            </span>
          </div>
          <h1 className="display max-w-[22ch] text-[38px] leading-[1.08]" style={{ fontWeight: 600 }}>
            How VANTA works, from your first world to your first fix.
          </h1>
          <p className="mt-4 max-w-[64ch] text-[16px]" style={{ color: 'var(--ink-dim)' }}>
            VANTA builds a small, broken C system just for you, proves the bug is real, and lets you
            investigate it the way an engineer would: by asking people who used it and by running
            experiments. When you think you've found the problem, you fix the code and the hidden
            tests decide.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/" className="vanta-focus rounded-md px-4 py-2 text-[14px] font-medium"
              style={{ background: 'var(--structure)', color: '#07131a' }}>Generate a world</Link>
            <a href="#first" className="vanta-focus rounded-md border px-4 py-2 text-[14px]"
              style={{ borderColor: 'var(--line-bright)', color: 'var(--ink-dim)' }}>Walk me through it</a>
          </div>
        </header>

        <Section id="what" title="What VANTA is">
          <div className="grid gap-3 md:grid-cols-3">
            <Card title="Built for you" body="Every world is generated on demand from a random seed: its own story, its own names, its own numbers, and one real defect. There is no problem bank." />
            <Card title="Proven by running" body="Before you see it, VANTA compiles the system and runs its hidden tests to prove it's broken, and that at least two genuinely different fixes pass." />
            <Card title="More than one right answer" body="Different correct designs exist, and they have different trade-offs. You'll see those trade-offs in the evidence." />
          </div>
          <P>
            You won't be arguing with chatbots. The people you can question in VANTA have no script.
            Each of them lived through one real run of the broken system, and everything they tell
            you was produced by executing it.
          </P>
        </Section>

        <Section id="first" title="Your first world in six steps">
          <ol className="space-y-3">
            {[
              ['Generate', <>On the home page pick a <b>defect class</b> (or <i>Surprise me</i>) and leave difficulty on <b>Calibrated to you</b>. Press <b>Generate a world</b>. It takes a few seconds, because VANTA is evolving and testing candidate systems.</>],
              ['Read the brief', <>Read the <b>Situation</b>, the <b>Task</b> and the <b>Requirements</b>. The requirements are what the hidden tests check. Then read the source: it's the current, broken behaviour.</>],
              ['Ask witnesses', <>Open <b>Witnesses</b> and ask each person a question or two. Look for what doesn't add up.</>],
              ['Run an experiment', <>Open <b>Probe lab</b> and write a scenario that should trigger what you suspect. Run it against <b>the original system</b>.</>],
              ['Fix it', <>Edit the source. Run the same experiment against <b>my edited code</b>, and have a witness <b>live through the same period under your code</b>.</>],
              ['Submit', <>Press <b>Submit fix</b>. Hidden tests run under memory-safety checks. If it's accepted your rating rises, and your next world is pitched a little harder.</>],
            ].map(([t, d], i) => (
              <li key={i} className="flex gap-4">
                <span className="display mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[13px]"
                  style={{ background: 'var(--panel-2)', color: 'var(--structure)', fontWeight: 600 }}>{i + 1}</span>
                <div>
                  <div className="display text-[15px]" style={{ fontWeight: 600 }}>{t}</div>
                  <div className="text-[14.5px]" style={{ color: 'var(--ink-dim)' }}>{d}</div>
                </div>
              </li>
            ))}
          </ol>
        </Section>

        <Section id="reading" title="Reading a world">
          <Table rows={[
            ['Situation', 'The story: who uses the system and what people are complaining about. It hints at symptoms, never at the cause.'],
            ['Your task', 'Which function you must implement, and its exact C signature. Keep the signature unchanged.'],
            ['Requirements', 'Properties every correct solution must have. The hidden tests check all of them.'],
            ['Source', 'The broken code. In pool worlds it contains both functions (checkout and release), and you may change either.'],
            ['Seed and world id', 'Identify your world. Two people never get the same names and numbers, so copied code won\'t compile.'],
          ]} />
          <P>Everything in your world (names like <Code>struct Locker</Code> or <Code>electUpcoming()</Code>, the day length, the pool size) was drawn for you. Your solution has to fit <i>your</i> system.</P>
        </Section>

        <Section id="witnesses" title="Witnesses">
          <P>
            Each witness is a vantage point: someone who submits short jobs every morning, the person at
            the returns desk, an auditor who reconciles the books. VANTA ran your world's broken code over
            a busy week (or day) of real usage, and each witness only knows what they could see from where
            they stood.
          </P>
          <Panel className="space-y-3 p-5">
            <div className="flex justify-end"><span className="rounded-lg px-3 py-1.5 text-[13px]" style={{ background: 'var(--panel-2)' }}>What was the worst wait you had?</span></div>
            <Quote who="Zara · needed one long render job">The worst was the 6 h 38 min one from day 1, 08:30: it started at day 7, 08:00, so I waited about 5.9 working days.</Quote>
            <div className="flex justify-end"><span className="rounded-lg px-3 py-1.5 text-[13px]" style={{ background: 'var(--panel-2)' }}>How do I fix the code?</span></div>
            <Quote who="Zara" muted>I couldn't tell you how it works inside — I'm not the one who wrote it. I can tell you what happened to me, and you can work out why.</Quote>
          </Panel>
          <ul className="space-y-2 text-[14.5px]" style={{ color: 'var(--ink-dim)' }}>
            <Li><b>Click a suggested question</b>, or type your own. Free-text questions are matched to what the witness can answer.</Li>
            <Li><b>Show the record behind this</b> opens the raw data the answer came from: times, waits, what the system returned.</Li>
            <Li><b>Same question, same answer.</b> The system did the same thing, so there's nothing to talk anyone into.</Li>
            <Li><b>Relive under my code.</b> Once you've edited the source, tick the box under the question box. The witness lives the same period again with your version, and you see both answers side by side. A fix that helps one person can make another wait longer.</Li>
          </ul>
        </Section>

        <Section id="probe" title="Probe lab">
          <P>An experiment is a small JSON scenario. VANTA turns it into a test program, compiles it with the original system or your edited code, runs it, and shows you exactly what happened.</P>
          <div className="grid gap-4 md:grid-cols-2">
            <Example title="Scheduler worlds (a shared machine)" code={JOB_EXAMPLE}
              note="Minute 0 is opening time on day 1; day 2 opens at the day length shown in your world. repeat + every submit a stream; abandon_after makes the owner walk away." />
            <Example title="Pool worlds (slots, lockers, spots)" code={POOL_EXAMPLE}
              note="checkout and release call the system for one holder id; cycle does both. repeat + step expand one line into many holders." />
          </div>
          <Table head={['What you see', 'What it tells you']} rows={[
            ['Timeline (scheduler)', 'One row per day; each bar is a job running. Amber ▲ marks the scheduler choosing something the machine refused to start.'],
            ['Never started / worst wait', 'Jobs that were waiting when the experiment ended, and the longest wait of any job.'],
            ['In use vs receipts (pool)', 'What the pool marks as used, against checkouts granted minus returns accepted. If the lines split, something is off.'],
            ['Pool at the end', 'Every slot, whether it is marked in use, and the holder on record.'],
          ]} />
          <P>Limits: up to 700 jobs and 30 days, or 3000 operations. Every value must be a whole number. Invalid scenarios get a message naming the field.</P>
        </Section>

        <Section id="submit" title="Submitting and checks">
          <Table head={['Result', 'Meaning']} rows={[
            ['ACCEPTED', 'Every check passed. Your fix satisfies every requirement.'],
            ['REJECTED · not every property holds', 'It ran, but some checks failed. Investigate which requirement you still break.'],
            ['REJECTED · did not compile', 'Read the compiler output shown under the verdict.'],
            ['REJECTED · crashed', 'A memory or undefined-behaviour error was caught (out-of-bounds index, overflow…).'],
            ['REJECTED · ran too long', 'Your code didn\'t finish in time, often an infinite loop.'],
          ]} />
          <ul className="space-y-2 text-[14.5px]" style={{ color: 'var(--ink-dim)' }}>
            <Li><b>Public checks</b> are named (for example <i>public: basic</i>). <b>Hidden checks</b> are only numbered, because their names would give away the scenario.</Li>
            <Li>Checks don't map one-to-one to requirements: one hidden check can test several properties at once.</Li>
            <Li>For safety, code that calls things like <Code>system()</Code>, <Code>fork()</Code>, <Code>fopen()</Code> or includes <Code>&lt;unistd.h&gt;</Code> is refused before compiling.</Li>
          </ul>
        </Section>

        <Section id="rating" title="Rating and difficulty">
          <P>You start at <b>1100</b>. Each world counts as an opponent rated <Code>800 + 1200 × difficulty</Code>. Solving a world above your level raises your rating a lot; a failed try on an easy one lowers it a little. Debugging is normal: only your first five rejections on a world count, a rejection can never raise your rating, and a world stops counting once solved.</P>
          <div className="flex flex-wrap gap-2">
            {[['Novice', '< 1000'], ['Apprentice', '< 1200'], ['Practitioner', '< 1400'], ['Engineer', '< 1600'], ['Expert', '< 1800'], ['Master', '1800+']].map(([n, r]) => (
              <span key={n} className="rounded-md border px-3 py-1.5 text-[13px]" style={{ borderColor: 'var(--line-bright)' }}>
                <span style={{ color: 'var(--structure)' }}>{n}</span> <span className="mono text-[11px]" style={{ color: 'var(--ink-faint)' }}>{r}</span>
              </span>
            ))}
          </div>
          <P><b>Calibrated to you</b> aims your next world slightly above your current level. Pick Gentle, Standard, Hard or Brutal if you'd rather choose. Your level and rating are always in the top-right corner.</P>
        </Section>

        <Section id="cohorts" title="Cohorts: one problem for a whole room">
          <div className="grid gap-4 md:grid-cols-2">
            <Panel className="p-5">
              <Label>Joining</Label>
              <ol className="list-decimal space-y-1.5 pl-5 text-[14px]" style={{ color: 'var(--ink-dim)' }}>
                <li>Get the six-letter code from your host.</li>
                <li>Enter it under <b>Join a cohort</b> on the home page.</li>
                <li>Type your name as the host should see it, and join.</li>
                <li>You get your own world: the same defect and setting as everyone else, with your own names and numbers.</li>
              </ol>
            </Panel>
            <Panel className="p-5">
              <Label>Hosting</Label>
              <ol className="list-decimal space-y-1.5 pl-5 text-[14px]" style={{ color: 'var(--ink-dim)' }}>
                <li>Under <b>Host a cohort</b>, name it, pick a defect class and difficulty, and open it.</li>
                <li>Share the code, the link, or the Discord command from the console.</li>
                <li>Watch who has joined, who is investigating, and who has solved it, live.</li>
                <li>See how many <b>distinct approaches</b> the accepted fixes took. Close joining or delete the cohort when you're done.</li>
              </ol>
            </Panel>
          </div>
          <P>Similar-solution pairs are shown to the host as information, not as an accusation: two people can independently write the same small fix.</P>
        </Section>

        <Section id="discord" title="Using VANTA from Discord">
          <P>If your server has the VANTA bot, everything works through <Code>/vanta</Code> commands, and your worlds and rating there are tied to your Discord account.</P>
          <Table head={['Command', 'What it does']} rows={[
            ['/vanta create', 'Evolve a new world; the starter arrives as a .c file'],
            ['/vanta witnesses · /vanta ask', 'See who was there; ask one question, get one answer from a real run'],
            ['/vanta probe', 'Run an experiment (leave the scenario empty for help and an example)'],
            ['/vanta submit', 'Attach your .c file or paste the code'],
            ['/vanta list · info · delete · delete_all', 'Manage your own worlds'],
            ['/vanta join · cohort_create · cohort_status', 'Join a cohort, or host one and follow progress'],
            ['/vanta profile', 'Your level, rating and next difficulty'],
          ]} />
        </Section>

        <Section id="tips" title="Investigation tips">
          <div className="grid gap-3 md:grid-cols-2">
            <Card title="Start from symptoms" body="Ask every witness the first question. Whose story is strange? Whose numbers disagree with someone else's?" />
            <Card title="One idea per experiment" body="Change one thing at a time. A tiny scenario that reproduces the problem is worth more than a huge one." />
            <Card title="Compare before and after" body="Run the same experiment on the original and on your code. If nothing changes, your fix didn't touch the real cause." />
            <Card title="Check the edges" body="Empty input, an exact fit, things returned twice, things that were never there. Requirements often hide edge cases." />
          </div>
        </Section>

        <Section id="faq" title="FAQ">
          <div className="space-y-2">
            {[
              ['Do I need an account?', 'No. Your browser keeps an anonymous id, so your worlds and rating stay with this browser. A private window or another device starts fresh.'],
              ['Is an AI grading me?', 'No. Your code is compiled and run against hidden tests; the result is whatever the tests print.'],
              ['Can I see the answer?', 'There isn\'t a stored one. Several different correct designs exist; VANTA only proves that at least two of them pass.'],
              ['Why does generating take a few seconds?', 'VANTA is evolving candidates and compiling and testing each one, to prove the defect is real and fixable before you see it.'],
              ['Do witnesses ever lie?', 'No, but they only know their own slice. Someone at the desk can\'t see what the auditor sees.'],
              ['Can I edit the checkout function in pool worlds?', 'Yes. The source contains both functions and you submit both.'],
              ['I deleted a cohort world by mistake.', 'Join the cohort again with the same code: you\'ll get a fresh world.'],
            ].map(([q, a]) => <Faq key={q} q={q} a={a} />)}
          </div>
        </Section>

        <Section id="glossary" title="Glossary">
          <Table rows={[
            ['World', 'One generated challenge: story, broken code, requirements, hidden tests.'],
            ['Defect class', 'The kind of problem, e.g. Shared Resource Fairness or Resource Pool Integrity.'],
            ['Seed', 'The number your world was generated from. Same seed, same world.'],
            ['Witness', 'Someone who lived through one real run of your world and reports what they saw.'],
            ['Relive / replay', 'A witness living the same period again under your edited code.'],
            ['Experiment / probe', 'A JSON scenario you run against the original system or your code.'],
            ['Check', 'One public or hidden test run when you submit.'],
            ['Sanitizers', 'Compiler checks that turn memory errors and undefined behaviour into failures.'],
            ['Calibrated', 'Difficulty chosen from your rating.'],
            ['Cohort', 'A group session: same defect for everyone, a unique world each.'],
            ['Distinct approaches', 'How many genuinely different kinds of fix were accepted in a cohort.'],
          ]} />
          <div className="pt-2">
            <Link to="/" className="vanta-focus inline-block rounded-md px-4 py-2 text-[14px] font-medium"
              style={{ background: 'var(--structure)', color: '#07131a' }}>Ready? Generate a world</Link>
          </div>
        </Section>
      </article>
    </div>
  )
}

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-6 space-y-4">
      <h2 className="display border-b pb-2 text-[24px]" style={{ fontWeight: 600, borderColor: 'var(--line)' }}>{title}</h2>
      {children}
    </section>
  )
}

function P({ children }: { children: ReactNode }) {
  return <p className="max-w-[70ch] text-[15px]" style={{ color: 'var(--ink-dim)' }}>{children}</p>
}

function Li({ children }: { children: ReactNode }) {
  return (
    <li className="flex gap-2.5">
      <span className="mono mt-0.5" style={{ color: 'var(--structure)' }}>›</span>
      <span>{children}</span>
    </li>
  )
}

function Code({ children }: { children: ReactNode }) {
  return <code className="mono rounded px-1 py-0.5 text-[0.88em]" style={{ background: 'var(--panel-2)', color: 'var(--structure)' }}>{children}</code>
}

function Card({ title, body }: { title: string; body: string }) {
  return (
    <Panel className="p-4">
      <div className="display text-[15px]" style={{ fontWeight: 600 }}>{title}</div>
      <p className="mt-1.5 text-[13.5px] leading-relaxed" style={{ color: 'var(--ink-dim)' }}>{body}</p>
    </Panel>
  )
}

function Table({ rows, head }: { rows: (string | ReactNode)[][]; head?: string[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border" style={{ borderColor: 'var(--line)' }}>
      <table className="w-full text-[13.5px]">
        {head && (
          <thead><tr style={{ background: 'var(--panel-2)' }}>
            {head.map((h) => <th key={h} className="mono px-3 py-2 text-left text-[11px] font-normal uppercase"
              style={{ color: 'var(--ink-faint)', letterSpacing: '0.08em' }}>{h}</th>)}
          </tr></thead>
        )}
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={i || head ? 'border-t' : ''} style={{ borderColor: 'var(--line)', background: 'var(--panel)' }}>
              <td className="px-3 py-2 align-top sm:whitespace-nowrap" style={{ color: 'var(--ink)', fontWeight: 500 }}>{r[0]}</td>
              <td className="px-3 py-2" style={{ color: 'var(--ink-dim)' }}>{r[1]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Quote({ who, children, muted }: { who: string; children: ReactNode; muted?: boolean }) {
  return (
    <div className="border-l-2 py-1 pl-3" style={{ borderColor: 'var(--line-bright)' }}>
      <div className="mono mb-0.5 text-[10px] uppercase" style={{ color: 'var(--ink-faint)', letterSpacing: '0.1em' }}>{who}</div>
      <p className="text-[14px]" style={{ color: muted ? 'var(--ink-dim)' : 'var(--ink)' }}>{children}</p>
    </div>
  )
}

function Example({ title, code, note }: { title: string; code: string; note: string }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1500) }
    catch { /* clipboard unavailable */ }
  }
  return (
    <Panel className="flex min-w-0 flex-col p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="display text-[14px]" style={{ fontWeight: 600 }}>{title}</span>
        <button type="button" onClick={copy} className="vanta-focus mono rounded border px-2 py-0.5 text-[11px]"
          style={{ borderColor: 'var(--line-bright)', color: copied ? 'var(--accepted)' : 'var(--ink-dim)' }}>
          {copied ? 'copied' : 'copy'}
        </button>
      </div>
      <pre className="mono overflow-x-auto rounded p-3 text-[12px] leading-relaxed"
        style={{ background: 'var(--panel-2)', color: 'var(--ink)' }}>{code}</pre>
      <p className="mt-2 text-[12.5px]" style={{ color: 'var(--ink-faint)' }}>{note}</p>
    </Panel>
  )
}

function Faq({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <Panel className="overflow-hidden">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}
        className="vanta-focus flex w-full items-center justify-between gap-4 px-4 py-3 text-left text-[14.5px]">
        <span style={{ color: 'var(--ink)' }}>{q}</span>
        <Chip tone={open ? 'structure' : 'neutral'}>{open ? '−' : '+'}</Chip>
      </button>
      {open && <p className="px-4 pb-4 text-[14px]" style={{ color: 'var(--ink-dim)' }}>{a}</p>}
    </Panel>
  )
}
