from collections import defaultdict, deque
import math
from scipy.stats import beta
from logger_config import default_logger as logger


# === 全局变量定义 ===
CORRECT_SIGNAL = "A"  # 正确信号
ERROR_SIGNAL = "B"    # 错误信号
SCHEDULED_SIGNAL = "C"  # 调度信号，表示需要替换执行体

class ExecutionUnit:
    def __init__(self, unit_id, weight=1.0, error_threshold=1, recovery_threshold=1,
                 attack_threshold=0.5, bayes_window=10):
        self.unit_id = unit_id
        self.weight = weight
        self.error_threshold = error_threshold
        self.recovery_threshold = recovery_threshold
        self.attack_threshold = attack_threshold
        self.active = True
        self.soft_retired = False

        self.recent_results = deque(maxlen=bayes_window)  # 窗口缓存正确/错误
        self.consecutive_corrects = 0

        for i in range(bayes_window):
            self.recent_results.append((True))


    def generate_output(self, attack_signal):
        return ERROR_SIGNAL if attack_signal > self.attack_threshold else CORRECT_SIGNAL

    def record_result(self, is_correct, fused_output, trust_threshold=0.5):
        self.recent_results.append(is_correct)
        if self.soft_retired:
            if is_correct:
                self.consecutive_corrects += 1
                if self.consecutive_corrects >= self.recovery_threshold:
                    self.soft_retired = False
                    self.active = True
                    logger.warning(f"[恢复] 执行体 {self.unit_id} 连续正确 {self.recovery_threshold} 次，已恢复上线")
            else:
                self.consecutive_corrects = 0
        else:
            acc = self.beta_accuracy()
            if (not is_correct or acc < trust_threshold) and fused_output != SCHEDULED_SIGNAL: # type: ignore
                self.soft_retired = True
                self.active = False
                self.consecutive_corrects = 0
                # logger.warning(f"[软下线] 执行体 {self.unit_id} 输出与融合结果不一致，疑似被攻击")

                # 软下线条件：准确率低于阈值 或 本轮输出与融合结果不一致
                logger.info(f"[软下线] 执行体 {self.unit_id} 的准确率 {acc:.2f} 低于阈值 {trust_threshold} 或输出与融合结果不符:{is_correct}，融合结果: {fused_output}")

    def beta_accuracy(self):
        correct = sum(self.recent_results)
        total = len(self.recent_results)
        a = correct + 1
        b = total - correct + 1
        return beta.mean(a, b)


class FusionSystem:
    def __init__(self, min_active_units=3):
        self.units = {}
        self.isScheduled = False  # 是否需要调度
        self.min_active_units = min_active_units
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
    

    # def compute_entropy(self, label_weights):
    #     total = sum(label_weights.values())
    #     if total == 0:
    #         return 1.0
    #     return -sum((w / total) * math.log2(w / total) for w in label_weights.values() if w > 0)

    def compute_entropy(self):

        weights = [unit.weight for unit in self.units.values() if unit.active]
        n = len(weights)
        if n <= 1:
            return 0.0

        mean = sum(weights) / n
        variance = sum((w - mean) ** 2 for w in weights) / n
        std_dev = math.sqrt(variance)

        # 可归一化：最大值假设其中一个为1其余为0，即最大偏差 = mean
        max_std_dev = math.sqrt((n - 1) * (mean ** 2) / n)
        return std_dev / max_std_dev if max_std_dev > 0 else 0.0
    

    def compute_entropy_threshold(self, alpha=0.9):
        # num_units = len([u for u in self.units.values() if u.active])
        # if num_units <= 1:
        #     return 999  # 只有一个标签，不存在不确定性
        # max_entropy = math.log2(num_units)
        return alpha
        # return alpha * max_entropy

    
    def output(self):
        fused_output = self.judge()  # ! 融合裁决
        assert fused_output is not None, "融合裁决结果不能为空"
        self.schedule() # ! 调度
        self.update_feedback(self.outputs, fused_output=fused_output)
        

        return fused_output
    
    def recover(self):
        self.isScheduled = False
    
    def judge(self, trust_threshold=0.6):  # ! 融合裁决
        outputs = self.outputs
        label_weights = defaultdict(float)
        weightSum = 0.0
        for uid, lbl in outputs.items():
            unit = self.units.get(uid)
            if unit and unit.active:
                label_weights[lbl] += unit.weight
                weightSum += unit.weight

        # if weightSum < 3.5:
        #     logger.warning("[警告] 权重和少于最小要求，执行体全量替换")
        #     self.isScheduled = True
        #     return CORRECT_SIGNAL
        

        # if not label_weights:
        #     logger.warning("[警告] 无在线的执行体，执行体全量替换")
        #     self.isScheduled = True
        #     return SCHEDULED_SIGNAL

        
        entropy = self.compute_entropy()

        labels = set(label_weights.keys())
        majority_label = max(label_weights.items(), key=lambda x: x[1])[0]
        other_labels = labels - {majority_label}
        other_label = other_labels.pop() if other_labels else None

        # if label_weights[majority_label] < 1.5:
        #     logger.warning("[警告] 权重和少于最小要求，执行体全量替换")
        #     self.isScheduled = True
        #     return SCHEDULED_SIGNAL

        logger.warning(f"[熵信息] 熵值: {entropy:.4f}, 主标签: {majority_label}")

        def avg_accuracy(label):
            if label is None:
                return 0.0
            units = [self.units[uid] for uid, lbl in outputs.items()
                     if lbl == label and self.units[uid].active]
            if not units:
                return 0.0
            return sum(u.beta_accuracy() for u in units) / len(units)

        majority_acc = avg_accuracy(majority_label)
        other_acc = avg_accuracy(other_label)

        logger.info(f"[准确率] 主标签 {majority_label} 平均准确率: {majority_acc:.3f}")
        if other_label is not None:
            logger.info(f"[准确率] 另一标签 {other_label} 平均准确率: {other_acc:.3f}")
        entropy_threshold = self.compute_entropy_threshold()

        if majority_acc < trust_threshold and other_acc < trust_threshold:
            logger.info(f"[触发替换] 主标签或另一标签准确率低于阈值 {trust_threshold:.2f}，触发执行体替换")
            self.isScheduled = True
            return SCHEDULED_SIGNAL
        if entropy >= entropy_threshold:
            logger.info(f"[高熵条件] 熵值 {entropy:.4f} 超过阈值 {entropy_threshold:.4f}，触发执行体替换")
            self.isScheduled = True
            return SCHEDULED_SIGNAL


        return majority_label if majority_acc >= other_acc else other_label  # ! 选择置信度大的



        # # 主标签准确率足够高，返回主标签
        # if other_acc >= trust_threshold and majority_acc >= other_acc and entropy <= entropy_threshold :
        #     return majority_label
        
        # elif majority_acc > other_acc and majority_acc <= trust_threshold:
        #     if entropy >= entropy_threshold:
        #         logger.info("[触发替换] 主标签准确率低于阈值且熵大，触发执行体替换")
        #         self.isScheduled = True
        #         return CORRECT_SIGNAL
        #     else:
        #         return majority_label
        # elif majority_acc < other_acc and other_acc >= trust_threshold:
        #     logger.info(f"[返回另一标签] 主标签准确率低，返回另一标签 {other_label}")
        #     return other_label
        # elif majority_acc < other_acc and other_acc < trust_threshold:
        #     # if entropy >= entropy_threshold:
        #         logger.info("[触发替换] 主标签准确率低且熵大，触发执行体替换")
        #         self.isScheduled = True
        #         return CORRECT_SIGNAL
        #     # else:
        #     #     return majority_label  # 返回主标签，避免错误输出
        # elif majority_acc >= trust_threshold and majority_acc > other_acc and other_acc < trust_threshold:
        #     return majority_label

        # # 情形④：majority >= trust，但准确率低于 other，且 other 不达阈值，熵也不高
        # elif majority_acc >= trust_threshold and other_acc < trust_threshold and entropy < entropy_threshold:
        #     return majority_label

        # # 情形②、③可以合并写成：
        # elif majority_acc >= trust_threshold and majority_acc > other_acc and entropy >= entropy_threshold:
        #     # 你想保守就调度，否则也可直接返回 majority_label
        #     logger.info("[高熵条件] 主标签可信但不确定，触发调度")
        #     self.isScheduled = True
        #     return CORRECT_SIGNAL
        
        
        # else:
        #     logger.info("无法正确裁决，直接调度")
        #     self.isScheduled = True
        #     return CORRECT_SIGNAL

    def schedule(self):
        if self.isScheduled:
            self._replace_all_units()
            self.scheduledNum += 1

        
    def update_feedback(self, outputs, fused_output, decay_factor=0.1):
        for uid, out in outputs.items():
            unit = self.units.get(uid)
            if not unit:
                continue

            is_correct = (out == fused_output) if fused_output != SCHEDULED_SIGNAL else False
            logger.info(f"[反馈] 执行体 {uid} 输出: {out}, 融合结果: {fused_output}, 正确: {is_correct}")
            unit.record_result(is_correct, fused_output)
            if is_correct:
                self.units[uid].weight *= 1 + decay_factor  # ! 正确输出，权重衰减
                if self.units[uid].weight > 1.0:
                    self.units[uid].weight = 1.0
                if self.units[uid].weight < 0.0:
                    self.units[uid].weight = 0.0
            else:
                self.units[uid].weight *= 1 - decay_factor
                if self.units[uid].weight > 1.0:
                    self.units[uid].weight = 1.0
                if self.units[uid].weight < 0.0:
                    self.units[uid].weight = 0.0

    

                # else:
                #     self.units[uid].weight /= score

            # # 软下线条件：准确率低于阈值 或 本轮输出与融合结果不一致
            # acc = unit.beta_accuracy()
            # if unit.active and (acc < trust_threshold or not is_correct):
            #     unit.soft_retired = True
            #     unit.active = False
            #     logger.info(f"[软下线] 执行体 {uid} 的准确率 {acc:.2f} 低于阈值 {trust_threshold} 或输出与融合结果不符")



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
