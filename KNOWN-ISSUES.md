# Verification and known limitations

**Security update:** Supporting dependency pins, the local viewer launcher, and evaluation error classification were updated after the live runs described below. Those historical live results do not constitute a new live test of this archive. The security update is verified with fresh installations, offline SDK checks, recorded-result replay, and local viewer tests. Models, scoring criteria, reference datasets, and unfinished exercises are preserved.

On 2026-09-01, completed-starter and reference baselines, all three 18-row variants, and both 18-row evaluations ran against the live `openai/gpt-oss-20b` model without runtime or grader errors. Both evaluations passed 7/18 overall; this is an observed outcome, not a required score. Instrumented live tests rejected off-topic and injection inputs with zero tools or handoffs in both implementations; accepted payment questions exercised the tool path. Separate offline SDK tests verified both tool and handoff ordering with accepted controls. The bundle preserves the exercise and existing references.

- One external course lookup harness uses Terra while the repository uses `openai/gpt-oss-20b`. Source model choices are retained. Task 4 now explicitly keeps Luna.
- The approved blocking guardrail correction requires the four dependency updates documented in the root README. A rejected input cannot reach the entry agent's tools or handoffs; model classification itself is probabilistic.
- Several guide harnesses exercise reference tools and do not verify learner files. The reference baseline has optional session memory and a different helper signature. Reference prompts mention `faq_specialist` and older complaint/contact tool names that differ from registered names. These pre-existing differences remain for course-owner reconciliation.
- Reference order validation strips whitespace for checking but then looks up the original string; surrounding whitespace can produce “not found.” Missing `args['order_id']` can raise `KeyError` at the Python level. These mock workflows do not implement production business authorization.
- The runner has a four-turn limit and catches runtime exceptions into `[ERROR]` rows. A zero exit code or saved file alone is not proof of success. Its trace label still says “Agents Challenge” although this is the guided lab.

All starter TODOs remain. Generated answers, evaluation histories, credentials, prior resource IDs, and unrelated labs are excluded. Windows and Linux instructions were reviewed, not runtime-tested on those systems. The verification host was macOS with Python 3.13.0 and Node 24.19.0; Python 3.12 was not executed.

The standard [MIT license](LICENSE) was added at the packaging requester’s direction; original source attribution is retained in [ATTRIBUTION.md](ATTRIBUTION.md).
