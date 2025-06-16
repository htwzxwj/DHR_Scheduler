import numpy as np
from Scheduler import compute_weight

# 基础范围参数 - 所有测试共用
ranges = {
    "mtbf_range": (50, 200),
    "mttr_range": (5, 60),
    "failure_rate_range": (0.01, 0.1),
    "load_range": (0.3, 1.0)
}

# 测试集1: 默认参数
test1 = {
    "name": "默认参数配置",
    "mtbf": 120,
    "mttr": 10,
    "failure_rate": 0.02,
    "heterogeneity": 0.8,
    "load": 0.7,
    "alpha": 0.30,
    "beta": 0.20,
    "gamma": 0.10,
    "delta": 0.25,
    "epsilon": 0.15,
    "kappa": 2.0
}

# 测试集2: 高可靠性权重
test2 = {
    "name": "默认参数配置22",
    "mtbf": 180,
    "mttr": 10,
    "failure_rate": 0.02,
    "heterogeneity": 0.8,
    "load": 0.7,
    "alpha": 0.30,
    "beta": 0.20,
    "gamma": 0.10,
    "delta": 0.25,
    "epsilon": 0.15,
    "kappa": 2.0
}

# 测试集3: 高性能权重
test3 = {
    "name": "高性能权重配置",
    "mtbf": 100,
    "mttr": 15,
    "failure_rate": 0.03,
    "heterogeneity": 0.9,
    "load": 0.4,
    "alpha": 0.10,
    "beta": 0.10,
    "gamma": 0.05,
    "delta": 0.60,  # 增加异构度权重
    "epsilon": 0.15,
    "kappa": 1.5
}

# 测试集4: 负载均衡优先
test4 = {
    "name": "负载均衡优先配置",
    "mtbf": 140,
    "mttr": 20,
    "failure_rate": 0.025,
    "heterogeneity": 0.7,
    "load": 0.8,
    "alpha": 0.15,
    "beta": 0.15,
    "gamma": 0.05,
    "delta": 0.15,
    "epsilon": 0.50,  # 增加负载权重
    "kappa": 3.0
}

# 测试集5: 极端情况测试
test5 = {
    "name": "极端情况测试",
    "mtbf": 55,     # 接近最低值
    "mttr": 55,     # 接近最高值
    "failure_rate": 0.09, # 接近最高故障率
    "heterogeneity": 0.2, # 低异构度
    "load": 0.95,   # 高负载
    "alpha": 0.20,
    "beta": 0.20,
    "gamma": 0.20,
    "delta": 0.20,
    "epsilon": 0.20,
    "kappa": 4.0    # 陡峭的映射曲线
}

# 运行所有测试
test_sets = [test1, test2, test3, test4, test5]

print("权重计算结果比较:\n")
print("-" * 80)
print(f"{'配置名称':<20} {'权重值':<10} {'R_up':<8} {'R_down':<8} {'F':<8} {'H':<8} {'C':<8} {'S':<8}")
print("-" * 80)

for test in test_sets:
    # 创建测试参数的副本，这样我们可以保留原始字典不变
    test_params = test.copy()
    name = test_params.pop("name")
    params = {**test_params, **ranges}
    weight, components = compute_weight(**params)
    
    print(f"{name:<20} {weight:.6f}  {components['R_up']:.4f}  {components['R_down']:.4f}  "
          f"{components['F']:.4f}  {components['H']:.4f}  {components['C']:.4f}  {components['S']:.4f}")

print("-" * 80)
print("\n各配置权重系数:\n")
print("-" * 80)
print(f"{'配置名称':<20} {'alpha':<8} {'beta':<8} {'gamma':<8} {'delta':<8} {'epsilon':<8} {'kappa':<8}")
print("-" * 80)

for test in test_sets:
    print(f"{test['name']:<20} {test['alpha']:.4f}  {test['beta']:.4f}  {test['gamma']:.4f}  "
          f"{test['delta']:.4f}  {test['epsilon']:.4f}  {test['kappa']:.4f}")