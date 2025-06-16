import numpy as np
import pandas as pd
import argparse
import matplotlib.pyplot as plt

def generate_random_data(n_samples, ranges):
    """
    生成n_samples个随机样本数据，包括输入参数和权重都是随机生成的
    
    参数:
        n_samples: 要生成的样本数
        ranges: 包含每个属性范围的字典
        
    返回:
        包含输入和输出数据的DataFrame
    """
    # 初始化数据字典
    data = {
        'mtbf': np.random.uniform(ranges['mtbf'][0], ranges['mtbf'][1], n_samples),
        'mttr': np.random.uniform(ranges['mttr'][0], ranges['mttr'][1], n_samples),
        'failure_rate': np.random.uniform(ranges['failure_rate'][0], ranges['failure_rate'][1], n_samples),
        'heterogeneity': np.random.uniform(ranges['heterogeneity'][0], ranges['heterogeneity'][1], n_samples),
        'load': np.random.uniform(ranges['load'][0], ranges['load'][1], n_samples),
        'weight': np.random.uniform(ranges['weight'][0], ranges['weight'][1], n_samples)  # 直接随机生成权重
    }
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    return df

def parse_args():
    parser = argparse.ArgumentParser(description='生成随机数据和权重')
    parser.add_argument('--samples', type=int, default=100, help='要生成的样本数量')
    parser.add_argument('--output', type=str, default='weight_data.csv', help='输出CSV文件名')
    parser.add_argument('--plot', action='store_true', default=True, help='是否生成可视化图表')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # 设定各属性的范围
    ranges = {
        'mtbf': [50, 200],         # 平均无故障时间范围
        'mttr': [5, 60],           # 平均修复时间范围
        'failure_rate': [0.01, 0.1], # 故障率范围
        'heterogeneity': [0, 1],    # 异构度范围
        'load': [0.3, 1.0],         # 负载范围
        'weight': [0.7, 1]            # 权重范围
    }
    
    print(f"生成 {args.samples} 个随机样本，参数范围:")
    for k, v in ranges.items():
        print(f"  {k}: {v}")
    
    # 生成数据
    df = generate_random_data(args.samples, ranges)
    
    # 保存到CSV
    df.to_csv(args.output, index=False)
    print(f"数据已保存到 {args.output}")
    
    # 显示基本统计信息
    print("\n生成数据的基本统计信息:")
    print(df.describe())
    
    # 如果需要绘制图表
    if args.plot:
        # 创建一个图形，展示输入与权重的关系
        plt.figure(figsize=(15, 10))
        
        # 绘制各个输入与权重的散点图
        features = ['mtbf', 'mttr', 'failure_rate', 'heterogeneity', 'load']
        for i, feature in enumerate(features):
            plt.subplot(2, 3, i+1)
            plt.scatter(df[feature], df['weight'], alpha=0.6)
            plt.xlabel(feature)
            plt.ylabel('weight')
            plt.title(f'{feature} vs weight')
        
        # 绘制权重分布直方图
        plt.subplot(2, 3, 6)
        plt.hist(df['weight'], bins=20)
        plt.xlabel('Weight')
        plt.ylabel('Frequency')
        plt.title('Weight Distribution')
        
        plt.tight_layout()
        plt.savefig('weight_analysis.png')
        print("已生成分析图表: weight_analysis.png")

if __name__ == "__main__":
    main()