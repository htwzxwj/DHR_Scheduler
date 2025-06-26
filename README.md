# DHR_Scheduler 仿真平台

<p align="center">
   <img src="assets/logo.png" alt="DHR_Scheduler Logo" width="500"/>
</p>

## 项目简介
本项目用于仿真和对比分布式冗余容错系统（DHR, Distributed Heterogeneous Redundancy）在面对攻击时的鲁棒性表现。支持自适应融合系统（FusionSystem）与静态冗余系统（vanilleDHR）两种典型架构。

## 主要功能
- 支持多执行体的攻击仿真与融合决策
- 支持自适应权重调整、软下线、全体替换等机制
- 支持多轮攻击、攻击概率、恢复机制等参数配置
- 自动统计各系统输出准确率、调度次数等性能指标
- 日志详细记录每轮仿真过程

## 目录结构
```
├── main.py                # 主仿真入口，包含实验主循环
├── FusionSystem.py        # 自适应融合系统实现
├── VanilleDHR.py          # 静态冗余系统实现
├── AttackSignalGenerator.py # 攻击信号生成器
├── logger_config.py       # 日志配置
├── logs/                  # 仿真日志输出目录
└── README.md              # 项目说明
```

## 快速开始
1. 安装依赖（如有）：
   ```bash
   pip install scipy
   ```
2. 运行主仿真：
   ```bash
   python main.py
   ```
3. 查看日志输出和统计结果。

## 主要参数说明
- `NUM_UNITS`：执行体数量
- `NUM_ROUNDS`：仿真轮数
- `ATTACK_PROB`：每轮攻击概率
- `recoverTime`：调度后恢复等待时间

## 输出指标
- 各系统输出A/B次数与准确率
- 各系统调度（全体替换）次数
- 各执行体权重变化
- 日志详细记录每轮输出与状态

## 典型用法
- 对比 FusionSystem 与 vanilleDHR 在不同攻击概率、恢复时间等参数下的鲁棒性表现
- 分析自适应机制对系统性能的提升作用

## 联系方式
如有问题或建议，请联系项目维护者。
