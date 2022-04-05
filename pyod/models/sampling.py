# -*- coding: utf-8 -*-
"""Outlier detection based on Sampling (SP)
"""
# Author: Akira Tamamori <tamamori5917@gmail.com>
# License: BSD 2 clause

from __future__ import division, print_function

import numpy as np
from sklearn.neighbors import DistanceMetric
from sklearn.utils import check_array, check_random_state
from sklearn.utils.validation import check_is_fitted

from .base import BaseDetector


class Sampling(BaseDetector):
    """Sampling class for outlier detection.

    Sugiyama, M., Borgwardt, K. M.: Rapid Distance-Based Outlier Detection via
    Sampling, Advances in Neural Information Processing Systems (NIPS 2013),
    467-475, 2013.

    Parameters
    ----------
    contamination : float in (0., 0.5), optional (default=0.1)
        The amount of contamination of the data set,
        i.e. the proportion of outliers in the data set. Used when fitting to
        define the threshold on the decision function.

    subset_size : float in (0., 1.0) or int (0, n_samples), optional (default=20)
        The size of subset of the data set.
        Sampling subset from the data set is performed only once.

    metric : string or callable, default 'minkowski'
        metric to use for distance computation. Any metric from scikit-learn
        or scipy.spatial.distance can be used.

        If metric is a callable function, it is called on each
        pair of instances (rows) and the resulting value recorded. The callable
        should take two arrays as input and return one value indicating the
        distance between them. This works for Scipy's metrics, but is less
        efficient than passing the metric name as a string.

        Distance matrices are not supported.

        Valid values for metric are:

        - from scikit-learn: ['cityblock', 'cosine', 'euclidean', 'l1', 'l2',
          'manhattan']

        - from scipy.spatial.distance: ['braycurtis', 'canberra', 'chebyshev',
          'correlation', 'dice', 'hamming', 'jaccard', 'kulsinski',
          'mahalanobis', 'matching', 'minkowski', 'rogerstanimoto',
          'russellrao', 'seuclidean', 'sokalmichener', 'sokalsneath',
          'sqeuclidean', 'yule']

        See the documentation for scipy.spatial.distance for details on these
        metrics.

    metric_params : dict, optional (default = None)
        Additional keyword arguments for the metric function.

    random_state : int, RandomState instance or None, optional (default None)
        If int, random_state is the seed used by the random number generator;
        If RandomState instance, random_state is the random number generator;
        If None, the random number generator is the RandomState instance used
        by `np.random`.

    Attributes
    ----------
    decision_scores_ : numpy array of shape (n_samples,)
        The outlier scores of the training data.
        The higher, the more abnormal. Outliers tend to have higher
        scores. This value is available once the detector is
        fitted.

    threshold_ : float
        The threshold is based on ``contamination``. It is the
        ``n_samples * contamination`` most abnormal samples in
        ``decision_scores_``. The threshold is calculated for generating
        binary outlier labels.

    labels_ : int, either 0 or 1
        The binary labels of the training data. 0 stands for inliers
        and 1 for outliers/anomalies. It is generated by applying
        ``threshold_`` on ``decision_scores_``.
    """

    def __init__(
        self,
        contamination=0.1,
        subset_size=20,
        metric="minkowski",
        metric_params=None,
        random_state=None,
    ):
        super().__init__(contamination=contamination)
        self.subset_size = subset_size
        self.metric = metric
        self.metric_params = metric_params
        self.random_state = check_random_state(random_state)
        self.dist = None
        self.subset = None
        self.decision_scores_ = None

    def fit(self, X, y=None):
        """Fit detector. y is ignored in unsupervised methods.

        Parameters
        ----------
        X : numpy array of shape (n_samples, n_features)
            The input samples.

        y : Ignored
            Not used, present for API consistency by convention.

        Returns
        -------
        self : object
            Fitted estimator.
        """

        # validate inputs X and y (optional)
        X = check_array(X)
        self._set_n_classes(y)

        n_samples, _ = X.shape
        if (isinstance(self.subset_size, int) is True) and (
            not 0 <= self.subset_size <= n_samples
        ):
            raise ValueError(
                "subset_size=%r must be between 0 and n_samples=%r."
                % (self.subset_size, n_samples)
            )
        if isinstance(self.subset_size, float) is True:
            if 0.0 < self.subset_size <= 1.0:
                self.subset_size = int(self.subset_size * n_samples)
            else:
                raise ValueError("subset_size=%r must be between 0.0 and 1.0")

        random_indices = self.random_state.choice(
            n_samples,
            size=self.subset_size,
            replace=False,
        )
        self.subset = X[random_indices, :]

        if self.metric_params is None:
            self.dist = DistanceMetric.get_metric(self.metric)
        else:
            self.dist = DistanceMetric.get_metric(self.metric, *self.metric_params)

        pair_dist = self.dist.pairwise(X, self.subset)
        anomaly_scores = np.min(pair_dist, axis=1)

        self.decision_scores_ = anomaly_scores
        self._process_decision_scores()

        return self

    def decision_function(self, X):
        """Predict raw anomaly score of X using the fitted detector.

        The anomaly score of an input sample is computed based on different
        detector algorithms. For consistency, outliers are assigned with
        larger anomaly scores.

        Parameters
        ----------
        X : numpy array of shape (n_samples, n_features)
            The test input samples.

        Returns
        -------
        anomaly_scores : numpy array of shape (n_samples,)
            The anomaly score of the input samples.
        """
        check_is_fitted(self, ["decision_scores_", "threshold_", "labels_"])

        X = check_array(X)

        pair_dist = self.dist.pairwise(X, self.subset)
        anomaly_scores = np.min(pair_dist, axis=1)

        return anomaly_scores
