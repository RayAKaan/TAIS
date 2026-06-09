# PAPER SUBMISSION CHECKLIST

## Metadata
- [x] Commit hash: `f56b4fd` (post-R6, main)
- [x] Test baseline: 305 passing
- [x] Date: 2026-06-09
- [ ] Authors: TBD (anonymous for submission)
- [ ] Venue: TBD

## Experimental Record
- [x] All 27 experimental conditions documented
- [x] All 6 research phases (R1-R6/F2) integrated
- [x] Every number traces to committed artifact
- [x] Statistical reporting: Cohen's d, 95% CI, p-values

## Paper Structure
- [x] Abstract (reflects full R1-R6 findings)
- [x] Introduction
- [x] Related Work
- [x] Formalism
- [x] Architecture
- [x] Domains
- [x] Experimental Setup & Provenance
- [x] Results (Sections 7.1-7.8)
- [x] Mechanistic Analysis
- [x] Discussion
- [x] Limitations
- [x] Conclusion
- [x] Reproducibility Appendix
- [x] Reviewer Risk Appendix
- [x] Repair/Appendix figures
- [x] Cognitive Contribution Appendix
- [x] Prediction Gating (full sweep) Appendix
- [x] Learned Compatibility (full sweep) Appendix

## Claims Checklist
- [x] No "solves generalization"
- [x] No "role-balanced curriculum works"
- [x] No "prediction is load-bearing"
- [x] No "learned roles solved ontology"
- [x] No speech claims
- [x] Acknowledges approach-only > role-balanced
- [x] Acknowledges non-transfer for hazard_large
- [x] Acknowledges diminishing returns for R5/R6
- [x] 1000-seed estimate (d=-0.238) replaces noisy Phase D estimate
- [x] Baseline comparison shows TAIS is not trivially powerful

## Figures
- [ ] Figures generated from committed data via `generate_paper_figures.py`
- [ ] All figure paths referenced in .tex point to `paper/figures/`
- [ ] All axes labeled, legends present

## Tables
- [x] Table 1: Provenance table
- [x] Table 2: Role-balanced curriculum
- [x] Table 3: 1000-seed replication
- [x] Table 4: Role-ontology robustness
- [x] Table 5: Baseline comparison
- [x] Table 6: Larger-domain transfer
- [x] Table 7: Cognitive contribution (appendix)
- [x] Table 8: Prediction gating full sweep (appendix)
- [x] Table 9: Learned compatibility full sweep (appendix)

## Validation
- [ ] No HTML artifacts in .tex (no `[http` without `\url{...}`)
- [ ] No `TODO` / `FIXME` / `HACK`
- [ ] No outdated metadata (commit hash, test count)
- [ ] All LaTeX commands valid
- [ ] Run `python -m pytest tests/ -q --timeout=120`
- [ ] Run `python scripts/generate_paper_figures.py`

## Build
- [ ] pdflatex available: run `make -C paper/`
- [ ] pdflatex unavailable: note "PDF compilation pending" in README

## Repository
- [ ] `paper/` directory committed and pushed
- [ ] All result artifacts committed
- [ ] Scripts versioned
- [ ] README updated with submission note

---

*Last updated: 2026-06-09*
