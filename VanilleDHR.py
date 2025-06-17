from collections import defaultdict

# === 全局变量定义 ===
CORRECT_SIGNAL = "A"  # 正确信号
ERROR_SIGNAL = "B"    # 错误信号

class ExecutionUnit:
    def __init__(self, unit_id, weight=1.0, error_threshold=1, recovery_threshold=1,
                 attack_threshold=0.5):
        self.unit_id = unit_id
        self.weight = weight
        self.error_threshold = error_threshold
        self.recovery_threshold = recovery_threshold
        self.attack_threshold = attack_threshold
        self.active = True
        self.consecutive_corrects = 0


    def generate_output(self, attack_signal):
        return ERROR_SIGNAL if attack_signal > self.attack_threshold else CORRECT_SIGNAL

    def record_result(self, is_correct):
        if not is_correct and self.active:
            self.active = False
            self.consecutive_corrects = 0
            print(f"[vanilleDHR] 执行体 {self.unit_id} 输出与融合结果不一致，疑似被攻击，已置为非活跃状态")


class vanilleDHR:
    """
    简化版分布式异构冗余系统，所有执行体权重相等，基于少数服从多数原则进行投票
    不包含参数更新、软下线等复杂功能，直接使用ExecutionUnit构建执行体
    """
    def __init__(self, min_active_units=3):
        """
        初始化基本DHR系统
        
        Args:
            min_active_units: 最小活跃单元数量
        """
        self.units = {}  # 存储所有执行单元
        self.min_active_units = min_active_units
        self.checkFlag = False
        
    def add_unit(self, unit_id, attack_threshold=0.5):
        """
        添加一个执行单元
        
        Args:
            unit_id: 执行单元ID
            attack_threshold: 攻击阈值，用于决定输出信号
        """
        # 使用ExecutionUnit类创建执行单元，将weight固定为1.0
        self.units[unit_id] = ExecutionUnit(
            unit_id=unit_id, 
            weight=1.0,  # 固定权重为1.0
            attack_threshold=attack_threshold
        )
    
    def collect_outputs(self, attack_signals):
        outputs = {}
        for unit_id, unit in self.units.items():
            attack_strength = attack_signals.get(unit_id, 0.0)
            outputs[unit_id] = unit.generate_output(attack_strength)   
        return outputs
    
    def fuse_outputs_with_replacement(self, outputs):
        vote_counts = defaultdict(int)
        
        for uid, output in outputs.items():
            unit = self.units.get(uid)
            if unit and unit.active:
                vote_counts[output] += 1

        max_vote = max(vote_counts.items(), key=lambda x: x[1])
        # 检查是否有平局的情况
        ties = [vote for vote, count in vote_counts.items() if count == max_vote[1]]
        
        # 如果平局且包含正确信号，则优先返回正确信号
        if len(ties) > 1:
            self._replace_all_units()  # 替换所有执行体
            return CORRECT_SIGNAL
        else: 
            return max_vote[0]
    
    def get_decision(self, attack_signals):
        """
        一步完成输出收集和融合过程
        
        Args:
            attack_signals: 攻击信号字典
            
        Returns:
            融合决策结果和详细统计信息
        """
        outputs = self.collect_outputs(attack_signals)
        decision = self.fuse_outputs_with_replacement(outputs)
        
        # 统计输出情况
        stats = {
            "total_units": len(self.units),
            "active_units": sum(1 for u in self.units.values() if u.active),
            "outputs": outputs,
            "output_counts": {
                CORRECT_SIGNAL: sum(1 for o in outputs.values() if o == CORRECT_SIGNAL),
                ERROR_SIGNAL: sum(1 for o in outputs.values() if o == ERROR_SIGNAL)
            },
            "decision": decision
        }
        
        return decision, stats
         
    def get_status(self):
        """
        获取DHR系统当前状态
        
        Returns:
            系统状态字典
        """
        return {
            "total_units": len(self.units),
            "active_units": sum(1 for u in self.units.values() if u.active),
            "units": {uid: {
                        "active": u.active, 
                        "attack_threshold": u.attack_threshold,
                        "weight": u.weight
                      } for uid, u in self.units.items()}
        }
    
    def update_feedback(self, outputs, fused_output):
        """
        简单版反馈更新 - vanilleDHR不更新权重，但会跟踪错误次数
        
        Args:
            outputs: 各执行单元的输出信号字典
            fused_output: 融合后的输出信号
        """
        for unit_id, output in outputs.items():
            unit = self.units.get(unit_id)
            if not unit:
                continue

            is_correct = (output == fused_output)
            unit.record_result(is_correct)  # 如果输出不一致，记录unit的错误，并将unit.active设为False

            # 简单记录连续错误次数，不进行软下线操作
            if is_correct:
                unit.consecutive_corrects = 0
            else:
                unit.consecutive_corrects += 1

    def _replace_all_units(self):
        old_ids = list(self.units.keys())
        self.units.clear()
        for oid in old_ids:
            self.add_unit(oid + "_replaced", attack_threshold=0.5)
        print("[替换] 所有执行体已替换")

        self.checkFlag  = True  # 标记替换操作已发生