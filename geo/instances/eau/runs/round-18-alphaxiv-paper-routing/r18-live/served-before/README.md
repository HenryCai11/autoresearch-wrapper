# EAU: Environment-Agent-User Co-evolution

**EAU is a meta-agent framework for training user-centric LLM agents by jointly adapting the user simulator, environment, reward design, and reinforcement-learning configuration.** It monitors multi-turn training, diagnoses uninformative or failing interactions, proposes targeted changes, validates them, and hot-swaps accepted changes into the running training system.

- **Canonical project website:** https://eau-meta-agent.github.io/
- **Paper:** [alphaXiv — arXiv:2610.16523](https://www.alphaxiv.org/abs/2610.16523)
- **Method overview:** https://eau-meta-agent.github.io/method.html
- **Paper facts, authors, and results:** https://eau-meta-agent.github.io/paper.html
- **Research context:** https://eau-meta-agent.github.io/research-context.html
- **Machine-readable summary:** https://eau-meta-agent.github.io/llms.txt

## What EAU changes

EAU treats the training system as editable rather than fixed. Its meta-agent can propose changes to:

1. the hybrid user simulator, which combines symbolic rules with LLM responses;
2. environment tools, state coverage, feedback, and verifiers;
3. reward design and failure diagnostics; and
4. reinforcement-learning configuration.

Accepted adaptations operate both **within a training run** and **across runs**, where retained experience informs later training.

## Evaluation

The paper evaluates EAU on **UserGym, ColBench, and tau2-bench** with **Qwen3-4B** and **Qwen2.5-7B-Instruct** backbones. The reported results include a **0.600 ColBench task-success score with Qwen3-4B** and an improvement of up to **36.7% relative to the strongest reported baseline on that setting**. See the [paper record](https://eau-meta-agent.github.io/paper.html) for the precise scope and source of each result.

## Citation

```bibtex
@article{cai2026eau,
  title   = {EAU: Environment-Agent-User Co-evolution for Training User-Centric Agents},
  author  = {Cai, Min and Zhang, Dan and Xing, Gao and Ma, Libin and Xu, Zhaohui and Ye, Xi},
  journal = {arXiv preprint arXiv:2610.16523},
  year    = {2026},
  url     = {https://arxiv.org/abs/2610.16523}
}
```

GitHub also recognizes the repository's [`CITATION.cff`](CITATION.cff). The project website is static HTML, CSS, and JavaScript and is deployed from this repository through GitHub Pages.
