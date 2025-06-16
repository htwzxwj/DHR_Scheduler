import time
from collections import defaultdict
import math

# === 全局变量定义 ===
CORRECT_SIGNAL = "A"  # 正确信号
ERROR_SIGNAL = "B"    # 错误信号

class ExecutionUnit:
    def __init__(self, unit_id, weight=1.0, error_threshold=3, recovery_threshold=1, attack_threshold=0.5):
        self.unit_id = unit_id
        self.weight = weight
        self.error_threshold = error_threshold
        self.recovery_threshold = recovery_threshold
        self.attack_threshold = attack_threshold

        self.consecutive_errors = 0
        self.active = True
        self.soft_retired = False

    def generate_output(self, attack_signal):
        if attack_signal > self.attack_threshold:
            return ERROR_SIGNAL
        else:
            return CORRECT_SIGNAL


class FusionSystem:
    def __init__(self, min_active_units=3):
        self.units = {}
        self.min_active_units = min_active_units

    def add_unit(self, unit_id, **kwargs):
        self.units[unit_id] = ExecutionUnit(unit_id, **kwargs)

    def collect_outputs(self, attack_signals):
        outputs = {}
        for unit_id, unit in self.units.items():
            if unit.active:
                atk_sig = attack_signals.get(unit_id, 0.0)
                outputs[unit_id] = unit.generate_output(atk_sig)
        return outputs

    def fuse_outputs(self, outputs):
        label_weights = defaultdict(float)
        for unit_id, label in outputs.items():
            unit = self.units.get(unit_id)
            if unit and unit.active:
                label_weights[label] += unit.weight
        if not label_weights:
            return None
        return max(label_weights.items(), key=lambda x: x[1])[0]

    def update_feedback(self, outputs, fused_output):
        """
        统一在这里更新每个执行体状态（替代原 ExecutionUnit.update 方法）
        """
        for unit_id, output in outputs.items():
            unit = self.units.get(unit_id)
            if not unit:
                continue

            is_correct = (output == fused_output)

            if unit.soft_retired:
                # 软下线状态下，输出正确则恢复
                if is_correct:
                    unit.consecutive_errors = 0
                    unit.soft_retired = False
                    unit.active = True
                    print(f"[恢复] 执行体 {unit.unit_id} 恢复上线")
                else:
                    unit.consecutive_errors += 1
                continue

            # 激活状态下更新连续错误计数
            if is_correct:
                unit.consecutive_errors = 0
            else:
                unit.consecutive_errors += 1
                if unit.consecutive_errors >= unit.error_threshold:
                    unit.soft_retired = True
                    unit.active = False
                    print(f"[软下线] 执行体 {unit.unit_id} 连续错误{unit.consecutive_errors}次，暂时下线")

    # 其他方法保持不变


    def update_weights(self, decay_factor=0.5):
        """
        动态调整执行体权重：连续错误越多，权重越小
        """
        for unit in self.units.values():
            unit.weight = math.exp(-decay_factor * unit.consecutive_errors)

        total_weight = sum(u.weight for u in self.units.values())
        if total_weight > 0:
            for u in self.units.values():
                u.weight /= total_weight  # 归一化权重
        else:
            # 所有权重为0，则均分
            n = len(self.units)
            for u in self.units.values():
                u.weight = 1.0 / n

    def try_replace_if_needed(self):
        """
        如果当前活跃执行体数量小于最小要求，尝试替换软下线中最差的一个
        """
        active_units = [u for u in self.units.values() if u.active]
        if len(active_units) >= self.min_active_units:
            return

        soft_retired_units = [u for u in self.units.values() if u.soft_retired]
        if not soft_retired_units:
            print("[替换] 无软下线执行体可替换")
            return

        # 找出连续错误最多的软下线执行体并替换
        worst = max(soft_retired_units, key=lambda u: u.consecutive_errors)
        print(f"[替换] 替换软下线执行体 {worst.unit_id}")
        del self.units[worst.unit_id]

        new_id = worst.unit_id + "_new"
        self.add_unit(new_id)
        print(f"[添加] 新执行体 {new_id} 已上线")

    def get_status(self):
        """
        获取当前所有执行体的状态信息
        """
        status = {}
        for uid, u in self.units.items():
            status[uid] = {
                "weight": round(u.weight, 3),
                "active": u.active,
                "soft_retired": u.soft_retired,
                "error_count": u.consecutive_errors,
            }
        return status

# === 示例主程序 ===
if __name__ == "__main__":
    fusion = FusionSystem(min_active_units=3)

    # 初始化5个执行体
    for i in range(1, 6):
        fusion.add_unit(f"unit_{i}", weight=1.0, error_threshold=3, attack_threshold=0.6)

    # 模拟攻击场景序列
    attack_scenarios = [
        {"unit_1": 0.1, "unit_2": 0.1, "unit_3": 0.8, "unit_4": 0.1, "unit_5": 0.1},
        {"unit_1": 0.8, "unit_2": 0.1, "unit_3": 0.8, "unit_4": 0.1, "unit_5": 0.1},
        {"unit_1": 0.8, "unit_2": 0.8, "unit_3": 0.8, "unit_4": 0.8, "unit_5": 0.1},
        {"unit_1": 0.8, "unit_2": 0.8, "unit_3": 0.8, "unit_4": 0.8, "unit_5": 0.1},
        {"unit_1": 0.8, "unit_2": 0.8, "unit_3": 0.8, "unit_4": 0.8, "unit_5": 0.8},
        {"unit_1": 0.1, "unit_2": 0.8, "unit_3": 0.8, "unit_4": 0.8, "unit_5": 0.8},
        {"unit_1": 0.1, "unit_2": 0.8, "unit_3": 0.8, "unit_4": 0.8, "unit_5": 0.8},
    ]

    # 模拟每一轮攻击并输出系统状态
    for i, atk in enumerate(attack_scenarios):
        print(f"\n--- Round {i + 1} ---")
        outputs = fusion.collect_outputs(atk)  # 收集输出
        fused = fusion.fuse_outputs(outputs)  # 融合输出
        print(f"攻击输入: {atk}")
        print(f"输出: {outputs}")
        print(f"融合输出: {fused}")
        fusion.update_feedback(outputs, fused)  # 更新执行体状态
        fusion.update_weights()  # 更新权重
        fusion.try_replace_if_needed()  # 尝试替换下线执行体
        print(f"状态: {fusion.get_status()}")  # 输出当前状态
