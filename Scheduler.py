import numpy as np

# 归一化函数
def normalize(value, min_val, max_val, reverse=False):
    norm = (value - min_val) / (max_val - min_val + 1e-8)
    return 1 - norm if reverse else norm

# 权重计算函数
def compute_weight(mtbf, mttr, failure_rate, heterogeneity, load,
                   mtbf_range, mttr_range, failure_rate_range, load_range,
                   alpha=0.30, beta=0.20, gamma=0.10, delta=0.25, epsilon=0.15, kappa=2.0):
    """
    计算执行体的0-1连续权重分数

    参数：
        mtbf: 平均无故障时间
        mttr: 平均修复时间
        failure_rate: 故障率
        heterogeneity: 异构度 (0-1)
        load: 当前负载（0表示依赖低，1表示依赖高）
        *_range: 每个指标的归一化区间 (min, max)
        alpha~epsilon: 五个维度的权重系数
        kappa: 控制输出映射曲线形状的指数

    返回：
        weight: 0-1连续权重
        components: 中间指标值，用于调试或展示
    """
    # 步骤1：归一化每项
    R_up = normalize(mtbf, *mtbf_range)
    R_down = normalize(mttr, *mttr_range, reverse=True)
    F = normalize(failure_rate, *failure_rate_range, reverse=True)
    H = heterogeneity  # 已归一化
    C = normalize(load, *load_range, reverse=True)

    # 步骤2：线性组合
    S = alpha * R_up + beta * R_down + gamma * F + delta * H + epsilon * C

    # 步骤3：非线性映射为权重
    weight = (1 - np.exp(-kappa * S)) / (1 - np.exp(-kappa))

    return weight, {
        "R_up": R_up,
        "R_down": R_down,
        "F": F,
        "H": H,
        "C": C,
        "S": S
    }

# 示例用法
if __name__ == "__main__":
    sample_params = {
        "mtbf": 120,  # 小时
        "mttr": 10,   # 分钟
        "failure_rate": 0.02,
        "heterogeneity": 0.8,
        "load": 0.7,
        "mtbf_range": (50, 200),
        "mttr_range": (5, 60),
        "failure_rate_range": (0.01, 0.1),
        "load_range": (0.3, 1.0)
    }

    weight, components = compute_weight(**sample_params)
    print("Final weight:", weight)
    print("Component scores:", components)
