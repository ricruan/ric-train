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

# 简单一元线性回归类
class SimpleLinearRegression:
    def __init__(self,train_x = None, train_y = None):
        self.slope = None
        self.intercept = None
        self.train_x = train_x
        self.train_y = train_y
        if self.train_x is not None and self.train_y is not None:
            self.fit(train_x,train_y)

    def fit(self, x, y):
        """
        拟合
        使用最小二乘法拟合 y = slope * x + intercept
        """
        self.train_x = x
        self.train_y = y
        x_mean = np.mean(x)
        y_mean = np.mean(y)

        # 计算斜率 (slope)
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        self.slope = numerator / denominator

        # 计算截距 (intercept)
        self.intercept = y_mean - self.slope * x_mean

    def predict(self, x):
        """
        预测
        :param x: 自变量
        :return: 预测值
        """
        if self.slope is None or self.intercept is None:
            raise ValueError("请先调用 fit 方法进行拟合")
        if isinstance(x, list):
            x = np.array(x).flatten()
        self.log_info()
        pred = self.slope * x + self.intercept
        return pred

    def log_info(self):
        logger.info(f"LR模型拟合的斜率（slope）: {self.slope:.2f}")
        logger.info(f"LR模型拟合的截距（intercept）: {self.intercept:.2f}")

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

    def statistics_info(self,y_true,y_pred):
        r2 = r2_score(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        logger.info(f'\nR²（决定系数，R-squared）为：{r2:.3f} [表示模型能解释的因变量变异比例  范围：0 到 1（越大越好）]\n')
        logger.info(f"\nRMSE: {rmse:.3f} 对均方误差开根， 均方根误差 ，单位与原始因变量一致\n")
        logger.info(f"\nMAE: {mae:.3f} 平均绝对误差   相较于均方误差 对极端值不敏感 \n")
        pass



class SklearnLR():
    pass



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    student_dataset = DataSetModel().read_csv(file_path='../DataSet/Student_Performance.csv', pred_key='Performance Index',
                                  split_ratio=[0.1, 0.1],
                                  text_2_num_mapping={'Extracurricular Activities': {'Yes': 1, 'No': 0}})
    lr = SimpleLinearRegression(train_x = student_ds.train_x, train_y= student_ds.train_y)
    pred_value = lr.predict([item[0] for item in student_dataset.valid_x])
    # lr.draw_picture()
    lr.statistics_info(student_dataset.valid_y,pred_value)
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