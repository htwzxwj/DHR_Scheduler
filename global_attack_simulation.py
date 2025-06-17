"""
全局攻击模拟 - 攻击会影响所有执行体，基于FusionSystem
"""

import random
from typing import List, Dict, Optional
from logger_config import setup_logger
from AttackSignalGenerator import AttackSignalGenerator

# 设置日志记录器
logger = setup_logger("GlobalAttackSimulator")


# 直接从FusionSystem导入类和常量
from FusionSystem import FusionSystem, CORRECT_SIGNAL, ERROR_SIGNAL
from VanilleDHR import vanilleDHR
# 注意：MTBF 统计数据现在封装在每个模拟器实例中，避免全局变量冲突

class GlobalAttackSimulator:
    """全局攻击模拟器 - 每次攻击会影响所有执行体，可以使用不同的融合系统实现"""
    
    def __init__(self, fusion_system=None, system_name="GenericSystem", num_units: int = 5, 
                 min_active_units: int = 3, seed=None, attack_signal_generator: Optional[AttackSignalGenerator] = None):
        """
        初始化全局攻击模拟器
        
        Args:
            fusion_system: 预先创建的融合系统实例，如果为None则内部创建FusionSystem
            system_name: 系统名称，用于日志和结果输出
            num_units: 执行单元数量（当fusion_system为None时使用）
            min_active_units: 最小活跃单元数（当fusion_system为None时使用）
            seed: 随机数种子，用于复现结果
            attack_signal_generator: 外部攻击信号生成器，如果提供则使用它来获取攻击信号
        """
        if seed is not None:
            random.seed(seed)
            
        self.system_name = system_name
        self.attack_signal_generator = attack_signal_generator
        
        # 初始化MTBF统计数据（实例级别，避免全局变量冲突）
        self.global_mtbf = 0.0
        self.global_total_failures = 0
        self.global_total_runtime = 0
        
        # 如果没有提供融合系统，则创建默认的FusionSystem
        if fusion_system is None:
            self.fusion_system = FusionSystem(min_active_units=min_active_units)
            
            # 创建执行体
            for i in range(num_units):
                unit_id = f"unit_{i}"
                defense_threshold = random.uniform(0.3, 0.8)  # 随机防御阈值
                self.fusion_system.add_unit(unit_id, 
                                        weight=1.0, 
                                        error_threshold=3, 
                                        attack_threshold=defense_threshold)
        else:
            # 使用提供的融合系统
            self.fusion_system = fusion_system
        
        self.attack_history = []
        self.simulation_rounds = 0
        
    def generate_attack_strength(self, min_strength: float = 0.1, max_strength: float = 1.0) -> float:
        """生成攻击强度"""
        return random.uniform(min_strength, max_strength)
            
    def simulate_global_attack(self, attack_strength=None, use_external_signal=True) -> Optional[Dict]:
        """模拟全局攻击，攻击会影响所有执行体
        
        Args:
            attack_strength: 固定攻击强度，若不提供且use_external_signal=False则随机生成
            use_external_signal: 是否使用外部攻击信号生成器，默认为True
            
        Returns:
            攻击结果字典，包含攻击详情；如果外部信号耗尽则返回None
        """
        # 确定攻击强度的来源
        if attack_strength is None:
            if use_external_signal and self.attack_signal_generator is not None:
                # 使用外部攻击信号生成器
                attack_signal = self.attack_signal_generator.get_next_attack_signal()
                if attack_signal is None:
                    logger.warning(f"{self.system_name}: No more attack signals available from external generator")
                    return None
                attack_strength = attack_signal["attack_strength"]
                logger.debug(f"{self.system_name}: Using external attack signal - round {attack_signal['round']}, "
                           f"strength={attack_strength:.3f}")
            else:
                # 内部生成攻击强度
                attack_strength = self.generate_attack_strength()
                logger.debug(f"{self.system_name}: Generated internal attack signal - strength={attack_strength:.3f}")
        else:
            logger.debug(f"{self.system_name}: Using provided attack strength={attack_strength:.3f}")
        
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
                    # 这个单元已经确认为活跃且被攻破，直接计数
                    attack_result["compromised_count"] += 1
                    
                    # 更新MTBF统计 - 记录故障
                    self.global_total_failures += 1
                
                # 添加本次攻击记录
                target_result = {
                    "unit_id": unit_id,
                    "defense_threshold": unit.attack_threshold,
                    "attack_success": attack_success,
                    "status": "Attack Success" if attack_success else "Safe"
                }
                
                attack_result["targets"].append(target_result)
        
        # 收集所有执行体的输出信号
        outputs = self.fusion_system.collect_outputs(attack_signals)
        # Log inactive units
        inactive_units = [unit for unit_id, unit in self.fusion_system.units.items() if not unit.active]
        if inactive_units:
            logger.info(f"Inactive units ({len(inactive_units)}):")
            for unit in inactive_units:
                unit_info = f"  Unit ID: {unit.unit_id}, "
                logger.info(unit_info)

        # 融合输出信号
        fused_output = self.fusion_system.fuse_outputs_with_replacement(outputs)
        
        # 更新执行体状态
        self.fusion_system.update_feedback(outputs, fused_output)
        
        # # 对于FusionSystem类，可以更新权重和替换下线执行体
        if hasattr(self.fusion_system, 'update_weights') and callable(getattr(self.fusion_system, 'update_weights')):
            self.fusion_system.update_weights()
            
        # if hasattr(self.fusion_system, 'try_replace_if_needed') and callable(getattr(self.fusion_system, 'try_replace_if_needed')):
        #     self.fusion_system.try_replace_if_needed()
        
        # 将输出信号添加到攻击结果中
        attack_result["executor_outputs"] = outputs
        attack_result["fused_output"] = fused_output
        
        self.attack_history.append(attack_result)
        return attack_result
        
    def simulate_global_attack_rounds(self, num_rounds: int, min_strength: float = 0.2, max_strength: float = 0.9, 
                                     use_external_signals: bool = True) -> List[Dict]:
        """模拟多轮全局攻击
        
        Args:
            num_rounds: 攻击轮数
            min_strength: 最小攻击强度（仅在不使用外部信号时生效）
            max_strength: 最大攻击强度（仅在不使用外部信号时生效）
            use_external_signals: 是否使用外部攻击信号生成器
            
        Returns:
            所有攻击结果列表
        """
        results = []
        
        # 更新全局运行时间
        self.global_total_runtime += num_rounds
        
        for round_num in range(num_rounds):
            logger.info(f"\n {self.system_name}-Global Attack Round {round_num + 1}")
            self.simulation_rounds = round_num + 1
            
            # 执行全局攻击
            if use_external_signals:
                # 使用外部攻击信号生成器
                result = self.simulate_global_attack(use_external_signal=True)
                if result is None:
                    logger.warning(f"{self.system_name}: Attack simulation stopped - no more external signals available")
                    break
            else:
                # 生成本轮攻击的强度（旧方式）
                attack_strength = random.uniform(min_strength, max_strength)
                logger.info(f"Attack Strength: {attack_strength:.3f}")
                result = self.simulate_global_attack(attack_strength, use_external_signal=False)
                # 在旧方式下，result 不应该为 None
                if result is None:
                    logger.error(f"{self.system_name}: Unexpected None result in non-external mode")
                    break
                
            results.append(result)
            
            # 记录本轮攻击结果（此时确保 result 不为 None）
            logger.info(f"Attack Strength: {result['attack_strength']:.3f}")
            logger.info(f"Success Rate: {result['successful_attacks']}/{result['total_attacks']} ({result['successful_attacks']/max(1, result['total_attacks']):.2%})")
            
                
            # 显示当前各执行体状态
            active_units = [u for u in self.fusion_system.units.values() if u.active]
            all_units = self.fusion_system.units.values()
            logger.info(f"Active Units: {len(active_units)}/{len(self.fusion_system.units)}")
            
            # 输出各执行体信号状态
            logger.info("Unit Signals:")
            for unit_id, signal in result.get("executor_outputs", {}).items():
                status = "正常" if signal == CORRECT_SIGNAL else "异常"
                logger.info(f"  Unit {unit_id}: {signal} ({status})")
                
            # 输出融合信号
            fused = result.get("fused_output")
            if fused:
                fused_status = "正常" if fused == CORRECT_SIGNAL else "异常"
                logger.info(f"Fused Output: {fused} ({fused_status})")
            
            # 检查是否所有执行体都被软下线
            if not any(u.active for u in self.fusion_system.units.values()):
                logger.warning(f"All units are inactive after round {round_num + 1}, simulation ended")
                break
        
            logger.info(f"Global Attack Round {round_num + 1} completed")
            logger.info("-" * 30)
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
        
        # 重置全局MTBF统计数据
        self.global_mtbf = 0.0
        self.global_total_failures = 0
        self.global_total_runtime = 0
        
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
                "consecutive_corrects": unit.consecutive_corrects,
                "active": unit.active,
                "soft_retired": unit.soft_retired if hasattr(unit, "soft_retired") else False,
                "weight": unit.weight
            }
            unit_stats.append(stats)
        
        # 计算系统平均无故障时间 (MTBF)
        if self.global_total_failures > 0:
            self.global_mtbf = self.global_total_runtime / self.global_total_failures
        else:
            self.global_mtbf = self.global_total_runtime  # 如果没有故障，MTBF等于总运行时间
        
        return {
            "system_name": self.system_name,
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
            },
            "reliability_stats": {
                "global_mtbf": self.global_mtbf,
                "total_failures": self.global_total_failures,
                "total_runtime": self.global_total_runtime
            }
        }
        

# 用于记录模拟结果的帮助函数
def log_simulation_results(summary):
    """记录模拟结果到日志"""
    system_name = summary.get("system_name", "Unknown")
    logger.info(f"\n===== {system_name} Simulation Results =====")
    logger.info(f"Total rounds: {summary['total_rounds']}")
    logger.info(f"Total attacks: {summary['total_attacks']}")
    logger.info(f"Successful attacks: {summary['successful_attacks']}")
    logger.info(f"Attack success rate: {summary['success_rate']:.2%}")
    logger.info(f"Active units: {summary['active_units']}/{summary['total_units']}")
    
    # 显示输出信号统计
    signal_stats = summary.get("signal_stats", {})
    logger.info("\nSignal Statistics:")
    logger.info(f"Correct Signals: {signal_stats.get('correct_signals', 0)}")
    logger.info(f"Error Signals: {signal_stats.get('error_signals', 0)}")
    logger.info(f"Fused Correct: {signal_stats.get('fused_correct', 0)}")
    logger.info(f"Fused Error: {signal_stats.get('fused_error', 0)}")
    
    # 显示可靠性统计（MTBF）
    reliability_stats = summary.get("reliability_stats", {})
    logger.info("\nReliability Statistics:")
    logger.info(f"Global Mean Time Between Failures (MTBF): {reliability_stats.get('global_mtbf', 0):.2f} cycles")
    logger.info(f"Total Failures: {reliability_stats.get('total_failures', 0)}")
    logger.info(f"Total Runtime: {reliability_stats.get('total_runtime', 0)} cycles")

# 保持向后兼容的打印函数
def print_simulation_results(summary):
    """打印模拟结果（为保持向后兼容）"""
    log_simulation_results(summary)

# 示例使用
if __name__ == "__main__":
    NUM_UNITS = 5
    MIN_ACTIVE_UNITS = 3
    RANDOM_SEED = 114514
    NUM_ROUNDS = 100
    ATTACK_MIN_STRENGTH = 0.0
    ATTACK_MAX_STRENGTH = 1.0

    # 设置随机种子以便复现结果
    random.seed(RANDOM_SEED)  
    
    logger.info("\n" + "="*60)
    logger.info("COMPARING FUSION SYSTEMS: FusionSystem vs vanilleDHR")
    logger.info("="*60)
    
    # 1. 创建FusionSystem实例
    logger.info("\n[1] Creating adaptive FusionSystem...")
    fusion_system = FusionSystem(min_active_units=MIN_ACTIVE_UNITS)
    
    # 添加执行单元
    for i in range(NUM_UNITS):
        unit_id = f"unit_{i}"
        defense_threshold = random.uniform(0, 1)  # 随机防御阈值
        fusion_system.add_unit(
            unit_id=unit_id, 
            weight=1.0, 
            error_threshold=1, 
            attack_threshold=defense_threshold
        )
    
    # 2. 创建vanilleDHR实例
    logger.info("\n[2] Creating vanilleDHR system...")
    vanilla_dhr = vanilleDHR(min_active_units=MIN_ACTIVE_UNITS)
    
    # 添加相同配置的执行单元
    for i in range(NUM_UNITS):
        unit_id = f"unit_{i}"
        defense_threshold = random.uniform(0, 1)  # 随机防御阈值
        vanilla_dhr.add_unit(
            unit_id=unit_id, 
            attack_threshold=defense_threshold
        )
    
    # 3. 创建攻击信号生成器（确保两个模拟器使用相同的攻击序列）
    logger.info("\n[3] Creating shared attack signal generator...")
    attack_generator = AttackSignalGenerator(
        seed=RANDOM_SEED,
        min_strength=ATTACK_MIN_STRENGTH,
        max_strength=ATTACK_MAX_STRENGTH
    )
    
    # 预生成攻击序列
    attack_generator.pregenerate_attack_sequence(NUM_ROUNDS)
    attack_generator.log_sequence_summary()
    
    # 4. 创建和配置两个攻击模拟器
    logger.info("\n[4] Setting up attack simulators...")
    
    # 为FusionSystem创建攻击模拟器
    adaptive_simulator = GlobalAttackSimulator(
        fusion_system=fusion_system,
        system_name="Adaptive FusionSystem",
        seed=RANDOM_SEED,
        attack_signal_generator=attack_generator  # 使用共享的攻击信号生成器
    )
    
    # 重置攻击信号生成器，确保两个模拟器从同一起点开始
    attack_generator.reset_sequence()
    
    # 为vanilleDHR创建攻击模拟器
    vanilla_simulator = GlobalAttackSimulator(
        fusion_system=vanilla_dhr,
        system_name="Static vanilleDHR",
        seed=RANDOM_SEED,
        attack_signal_generator=attack_generator  # 使用相同的攻击信号生成器
    )
    
    # 5. 运行模拟
    logger.info("\n[5] Running simulations...\n")
    logger.info("-"*30)
    logger.info("Adaptive FusionSystem Simulation")
    logger.info("-"*30)
    
    # 重置信号生成器到开始位置
    attack_generator.reset_sequence()
    adaptive_simulator.simulate_global_attack_rounds(
        num_rounds=NUM_ROUNDS,
        use_external_signals=True  # 使用外部攻击信号
    )
    
    logger.info("\n" + "-"*30)
    logger.info("Static vanilleDHR Simulation")
    logger.info("-"*30)
    
    # 重置信号生成器到开始位置，确保两个模拟器使用相同的攻击序列
    attack_generator.reset_sequence()
    vanilla_simulator.simulate_global_attack_rounds(
        num_rounds=NUM_ROUNDS,
        use_external_signals=True  # 使用外部攻击信号
    )
    
    # 6. 比较结果
    logger.info("\n[6] Comparing results...\n")
    adaptive_summary = adaptive_simulator.get_simulation_summary()
    vanilla_summary = vanilla_simulator.get_simulation_summary()
    
    # 记录结果到日志
    log_simulation_results(adaptive_summary)
    log_simulation_results(vanilla_summary)
    
    # 7. 记录比较总结
    logger.info("\n" + "="*60)
    logger.info("SIMULATION COMPARISON SUMMARY")
    logger.info("="*60)
    
    # 计算并比较成功率
    adaptive_success_rate = adaptive_summary["success_rate"]
    vanilla_success_rate = vanilla_summary["success_rate"]
    rate_diff = abs(adaptive_success_rate - vanilla_success_rate)
    better_system = "Adaptive FusionSystem" if adaptive_success_rate < vanilla_success_rate else "Static vanilleDHR"
    
    logger.info(f"Attack Success Rate:")
    logger.info(f"- Adaptive FusionSystem: {adaptive_success_rate:.2%}")
    logger.info(f"- Static vanilleDHR: {vanilla_success_rate:.2%}")
    logger.info(f"- Difference: {rate_diff:.2%}")
    logger.info(f"- Better system: {better_system} (lower is better)\n")
    
    # 比较MTBF
    adaptive_mtbf = adaptive_summary["reliability_stats"]["global_mtbf"]
    vanilla_mtbf = vanilla_summary["reliability_stats"]["global_mtbf"]
    mtbf_ratio = adaptive_mtbf / vanilla_mtbf if vanilla_mtbf > 0 else float('inf')
    better_mtbf_system = "Adaptive FusionSystem" if adaptive_mtbf > vanilla_mtbf else "Static vanilleDHR"
    
    logger.info(f"Mean Time Between Failures (MTBF):")
    logger.info(f"- Adaptive FusionSystem: {adaptive_mtbf:.2f} cycles")
    logger.info(f"- Static vanilleDHR: {vanilla_mtbf:.2f} cycles")
    logger.info(f"- Ratio: {mtbf_ratio:.2f}x")
    logger.info(f"- Better system: {better_mtbf_system} (higher is better)")
    
    logger.info("\nFinal execution unit states (Adaptive):")
    for stats in adaptive_summary['unit_stats']:
        logger.info(f"Unit {stats['id']}: "
              f"Attack threshold: {stats['attack_threshold']:.3f}, "
              f"Weight: {stats['weight']:.3f}, "
              f"Active: {'Yes' if stats['active'] else 'No'}, "
              f"Soft retired: {'Yes' if stats['soft_retired'] else 'No'}, "
              f"consecutive_corrects: {stats['consecutive_corrects']}")
              
    logger.info("\nFinal execution unit states (Vanilla):")
    for stats in vanilla_summary['unit_stats']:
        logger.info(f"Unit {stats['id']}: "
              f"Attack threshold: {stats['attack_threshold']:.3f}, "
              f"Weight: {stats['weight']:.3f}, "
              f"Active: {'Yes' if stats['active'] else 'No'}, "
              f"Soft retired: {'Yes' if stats.get('soft_retired', False) else 'No'}, "
              f"consecutive_corrects: {stats['consecutive_corrects']}")
