# Reddit Comment Annotation Tool

A web-based annotation interface for computational communication research, built with Streamlit.

Developed as part of a graduate thesis studying **how subreddit community rules affect deliberative quality** in online political discussions across 8 Reddit communities (r/climate, r/geopolitics, r/worldnews, r/Economics, r/science, r/technology, r/politics, r/energy).

---

## Key Features

**Dual-mode operation**
- Training mode: annotators code sample comments and receive immediate feedback against reference answers, with per-dimension accuracy tracking
- Production mode: full annotation workflow with auto-resume — pick up exactly where you left off

**Inline codebook** — no context switching
- Each coding dimension has a collapsible definition panel directly beside the input
- Eliminates the back-and-forth between annotation interface and codebook document (a known pain point in tools like Dıvominer)

**Four deliberative quality dimensions** based on Stolwijk et al. (2025)
- Interactivity — whether the comment engages with others' views
- Diversity — ideological direction (liberal / conservative, two independent dummies)
- Rationality — presence of reasoning, evidence, or background analysis
- Incivility — presence of any of 9 uncivil elements (reverse-coded)

**Built-in inter-rater reliability**
- Calculates Cohen's κ and percent agreement per dimension
- Displays disagreements between annotators for discussion
- Exports uncertain cases as a CSV for calibration sessions

**Time tracking and compensation logging**
- Records time spent per comment (capped at 5 minutes to avoid idle inflation)
- Generates per-annotator work logs for hourly compensation calculation
- Session timer displayed in the interface

**Negative-score comment flagging**
- Comments with score < 0 are visually flagged to alert annotators to check the incivility dimension — a sampling design choice to preserve low-civility cases often filtered out by score thresholds

---

## Deliberative Quality Framework

| Dimension | Coding | Key criterion |
|-----------|--------|---------------|
| Interactivity | 1 / 0 / – | Does the comment explicitly respond to another's argument? |
| Diversity (liberal) | 1 / 0 | Does it express a liberal/Democrat ideological direction? |
| Diversity (conservative) | 1 / 0 | Does it express a conservative/Republican ideological direction? |
| Rationality | 1 / 0 / – | Does it contain reasoning, evidence, or background analysis? |
| Incivility | 1 / 0 / – | Does it contain any of 9 uncivil elements? (1 = uncivil) |

Codebook design based on: Stolwijk et al. (2025), Freelon (2015), Rossini (2022), Rowe (2015), Ziegele et al. (2020), Papacharissi (2004).

---

## Data Format

**Input CSV** (`sample_for_coding.csv`):
```
comment_id, subreddit, body, score, created_utc
```

**Output CSV** (`annotations.csv`):
```
comment_id, subreddit, body, score,
interactivity, is_liberal, is_conservative, rationality, incivility,
is_uncertain, note, annotator_id, timestamp, time_spent_seconds
```

**Training CSV** (`training_sample.csv`): same as input, plus reference answer columns.

---

## Usage

```bash
pip install streamlit pandas scikit-learn
streamlit run annotator.py
```

On launch, enter your name and select a mode. The tool auto-detects existing annotation progress and resumes from where you left off.

---

## Research Context

This tool was built to support a master's thesis in journalism studies examining deliberative quality in Reddit political discussions. The study uses:

- **Data**: ~5 million comments from 8 subreddits collected via Arctic Shift API and Reddit PRAW (2015–2024)
- **Sampling**: stratified by community and time period, with oversampling of negative-score comments for the incivility dimension
- **Annotation**: manual coding of ~3,000 comments by two independent coders, followed by BERT fine-tuning for full-corpus classification
- **Analysis**: regression models examining the effect of community rule characteristics on deliberative quality

---

## References

Stolwijk, S. B., Boukes, M., Yeung, W. N., Liao, Y., Münker, S., Kroon, A. C., & Trilling, D. (2025). Can we use automated approaches to measure the quality of online political discussion? *Communication Methods and Measures*.

Freelon, D. (2015). Discourse architecture, ideology, and democratic norms in online political discussion. *New Media & Society, 17*(5), 772–791.

Rossini, P. (2022). Beyond incivility: Understanding patterns of uncivil and intolerant discourse in online political talk. *Communication Research, 49*(3), 399–425.
