"""Independent labeling helper; see IMPLEMENTATION_SPEC.md section 9."""

import numpy as np
from scipy import sparse
from sklearn.preprocessing import normalize


def class_tfidf(class_counts: sparse.csr_matrix) -> sparse.csr_matrix:
    """Own small implementation of the documented default c-TF-IDF formula."""
    counts = sparse.csr_matrix(class_counts, dtype=np.float64)
    if counts.shape[0] == 0 or counts.shape[1] == 0:
        return counts
    if not np.isfinite(counts.data).all() or (counts.data < 0).any():
        raise ValueError("Counts must be finite and nonnegative")
    row_lengths = np.asarray(counts.sum(axis=1)).ravel()
    average_length = float(row_lengths.mean())
    if average_length == 0:
        return counts
    term_totals = np.asarray(counts.sum(axis=0)).ravel()
    idf = np.zeros_like(term_totals)
    present = term_totals > 0
    idf[present] = np.log1p(average_length / term_totals[present])
    tf = normalize(counts, norm="l1", axis=1)
    return (tf @ sparse.diags(idf)).tocsr()
