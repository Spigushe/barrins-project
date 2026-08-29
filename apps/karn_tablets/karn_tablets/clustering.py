"""Clustering pipeline: PCA -> algorithm (KMeans / DBSCAN / GMM) -> 2D-PCA viz.

Ported from the prior attempt at this
(`barrins-archive/barrins_api/app/services/ml/clustering.py`), with
`clusterize_by_window` adapted to take a resolved `dc_calendar.windowing.Window`
instead of re-deriving a rolling window inline -- date-range resolution
lives in one shared place (`libs/dc_calendar`), not duplicated here.
"""

from typing import Literal

import numpy as np
import pandas as pd
from dc_calendar.windowing import Window
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from karn_tablets import extract, features
from karn_tablets.schemas import DeckCoordinates

AlgorithmLiteral = Literal["kmeans", "dbscan", "gmm"]


def suggest_clusters(
    vectors: np.ndarray,
    min_clusters: int = 4,
    max_clusters: int = 10,
    random_state: int = 42,
) -> int:
    """Selects k by silhouette-score maximization (KMeans)."""
    n = len(vectors)
    # silhouette_score requires k >= 2 and n > k (non-singleton clusters).
    if n < 3:
        return 1
    # Also bound by the number of distinct points, to avoid KMeans'
    # ConvergenceWarning on data with duplicate rows.
    n_unique = len(np.unique(vectors, axis=0))
    lo = max(2, min_clusters)
    hi = min(max_clusters, n - 1, n_unique - 1)
    if lo > hi:
        # Not enough samples/distinct points to reach even `min_clusters`
        # -- fall back to the largest *feasible* k (never `lo`, which can
        # exceed `n` and crash KMeans outright on small windows).
        return max(1, hi)

    scores = []
    for k in range(lo, hi + 1):
        km = KMeans(n_clusters=k, n_init="auto", random_state=random_state)
        km.fit(vectors)
        scores.append(silhouette_score(vectors, km.labels_))
    return int(np.argmax(scores)) + lo


def suggest_clusters_bic(
    vectors: np.ndarray,
    min_clusters: int = 4,
    max_clusters: int = 10,
    random_state: int = 42,
) -> int:
    """Selects n_components for a GMM by BIC minimization."""
    from sklearn.mixture import GaussianMixture

    n = len(vectors)
    # GMM requires n_samples >= n_components.
    if n < 2:
        return 1
    lo = max(1, min_clusters)
    hi = min(max_clusters, n)
    if lo > hi:
        # Same fallback as suggest_clusters(): the largest feasible k,
        # never a `lo` that can exceed `n`.
        return max(1, hi)

    bic_scores = []
    for k in range(lo, hi + 1):
        gmm = GaussianMixture(
            n_components=k, covariance_type="full", random_state=random_state
        )
        gmm.fit(vectors)
        bic_scores.append(gmm.bic(vectors))
    return int(np.argmin(bic_scores)) + lo


def clusterize(
    df_features: pd.DataFrame,
    n_pca_components: int = 20,
    n_viz_components: int = 2,
    algorithm: AlgorithmLiteral = "kmeans",
    random_state: int = 42,
) -> list[DeckCoordinates]:
    """Full pipeline:

    1. High-dimension PCA (`n_pca_components`) -> the clustering space.
    2. Dispatch on `algorithm` (kmeans / dbscan / gmm).
    3. Separate 2D PCA (`n_viz_components`) -> visualization coordinates.

    DBSCAN: noise points (label=-1) -> cluster=0.
    GMM: k selected via BIC.
    KMeans: k selected via silhouette score.
    """
    if df_features.empty:
        return []

    exclude = [c for c in ["deck_id"] if c in df_features.columns]
    vectors = df_features.drop(columns=exclude).fillna(0).astype(float).to_numpy()

    n_clust = min(n_pca_components, vectors.shape[0], vectors.shape[1])
    pca_clust = PCA(n_components=n_clust, random_state=random_state)
    with np.errstate(invalid="ignore"):
        x_clust = pca_clust.fit_transform(vectors)

    if algorithm == "kmeans":
        k = suggest_clusters(x_clust, random_state=random_state)
        model = KMeans(n_clusters=k, n_init="auto", random_state=random_state)
        model.fit(x_clust)
        raw_labels = model.labels_

    elif algorithm == "dbscan":
        from sklearn.cluster import DBSCAN
        from sklearn.neighbors import NearestNeighbors

        n_samples = len(x_clust)
        if n_samples < 2:
            raw_labels = np.zeros(n_samples, dtype=int)
        else:
            # n_neighbors excludes the point itself (max = n-1).
            n_neighbors = min(5, n_samples - 1)
            min_samples = min(5, n_samples)
            # Auto-estimate eps: 95th percentile of distances to the k-th neighbor.
            nn = NearestNeighbors(n_neighbors=n_neighbors).fit(x_clust)
            dists, _ = nn.kneighbors(x_clust)
            eps = float(np.percentile(dists[:, -1], 95))
            model = DBSCAN(eps=eps, min_samples=min_samples)
            model.fit(x_clust)
            raw_labels = model.labels_  # -1 = noise

    elif algorithm == "gmm":
        from sklearn.mixture import GaussianMixture

        k = suggest_clusters_bic(x_clust, random_state=random_state)
        model = GaussianMixture(
            n_components=k, covariance_type="full", random_state=random_state
        )
        model.fit(x_clust)
        raw_labels = model.predict(x_clust)

    else:
        raise ValueError(f"unknown algorithm: {algorithm!r}")

    # sklearn's stubs type `.labels_`/`.predict()` as possibly `None`
    # (only true before `fit`, which every branch above already called) --
    # ty can't see through that without an explicit narrowing assertion.
    assert raw_labels is not None

    # 1-indexed clusters; DBSCAN noise (label=-1) -> cluster=0.
    labels = [0 if raw == -1 else int(raw) + 1 for raw in raw_labels]

    n_viz = min(n_viz_components, vectors.shape[0], vectors.shape[1])
    pca_viz = PCA(n_components=n_viz, random_state=random_state)
    with np.errstate(invalid="ignore"):
        x_viz = pca_viz.fit_transform(vectors)

    deck_ids = df_features["deck_id"].tolist()
    return [
        DeckCoordinates(
            deck_id=did,
            cluster=label,
            x_coord=float(x_viz[i, 0]),
            y_coord=float(x_viz[i, 1] if n_viz >= 2 else 0.0),
        )
        for i, (did, label) in enumerate(zip(deck_ids, labels, strict=True))
    ]


def clusterize_by_window(
    window: Window, algorithm: AlgorithmLiteral = "kmeans"
) -> list[DeckCoordinates]:
    """Entry point: extracts Duel Commander decks in `window` and clusters them."""
    df_dc = extract.load_deck_cards(window.date_from, window.date_to)
    if df_dc.empty:
        return []

    df_cards = extract.load_cards_features()
    df_main = df_dc[~df_dc["is_sideboard"]]
    df_feat = features.flatten_features_dict(df_main, df_cards)
    return clusterize(df_feat, algorithm=algorithm)
