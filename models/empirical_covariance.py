import mlflow.pyfunc
import numpy as np
from mlflow.pyfunc import PythonModel
from sklearn.covariance import EmpiricalCovariance as _EC

class EmpiricalCovarianceModel(PythonModel):
    """
    A combined MLflow pyfunc model that fits an empirical covariance and predicts
    repeated covariance matrices per input row.

    Usage:
        model = EmpiricalCovarianceModel().fit(X)
        mlflow.pyfunc.log_model(
            artifact_path="emp_cov_model",
            python_model=model,
            registered_model_name="EmpiricalCovarianceModel"
        )
    """
    def __init__(self):
        # PythonModel has its own initializer
        super().__init__()
        self._cov = None

    def fit(self, X, y=None):
        # Accept DataFrame or numpy array
        arr = X.values if hasattr(X, "values") else np.asarray(X)
        ec = _EC().fit(arr)
        self._cov = ec.covariance_
        return self

    def predict(self, context, model_input):
        # Accept DataFrame or numpy array
        arr = model_input.values if hasattr(model_input, "values") else np.asarray(model_input)
        m, n = arr.shape
        return np.repeat(self._cov[np.newaxis, :, :], repeats=m, axis=0)
