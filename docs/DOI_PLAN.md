# DOI minting plan — PUBLISHED; DOI pending one Zenodo toggle

This library is published, mirroring the sibling `finserv-agent-audit` (concept
DOI 10.5281/zenodo.20434570) and `cre-agent-audit` (10.5281/zenodo.20434575).
Owner authorized publication 2026-06-05 after a genuine council 10/10.

## Done

- [x] 0.1.0 built to the corrected primitive standard; CI green (locally **and**
      on GitHub: CI · OSV · Bandit · gitleaks · CodeQL all pass).
- [x] Council 10/10 on README/CITATION/obligation docs (recorded); `publish-check` clean.
- [x] **Public repo created + pushed:** <https://github.com/linus10x/banking-agent-audit>.
- [x] **Tag `v0.1.0` pushed + GitHub Release published.**
- [x] Factual-only reg content (no `pending_counsel` positioning rendered), so no
      counsel-read gate blocks publication.

## Remaining — the ONE Zenodo step (needs the owner's Zenodo login)

The DOI did **not** auto-mint: this brand-new repo had no Zenodo webhook at
release time (Zenodo only mints for releases created *after* the repo is enabled).
To mint:

1. At <https://zenodo.org/account/settings/github/> (logged in as the account
   that holds the finserv/cre DOIs), toggle **`linus10x/banking-agent-audit` ON**.
2. Re-publish the release so Zenodo's webhook fires: either delete + recreate the
   `v0.1.0` GitHub Release, or cut `v0.1.1`. Zenodo then mints a version DOI + a
   concept DOI.
3. Put the concept DOI in `CITATION.cff` (`doi:`) and back into this file; commit.
4. Flip Banking `cross-applied → backed` in the funnel (via the SHIPPED note → S2).

## SemVer discipline

- 0.1.0 is the first public-candidate. A default/observable-contract change
  (e.g. flipping the advisory default to enforcing) is a MAJOR bump.
- Never re-tag a DOI'd version; bump from the live tag.
