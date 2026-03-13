"""Filtering utilities for keyword, genre, tempo, popularity, and explicit flags."""
from __future__ import annotations
import pandas as pd
from typing import Iterable, Optional, Set, Tuple, Union


def filter_tracks(
    df: pd.DataFrame,
    *,
    keyword: Optional[str] = None,
    genres: Optional[Set[str]] = None,
    tempo_range: Optional[Set[Union[int, float, None]]] = None,
    popularity_range: Optional[Set[Union[int, float, None]]] = None,
    explicit: Optional[bool] = None,
    copy: bool = False,
) -> pd.DataFrame:
    """
    Filter tracks with multiple optional conditions.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataset.

    keyword : str | None
        Case-insensitive keyword search over text columns (track_name, artists).
        If None, no keyword filtering is applied.

    genres : set[str] | None
        A set of genre names to keep. If None or empty, keep all genres.

    tempo_range : set[float | int | None] | None
        A set with length 2: {lower, upper}. Either bound can be None.
        Examples:
          {None, 80}   -> [min_tempo, 80]
          {90, None}   -> [90, max_tempo]
          {90, 140}   -> [90, 140]
        If None, no tempo filtering.

    popularity_range : set[int | None] | None
        Same convention as tempo_range but for popularity.
        Examples:
          {None, 80} -> [min_popularity, 80]
          {40, None} -> [40, max_popularity]

    explicit : bool | None
        If True  -> keep only explicit == True
        If False -> keep only explicit == False
        If None  -> keep both True and False

    copy : bool
        If True, return df.copy() after filtering.
        If False, return the filtered view.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame (or a copy if copy=True).
    """

    out = df

    # ---------- keyword (case-insensitive) ----------
    if keyword:
        kw = keyword.lower().strip()
        # Use precomputed lowercase columns when available to avoid repeated
        # per-callback string normalization on large datasets.
        name_col = "_track_name_lc" if "_track_name_lc" in out.columns else "track_name"
        artist_col = "_artists_lc" if "_artists_lc" in out.columns else "artists"

        left = out[name_col].astype(str) if name_col.startswith("_") else out[name_col].astype(str).str.lower()
        right = out[artist_col].astype(str) if artist_col.startswith("_") else out[artist_col].astype(str).str.lower()

        mask = left.str.contains(kw, na=False) | right.str.contains(kw, na=False)
        out = out[mask]

    # ---------- genre ----------
    if genres:
        genres = set(genres)
        out = out[out["track_genre"].isin(genres)]

    # ---------- tempo range ----------
    if tempo_range:
        lo, hi = _parse_range(tempo_range, out["tempo"])
        out = out[(out["tempo"] >= lo) & (out["tempo"] <= hi)]

    # ---------- popularity range ----------
    if popularity_range:
        lo, hi = _parse_range(popularity_range, out["popularity"])
        out = out[(out["popularity"] >= lo) & (out["popularity"] <= hi)]

    # ---------- explicit ----------
    if explicit is True:
        out = out[out["explicit"] == True]
    elif explicit is False:
        out = out[out["explicit"] == False]
    # explicit is None -> keep both

    return out.copy() if copy else out


def _parse_range(rng, series: pd.Series):
    """
    Accept [lo, hi] / (lo, hi) / {lo, hi}. Either bound can be None.
    If a bound is None, use series min/max.
    """
    if rng is None:
        return float(series.min()), float(series.max())

    # normalize input into (lo, hi)
    if isinstance(rng, (list, tuple)):
        if len(rng) != 2:
            raise ValueError("Range must have exactly 2 elements: [lower, upper].")
        lo, hi = rng[0], rng[1]

    elif isinstance(rng, set):
        # sets break when lo==hi (dedup), so handle len==1 as a point-range
        if len(rng) == 1:
            (v,) = tuple(rng)
            lo, hi = v, v
        elif len(rng) == 2:
            lo, hi = tuple(rng)
        else:
            raise ValueError("Range set must have 1 or 2 elements.")
    else:
        raise TypeError("Range must be a list/tuple/set with bounds.")

    if lo is None:
        lo = float(series.min())
    if hi is None:
        hi = float(series.max())

    lo = float(lo)
    hi = float(hi)

    if lo > hi:
        raise ValueError(f"Invalid range: lower bound {lo} is greater than upper bound {hi}.")

    return lo, hi
