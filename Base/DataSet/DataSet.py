from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


@dataclass
class DataSetModel:
    train_x: np.ndarray = None
    train_y: np.ndarray = None
    valid_x: np.ndarray = None
    valid_y: np.ndarray = None
    test_x: np.ndarray = None
    test_y: np.ndarray = None
    type: str = None

    @staticmethod
    def get_instance():
        return DataSetModel

    @staticmethod
    @lru_cache
    def get_random_liner_regression_ds(seed: int = None,
                                       x_samples: int = 100,
                                       x_features: int = 1,
                                       x_power: int = 10,
                                       slope: float = 2.5,
                                       ):
        """
        构造一个随机数组成的一元线性回归数据集
         y = slope * x + 1.0 + noise
        :param seed: 随机数种子
        :param x_samples: 样本数
        :param x_features: 特征数
        :param x_power: 数值倍率  随机数*该倍率
        :param slope: 斜率
        :return:
        """
        np.random.seed(seed)
        x = np.random.rand(x_samples, x_features) * x_power
        return DataSetModel(train_x=x,
                            train_y=slope * x.flatten() + 1.0 + np.random.randn(100) * 2,
                            type='liner')

    def read_csv(self, file_path: str, pred_key: str, split_ratio=None, text_2_num_mapping: dict = None):
        """
        读取csv
        :param file_path: 文件路径
        :param pred_key: 预测列列名
        :param split_ratio: 验证集 与 测试集 分割比例，为 None 则不分割
        :param text_2_num_mapping: 形如 {'type' : {'yes' : 0 , 'no' : 1}} 将df中的type字段的 yes 转化为 0 no 转化为 1
        :return:
        """
        df = pd.read_csv(file_path)
        if text_2_num_mapping:
            for key, value in text_2_num_mapping.items():
                if key in df.columns:
                    df[key] = df[key].map(value)

        labels = df[[pred_key]].values
        features = df.drop(pred_key, axis=1).values

        if split_ratio:
            split_ratio.extend([0.1,0.1])
            split_ratio = [i if i < 0.5 else 0.1 for i in split_ratio[:2]]
            self.train_y, test_val_df = train_test_split(labels, test_size=split_ratio[0] + split_ratio[1],
                                                         random_state=42)
            self.valid_y, self.test_y = train_test_split(test_val_df,
                                                         test_size=split_ratio[1] / (split_ratio[0] + split_ratio[1]),
                                                         random_state=42)
            self.train_x, features_test_val_df = train_test_split(features, test_size=split_ratio[0] + split_ratio[1],
                                                                  random_state=42)
            self.valid_x, self.test_x = train_test_split(features_test_val_df,
                                                         test_size=split_ratio[1] / (split_ratio[0] + split_ratio[1]),
                                                         random_state=42)
        else:
            self.train_y = labels
            self.train_x = features

        return self


if __name__ == "__main__":
    test = [1, 2, 3, 4, 5]
    # df1 = DataSetModel().read_csv(file_path='../DataSet/Student_Performance.csv', pred_key='Performance Index',
    #                               split_ratio=[0.1, 0.1],
    #                               text_2_num_mapping={'Extracurricular Activities': {'Yes': 1, 'No': 0}})
    print(test[:2])
