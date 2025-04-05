import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.express as px
import folium
from pandasql import sqldf

# 设定sns风格和DataFrame最大显示列数
sns.set(style="whitegrid")
pd.set_option("display.max_columns", 36)
# 设置中文字体（黑体）
plt.rcParams['font.sans-serif'] = ['SimHei']

# 1. 数据加载与初步探索
df = pd.read_csv('hotel_bookings.csv')
print("数据大小:", df.shape)
print("\n前3行数据示例:\n", df.head(3))
print("\n缺失值统计:\n", df.isnull().sum())
# 得出children,country,agent,company四个字段含有缺失项
# agent一栏若是缺失的，那么这个订单很可能没有代理。
# company一栏若是缺失的，可能是私人预订。

# 2. 数据清洗

# 替换缺失值
# 构造映射字典
nan_replacements = {"children": 0.0, "country": "Unknown", "agent": 0, "company": 0}
# 替换缺失项得到新数据
df_cln = df.fillna(nan_replacements)

# 替换df_cln中不规范值
# meal字段包含'Undefined'意味着自带食物SC
df_cln["meal"].replace("Undefined", "SC", inplace=True)
# 取得入住人数为0的行号,将这些行在df_cln中删除
zero_guests = list(df_cln.loc[df_cln["adults"]
                              + df_cln["children"]
                              + df_cln["babies"] == 0].index)
df_cln.drop(df_cln.index[zero_guests], inplace=True)
# 查看清洗后的数据大小：
print('\n清洗后的数据大小：\n',df_cln.shape)

# 3. 核心分析
# 分析1：整体取消率
cancel_rate = df_cln['is_canceled'].mean()
print(f"\n整体订单取消率: {cancel_rate:.2%}")

# 分析2：不同客户类型的取消率对比（SQL）
sql = """
SELECT customer_type,
       hotel,
       COUNT(*) AS total,
       SUM(is_canceled) AS canceled_bookings,
       SUM(is_canceled)*1.0 / COUNT(*) AS cancel_rate
FROM df
GROUP BY customer_type
"""
cancel_by_customer_type = sqldf(sql, locals())

print("\n不同客户类型取消率:\n", cancel_by_customer_type)

# 分析3：提前预订天数与取消率的关系
plt.figure(figsize=(10, 6))
sns.boxplot(x='is_canceled', y='lead_time', data=df_cln)
plt.title('提前预订天数 vs 订单取消情况')
plt.xlabel('是否取消订单（0=未取消，1=取消）')
plt.ylabel('提前预订天数')
plt.show()

# 分析4：城市酒店 vs 度假酒店月度入住量对比
monthly_data = df_cln.groupby(['arrival_date_month', 'hotel']).size().unstack()
# 处理月份排序
month_order = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
monthly_data = monthly_data.reindex(month_order)

year_factors = monthly_data.index.to_series().isin(['July', 'August']).replace({True: 3, False: 2})
monthly_data = monthly_data.div(year_factors, axis=0)

plot_data = monthly_data.reset_index().melt(
    id_vars='arrival_date_month',
    value_name='guests',
    var_name='hotel_type'
)

plt.figure(figsize=(12, 6))
sns.lineplot(
    x='arrival_date_month',
    y='guests',
    hue='hotel_type',
    data=plot_data,
    marker='o',
    palette=['#1f77b4', '#ff7f0e']
)
plt.title('月度平均客流量对比（城市酒店 vs 度假酒店）')
plt.xlabel('月份')
plt.ylabel('预订量')
plt.xticks(rotation=45)
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()


# 4. 业务建议总结
print("""
1. 合同(Contract)订单和短期(Transient)订单取消率高，建议对这两类客户收取定金降低风险；
2. 提前预订超过100天的订单取消率显著上升，可设置阶梯式退改政策；
3. 城市酒店在春季和秋季客人较多，度假酒店在六月到九月人数较少，在冬季两家酒店的客人最少。
""")
