# app/services/statistics.py
import decimal
import math
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
import scipy.stats as stats

logger = logging.getLogger(__name__)

class StatisticsService:
    """Service for statistical calculations related to A/B testing"""
    
    @staticmethod
    def _ensure_float(value: Union[int, float, decimal.Decimal]) -> float:
        """Convert any numeric type to float"""
        if isinstance(value, decimal.Decimal):
            return float(value)
        return float(value)
    
    @staticmethod
    def analyze_experiment_results(
        data: Dict[str, Dict[str, Any]],
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Analyze experiment results and generate statistical insights
        
        Args:
            data: Dictionary of variant data in the format:
                 {
                     "variant_name": {
                         "conversion": int,
                         "impression": int
                     },
                     ...
                 }
            confidence_level: Statistical confidence level
            
        Returns:
            Dictionary with statistical analysis
        """
        try:
            # Validate input
            if len(data) < 2:
                raise ValueError("Need at least two variants to compare")
                
            result = {
                "variants": {},
                "comparisons": []
            }
            
            # Identify the control variant (first one by default)
            control_name = next(iter(data.keys()))
            control_data = data[control_name]
            
            # Calculate rates and confidence intervals for each variant
            for name, counts in data.items():
                try:
                    conversions = StatisticsService._ensure_float(counts.get("conversion", 0))
                    impressions = StatisticsService._ensure_float(counts.get("impression", 0))
                    
                    # Calculate conversion rate
                    rate = conversions / impressions if impressions > 0 else 0
                    
                    # Calculate confidence interval
                    lower, upper = StatisticsService.calculate_confidence_interval(
                        conversions, impressions, confidence_level
                    )
                    
                    result["variants"][name] = {
                        "conversions": conversions,
                        "impressions": impressions,
                        "rate": rate,
                        "confidence_interval": [lower, upper]
                    }
                except Exception as e:
                    logger.warning(f"Error calculating stats for variant {name}: {str(e)}")
                    # Provide default values
                    result["variants"][name] = {
                        "conversions": 0,
                        "impressions": 0,
                        "rate": 0,
                        "confidence_interval": [0, 0]
                    }
            
            # For each non-control variant, compare to control
            for name, counts in data.items():
                if name == control_name:
                    continue
                    
                try:
                    variant_data = result["variants"][name]
                    control_stats = result["variants"][control_name]
                    
                    # Calculate p-value
                    p_value = StatisticsService.calculate_p_value(
                        control_stats["conversions"], control_stats["impressions"],
                        variant_data["conversions"], variant_data["impressions"]
                    )
                    
                    # Calculate relative improvement
                    rel_improvement = StatisticsService.calculate_relative_improvement(
                        control_stats["rate"], variant_data["rate"]
                    )
                    
                    # Determine if the result is statistically significant
                    is_significant = p_value < (1 - confidence_level)
                    
                    # Determine if the variant is winning, losing, or inconclusive
                    if is_significant:
                        if rel_improvement > 0:
                            status = "winning"
                        else:
                            status = "losing"
                    else:
                        status = "inconclusive"
                    
                    result["comparisons"].append({
                        "variant": name,
                        "control": control_name,
                        "absolute_difference": variant_data["rate"] - control_stats["rate"],
                        "relative_improvement": rel_improvement,
                        "p_value": p_value,
                        "is_significant": is_significant,
                        "status": status
                    })
                except Exception as e:
                    logger.warning(f"Error comparing variant {name} to control: {str(e)}")
                    # Provide default comparison
                    result["comparisons"].append({
                        "variant": name,
                        "control": control_name,
                        "absolute_difference": 0,
                        "relative_improvement": 0,
                        "p_value": 1,
                        "is_significant": False,
                        "status": "inconclusive"
                    })
            
            return result
        except Exception as e:
            logger.exception(f"Error analyzing experiment results: {type(e)}")
            raise
    
    @staticmethod
    def calculate_sample_size(
        base_rate: Union[float, decimal.Decimal], 
        min_detectable_effect: Union[float, decimal.Decimal], 
        confidence_level: float = 0.95, 
        power: float = 0.8
    ) -> int:
        """
        Calculate the required sample size per variant
        
        Args:
            base_rate: Baseline conversion rate (e.g., 0.2 for 20%)
            min_detectable_effect: Minimum detectable effect (e.g., 0.05 for 5% absolute improvement)
            confidence_level: Statistical confidence level (default: 0.95 for 95%)
            power: Statistical power (default: 0.8 for 80%)
            
        Returns:
            Required sample size per variant
        """
        # Convert to float and validate inputs
        base_rate = StatisticsService._ensure_float(base_rate)
        min_detectable_effect = StatisticsService._ensure_float(min_detectable_effect)
        confidence_level = StatisticsService._ensure_float(confidence_level)
        power = StatisticsService._ensure_float(power)
        
        if not 0 <= base_rate <= 1:
            raise ValueError("Base rate must be between 0 and 1")
        if not 0 < min_detectable_effect <= 1:
            raise ValueError("Minimum detectable effect must be between 0 and 1")
        if not 0 < confidence_level < 1:
            raise ValueError("Confidence level must be between 0 and 1")
        if not 0 < power < 1:
            raise ValueError("Power must be between 0 and 1")
            
        # Get Z values for confidence level and power
        z_alpha = stats.norm.ppf(1 - (1 - confidence_level) / 2)  # Two-tailed
        z_beta = stats.norm.ppf(power)
        
        # Expected rates in control and treatment
        p1 = base_rate
        p2 = base_rate + min_detectable_effect
        
        # Pooled probability
        p_pooled = (p1 + p2) / 2
        
        # Calculate sample size per group
        numerator = (z_alpha * math.sqrt(2 * p_pooled * (1 - p_pooled)) + 
                    z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        denominator = (p2 - p1) ** 2
        
        # Return ceiling of sample size
        return math.ceil(numerator / denominator)
    
    @staticmethod
    def calculate_confidence_interval(
        successes: Union[int, decimal.Decimal], 
        trials: Union[int, decimal.Decimal], 
        confidence_level: float = 0.95
    ) -> Tuple[float, float]:
        """
        Calculate the confidence interval for a proportion
        
        Args:
            successes: Number of successes (e.g., conversions)
            trials: Number of trials (e.g., impressions)
            confidence_level: Statistical confidence level (default: 0.95 for 95%)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        # Convert to float
        successes = StatisticsService._ensure_float(successes)
        trials = StatisticsService._ensure_float(trials)
        confidence_level = StatisticsService._ensure_float(confidence_level)
        
        if trials == 0:
            return (0, 0)
        
        # Proportion
        p_hat = successes / trials
        
        # Z value for confidence level
        z = stats.norm.ppf(1 - (1 - confidence_level) / 2)
        
        # Standard error
        se = math.sqrt(p_hat * (1 - p_hat) / trials)
        
        # Confidence interval
        lower = max(0, p_hat - z * se)
        upper = min(1, p_hat + z * se)
        
        return (lower, upper)
    
    @staticmethod
    def calculate_p_value(
        successes_a: Union[int, decimal.Decimal], 
        trials_a: Union[int, decimal.Decimal],
        successes_b: Union[int, decimal.Decimal], 
        trials_b: Union[int, decimal.Decimal]
    ) -> float:
        """
        Calculate the p-value for the difference between two proportions
        using the chi-squared test
        
        Args:
            successes_a: Number of successes in variant A
            trials_a: Number of trials in variant A
            successes_b: Number of successes in variant B
            trials_b: Number of trials in variant B
            
        Returns:
            p-value (probability that the observed difference is due to chance)
        """
        # Convert to float
        successes_a = StatisticsService._ensure_float(successes_a)
        trials_a = StatisticsService._ensure_float(trials_a)
        successes_b = StatisticsService._ensure_float(successes_b)
        trials_b = StatisticsService._ensure_float(trials_b)
        
        # Create contingency table
        # [ successes_a, successes_b ]
        # [ trials_a - successes_a, trials_b - successes_b ]
        contingency = [
            [successes_a, successes_b],
            [trials_a - successes_a, trials_b - successes_b]
        ]
        
        # Calculate chi-squared statistic and p-value
        _, p_value, _, _ = stats.chi2_contingency(contingency)
        
        return p_value
    
    @staticmethod
    def calculate_relative_improvement(
        rate_control: Union[float, decimal.Decimal],
        rate_treatment: Union[float, decimal.Decimal]
    ) -> float:
        """
        Calculate the relative improvement of the treatment compared to control
        
        Args:
            rate_control: Conversion rate of the control group
            rate_treatment: Conversion rate of the treatment group
            
        Returns:
            Relative improvement (e.g., 0.15 for 15% improvement)
        """
        # Convert to float
        rate_control = StatisticsService._ensure_float(rate_control)
        rate_treatment = StatisticsService._ensure_float(rate_treatment)
        
        if rate_control == 0:
            # Avoid division by zero
            return float('inf') if rate_treatment > 0 else 0
            
        return (rate_treatment - rate_control) / rate_control

# Initialize the global service
statistics_service = StatisticsService()