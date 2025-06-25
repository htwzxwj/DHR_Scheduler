from collections import defaultdict
import random
from logger_config import default_logger as logger
from FusionSystem import ExecutionUnit, CORRECT_SIGNAL, ERROR_SIGNAL, SCHEDULED_SIGNAL

# random.seed(42)  # 固定随机种子以确保可重复性


class vanilleDHR:
    def __init__(self, min_active_units=2):
        self.units = {}
        self.min_active_units = min_active_units
        self.isScheduled = False  # 是否需要调度
        self.scheduledNum = 0
        self.outputs = {}  # 每个执行体的输出，{id，输出}

    def add_unit(self, unit_id, **kwargs):
        self.units[unit_id] = ExecutionUnit(unit_id, **kwargs)

    def collect_outputs(self, attack_signals):
        # outputs = {}
        for uid, unit in self.units.items():
            sig = attack_signals.get(uid, 0.0)
            self.outputs[uid] = unit.generate_output(sig)  # ! 输出类型是CORRECT_SIGNAL或ERROR_SIGNAL
        return self.outputs
    

            
    
    
    def output(self):
        fused_output = self.judge()  # ! 融合裁决
        self.schedule() # ! 调度
        self.update_feedback(self.outputs, fused_output)
        return fused_output
    
    def recover(self):
        self.isScheduled = False
    
    def judge(self):  # 融合结果
        outputs = self.outputs
        vote_counts = defaultdict(int)
        active_units = [uid for uid, unit in self.units.items() if unit.active]
        
        if (len(active_units) < self.min_active_units):
            logger.warning("[警告] 活跃执行体数量少于最小要求，执行体全量替换")
            self.isScheduled = True
            return SCHEDULED_SIGNAL  # 返回正确信号以避免错误输出
        
        for uid, output in outputs.items():
            unit = self.units.get(uid)
            if unit and unit.active:
                vote_counts[output] += 1

        max_vote = max(vote_counts.items(), key=lambda x: x[1])
        # 检查是否有平局的情况
        ties = [vote for vote, count in vote_counts.items() if count == max_vote[1]]

        # 如果平局且包含正确信号，则优先返回正确信号
        if len(ties) > 1:
            self.isScheduled = True  # 标记替换操作已发生
            return SCHEDULED_SIGNAL
        else: 
            return max_vote[0]

    
    def update_feedback(self, outputs, fused_output):
        # outputs = self.outputs
        for uid, out in outputs.items():
            unit = self.units.get(uid)
            if not unit:
                continue

            is_correct = (out == fused_output) if fused_output != SCHEDULED_SIGNAL else False

            unit.record_result(is_correct, fused_output)

    
    def schedule(self):
        if self.isScheduled:
            self._replace_all_units()
            self.scheduledNum += 1
        

    def _replace_all_units(self):
        old_ids = list(self.units.keys())
        self.units.clear()
        for oid in old_ids:
            self.add_unit(oid)
        logger.info("[替换] 所有执行体已替换")

    def get_status(self):
        status = {}
        for uid, unit in self.units.items():
            status[uid] = {
                "weight": round(unit.weight, 3),
                "active": unit.active,
                "soft_retired": unit.soft_retired,
                "recent_correct": sum(unit.recent_results),
                "total_in_window": len(unit.recent_results),
                "beta_mean_accuracy": round(unit.beta_accuracy(), 3)
            }
        return status