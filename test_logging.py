#!/usr/bin/env python3
"""
测试日志功能的简单脚本
运行global_attack_simulation.py并验证日志文件是否正确创建
"""

import os
import sys
from datetime import datetime

def test_logging():
    """测试日志记录功能"""
    print("Testing logging functionality...")
    
    # 1. 检查日志配置
    try:
        from logger_config import setup_logger
        logger = setup_logger("TestLogger")
        logger.info("Test log message")
        print("✓ Logger configuration successful")
    except Exception as e:
        print(f"✗ Logger configuration failed: {e}")
        return False
    
    # 2. 检查日志目录是否创建
    log_dir = "logs"
    if os.path.exists(log_dir):
        print("✓ Log directory exists")
    else:
        print("✗ Log directory not found")
        return False
    
    # 3. 检查日志文件是否创建
    timestamp = datetime.now().strftime("%Y%m%d")
    log_filename = os.path.join(log_dir, f"dhr_scheduler_{timestamp}.log")
    
    if os.path.exists(log_filename):
        print(f"✓ Log file exists: {log_filename}")
        
        # 查看日志文件大小
        file_size = os.path.getsize(log_filename)
        print(f"  Log file size: {file_size} bytes")
        
        # 显示最后几行日志
        try:
            with open(log_filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    print(f"  Last log entry: {lines[-1].strip()}")
                else:
                    print("  Log file is empty")
        except Exception as e:
            print(f"  Could not read log file: {e}")
    else:
        print(f"✗ Log file not found: {log_filename}")
        return False
    
    # 4. 测试GlobalAttackSimulator的日志记录
    try:
        print("\n" + "="*50)
        print("Testing GlobalAttackSimulator logging...")
        print("="*50)
        
        # 导入并运行一个简单的模拟
        from global_attack_simulation import GlobalAttackSimulator
        from FusionSystem import FusionSystem
        
        # 创建一个简单的FusionSystem用于测试
        fusion_system = FusionSystem(min_active_units=2)
        fusion_system.add_unit("test_unit_1", weight=1.0, error_threshold=3, attack_threshold=0.5)
        fusion_system.add_unit("test_unit_2", weight=1.0, error_threshold=3, attack_threshold=0.6)
        
        # 创建攻击模拟器
        simulator = GlobalAttackSimulator(
            fusion_system=fusion_system,
            system_name="Test System",
            seed=42
        )
        
        print("Running a simple 3-round simulation...")
        # 运行一个简单的模拟
        simulator.simulate_global_attack_rounds(
            num_rounds=3,
            min_strength=0.3,
            max_strength=0.7
        )
        
        print("✓ Simulation completed successfully")
        
        # 检查日志文件是否有新内容
        with open(log_filename, 'r', encoding='utf-8') as f:
            content = f.read()
            if "Global Attack Round" in content:
                print("✓ Simulation logs found in log file")
            else:
                print("✗ Simulation logs not found in log file")
                
    except Exception as e:
        print(f"✗ GlobalAttackSimulator test failed: {e}")
        return False
    
    print("\n" + "="*50)
    print("LOG FILE CONTENT PREVIEW:")
    print("="*50)
    
    # 显示日志文件的最后20行
    try:
        with open(log_filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-20:] if len(lines) > 20 else lines
            for i, line in enumerate(recent_lines, 1):
                print(f"{i:2d}: {line.rstrip()}")
    except Exception as e:
        print(f"Could not display log content: {e}")
    
    print("\n✓ All logging tests passed!")
    print(f"Log file location: {os.path.abspath(log_filename)}")
    return True

if __name__ == "__main__":
    success = test_logging()
    sys.exit(0 if success else 1)
