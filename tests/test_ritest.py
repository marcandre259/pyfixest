import matplotlib
import numpy as np
import pandas as pd
import pytest

import pyfixest as pf

matplotlib.use("Agg")  # Use a non-interactive backend


@pytest.mark.parametrize("fml", ["Y~X1+f3", "Y~X1+f3|f1", "Y~X1+f3|f1+f2"])
@pytest.mark.parametrize("resampvar", ["X1", "f3"])
@pytest.mark.parametrize("reps", [111, 212])
@pytest.mark.parametrize("cluster", [None, "group_id"])
def test_algos_internally(data, fml, resampvar, reps, cluster):
    fit = pf.feols(fml, data=data)

    rng1 = np.random.default_rng(1234)
    rng2 = np.random.default_rng(1234)

    kwargs = {
        "resampvar": resampvar,
        "reps": reps,
        "type": "randomization-c",
        "store_ritest_statistics": True,
        "cluster": cluster,
    }

    kwargs1 = kwargs.copy()
    kwargs2 = kwargs.copy()

    kwargs1["choose_algorithm"] = "slow"
    kwargs1["rng"] = rng1
    kwargs2["choose_algorithm"] = "fast"
    kwargs2["rng"] = rng2

    res1 = fit.ritest(**kwargs1)
    ritest_stats1 = fit._ritest_statistics.copy()

    res2 = fit.ritest(**kwargs2)
    ritest_stats2 = fit._ritest_statistics.copy()

    assert np.allclose(res1.Estimate, res2.Estimate, atol=1e-8, rtol=1e-8)
    assert np.allclose(res1["Pr(>|t|)"], res2["Pr(>|t|)"], atol=1e-8, rtol=1e-8)
    assert np.allclose(ritest_stats1, ritest_stats2, atol=1e-8, rtol=1e-8)


@pytest.mark.parametrize("fml", ["Y~X1+f3", "Y~X1+f3|f1", "Y~X1+f3|f1+f2"])
@pytest.mark.parametrize("resampvar", ["X1", "f3"])
@pytest.mark.parametrize("reps", [1000])
@pytest.mark.parametrize("cluster", [None, "group_id"])
def test_randomization_t_vs_c(data, fml, resampvar, reps, cluster):
    fit = pf.feols(fml, data=data)

    rng1 = np.random.default_rng(1234)
    rng2 = np.random.default_rng(1234)

    kwargs = {
        "resampvar": resampvar,
        "reps": reps,
        "store_ritest_statistics": True,
        "cluster": cluster,
    }

    kwargs1 = kwargs.copy()
    kwargs2 = kwargs.copy()

    kwargs1["type"] = "randomization-c"
    kwargs1["rng"] = rng1
    kwargs2["choose_algorithm"] = "randomization-t"
    kwargs2["rng"] = rng2

    res1 = fit.ritest(**kwargs1)
    ritest_stats1 = fit._ritest_statistics.copy()

    res2 = fit.ritest(**kwargs2)
    ritest_stats2 = fit._ritest_statistics.copy()

    assert np.allclose(res1.Estimate, res2.Estimate, atol=1e-8, rtol=1e-8)
    assert np.allclose(res1["Pr(>|t|)"], res2["Pr(>|t|)"], atol=1e-2, rtol=1e-2)
    assert np.allclose(ritest_stats1, ritest_stats2, atol=1e-2, rtol=1e-2)


@pytest.fixture
def ritest_results():
    # Load the CSV file into a pandas DataFrame
    file_path = "tests/data/ritest_results.csv"
    results_df = pd.read_csv(file_path)
    results_df.set_index(["formula", "resampvar", "cluster"], inplace=True)
    return results_df


@pytest.fixture
def data():
    return pf.get_data(N=1000, seed=2999)


@pytest.mark.parametrize("fml", ["Y~X1+f3", "Y~X1+f3|f1", "Y~X1+f3|f1+f2"])
@pytest.mark.parametrize("resampvar", ["X1", "f3", "X1=-0.75", "f3>0.05"])
@pytest.mark.parametrize("cluster", [None, "group_id"])
def test_vs_r(data, fml, resampvar, cluster, ritest_results):
    fit = pf.feols(fml, data=data)
    reps = 4000

    rng1 = np.random.default_rng(1234)

    kwargs = {
        "resampvar": resampvar,
        "reps": reps,
        "type": "randomization-c",
        "cluster": cluster,
    }

    kwargs1 = kwargs.copy()

    kwargs1["choose_algorithm"] = "fast"
    kwargs1["rng"] = rng1

    res1 = fit.ritest(**kwargs1)

    if cluster is not None:
        pval = ritest_results.xs(
            (fml, resampvar, cluster), level=("formula", "resampvar", "cluster")
        )["pval"].to_numpy()
        se = ritest_results.xs(
            (fml, resampvar, cluster), level=("formula", "resampvar", "cluster")
        )["se"].to_numpy()
        ci_lower = ritest_results.xs(
            (fml, resampvar, cluster), level=("formula", "resampvar", "cluster")
        )["ci_lower"].to_numpy()
    else:
        pval = ritest_results.xs(
            (fml, resampvar, "none"), level=("formula", "resampvar", "cluster")
        )["pval"].to_numpy()
        se = ritest_results.xs(
            (fml, resampvar, "none"), level=("formula", "resampvar", "cluster")
        )["se"].to_numpy()
        ci_lower = ritest_results.xs(
            (fml, resampvar, "none"), level=("formula", "resampvar", "cluster")
        )["ci_lower"].to_numpy()

    assert np.allclose(res1["Pr(>|t|)"], pval, rtol=0.005, atol=0.005)
    assert np.allclose(res1["Std. Error (Pr(>|t|))"], se, rtol=0.005, atol=0.005)
    assert np.allclose(res1["2.5% (Pr(>|t|))"], ci_lower, rtol=0.005, atol=0.005)


def test_fepois_ritest():
    data = pf.get_data(model="Fepois")
    fit = pf.fepois("Y ~ X1*f3", data=data)
    fit.ritest(resampvar="f3", reps=2000, store_ritest_statistics=True)

    assert fit._ritest_statistics is not None
    assert np.allclose(fit.pvalue().xs("f3"), fit._ritest_pvalue, rtol=0.01, atol=0.01)


@pytest.fixture
def data_r_vs_t():
    return pf.get_data(N=5000, seed=2999)


@pytest.mark.parametrize("fml", ["Y~X1+f3", "Y~X1+f3|f1", "Y~X1+f3|f1+f2"])
@pytest.mark.parametrize("resampvar", ["X1", "f3"])
@pytest.mark.parametrize("cluster", [None, "group_id"])
@pytest.mark.skip(reason="This feature is not yet fully implemented.")
def test_randomisation_c_vs_t(data_r_vs_t, fml, resampvar, cluster):
    """Test that the randomization-c and randomization-t tests give similar results."""
    reps = 1000
    fit = pf.feols(fml, data=data_r_vs_t)

    rng = np.random.default_rng(1234)

    ri1 = fit.ritest(
        resampvar=resampvar, reps=reps, type="randomization-c", rng=rng, cluster=cluster
    )
    ri2 = fit.ritest(
        resampvar=resampvar, reps=reps, type="randomization-t", rng=rng, cluster=cluster
    )

    assert np.allclose(ri1.Estimate, ri2.Estimate, rtol=0.01, atol=0.01)
    assert np.allclose(ri1["Pr(>|t|)"], ri2["Pr(>|t|)"], rtol=0.01, atol=0.01)
    assert np.allclose(
        ri1["Std. Error (Pr(>|t|))"], ri2["Std. Error (Pr(>|t|))"], rtol=0.01, atol=0.01
    )
