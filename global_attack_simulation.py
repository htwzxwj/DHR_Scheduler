"""
全局攻击模拟 - 攻击会影响所有执行体
"""

import random
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from AttackSimulation import Executor, create_sample_executors

# === 全局变量定义 ===
CORRECT_SIGNAL = "正常"   # 正确信号
ERROR_SIGNAL = "异常"     # 错误信号

# 为Executor类扩展generate_output方法
def generate_output(executor):
    """生成执行体的输出信号
    
    Args:
        executor: 执行体实例
        
    Returns:
        输出信号: CORRECT_SIGNAL或ERROR_SIGNAL
    """
    if executor.is_compromised:
        return ERROR_SIGNAL
    else:
        return CORRECT_SIGNAL


class GlobalAttackSimulator:
    """全局攻击模拟器 - 每次攻击会影响所有执行体"""
    
    def __init__(self, executors: List[Executor]):
        self.executors = executors
        self.attack_history = []
        self.simulation_rounds = 0
        
    def generate_attack_strength(self, min_strength: float = 0.1, max_strength: float = 1.0) -> float:
        """生成攻击强度"""
        return random.uniform(min_strength, max_strength)
            
    def simulate_global_attack(self, attack_strength=None) -> Dict:
        """模拟全局攻击，攻击会影响所有执行体
        
        Args:
            attack_strength: 固定攻击强度，若不提供则随机生成
            
        Returns:
            攻击结果字典，包含攻击详情
        """
        # 如果未提供攻击强度，则随机生成
        if attack_strength is None:
            attack_strength = self.generate_attack_strength()
        
        # 记录攻击结果
        attack_result = {
            "round": self.simulation_rounds,
            "attack_strength": attack_strength,
            "targets": [],
            "successful_attacks": 0,
            "total_attacks": 0,
            "compromised_count": 0
        }
        
        # 对每个未被攻陷的执行体进行攻击
        for executor in [e for e in self.executors if not e.is_compromised]:
            # 判断攻击是否成功
            attack_success = attack_strength > executor.defense_threshold
            
            # 应用攻击效果
            executor.attack_count += 1
            attack_result["total_attacks"] += 1
            
            # 记录攻击前的状态
            was_compromised = executor.is_compromised
            
            # 如果攻击成功，执行体被攻陷
            if attack_success:
                executor.successful_attacks += 1
                attack_result["successful_attacks"] += 1
                executor.is_compromised = True
            
            # 记录攻击后的状态
            became_compromised = executor.is_compromised and not was_compromised
            if became_compromised:
                attack_result["compromised_count"] += 1
            
            # 添加本次攻击记录
            target_result = {
                "executor_id": executor.id,
                "defense_threshold": executor.defense_threshold,
                "attack_success": attack_success,
                "status": "Compromised" if became_compromised else ("Safe" if not attack_success else "Success"),
                "became_compromised": became_compromised
            }
            
            attack_result["targets"].append(target_result)
        
        self.attack_history.append(attack_result)
        return attack_result
        
    def simulate_global_attack_rounds(self, num_rounds: int, min_strength: float = 0.2, max_strength: float = 0.9) -> List[Dict]:
        """模拟多轮全局攻击
        
        Args:
            num_rounds: 攻击轮数
            min_strength: 最小攻击强度
            max_strength: 最大攻击强度
            
        Returns:
            所有攻击结果列表
        """
        results = []
        
        for round_num in range(num_rounds):
            self.simulation_rounds = round_num + 1
            
            # ! 生成本轮攻击的强度
            attack_strength = random.uniform(min_strength, max_strength)
            
            # 执行全局攻击
            result = self.simulate_global_attack(attack_strength)
            results.append(result)
            
            # 打印本轮攻击结果
            print(f"\nGlobal Attack Round {round_num + 1}")
            print(f"Attack Strength: {attack_strength:.3f}")
            print(f"Success Rate: {result['successful_attacks']}/{result['total_attacks']} ({result['successful_attacks']/max(1, result['total_attacks']):.2%})")
            
            if result['compromised_count'] > 0:
                print(f"Newly Compromised Executors: {result['compromised_count']}")
                
            # 显示当前各执行体状态
            active_executors = [e for e in self.executors if not e.is_compromised]
            print(f"Active Executors: {len(active_executors)}/{len(self.executors)}")
            
            # 检查是否所有执行体都被攻陷
            if all(e.is_compromised for e in self.executors):
                print(f"All executors compromised after round {round_num + 1}, simulation ended")
                break
        
        return results
        
    def reset_simulation(self):
        """重置模拟状态"""
        for executor in self.executors:
            executor.reset()
        self.attack_history.clear()
        self.simulation_rounds = 0
        
    def get_simulation_summary(self) -> Dict:
        """获取模拟结果摘要"""
        total_attacks = sum(result["total_attacks"] for result in self.attack_history)
        successful_attacks = sum(result["successful_attacks"] for result in self.attack_history)
        
        executor_stats = []
        for executor in self.executors:
            stats = {
                "id": executor.id,
                "defense_threshold": executor.defense_threshold,
                "attacks_received": executor.attack_count,
                "successful_attacks_received": executor.successful_attacks,
                "is_compromised": executor.is_compromised
            }
            executor_stats.append(stats)
        
        return {
            "total_rounds": self.simulation_rounds,
            "total_attacks": total_attacks,
            "successful_attacks": successful_attacks,
            "success_rate": successful_attacks / max(1, total_attacks),
            "compromised_executors": sum(1 for e in self.executors if e.is_compromised),
            "executor_stats": executor_stats
        }
        


# 示例使用
if __name__ == "__main__":
    # 创建样本执行体
    print("Creating sample executors...")
    executors = create_sample_executors(5)
    
    # 显示初始状态
    print("Initial executor states:")
    for executor in executors:
        print(f"Executor {executor.id}: Defense={executor.defense_threshold:.3f}")
    
    # 创建全局攻击模拟器
    simulator = GlobalAttackSimulator(executors)
    
    # 运行全局攻击模拟
    print("\nStarting global attack simulation...")
    simulator.simulate_global_attack_rounds(
        num_rounds=15, 
        min_strength=0.0,
        max_strength=0.7
    )
    
    # 展示模拟结果
    summary = simulator.get_simulation_summary()
    print("\nGlobal attack simulation completed!")
    print(f"Total rounds: {summary['total_rounds']}")
    print(f"Total attacks: {summary['total_attacks']}")
    print(f"Successful attacks: {summary['successful_attacks']}")
    print(f"Attack success rate: {summary['success_rate']:.2%}")
    print(f"Compromised executors: {summary['compromised_executors']}")
    
    print("\nFinal executor states:")
    for stats in summary['executor_stats']:
        print(f"Executor {stats['id']}: "
              f"Defense threshold: {stats['defense_threshold']:.3f}, "
              f"Attacks received: {stats['attacks_received']}, "
              f"Compromised: {'Yes' if stats['is_compromised'] else 'No'}")
