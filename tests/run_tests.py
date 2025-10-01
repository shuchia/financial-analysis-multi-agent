#!/usr/bin/env python3
"""
Test runner for onboarding tests.
Run all tests or specific test suites.
"""

import sys
import os
import unittest
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_unit_tests():
    """Run unit tests for onboarding components."""
    print("\n" + "="*60)
    print("RUNNING UNIT TESTS FOR ONBOARDING")
    print("="*60 + "\n")
    
    # Import and run unit tests
    from test_onboarding import (
        TestOnboardingComponents,
        TestOnboardingFlow,
        TestOnboardingHelpers
    )
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add unit test classes
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOnboardingComponents))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOnboardingFlow))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOnboardingHelpers))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_integration_tests():
    """Run integration tests for complete onboarding flow."""
    print("\n" + "="*60)
    print("RUNNING INTEGRATION TESTS FOR ONBOARDING")
    print("="*60 + "\n")
    
    # Import and run integration tests
    from test_integration_onboarding import (
        TestCompleteOnboardingJourney,
        TestOnboardingErrorHandling,
        TestOnboardingAnalytics
    )
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add integration test classes
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCompleteOnboardingJourney))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOnboardingErrorHandling))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOnboardingAnalytics))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_all_tests():
    """Run all onboarding tests."""
    print("\n" + "#"*60)
    print("# ONBOARDING TEST SUITE")
    print(f"# Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*60)
    
    # Track overall success
    all_passed = True
    
    # Run unit tests
    unit_success = run_unit_tests()
    all_passed = all_passed and unit_success
    
    # Run integration tests
    integration_success = run_integration_tests()
    all_passed = all_passed and integration_success
    
    # Summary
    print("\n" + "#"*60)
    print("# TEST SUMMARY")
    print("#"*60)
    print(f"Unit Tests: {'PASSED' if unit_success else 'FAILED'}")
    print(f"Integration Tests: {'PASSED' if integration_success else 'FAILED'}")
    print(f"Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print(f"# Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*60 + "\n")
    
    return all_passed


def run_specific_test(test_name):
    """Run a specific test class or method."""
    print(f"\n Running specific test: {test_name}")
    
    # Try to load and run the specific test
    suite = unittest.TestLoader().loadTestsFromName(test_name)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description='Run onboarding tests')
    parser.add_argument(
        '--suite',
        choices=['unit', 'integration', 'all'],
        default='all',
        help='Which test suite to run'
    )
    parser.add_argument(
        '--test',
        type=str,
        help='Run a specific test (e.g., test_onboarding.TestOnboardingComponents.test_demographics_step_initialization)'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Run with coverage reporting (requires coverage.py)'
    )
    
    args = parser.parse_args()
    
    # Handle coverage if requested
    if args.coverage:
        try:
            import coverage
            cov = coverage.Coverage()
            cov.start()
        except ImportError:
            print("Warning: coverage.py not installed. Install with: pip install coverage")
            args.coverage = False
    
    # Run tests based on arguments
    success = False
    
    if args.test:
        # Run specific test
        success = run_specific_test(args.test)
    elif args.suite == 'unit':
        success = run_unit_tests()
    elif args.suite == 'integration':
        success = run_integration_tests()
    else:
        success = run_all_tests()
    
    # Report coverage if enabled
    if args.coverage and 'cov' in locals():
        cov.stop()
        print("\n" + "="*60)
        print("COVERAGE REPORT")
        print("="*60)
        cov.report()
        cov.html_report(directory='htmlcov')
        print("\nDetailed HTML coverage report generated in: htmlcov/index.html")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()