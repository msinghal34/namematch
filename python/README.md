# namematch (Python)

Rule-based matching of person names in Indian, and especially Karnataka, property and identity records.
See the repository's README for the full description; the Java library in the same repository gives identical results.

```python
from namematch import match

r = match("Suresh Kumr Gowda", "SURESH KUMAR")
r.score    # 0.762
r.band     # "likely_same"
r.reasons  # ["kumr~kumar 0.86", "extra: gowda"]
```
