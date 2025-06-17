"""
攻击信号生成器 - 为多个模拟器提供统一的攻击信号序列
"""

import random
from typing import List, Dict, Optional
from logger_config import setup_logger

# 设置日志记录器
logger = setup_logger("AttackSignalGenerator")


class AttackSignalGenerator:
    """攻击信号生成器类 - 生成一致的攻击信号序列，可被多个模拟器共享使用"""
    
    def __init__(self, seed: Optional[int] = None, min_strength: float = 0.1, max_strength: float = 1.0):
        """
        初始化攻击信号生成器
        
        Args:
            seed: 随机数种子，确保生成的攻击序列可复现
            min_strength: 攻击强度最小值
            max_strength: 攻击强度最大值
        """
        self.seed = seed
        self.min_strength = min_strength
        self.max_strength = max_strength
        self.attack_sequence = []  # 预生成的攻击序列
        self.current_round = 0
        
        # 设置随机数种子
        if seed is not None:
            random.seed(seed)
            
        logger.info(f"AttackSignalGenerator initialized with seed={seed}, "
                   f"strength_range=[{min_strength:.2f}, {max_strength:.2f}]")
    
    def generate_attack_strength(self) -> float:
        """生成单个攻击强度值"""
        return random.uniform(self.min_strength, self.max_strength)
    
    def pregenerate_attack_sequence(self, num_rounds: int) -> None:
        """
        预生成指定轮数的攻击序列
        
        Args:
            num_rounds: 要生成的攻击轮数
        """
        # 重置随机种子确保一致性
        if self.seed is not None:
            random.seed(self.seed)
            
        self.attack_sequence = []
        for round_idx in range(num_rounds):
            attack_strength = self.generate_attack_strength()
            attack_signal = {
                "round": round_idx,
                "attack_strength": attack_strength,
                "timestamp": round_idx  # 可以用实际时间戳替换
            }
            self.attack_sequence.append(attack_signal)
        
        self.current_round = 0
        logger.info(f"Pre-generated {num_rounds} attack signals")
        sample_strengths = [f"{signal['attack_strength']:.3f}" for signal in self.attack_sequence[:5]]
        logger.info(f"Sample attack strengths (first 5): {sample_strengths}")
    
    def get_next_attack_signal(self) -> Optional[Dict]:
        """
        获取下一个攻击信号
        
        Returns:
            攻击信号字典，如果序列已耗尽则返回None
        """
        if self.current_round >= len(self.attack_sequence):
            logger.warning(f"Attack sequence exhausted at round {self.current_round}")
            return None
            
        attack_signal = self.attack_sequence[self.current_round]
        self.current_round += 1
        
        logger.debug(f"Providing attack signal for round {attack_signal['round']}: "
                    f"strength={attack_signal['attack_strength']:.3f}")
        
        return attack_signal
    
    def get_attack_signal_by_round(self, round_idx: int) -> Optional[Dict]:
        """
        根据轮次索引获取特定的攻击信号
        
        Args:
            round_idx: 轮次索引（从0开始）
            
        Returns:
            攻击信号字典，如果索引超出范围则返回None
        """
        if round_idx < 0 or round_idx >= len(self.attack_sequence):
            logger.warning(f"Invalid round index {round_idx}, sequence length: {len(self.attack_sequence)}")
            return None
            
        return self.attack_sequence[round_idx]
    
    def reset_sequence(self) -> None:
        """重置序列到开始位置"""
        self.current_round = 0
        logger.info("Attack sequence reset to beginning")
    
    def get_sequence_info(self) -> Dict:
        """
        获取攻击序列的统计信息
        
        Returns:
            包含序列统计信息的字典
        """
        if not self.attack_sequence:
            return {
                "total_rounds": 0,
                "current_round": self.current_round,
                "remaining_rounds": 0,
                "avg_strength": 0.0,
                "min_strength": 0.0,
                "max_strength": 0.0
            }
        
        strengths = [signal["attack_strength"] for signal in self.attack_sequence]
        
        return {
            "total_rounds": len(self.attack_sequence),
            "current_round": self.current_round,
            "remaining_rounds": len(self.attack_sequence) - self.current_round,
            "avg_strength": sum(strengths) / len(strengths),
            "min_strength": min(strengths),
            "max_strength": max(strengths),
            "configured_min": self.min_strength,
            "configured_max": self.max_strength,
            "seed": self.seed
        }
    
    def log_sequence_summary(self) -> None:
        """记录攻击序列摘要信息到日志"""
        info = self.get_sequence_info()
        
        logger.info("Attack Sequence Summary:")
        logger.info(f"  Total rounds: {info['total_rounds']}")
        logger.info(f"  Current round: {info['current_round']}")
        logger.info(f"  Remaining rounds: {info['remaining_rounds']}")
        logger.info(f"  Average strength: {info['avg_strength']:.3f}")
        logger.info(f"  Strength range: [{info['min_strength']:.3f}, {info['max_strength']:.3f}]")
        logger.info(f"  Configured range: [{info['configured_min']:.3f}, {info['configured_max']:.3f}]")
        logger.info(f"  Random seed: {info['seed']}")


# 示例用法
if __name__ == "__main__":
    # 创建攻击信号生成器
    attack_generator = AttackSignalGenerator(seed=114514, min_strength=0.2, max_strength=0.9)
    
    # 预生成10轮攻击信号
    attack_generator.pregenerate_attack_sequence(10)
    
    # 显示序列信息
    attack_generator.log_sequence_summary()
    
    # 模拟获取攻击信号
    logger.info("\nSimulating attack signal consumption:")
    for i in range(12):  # 故意超出序列长度以测试边界情况
        signal = attack_generator.get_next_attack_signal()
        if signal:
            logger.info(f"Round {signal['round']}: attack_strength={signal['attack_strength']:.3f}")
        else:
            logger.info(f"No more attack signals available (attempted round {i})")
    
    # 重置并再次获取
    logger.info("\nResetting sequence and getting specific signals:")
    attack_generator.reset_sequence()
    
    # 获取特定轮次的信号
    for round_idx in [0, 3, 5, 15]:  # 包含一个无效索引
        signal = attack_generator.get_attack_signal_by_round(round_idx)
        if signal:
            logger.info(f"Round {round_idx}: attack_strength={signal['attack_strength']:.3f}")
        else:
            logger.info(f"Round {round_idx}: signal not available")
