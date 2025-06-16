import random
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple

# 设置随机种子，确保结果可重现
random.seed(42)
np.random.seed(42)

class Executor:
    """执行体类"""
    def __init__(self, executor_id: int, defense_threshold: float, initial_weight: float, 
                 error_threshold: int = 3, recovery_threshold: int = 1):
        self.id = executor_id
        self.defense_threshold = defense_threshold  # 防御阈值
        self.initial_weight = initial_weight        # 初始权重
        self.current_weight = initial_weight        # 当前权重
        self.attack_count = 0                       # 被攻击次数
        self.successful_attacks = 0                 # 成功攻击次数
        self.is_compromised = False                 # 是否被攻陷
        
        # 添加权重投票相关属性
        self.consecutive_errors = 0                 # 连续错误次数
        self.error_threshold = error_threshold      # 错误阈值
        self.recovery_threshold = recovery_threshold # 恢复阈值
        self.active = True                          # 是否活跃
        self.soft_retired = False                   # 是否软下线
        self.voting_weight = initial_weight         # 投票权重
        
    def reset(self):
        """重置执行体状态"""
        self.current_weight = self.initial_weight
        self.attack_count = 0
        self.successful_attacks = 0
        self.is_compromised = False
        self.consecutive_errors = 0
        self.active = True
        self.soft_retired = False
        self.voting_weight = self.initial_weight
    
    def generate_decision(self, attack_strength: float) -> str:
        """生成决策输出 - 模拟FusionSystem中的输出生成"""
        if not self.active or self.is_compromised:
            return "OFFLINE"
        
        # 根据攻击强度和防御阈值生成决策
        if attack_strength > self.defense_threshold:
            return "THREAT_DETECTED"  # 检测到威胁
        else:
            return "SAFE"             # 安全状态
    
    def update_voting_weight(self, decay_factor: float = 0.5):
        """根据连续错误次数更新投票权重"""
        import math
        self.voting_weight = self.current_weight * math.exp(-decay_factor * self.consecutive_errors)
        if self.current_weight <= 0.1:  # 权重过低则认为被攻陷
            self.is_compromised = True

class AttackSimulator:
    """攻击模拟器"""
    
    def __init__(self, executors: List[Executor]):
        self.executors = executors
        self.attack_history = []
        self.simulation_rounds = 0
        
    def generate_attack_strength(self, min_strength: float = 0.1, max_strength: float = 1.0) -> float:
        """生成攻击强度"""
        return random.uniform(min_strength, max_strength)
    
    def select_target(self, strategy: str = "random"):
        """选择攻击目标
        
        Args:
            strategy: 攻击策略
                - "random": 随机选择
                - "highest_weight": 选择权重最高的
                - "lowest_defense": 选择防御最低的
                - "weakest": 选择当前权重最低的
        """
        available_targets = [e for e in self.executors if not e.is_compromised]
        
        if not available_targets:
            return None
            
        if strategy == "random":
            return random.choice(available_targets)
        elif strategy == "highest_weight":
            return max(available_targets, key=lambda x: x.current_weight)
        elif strategy == "lowest_defense":
            return min(available_targets, key=lambda x: x.defense_threshold)
        elif strategy == "weakest":
            return min(available_targets, key=lambda x: x.current_weight)
        else:
            return random.choice(available_targets)
    
    def simulate_single_attack(self, attack_strategy: str = "random") -> Dict:
        """模拟单次攻击
        
        Returns:
            攻击结果字典，包含攻击详情
        """
        # 选择目标
        target = self.select_target(attack_strategy)
        if target is None:
            return {"success": False, "reason": "No available targets"}
        
        # 生成攻击强度
        attack_strength = self.generate_attack_strength()
        
        # 判断攻击是否成功
        attack_success = attack_strength > target.defense_threshold
        
        # 应用攻击效果
        target.attack_count += 1
        if attack_success:
            target.successful_attacks += 1
            target.is_compromised = True  # 攻击成功时将目标标记为已攻陷
        
        # 记录攻击结果
        attack_result = {
            "round": self.simulation_rounds,
            "target_id": target.id,
            "attack_strength": attack_strength,
            "defense_threshold": target.defense_threshold,
            "attack_success": attack_success,
            "target_compromised": target.is_compromised
        }
        
        self.attack_history.append(attack_result)
        return attack_result
    
    def simulate_attack_rounds(self, num_rounds: int, attack_strategy: str = "random", attacks_per_round: int = 1) -> List[Dict]:
        """模拟多轮攻击
        
        Args:
            num_rounds: 轮数
            attack_strategy: 攻击策略
            attacks_per_round: 每轮攻击次数
            
        Returns:
            所有攻击结果的列表
        """
        round_results = []
        
        for round_num in range(num_rounds):
            self.simulation_rounds = round_num + 1
            round_attacks = []
            
            for _ in range(attacks_per_round):
                attack_result = self.simulate_single_attack(attack_strategy)
                if attack_result.get("success", True):  # 如果不是"No targets"错误
                    round_attacks.append(attack_result)
                else:
                    break  # 没有可用目标，结束模拟
            
            round_results.extend(round_attacks)
            
            # 检查是否所有执行体都被攻陷
            if all(e.is_compromised for e in self.executors):
                print(f"All executors compromised after round {round_num + 1}, simulation ended")
                break
        
        return round_results
    
    def get_simulation_summary(self) -> Dict:
        """获取模拟结果摘要"""
        total_attacks = len(self.attack_history)
        successful_attacks = sum(1 for attack in self.attack_history if attack["attack_success"])
        
        executor_stats = []
        for executor in self.executors:
            stats = {
                "id": executor.id,
                "initial_weight": executor.initial_weight,
                "current_weight": executor.current_weight,
                "defense_threshold": executor.defense_threshold,
                "attacks_received": executor.attack_count,
                "successful_attacks_received": executor.successful_attacks,
                "weight_loss": executor.initial_weight - executor.current_weight,
                "is_compromised": executor.is_compromised
            }
            executor_stats.append(stats)
        
        return {
            "total_rounds": self.simulation_rounds,
            "total_attacks": total_attacks,
            "successful_attacks": successful_attacks,
            "success_rate": successful_attacks / total_attacks if total_attacks > 0 else 0,
            "compromised_executors": sum(1 for e in self.executors if e.is_compromised),
            "executor_stats": executor_stats
        }
    
    def reset_simulation(self):
        """重置模拟状态"""
        for executor in self.executors:
            executor.reset()
        self.attack_history.clear()
        self.simulation_rounds = 0
    
    def show_statistics(self):
        """显示攻击统计信息"""
        if not self.attack_history:
            print("No attack history data available for statistics")
            return
        
        print("\n攻击统计信息:")
        
        # 攻击成功率
        successes = sum(1 for attack in self.attack_history if 
                        isinstance(attack.get('attack_success'), bool) and attack.get('attack_success'))
        total = sum(1 for attack in self.attack_history if 
                   isinstance(attack.get('attack_success'), bool))
        
        if total > 0:
            success_rate = successes / total
            print(f"攻击成功率: {success_rate:.2%} ({successes}/{total})")
        
        # 被攻陷的执行体
        compromised = sum(1 for e in self.executors if e.is_compromised)
        print(f"被攻陷执行体: {compromised}/{len(self.executors)}")
        
        # 各执行体状态
        print("\n各执行体当前状态:")
        for executor in self.executors:
            status = "已攻陷" if executor.is_compromised else "安全"
            print(f"执行体 {executor.id}: 攻击次数={executor.attack_count}, "
                 f"成功攻击次数={executor.successful_attacks}, 状态={status}")

    def collect_decisions(self, attack_strengths: Dict[int, float]) -> Dict[int, str]:
        """收集所有执行体的决策输出"""
        decisions = {}
        for executor in self.executors:
            if executor.active and not executor.is_compromised:
                attack_strength = attack_strengths.get(executor.id, 0.0)
                decisions[executor.id] = executor.generate_decision(attack_strength)
        return decisions
    
    def fuse_decisions(self, decisions: Dict[int, str]) -> str:
        """使用权重投票融合所有决策"""
        from collections import defaultdict
        
        decision_weights = defaultdict(float)
        
        for executor_id, decision in decisions.items():
            executor = next((e for e in self.executors if e.id == executor_id), None)
            if executor and executor.active and not executor.is_compromised:
                decision_weights[decision] += executor.voting_weight
        
        if not decision_weights:
            return "NO_CONSENSUS"  # 无有效决策
        
        # 返回权重最高的决策
        return max(decision_weights.items(), key=lambda x: x[1])[0]
    
    def update_executor_feedback(self, decisions: Dict[int, str], fused_decision: str):
        """根据融合决策更新执行体的反馈状态"""
        for executor_id, decision in decisions.items():
            executor = next((e for e in self.executors if e.id == executor_id), None)
            if not executor:
                continue
            
            is_correct = (decision == fused_decision)
            
            if executor.soft_retired:
                # 软下线状态下，决策正确则恢复
                if is_correct:
                    executor.consecutive_errors = max(0, executor.consecutive_errors - 1)
                    if executor.consecutive_errors <= executor.recovery_threshold:
                        executor.soft_retired = False
                        executor.active = True
                else:
                    executor.consecutive_errors += 1
            else:
                # 活跃状态下更新连续错误计数
                if is_correct:
                    executor.consecutive_errors = max(0, executor.consecutive_errors - 1)
                else:
                    executor.consecutive_errors += 1
                    if executor.consecutive_errors >= executor.error_threshold:
                        executor.soft_retired = True
                        executor.active = False
    
    def update_voting_weights(self, decay_factor: float = 0.5):
        """更新所有执行体的投票权重"""
        total_weight = 0.0
        
        # 更新每个执行体的投票权重
        for executor in self.executors:
            executor.update_voting_weight(decay_factor)
            if executor.active and not executor.is_compromised:
                total_weight += executor.voting_weight
        
        # 归一化权重
        if total_weight > 0:
            for executor in self.executors:
                if executor.active and not executor.is_compromised:
                    executor.voting_weight /= total_weight
        else:
            # 所有权重为0，均分给活跃执行体
            active_count = sum(1 for e in self.executors if e.active and not e.is_compromised)
            if active_count > 0:
                for executor in self.executors:
                    if executor.active and not executor.is_compromised:
                        executor.voting_weight = 1.0 / active_count
    
    def simulate_attack_with_voting(self, num_rounds: int, attack_strategy: str = "random") -> List[Dict]:
        """使用权重投票机制模拟攻击
        
        Args:
            num_rounds: 轮数
            attack_strategy: 攻击策略
            
        Returns:
            所有轮次结果的列表
        """
        round_results = []
        
        for round_num in range(num_rounds):
            self.simulation_rounds = round_num + 1
            
            # 为每个执行体生成攻击强度
            attack_strengths = {}
            for executor in self.executors:
                if not executor.is_compromised:
                    attack_strengths[executor.id] = self.generate_attack_strength()
            
            # 收集决策
            decisions = self.collect_decisions(attack_strengths)
            
            # 融合决策
            fused_decision = self.fuse_decisions(decisions)
            
            # 更新反馈
            self.update_executor_feedback(decisions, fused_decision)
            
            # 更新投票权重
            self.update_voting_weights()
            
            # 模拟基于融合决策的攻击结果
            if fused_decision == "THREAT_DETECTED":
                # 系统检测到威胁，执行防御措施
                # 不进行任何伤害计算，仅记录攻击被成功防御
                pass
            else:
                # 系统未检测到威胁，可能被攻击成功
                target = self.select_target(attack_strategy)
                if target:
                    attack_strength = attack_strengths.get(target.id, 0.5)
                    attack_success = attack_strength > target.defense_threshold
                    
                    target.attack_count += 1
                    if attack_success:
                        target.successful_attacks += 1
                        target.is_compromised = True  # 攻击成功时将目标标记为已攻陷
            
            # 记录本轮结果
            round_result = {
                "round": self.simulation_rounds,
                "attack_strengths": attack_strengths.copy(),
                "decisions": decisions.copy(),
                "fused_decision": fused_decision,
                "active_executors": len([e for e in self.executors if e.active and not e.is_compromised]),
                "compromised_executors": len([e for e in self.executors if e.is_compromised])
            }
            
            round_results.append(round_result)
            self.attack_history.append(round_result)
            
            # 检查是否所有执行体都被攻陷
            if all(e.is_compromised for e in self.executors):
                print(f"All executors compromised after round {round_num + 1}, simulation ended")
                break
        
        return round_results

def create_sample_executors(num_executors: int = 5) -> List[Executor]:
    """Create sample executor list"""
    executors = []
    for i in range(num_executors):
        defense_threshold = random.uniform(0.3, 0.8)  # Defense threshold
        initial_weight = random.uniform(0.5, 1.0)     # Initial weight
        executor = Executor(i, defense_threshold, initial_weight)
        executors.append(executor)
    return executors


if __name__ == "__main__":
    # * 创建示例执行体
    print("Creating sample executors...")
    executors = create_sample_executors(5)
    
    # 显示初始状态
    print("\nInitial executor states:")
    for executor in executors:
        print(f"Executor {executor.id}: Weight={executor.current_weight:.3f}, "
              f"Defense={executor.defense_threshold:.3f}")
    
    # 创建攻击模拟器
    simulator = AttackSimulator(executors)
    
    # 开始攻击模拟
    print("\nStarting attack simulation...")
    results = simulator.simulate_attack_rounds(
        num_rounds=50, 
        attack_strategy="random", 
        attacks_per_round=2
    )
    
    # 获取模拟摘要
    summary = simulator.get_simulation_summary()
    
    # 打印结果
    print(f"\nSimulation completed!")
    print(f"Total rounds: {summary['total_rounds']}")
    print(f"Total attacks: {summary['total_attacks']}")
    print(f"Successful attacks: {summary['successful_attacks']}")
    print(f"Attack success rate: {summary['success_rate']:.2%}")
    print(f"Compromised executors: {summary['compromised_executors']}")
    
    print("\nExecutor states:")
    for stats in summary['executor_stats']:
        print(f"Executor {stats['id']}: "
              f"Weight {stats['current_weight']:.3f} "
              f"(Initial: {stats['initial_weight']:.3f}), "
              f"Defense threshold: {stats['defense_threshold']:.3f}, "
              f"Attacks received: {stats['attacks_received']}, "
              f"Compromised: {'Yes' if stats['is_compromised'] else 'No'}")
    
    # 显示统计信息
    simulator.show_statistics()
    
    # ====== 演示权重投票机制 ======
    print("\n" + "="*60)
    print("Demonstrating Weight-based Voting Mechanism")
    print("="*60)
    
    # 重置系统状态
    simulator.reset_simulation()
    
    # 运行权重投票模拟
    print("\nStarting voting-based attack simulation...")
    voting_results = simulator.simulate_attack_with_voting(
        num_rounds=20,
        attack_strategy="random"
    )
    
    # 显示权重投票结果
    print(f"\nVoting simulation completed after {len(voting_results)} rounds!")
    
    print("\nFinal executor states with voting weights:")
    for executor in simulator.executors:
        print(f"Executor {executor.id}: "
              f"Weight {executor.current_weight:.3f}, "
              f"Voting Weight {executor.voting_weight:.3f}, "
              f"Errors {executor.consecutive_errors}, "
              f"Active: {'Yes' if executor.active else 'No'}, "
              f"Compromised: {'Yes' if executor.is_compromised else 'No'}")
    
    # 显示最后几轮的决策情况
    print("\nLast 5 rounds decision summary:")
    for i, result in enumerate(voting_results[-5:]):
        round_num = result['round']
        decisions = result['decisions']
        fused = result['fused_decision']
        active = result['active_executors']
        print(f"Round {round_num}: Decisions={decisions}, Fused='{fused}', Active={active}")
