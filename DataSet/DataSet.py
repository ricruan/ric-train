from dataclasses import dataclass

import numpy as np


@dataclass
class DataSetModel:
    X: np.ndarray
    Y: np.ndarray
    type: str


    @staticmethod
    def get_random_liner_regression_ds(seed:int = None,
                                       x_samples:int = 100,
                                       x_features:int = 1,
                                       x_power:int = 10,
                                       slope :float = 2.5,
                                       ):
        """
        构造一个随机数组成的线性回归数据集
         y = slope * x + 1.0 + noise
        :param seed: 随机数种子
        :param x_samples: 样本数
        :param x_features: 特征数
        :param x_power: 数值倍率  随机数*该倍率
        :param slope: 斜率
        :return:
        """
        np.random.seed(seed)
        X = np.random.rand(x_samples, x_features) * x_power
        return DataSetModel(X= X,
                       Y= slope * X.flatten() + 1.0 + np.random.randn(100) * 2,
                       type='liner')
