from collections import defaultdict, deque
import math
from scipy.stats import beta
from logger_config import default_logger as logger


# === 全局变量定义 ===
CORRECT_SIGNAL = "A"  # 正确信号
# ERROR_SIGNAL = ["B", "D", "E", "F", "1", "2", "3", "11", "22", "33"]   
# ERROR_SIGNAL = ["B", "D", "E", "F"]    # 错误信号
ERROR_SIGNAL = ["B"]    # 错误信号
SCHEDULED_SIGNAL = "C"  # 调度信号，表示需要替换执行体

def chooseERROR_SIGNAL(attackResult):
    """随机选择一个错误信号"""
    n = len(ERROR_SIGNAL)
    idx = min(int(attackResult * n), n - 1)
    return ERROR_SIGNAL[idx]


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
        # self.unit_output = CORRECT_SIGNAL  # ! 执行体输出，默认为正确信号
        self.recent_results = deque(maxlen=bayes_window)  # 窗口缓存正确/错误
        self.consecutive_corrects = 0

        for i in range(bayes_window):
            self.recent_results.append((True))


    def generate_output(self, attack_signal):
        attackResult = attack_signal - self.attack_threshold
        self.result = chooseERROR_SIGNAL(attackResult) if attackResult >= 0 else CORRECT_SIGNAL
        return self.result

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
    def __init__(self):
        self.units = {}
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
    

    # def compute_entropy(self, label_weights):
    #     total = sum(label_weights.values())
    #     if total == 0:
    #         return 1.0
    #     return -sum((w / total) * math.log2(w / total) for w in label_weights.values() if w > 0)

    def compute_entropy(self):
        # 统计每个输出标签的总权重
        label_weight = {}
        for unit in self.units.values():
            if unit.active:
                label = unit.result
                label_weight[label] = label_weight.get(label, 0.0) + unit.weight
        n = len(label_weight)
        if n <= 1:
            return 0.0
        mean = [w for w in label_weight.values() if w > 0]
        mean = sum(mean) / n
        variance = sum((w - mean) ** 2 for w in label_weight.values()) / n
        max_var = mean ** 2 * (n - 1)
        return variance / max_var if max_var > 0 else 0.0
    

    def compute_entropy_threshold(self, alpha=0.7):
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
    
    def judge(self, trust_threshold=0.4):  # ! 融合裁决
        outputs = self.outputs
        label_weights = defaultdict(float)
        weightSum = 0.0
        for uid, lbl in outputs.items():
            unit = self.units.get(uid)
            if unit and unit.active:
                label_weights[lbl] += unit.weight
                weightSum += unit.weight

        entropy = self.compute_entropy()
        labels = set(label_weights.keys())
        def avg_accuracy(label):
            if label is None:
                return 0.0
            units = [self.units[uid] for uid, lbl in outputs.items()
                     if lbl == label and self.units[uid].active]
            if not units:
                return 0.0
            return sum(u.beta_accuracy() for u in units) / len(units)
        output_dict = {}
        for lbl in labels:
            acc = avg_accuracy(lbl)
            output_dict[lbl] = acc

        entropy_threshold = self.compute_entropy_threshold()

        if all(acc < trust_threshold for acc in output_dict.values()):
            logger.info(f"[触发替换] 主标签和所有其他标签准确率均低于阈值 {trust_threshold:.2f}，触发执行体替换")
            self.isScheduled = True
            return SCHEDULED_SIGNAL
        if entropy >= entropy_threshold:
            logger.info(f"[高熵条件] 熵值 {entropy:.4f} 超过阈值 {entropy_threshold:.4f}，触发执行体替换")
            self.isScheduled = True
            return SCHEDULED_SIGNAL
        sorted_labels = sorted(label_weights.items(), key=lambda x: x[1], reverse=True)
        for lbl, _ in sorted_labels:
            if output_dict[lbl] >= trust_threshold:
                return lbl
        return sorted_labels[0][0] if sorted_labels else None

        
        # # 选择置信度（准确率）最大的标签，如果有多个，选择权重最大的标签
        # max_acc = max(output_dict.values())
        # max_acc_labels = [lbl for lbl, acc in output_dict.items() if acc == max_acc]
        # if len(max_acc_labels) == 1:
        #     return max_acc_labels[0]
        # else:
        #     # 多个标签置信度最大，选择权重最大的
        #     label_weights = {lbl: label_weights[lbl] for lbl in max_acc_labels}
        #     return max(label_weights.items(), key=lambda x: x[1])[0]



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
