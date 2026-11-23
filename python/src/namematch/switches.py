"""Switches for the live rules, all on in production.

Each switch turns one rule on or off, so its effect on a labelled set of name pairs can be measured
alone. Rules that a sealed evaluation set showed to add false accepts, or to bring no measurable
benefit, were deleted rather than left switched off. near_miss was added in v0.3.0.
"""

ON = {
    "vowel_drop": True,          # 'kumr' ~ 'kumar'
    "short_floor": True,         # short names need near-identity: kamala != komal
    "word_conflict": True,       # leftover initial vs an unexplained word ('Pallavi Ramappa K' vs 'K B Ramappa')
    "firm_cap": True,            # 'M/s <person>' vs the person capped at 0.6
    "holder_for": True,          # '<agent> GPA holder for <owner>'
    "spelled_initials": True,    # 'EM' = M
    "relative_explains": True,   # extra word that is the other side's S/o name
    "relative_conflict": True,   # different fathers / relation kinds / initials vs father
    "near_miss": True,           # v0.3.0: one-letter slip in a short name -> review (<= 0.64), never accepted
}
