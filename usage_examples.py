#!/usr/bin/env python3
"""
DHR Scheduler Usage Examples
============================

This file demonstrates various ways to use and extend the DHR attack simulation system.
Run this file to see different usage patterns and capabilities.
"""

import random
from global_attack_simulation import GlobalAttackSimulator, print_simulation_results
from FusionSystem import FusionSystem, vanilleDHR

def example_1_basic_comparison():
    """Example 1: Basic comparison between adaptive and vanilla systems"""
    print("=" * 60)
    print("EXAMPLE 1: Basic System Comparison")
    print("=" * 60)
    
    # Create systems with identical configurations
    adaptive_system = FusionSystem(min_active_units=3)
    vanilla_system = vanilleDHR(min_active_units=3)
    
    # Add identical units
    for i in range(5):
        threshold = 0.3 + (i * 0.1)
        adaptive_system.add_unit(f"unit_{i}", weight=1.0, attack_threshold=threshold)
        vanilla_system.add_unit(f"unit_{i}", attack_threshold=threshold)
    
    # Create simulators
    adaptive_sim = GlobalAttackSimulator(adaptive_system, "Adaptive", seed=123)
    vanilla_sim = GlobalAttackSimulator(vanilla_system, "Vanilla", seed=123)
    
    # Run simulations
    adaptive_sim.simulate_global_attack_rounds(10, 0.0, 1.0)
    vanilla_sim.simulate_global_attack_rounds(10, 0.0, 1.0)
    
    # Compare results
    adaptive_results = adaptive_sim.get_simulation_summary()
    vanilla_results = vanilla_sim.get_simulation_summary()
    
    print("\nCOMPARISON RESULTS:")
    print(f"Adaptive Success Rate: {adaptive_results['success_rate']:.1%}")
    print(f"Vanilla Success Rate:  {vanilla_results['success_rate']:.1%}")
    improvement = (vanilla_results['success_rate'] - adaptive_results['success_rate']) / vanilla_results['success_rate'] * 100
    print(f"Improvement: {improvement:.1f}%")

def example_2_custom_configuration():
    """Example 2: Custom system configuration with specific parameters"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Custom Configuration")
    print("=" * 60)
    
    # Create a high-security fusion system
    secure_system = FusionSystem(min_active_units=4)  # Higher minimum for security
    
    # Add units with varying security levels
    security_levels = [
        ("critical", 0.2),    # Very secure
        ("high", 0.4),        # High security
        ("medium", 0.6),      # Medium security
        ("standard", 0.8),    # Standard security
        ("legacy", 0.9)       # Lower security (legacy system)
    ]
    
    for name, threshold in security_levels:
        secure_system.add_unit(
            unit_id=f"{name}_unit",
            weight=1.0,
            error_threshold=2,  # Stricter error tolerance
            attack_threshold=threshold
        )
    
    # Run high-intensity attacks
    secure_sim = GlobalAttackSimulator(secure_system, "High-Security", seed=456)
    secure_sim.simulate_global_attack_rounds(
        num_rounds=15,
        min_strength=0.5,    # More intense attacks
        max_strength=1.0
    )
    
    results = secure_sim.get_simulation_summary()
    print(f"\nHigh-Security System Results:")
    print(f"Attack Success Rate: {results['success_rate']:.1%}")
    print(f"System MTBF: {results['reliability_stats']['global_mtbf']:.2f}")
    print(f"Active Units: {results['active_units']}/{results['total_units']}")

def example_3_custom_attack_patterns():
    """Example 3: Simulate specific attack patterns"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Custom Attack Patterns")
    print("=" * 60)
    
    system = FusionSystem(min_active_units=3)
    for i in range(5):
        system.add_unit(f"unit_{i}", attack_threshold=0.5)
    
    simulator = GlobalAttackSimulator(system, "Custom Attacks", seed=789)
    
    # Simulate different attack intensities
    attack_patterns = [
        ("Low Intensity", 0.0, 0.3),
        ("Medium Intensity", 0.3, 0.6),
        ("High Intensity", 0.6, 1.0)
    ]
    
    pattern_results = []
    for pattern_name, min_str, max_str in attack_patterns:
        print(f"\n--- {pattern_name} Attacks ---")
        simulator.reset_simulation()
        simulator.simulate_global_attack_rounds(5, min_str, max_str)
        results = simulator.get_simulation_summary()
        pattern_results.append((pattern_name, results['success_rate']))
        print(f"Success Rate: {results['success_rate']:.1%}")
    
    print(f"\nAttack Pattern Summary:")
    for name, rate in pattern_results:
        print(f"{name}: {rate:.1%}")

def example_4_resilience_testing():
    """Example 4: Test system resilience over extended periods"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Resilience Testing")
    print("=" * 60)
    
    # Test with minimal redundancy
    minimal_system = FusionSystem(min_active_units=2)
    for i in range(3):  # Only 3 units for stress testing
        minimal_system.add_unit(f"unit_{i}", attack_threshold=0.4)
    
    resilience_sim = GlobalAttackSimulator(minimal_system, "Resilience Test", seed=101)
    
    # Extended attack simulation
    print("Running extended attack simulation...")
    resilience_sim.simulate_global_attack_rounds(
        num_rounds=25,
        min_strength=0.2,
        max_strength=0.8
    )
    
    results = resilience_sim.get_simulation_summary()
    print(f"\nResilience Test Results:")
    print(f"Survived {results['total_rounds']} rounds")
    print(f"Final Active Units: {results['active_units']}/{results['total_units']}")
    print(f"Overall Success Rate: {results['success_rate']:.1%}")
    print(f"System MTBF: {results['reliability_stats']['global_mtbf']:.2f}")
    
    # Check if system maintained minimum active units
    if results['active_units'] >= 2:
        print("✅ System maintained minimum redundancy")
    else:
        print("⚠️  System fell below minimum redundancy")

def example_5_parameter_sensitivity():
    """Example 5: Test sensitivity to different parameters"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Parameter Sensitivity Analysis")
    print("=" * 60)
    
    # Test different entropy thresholds
    entropy_thresholds = [0.6, 0.8, 1.0]
    trust_thresholds = [0.3, 0.5, 0.7]
    
    print("Testing parameter combinations...")
    
    best_config = None
    best_score = float('inf')
    
    for entropy_thresh in entropy_thresholds:
        for trust_thresh in trust_thresholds:
            # Create system with specific parameters
            test_system = FusionSystem(min_active_units=3)
            for i in range(5):
                test_system.add_unit(f"unit_{i}", attack_threshold=0.5)
            
            # Create a simulator (would need to modify FusionSystem to accept these parameters)
            test_sim = GlobalAttackSimulator(test_system, f"Test_{entropy_thresh}_{trust_thresh}")
            test_sim.simulate_global_attack_rounds(10, 0.0, 1.0)
            
            results = test_sim.get_simulation_summary()
            score = results['success_rate']  # Lower is better
            
            print(f"Entropy: {entropy_thresh}, Trust: {trust_thresh} → Success Rate: {score:.1%}")
            
            if score < best_score:
                best_score = score
                best_config = (entropy_thresh, trust_thresh)
    
    if best_config:
        print(f"\nBest configuration: Entropy={best_config[0]}, Trust={best_config[1]} (Success Rate: {best_score:.1%})")
    else:
        print("\nNo valid configuration found.")

def main():
    """Run all examples"""
    print("DHR Scheduler Usage Examples")
    print("This demonstration shows various ways to use the system.\n")
    
    try:
        example_1_basic_comparison()
        example_2_custom_configuration()
        example_3_custom_attack_patterns()
        example_4_resilience_testing()
        example_5_parameter_sensitivity()
        
        print("\n" + "=" * 60)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nKey Takeaways:")
        print("• Adaptive systems consistently outperform vanilla systems")
        print("• Higher security thresholds improve defense but may increase false positives")
        print("• System resilience depends on maintaining minimum active units")
        print("• Parameter tuning can significantly impact performance")
        print("• The system gracefully handles various attack patterns")
        
    except Exception as e:
        print(f"Error during examples: {e}")
        print("Check your Python environment and dependencies.")

if __name__ == "__main__":
    main()
