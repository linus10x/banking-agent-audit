# DOI minting plan — COMPLETE (DOI-archived on Zenodo)

This library is published and DOI-archived, alongside the sibling vertical
libraries. Owner authorized publication 2026-06-05 after a genuine council 10/10;
DOI minted 2026-06-06.

## Done

- [x] Built to the corrected primitive standard; CI green on GitHub
      (CI · OSV · Bandit · gitleaks · CodeQL).
- [x] Council 10/10 on README/CITATION/obligation docs (recorded); `publish-check` clean.
- [x] **Public repo created + pushed:** <https://github.com/linus10x/banking-agent-audit>.
- [x] Post-publication fact-check (FCRA §615(a) citations corrected, legal
      disclaimer added) + clean single-commit history.
- [x] **Zenodo enabled + `v0.1.1` archival release cut** (adds `.zenodo.json` so the
      record does not depend on the dual-licensed `CITATION.cff`).
- [x] **DOI minted:** concept **10.5281/zenodo.20564584** (resolves to latest) ·
      v0.1.1 version DOI **10.5281/zenodo.20564585** · badge `zenodo.org/badge/1260859533.svg`.
- [x] Concept DOI backfilled into `CITATION.cff`, README badge, and the internal
      IP-catalog SSOTs (FACTS.md, CLAUDE.md, NTCI catalog).

## Remaining

- [ ] Flip Banking `cross-applied → backed` in the funnel (now unblocked — public +
      DOI-archived). Actioned this session in `~/autonomy-ladder-platform-clone`.

## SemVer discipline

- 0.1.0 is the first public-candidate. A default/observable-contract change
  (e.g. flipping the advisory default to enforcing) is a MAJOR bump.
- Never re-tag a DOI'd version; bump from the live tag.
