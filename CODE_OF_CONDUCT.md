# Contributor Covenant Code of Conduct

## Our Pledge

We as members, contributors, and leaders of the **ASTRA — Automated Stellar
Transient Recognition & Analysis** project pledge to make participation in our
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic status,
nationality, personal appearance, race, caste, colour, religion, or sexual
identity and orientation.

We pledge to act and interact in ways that contribute to an open, welcoming,
diverse, inclusive, and healthy community — and, as a scientific ML project, to
maintain rigorous standards of data integrity, reproducibility, and honest
communication of results.

---

## Our Standards

### Examples of behaviour that contributes to a positive environment

- Using welcoming and inclusive language in code review, issues, and discussions
- Being respectful of differing viewpoints, scientific approaches, and experience
  levels — from domain astronomers to ML engineers
- Giving and gracefully accepting constructive feedback
- Accepting responsibility and apologising when we have made mistakes, and
  learning from the experience
- Focusing on what is best for the community and the scientific integrity of
  the project
- **Accurately attributing data sources:** Always citing the VSX catalog, MAST
  data products, peer-reviewed publications, or SIMBAD records that underpin
  any scientific claim
- **Reporting results honestly:** Never overstating model performance, omitting
  confidence intervals, or cherry-picking evaluation sets; all metrics must be
  traceable to artifacts in `models/saved/`
- **Maintaining dataset provenance:** Preserving and documenting the chain of
  custody for every TIC ID added to the catalog, consistent with the audit
  reports (`ground_truth_*.md`, `phase6_*.md`, `phase7_*.md`)

### Examples of unacceptable behaviour

- The use of sexualised language or imagery, and sexual attention or advances
  of any kind
- Trolling, insulting or derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information, such as a physical or email address,
  without their explicit permission
- **Scientific misconduct:** Fabricating, falsifying, or selectively omitting
  data; misrepresenting model accuracy or dataset composition; adding unverified
  TIC IDs to the catalog without MAST confirmation; introducing SHA-256 hashes
  that do not match the actual checkpoint files
- **Hallucinated citations:** Citing non-existent papers, VSX entries, or MAST
  records to justify a contribution
- Other conduct which could reasonably be considered inappropriate in a
  professional or scientific research setting

---

## Scientific Data Integrity

ASTRA classifies real astronomical objects observed by the TESS mission. Because
our outputs have potential downstream use in professional and citizen-science
astronomy, data integrity is a first-class community value — not merely a
technical requirement.

All contributors agree to:

1. **Source every label:** Each stellar class assignment must trace to at least
   one of: a VSX variable type, a SIMBAD classification, a published asteroseismic
   catalog, or a documented pipeline decision in the ASTRA audit trail.
2. **Never fabricate metrics:** Performance figures (accuracy, F1, ECE) must
   correspond to real evaluation runs whose artifacts exist in `models/saved/`.
   Reporting results from a run that cannot be reproduced or whose checkpoint
   has been lost is a violation of this Code.
3. **Preserve reproducibility:** Training seeds (`seed: 42`), dataset fingerprint
   hashes, and split hashes recorded in `experiment_metadata.json` must not be
   altered retroactively. If a bug invalidates prior results, the correct action
   is to document the issue and rerun — not to silently update metadata.
4. **Disclose AI assistance:** If a contribution was generated in whole or in
   part by an AI coding assistant, the PR description must say so. The human
   submitter remains personally responsible for the scientific accuracy of every
   claim in the contribution.

---

## Enforcement Responsibilities

Community leaders are responsible for clarifying and enforcing our standards of
acceptable behaviour and will take appropriate and fair corrective action in
response to any behaviour that they deem inappropriate, threatening, offensive,
or harmful.

Community leaders have the right and responsibility to remove, edit, or reject
comments, commits, code, wiki edits, issues, and other contributions that are
not aligned to this Code of Conduct, and will communicate reasons for moderation
decisions when appropriate.

---

## Scope

This Code of Conduct applies within all community spaces, and also applies when
an individual is officially representing the community in public spaces.
Examples of representing our community include using an official email address,
posting via an official social media account, or acting as an appointed
representative at an online or offline event.

---

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behaviour — including
scientific misconduct — may be reported to the community leaders responsible for
enforcement. All complaints will be reviewed and investigated promptly and fairly.

All community leaders are obligated to respect the privacy and security of the
reporter of any incident.

---

## Enforcement Guidelines

Community leaders will follow these Community Impact Guidelines in determining
the consequences for any action they deem in violation of this Code of Conduct:

### 1. Correction

**Community Impact:** Use of inappropriate language or other behaviour deemed
unprofessional or unwelcome in the community, or a minor unintentional data
integrity lapse (e.g., a typo in a hash that was not caught before merging).

**Consequence:** A private, written warning from community leaders, providing
clarity around the nature of the violation and an explanation of why the
behaviour was inappropriate. A public apology may be requested. The contribution
will be corrected or reverted.

### 2. Warning

**Community Impact:** A violation through a single incident or series of
actions, including introducing unverified labels or metrics that were merged
before review could catch them.

**Consequence:** A warning with consequences for continued behaviour. No
interaction with the people involved, including unsolicited interaction with
those enforcing the Code of Conduct, for a specified period of time. This
includes avoiding interactions in community spaces as well as external channels
like social media. Violating these terms may lead to a temporary or permanent
ban.

### 3. Temporary Ban

**Community Impact:** A serious violation of community standards, including
sustained inappropriate behaviour, repeated scientific misconduct, or knowingly
introducing fabricated data or metrics.

**Consequence:** A temporary ban from any sort of interaction or public
communication with the community for a specified period of time. No public or
private interaction with the people involved, including unsolicited interaction
with those enforcing the Code of Conduct, is allowed during this period.
Violating these terms may lead to a permanent ban.

### 4. Permanent Ban

**Community Impact:** Demonstrating a pattern of violation of community
standards, including sustained inappropriate behaviour, harassment of an
individual, or deliberate and repeated scientific fraud — for example,
systematically introducing false TIC IDs, fabricating evaluation results, or
knowingly corrupting the dataset audit trail.

**Consequence:** A permanent ban from any sort of public interaction within the
community.

---

## Attribution

This Code of Conduct is adapted from the
[Contributor Covenant](https://www.contributor-covenant.org), version 2.1,
available at
https://www.contributor-covenant.org/version/2/1/code_of_conduct.html.

Community Impact Guidelines were inspired by
[Mozilla's code of conduct enforcement ladder](https://github.com/mozilla/diversity).

For answers to common questions about this code of conduct, see the FAQ at
https://www.contributor-covenant.org/faq. Translations are available at
https://www.contributor-covenant.org/translations.
