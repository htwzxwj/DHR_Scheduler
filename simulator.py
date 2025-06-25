from FusionSystem import CORRECT_SIGNAL, ERROR_SIGNAL, FusionSystem, SCHEDULED_SIGNAL
from VanilleDHR import vanilleDHR
import random
random.seed(42)
from logger_config import default_logger as logger

NUM_UNITS = 5
NUM_ROUNDS = 3000
ATTACK_PROB = 0.6  # * 攻击概率


fusion_A_count = 0
fusion_B_count = 0
dhr_A_count = 0
dhr_B_count = 0
defense_thresholds = [random.uniform(0.0, 1.0) for _ in range(NUM_UNITS)]  # ! 随机生成的防御阈值
recoverTime = 5  # 恢复时间
# 实例化 FusionSystem
fusion_system = FusionSystem()
# 添加执行单元
for i in range(NUM_UNITS):
    fusion_system.add_unit(
        unit_id=f"unit_{i}", 
        weight=1.0, 
        error_threshold=1, 
        attack_threshold=defense_thresholds[i]
    )

dhr = vanilleDHR()
for i in range(NUM_UNITS):
    dhr.add_unit(
        unit_id=f"unit_{i}", 
        attack_threshold=defense_thresholds[i]
    )
tempRecoverTime = 0  # 恢复时间
dhrTempRecoverTime = 0
for i in range(NUM_ROUNDS):
    attack_signals = {f"unit_{i}": random.uniform(0.0, 1.0) for i in range(NUM_UNITS)}  # ! 随机生成的攻击信号

    if random.random() > ATTACK_PROB:
        attack_signals = {f"unit_{i}": 0 for i in range(NUM_UNITS)}
    if fusion_system.isScheduled and tempRecoverTime < recoverTime:
        tempRecoverTime += 1
        # continue
    else:
        tempRecoverTime = 0
        fusion_system.recover()

        output = fusion_system.collect_outputs(attack_signals)
        logger.info(f"Fusion Outputs: {output}")

        fused_output = fusion_system.output()
        logger.info(f"Fusion Fused Output: {fused_output}")
        if fused_output == CORRECT_SIGNAL:
            fusion_A_count += 1
        elif fused_output != CORRECT_SIGNAL:
            fusion_B_count += 1

        for unit_id, unit in fusion_system.units.items():
            pass
            logger.info(f"FusionSystem执行体 {unit_id} 权重: {unit.weight}")
        

    if dhr.isScheduled and dhrTempRecoverTime < recoverTime:
        dhrTempRecoverTime += 1
        # continue
    else:
        dhrTempRecoverTime = 0
        dhr.recover()
    
        output = dhr.collect_outputs(attack_signals)
        logger.info(f"DHR Active Units: {[uid for uid, unit in dhr.units.items() if unit.active]}")
        logger.info(f"DHR Outputs: {output}")
        fused_output = dhr.output()
        logger.info(f"DHR Fused Output: {fused_output}")
        if fused_output == CORRECT_SIGNAL:
            dhr_A_count += 1
        elif fused_output != CORRECT_SIGNAL:
            dhr_B_count += 1


logger.info(f"FusionSystem输出A次数: {fusion_A_count}, 输出B次数: {fusion_B_count}，准确率: {fusion_A_count / (fusion_A_count + fusion_B_count):.2f}")
logger.info(f"vanilleDHR输出A次数: {dhr_A_count}, 输出B次数: {dhr_B_count}，准确率: {dhr_A_count / (dhr_A_count + dhr_B_count):.2f}")

logger.info(f"融合系统调度次数: {fusion_system.scheduledNum}")
logger.info(f"DHR系统调度次数: {dhr.scheduledNum}")
logger.info(f"融合系统平均调度时间: {(dhr.scheduledNum - fusion_system.scheduledNum) / dhr.scheduledNum:.2f}")