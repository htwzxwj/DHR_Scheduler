"""
全局攻击模拟 - 攻击会影响所有执行体，基于FusionSystem
"""

import random
from typing import List, Dict, Optional
from logger_config import default_logger as logger
from AttackSignalGenerator import AttackSignalGenerator



# 直接从FusionSystem导入类和常量
from FusionSystem import FusionSystem, CORRECT_SIGNAL, ERROR_SIGNAL
from VanilleDHR import vanilleDHR

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
        
        # 如果没有提供融合系统，则创建默认的FusionSystem
        if fusion_system is None:
            self.fusion_system = FusionSystem(min_active_units=min_active_units)
        else:
            # 使用提供的融合系统
            self.fusion_system = fusion_system
        
        self.attack_history = []
        self.simulation_rounds = 0
        
        # 添加vanilleDHR替换次数跟踪
        self.vanilla_replacement_count = 0
        
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
        
        # 为每个执行单元生成攻击信号（包括停用的单元）
        attack_signals = {}
        for unit_id, unit in self.fusion_system.units.items():
            # 为所有单元生成攻击信号，不管是否活跃
            attack_signals[unit_id] = attack_strength
            attack_result["total_attacks"] += 1
            
            # 判断攻击是否成功（比较攻击强度和防御阈值）
            attack_success = attack_strength > unit.attack_threshold
            
            # 记录攻击结果
            if attack_success:
                attack_result["successful_attacks"] += 1
                # 这个单元被攻破，直接计数
                attack_result["compromised_count"] += 1
            
            # 添加本次攻击记录（所有单元都记录，不论是否活跃）
            target_result = {
                "unit_id": unit_id,
                "defense_threshold": unit.attack_threshold,
                "attack_success": attack_success,
                "status": "Attack Success" if attack_success else "Safe",
                "active": unit.active  # 记录单元是否活跃
            }
            
            attack_result["targets"].append(target_result)
        
        # 收集所有执行体的输出信号
        outputs = self.fusion_system.collect_outputs(attack_signals)
        # Log inactive units
        inactive_units = [unit for unit_id, unit in self.fusion_system.units.items() if not unit.active]
        if inactive_units:
            logger.info(f"下线了{len(inactive_units)}个执行体：")
            for unit in inactive_units:
                unit_info = f"  下线的执行体ID: {unit.unit_id}, "
                logger.info(unit_info)

        # 融合输出信号
        fused_output = self.fusion_system.fuse_outputs_with_replacement(outputs)
        
        # 更新执行体状态
        self.fusion_system.update_feedback(outputs, fused_output)
        
        # 检查vanilleDHR是否发生了替换操作
        if self.fusion_system.checkFlag:
            self.vanilla_replacement_count += 1
            self.fusion_system.checkFlag = False  # 重置标志
            logger.info(f"{self.system_name}: replacement occurred (total replacements: {self.vanilla_replacement_count})")
        
        # # 对于FusionSystem类，可以更新权重和替换下线执行体
        if hasattr(self.fusion_system, 'update_weights') and callable(getattr(self.fusion_system, 'update_weights')):
            self.fusion_system.update_weights()
            
        
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
        self.vanilla_replacement_count = 0  # 重置替换次数计数器
        
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
        
        return {
            "system_name": self.system_name,
            "total_rounds": self.simulation_rounds,
            "total_attacks": total_attacks,
            "successful_attacks": successful_attacks,
            "active_units": sum(1 for u in self.fusion_system.units.values() if u.active),
            "total_units": len(self.fusion_system.units),
            "vanilla_replacement_count": self.vanilla_replacement_count,  # 添加vanilleDHR替换次数
            "unit_stats": unit_stats,
            "signal_stats": {
                "correct_signals": correct_signals,
                "error_signals": error_signals,
                "fused_correct": fused_correct,
                "fused_error": fused_error
            }
        }
    
    def calculate_error_signal_rate(self) -> Dict:
        """计算ERROR_SIGNAL的比例（错误率）
        
        Returns:
            包含错误率统计信息的字典
        """
        # 统计所有轮次中的输出信号
        total_unit_signals = 0
        error_unit_signals = 0
        total_fused_signals = 0
        error_fused_signals = 0
        
        for result in self.attack_history:
            # 统计各执行体的输出信号
            for unit_id, signal in result.get("executor_outputs", {}).items():
                total_unit_signals += 1
                if signal == ERROR_SIGNAL:
                    error_unit_signals += 1
            
            # 统计融合输出信号
            fused_output = result.get("fused_output")
            if fused_output is not None:
                total_fused_signals += 1
                if fused_output == ERROR_SIGNAL:
                    error_fused_signals += 1
        
        # 计算错误率
        unit_error_rate = error_unit_signals / max(1, total_unit_signals)
        fused_error_rate = error_fused_signals / max(1, total_fused_signals)
        
        return {
            "system_name": self.system_name,
            "unit_signals": {
                "total": total_unit_signals,
                "errors": error_unit_signals,
                "error_rate": unit_error_rate
            },
            "fused_signals": {
                "total": total_fused_signals,
                "errors": error_fused_signals,
                "error_rate": fused_error_rate
            }
        }
    
    def log_error_signal_rate(self):
        """记录ERROR_SIGNAL错误率到日志"""
        error_stats = self.calculate_error_signal_rate()
        
        logger.info(f"\n===== {error_stats['system_name']} Error Signal Rate Analysis =====")
        
        # 执行体信号错误率
        unit_stats = error_stats['unit_signals']
        logger.info(f"Unit Signals Error Rate:")
        logger.info(f"  Total unit signals: {unit_stats['total']}")
        logger.info(f"  ERROR_SIGNALs: {unit_stats['errors']}")
        logger.info(f"  Error rate: {unit_stats['error_rate']:.2%}")
        
        # 融合信号错误率
        fused_stats = error_stats['fused_signals']
        logger.info(f"Fused Signals Error Rate:")
        logger.info(f"  Total fused signals: {fused_stats['total']}")
        logger.info(f"  ERROR_SIGNALs: {fused_stats['errors']}")
        logger.info(f"  Error rate: {fused_stats['error_rate']:.2%}")
        
        return error_stats


# 比较两个模拟器错误率的函数
def compare_error_signal_rates(simulator1: GlobalAttackSimulator, simulator2: GlobalAttackSimulator):
    """比较两个GlobalAttackSimulator的ERROR_SIGNAL错误率
    
    Args:
        simulator1: 第一个攻击模拟器
        simulator2: 第二个攻击模拟器
    """
    logger.info("\n" + "="*60)
    logger.info("ERROR SIGNAL RATE COMPARISON")
    logger.info("="*60)
    
    # 获取两个模拟器的错误率统计
    error_stats1 = simulator1.calculate_error_signal_rate()
    error_stats2 = simulator2.calculate_error_signal_rate()
    
    # 记录详细错误率信息
    simulator1.log_error_signal_rate()
    simulator2.log_error_signal_rate()
    
    # 比较分析
    logger.info(f"\n===== Error Rate Comparison Summary =====")
    
    # 比较执行体信号错误率
    unit_rate1 = error_stats1['unit_signals']['error_rate']
    unit_rate2 = error_stats2['unit_signals']['error_rate']
    unit_diff = abs(unit_rate1 - unit_rate2)
    better_unit_system = error_stats1['system_name'] if unit_rate1 < unit_rate2 else error_stats2['system_name']
    
    logger.info(f"Unit Signals Error Rate Comparison:")
    logger.info(f"  {error_stats1['system_name']}: {unit_rate1:.2%}")
    logger.info(f"  {error_stats2['system_name']}: {unit_rate2:.2%}")
    logger.info(f"  Difference: {unit_diff:.2%}")
    logger.info(f"  Better system: {better_unit_system} (lower error rate is better)")
    
    # 比较融合信号错误率
    fused_rate1 = error_stats1['fused_signals']['error_rate']
    fused_rate2 = error_stats2['fused_signals']['error_rate']
    fused_diff = abs(fused_rate1 - fused_rate2)
    better_fused_system = error_stats1['system_name'] if fused_rate1 < fused_rate2 else error_stats2['system_name']
    
    logger.info(f"\nFused Signals Error Rate Comparison:")
    logger.info(f"  {error_stats1['system_name']}: {fused_rate1:.2%}")
    logger.info(f"  {error_stats2['system_name']}: {fused_rate2:.2%}")
    logger.info(f"  Difference: {fused_diff:.2%}")
    logger.info(f"  Better system: {better_fused_system} (lower error rate is better)")
    
    # 综合评估
    logger.info(f"\nOverall Assessment:")
    if unit_rate1 < unit_rate2 and fused_rate1 < fused_rate2:
        logger.info(f"  {error_stats1['system_name']} performs better in both unit and fused signal error rates")
    elif unit_rate1 > unit_rate2 and fused_rate1 > fused_rate2:
        logger.info(f"  {error_stats2['system_name']} performs better in both unit and fused signal error rates")
    else:
        logger.info(f"  Mixed results: Each system has advantages in different aspects")
        if unit_rate1 < unit_rate2:
            logger.info(f"    {error_stats1['system_name']} has better unit signal reliability")
            logger.info(f"    {error_stats2['system_name']} has better fused signal reliability")
        else:
            logger.info(f"    {error_stats2['system_name']} has better unit signal reliability")
            logger.info(f"    {error_stats1['system_name']} has better fused signal reliability")

# 用于记录模拟结果的帮助函数
def log_simulation_results(summary):
    """记录模拟结果到日志"""
    system_name = summary.get("system_name", "Unknown")
    logger.info(f"\n===== {system_name} Simulation Results =====")
    logger.info(f"Total rounds: {summary['total_rounds']}")
    logger.info(f"Total attacks: {summary['total_attacks']}")
    logger.info(f"Successful attacks: {summary['successful_attacks']}")
    logger.info(f"Active units: {summary['active_units']}/{summary['total_units']}")
    
    # 显示vanilleDHR替换次数（如果存在）
    replacement_count = summary.get("vanilla_replacement_count", 0)
    if replacement_count > 0:
        logger.info(f"replacement count: {replacement_count}")
    
    # 显示输出信号统计
    signal_stats = summary.get("signal_stats", {})
    logger.info("\nSignal Statistics:")
    logger.info(f"Correct Signals: {signal_stats.get('correct_signals', 0)}")
    logger.info(f"Error Signals: {signal_stats.get('error_signals', 0)}")
    logger.info(f"Fused Correct: {signal_stats.get('fused_correct', 0)}")
    logger.info(f"Fused Error: {signal_stats.get('fused_error', 0)}")

# 保持向后兼容的打印函数
def print_simulation_results(summary):
    """打印模拟结果（为保持向后兼容）"""
    log_simulation_results(summary)

# 示例使用
if __name__ == "__main__":
    NUM_UNITS = 5
    MIN_ACTIVE_UNITS = 3
    RANDOM_SEED = 42
    NUM_ROUNDS = 1000
    ATTACK_MIN_STRENGTH = 0.0
    ATTACK_MAX_STRENGTH = 1.0

    # 设置随机种子以便复现结果
    random.seed(RANDOM_SEED)  
    
    logger.info("\n" + "="*60)
    logger.info("COMPARING FUSION SYSTEMS: FusionSystem vs vanilleDHR")
    logger.info("="*60)
    defense_thresholds = [random.uniform(0.0, 1.0) for _ in range(NUM_UNITS)]  # ! 随机生成的防御阈值
    
    # 1. 创建FusionSystem实例
    logger.info("\n[1] Creating adaptive FusionSystem...")
    fusion_system = FusionSystem(min_active_units=MIN_ACTIVE_UNITS)
    
    # 添加执行单元
    for i in range(NUM_UNITS):
        unit_id = f"unit_{i}"
        # defense_threshold = 0.3  + 0.05 * i
        # defense_threshold = 0.5
        fusion_system.add_unit(
            unit_id=unit_id, 
            weight=1.0, 
            error_threshold=1, 
            attack_threshold=defense_thresholds[i]
        )
    
    # 2. 创建vanilleDHR实例
    logger.info("\n[2] Creating vanilleDHR system...")
    vanilla_dhr = vanilleDHR(min_active_units=MIN_ACTIVE_UNITS)
    
    # 添加相同配置的执行单元
    for i in range(NUM_UNITS):
        unit_id = f"unit_{i}"
        vanilla_dhr.add_unit(
            unit_id=unit_id, 
            attack_threshold=defense_thresholds[i]
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
    
    # 比较vanilleDHR替换次数
    adaptive_replacements = adaptive_summary.get("vanilla_replacement_count", 0)
    vanilla_replacements = vanilla_summary.get("vanilla_replacement_count", 0)
    
    logger.info(f"VanilleDHR Replacement Count:")
    logger.info(f"- Adaptive FusionSystem: {adaptive_replacements}")
    logger.info(f"- Static vanilleDHR: {vanilla_replacements}")
    if adaptive_replacements != vanilla_replacements:
        logger.info(f"- Difference: {abs(adaptive_replacements - vanilla_replacements)}")
        if vanilla_replacements > adaptive_replacements:
            logger.info("- Static vanilleDHR had more replacements")
        else:
            logger.info("- Adaptive FusionSystem had more replacements")
    else:
        logger.info("- Both systems had the same number of replacements")
    
    # 8. 错误信号率分析
    logger.info("\n[8] Analyzing ERROR_SIGNAL rates...")
    compare_error_signal_rates(adaptive_simulator, vanilla_simulator)
    
    logger.info("\n" + "="*60)
    logger.info("SIMULATION COMPLETED SUCCESSFULLY")
    logger.info("="*60)
    
    # 8. 比较错误率
    logger.info("\n[8] Comparing ERROR_SIGNAL rates...\n")
    compare_error_signal_rates(adaptive_simulator, vanilla_simulator)
