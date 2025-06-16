"""
全局攻击模拟 - 攻击会影响所有执行体，基于FusionSystem
"""

import random
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from collections import defaultdict

# 直接从FusionSystem导入类和常量
from FusionSystem import FusionSystem, CORRECT_SIGNAL, ERROR_SIGNAL

class GlobalAttackSimulator:
    """全局攻击模拟器 - 每次攻击会影响所有执行体，使用FusionSystem实现"""
    
    def __init__(self, num_units: int = 5, min_active_units: int = 3):
        # 创建融合系统
        self.fusion_system = FusionSystem(min_active_units=min_active_units)
        
        # 创建执行单元
        for i in range(num_units):
            unit_id = f"unit_{i}"
            defense_threshold = random.uniform(0.3, 0.8)  # 随机防御阈值
            self.fusion_system.add_unit(unit_id, 
                                      weight=1.0, 
                                      error_threshold=3, 
                                      attack_threshold=defense_threshold)
        
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
        
        # 为每个执行单元生成攻击信号
        attack_signals = {}
        for unit_id, unit in self.fusion_system.units.items():
            if unit.active:  # 只攻击活跃的单元
                attack_signals[unit_id] = attack_strength
                attack_result["total_attacks"] += 1
                
                # 判断攻击是否成功（比较攻击强度和防御阈值）
                attack_success = attack_strength > unit.attack_threshold
                
                # 记录攻击结果
                if attack_success:
                    attack_result["successful_attacks"] += 1
                    
                    # 如果单元之前是活跃的，现在被攻破，计数器+1
                    if unit.active and attack_success:
                        attack_result["compromised_count"] += 1
                
                # 添加本次攻击记录
                target_result = {
                    "unit_id": unit_id,
                    "defense_threshold": unit.attack_threshold,
                    "attack_success": attack_success,
                    "status": "Success" if attack_success else "Safe"
                }
                
                attack_result["targets"].append(target_result)
        
        # 收集所有执行体的输出信号
        outputs = self.fusion_system.collect_outputs(attack_signals)
        
        # 融合输出信号
        fused_output = self.fusion_system.fuse_outputs(outputs)
        
        # 更新执行体状态
        self.fusion_system.update_feedback(outputs, fused_output)
        
        # 更新权重
        self.fusion_system.update_weights()
        
        # 尝试替换下线的执行体
        self.fusion_system.try_replace_if_needed()
        
        # 将输出信号添加到攻击结果中
        attack_result["executor_outputs"] = outputs
        attack_result["fused_output"] = fused_output
        
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
            
            # 生成本轮攻击的强度
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
            active_units = [u for u in self.fusion_system.units.values() if u.active]
            all_units = self.fusion_system.units.values()
            print(f"Active Units: {len(active_units)}/{len(self.fusion_system.units)}")
            
            # 输出各执行体信号状态
            print("Unit Signals:")
            for unit_id, signal in result.get("executor_outputs", {}).items():
                status = "正常" if signal == CORRECT_SIGNAL else "异常"
                print(f"  Unit {unit_id}: {signal} ({status})")
                
            # 输出融合信号
            fused = result.get("fused_output")
            if fused:
                fused_status = "正常" if fused == CORRECT_SIGNAL else "异常"
                print(f"Fused Output: {fused} ({fused_status})")
            
            # 检查是否所有执行体都被软下线
            if not any(u.active for u in self.fusion_system.units.values()):
                print(f"All units are inactive after round {round_num + 1}, simulation ended")
                break
        
        return results
        
    def reset_simulation(self):
        """重置模拟状态"""
        # 重新创建一个新的融合系统
        num_units = len(self.fusion_system.units)
        min_active_units = self.fusion_system.min_active_units
        
        self.fusion_system = FusionSystem(min_active_units=min_active_units)
        
        # 重新添加执行单元
        for i in range(num_units):
            unit_id = f"unit_{i}"
            defense_threshold = random.uniform(0.3, 0.8)  # 随机防御阈值
            self.fusion_system.add_unit(unit_id, 
                                      weight=1.0, 
                                      error_threshold=3, 
                                      attack_threshold=defense_threshold)
            
        self.attack_history.clear()
        self.simulation_rounds = 0
        
    def get_simulation_summary(self) -> Dict:
        """获取模拟结果摘要"""
        total_attacks = sum(result["total_attacks"] for result in self.attack_history)
        successful_attacks = sum(result["successful_attacks"] for result in self.attack_history)
        
        # 统计输出信号
        correct_signals = 0
        error_signals = 0
        for result in self.attack_history:
            for _, signal in result.get("executor_outputs", {}).items():
                if signal == CORRECT_SIGNAL:
                    correct_signals += 1
                elif signal == ERROR_SIGNAL:
                    error_signals += 1
        
        # 统计融合结果
        fused_correct = sum(1 for result in self.attack_history if result.get("fused_output") == CORRECT_SIGNAL)
        fused_error = sum(1 for result in self.attack_history if result.get("fused_output") == ERROR_SIGNAL)
        
        # 获取执行单元状态
        unit_stats = []
        for unit_id, unit in self.fusion_system.units.items():
            stats = {
                "id": unit_id,
                "attack_threshold": unit.attack_threshold,
                "consecutive_errors": unit.consecutive_errors,
                "active": unit.active,
                "soft_retired": unit.soft_retired,
                "weight": unit.weight
            }
            unit_stats.append(stats)
        
        return {
            "total_rounds": self.simulation_rounds,
            "total_attacks": total_attacks,
            "successful_attacks": successful_attacks,
            "success_rate": successful_attacks / max(1, total_attacks),
            "active_units": sum(1 for u in self.fusion_system.units.values() if u.active),
            "total_units": len(self.fusion_system.units),
            "unit_stats": unit_stats,
            "signal_stats": {
                "correct_signals": correct_signals,
                "error_signals": error_signals,
                "fused_correct": fused_correct,
                "fused_error": fused_error
            }
        }
        

# 示例使用
if __name__ == "__main__":
    # 创建全局攻击模拟器（内部会创建融合系统和执行单元）
    print("Creating global attack simulator with fusion system...")
    simulator = GlobalAttackSimulator(num_units=5, min_active_units=3)
    
    # 显示初始状态
    print("Initial execution unit states:")
    for unit_id, unit in simulator.fusion_system.units.items():
        print(f"Unit {unit_id}: Attack Threshold={unit.attack_threshold:.3f}, "
              f"Active={unit.active}, Weight={unit.weight:.3f}")
    
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
    print(f"Active units: {summary['active_units']}/{summary['total_units']}")
    
    # 显示输出信号统计
    signal_stats = summary.get("signal_stats", {})
    print("\nSignal Statistics:")
    print(f"Correct Signals: {signal_stats.get('correct_signals', 0)}")
    print(f"Error Signals: {signal_stats.get('error_signals', 0)}")
    print(f"Fused Correct: {signal_stats.get('fused_correct', 0)}")
    print(f"Fused Error: {signal_stats.get('fused_error', 0)}")
    
    print("\nFinal execution unit states:")
    for stats in summary['unit_stats']:
        print(f"Unit {stats['id']}: "
              f"Attack threshold: {stats['attack_threshold']:.3f}, "
              f"Weight: {stats['weight']:.3f}, "
              f"Active: {'Yes' if stats['active'] else 'No'}, "
              f"Soft retired: {'Yes' if stats['soft_retired'] else 'No'}, "
              f"Consecutive errors: {stats['consecutive_errors']}")
