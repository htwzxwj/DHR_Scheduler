from collections import defaultdict, deque
import math
from scipy.stats import beta
from logger_config import default_logger as logger
import sys


# === 全局变量定义 ===
CORRECT_SIGNAL = "A"  # 正确信号
ERROR_SIGNAL = "B"    # 错误信号

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

    def record_result(self, is_correct):
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
            if not is_correct:
                self.soft_retired = True
                self.active = False
                self.consecutive_corrects = 0
                logger.warning(f"[软下线] 执行体 {self.unit_id} 输出与融合结果不一致，疑似被攻击")

    def beta_accuracy(self):
        correct = sum(self.recent_results)
        total = len(self.recent_results)
        a = correct + 1
        b = total - correct + 1
        return beta.mean(a, b)


class FusionSystem:
    def __init__(self, min_active_units=3):
        self.units = {}
        self.min_active_units = min_active_units
        self.checkFlag = False

    def add_unit(self, unit_id, **kwargs):
        self.units[unit_id] = ExecutionUnit(unit_id, **kwargs)

    def collect_outputs(self, attack_signals):
        outputs = {}
        for uid, unit in self.units.items():
            sig = attack_signals.get(uid, 0.0)
            outputs[uid] = unit.generate_output(sig)
        return outputs

    def compute_entropy(self, label_weights):
        total = sum(label_weights.values())
        if total == 0:
            return 1.0
        return -sum((w / total) * math.log2(w / total) for w in label_weights.values() if w > 0)

    def fuse_outputs_with_replacement(self, outputs, entropy_threshold=0.8, trust_threshold=0.9):
        label_weights = defaultdict(float)
        for uid, lbl in outputs.items():
            unit = self.units.get(uid)
            if unit and unit.active:
                label_weights[lbl] += unit.weight

        if not label_weights:
            logger.warning("[警告] 无在线的执行体，执行体全量替换")
            self.checkFlag = True
            self._replace_all_units()
            return CORRECT_SIGNAL

        entropy = self.compute_entropy(label_weights)

        labels = set(label_weights.keys())
        majority_label = max(label_weights.items(), key=lambda x: x[1])[0]
        other_labels = labels - {majority_label}
        other_label = other_labels.pop() if other_labels else None

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

        # 熵大且主标签准确率低于另一标签，触发替换
        if entropy > entropy_threshold and majority_acc < other_acc:
            logger.info("[触发替换] 熵大且主标签准确率低于另一标签，触发执行体替换")
            self.checkFlag = True
            self._replace_all_units()
            return CORRECT_SIGNAL

        # 主标签准确率足够高，返回主标签
        if majority_acc >= trust_threshold:
            return majority_label

        # 主标签准确率不够高但另一标签达标，返回另一标签
        if other_acc >= trust_threshold:
            logger.info(f"[返回另一标签] 主标签准确率低，返回另一标签 {other_label}")
            return other_label

        # 两者准确率都不达标，触发替换
        logger.info("[软降级] 主标签和另一标签准确率均低，触发执行体替换")
        self.checkFlag = True
        self._replace_all_units()
        return CORRECT_SIGNAL

    def update_feedback(self, outputs, fused_output, trust_threshold=0.5):
        for uid, out in outputs.items():
            unit = self.units.get(uid)
            if not unit:
                continue

            is_correct = (out == fused_output)
            unit.record_result(is_correct)

            # 软下线条件：准确率低于阈值 或 本轮输出与融合结果不一致
            acc = unit.beta_accuracy()
            if unit.active and (acc < trust_threshold or not is_correct):
                unit.soft_retired = True
                unit.active = False
                logger.info(f"[软下线] 执行体 {uid} 的准确率 {acc:.2f} 低于阈值 {trust_threshold} 或输出与融合结果不符")

    def update_weights(self, decay_factor=0.5):
        temp = {}
        for uid, unit in self.units.items():
            if unit.soft_retired:
                unit.weight = 0.0
                continue

            beta_mean = unit.beta_accuracy()
            penalty = math.exp(-decay_factor * (1 - beta_mean))  # 越不准惩罚越重
            temp[uid] = beta_mean * penalty

        total = sum(temp.values())
        if total == 0:
            avg = 1.0 / len(self.units)
            for unit in self.units.values():
                unit.weight = avg
        else:
            for uid, score in temp.items():
                self.units[uid].weight = score / total

    def _replace_all_units(self):
        old_ids = list(self.units.keys())
        self.units.clear()
        for oid in old_ids:
            self.add_unit(oid + "_replaced")
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
