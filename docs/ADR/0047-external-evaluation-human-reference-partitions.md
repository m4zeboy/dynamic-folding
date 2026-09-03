# ADR 0047: External evaluation against human reference partitions

Date: 2026-09-02

## Status

Accepted. Amends ADR 0018's rejection of ARI/NMI-style metrics and supersedes
that rejection only for the three explicitly labeled, frozen corpora.

## Context

ADR 0018 correctly noted that an organization made by one human is not a
universal, objective ground truth.  The advisor has now requested an explicit
external evaluation after human reference labels were created for all three
corpora.  The relevant question is therefore bounded: how closely does the
tool's proposed top-level organization agree with that human reference for the
same corpus and fixed configuration?

The human references are flat partitions. The proposal is hierarchical and can
place files in `Outros`, so both comparison choices must be explicit rather
than hidden inside a metric implementation.

## Decision

- Add `dynamic-folding external-eval <corpus> --labels <csv> --config <toml>`.
  It runs the normal pipeline once, then compares the result to a complete
  two-column UTF-8, semicolon-separated reference-label CSV.
- The comparison flattens the proposal at its **top-level folders**. Files in
  nested folders inherit their top-level parent label.
- Every scanned file is required to have exactly one reference label. `Outros`
  and proposal orphans remain a predicted `Outros` class; no file is excluded
  to improve a score.
- Report ARI, NMI and AMI (also called ANMI in the advisor guidance). NMI and
  AMI use the arithmetic entropy average; ARI and AMI adjust for chance.
- Report one result per corpus. Do not pool documents or select a configuration
  by the external scores. JSON records the effective configuration and version;
  CSV is a flat, one-row corpus summary.
- Interpret the result as adherence to this human reference partition, not as
  correctness or utility for every possible user. Internal characterization
  and the perceived-utility protocol remain independent evidence.

## Consequences

- The thesis can answer the advisor's new adherence question with reproducible
  measurements while preserving the subjectivity caveat that motivated ADR
  0018.
- A label export with missing, extra, duplicate, or empty paths fails before
  scoring, so a metric never silently compares different file sets.
- The three metrics are complementary. ARI compares pair co-membership; NMI
  measures normalized information shared by the partitions; AMI removes the
  information expected by chance. No metric alone is treated as a percentage
  of correctness.

## References

- [ADR 0018](0018-empirical-characterization-no-ground-truth.md)
- [scikit-learn clustering performance evaluation](https://scikit-learn.org/stable/modules/clustering.html#clustering-performance-evaluation)
