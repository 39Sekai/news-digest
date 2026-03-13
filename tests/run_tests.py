"""
QA Test Suite Runner
Runs all test modules for the News Digest v2 project
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def run_all_tests():
    """Run all tests with verbose output"""
    args = [
        '-v',
        '--tb=short',
        '-x',  # Stop on first failure
        os.path.dirname(__file__)
    ]
    
    return pytest.main(args)


def run_scorer_tests():
    """Run only scorer tests"""
    args = [
        '-v',
        os.path.join(os.path.dirname(__file__), 'test_scorer.py')
    ]
    
    return pytest.main(args)


def run_fetcher_tests():
    """Run only fetcher tests"""
    args = [
        '-v',
        os.path.join(os.path.dirname(__file__), 'test_fetcher.py')
    ]
    
    return pytest.main(args)


def run_database_tests():
    """Run only database tests"""
    args = [
        '-v',
        os.path.join(os.path.dirname(__file__), 'test_database.py')
    ]
    
    return pytest.main(args)


def run_discord_tests():
    """Run only discord tests"""
    args = [
        '-v',
        os.path.join(os.path.dirname(__file__), 'test_discord.py')
    ]
    
    return pytest.main(args)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run News Digest v2 QA Tests')
    parser.add_argument(
        '--module',
        choices=['all', 'scorer', 'fetcher', 'database', 'discord'],
        default='all',
        help='Which test module to run (default: all)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("News Digest v2 - QA Test Suite")
    print("=" * 60)
    print()
    
    if args.module == 'all':
        exit_code = run_all_tests()
    elif args.module == 'scorer':
        exit_code = run_scorer_tests()
    elif args.module == 'fetcher':
        exit_code = run_fetcher_tests()
    elif args.module == 'database':
        exit_code = run_database_tests()
    elif args.module == 'discord':
        exit_code = run_discord_tests()
    
    sys.exit(exit_code)
