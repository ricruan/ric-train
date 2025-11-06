import logging

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from numpy import ndarray
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

from DataSet.DataSet import DataSetModel

logger = logging.getLogger(__name__)

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False    # 用来正常显示负号
# 获取随机数据集
random_ds = DataSetModel.get_random_liner_regression_ds(seed=47)

# 数据集数据
df = pd.read_csv('../DataSet/Student_Performance.csv')
# 将 "Yes"/"No" 转为 1/0
df['Extracurricular Activities'] = df['Extracurricular Activities'].map({'Yes': 1, 'No': 0})

student_ds = DataSetModel(train_x= df[['Hours Studied']].values, train_y= df[['Performance Index']].values, type='liner')
student_ds_multi = DataSetModel(train_x= df[:-100].drop('Performance Index', axis=1).values, train_y= df[:-100][['Performance Index']].values, type='liner')
print(1)

# 线性回归类
class OriginLinearRegression:
    def __init__(self,train_x = None, train_y = None):
        self.slope = None
        self.intercept = None
        self.train_x = train_x
        self.train_y = train_y
        if self.train_x is not None and self.train_y is not None:
            self.fit(train_x,train_y)

    def fit(self, x, y):
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
        self.intercept = beta[0]
        self.slope = beta[1:]  # 对一元回归，这是标量；对多元，是数组

    def predict(self, x):
        """
        预测（支持一元和多元）
        """
        if self.slope is None or self.intercept is None:
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
        pred = x @ slope + self.intercept

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
        logger.info(f"LR模型拟合的截距（intercept）: {str(self.intercept)}")

    def draw_picture(self):
        """
        绘图 可视化展示
        :return:
        """
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
        plt.scatter(self.train_x, self.train_y, color='blue', label='真实数据')
        plt.plot(self.train_x, self.predict(self.train_x), color='red', label='手撕拟合直线')
        plt.xlabel('X')
        plt.ylabel('y')
        plt.legend()
        plt.title('简单线性回归')
        plt.show()

    @staticmethod
    def statistics_info(y_true,y_pred):
        r2 = r2_score(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        logger.info(f'\nR²（决定系数，R-squared）为：{r2:.3f} [表示模型能解释的因变量变异比例  范围：0 到 1（越大越好）]\n')
        logger.info(f"\nRMSE: {rmse:.3f} [对均方误差开根， 均方根误差 ，单位与原始因变量一致]\n")
        logger.info(f"\nMAE: {mae:.3f} [平均绝对误差   相较于均方误差 对极端值不敏感] \n")
        pass



class SklearnLR(OriginLinearRegression):
    pass



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    student_dataset = DataSetModel().read_csv(file_path='../DataSet/Student_Performance.csv', pred_key='Performance Index',
                                  split_ratio=[0.1, 0.1],
                                  text_2_num_mapping={'Extracurricular Activities': {'Yes': 1, 'No': 0}})
    lr = OriginLinearRegression(train_x = student_dataset.train_x, train_y= student_dataset.train_y)
    pred_value = lr.predict(student_dataset.valid_x)
    pred_test_value = lr.predict(student_dataset.test_x)
    # lr.draw_picture()
    lr.statistics_info(student_dataset.valid_y,pred_value)
    lr.statistics_info(student_dataset.test_y,pred_test_value)
    pass
    # #  自建随机数据集 random_ds   真实数据集 student_ds
    # x = student_ds.X
    # y = student_ds.Y
    #
    # # 待预测值
    # predict_value = 14
    # student_test_data = [[12,56,0,9,12]] # 学习时间、以前的分数、课外活动、睡眠时间、练习的样卷、成绩指数
    # # 验证集
    # student_valid_data = df[-100:].drop('Performance Index', axis=1).values
    # student_valid_result = df[-100:][['Performance Index']].values
    #
    # # 手撕 一元线性回归模型
    # model = SimpleUnitaryLinearRegression()
    # model.fit(x.flatten(),y.flatten())
    # y_pred = model.predict(x.flatten())
    # # 框架 一元线性回归模型
    # skl_model = LinearRegression()
    # skl_model.fit(x, y)
    # y_pred_skl = skl_model.predict(x)
    # # 框架 多元线性回归模型
    # skl_model_mul = LinearRegression()
    # skl_model_mul.fit(student_ds_multi.X,student_ds_multi.Y)
    # y_pred_skl_mul = skl_model_mul.predict(student_valid_data)
    # # 合并验证结果和预测结果并打印
    # r2 = r2_score(student_valid_result, y_pred_skl_mul)
    # rmse = np.sqrt(mean_squared_error(student_valid_result, y_pred_skl_mul))
    # mae = mean_absolute_error(student_valid_result, y_pred_skl_mul)
    # # R²（决定系数，R-squared）  表示模型能解释的因变量变异比例  范围：0 到 1（越大越好）
    # print(f"R²: {r2:.3f}")
    # # 对均方误差开根， 均方根误差 ，单位与原始因变量一致，例如，此处为平均误差为2.1分左右
    # print(f"RMSE: {rmse:.3f}")
    # # 平均绝对误差   相较于均方误差 对极端值不敏感
    # print(f"MAE: {mae:.3f}")
    #
    # # 输出结果
    # print(f"手撕 拟合的斜率（slope）: {model.slope:.2f}")
    # print(f"手撕 拟合的截距（intercept）: {model.intercept:.2f}")
    # print(f"手撕 预测 {predict_value} 的值: {model.predict(predict_value):.2f}")
    #
    # print(f"框架 拟合的斜率（slope）: {skl_model.coef_[0]}")
    # print(f"框架 拟合的截距（intercept）: {skl_model.intercept_}")
    # print(f"框架 预测 {predict_value} 的值: {skl_model.predict([[predict_value]])}")
    #
    # # print(f"多元预测值 {student_test_data} 的值： {y_pred_skl_mul} ")
    #
    # # 可视化
    # plt.scatter(x, y, color='blue', label='真实数据')
    # plt.plot(x, y_pred, color='red', label='手撕拟合直线')
    # plt.plot(x, y_pred_skl, color='green', label='框架拟合直线')
    # plt.xlabel('X')
    # plt.ylabel('y')
    # plt.legend()
    # plt.title('简单线性回归')
    # plt.show()