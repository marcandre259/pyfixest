import warnings
from typing import Optional, Union

import numpy as np
import pandas as pd
import polars as pl

from pyfixest.errors import FeatureDeprecationError
from pyfixest.estimation.feols_ import Feols
from pyfixest.estimation.fepois_ import Fepois
from pyfixest.estimation.FixestMulti_ import FixestMulti
from pyfixest.utils.dev_utils import DataFrameType
from pyfixest.utils.utils import ssc


def feols(
    fml: str,
    data: DataFrameType,  # type: ignore
    vcov: Optional[Union[str, dict[str, str]]] = None,
    weights: Union[None, str] = None,
    ssc: dict[str, Union[str, bool]] = ssc(),
    fixef_rm: str = "none",
    fixef_tol=1e-08,
    collin_tol: float = 1e-10,
    drop_intercept: bool = False,
    i_ref1=None,
    copy_data: bool = True,
    store_data: bool = True,
    lean: bool = False,
    weights_type: str = "aweights",
    use_compression: bool = False,
    use_mundlak: bool = False,
) -> Union[Feols, FixestMulti]:
    """
    Estimate a linear regression models with fixed effects using fixest formula syntax.

    Parameters
    ----------
    fml : str
        A three-sided formula string using fixest formula syntax.
        Syntax: "Y ~ X1 + X2 | FE1 + FE2 | X1 ~ Z1". "|" separates dependent variable,
        fixed effects, and instruments. Special syntax includes stepwise regressions,
        cumulative stepwise regression, multiple dependent variables,
        interaction of variables (i(X1,X2)), and interacted fixed effects (fe1^fe2).

    data : DataFrameType
        A pandas or polars dataframe containing the variables in the formula.

    vcov : Union[str, dict[str, str]]
        Type of variance-covariance matrix for inference. Options include "iid",
        "hetero", "HC1", "HC2", "HC3", or a dictionary for CRV1/CRV3 inference.

    weights : Union[None, str], optional.
        Default is None. Weights for WLS estimation. If None, all observations
        are weighted equally. If a string, the name of the column in `data` that
        contains the weights.

    ssc : str
        A ssc object specifying the small sample correction for inference.

    fixef_rm : str
        Specifies whether to drop singleton fixed effects.
        Options: "none" (default), "singleton".

    collin_tol : float, optional
        Tolerance for collinearity check, by default 1e-10.

    fixef_tol: float, optional
        Tolerance for the fixed effects demeaning algorithm. Defaults to 1e-08.

    drop_intercept : bool, optional
        Whether to drop the intercept from the model, by default False.

    i_ref1: None
        Deprecated with pyfixest version 0.18.0. Please use i-syntax instead, i.e.
        feols('Y~ i(f1, ref=1)', data = data) instead of the former
        feols('Y~ i(f1)', data = data, i_ref=1).

    copy_data : bool, optional
        Whether to copy the data before estimation, by default True.
        If set to False, the data is not copied, which can save memory but
        may lead to unintended changes in the input data outside of `fepois`.
        For example, the input data set is re-index within the function.
        As far as I know, the only other relevant case is
        when using interacted fixed effects, in which case you'll find
        a column with interacted fixed effects in the data set.

    store_data : bool, optional
        Whether to store the data in the model object, by default True.
        If set to False, the data is not stored in the model object, which can
        improve performance and save memory. However, it will no longer be possible
        to access the data via the `data` attribute of the model object. This has
        impact on post-estimation capabilities that rely on the data, e.g. `predict()`
        or `vcov()`.

    lean: bool, optional
        False by default. If True, then all large objects are removed from the
        returned result: this will save memory but will block the possibility
        to use many methods. It is recommended to use the argument vcov
        to obtain the appropriate standard-errors at estimation time,
        since obtaining different SEs won't be possible afterwards.

    weights_type: str, optional
        Options include `aweights` or `fweights`. `aweights` implement analytic or
        precision weights, while `fweights` implement frequency weights. For details
        see this blog post: https://notstatschat.rbind.io/2020/08/04/weights-in-statistics/.

    use_compression: bool
        Whether to use sufficient statistics to losslessly fit the regression model
        on compressed data. False by default.

    use_mundlak: bool
        Whether to use the Mundlak transform for fixed effects estimation. Works
        for oneway fixed effects. For two-way fixed effects, the two-way Mundlak
        only works for panel data sets. False by default.


    Returns
    -------
    object
        An instance of the [Feols(/reference/Feols.qmd) class or `FixestMulti`
        class for multiple models specified via `fml`.

    Examples
    --------
    As in `fixest`, the [Feols(/reference/Feols.qmd) function can be used to
    estimate a simple linear regression model with fixed effects.
    The following example regresses `Y` on `X1` and `X2` with fixed effects for
    `f1` and `f2`: fixed effects are specified after the `|` symbol.

    ```{python}
    import pyfixest as pf

    data = pf.get_data()

    fit = pf.feols("Y ~ X1 + X2 | f1 + f2", data)
    fit.summary()
    ```

    Calling `feols()` returns an instance of the [Feols(/reference/Feols.qmd)
    class. The `summary()` method can be used to print the results.

    An alternative way to retrieve model results is via the `tidy()` method, which
    returns a pandas dataframe with the estimated coefficients, standard errors,
    t-statistics, and p-values.

    ```{python}
    fit.tidy()
    ```

    You can also access all elements in the tidy data frame by dedicated methods,
    e.g. `fit.coef()` for the coefficients, `fit.se()` for the standard errors,
    `fit.tstat()` for the t-statistics, and `fit.pval()` for the p-values, and
    `fit.confint()` for the confidence intervals.

    The employed type of inference can be specified via the `vcov` argument. If
    vcov is not provided, `PyFixest` employs the `fixest` default of iid inference,
    unless there are fixed effects in the model, in which case `feols()` clusters
    the standard error by the first fixed effect (CRV1 inference).

    ```{python}
    fit1 = pf.feols("Y ~ X1 + X2 | f1 + f2", data, vcov="iid")
    fit2 = pf.feols("Y ~ X1 + X2 | f1 + f2", data, vcov="hetero")
    fit3 = pf.feols("Y ~ X1 + X2 | f1 + f2", data, vcov={"CRV1": "f1"})
    ```

    Supported inference types are "iid", "hetero", "HC1", "HC2", "HC3", and
    "CRV1"/"CRV3". Clustered standard errors are specified via a dictionary,
    e.g. `{"CRV1": "f1"}` for CRV1 inference with clustering by `f1` or
    `{"CRV3": "f1"}` for CRV3 inference with clustering by `f1`. For two-way
    clustering, you can provide a formula string, e.g. `{"CRV1": "f1 + f2"}` for
    CRV1 inference with clustering by `f1`.

    ```{python}
    fit4 = pf.feols("Y ~ X1 + X2 | f1 + f2", data, vcov={"CRV1": "f1 + f2"})
    ```

    Inference can be adjusted post estimation via the `vcov` method:

    ```{python}
    fit.summary()
    fit.vcov("iid").summary()
    ```

    The `ssc` argument specifies the small sample correction for inference. In
    general, `feols()` uses all of `fixest::feols()` defaults, but sets the
    `fixef.K` argument to `"none"` whereas the `fixest::feols()` default is `"nested"`.
    See here for more details: [link to github](https://github.com/py-econometrics/pyfixest/issues/260).

    `feols()` supports a range of multiple estimation syntax, i.e. you can estimate
    multiple models in one call. The following example estimates two models, one with
    fixed effects for `f1` and one with fixed effects for `f2` using the `sw()` syntax.

    ```{python}
    fit = pf.feols("Y ~ X1 + X2 | sw(f1, f2)", data)
    type(fit)
    ```

    The returned object is an instance of the `FixestMulti` class. You can access
    the results of the first model via `fit.fetch_model(0)` and the results of
    the second model via `fit.fetch_model(1)`. You can compare the model results
    via the `etable()` function:

    ```{python}
    pf.etable([fit.fetch_model(0), fit.fetch_model(1)])
    ```

    Other supported multiple estimation syntax include `sw0()`, `csw()` and `csw0()`.
    While `sw()` adds variables in a "stepwise" fashion, `csw()` does so cumulatively.

    ```{python}
    fit = pf.feols("Y ~ X1 + X2 | csw(f1, f2)", data)
    pf.etable([fit.fetch_model(0), fit.fetch_model(1)])
    ```

    The `sw0()` and `csw0()` syntax are similar to `sw()` and `csw()`, but start
    with a model that excludes the variables specified in `sw()` and `csw()`:

    ```{python}
    fit = pf.feols("Y ~ X1 + X2 | sw0(f1, f2)", data)
    pf.etable([fit.fetch_model(0), fit.fetch_model(1), fit.fetch_model(2)])
    ```

    The `feols()` function also supports multiple dependent variables. The following
    example estimates two models, one with `Y1` as the dependent variable and one
    with `Y2` as the dependent variable.

    ```{python}
    fit = pf.feols("Y + Y2 ~ X1 | f1 + f2", data)
    pf.etable([fit.fetch_model(0), fit.fetch_model(1)])
    ```

    It is possible to combine different multiple estimation operators:

    ```{python}
    fit = pf.feols("Y + Y2 ~ X1 | sw(f1, f2)", data)
    pf.etable([fit.fetch_model(0),
            fit.fetch_model(1),
            fit.fetch_model(2),
            fit.fetch_model(3)
            ]
        )
    ```

    In general, using muliple estimation syntax can improve the estimation time
    as covariates that are demeaned in one model and are used in another model do
    not need to be demeaned again: `feols()` implements a caching mechanism that
    stores the demeaned covariates.

    Besides OLS, `feols()` also supports IV estimation via three part formulas:

    ```{python}
    fit = pf.feols("Y ~  X2 | f1 + f2 | X1 ~ Z1", data)
    fit.tidy()
    ```
    Here, `X1` is the endogenous variable and `Z1` is the instrument. `f1` and `f2`
    are the fixed effects, as before. To estimate IV models without fixed effects,
    simply omit the fixed effects part of the formula:

    ```{python}
    fit = pf.feols("Y ~  X2 | X1 ~ Z1", data)
    fit.tidy()
    ```

    Last, `feols()` supports interaction of variables via the `i()` syntax.
    Documentation on this is tba.

    After fitting a model via `feols()`, you can use the `predict()` method to
    get the predicted values:

    ```{python}
    fit = pf.feols("Y ~ X1 + X2 | f1 + f2", data)
    fit.predict()[0:5]
    ```

    The `predict()` method also supports a `newdata` argument to predict on new data,
    which returns a numpy array of the predicted values:

    ```{python}
    fit = pf.feols("Y ~ X1 + X2 | f1 + f2", data)
    fit.predict(newdata=data)[0:5]
    ```

    Last, you can plot the results of a model via the `coefplot()` method:

    ```{python}
    fit = pf.feols("Y ~ X1 + X2 | f1 + f2", data)
    fit.coefplot()
    ```

    Objects of type `Feols` support a range of other methods to conduct inference.
    For example, you can run a wild (cluster) bootstrap via the `wildboottest()` method:

    ```{python}
    fit.wildboottest(param = "X1", reps=1000)
    ```
    would run a wild bootstrap test for the coefficient of `X1` with 1000
    bootstrap repetitions.

    For a wild cluster bootstrap, you can specify the cluster variable
      via the `cluster` argument:

    ```{python}
    fit.wildboottest(param = "X1", reps=1000, cluster="group_id")
    ```

    The `ritest()` method can be used to conduct randomization inference:

    ```{python}
    fit.ritest(resampvar = "X1", reps=1000)
    ```

    Last, you can compute the cluster causal variance estimator by Athey et
    al by using the `ccv()` method:

    ```{python}
    import numpy as np
    rng = np.random.default_rng(1234)
    data["D"] = rng.choice([0, 1], size = data.shape[0])
    fit_D = pf.feols("Y ~ D", data = data)
    fit_D.ccv(treatment = "D", cluster = "group_id")
    ```

    """
    if i_ref1 is not None:
        raise FeatureDeprecationError(
            """
            The 'i_ref1' function argument is deprecated with pyfixest version 0.18.0.
            Please use i-syntax instead, i.e. feols('Y~ i(f1, ref=1)', data = data)
            instead of the former feols('Y~ i(f1)', data = data, i_ref=1).
            """
        )

    _estimation_input_checks(
        fml=fml,
        data=data,
        vcov=vcov,
        weights=weights,
        ssc=ssc,
        fixef_rm=fixef_rm,
        collin_tol=collin_tol,
        copy_data=copy_data,
        store_data=store_data,
        lean=lean,
        fixef_tol=fixef_tol,
        weights_type=weights_type,
        use_compression=use_compression,
        use_mundlak=use_mundlak,
    )

    fixest = FixestMulti(
        data=data,
        copy_data=copy_data,
        store_data=store_data,
        lean=lean,
        fixef_tol=fixef_tol,
        weights_type=weights_type,
        use_compression=use_compression,
        use_mundlak=use_mundlak,
    )

    fixest._prepare_estimation(
        "feols", fml, vcov, weights, ssc, fixef_rm, drop_intercept
    )

    # demean all models: based on fixed effects x split x missing value combinations
    fixest._estimate_all_models(vcov, collin_tol=collin_tol)

    if fixest._is_multiple_estimation:
        return fixest
    else:
        return fixest.fetch_model(0, print_fml=False)


def fepois(
    fml: str,
    data: DataFrameType,  # type: ignore
    vcov: Optional[Union[str, dict[str, str]]] = None,
    ssc: dict[str, Union[str, bool]] = ssc(),
    fixef_rm: str = "none",
    fixef_tol: float = 1e-08,
    iwls_tol: float = 1e-08,
    iwls_maxiter: int = 25,
    collin_tol: float = 1e-10,
    drop_intercept: bool = False,
    i_ref1=None,
    copy_data: bool = True,
    store_data: bool = True,
    lean: bool = False,
) -> Union[Feols, Fepois, FixestMulti]:
    """
    Estimate Poisson regression model with fixed effects using the `ppmlhdfe` algorithm.

    Parameters
    ----------
    fml : str
        A two-sided formula string using fixest formula syntax.
        Syntax: "Y ~ X1 + X2 | FE1 + FE2". "|" separates left-hand side and fixed
        effects.
        Special syntax includes:
        - Stepwise regressions (sw, sw0)
        - Cumulative stepwise regression (csw, csw0)
        - Multiple dependent variables (Y1 + Y2 ~ X)
        - Interaction of variables (i(X1,X2))
        - Interacted fixed effects (fe1^fe2)
        Compatible with formula parsing via the formulaic module.

    data : DataFrameType
        A pandas or polars dataframe containing the variables in the formula.

    vcov : Union[str, dict[str, str]]
        Type of variance-covariance matrix for inference. Options include "iid",
        "hetero", "HC1", "HC2", "HC3", or a dictionary for CRV1/CRV3 inference.

    ssc : str
        A ssc object specifying the small sample correction for inference.

    fixef_rm : str
        Specifies whether to drop singleton fixed effects.
        Options: "none" (default), "singleton".

    fixef_tol: float, optional
        Tolerance for the fixed effects demeaning algorithm. Defaults to 1e-08.

    iwls_tol : Optional[float], optional
        Tolerance for IWLS convergence, by default 1e-08.

    iwls_maxiter : Optional[float], optional
        Maximum number of iterations for IWLS convergence, by default 25.

    collin_tol : float, optional
        Tolerance for collinearity check, by default 1e-10.

    drop_intercept : bool, optional
        Whether to drop the intercept from the model, by default False.

    i_ref1: None
        Deprecated with pyfixest version 0.18.0. Please use i-syntax instead, i.e.
        fepois('Y~ i(f1, ref=1)', data = data) instead of the former
        fepois('Y~ i(f1)', data = data, i_ref=1).

    copy_data : bool, optional
        Whether to copy the data before estimation, by default True.
        If set to False, the data is not copied, which can save memory but
        may lead to unintended changes in the input data outside of `fepois`.
        For example, the input data set is re-index within the function.
        As far as I know, the only other relevant case is
        when using interacted fixed effects, in which case you'll find
        a column with interacted fixed effects in the data set.

    store_data : bool, optional
        Whether to store the data in the model object, by default True.
        If set to False, the data is not stored in the model object, which can
        improve performance and save memory. However, it will no longer be possible
        to access the data via the `data` attribute of the model object. This has
        impact on post-estimation capabilities that rely on the data, e.g. `predict()`
        or `vcov()`.

    lean: bool, optional
        False by default. If True, then all large objects are removed from the
        returned result: this will save memory but will block the possibility
        to use many methods. It is recommended to use the argument vcov
        to obtain the appropriate standard-errors at estimation time,
        since obtaining different SEs won't be possible afterwards.

    Returns
    -------
    object
        An instance of the `Fepois` class or an instance of class `FixestMulti`
        for multiple models specified via `fml`.

    Examples
    --------
    The `fepois()` function can be used to estimate a simple Poisson regression
    model with fixed effects.
    The following example regresses `Y` on `X1` and `X2` with fixed effects for
    `f1` and `f2`: fixed effects are specified after the `|` symbol.

    ```{python}
    import pyfixest as pf

    data = pf.get_data(model = "Fepois")
    fit = pf.fepois("Y ~ X1 + X2 | f1 + f2", data)
    fit.summary()
    ```
    For more examples, please take a look at the documentation of the `feols()`
    function.
    """
    if i_ref1 is not None:
        raise FeatureDeprecationError(
            """
            The 'i_ref1' function argument is deprecated with pyfixest version 0.18.0.
            Please use i-syntax instead, i.e. fepois('Y~ i(f1, ref=1)', data = data)
            instead of the former fepois('Y~ i(f1)', data = data, i_ref=1).
            """
        )

    # WLS currently not supported for Poisson regression
    weights = None
    weights_type = "aweights"

    _estimation_input_checks(
        fml=fml,
        data=data,
        vcov=vcov,
        weights=weights,
        ssc=ssc,
        fixef_rm=fixef_rm,
        collin_tol=collin_tol,
        copy_data=copy_data,
        store_data=store_data,
        lean=lean,
        fixef_tol=fixef_tol,
        weights_type=weights_type,
        use_compression=False,  # Poisson regression does not support compression as it doesn't support weights
        use_mundlak=False,
    )

    fixest = FixestMulti(
        data=data,
        copy_data=copy_data,
        store_data=store_data,
        lean=lean,
        fixef_tol=fixef_tol,
        weights_type=weights_type,
        use_compression=False,
    )

    fixest._prepare_estimation(
        "fepois", fml, vcov, weights, ssc, fixef_rm, drop_intercept
    )
    if fixest._is_iv:
        raise NotImplementedError(
            "IV Estimation is not supported for Poisson Regression"
        )

    fixest._estimate_all_models(
        vcov=vcov,
        iwls_tol=iwls_tol,
        iwls_maxiter=iwls_maxiter,
        collin_tol=collin_tol,
    )

    if fixest._is_multiple_estimation:
        return fixest
    else:
        return fixest.fetch_model(0, print_fml=False)


def _estimation_input_checks(
    fml: str,
    data: DataFrameType,
    vcov: Optional[Union[str, dict[str, str]]],
    weights: Union[None, str],
    ssc: dict[str, Union[str, bool]],
    fixef_rm: str,
    collin_tol: float,
    copy_data: bool,
    store_data: bool,
    lean: bool,
    fixef_tol: float,
    weights_type: str,
    use_compression: bool = False,
    use_mundlak: bool = False,
):
    if not isinstance(fml, str):
        raise TypeError("fml must be a string")
    if not isinstance(data, pd.DataFrame):
        try:
            import polars as pl

            if not isinstance(data, pl.DataFrame):
                raise TypeError("data must be a pandas or polars dataframe")
        except ImportError:
            raise TypeError("data must be a pandas or polars dataframe")
    if not isinstance(vcov, (str, dict, type(None))):
        raise TypeError("vcov must be a string, dictionary, or None")
    if not isinstance(fixef_rm, str):
        raise TypeError("fixef_rm must be a string")
    if not isinstance(collin_tol, float):
        raise TypeError("collin_tol must be a float")

    if fixef_rm not in ["none", "singleton"]:
        raise ValueError("fixef_rm must be either 'none' or 'singleton'")
    if collin_tol <= 0:
        raise ValueError("collin_tol must be greater than zero")
    if collin_tol >= 1:
        raise ValueError("collin_tol must be less than one")

    if not (isinstance(weights, str) or weights is None):
        raise ValueError(
            f"weights must be a string or None but you provided weights = {weights}."
        )
    if weights is not None:
        assert weights in data.columns, "weights must be a column in data"

    bool_args = [copy_data, store_data, lean]
    for arg in bool_args:
        if not isinstance(arg, bool):
            raise TypeError(f"The function argument {arg} must be of type bool.")

    if not isinstance(fixef_tol, float):
        raise TypeError(
            """The function argument `fixef_tol` needs to be of
            type float.
            """
        )
    if fixef_tol <= 0:
        raise ValueError(
            """
            The function argument `fixef_tol` needs to be of
            strictly larger than 0.
            """
        )
    if fixef_tol >= 1:
        raise ValueError(
            """
            The function argument `fixef_tol` needs to be of
            strictly smaller than 1.
            """
        )

    if weights_type not in ["aweights", "fweights"]:
        raise ValueError(
            f"""
            The `weights_type` argument must be of type `aweights`
            (for analytical / precision weights) or `fweights`
            (for frequency weights) but it is {weights_type}.
            """
        )

    if not isinstance(use_compression, bool):
        raise TypeError("The function argument `use_compression` must be of type bool.")
    if use_compression and weights is not None:
        raise NotImplementedError(
            "Compressed regression is not supported with weights."
        )

    if not isinstance(use_mundlak, bool):
        raise TypeError("The function argument `use_mundlak` must be of type bool.")


def _regression_compression(
    depvars: list[str], covars: list[str], data_long: pl.DataFrame
) -> pl.DataFrame:
    "Compress data for regression based on sufficient statistics."
    aggregate_by = covars

    agg_expressions = []
    agg_expressions.append(pl.count(depvars[0]).alias("count"))
    for var in depvars:
        agg_expressions.append(pl.sum(var).alias(f"sum_{var}"))
        agg_expressions.append(pl.col(var).pow(2).sum().alias(f"sum_{var}_sq"))

    df_compressed = data_long.group_by(aggregate_by).agg(agg_expressions)

    mean_expressions = []
    for var in depvars:
        mean_expressions.append(
            (pl.col(f"sum_{var}") / pl.col("count")).alias(f"mean_{var}")
        )
    df_compressed = df_compressed.with_columns(mean_expressions)

    return df_compressed


def feols_compressed(
    fml,
    data,
    vcov,
    bootstrap=False,
    reps=1000,
    seed=None,
    # ssc = ssc(),
):
    """Run a regression model using sufficient statistics."""
    # data = data.dropna().reset_index(drop = True).copy()

    def _feols_compressed(
        fml, data, vcov, weights=None, weights_type="aweights", **kwargs
    ):
        fml2 = fml.split("~")
        depvar = [fml2[0].replace(" ", "")]
        rhs_fml = fml2[1].replace(" ", "").replace("|", "+")
        rhs_vars = rhs_fml.split("+")

        df_compressed = _regression_compression(
            depvars=depvar, covars=rhs_vars, data_long=pl.DataFrame(data)
        )

        fml_compressed = f"mean_{depvar[0]} ~ {rhs_fml}"

        fit = feols(
            fml=fml_compressed,
            data=df_compressed.to_pandas(),
            vcov=vcov,
            weights="count",
            weights_type="fweights",
            # ssc=ssc,
        )

        fit._depvar = depvar[0]
        fit._covars = rhs_fml

        return fit

    def _vcov_iid(fit):
        yprime = fit._data[f"sum_{fit._depvar}"].to_numpy().reshape(-1, 1)
        yprimeprime = fit._data[f"sum_{fit._depvar}_sq"].to_numpy().reshape(-1, 1)
        weights = fit._weights
        X = fit._X / np.sqrt(fit._weights)
        beta_hat = fit._beta_hat
        yhat = (X @ beta_hat).reshape(-1, 1)
        rss_g = (yhat**2) * weights - 2 * yhat * yprime + yprimeprime
        sigma2 = np.sum(rss_g) / (fit._N - 1)
        return fit._ssc * fit._bread * sigma2

    def _vcov_hetero(fit):
        yprime = fit._data[f"sum_{fit._depvar}"].to_numpy().reshape(-1, 1)
        yprimeprime = fit._data[f"sum_{fit._depvar}_sq"].to_numpy().reshape(-1, 1)
        weights = fit._weights
        X = fit._X / np.sqrt(fit._weights)
        beta_hat = fit._beta_hat
        yhat = (X @ beta_hat).reshape(-1, 1)
        rss_g = (yhat**2) * weights - 2 * yhat * yprime + yprimeprime
        _bread = fit._bread
        _meat = (X * rss_g).T @ X
        return fit._ssc * (_bread @ _meat @ _bread)

    fit = _feols_compressed(fml, data, vcov, ssc=ssc)

    if bootstrap:
        kwargs = {"data": data, "fml": fml}
        fit.bootstrap(
            reps=reps, seed=12, inplace=True, fit_func=_feols_compressed, **kwargs
        )
    else:
        if vcov == "iid":
            fit._vcov = _vcov_iid(fit)
        elif vcov == "hetero":
            fit._vcov = _vcov_hetero(fit)
        else:
            warnings.warn(
                "Analytical standard errors are only available for 'iid' and 'hetero' vcov. Using a clustter bootstrap instead."
            )
            fit.bootstrap(
                reps=reps, seed=seed, inplace=True, fit_func=_feols_compressed, **kwargs
            )

    fit.get_inference()
    return fit


def feols_c(fml, data, vcov, bootstrap=False, reps=1000, seed=None):
    "Shorthand for feols_compressed function."
    return feols_compressed(
        fml=fml, data=data, vcov=vcov, bootstrap=bootstrap, reps=reps, seed=seed
    )
