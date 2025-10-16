import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.linear_model import LinearRegression

from DataSet.DataSet import DataSetModel

plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False    # 用来正常显示负号
# 获取随机数据集
random_ds = DataSetModel.get_random_liner_regression_ds(seed=47)

# 数据集数据
df = pd.read_csv('../DataSet/Student_Performance.csv')
# 将 "Yes"/"No" 转为 1/0
df['Extracurricular Activities'] = df['Extracurricular Activities'].map({'Yes': 1, 'No': 0})

student_ds = DataSetModel(X= df[['Hours Studied']].values,Y= df[['Performance Index']].values,type='liner')
student_ds_multi = DataSetModel(X= df.drop('Performance Index', axis=1).values,Y= df[['Performance Index']].values,type='liner')
print(1)

# 简单一元线性回归类
class SimpleUnitaryLinearRegression:
    def __init__(self):
        self.slope = None
        self.intercept = None

    def fit(self, X, y):
        """
        使用最小二乘法拟合 y = slope * x + intercept
        """
        x_mean = np.mean(X)
        y_mean = np.mean(y)

        # 计算斜率 (slope)
        numerator = np.sum((X - x_mean) * (y - y_mean))
        denominator = np.sum((X - x_mean) ** 2)
        self.slope = numerator / denominator

        # 计算截距 (intercept)
        self.intercept = y_mean - self.slope * x_mean

    def predict(self, X, y = None):
        if self.slope is None or self.intercept is None:
            raise ValueError("请先调用 fit 方法进行拟合")
        return self.slope * X + self.intercept





if __name__ == '__main__':
    #  自建随机数据集 random_ds   真实数据集 student_ds
    x = student_ds.X
    y = student_ds.Y

    # 待预测值
    predict_value = 14
    student_test_data = [[12,56,0,9,12]] # 学习时间、以前的分数、课外活动、睡眠时间、练习的样卷、成绩指数

    # 手撕 一元线性回归模型
    model = SimpleUnitaryLinearRegression()
    model.fit(x.flatten(),y.flatten())
    y_pred = model.predict(x.flatten())
    # 框架 一元线性回归模型
    skl_model = LinearRegression()
    skl_model.fit(x, y)
    y_pred_skl = skl_model.predict(x)
    # 框架 多元线性回归模型
    skl_model_mul = LinearRegression()
    skl_model_mul.fit(student_ds_multi.X,student_ds_multi.Y)
    y_pred_skl_mul = skl_model_mul.predict(student_test_data)

    # 输出结果
    print(f"手撕 拟合的斜率（slope）: {model.slope:.2f}")
    print(f"手撕 拟合的截距（intercept）: {model.intercept:.2f}")
    print(f"手撕 预测 {predict_value} 的值: {model.predict(predict_value):.2f}")

    print(f"框架 拟合的斜率（slope）: {skl_model.coef_[0]}")
    print(f"框架 拟合的截距（intercept）: {skl_model.intercept_}")
    print(f"框架 预测 {predict_value} 的值: {skl_model.predict([[predict_value]])}")

    print(f"多元预测值 {student_test_data} 的值： {y_pred_skl_mul} ")

    # 可视化
    plt.scatter(x, y, color='blue', label='真实数据')
    plt.plot(x, y_pred, color='red', label='手撕拟合直线')
    plt.plot(x, y_pred_skl, color='green', label='框架拟合直线')
    # plt.plot(x, y_pred_skl_mul, color='yellow', label='框架多元拟合直线')
    plt.xlabel('X')
    plt.ylabel('y')
    plt.legend()
    plt.title('简单线性回归')
    plt.show()