"""
Tests for neighbor embedding methods.
"""

# Author: Hugues Van Assel <vanasselhugues@gmail.com>
#         Nicolas Courty <ncourty@irisa.fr>
#
# License: BSD 3-Clause License

import numpy as np
import pytest
import torch
from sklearn.metrics import silhouette_score

from torchdr.neighbor_embedding import (
    SNE,
    TSNE,
    COSNE,
    UMAP,
    InfoTSNE,
    LargeVis,
    TSNEkhorn,
    PACMAP,
)
from torchdr.tests.utils import toy_dataset, iris_dataset
from torchdr.utils import check_shape, pykeops

if pykeops:
    lst_backend = ["keops", None]
else:
    lst_backend = [None]


lst_types = ["float32", "float64"]
SEA_params = {"lr_affinity_in": 1e-1, "max_iter_affinity_in": 1000}
DEVICE = "cpu"


param_optim = {"lr": 1.0, "optimizer": "Adam", "optimizer_kwargs": None}


@pytest.mark.parametrize(
    "DRModel, kwargs",
    [
        (SNE, {}),
        (TSNE, {}),
        (TSNEkhorn, {**SEA_params, "unrolling": True}),
        (TSNEkhorn, {**SEA_params, "unrolling": False}),
        (LargeVis, {}),
        (InfoTSNE, {}),
        (UMAP, {"optimizer": "SGD"}),
        (PACMAP, {}),
    ],
)
@pytest.mark.parametrize("dtype", lst_types)
@pytest.mark.parametrize("backend", lst_backend)
def test_NE(DRModel, kwargs, dtype, backend):
    n = 100
    X, y = toy_dataset(n, dtype)

    model = DRModel(
        n_components=2,
        backend=backend,
        device=DEVICE,
        init="normal",
        max_iter=100,
        random_state=0,
        min_grad_norm=1e-10,
        **{**param_optim, **kwargs},
    )
    Z = model.fit_transform(X)

    check_shape(Z, (n, 2))
    assert silhouette_score(Z, y) > 0.15, "Silhouette score should not be too low."


@pytest.mark.parametrize("dtype", lst_types)
def test_COSNE(dtype):
    X, y = iris_dataset(dtype)

    model = COSNE(
        lr=1e-1,
        n_components=2,
        device=DEVICE,
        max_iter=1000,
        random_state=0,
        gamma=1,
        lambda1=0.01,
    )
    Z = model.fit_transform(X)

    check_shape(Z, (X.shape[0], 2))
    assert silhouette_score(Z, y) > 0.15, "Silhouette score should not be too low."


@pytest.mark.parametrize("dtype", lst_types)
@pytest.mark.parametrize("backend", lst_backend)
def test_array_init(dtype, backend):
    n = 100
    X, y = toy_dataset(n, dtype)

    Z_init_np = np.random.randn(n, 2).astype(dtype)
    Z_init_torch = torch.from_numpy(Z_init_np)

    torch.use_deterministic_algorithms(True)

    lst_Z = []
    for Z_init in [Z_init_np, Z_init_torch]:
        model = SNE(
            n_components=2,
            backend=backend,
            device=DEVICE,
            init=Z_init,
            max_iter=100,
            random_state=0,
            **param_optim,
        )
        Z = model.fit_transform(X)
        lst_Z.append(Z)

        check_shape(Z, (n, 2))
        assert silhouette_score(Z, y) > 0.2, "Silhouette score should not be too low."

    # --- checks that the two inits yield similar results ---
    assert ((lst_Z[0] - lst_Z[1]) ** 2).mean() < 1e-5, (
        "The two inits should yield similar results."
    )
