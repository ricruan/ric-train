import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import statsmodels.api as sm

from DataSet.DataSet import DataSetModel

logger = logging.getLogger(__name__)

# 获取随机数据集
random_ds = DataSetModel.get_random_liner_regression_ds(seed=47)


# 线性回归类
class OriginLinearRegression:
    def __init__(self, train_x=None, train_y=None):
        self.sk_model = None
        self.slope = None
        self.const = None
        self.train_x = train_x
        self.train_y = train_y
        if self.train_x is not None and self.train_y is not None:
            self.fit(train_x, train_y)

    def fit(self, x, y):
        self._fit(x, y)
        self._fit_statsmodels()

    def _fit(self, x, y):
        """
        拟合线性回归模型（支持一元和多元）

        参数:
            x: array-like, shape (n_samples,) 或 (n_samples, n_features)
            y: array-like, shape (n_samples,)
        """
        # 转换为 NumPy 数组
        x = np.asarray(x)
        y = np.asarray(y)

        # 保存原始训练数据
        self.train_x = x.copy()
        self.train_y = y.copy()

        # 如果 x 是一维的（一元回归），reshape 为 (n_samples, 1)
        if x.ndim == 1:
            x = x.reshape(-1, 1)  # 变成列向量

        # 获取样本数和特征数
        n_samples, n_features = x.shape

        # 添加截距项：在 X 前面加一列 1
        X = np.hstack([np.ones((n_samples, 1)), x])  # shape: (n_samples, n_features + 1)

        # 使用正规方程求解：beta = (X^T X)^{-1} X^T y
        # 更稳定的做法是使用 np.linalg.lstsq（推荐）
        try:
            beta, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
        except np.linalg.LinAlgError:
            raise ValueError("矩阵不可逆，可能存在多重共线性或特征数大于样本数")

        # 分离截距和系数
        self.const = beta[0]
        self.slope = beta[1:]  # 对一元回归，这是标量；对多元，是数组

    def predict(self, x):
        """
        预测（支持一元和多元）
        """
        if self.slope is None or self.const is None:
            raise ValueError("请先调用 fit 方法进行拟合")

        x = np.asarray(x)

        # 确保 slope 是一维数组
        slope = np.atleast_1d(self.slope)  # 即使是 float 也会转成 array
        n_features = slope.shape[0]

        # 标准化输入 x 的形状
        if x.ndim == 0:
            x = x.reshape(1, -1)  # 标量 → (1, 1)
        elif x.ndim == 1:
            if x.shape[0] == n_features:
                x = x.reshape(1, -1)  # 单样本 → (1, n_features)
            else:
                # 可能是一元回归且输入多个样本（如 [1,2,3]）
                if n_features == 1:
                    x = x.reshape(-1, 1)
                else:
                    raise ValueError(f"输入维度 {x.shape} 与特征数 {n_features} 不匹配")
        # x.ndim == 2: 保持原样

        if x.shape[1] != n_features:
            raise ValueError(f"输入特征维度 {x.shape[1]} != 模型特征数 {n_features}")

        # 统一预测：矩阵乘法 + 截距
        pred = x @ slope + self.const

        self.log_info()
        return pred.ravel()  # 如果是单样本，返回标量或一维数组

    def log_info(self):
        # 处理 slope：统一转为 NumPy 数组以便判断
        slope = np.asarray(self.slope)

        if slope.ndim == 0 or slope.size == 1:
            # 一元回归：显示为标量
            slope_str = f"{slope.item():.2f}"
        else:
            # 多元回归：显示为列表或数组格式，保留两位小数
            slope_str = "[" + ", ".join(f"{s:.2f}" for s in slope.flatten()) + "]"

        logger.info(f"LR模型拟合的斜率（slope）: {slope_str}")
        # todo 截距这里改一下
        logger.info(f"LR模型拟合的截距（intercept）: {str(self.const)}")

    def draw_picture(self):
        """
        绘图 可视化展示
        :return:
        """
        if self.slope.size == 1:
            plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
            plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
            plt.scatter(self.train_x, self.train_y, color='blue', label='真实数据')
            plt.plot(self.train_x, self.predict(self.train_x), color='red', label='手撕拟合直线')
            plt.xlabel('X')
            plt.ylabel('y')
            plt.legend()
            plt.title('简单线性回归')
            plt.show()
        else:
            # TODO 绘制多元线性回归图 (二元可绘制， 多于二元将无法绘制)
            pass

    @staticmethod
    def statistics_info(y_true, y_pred):
        """
        模型预测评判信息打印
        :param y_true:
        :param y_pred:
        :return:
        """
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        logger.info(f"\nRMSE: {rmse:.3f} [均方根误差 ，单位与原始因变量一致]\n")
        logger.info(f"\nMAE: {mae:.3f} [平均绝对误差   相较于均方误差 对极端值不敏感] \n")
        pass

    def _fit_statsmodels(self):
        """
        打印统计推断评判信息
        :return:
        """
        x_with_const = sm.add_constant(self.train_x)
        self.sm_model = sm.OLS(self.train_y, x_with_const).fit()
        # 解读 summary() 打印的内容
        # https://yuanbao.tencent.com/bot/app/share/chat/0qQsg8TcWht5
        logger.info(self.sm_model.summary())
        pass


class SklearnLR(OriginLinearRegression):
    """
    基于 Sklearn 实现的 LR
    """

    def _fit(self, x, y):
        skl_model_mul = LinearRegression()
        skl_model_mul.fit(self.train_x, self.train_y)
        self.sk_model = skl_model_mul
        self.slope = skl_model_mul.coef_
        self.const = skl_model_mul.intercept_

    def predict(self, x):
        return self.sk_model.predict(x)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    student_dataset = DataSetModel().read_csv(file_path='../DataSet/Student_Performance.csv',
                                              pred_key='Performance Index',
                                              split_ratio=[0.1, 0.1],
                                              text_2_num_mapping={'Extracurricular Activities': {'Yes': 1, 'No': 0}})
    lr = SklearnLR(train_x=student_dataset.train_x, train_y=student_dataset.train_y)
    pred_value = lr.predict(student_dataset.valid_x)
    pred_test_value = lr.predict(student_dataset.test_x)
    lr.draw_picture()
    pass
