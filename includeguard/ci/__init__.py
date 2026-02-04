"""
CI/CD Integration Module for IncludeGuard
"""
from .github_action import generate_pr_comment, check_thresholds

__all__ = ['generate_pr_comment', 'check_thresholds']
