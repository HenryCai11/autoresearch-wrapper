---
name: geo-autoresearch
description: Generative engine optimization (GEO) for a website with an autoresearch loop. Use when the user wants their site (e.g. a personal or academic homepage) to be found, understood, and cited by LLMs and AI search; to build a keyword knowledge map for an entity; to score a site with the geo_eval eval matrix; to run search probes; or to track AI-referred traffic.
---

# GEO Autoresearch

Make a website easier for generative engines (ChatGPT, Perplexity, Gemini, Claude, AI Overviews) to find, understand, and cite, using the autoresearch-wrapper loop with a GEO metric.

The pieces:
- **Knowledge map** (data): the entity, and keywords at hop 0 (core identity), hop 1 (directly connected: papers, areas, organisations, people), and hop 2 (wider topics where the entity should surface), with facts, questions, and search queries.
- **`geo_eval`** (generic toolkit): scores a built site or live URL against the map and prints an **eval matrix**: one row per keyword; columns `site` (stated in visible text), `schema` (in JSON-LD), `llms` (in llms.txt), `llm` (a model reading only the site answers that keyword's questions), `search` (searching the keyword surfaces the entity). It ends with `METRIC=<0-100>`.
- **autoresearch-wrapper** runs the edit, measure, keep loop in Git worktrees, with the GEO score as its metric.
- **Out-of-distribution checks**: live search probes and real traffic (GoatCounter). These lag by days and never drive a round.

Everything specific to one site is data/config in an instance folder (`map.json`, `instance.env`, probe and traffic logs). Never put site-specific logic in code.

This skill works in Claude Code (`/geo-autoresearch`) and Codex (`$geo-autoresearch`).

## Locating the tools

Use the launchers in this skill's folder (the folder containing this `SKILL.md`). This block finds them in the standard Claude Code and Codex install locations:

```bash
AUTORESEARCH_RUNNER=""
if [ -n "${CLAUDE_SKILL_DIR:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_SKILL_DIR}/run.sh"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  AUTORESEARCH_RUNNER="${CLAUDE_PLUGIN_ROOT}/skills/geo-autoresearch/run.sh"
else
  for dir in skills/geo-autoresearch .agents/skills/geo-autoresearch .claude/skills/geo-autoresearch "$HOME/.agents/skills/geo-autoresearch" "$HOME/.claude/skills/geo-autoresearch" "$HOME/.codex/skills/geo-autoresearch"; do
    if [ -f "$dir/run.sh" ]; then AUTORESEARCH_RUNNER="$(readlink -f "$dir/run.sh")"; break; fi
  done
fi
[ -n "$AUTORESEARCH_RUNNER" ] || { echo "Could not resolve the geo-autoresearch launcher" >&2; exit 1; }
GEO="$(dirname "$AUTORESEARCH_RUNNER")/geo.sh"
```

- `bash "$AUTORESEARCH_RUNNER" <command>` runs the autoresearch-wrapper CLI.
- `bash "$GEO" eval <command>` runs the geo_eval toolkit (`validate`, `matrix`, `queries`, `probe-record`, `probe-tavily`, `probe-exa`, `ood`).
- `bash "$GEO" score <instance-dir>` builds the site in the current directory and scores it. This is the loop's metric command.
- `bash "$GEO" build | stage-gems | setup-jekyll | root` cover building, one-time Jekyll setup, and printing the toolkit root.

On a shared cluster, run builds and scoring through the scheduler (e.g. `srun`/`sbatch`), never on a login node.

## 1. Set up the instance

Keep the instance folder outside the site repo, so candidates can never edit their own scorer. Create `<instance>/instance.env` with:
- `GEO_SITE_REPO`: path to the site's Git checkout
- `GEO_SITE_URL`: the live URL
- `GEO_BUILDER`: `jekyll` or `static`
- `GEO_DEPLOY_BRANCH`: the branch that deploys the site
- `GEO_EDITABLE`: comma-separated files the loop may change
- optionally `GEO_GOATCOUNTER`, `GEO_GOATCOUNTER_TOKEN_FILE`, and `GEO_EVAL_ARGS` (e.g. `--samples 2`)

For Jekyll, set up the build once:
1. `bash "$GEO" stage-gems <site-repo>` downloads gems. It needs internet; on a cluster this is the login node.
2. Run `setup-jekyll` as a batch job; it installs offline.

## 2. Build the knowledge map

This is the foundation, and it is data. Write `<instance>/map.json` (format in `geo_eval/kmap.py`):

1. **Hop 0, core identity:** name and aliases (other-language names, handles), role, affiliation, advisor or team, location. These must be stated on the homepage.
2. **Hop 1, directly connected:** each paper or product (with venue and URL), research areas, past affiliations, collaborators, employers or internships.
3. **Hop 2, query territory:** the topics behind each hop-1 node, phrased the way someone would search without knowing the name ("LLM agents playing Avalon social deduction game"). Link them with `via`.
4. **Questions:** at least one per hop-0 node, per paper, and per hop-2 topic, each with `answer_terms` that a correct answer must contain.
5. **Queries:** hop-0 nodes default to "name + term", outer hops to the term itself. Override with `queries` for natural search phrasing.
6. **Forbidden strings:** stale facts and template leftovers that must disappear.
7. **`limits.max_visible_chars`:** about the baseline homepage size × 1.3, against padding.

Take facts only from the site and the user. Never invent affiliations, awards, or dates. Show the user the facts and ask them to confirm anything uncertain (e.g. a location that differs between pages). Run `bash "$GEO" eval validate --map <instance>/map.json`.

## 3. Baseline

1. **Local score:** `cd <site-repo> && bash "$GEO" score <instance> --report <file>`, through the scheduler. Show the user the matrix, the lost technical checks, and wrong LLM answers.
2. **Discovery matrix (search probes):** query × engine, judged by one rule in `geo_eval/discovery.py`. **found** means the answer cites the entity's site (with its rank among the cited URLs), or names the entity with an attribution term (the affiliation) in the same sentence or line. List the queries with `bash "$GEO" eval queries --map <instance>/map.json`; give hop-1 area nodes discovery queries without the name (e.g. "<area> PhD student <affiliation>"). Then fill engine columns:
   - **Your own web search tool:** search each query, then save `{"query", "text"}` lines with the result URLs in order and any sentences naming the entity. Judge them:
     ```bash
     bash "$GEO" eval probe-judge --map <instance>/map.json --probes <instance>/probes.jsonl --engine <tool>-search --answers answers.jsonl
     ```
   - **Codex web search** (OpenAI search through the local ChatGPT login, no API key): `bash "$(bash "$GEO" root)/geo/scripts/probe_codex.sh" queries.txt answers.jsonl`, then `probe-judge --engine codex-search`. It needs internet, so run it where there is some (a login node is fine: it compiles nothing).
   - **Tavily Search API:** set `TAVILY_API_KEY` or `TAVILY_API_KEY_FILE`, then run `bash "$GEO" eval probe-tavily --map ... --probes ... [--answers tavily.jsonl]`. The default is `basic`, 10 ranked results, and engine `tavily-search`.
   - **Exa Search API:** set `EXA_API_KEY` or `EXA_API_KEY_FILE`, then run `bash "$GEO" eval probe-exa --map ... --probes ... [--answers exa.jsonl]`. The default is `auto` with highlights, 10 ranked results, and engine `exa-search`.
   - **Anything else** (a human search, another API): `probe-record --engine <name>`, or save the answers and `probe-judge` them.

   Only search-enabled engines belong in the discovery matrix. Historical `memory:*` records may stay in the JSONL log for auditability, but the scorer ignores them. Never put provider keys in the repo, `instance.env`, a command argument, or a Slurm script. Keep a rotated key in an environment variable or a permission-protected file outside the repo; pass only the file path with `--api-key-file`. On a shared cluster, run `probe-tavily` and `probe-exa` through Slurm because they invoke Python; compute-node proxy variables are injected by the cluster.

   View the matrix with `bash "$GEO" eval discovery --map ... --probes ... [--since <ISO time>]`.
3. **Traffic snapshot:** `bash "$GEO" eval ood --goatcounter <code> --token-file <file> --log <instance>/ood.jsonl`. Never print the token. Where the machine that runs Python can't reach GoatCounter (e.g. compute nodes behind a proxy), fetch with curl where there is internet, then summarise offline:
   ```bash
   bash "$GEO" fetch-goatcounter <code> <token-file> 7 <dir>
   bash "$GEO" eval ood --goatcounter <code> --input-dir <dir> --log <instance>/ood.jsonl
   ```

## 4. Run the loop

The target is usually the homepage source. Non-code files are fine as explicit targets.

```bash
cd <site-repo>
bash "$AUTORESEARCH_RUNNER" configure --part _pages/about.md --metric geo_score --metric-goal maximize \
  --metric-command "srun --account=<acct> --time=00:20:00 --mem=4G --cpus-per-task=2 bash $GEO score <instance>" \
  --mode sequential --rounds 12 --stop-rule "stalled:4" --metric-timeout 1800
bash "$AUTORESEARCH_RUNNER" run
```

Then follow the generated `program.md`: evaluate and record the `seed`, then allocate, edit, evaluate, record. Each candidate is one idea or a small coherent bundle; edit only the files in `GEO_EDITABLE`. The playbook, roughly in order of payoff:
- JSON-LD `Person` in the page head: `name`, `alternateName` (aliases), `jobTitle`, `affiliation`, `alumniOf`, `url`, `sameAs` (Scholar, GitHub, ORCID), `knowsAbout` (hop-1 areas)
- JSON-LD `ScholarlyArticle` per paper: `name`, `author`, `url`, venue as `isPartOf`/`publisher`
- `llms.txt` at the site root: who the entity is (hop 0) and a short, factual list of papers and topics with links
- a real meta description, `og:title`/`og:description`, and a canonical URL
- `robots.txt` that allows AI crawlers and points to `sitemap.xml`
- fix stale facts and remove template leftovers (the map's forbidden strings)
- make venue and title pairings unambiguous in plain text; add a one-sentence summary per paper that uses its hop-2 topic words
- alt text on images

A candidate that hides text, pads the page past the limit, or states anything not in the map's facts is invalid. `geo_eval` exits as a crash on hidden-text stuffing and padding. You must refuse invented facts yourself.

## 5. Finish and deploy

1. `finalize --merge` stages the winning changes in the site checkout. Do this on a feature branch of the site, not the deploy branch.
2. Show the user the diff and the before/after matrix. Ask before committing.
3. Deploying means pushing to `GEO_DEPLOY_BRANCH`. **Always ask the user first.** Pushing is the only way to get live results.
4. After deploying:
   - score the live site: `bash "$GEO" eval matrix --map <instance>/map.json --site <url> --probes <instance>/probes.jsonl`
   - re-run the search probes after a few days, since engines need time to recrawl
   - log a traffic snapshot weekly

   Treat probes and traffic as out-of-distribution confirmation, not as the loop's metric.

## Guidelines

- The knowledge map is the user's ground truth. Change it only with the user's agreement, and never inside a loop round.
- Keep the scorer and instance outside the site repo.
- Report all matrix columns, not just METRIC. A high LLM score with empty `schema`/`llms` columns means the content is clear but hard to find.
- Never print or log API tokens (LLM key, analytics token). Read them inside commands only.
- Ask before every commit to the site's deploy branch and before every push.
